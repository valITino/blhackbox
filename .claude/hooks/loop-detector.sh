#!/bin/bash
# Loop Detection Hook for blhackbox
# Inspired by PentAGI's Reflector agent — detects repeated tool calls
# and injects warnings to prevent infinite loops.
#
# This hook runs on PreToolUse events. It tracks tool calls in a session
# log file and detects when the same tool+args combination is called
# repeatedly, which indicates the AI is stuck in a loop.

set -euo pipefail

# Session tracking directory
TRACK_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/loop-tracker"
mkdir -p "$TRACK_DIR"

# Session file — keyed by PID of the parent process (Claude Code session)
SESSION_FILE="$TRACK_DIR/session-$PPID.jsonl"

# Read the tool call from stdin (JSON with tool_name and tool_input)
INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json, hashlib
try:
    data = json.load(sys.stdin)
    name = data.get('tool_name', '')
    inp = json.dumps(data.get('tool_input', {}), sort_keys=True)
    args_hash = hashlib.md5(inp.encode()).hexdigest()[:12]
    print(f'{name}|{args_hash}')
except Exception:
    print('unknown|000000000000')
" 2>/dev/null) || exit 0

# Parse tool name and args hash
TOOL="${TOOL_NAME%%|*}"
HASH="${TOOL_NAME##*|}"

# Skip non-MCP tools (Bash, Read, Write, Edit, etc. are normal to repeat)
case "$TOOL" in
    Bash|Read|Write|Edit|Glob|Grep|Agent|WebSearch|WebFetch|TodoWrite)
        exit 0
        ;;
esac

# Log this call
echo "${TOOL}|${HASH}|$(date +%s)" >> "$SESSION_FILE"

# Count identical calls (same tool + same args hash)
REPEAT_COUNT=$(grep -c "^${TOOL}|${HASH}|" "$SESSION_FILE" 2>/dev/null || echo "0")

# Count total MCP tool calls in this session
TOTAL_CALLS=$(wc -l < "$SESSION_FILE" 2>/dev/null || echo "0")

# Detect repeated identical calls (threshold: 3)
if [ "$REPEAT_COUNT" -ge 4 ]; then
    # Output a warning message that Claude Code will see
    cat << EOF
{"decision": "block", "reason": "LOOP DETECTED: You have called '${TOOL}' with identical arguments ${REPEAT_COUNT} times. This indicates you are stuck in a loop. Stop and reassess your approach:\n\n1. Why did the previous calls fail or produce insufficient results?\n2. Is there an alternative tool or different arguments you should try?\n3. Should you move on to the next phase of your engagement?\n\nDo NOT retry the same call. Try a different approach or skip this step."}
EOF
    exit 0
fi

# Warn at 3 identical calls (approaching threshold)
if [ "$REPEAT_COUNT" -eq 3 ]; then
    cat << EOF
{"decision": "allow", "message": "WARNING: You have called '${TOOL}' with the same arguments 3 times. If this call doesn't produce the result you need, change your approach on the next attempt. Do not repeat the same call more than once more."}
EOF
    exit 0
fi

# Warn when total calls are high (approaching session limits)
if [ "$TOTAL_CALLS" -eq 50 ]; then
    cat << EOF
{"decision": "allow", "message": "SESSION CHECKPOINT: You have made 50 MCP tool calls in this session. Consider whether you have enough findings to begin aggregation. If you are still in early phases, continue — but start planning your wrap-up."}
EOF
    exit 0
fi

if [ "$TOTAL_CALLS" -eq 80 ]; then
    cat << EOF
{"decision": "allow", "message": "SESSION WARNING: 80 MCP tool calls used. Begin wrapping up findings. Call get_payload_schema() and aggregate_results() soon to ensure your work is captured before the session ends."}
EOF
    exit 0
fi

# Default: allow the call silently
exit 0
