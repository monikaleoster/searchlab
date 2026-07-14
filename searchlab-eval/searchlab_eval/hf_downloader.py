import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SPLIT_PREFERENCE = ["baseline", "test"]


def download_hf_dataset(hf_name: str, data_dir: Path) -> int:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("datasets is not installed — run: uv sync") from exc

    ds_dict = load_dataset(hf_name,'ragas_eval_v3')

    split = None
    for candidate in _SPLIT_PREFERENCE:
        if candidate in ds_dict:
            split = candidate
            break
    if split is None:
        split = next(iter(ds_dict))

    logger.info("Using split '%s' from %s", split, hf_name)
    dataset = ds_dict[split]

    out_path = data_dir / "records.jsonl"
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for record in dataset:
            # ragas_eval_v3 uses user_input/reference/retrieved_contexts;
            # older configs use question/ground_truth/contexts.
            row = {
                "question": record.get("user_input") or record["question"],
                "ground_truth": record.get("reference") or record["ground_truth"],
                "contexts": (
                    record.get("retrieved_contexts")
                    or record.get("contexts")
                    or []
                ),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    return count


def load_hf_records(data_dir: Path) -> list[dict]:
    records_path = data_dir / "records.jsonl"
    if not records_path.exists():
        raise FileNotFoundError(
            f"records not found at {records_path} — "
            f"run: searchlab-eval download --dataset {data_dir.name.replace('-', '/', 1)}"
        )
    records = []
    with records_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def slice_hf(records: list[dict], n: int) -> list[dict]:
    if n == 0:
        return records
    return records[:n]