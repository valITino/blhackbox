# MCP Server — Development Rules

- All MCP tool inputs **must** be validated with Pydantic models
- Never break the `aggregate_results` or `get_template` tool contracts — these are the primary interface for MCP clients
- The MCP server runs in **stdio** transport mode for Claude Code Web and as a CLI command (`blhackbox mcp`)
- All tool functions must be type-annotated and include docstrings
- Error responses must be structured and informative — never return raw tracebacks to MCP clients
