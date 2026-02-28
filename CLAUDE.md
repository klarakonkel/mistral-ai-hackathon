# KotoFlow — Project Rules

## Architecture
- **Backend**: Python 3.12 + FastAPI + Pydantic v2 (async/await)
- **Frontend**: Next.js 15 + React 19 + @xyflow/react + Tailwind CSS v4
- **AI**: Mistral Large (orchestrator), Ministral 8B (fine-tuned workflow gen)
- **Voice**: Mistral STT (base64), ElevenLabs TTS (level-based voice)
- **Execution**: 3-tier fallback (Composio → API → Browser)
- **Gamification**: XP system, 5 skill branches, achievements, appearance evolution

## Git
- **Authors**: `klarakonkel` and `koki-technoam77` ONLY. Never commit as any other author
- **Commands**: Always use `git-safe` wrapper (handles DEVELOPER_DIR/GIT_SSH)
- **Pre-commit**: Run `pre-commit-check` before every commit

## Testing
- **Runner**: `test-run` from project root (auto-detects backend pytest)
- **Venv**: `backend/.venv/bin/python`
- **Coverage**: All models, services, executor, routes, and security tests
- **Actions**: WorkflowStep.action must be from `ALLOWED_ACTIONS` frozenset in `models/workflow.py`

## Security (Enforced)
These patterns were identified by dual-hacker audit and must be maintained:

1. **Auth**: All endpoints (except /health) require Bearer token via `KOTOFLOW_API_KEY`
2. **No raw exceptions**: Never `detail=str(e)` — always generic messages, log with `exc_info=True`
3. **SSRF protection**: HTTPS only, `parsed.hostname` (not netloc), no redirects, private IP block
4. **Input limits**: chat 4000 chars, TTS 500 chars, upload 10MB, step action allowlist
5. **Session isolation**: Per-session orchestrator keyed by session_id (never global singleton)
6. **Prompt injection**: Anti-override system prompt, input sanitization, max lengths
7. **WebSocket**: Auth via query param token, max 50 connections, message size caps
8. **CORS**: No wildcard `*` with credentials, methods restricted to GET/POST

## Common Mistakes to Avoid
- `datetime.utcnow()` → Use `datetime.now(tz=UTC)`
- `.dict()` → Use `.model_dump()` (Pydantic v2)
- `client.chat.complete()` → Use `await client.chat.complete_async()`
- `DEFAULT_LIST.copy()` → Use `[item.model_copy() for item in DEFAULT_LIST]` for Pydantic objects
- Sharing mutable state between users via module-level singletons
