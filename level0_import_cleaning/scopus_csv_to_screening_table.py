#!/usr/bin/env python3
"""Convert a Scopus CSV export to a screening-ready CSV table."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


FIELDS = [
    "screening_id",
    "record_key",
    "entry_type",
    "title",
    "year",
    "authors",
    "first_author",
    "source_title",
    "volume",
    "issue",
    "pages",
    "doi",
    "scopus_url",
    "document_type",
    "publication_stage",
    "scopus_source",
    "language",
    "citation_note",
    "open_access_note",
    "pdf_search_query",
    "suggested_pdf_filename",
    "pdf_status",
    "pdf_file_path",
    "duplicate_group",
    "duplicate_decision",
    "level_1_title_decision",
    "level_1_exclusion_criterion",
    "level_1_notes",
    "level_2_abstract_decision",
    "level_2_exclusion_criterion",
    "level_2_notes",
    "level_3_fulltext_decision",
    "level_3_exclusion_criterion",
    "level_3_notes",
    "final_decision",
    "included_reason",
    "abstract",
    "author_keywords",
    "index_keywords",
    "abstract_source_key",
    "abstract_source_status",
]


def safe_filename(title: str, year: str, doi: str) -> str:
    base = f"{year} - {title}" if year else title
    if not base and doi:
        base = doi
    base = re.sub(r"[\\/:*?\"<>|]", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    if len(base) > 180:
        base = base[:180].rstrip()
    return f"{base}.pdf" if base else ""


def pdf_search_query(title: str, doi: str) -> str:
    if doi:
        return doi
    if title:
        return f'"{title}" pdf'
    return ""


def pages_from_scopus_csv(row: dict[str, str]) -> str:
    start = row.get("Page start", "").strip()
    end = row.get("Page end", "").strip()
    if start and end:
        return f"{start}-{end}"
    return start or end


def first_scopus_author(authors: str) -> str:
    if not authors:
        return ""
    return authors.split(";")[0].strip()


def row_from_scopus_csv(index: int, source_row: dict[str, str]) -> dict[str, str]:
    title = source_row.get("Title", "").strip()
    year = source_row.get("Year", "").strip()
    authors = source_row.get("Authors", "").strip()
    doi = source_row.get("DOI", "").strip()
    eid = source_row.get("EID", "").strip()
    cited_by = source_row.get("Cited by", "").strip()
    open_access = source_row.get("Open Access", "").strip()
    return {
        "screening_id": f"NS{index:04d}",
        "record_key": eid or f"SCOPUSCSV{index:04d}",
        "entry_type": source_row.get("Document Type", "").strip(),
        "title": title,
        "year": year,
        "authors": authors,
        "first_author": first_scopus_author(authors),
        "source_title": source_row.get("Source title", "").strip(),
        "volume": source_row.get("Volume", "").strip(),
        "issue": source_row.get("Issue", "").strip(),
        "pages": pages_from_scopus_csv(source_row),
        "doi": doi,
        "scopus_url": source_row.get("Link", "").strip(),
        "document_type": source_row.get("Document Type", "").strip(),
        "publication_stage": source_row.get("Publication Stage", "").strip(),
        "scopus_source": source_row.get("Source", "").strip(),
        "language": source_row.get("Language of Original Document", "").strip(),
        "citation_note": f"Cited by {cited_by}" if cited_by else "",
        "open_access_note": open_access,
        "pdf_search_query": pdf_search_query(title, doi),
        "suggested_pdf_filename": safe_filename(title, year, doi),
        "pdf_status": "",
        "pdf_file_path": "",
        "duplicate_group": "",
        "duplicate_decision": "",
        "level_1_title_decision": "",
        "level_1_exclusion_criterion": "",
        "level_1_notes": "",
        "level_2_abstract_decision": "",
        "level_2_exclusion_criterion": "",
        "level_2_notes": "",
        "level_3_fulltext_decision": "",
        "level_3_exclusion_criterion": "",
        "level_3_notes": "",
        "final_decision": "",
        "included_reason": "",
        "abstract": source_row.get("Abstract", "").strip(),
        "author_keywords": source_row.get("Author Keywords", "").strip(),
        "index_keywords": source_row.get("Index Keywords", "").strip(),
        "abstract_source_key": eid,
        "abstract_source_status": "from_scopus_csv" if source_row.get("Abstract", "").strip() else "missing_abstract",
    }


def rows_from_scopus_csv(input_path: Path) -> list[dict[str, str]]:
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    required_columns = {"Title", "Year", "DOI", "Abstract", "Document Type"}
    missing = sorted(required_columns - set(reader.fieldnames or []))
    if missing:
        raise ValueError(f"Input CSV is missing required Scopus columns: {', '.join(missing)}")
    return [row_from_scopus_csv(index, row) for index, row in enumerate(rows, start=1)]


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    if len(sys.argv) == 1:
        matches = sorted(script_dir.glob("scopus_export_*.csv"))
        if not matches:
            print("Usage: scopus_csv_to_screening_table.py input.csv output.csv", file=sys.stderr)
            return 2
        input_path = matches[0]
        output_path = script_dir / "screening_table.csv"
    elif len(sys.argv) == 3:
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
    else:
        print("Usage: scopus_csv_to_screening_table.py input.csv output.csv", file=sys.stderr)
        return 2
    if input_path.suffix.lower() != ".csv":
        print("This converter expects a Scopus CSV export.", file=sys.stderr)
        return 2
    rows = rows_from_scopus_csv(input_path)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
