#!/usr/bin/env python3
"""Apply conservative Level 1 title screening.

Level 1 only screens title-level relevance after Level 0 bibliographic
cleaning. Ambiguous records are kept as Uncertain for Level 2.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path


DT_TERMS = [
    "digital twin",
    "digital twins",
    "digital shadow",
    "cyber physical",
    "cyber-physical",
    "virtual commissioning",
    "online simulation",
    "synchronized simulation",
    "synchronised simulation",
]

MODEL_TERMS = [
    "simulation",
    "model",
    "models",
    "modelling",
    "modeling",
    "discrete event",
    "discrete-event",
    "agent based",
    "agent-based",
    "petri net",
    "graph",
]

VALIDATION_TERMS = [
    "validat",
    "verificat",
    "calibrat",
    "updat",
    "evolution",
    "evolv",
    "synchron",
    "conformance",
    "credib",
    "fidelity",
    "accuracy",
    "error",
    "residual",
    "state reconstruction",
    "trace driven",
    "trace-driven",
    "online validation",
]

PRODUCTION_TERMS = [
    "production",
    "manufactur",
    "industrial",
    "industry",
    "plant",
    "process",
    "shop floor",
    "factory",
    "factories",
    "bakery",
    "fabrication",
    "assembly",
    "assembly line",
    "production line",
    "smart manufacturing",
    "industrial production",
    "automated production",
    "material flow",
    "workshop",
    "machining",
    "machine tool",
    "robot",
    "robotic",
    "additive manufacturing",
    "laser powder bed",
    "process manufacturing",
    "pharmaceutical manufacturing",
    "semiconductor",
]

NON_PRODUCTION_DOMAIN_TERMS = [
    "building",
    "bridge",
    "concrete",
    "construction",
    "civil",
    "structural",
    "city",
    "urban",
    "traffic",
    "road",
    "vehicle",
    "automotive",
    "marine",
    "ship",
    "ocean",
    "battery",
    "power grid",
    "distribution network",
    "energy",
    "wind turbine",
    "water",
    "agricultur",
    "medical",
    "clinical",
    "patient",
    "cancer",
    "health",
    "space",
    "aerospace",
    "aircraft",
    "rail",
    "railway",
    "carbon capture",
    "oil",
    "gas",
    "well",
]

GENERAL_AI_TERMS = [
    "algorithm",
    "deep learning",
    "machine learning",
    "reinforcement learning",
    "neural network",
    "object detection",
    "image",
    "vision",
    "task planning",
    "motion coordination",
    "prediction",
    "forecast",
    "optimization",
    "optimisation",
    "control",
]

SURVEY_TERMS = [
    "review",
    "survey",
    "bibliometric",
    "literature",
    "state of the art",
    "state-of-the-art",
]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def title_screen(title: str) -> tuple[str, str, str]:
    t = normalize(title)
    has_dt = has_any(t, DT_TERMS)
    has_model = has_any(t, MODEL_TERMS)
    has_validation = has_any(t, VALIDATION_TERMS)
    has_production = has_any(t, PRODUCTION_TERMS)
    has_nonprod_domain = has_any(t, NON_PRODUCTION_DOMAIN_TERMS)
    has_general_ai = has_any(t, GENERAL_AI_TERMS)
    has_survey = has_any(t, SURVEY_TERMS)

    if not title.strip():
        return "Exclude", "L1-E-NODT", "No title available for title-level screening."

    if has_dt and has_validation and has_production:
        return (
            "Include",
            "",
            "Title contains DT/model, validation/update, and production/manufacturing signals.",
        )

    if has_dt and has_validation:
        return (
            "Include",
            "",
            "Title contains DT/model and validation/update signals; kept as potentially transferable.",
        )

    if has_production and has_validation and has_model:
        return (
            "Uncertain",
            "",
            "Title contains production, validation/update, and model/simulation signals, but DT signal is not explicit in the title.",
        )

    if has_dt and has_production:
        return (
            "Uncertain",
            "",
            "Title contains DT and production/manufacturing signals, but validation/update is not explicit in the title.",
        )

    if has_validation and has_model and not has_nonprod_domain:
        return (
            "Uncertain",
            "",
            "Title contains validation/update and model/simulation signals, but production and DT relevance need abstract screening.",
        )

    if has_production and has_model and not has_general_ai:
        return (
            "Uncertain",
            "",
            "Title contains production and model/simulation signals, but DT validation relevance needs abstract screening.",
        )

    if has_survey and (has_dt or has_production) and has_validation:
        return (
            "Include",
            "",
            "Title suggests a review/survey with DT or production and validation/update focus.",
        )

    if has_survey and (has_dt or has_production):
        return (
            "Uncertain",
            "",
            "Title suggests a broad DT/production review, but validation/update relevance needs abstract screening.",
        )

    if has_nonprod_domain and not has_dt and not has_validation:
        return (
            "Exclude",
            "L1-E-NOPROD",
            "Title is clearly outside production/manufacturing and lacks transferable validation/update signal.",
        )

    if has_dt and has_nonprod_domain and not has_validation:
        return (
            "Exclude",
            "L1-E-NOPROD",
            "Title is DT-related but clearly outside production/manufacturing and lacks a validation/update signal.",
        )

    if has_production:
        return (
            "Uncertain",
            "",
            "Title contains a production/manufacturing/industrial signal, but DT validation relevance needs abstract screening.",
        )

    if not has_dt and not has_model:
        return (
            "Exclude",
            "L1-E-NODT",
            "Title lacks DT-like model or simulation/model signal.",
        )

    if not has_validation and not has_production:
        return (
            "Exclude",
            "L1-E-NOVAL",
            "Title lacks validation/update and production/manufacturing signals.",
        )

    if has_general_ai and not has_dt and not has_validation:
        return (
            "Exclude",
            "L1-E-GENERICAI",
            "Title appears to be a generic AI/control/optimization topic without DT validation signal.",
        )

    return (
        "Uncertain",
        "",
        "Title-level relevance is ambiguous; kept for abstract screening.",
    )


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    if len(sys.argv) == 1:
        input_path = script_dir.parent / "level0_import_cleaning" / "screening_after_level0_included.csv"
        full_output_path = script_dir / "screening_level1.csv"
        pass_output_path = script_dir / "screening_after_level1_include_uncertain.csv"
        excluded_output_path = script_dir / "screening_level1_excluded_records.csv"
    elif len(sys.argv) == 5:
        input_path = Path(sys.argv[1])
        full_output_path = Path(sys.argv[2])
        pass_output_path = Path(sys.argv[3])
        excluded_output_path = Path(sys.argv[4])
    else:
        print(
            "Usage: level1_title_screening.py input.csv full_output.csv pass_output.csv excluded_output.csv",
            file=sys.stderr,
        )
        return 2

    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    for row in rows:
        decision, criterion, notes = title_screen(row.get("title", ""))
        row["level_1_title_decision"] = decision
        row["level_1_exclusion_criterion"] = criterion
        row["level_1_notes"] = notes

    passed_rows = [row for row in rows if row["level_1_title_decision"] in {"Include", "Uncertain"}]
    excluded_rows = [row for row in rows if row["level_1_title_decision"] == "Exclude"]

    write_rows(full_output_path, rows, fields)
    write_rows(pass_output_path, passed_rows, fields)
    write_rows(excluded_output_path, excluded_rows, fields)

    decision_counts = Counter(row["level_1_title_decision"] for row in rows)
    criterion_counts = Counter(row["level_1_exclusion_criterion"] for row in excluded_rows)
    print(f"Wrote {len(rows)} rows to {full_output_path}")
    print(f"Wrote {len(passed_rows)} Include/Uncertain rows to {pass_output_path}")
    print(f"Wrote {len(excluded_rows)} Exclude rows to {excluded_output_path}")
    print(f"Decision counts: {dict(decision_counts)}")
    print(f"Exclusion criteria counts: {dict(criterion_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
