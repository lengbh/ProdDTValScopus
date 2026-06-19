#!/usr/bin/env python3
"""Apply conservative Level 2 abstract screening."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path


DT_TERMS = [
    "digital twin",
    "digital twins",
    "digital-twin",
    "digital twinning",
    "digital shadow",
    "cognitive digital twin",
    "virtual commissioning",
]

MODEL_CONTEXT_TERMS = [
    "simulation model",
    "simulated model",
    "digital model",
    "virtual model",
    "cyber-physical",
    "cyber physical",
    "model-based",
    "model based",
    "real-time simulation",
    "online simulation",
    "discrete-event simulation",
    "discrete event simulation",
]

VALIDATION_TERMS = [
    "validat",
    "verificat",
    "calibrat",
    "model update",
    "model updating",
    "updated model",
    "updating the model",
    "parameter update",
    "parameter updating",
    "model evolution",
    "evolv",
    "synchroni",
    "fidelity",
    "credibility",
    "conformance",
    "accuracy",
    "accurate representation",
    "model mismatch",
    "mismatch",
    "deviation",
    "residual",
    "error",
    "rmse",
    "root mean square",
    "compare",
    "comparison",
    "measured",
    "measurement",
    "experimental",
    "experiment",
    "real data",
    "operational data",
    "sensor data",
    "state reconstruction",
    "parameter estimation",
    "identification of parameters",
    "identify its parameters",
    "data assimilation",
    "hardware-in-the-loop",
    "hardware in the loop",
]

STRONG_MODEL_VALIDATION_TERMS = [
    "model validation",
    "validated against",
    "validated with",
    "validated using",
    "experimental validation",
    "calibration",
    "calibrate",
    "calibrated",
    "model updating",
    "parameter updating",
    "synchronization",
    "synchronisation",
    "model fidelity",
    "state reconstruction",
    "data assimilation",
]

PRODUCTION_TERMS = [
    "production",
    "manufactur",
    "shop floor",
    "factory",
    "factories",
    "assembly line",
    "production line",
    "smart manufacturing",
    "industrial manufacturing",
    "industrial production",
    "automated production",
    "material flow",
    "workshop",
    "machining",
    "machine tool",
    "industrial robot",
    "robotic manufacturing",
    "collaborative manufacturing",
    "additive manufacturing",
    "laser powder bed",
    "process manufacturing",
    "pharmaceutical manufacturing",
    "semiconductor",
    "virtual commissioning",
    "production system",
    "manufacturing system",
    "production systems",
    "manufacturing systems",
]

PRODUCTION_ADJACENT_TERMS = [
    "industrial",
    "industry 4.0",
    "industry 5.0",
    "industrial iot",
    "iiot",
    "industrial cyber-physical",
    "industrial equipment",
    "industrial process",
    "industrial plant",
    "industrial automation",
    "predictive maintenance",
    "condition monitoring",
    "quality control",
    "supply chain",
    "logistics",
    "robot",
    "robotics",
]

NON_PRODUCTION_DOMAIN_TERMS = [
    "bridge",
    "building",
    "concrete",
    "construction",
    "civil infrastructure",
    "smart city",
    "urban",
    "traffic",
    "road",
    "vehicle",
    "autonomous driving",
    "marine",
    "ship",
    "ocean",
    "battery",
    "power grid",
    "distribution network",
    "energy system",
    "wind turbine",
    "water distribution",
    "agriculture",
    "crop",
    "medical",
    "clinical",
    "patient",
    "cancer",
    "therapy",
    "health",
    "space",
    "aerospace",
    "aircraft",
    "rail",
    "railway",
    "carbon capture",
    "oil and gas",
    "marine propulsion",
]

MONITOR_ONLY_TERMS = [
    "monitoring",
    "visualization",
    "visualisation",
    "dashboard",
    "predictive maintenance",
    "fault diagnosis",
    "fault detection",
    "decision support",
]

OPT_ONLY_TERMS = [
    "optimization",
    "optimisation",
    "scheduling",
    "planning",
    "control",
    "path planning",
    "task planning",
    "motion coordination",
    "decision-making",
    "decision making",
]

GENERAL_TERMS = [
    "architecture",
    "framework",
    "platform",
    "conceptual",
    "review",
    "survey",
    "bibliometric",
    "taxonomy",
    "roadmap",
]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def screen_row(row: dict[str, str]) -> tuple[str, str, str]:
    title = row.get("title", "")
    abstract = row.get("abstract", "")
    keywords = " ".join([row.get("author_keywords", ""), row.get("index_keywords", "")])
    text = normalize(" ".join([title, abstract, keywords]))

    has_dt = has_any(text, DT_TERMS)
    has_model_context = has_dt or has_any(text, MODEL_CONTEXT_TERMS)
    has_validation = has_any(text, VALIDATION_TERMS)
    has_strong_validation = has_any(text, STRONG_MODEL_VALIDATION_TERMS)
    has_production = has_any(text, PRODUCTION_TERMS)
    has_adjacent = has_any(text, PRODUCTION_ADJACENT_TERMS)
    has_nonprod = has_any(text, NON_PRODUCTION_DOMAIN_TERMS)
    has_monitor_only = has_any(text, MONITOR_ONLY_TERMS)
    has_opt_only = has_any(text, OPT_ONLY_TERMS)
    has_general = has_any(text, GENERAL_TERMS)

    if not abstract.strip():
        return "Uncertain", "", "No abstract text is available; kept for full-text screening."

    if not has_model_context:
        return "Exclude", "L2-E-NODT", "Abstract lacks a digital-twin-like model, simulation model, or real-system-linked model context."

    if has_dt and has_production and has_strong_validation:
        return "Include", "", "Abstract contains DT/model, production/manufacturing, and explicit validation/calibration/update/synchronization evidence."

    if has_dt and has_production:
        return "Uncertain", "", "Abstract contains DT and production/manufacturing context, but validation/update evidence is not explicit enough."

    if has_production and has_model_context and has_strong_validation:
        return "Uncertain", "", "Abstract contains production, model/simulation, and explicit validation/update signals, but DT relevance needs full-text confirmation."

    if has_dt and has_adjacent and has_strong_validation:
        return "Uncertain", "", "Abstract is industrial or production-adjacent with DT and validation/update signals; kept for transfer assessment."

    if has_dt and has_strong_validation:
        return "Uncertain", "", "Abstract has a strong DT validation/update signal outside the core production scope; kept as potentially transferable."

    if has_dt and has_nonprod and not has_strong_validation:
        return "Exclude", "L2-E-NOPROD", "Abstract is outside production/manufacturing and lacks a strong transferable validation/update method."

    if has_dt and not has_validation:
        if has_monitor_only:
            return "Exclude", "L2-E-MONITORONLY", "DT is used mainly for monitoring/visualization/prediction without model validation or updating."
        if has_opt_only:
            return "Exclude", "L2-E-OPTONLY", "DT is used mainly for optimization/planning/control without model validation or updating."
        if has_general:
            return "Exclude", "L2-E-TOOGENERAL", "Abstract is a general DT architecture/framework/review without concrete validation/update insight."
        return "Exclude", "L2-E-NOVAL", "Abstract does not address validation, calibration, updating, synchronization, fidelity, or mismatch handling."

    if has_validation and not has_dt and has_nonprod and not has_production:
        return "Exclude", "L2-E-NOPROD", "Abstract has validation/update language but is outside production/manufacturing and lacks DT transfer relevance."

    if has_validation and has_model_context:
        return "Uncertain", "", "Abstract has model and validation/update signals, but production-system DT relevance needs full-text confirmation."

    if not has_validation:
        return "Exclude", "L2-E-NOVAL", "Abstract does not address validation, calibration, updating, synchronization, fidelity, or mismatch handling."

    return "Uncertain", "", "Abstract-level relevance is ambiguous; kept for full-text screening."


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    if len(sys.argv) == 1:
        input_path = script_dir.parent / "level1_title_screening" / "screening_after_level1_include_uncertain.csv"
        full_output_path = script_dir / "screening_level2.csv"
        pass_output_path = script_dir / "screening_after_level2_include_uncertain.csv"
        excluded_output_path = script_dir / "screening_level2_excluded_records.csv"
    elif len(sys.argv) == 5:
        input_path = Path(sys.argv[1])
        full_output_path = Path(sys.argv[2])
        pass_output_path = Path(sys.argv[3])
        excluded_output_path = Path(sys.argv[4])
    else:
        print(
            "Usage: level2_abstract_screening.py input.csv full_output.csv pass_output.csv excluded_output.csv",
            file=sys.stderr,
        )
        return 2

    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    for row in rows:
        decision, criterion, notes = screen_row(row)
        row["level_2_abstract_decision"] = decision
        row["level_2_exclusion_criterion"] = criterion
        row["level_2_notes"] = notes

    passed_rows = [row for row in rows if row["level_2_abstract_decision"] in {"Include", "Uncertain"}]
    excluded_rows = [row for row in rows if row["level_2_abstract_decision"] == "Exclude"]

    write_rows(full_output_path, rows, fields)
    write_rows(pass_output_path, passed_rows, fields)
    write_rows(excluded_output_path, excluded_rows, fields)

    decision_counts = Counter(row["level_2_abstract_decision"] for row in rows)
    criterion_counts = Counter(row["level_2_exclusion_criterion"] for row in excluded_rows)
    print(f"Wrote {len(rows)} rows to {full_output_path}")
    print(f"Wrote {len(passed_rows)} Include/Uncertain rows to {pass_output_path}")
    print(f"Wrote {len(excluded_rows)} Exclude rows to {excluded_output_path}")
    print(f"Decision counts: {dict(decision_counts)}")
    print(f"Exclusion criteria counts: {dict(criterion_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
