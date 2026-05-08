# Codex AI Setup

This project is organized as a Python desktop/file-cleaner app. Future AI work should keep source code inside the approved application layout and avoid adding loose scripts or assets at the repository root.

## Required MCP Servers

Use these servers for local development sessions:

| Server | Command | Purpose |
| --- | --- | --- |
| Filesystem | `npx -y @modelcontextprotocol/server-filesystem "C:\Users\I'm not a hacker\OneDrive\Documents\New project\Computer Cleaner"` | Scoped file reads, writes, moves, and directory inspection |
| Git | `uvx mcp-server-git --repository "C:\Users\I'm not a hacker\OneDrive\Documents\New project\Computer Cleaner"` | Repository history, diffs, branches, and commits |
| SQLite | `uvx mcp-server-sqlite --db-path "C:\Users\I'm not a hacker\OneDrive\Documents\New project\Computer Cleaner\files.db"` | SQLite inspection and queries |
| Sequential Thinking | `npx -y @modelcontextprotocol/server-sequential-thinking` | Multi-step planning for complex architecture or debugging |
| GitHub | `npx -y @modelcontextprotocol/server-github` | GitHub PRs, issues, branches, and API operations |
| Fetch | `uvx mcp-server-fetch` | Fetch external docs and web pages |
| Brave Search | `npx -y @brave/brave-search-mcp-server --transport stdio` | Web and local search through Brave Search API |

GitHub MCP requires `GITHUB_PERSONAL_ACCESS_TOKEN`.
Brave Search MCP requires `BRAVE_API_KEY`.

## Smithery Skills

Install these with:

```powershell
npx @smithery/cli@latest skill add s-hiraoku/mcp-brave-search --agent codex
npx @smithery/cli@latest skill add growilabs/app-architecture
npx @smithery/cli@latest skill add jarredkenny/frontend-design
npx @smithery/cli@latest skill add openclaw/chatgpt-apps
npx @smithery/cli@latest skill add aiskillstore/frontend-agent --agent codex
```

Installed project skills are organized under `AI Resources/Skills/`.

## Project Structure Policy

Target layout:

```text
Computer Cleaner/
├── AI Resources/
│   ├── Skills/
│   └── Update Logs/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── config/
│   └── settings.py
├── src/
│   ├── ui/
│   ├── core/
│   ├── data/
│   └── utils/
├── assets/
│   ├── images/
│   ├── icons/
│   └── fonts/
├── tests/
└── docs/
```

Rules for future AI agents:

- Check the file tree before code changes.
- Keep `main.py` as an entry point only.
- Keep UI imports out of `src/core/` and `src/data/`.
- Use relative imports inside `src/`.
- Check `src/utils/` before creating new helpers.
- Keep each file under 200 lines.
- Put assets in `assets/images/`, `assets/icons/`, or `assets/fonts/`.
- Flag messy files before moving or deleting them.

## Current Cleanup Notes

The current repository has legacy folders and files that need a confirmed refactor before moving:

- `App.py`, `AppStreamlit.py`, `folder_preview_pipeline.py`, and `random_file_preview.py` are still root-level Python files.
- `backend/` is still a root-level source folder and needs a separate placement decision.
- Runtime/generated folders such as `venv/`, `venv.broken/`, `.uv-cache/`, `.python/`, `__pycache__/`, and `Microsoft/` should be reviewed before cleanup.
- Update logs are now under `AI Resources/Update Logs/`.
