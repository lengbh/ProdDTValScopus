#!/usr/bin/env python3
"""Local browser GUI for Level 5 full-text screening and object classification."""

from __future__ import annotations

import argparse
import csv
import json
import socketserver
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse


APP_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = APP_DIR.parent / "level4_full_text_availability" / "level4_full_text_availability_66_papers.csv"
DEFAULT_DECISIONS = APP_DIR / "level5_full_text_screening_decisions.json"
DEFAULT_OUTPUT = APP_DIR / "level5_full_text_screening_59_papers.csv"
DEFAULT_PRODUCTION_OUTPUT = APP_DIR / "level5_production_system_papers.csv"
DEFAULT_NON_PRODUCTION_OUTPUT = APP_DIR / "level5_other_general_papers.csv"
DEFAULT_EXCLUDED_OUTPUT = APP_DIR / "level5_excluded_after_full_text_screening.csv"

DECISIONS = {
    "PRODUCTION_SYSTEM": "Object is production system",
    "NON_PRODUCTION_USED": "Not production system but used in paper",
    "EXCLUDE": "Exclude",
}


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Level 5 Full-Text Screening Review</title>
  <style>
    :root {
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #5f6b7a;
      --line: #d9dee7;
      --blue: #2563eb;
      --green: #147d50;
      --orange: #b45309;
      --red: #b91c1c;
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
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 18px 20px 28px;
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
    button.production { background: #e8f7ef; color: var(--green); border-color: #b8e3ca; }
    button.inpaper { background: #fff7ed; color: var(--orange); border-color: #fed7aa; }
    button.exclude { background: #fef2f2; color: var(--red); border-color: #fecaca; }
    button.clear { background: #fff; color: var(--muted); }
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
    .meta div, .detail {
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
      grid-template-columns: 1fr 1fr 1fr 1fr;
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
      .toolbar, .meta, .details, .actions { grid-template-columns: 1fr; }
      .title { font-size: 21px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Level 5 Full-Text Screening</h1>
    <div class="status" id="status"></div>
  </header>
  <main>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Filter by title, abstract, author, source, DOI, or ID">
      <select id="filter">
        <option value="pending">Pending only</option>
        <option value="all">All records</option>
        <option value="production">Production system</option>
        <option value="inpaper">Not production but used</option>
        <option value="exclude">Exclude</option>
      </select>
      <button class="primary" id="saveExport">Save Export</button>
    </div>

    <section class="card">
      <div class="meta">
        <div><span class="label">Object ID</span><span class="value" id="screeningId"></span></div>
        <div><span class="label">Source</span><span class="value" id="classificationSource"></span></div>
        <div><span class="label">Previous ID</span><span class="value" id="sourceScreeningId"></span></div>
        <div><span class="label">Decision</span><span class="value" id="decision"></span></div>
      </div>

      <div class="title" id="title"></div>
      <span class="label">Abstract</span>
      <div class="abstract" id="abstract"></div>

      <div class="details">
        <div class="detail"><span class="label">Authors</span><span class="value" id="authors"></span></div>
        <div class="detail"><span class="label">Source</span><span class="value" id="source"></span></div>
        <div class="detail"><span class="label">Year / Type</span><span class="value" id="yearType"></span></div>
        <div class="detail"><span class="label">DOI / Scopus</span><span class="value" id="links"></span></div>
      </div>

      <label class="label" for="note">Classification note</label>
      <textarea id="note" rows="3" placeholder="Optional note"></textarea>

      <div class="actions">
        <button class="production" id="markProduction">P - Production system</button>
        <button class="inpaper" id="markInPaper">I - Used in paper</button>
        <button class="exclude" id="markExclude">O - Exclude</button>
        <button class="clear" id="clearDecision">Clear</button>
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
        Shortcuts: P = production system, I = not production system but used in paper, O = exclude, C = clear, Z = undo last choice, Left/Right = previous/next.
      </div>
    </section>
  </main>

  <script>
    let records = [];
    let visible = [];
    let index = 0;
    let dirtyNote = false;
    let lastChoice = null;

    const labels = {
      "PRODUCTION_SYSTEM": "Object is production system",
      "NON_PRODUCTION_USED": "Not production system but used in paper",
      "EXCLUDE": "Exclude"
    };
    const $ = (id) => document.getElementById(id);

    async function api(path, options = {}) {
      const res = await fetch(path, options);
      if (!res.ok) throw new Error(await res.text());
      return await res.json();
    }
    function text(value) { return value || ""; }
    function escapeHtml(value) {
      return text(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);
    }
    function highlightKeywords(value) {
      const escaped = escapeHtml(value);
      const pattern = /\b(production system\w*|manufactur\w*|factory|shop floor|production line|assembly line|digital twin\w*|validat\w*|calibrat\w*|updat\w*|align\w*|synchroni\w*)\b/gi;
      return escaped.replace(pattern, '<span class="keyword-hit">$1</span>');
    }
    function counts(rows) {
      const c = { total: rows.length, pending: 0, production: 0, inpaper: 0, exclude: 0 };
      for (const r of rows) {
        if (r.object_class_decision === "PRODUCTION_SYSTEM") c.production++;
        else if (r.object_class_decision === "NON_PRODUCTION_USED") c.inpaper++;
        else if (r.object_class_decision === "EXCLUDE") c.exclude++;
        else c.pending++;
      }
      return c;
    }
    function applyFilters() {
      const query = $("search").value.trim().toLowerCase();
      const filter = $("filter").value;
      visible = records.filter((r) => {
        if (filter === "pending" && r.object_class_decision) return false;
        if (filter === "production" && r.object_class_decision !== "PRODUCTION_SYSTEM") return false;
        if (filter === "inpaper" && r.object_class_decision !== "NON_PRODUCTION_USED") return false;
        if (filter === "exclude" && r.object_class_decision !== "EXCLUDE") return false;
        if (!query) return true;
        const haystack = [
          r.screening_id, r.source_screening_id, r.classification_source, r.title,
          r.abstract, r.authors, r.source_title, r.doi, r.document_type
        ].join(" ").toLowerCase();
        return haystack.includes(query);
      });
      if (index >= visible.length) index = Math.max(0, visible.length - 1);
      render();
    }
    function renderStatus() {
      const all = counts(records);
      $("status").innerHTML = `
        <span class="pill">Total: ${all.total}</span>
        <span class="pill">Pending: ${all.pending}</span>
        <span class="pill">Production: ${all.production}</span>
        <span class="pill">Used in paper: ${all.inpaper}</span>
        <span class="pill">Exclude: ${all.exclude}</span>
        <span class="pill">Showing: ${visible.length ? index + 1 : 0}/${visible.length}</span>
      `;
    }
    function render() {
      renderStatus();
      const r = visible[index];
      for (const id of ["markProduction", "markInPaper", "markExclude", "clearDecision", "prev", "next", "firstPending"]) {
        $(id).disabled = !r;
      }
      if (!r) {
        $("screeningId").textContent = "";
        $("classificationSource").textContent = "";
        $("sourceScreeningId").textContent = "";
        $("decision").textContent = "";
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
      $("classificationSource").textContent = text(r.classification_source);
      $("sourceScreeningId").textContent = text(r.source_screening_id);
      $("decision").textContent = labels[r.object_class_decision] || "Pending";
      $("title").innerHTML = highlightKeywords(r.title);
      $("abstract").innerHTML = highlightKeywords(r.abstract);
      $("authors").textContent = text(r.authors);
      $("source").textContent = text(r.source_title);
      $("yearType").textContent = `${text(r.year)} / ${text(r.document_type)}`;
      const parts = [];
      if (r.doi) parts.push(`<a href="https://doi.org/${encodeURIComponent(r.doi)}" target="_blank">${r.doi}</a>`);
      if (r.scopus_url) parts.push(`<a href="${r.scopus_url}" target="_blank">Scopus</a>`);
      $("links").innerHTML = parts.join(" | ");
      $("note").value = text(r.object_class_note);
      dirtyNote = false;
    }
    async function saveDecision(decision, rememberUndo = true) {
      const r = visible[index];
      if (!r) return;
      if (rememberUndo) {
        lastChoice = {
          screening_id: r.screening_id,
          decision: r.object_class_decision || "",
          note: r.object_class_note || ""
        };
      }
      const updated = await api("/api/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screening_id: r.screening_id, decision, note: $("note").value })
      });
      const master = records.find((x) => x.screening_id === r.screening_id);
      Object.assign(master, updated.record);
      applyFilters();
      if (visible.length && index < visible.length - 1) index++;
      render();
    }
    async function undoLastChoice() {
      if (!lastChoice) return;
      const undo = lastChoice;
      lastChoice = null;
      const updated = await api("/api/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screening_id: undo.screening_id, decision: undo.decision, note: undo.note })
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
      await saveDecision(r.object_class_decision || "", false);
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
    $("markProduction").addEventListener("click", () => saveDecision("PRODUCTION_SYSTEM"));
    $("markInPaper").addEventListener("click", () => saveDecision("NON_PRODUCTION_USED"));
    $("markExclude").addEventListener("click", () => saveDecision("EXCLUDE"));
    $("clearDecision").addEventListener("click", () => saveDecision(""));
    $("prev").addEventListener("click", async () => { await saveNoteOnly(); index = Math.max(0, index - 1); render(); });
    $("next").addEventListener("click", async () => { await saveNoteOnly(); index = Math.min(visible.length - 1, index + 1); render(); });
    $("firstPending").addEventListener("click", () => {
      const next = visible.findIndex((r) => !r.object_class_decision);
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
      if (event.key.toLowerCase() === "p") saveDecision("PRODUCTION_SYSTEM");
      if (event.key.toLowerCase() === "i") saveDecision("NON_PRODUCTION_USED");
      if (event.key.toLowerCase() === "o") saveDecision("EXCLUDE");
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


class ClassificationStore:
    def __init__(
        self,
        input_path: Path,
        decisions_path: Path,
        output_path: Path,
        production_output_path: Path,
        non_production_output_path: Path,
        excluded_output_path: Path,
    ) -> None:
        self.input_path = input_path
        self.decisions_path = decisions_path
        self.output_path = output_path
        self.production_output_path = production_output_path
        self.non_production_output_path = non_production_output_path
        self.excluded_output_path = excluded_output_path
        self.lock = threading.Lock()
        self.fields: list[str] = []
        self.rows: list[dict[str, str]] = []
        self.decisions: dict[str, dict[str, str]] = {}
        self.load()

    def load(self) -> None:
        with self.input_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            self.fields = list(reader.fieldnames or [])
            self.rows = list(reader)
        if self.decisions_path.exists():
            self.decisions = json.loads(self.decisions_path.read_text(encoding="utf-8"))
        else:
            self.decisions = {}
        self.apply_decisions()

    def apply_decisions(self) -> None:
        for row in self.rows:
            saved = self.decisions.get(row["screening_id"], {})
            decision = saved.get("object_class_decision", "")
            row["object_class_decision"] = decision
            row["object_class_label"] = DECISIONS.get(decision, "")
            row["object_class_note"] = saved.get("object_class_note", "")

    def review_fields(self) -> list[str]:
        fields = list(self.fields)
        for field in ["object_class_decision", "object_class_label", "object_class_note"]:
            if field not in fields:
                fields.append(field)
        return fields

    def save_files(self) -> None:
        self.decisions_path.write_text(
            json.dumps(self.decisions, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        fields = self.review_fields()
        with self.output_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.rows)
        output_sets = [
            (self.production_output_path, "PRODUCTION_SYSTEM"),
            (self.non_production_output_path, "NON_PRODUCTION_USED"),
            (self.excluded_output_path, "EXCLUDE"),
        ]
        for path, decision in output_sets:
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows([row for row in self.rows if row.get("object_class_decision") == decision])

    def update_decision(self, screening_id: str, decision: str, note: str) -> dict[str, str]:
        if decision not in {"", *DECISIONS.keys()}:
            raise ValueError("Unknown decision.")
        with self.lock:
            row = next((item for item in self.rows if item.get("screening_id") == screening_id), None)
            if row is None:
                raise KeyError(f"Unknown screening_id: {screening_id}")
            self.decisions[screening_id] = {
                "object_class_decision": decision,
                "object_class_note": note,
            }
            row["object_class_decision"] = decision
            row["object_class_label"] = DECISIONS.get(decision, "")
            row["object_class_note"] = note
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


def make_handler(store: ClassificationStore):
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
                self.send_header("Content-Disposition", f'attachment; filename="{output.name}"')
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
    parser = argparse.ArgumentParser(description="Run the Level 5 full-text screening and object classification GUI.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--production-output", type=Path, default=DEFAULT_PRODUCTION_OUTPUT)
    parser.add_argument("--non-production-output", type=Path, default=DEFAULT_NON_PRODUCTION_OUTPUT)
    parser.add_argument("--excluded-output", type=Path, default=DEFAULT_EXCLUDED_OUTPUT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8792)
    args = parser.parse_args()

    store = ClassificationStore(
        args.input,
        args.decisions,
        args.output,
        args.production_output,
        args.non_production_output,
        args.excluded_output,
    )
    store.export()
    handler = make_handler(store)
    with ReusableTCPServer((args.host, args.port), handler) as httpd:
        print(f"Level 5 full-text screening GUI: http://{args.host}:{args.port}")
        print(f"Loaded {len(store.rows)} records.")
        print(f"Saving decisions to {args.decisions}")
        print(f"Exporting reviewed CSV to {args.output}")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
