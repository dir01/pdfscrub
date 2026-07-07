from urllib.parse import quote, quote_plus

import fitz


def term_variants(term: str) -> list[str]:
    """
    Return the term plus its URL-encoded forms, so terms embedded in URLs
    (e.g. "01/02/2000" appearing as "01%2F02%2F2000") are still matched.
    """
    return list({term, quote(term, safe=""), quote_plus(term)})


def image_only_pages(pdf_path: str) -> list[int]:
    """
    Return 1-based page numbers that appear to be image-only (no text layer).
    A page qualifies when it contains at least one image and zero text characters,
    which is the signature of a scanned page that hasn't been OCR'd.
    """
    unreadable: list[int] = []
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            has_images = bool(page.get_images())
            has_text = bool(page.get_text().strip())
            if has_images and not has_text:
                unreadable.append(page.number + 1)
    finally:
        doc.close()
    return unreadable


def search_pdf(pdf_path: str, terms: list[str], case_sensitive: bool = False) -> dict[int, list[tuple[str, fitz.Rect]]]:
    """
    Search for terms in a PDF. Returns a dict mapping 1-based page numbers to
    a list of (matched_term, rect) tuples for every hit on that page.
    """
    flags = fitz.TEXT_PRESERVE_WHITESPACE
    if not case_sensitive:
        flags |= fitz.TEXT_DEHYPHENATE

    results: dict[int, list[tuple[str, fitz.Rect]]] = {}

    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            page_num = page.number + 1
            hits: list[tuple[str, fitz.Rect]] = []
            for term in terms:
                quads = page.search_for(term, quads=True)
                for quad in quads:
                    hits.append((term, quad.rect))
            if hits:
                results[page_num] = hits
    finally:
        doc.close()

    return results


def search_raw_bytes(pdf_path: str, terms: list[str], case_sensitive: bool = False) -> list[str]:
    """
    Scan the raw PDF byte stream for terms (catches metadata, hidden streams, etc.).
    Returns list of matched lines.
    """
    matched: list[str] = []
    with open(pdf_path, "rb") as f:
        raw = f.read()

    text = raw.decode("latin-1", errors="replace")
    for line in text.splitlines():
        for term in terms:
            needle = term if case_sensitive else term.lower()
            haystack = line if case_sensitive else line.lower()
            if needle in haystack:
                matched.append(line)
                break

    return matched


def search_metadata(pdf_path: str, terms: list[str], case_sensitive: bool = False) -> dict[str, str]:
    """
    Check PDF metadata fields for any of the given terms.
    Returns dict of {field: value} for fields that matched.
    """
    doc = fitz.open(pdf_path)
    try:
        meta = doc.metadata or {}
    finally:
        doc.close()

    hits: dict[str, str] = {}
    for field, value in meta.items():
        if not value:
            continue
        haystack = value if case_sensitive else value.lower()
        for term in terms:
            for variant in term_variants(term):
                needle = variant if case_sensitive else variant.lower()
                if needle in haystack:
                    hits[field] = value
                    break
            else:
                continue
            break

    return hits
