from pathlib import Path


def download_dataset(
    dataset_name: str, data_dir: Path | None = None
) -> tuple[dict, dict, dict]:
    """Download a BEIR dataset and return (corpus, queries, qrels).

    corpus  = {doc_id: {"title": str, "text": str}}
    queries = {query_id: str}
    qrels   = {query_id: {doc_id: int}}
    """
    if data_dir is None:
        data_dir = Path("data") / dataset_name

    # BEIR extracts into parent_dir/<dataset_name>/
    parent_dir = data_dir.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    try:
        from beir import util
        from beir.datasets.data_loader import GenericDataLoader
    except ImportError as exc:
        raise RuntimeError("beir is not installed — run: uv sync") from exc

    url = (
        "https://public.ukp.informatik.tu-darmstadt.de"
        f"/thakur/BEIR/datasets/{dataset_name}.zip"
    )

    try:
        extracted_path = util.download_and_unzip(url, str(parent_dir))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download dataset '{dataset_name}': {exc}"
        ) from exc

    try:
        corpus, queries, qrels = GenericDataLoader(
            data_folder=extracted_path
        ).load(split="test")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load dataset '{dataset_name}' from {extracted_path}: {exc}"
        ) from exc

    return corpus, queries, qrels
