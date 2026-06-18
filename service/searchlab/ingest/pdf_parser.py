from pathlib import Path
from typing import NamedTuple

import fitz  # pymupdf


class PageText(NamedTuple):
    page_number: int  # 1-indexed
    text: str


def parse_pdf(path: Path) -> list[PageText]:
    pages = []
    with fitz.open(str(path)) as doc:
        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append(PageText(page_number=i + 1, text=text))
    return pages
