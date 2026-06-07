# BOAZ-MCP Gamma / BOAZ Gamma Integration Review

## Source inspected

- `https://github.com/valITino/BOAZ-MCP_gamma`
- `https://github.com/valITino/BOAZ_gamma`
- Key files reviewed: `BOAZ-MCP_gamma/boaz_mcp/server.py`, `BOAZ-MCP_gamma/README.md`, `BOAZ_gamma/Boaz.py`, `BOAZ_gamma/README.md`, encoder/compiler directories.

## Relevant architecture observed

BOAZ-MCP Gamma implements a full MCP wrapper around BOAZ. The wrapper includes useful engineering patterns:

- environment-based BOAZ path discovery (`BOAZ_PATH`)
- relative path validation to avoid traversal
- loader/encoding/compiler/shellcode-type validators
- file-size checks
- subprocess timeout handling
- listing/validation tools

It also exposes payload-generation functionality around BOAZ. BOAZ Gamma contains payload encoders, loader/compiler assets, and Windows-focused payload/evasion build logic.

## blhackbox integration decision

blhackbox now integrates BOAZ as a default MCP service under `boaz-mcp/` by cloning the upstream `BOAZ-MCP_gamma` server unchanged and exposing it through a small SSE entrypoint.

The upstream service exposes its original tools through blhackbox:

- `generate_payload`
- `list_loaders`
- `list_encoders`
- `analyze_binary`
- `validate_options`

blhackbox does not rewrite those tool definitions; it only provides the container and SSE transport adapter.

## BOAZ patterns adopted

- Keep the upstream BOAZ-MCP Gamma MCP namespace and tool definitions.
- Preserve BOAZ-MCP Gamma path confinement and option validation in the upstream server.
- Bundle BOAZ_gamma in the container image so the service works with normal setup.
- Keep workspace files under explicit lab directories.

## Implementation note

The integration preserves the upstream BOAZ-MCP Gamma server content and adds only Docker/SSE glue needed for blhackbox interoperability.
