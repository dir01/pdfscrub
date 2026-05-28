import fitz
import pytest
import os
from pdfscrub.search import search_pdf, search_metadata
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


def test_metadata_search(tmp_path):
    pdf = str(tmp_path / "meta.pdf")
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({"author": "John Doe", "title": "Test Doc"})
    doc.save(pdf)
    doc.close()

    hits = search_metadata(pdf, ["John Doe"])
    assert "author" in hits
