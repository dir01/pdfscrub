import fitz


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
        for term in terms:
            needle = term if case_sensitive else term.lower()
            haystack = value if case_sensitive else value.lower()
            if needle in haystack:
                hits[field] = value
                break

    return hits
