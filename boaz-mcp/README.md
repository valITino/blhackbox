# BOAZ MCP

The default Docker stack runs the upstream `BOAZ-MCP_gamma` server on SSE port `9005`. The upstream server is cloned into the image unchanged and is loaded by `boaz-mcp/server.py`, which only adapts the upstream stdio MCP server to the same SSE transport style used by the other blhackbox MCP containers.

The image also clones `BOAZ_gamma` into `/opt/BOAZ_gamma` and sets `BOAZ_PATH=/opt/BOAZ_gamma`. The service mounts `./output/boaz-lab` as an operator workspace.

Upstream BOAZ-MCP Gamma tools exposed through this container:

- `generate_payload`
- `list_loaders`
- `list_encoders`
- `analyze_binary`
- `validate_options`

Run manually for local adapter checks:

```bash
python boaz-mcp/server.py
```

Default SSE port: `9005`.
