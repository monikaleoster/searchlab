from pathlib import Path


def is_hf_dataset(name: str) -> bool:
    return "/" in name


def hf_data_dir(name: str) -> Path:
    safe = name.replace("/", "-")
    return Path("data") / safe