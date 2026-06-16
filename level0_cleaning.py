#!/usr/bin/env python3
"""Apply Level 0 bibliographic cleaning to the screening table."""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path


EXCLUDED_DOCUMENT_TYPES = {
    "book": "L0-DOCTYPE",
    "conference review": "L0-DOCTYPE",
    "editorial": "L0-DOCTYPE",
    "erratum": "L0-DOCTYPE",
    "note": "L0-DOCTYPE",
    "retracted": "L0-RETRACTED",
}


def is_english_language(language: str) -> bool:
    if not language.strip():
        return True
    parts = re.split(r"[,;/|]+|\band\b", language.lower())
    return any(part.strip() == "english" for part in parts)


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def decision_for_row(row: dict[str, str]) -> tuple[str, str, str]:
    if not row.get("title") and not row.get("doi") and not row.get("scopus_url"):
        return "Exclude", "L0-NODOC", "No usable title, DOI, or Scopus URL."
    document_type = row.get("document_type", "").strip().lower()
    if document_type in EXCLUDED_DOCUMENT_TYPES:
        code = EXCLUDED_DOCUMENT_TYPES[document_type]
        return "Exclude", code, f"Document type is {row.get('document_type', '')}."
    language = row.get("language", "").strip()
    if not is_english_language(language):
        return "Exclude", "L0-LANGUAGE", f"Original document language is {language}."
    return "Include", "", ""


def add_duplicate_decisions(rows: list[dict[str, str]]) -> None:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        doi = row.get("doi", "").strip().lower()
        if doi:
            groups[f"doi:{doi}"].append(index)
        else:
            title_key = normalize_title(row.get("title", ""))
            year = row.get("year", "").strip()
            if title_key and year:
                groups[f"title-year:{title_key}|{year}"].append(index)

    duplicate_number = 1
    for group_key, indexes in groups.items():
        if len(indexes) < 2:
            continue
        group_id = f"DUP{duplicate_number:03d}"
        duplicate_number += 1
        keep_index = indexes[0]
        for index in indexes:
            rows[index]["duplicate_group"] = group_id
            if index == keep_index:
                rows[index]["duplicate_decision"] = "Keep"
            else:
                rows[index]["duplicate_decision"] = "Duplicate"
                if rows[index]["level_0_decision"] == "Include":
                    rows[index]["level_0_decision"] = "Exclude"
                    rows[index]["level_0_exclusion_criterion"] = "L0-DUP"
                    rows[index]["level_0_notes"] = f"Duplicate of {rows[keep_index]['screening_id']} in {group_id}."


def title_language_flag(title: str) -> str:
    if any(ord(char) > 127 for char in title):
        return "Check non-ASCII title text"
    return ""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: level0_cleaning.py input.csv output.csv", file=sys.stderr)
        return 2
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        original_fields = list(reader.fieldnames or [])
        rows = list(reader)

    new_fields = [
        "level_0_decision",
        "level_0_exclusion_criterion",
        "level_0_notes",
        "level_0_language_flag",
    ]
    output_fields = []
    for field in original_fields:
        output_fields.append(field)
        if field == "duplicate_decision":
            output_fields.extend(new_fields)
    for field in new_fields:
        if field not in output_fields:
            output_fields.append(field)

    for row in rows:
        decision, criterion, notes = decision_for_row(row)
        row["level_0_decision"] = decision
        row["level_0_exclusion_criterion"] = criterion
        row["level_0_notes"] = notes
        row["level_0_language_flag"] = title_language_flag(row.get("title", ""))

    add_duplicate_decisions(rows)

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
