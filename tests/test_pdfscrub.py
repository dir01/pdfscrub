import fitz
import pytest
import os
from pdfscrub.search import search_pdf, search_metadata, image_only_pages
from pdfscrub.redact import redact_pdf


def make_pdf(path: str, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


def test_search_finds_term(tmp_path):
    pdf = str(tmp_path / "test.pdf")
    make_pdf(pdf, "Hello John Doe, welcome.")
    results = search_pdf(pdf, ["John Doe"])
    assert 1 in results
    assert any(term == "John Doe" for term, _ in results[1])


def test_search_returns_empty_when_no_match(tmp_path):
    pdf = str(tmp_path / "test.pdf")
    make_pdf(pdf, "No sensitive data here.")
    results = search_pdf(pdf, ["John Doe"])
    assert results == {}


def test_redact_removes_term(tmp_path):
    pdf = str(tmp_path / "input.pdf")
    out = str(tmp_path / "output.pdf")
    make_pdf(pdf, "Hello John Doe, welcome.")

    counts = redact_pdf(pdf, out, ["John Doe"])

    assert counts  # something was redacted
    results = search_pdf(out, ["John Doe"])
    assert results == {}


def test_redact_no_match_saves_file(tmp_path):
    pdf = str(tmp_path / "input.pdf")
    out = str(tmp_path / "output.pdf")
    make_pdf(pdf, "Nothing sensitive.")

    counts = redact_pdf(pdf, out, ["John Doe"])

    assert counts == {}
    assert os.path.exists(out)


def make_image_pdf(path: str) -> None:
    """Create a PDF whose page contains a raster image but no text layer."""
    import struct, zlib

    def _png_1x1_white() -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"
        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        raw = zlib.compress(b"\x00\xff\xff\xff")
        idat = chunk(b"IDAT", raw)
        iend = chunk(b"IEND", b"")
        return sig + ihdr + idat + iend

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_image(fitz.Rect(0, 0, 200, 200), stream=_png_1x1_white())
    doc.save(path)
    doc.close()


def test_image_only_pages_detected(tmp_path):
    pdf = str(tmp_path / "scan.pdf")
    make_image_pdf(pdf)
    assert image_only_pages(pdf) == [1]


def test_text_pdf_not_flagged_as_image_only(tmp_path):
    pdf = str(tmp_path / "text.pdf")
    make_pdf(pdf, "Hello world")
    assert image_only_pages(pdf) == []


def test_metadata_search(tmp_path):
    pdf = str(tmp_path / "meta.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({"author": "John Doe", "title": "Test Doc"})
    doc.save(pdf)
    doc.close()

    hits = search_metadata(pdf, ["John Doe"])
    assert "author" in hits
