import sys
import click
from .search import search_pdf, search_raw_bytes, search_metadata, image_only_pages
from .redact import redact_pdf


@click.group()
def cli():
    """pdfscrub — search and redact sensitive text from PDF files."""


@cli.command("find")
@click.argument("pdfs", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--terms-file", "-f", type=click.Path(exists=True), multiple=True,
              help="File of terms to search, one per line. Can be used multiple times. "
                   "Blank lines and lines starting with # are ignored.")
@click.option("--raw", is_flag=True, help="Also scan raw PDF byte stream (catches hidden streams and metadata).")
@click.option("--case-sensitive", "-c", is_flag=True, help="Case-sensitive matching.")
@click.option("--inline-terms", "-t", multiple=True, metavar="TERM",
              help="Term to search for. Can be used multiple times.")
def find_cmd(pdfs, inline_terms, terms_file, raw, case_sensitive):
    """Search for terms in one or more PDFs. Accepts wildcards via shell expansion."""
    terms = _load_terms(inline_terms, terms_file)
    found_anything = False

    for pdf in pdfs:
        if len(pdfs) > 1:
            click.echo(click.style(f"\n{pdf}", bold=True))

        _warn_image_only_pages(pdf)

        # Visible text
        results = search_pdf(pdf, terms, case_sensitive=case_sensitive)
        if results:
            found_anything = True
            click.echo(click.style("Visible text matches:", fg="yellow", bold=True))
            for page_num, hits in sorted(results.items()):
                for term, rect in hits:
                    click.echo(f"  page {page_num}: {click.style(repr(term), fg='red')}  @ {rect}")
        else:
            click.echo("No visible text matches found.")

        # Metadata
        meta_hits = search_metadata(pdf, terms, case_sensitive=case_sensitive)
        if meta_hits:
            found_anything = True
            click.echo(click.style("\nMetadata matches:", fg="yellow", bold=True))
            for field, value in meta_hits.items():
                click.echo(f"  {field}: {click.style(value, fg='red')}")
        else:
            click.echo("No metadata matches found.")

        # Raw byte stream
        if raw:
            raw_hits = search_raw_bytes(pdf, terms, case_sensitive=case_sensitive)
            if raw_hits:
                found_anything = True
                click.echo(click.style(f"\nRaw stream matches ({len(raw_hits)} lines):", fg="yellow", bold=True))
                for line in raw_hits[:50]:
                    click.echo(f"  {line.strip()}")
                if len(raw_hits) > 50:
                    click.echo(f"  ... and {len(raw_hits) - 50} more lines")
            else:
                click.echo("No raw stream matches found.")

    sys.exit(1 if found_anything else 0)


@cli.command("scrub")
@click.argument("pdfs", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--terms-file", "-f", type=click.Path(exists=True), multiple=True,
              help="File of terms to redact, one per line. Can be used multiple times. "
                   "Blank lines and lines starting with # are ignored.")
@click.option("--inline-terms", "-t", multiple=True, metavar="TERM",
              help="Term to redact. Can be used multiple times.")
@click.option("--output-dir", "-o", default=None, type=click.Path(),
              help="Directory for redacted files (default: same directory as input). "
                   "Each output is named <stem>.redacted.pdf.")
@click.option("--color", default="black", type=click.Choice(["black", "white"]), help="Redaction fill color.")
@click.option("--keep-metadata", is_flag=True, help="Do not scrub metadata fields.")
@click.option("--no-verify", is_flag=True, help="Skip post-scrub verification.")
@click.option("--jitter", default=1.0, show_default=True, metavar="CHARS",
              help="Randomly widen/narrow each redaction box by up to CHARS character-widths "
                   "so box size doesn't reveal the exact length of redacted text. Set to 0 to disable.")
def scrub_cmd(pdfs, inline_terms, terms_file, output_dir, color, keep_metadata, no_verify, jitter):
    """Redact terms from one or more PDFs. Accepts wildcards via shell expansion."""
    terms = _load_terms(inline_terms, terms_file)
    fill = (0.0, 0.0, 0.0) if color == "black" else (1.0, 1.0, 1.0)
    any_failed = False

    for pdf in pdfs:
        if len(pdfs) > 1:
            click.echo(click.style(f"\n{pdf}", bold=True))

        stem = pdf.rsplit(".", 1)[0]
        if output_dir:
            import os
            stem = os.path.join(output_dir, os.path.basename(stem))
        output = stem + ".redacted.pdf"

        _warn_image_only_pages(pdf)

        click.echo(f"Redacting {len(terms)} term(s) from {click.style(pdf, bold=True)} ...")
        counts = redact_pdf(pdf, output, terms, fill_color=fill, scrub_metadata=not keep_metadata, jitter=jitter)

        if counts:
            total = sum(counts.values())
            click.echo(click.style(f"  Redacted {total} occurrence(s) across {len(counts)} page(s):", fg="green"))
            for page_num, n in sorted(counts.items()):
                click.echo(f"    page {page_num}: {n} hit(s)")
        else:
            click.echo(click.style("  No visible text matches found — file saved unchanged.", fg="yellow"))

        click.echo(f"Saved to {click.style(output, bold=True)}")

        if not no_verify:
            click.echo("\nVerifying redacted file ...")
            results = search_pdf(output, terms)
            meta_hits = search_metadata(output, terms)
            if results or meta_hits:
                click.echo(click.style("WARNING: terms still found in redacted file!", fg="red", bold=True))
                for page_num, hits in sorted(results.items()):
                    for term, rect in hits:
                        click.echo(f"  page {page_num}: {repr(term)} @ {rect}")
                for field, value in meta_hits.items():
                    click.echo(f"  metadata {field}: {value}")
                any_failed = True
            else:
                click.echo(click.style("  Verification passed — terms not found in output.", fg="green"))

    if any_failed:
        sys.exit(1)


def _load_terms(inline: tuple[str, ...] | list[str], files: tuple[str, ...]) -> list[str]:
    terms: list[str] = list(inline)
    for path in files:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    terms.append(line)
    if not terms:
        raise click.UsageError("Provide at least one term as an argument or via --terms-file / -f.")
    return terms


def _warn_image_only_pages(pdf: str) -> None:
    pages = image_only_pages(pdf)
    if not pages:
        return
    page_list = ", ".join(str(p) for p in pages)
    ocr_out = pdf.rsplit(".", 1)[0] + ".ocr.pdf"
    click.echo(
        click.style(
            f"WARNING: page(s) {page_list} appear to be scanned images with no text layer. "
            f"Text search cannot find content on these pages. Run OCR first:\n"
            f"  ocrmypdf {pdf} {ocr_out}",
            fg="yellow",
            bold=True,
        ),
        err=True,
    )
