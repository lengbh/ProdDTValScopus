#!/usr/bin/env python3
"""Local browser GUI for manual Level 3 topic-scope screening.

The app reviews records marked Include or Uncertain at Level 2.
Manual choices are saved after every click.
"""

from __future__ import annotations

import argparse
import csv
import json
import socketserver
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse


APP_DIR = Path(__file__).resolve().parent
INTERMEDIATE_DIR = APP_DIR / "intermediate_results"
DEFAULT_INPUT = INTERMEDIATE_DIR / "screening_after_level2_include_uncertain.csv"
DEFAULT_DECISIONS = INTERMEDIATE_DIR / "manual_level3_screening_decisions.json"
DEFAULT_OUTPUT = INTERMEDIATE_DIR / "screening_level3_manual_review.csv"
DEFAULT_INCLUDED_OUTPUT = INTERMEDIATE_DIR / "screening_after_level3_included.csv"
DEFAULT_EXCLUDED_OUTPUT = INTERMEDIATE_DIR / "screening_level3_excluded_records.csv"
REVIEW_DECISIONS = {"Include", "Uncertain"}


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
	  <title>Level 3 Manual Topic Review</title>
  <style>
    :root {
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --blue: #2563eb;
      --green: #147d50;
      --red: #c2410c;
      --amber: #a16207;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: var(--bg);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 2;
    }
    h1 {
      font-size: 18px;
      line-height: 1.2;
      margin: 0;
      font-weight: 650;
    }
    .status {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      white-space: nowrap;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 18px 20px 28px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
    }
    input[type="search"], textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: #fff;
      color: var(--text);
    }
    button {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 12px;
      font: inherit;
      color: var(--text);
      background: #fff;
      cursor: pointer;
    }
    button:hover { border-color: #9aa6b8; }
    button.primary { background: var(--blue); color: white; border-color: var(--blue); }
    button.in { background: #e8f7ef; color: var(--green); border-color: #b8e3ca; }
    button.out { background: #fff1e8; color: var(--red); border-color: #ffd1b5; }
    button.skip { background: #fff9db; color: var(--amber); border-color: #f5dc83; }
    button:disabled { opacity: .45; cursor: default; }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .meta {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .meta div {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      min-height: 56px;
      background: #fbfcfe;
    }
    .label {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 3px;
    }
    .value {
      font-size: 14px;
      overflow-wrap: anywhere;
    }
    .title {
      font-size: 25px;
      line-height: 1.28;
      margin: 6px 0 16px;
      font-weight: 700;
      overflow-wrap: anywhere;
    }
	    .abstract {
	      border: 1px solid var(--line);
	      border-radius: 6px;
	      background: #fbfcfe;
	      padding: 12px;
	      margin: 0 0 14px;
	      font-size: 15px;
	      line-height: 1.48;
	      white-space: pre-wrap;
	    }
	    .keyword-hit {
	      background: #fff3a3;
	      border-radius: 3px;
	      padding: 0 2px;
	    }
	    .details {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 14px;
    }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
      margin-top: 12px;
    }
    .nav {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: space-between;
      margin-top: 14px;
    }
    .nav-left, .nav-right {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .notice {
      color: var(--muted);
      font-size: 13px;
      margin-top: 10px;
    }
    a { color: var(--blue); text-decoration: none; }
    a:hover { text-decoration: underline; }
    @media (max-width: 760px) {
      header { align-items: flex-start; flex-direction: column; }
      .toolbar { grid-template-columns: 1fr; }
      .meta, .details, .actions { grid-template-columns: 1fr; }
      .title { font-size: 21px; }
    }
  </style>
</head>
<body>
  <header>
	    <h1>Manual Level 3 Topic-Scope Screening</h1>
    <div class="status" id="status"></div>
  </header>
  <main>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Filter by title, abstract, author, source, DOI, or screening ID">
      <select id="filter">
        <option value="pending">Pending only</option>
        <option value="all">All reviewed set</option>
        <option value="in">Manual IN</option>
        <option value="out">Manual OUT</option>
	        <option value="undecided">No manual decision</option>
      </select>
      <button class="primary" id="saveExport">Save Export</button>
    </div>

    <section class="card" id="card">
      <div class="meta">
        <div><span class="label">Screening ID</span><span class="value" id="screeningId"></span></div>
	        <div><span class="label">Level 2 Decision</span><span class="value" id="l2Decision"></span></div>
	        <div><span class="label">Level 2 Notes</span><span class="value" id="l2Notes"></span></div>
        <div><span class="label">Manual Decision</span><span class="value" id="manualDecision"></span></div>
      </div>

      <div class="title" id="title"></div>
      <span class="label">Abstract</span>
      <div class="abstract" id="abstract"></div>

      <div class="details">
        <div><span class="label">Authors</span><span class="value" id="authors"></span></div>
        <div><span class="label">Source</span><span class="value" id="source"></span></div>
        <div><span class="label">Year / Type</span><span class="value" id="yearType"></span></div>
        <div><span class="label">DOI / Scopus</span><span class="value" id="links"></span></div>
      </div>

      <label class="label" for="note">Manual note</label>
	      <textarea id="note" rows="3" placeholder="Optional note: why this is in/out of validation-on-digital-twin scope"></textarea>

      <div class="actions">
        <button class="in" id="markIn">IN</button>
        <button class="out" id="markOut">OUT</button>
        <button class="skip" id="clearDecision">Clear</button>
      </div>

      <div class="nav">
        <div class="nav-left">
          <button id="prev">Previous</button>
          <button id="next">Next</button>
        </div>
        <div class="nav-right">
          <button id="firstPending">First Pending</button>
          <button id="download">Download CSV</button>
        </div>
      </div>
      <div class="notice">
		        Shortcuts: I = IN, O = OUT, C = clear, Z = undo last choice, Left/Right = previous/next.
	        Choices are saved immediately to JSON and CSV.
      </div>
    </section>
  </main>

  <script>
	    let records = [];
	    let visible = [];
	    let index = 0;
	    let dirtyNote = false;
	    let lastChoice = null;

    const $ = (id) => document.getElementById(id);

    async function api(path, options = {}) {
      const res = await fetch(path, options);
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    }

	    function text(value) {
	      return value || "";
	    }

	    function escapeHtml(value) {
	      return text(value).replace(/[&<>"']/g, (char) => ({
	        "&": "&amp;",
	        "<": "&lt;",
	        ">": "&gt;",
	        '"': "&quot;",
	        "'": "&#39;"
	      })[char]);
	    }

	    function highlightKeywords(value) {
	      const escaped = escapeHtml(value);
	      const pattern = /\b(validat\w*|calibrat\w*|updat\w*|evolution|align\w*|synchroni\w*|conformance check\w*)\b/gi;
	      return escaped.replace(pattern, '<span class="keyword-hit">$1</span>');
	    }

    function decisionCounts(rows) {
      const counts = { total: rows.length, pending: 0, in: 0, out: 0 };
      for (const r of rows) {
	        if (r.manual_level3_decision === "IN") counts.in++;
	        else if (r.manual_level3_decision === "OUT") counts.out++;
        else counts.pending++;
      }
      return counts;
    }

    function applyFilters() {
      const query = $("search").value.trim().toLowerCase();
      const filter = $("filter").value;
      visible = records.filter((r) => {
	        if (filter === "pending" && r.manual_level3_decision) return false;
	        if (filter === "in" && r.manual_level3_decision !== "IN") return false;
	        if (filter === "out" && r.manual_level3_decision !== "OUT") return false;
	        if (filter === "undecided" && r.manual_level3_decision) return false;
        if (!query) return true;
        const haystack = [
          r.screening_id, r.title, r.abstract, r.author_keywords, r.index_keywords,
          r.authors, r.source_title, r.doi, r.level_2_abstract_decision,
          r.level_2_exclusion_criterion
        ].join(" ").toLowerCase();
        return haystack.includes(query);
      });
      if (index >= visible.length) index = Math.max(0, visible.length - 1);
      render();
    }

    function renderStatus() {
      const all = decisionCounts(records);
      const shown = decisionCounts(visible);
      $("status").innerHTML = `
        <span class="pill">Review set: ${all.total}</span>
        <span class="pill">Pending: ${all.pending}</span>
        <span class="pill">IN: ${all.in}</span>
        <span class="pill">OUT: ${all.out}</span>
        <span class="pill">Showing: ${visible.length ? index + 1 : 0}/${visible.length}</span>
      `;
    }

    function render() {
      renderStatus();
      const r = visible[index];
      const disabled = !r;
      for (const id of ["markIn", "markOut", "clearDecision", "prev", "next", "firstPending"]) {
        $(id).disabled = disabled;
      }
      if (!r) {
        $("screeningId").textContent = "";
	        $("l2Decision").textContent = "";
	        $("l2Notes").textContent = "";
        $("manualDecision").textContent = "";
        $("title").textContent = "No records match the current filter.";
        $("abstract").textContent = "";
        $("authors").textContent = "";
        $("source").textContent = "";
        $("yearType").textContent = "";
        $("links").innerHTML = "";
        $("note").value = "";
        return;
      }
      $("screeningId").textContent = text(r.screening_id);
	      $("l2Decision").textContent = text(r.level_2_abstract_decision);
	      $("l2Notes").textContent = text(r.level_2_notes);
	      $("manualDecision").textContent = text(r.manual_level3_decision || "Pending");
	      $("title").innerHTML = highlightKeywords(r.title);
	      $("abstract").innerHTML = highlightKeywords(r.abstract);
      $("authors").textContent = text(r.authors);
      $("source").textContent = text(r.source_title);
      $("yearType").textContent = `${text(r.year)} / ${text(r.document_type)}`;
      const parts = [];
      if (r.doi) parts.push(`<a href="https://doi.org/${encodeURIComponent(r.doi)}" target="_blank">${r.doi}</a>`);
      if (r.scopus_url) parts.push(`<a href="${r.scopus_url}" target="_blank">Scopus</a>`);
      $("links").innerHTML = parts.join(" | ");
	      $("note").value = text(r.manual_level3_note);
      dirtyNote = false;
    }

	    async function saveDecision(decision, rememberUndo = true) {
	      const r = visible[index];
	      if (!r) return;
	      if (rememberUndo) {
	        lastChoice = {
	          screening_id: r.screening_id,
	          decision: r.manual_level3_decision || "",
	          note: r.manual_level3_note || ""
	        };
	      }
	      const payload = {
	        screening_id: r.screening_id,
	        decision,
        note: $("note").value
      };
      const updated = await api("/api/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const master = records.find((x) => x.screening_id === r.screening_id);
      Object.assign(master, updated.record);
      applyFilters();
      if (visible.length && index < visible.length - 1) {
        index++;
      }
	      render();
	    }

	    async function undoLastChoice() {
	      if (!lastChoice) return;
	      const undo = lastChoice;
	      lastChoice = null;
	      const updated = await api("/api/decision", {
	        method: "POST",
	        headers: { "Content-Type": "application/json" },
	        body: JSON.stringify({
	          screening_id: undo.screening_id,
	          decision: undo.decision,
	          note: undo.note
	        })
	      });
	      const master = records.find((x) => x.screening_id === undo.screening_id);
	      if (master) Object.assign(master, updated.record);
	      applyFilters();
	      const restoredIndex = visible.findIndex((r) => r.screening_id === undo.screening_id);
	      if (restoredIndex >= 0) index = restoredIndex;
	      render();
	    }

    async function saveNoteOnly() {
      if (!dirtyNote) return;
      const r = visible[index];
      if (!r) return;
		      await saveDecision(r.manual_level3_decision || "", false);
      dirtyNote = false;
    }

    async function load() {
      const data = await api("/api/records");
      records = data.records;
      applyFilters();
    }

    $("search").addEventListener("input", () => { index = 0; applyFilters(); });
    $("filter").addEventListener("change", () => { index = 0; applyFilters(); });
    $("note").addEventListener("input", () => { dirtyNote = true; });
    $("markIn").addEventListener("click", () => saveDecision("IN"));
    $("markOut").addEventListener("click", () => saveDecision("OUT"));
    $("clearDecision").addEventListener("click", () => saveDecision(""));
    $("prev").addEventListener("click", async () => { await saveNoteOnly(); index = Math.max(0, index - 1); render(); });
    $("next").addEventListener("click", async () => { await saveNoteOnly(); index = Math.min(visible.length - 1, index + 1); render(); });
    $("firstPending").addEventListener("click", () => {
	      const next = visible.findIndex((r) => !r.manual_level3_decision);
      if (next >= 0) index = next;
      render();
    });
    $("saveExport").addEventListener("click", async () => {
      await saveNoteOnly();
      const res = await api("/api/export", { method: "POST" });
      alert(`Saved ${res.output}`);
    });
    $("download").addEventListener("click", async () => {
      await saveNoteOnly();
      window.location = "/download";
    });
    document.addEventListener("keydown", (event) => {
      if (event.target.tagName === "TEXTAREA" || event.target.tagName === "INPUT") return;
	      if (event.key.toLowerCase() === "i") saveDecision("IN");
	      if (event.key.toLowerCase() === "o") saveDecision("OUT");
	      if (event.key.toLowerCase() === "c") saveDecision("");
	      if (event.key.toLowerCase() === "z") undoLastChoice();
	      if (event.key === "ArrowLeft") $("prev").click();
      if (event.key === "ArrowRight") $("next").click();
    });

    load().catch((err) => {
      $("title").textContent = "Failed to load records.";
      $("authors").textContent = err.message;
    });
  </script>
</body>
</html>
"""


class ScreeningStore:
    def __init__(
        self,
        input_path: Path,
        decisions_path: Path,
        output_path: Path,
        included_output_path: Path,
        excluded_output_path: Path,
    ) -> None:
        self.input_path = input_path
        self.decisions_path = decisions_path
        self.output_path = output_path
        self.included_output_path = included_output_path
        self.excluded_output_path = excluded_output_path
        self.lock = threading.Lock()
        self.fields: list[str] = []
        self.all_rows: list[dict[str, str]] = []
        self.rows: list[dict[str, str]] = []
        self.decisions: dict[str, dict[str, str]] = {}
        self.load()

    def load(self) -> None:
        with self.input_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            self.fields = list(reader.fieldnames or [])
            self.all_rows = [
                row for row in reader
                if row.get("level_2_abstract_decision") in REVIEW_DECISIONS
            ]
            self.rows = list(self.all_rows)
        if self.decisions_path.exists():
            self.decisions = json.loads(self.decisions_path.read_text(encoding="utf-8"))
        else:
            self.decisions = {}
        self.apply_decisions()

    def apply_decisions(self) -> None:
        for row in self.all_rows:
            saved = self.decisions.get(row["screening_id"], {})
            row["manual_level3_decision"] = saved.get("manual_level3_decision", "")
            row["manual_level3_note"] = saved.get("manual_level3_note", "")
            self.apply_level3_fields(row)

    def apply_level3_fields(self, row: dict[str, str]) -> None:
        decision = row.get("manual_level3_decision", "")
        note = row.get("manual_level3_note", "")
        if decision == "IN":
            row["level_3_fulltext_decision"] = "Include"
            row["level_3_exclusion_criterion"] = ""
            row["level_3_notes"] = note or "Manual Level 3 topic-scope review: in scope."
            row["final_decision"] = ""
            row["included_reason"] = ""
        elif decision == "OUT":
            row["level_3_fulltext_decision"] = "Exclude"
            row["level_3_exclusion_criterion"] = "L3-E-MANUALSCOPE"
            row["level_3_notes"] = note or "Manual Level 3 topic-scope review: out of scope."
            row["final_decision"] = "Exclude"
            row["included_reason"] = ""
        else:
            row["level_3_fulltext_decision"] = ""
            row["level_3_exclusion_criterion"] = ""
            row["level_3_notes"] = ""
            row["final_decision"] = ""
            row["included_reason"] = ""

    def review_fields(self) -> list[str]:
        fields = list(self.fields)
        for field in ["manual_level3_decision", "manual_level3_note"]:
            if field not in fields:
                fields.append(field)
        return fields

    def save_files(self) -> None:
        self.decisions_path.write_text(
            json.dumps(self.decisions, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        with self.output_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.review_fields(), extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.all_rows)
        included_rows = [row for row in self.all_rows if row.get("manual_level3_decision") == "IN"]
        excluded_rows = [row for row in self.all_rows if row.get("manual_level3_decision") == "OUT"]
        for path, rows in [
            (self.included_output_path, included_rows),
            (self.excluded_output_path, excluded_rows),
        ]:
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.review_fields(), extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)

    def update_decision(self, screening_id: str, decision: str, note: str) -> dict[str, str]:
        if decision not in {"", "IN", "OUT"}:
            raise ValueError("Decision must be IN, OUT, or empty.")
        with self.lock:
            row = next((item for item in self.all_rows if item.get("screening_id") == screening_id), None)
            if row is None:
                raise KeyError(f"Unknown screening_id: {screening_id}")
            self.decisions[screening_id] = {
                "manual_level3_decision": decision,
                "manual_level3_note": note,
            }
            row["manual_level3_decision"] = decision
            row["manual_level3_note"] = note
            self.apply_level3_fields(row)
            self.save_files()
            return row

    def export(self) -> Path:
        with self.lock:
            self.save_files()
        return self.output_path


def json_response(handler: BaseHTTPRequestHandler, payload: object, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(handler: BaseHTTPRequestHandler, body: str, status: int = 200) -> None:
    data = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def make_handler(store: ScreeningStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                data = HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if parsed.path == "/api/records":
                json_response(self, {"records": store.rows})
                return
            if parsed.path == "/download":
                output = store.export()
                data = output.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{output.name}"',
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            text_response(self, "Not found", HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/decision":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                try:
                    row = store.update_decision(
                        str(payload.get("screening_id", "")),
                        str(payload.get("decision", "")),
                        str(payload.get("note", "")),
                    )
                except (KeyError, ValueError) as exc:
                    json_response(self, {"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                json_response(self, {"record": row})
                return
            if parsed.path == "/api/export":
                output = store.export()
                json_response(self, {"output": str(output)})
                return
            text_response(self, "Not found", HTTPStatus.NOT_FOUND)

    return Handler


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the manual Level 3 topic-scope screening GUI.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--included-output", type=Path, default=DEFAULT_INCLUDED_OUTPUT)
    parser.add_argument("--excluded-output", type=Path, default=DEFAULT_EXCLUDED_OUTPUT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()

    store = ScreeningStore(
        args.input,
        args.decisions,
        args.output,
        args.included_output,
        args.excluded_output,
    )
    store.export()
    handler = make_handler(store)
    with ReusableTCPServer((args.host, args.port), handler) as httpd:
        print(f"Manual Level 3 topic-scope screening GUI: http://{args.host}:{args.port}")
        print(f"Loaded {len(store.rows)} records marked Include/Uncertain at Level 2.")
        print(f"Saving decisions to {args.decisions}")
        print(f"Exporting reviewed CSV to {args.output}")
        print(f"Exporting IN records to {args.included_output}")
        print(f"Exporting OUT records to {args.excluded_output}")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
