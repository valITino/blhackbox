# Models — Development Rules

- `AggregatedPayload` is the **contract** between the MCP host and the reporting tools — do not modify its schema without updating all consumers (`mcp/server.py`, `reporting/`, tests)
- All model fields **must** be type-annotated
- All models **must** use Pydantic `BaseModel`
- PoC fields in `VulnerabilityEntry` (`evidence`, `poc_steps`, `poc_payload`) are **mandatory** by design — do not make them optional
- When adding new fields, always provide sensible defaults to maintain backwards compatibility with existing `AggregatedPayload` JSON files in `output/sessions/`
- The `Severity` enum order matters: CRITICAL > HIGH > MEDIUM > LOW > INFO
