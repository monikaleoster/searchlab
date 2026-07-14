"""
Generation and RAGAS scoring for Phase 2 evaluation.

Generation: calls POST /rag on the running searchlab service once per query.
Scoring:    runs RAGAS metrics locally against the generated answers.
"""
from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

import requests
from tqdm import tqdm

# ── Compatibility shim ──────────────────────────────────────────────────────
# ragas 0.2.x imports langchain_community.chat_models.vertexai at module
# level, but langchain-community ≥ 0.3 removed that submodule.
for _mod_name in (
    "langchain_community.chat_models.vertexai",
    "langchain_community.llms.vertexai",
):
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        _stub.ChatVertexAI = type("ChatVertexAI", (), {})  # type: ignore[attr-defined]
        _stub.VertexAI = type("VertexAI", (), {})  # type: ignore[attr-defined]
        sys.modules[_mod_name] = _stub
# ───────────────────────────────────────────────────────────────────────────

# Datasets that ship Q&A ground truth enabling all four RAGAS metrics.
FOUR_METRIC_DATASETS = {"fiqa"}


def _load_corpus(data_dir: Path) -> dict[str, str]:
    corpus: dict[str, str] = {}
    with open(data_dir / "corpus.jsonl") as fh:
        for line in fh:
            obj = json.loads(line)
            title = obj.get("title", "")
            text = obj.get("text", "")
            corpus[obj["_id"]] = (f"{title} {text}").strip() if title else text
    return corpus


def _load_ground_truth(
    data_dir: Path,
    dataset: str,
    corpus: dict[str, str],
) -> dict[str, str | None]:
    """Return {query_id: passage_text} for datasets with ground truth.

    For FiQA, the relevant corpus passages are the answers — we pick the
    highest-scored qrel doc per query as the reference answer.
    """
    if dataset not in FOUR_METRIC_DATASETS:
        return {}

    best: dict[str, tuple[str, int]] = {}
    with open(data_dir / "qrels" / "test.tsv", newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        next(reader)
        for row in reader:
            if len(row) < 3:
                continue
            qid, doc_id, score = row[0], row[1], int(row[2])
            if qid not in best or best[qid][1] < score:
                best[qid] = (doc_id, score)

    return {qid: corpus.get(info[0]) for qid, info in best.items()}


def generate(
    queries: dict[str, str],
    data_dir: Path,
    dataset: str,
    searchlab_url: str,
    top_k: int = 10,
) -> list[dict]:
    """Call POST /rag once per query; return list of per-query result dicts."""
    corpus = _load_corpus(data_dir)
    ground_truth = _load_ground_truth(data_dir, dataset, corpus)
    results: list[dict] = []

    for query_id, question in tqdm(queries.items(), desc="Generating", unit="q"):
        try:
            resp = requests.post(
                f"{searchlab_url}/rag",
                data={"question": question, "topK": str(top_k), "dataset": dataset},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            print(
                f"\nError: searchlab service unreachable at {searchlab_url}",
                file=sys.stderr,
            )
            sys.exit(1)
        except requests.exceptions.Timeout:
            print(f"Warning: query {query_id!r} timed out — skipping", file=sys.stderr)
            continue
        except Exception as exc:
            print(f"Warning: query {query_id!r} failed: {exc}", file=sys.stderr)
            continue

        if "error" in data:
            msg = data["error"]
            if "OPENAI_API_KEY" in msg:
                print(
                    "\nOPENAI_API_KEY is not set on the service — skipping generation.\n"
                    "Set OPENAI_API_KEY in the service environment and retry.",
                    file=sys.stderr,
                )
                sys.exit(0)
            print(f"Warning: query {query_id!r} returned error: {msg}", file=sys.stderr)
            continue

        # source_filename == doc_id for BEIR corpus docs (see service/ingest/indexer.py)
        contexts = [
            corpus.get(str(s["filename"]), "")
            for s in data.get("sources", [])
            if s.get("filename")
        ]

        results.append({
            "query_id":    query_id,
            "question":    question,
            "contexts":    contexts,
            "answer":      data.get("answer", ""),
            "ground_truth": ground_truth.get(query_id),
        })

    return results


def score(
    results: list[dict],
    dataset: str,
    judge_model: str,
) -> tuple[dict[str, float], dict[str, dict[str, float | None]], list[str]]:
    """Run RAGAS locally; return (aggregate, per_query, measure_names).

    FiQA gets all four metrics; nfcorpus gets the two that need no ground truth.
    A single bad judge response is caught per-query and excluded from the
    aggregate — the batch does not abort.
    """
    from datasets import Dataset
    from langchain_openai import ChatOpenAI
    from ragas import evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_relevancy, faithfulness

    use_ground_truth = dataset in FOUR_METRIC_DATASETS
    metrics = [faithfulness, answer_relevancy]
    measure_names = ["faithfulness", "answer_relevancy"]

    if use_ground_truth:
        from ragas.metrics import context_precision, context_recall
        metrics += [context_recall, context_precision]
        measure_names += ["context_recall", "context_precision"]
    else:
        print(
            f"Note: context_recall and context_precision require ground truth — "
            f"omitting for {dataset}.",
            file=sys.stderr,
        )

    hf_dict: dict = {
        "question": [r["question"] for r in results],
        "answer":   [r["answer"]   for r in results],
        "contexts": [r["contexts"] for r in results],
        "query_id": [r["query_id"] for r in results],
    }
    if use_ground_truth:
        hf_dict["ground_truth"] = [r.get("ground_truth") or "" for r in results]

    ds = Dataset.from_dict(hf_dict)
    llm = LangchainLLMWrapper(ChatOpenAI(model=judge_model, temperature=0))

    result = evaluate(ds, metrics=metrics, llm=llm, raise_exceptions=False)
    df = result.to_pandas()

    per_query: dict[str, dict[str, float | None]] = {}
    for _, row in df.iterrows():
        qid = str(row.get("query_id", _))
        per_query[qid] = {
            m: (float(row[m]) if row.get(m) is not None else None)
            for m in measure_names
            if m in df.columns
        }

    aggregate: dict[str, float] = {}
    for m in measure_names:
        vals = [v[m] for v in per_query.values() if v.get(m) is not None]
        aggregate[m] = round(sum(vals) / len(vals), 6) if vals else 0.0

    return aggregate, per_query, measure_names
