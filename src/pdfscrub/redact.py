import fitz


def redact_pdf(
    input_path: str,
    output_path: str,
    terms: list[str],
    fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scrub_metadata: bool = True,
) -> dict[int, int]:
    """
    Redact all occurrences of each term from the PDF and save to output_path.
    Returns a dict mapping 1-based page numbers to the number of redactions made.
    fill_color is an RGB tuple with values in [0, 1].
    """
    doc = fitz.open(input_path)
    redaction_counts: dict[int, int] = {}

    for page in doc:
        count = 0
        for term in terms:
            quads = page.search_for(term, quads=True)
            for quad in quads:
                page.add_redact_annot(quad.rect, fill=fill_color)
                count += 1

        if count:
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_PIXELS,
                graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                text=fitz.PDF_REDACT_TEXT_REMOVE,
            )
            redaction_counts[page.number + 1] = count

    if scrub_metadata:
        _scrub_metadata(doc, terms)

    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()

    return redaction_counts


def _scrub_metadata(doc: fitz.Document, terms: list[str]) -> None:
    meta = doc.metadata or {}
    cleaned = {}
    for field, value in meta.items():
        if not value:
            cleaned[field] = value
            continue
        new_value = value
        for term in terms:
            new_value = new_value.replace(term, "[REDACTED]")
        cleaned[field] = new_value
    doc.set_metadata(cleaned)
