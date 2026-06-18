from dataclasses import dataclass

import tiktoken

from .pdf_parser import PageText

_ENCODING = None
CHUNK_SIZE = 512


def _enc():
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


@dataclass
class Chunk:
    text: str
    page_number: int
    position: int


def chunk(pages: list[PageText]) -> list[Chunk]:
    enc = _enc()

    tokens: list[int] = []
    token_pages: list[int] = []

    for page in pages:
        page_tokens = enc.encode(page.text)
        tokens.extend(page_tokens)
        token_pages.extend([page.page_number] * len(page_tokens))

    chunks: list[Chunk] = []
    position = 0
    for start in range(0, len(tokens), CHUNK_SIZE):
        window = tokens[start : start + CHUNK_SIZE]
        text = enc.decode(window)
        page_num = token_pages[start]
        chunks.append(Chunk(text=text, page_number=page_num, position=position))
        position += 1

    return chunks
