# Backends — Development Rules

- **`shell=False` in ALL subprocess calls** — no exceptions, ever
- Always use `subprocess.run(args_list, shell=False)` with an explicit list of arguments
- Never construct shell command strings — always pass arguments as a list
- All tool arguments must be validated against the allowlisted tool dispatch pattern in `local.py`
- Timeouts are mandatory on all subprocess calls — use the configured `KALI_MAX_TIMEOUT` or a sensible default
- New tools must be added to both `local.py` argument builders AND `data/tools_catalog.json`
