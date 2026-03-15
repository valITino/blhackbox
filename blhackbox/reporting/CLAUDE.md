# Reporting — Development Rules

- Always use `reporting/paths.py` (`get_report_dir`, `get_report_path`) for all output paths — never hardcode report locations
- Reports are organized as: `output/reports/reports-DDMMYYYY/report-<target-slug>-DDMMYYYY.<ext>`
- The HTML generator includes inline CSS — do not add external stylesheet dependencies
- PDF generation depends on WeasyPrint — ensure any HTML changes remain WeasyPrint-compatible
- All report generators receive a `ScanSession` or `AggregatedPayload` — they must never call MCP tools or subprocess directly
