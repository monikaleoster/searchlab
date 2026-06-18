import pytest
from searchlab.ingest.chunker import chunk, CHUNK_SIZE
from searchlab.ingest.pdf_parser import PageText


def _page(text: str, num: int = 1) -> PageText:
    return PageText(page_number=num, text=text)


def test_empty_pages():
    assert chunk([]) == []


def test_single_page_under_limit():
    result = chunk([_page("hello world")])
    assert len(result) == 1
    assert result[0].position == 0
    assert result[0].page_number == 1
    assert "hello" in result[0].text


def test_single_page_over_limit():
    long_text = "word " * (CHUNK_SIZE + 10)
    result = chunk([_page(long_text)])
    assert len(result) == 2


def test_page_attribution_on_split():
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    # Build page 1 with exactly CHUNK_SIZE tokens by decoding CHUNK_SIZE tokens from
    # varied English text; BPE boundaries in ASCII prose round-trip cleanly.
    seed = ("The quick brown fox jumps over the lazy dog. " * 100 +
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50)
    seed_tokens = enc.encode(seed)
    assert len(seed_tokens) >= CHUNK_SIZE
    page1_text = enc.decode(seed_tokens[:CHUNK_SIZE])
    assert len(enc.encode(page1_text)) == CHUNK_SIZE, "token boundary split a multi-char token"

    page2_text = "hello world"
    result = chunk([_page(page1_text, num=1), _page(page2_text, num=2)])
    assert len(result) == 2
    assert result[0].page_number == 1
    assert result[1].page_number == 2


def test_positions_are_sequential():
    long_text = "word " * (CHUNK_SIZE * 3)
    result = chunk([_page(long_text)])
    for i, c in enumerate(result):
        assert c.position == i


@pytest.mark.integration
def test_parse_sample_pdf():
    from pathlib import Path
    from searchlab.ingest.pdf_parser import parse_pdf
    path = Path(__file__).parent.parent.parent / "test-corpus" / "sample.pdf"
    if not path.exists():
        pytest.skip("test-corpus/sample.pdf not present")
    pages = parse_pdf(path)
    assert len(pages) >= 1
    assert any(p.text.strip() for p in pages)
