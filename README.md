# Ariadne

Ariadne is an AI agent project, started from a small, changeable foundation.
The full proposed design is in [Adaptive_Cognitive_Architecture_Ariadne.md](Adaptive_Cognitive_Architecture_Ariadne.md).

## Architecture direction

Start with a capable, replaceable local model as the language and reasoning engine. Ariadne's own software supplies the cognitive controller, task state, memory, tools, skills, and evaluation loop. Train or structurally grow a custom neural core only after those layers identify a measured capability bottleneck and a safe evaluation path.

The current controller supports bounded model/tool cycles and in-session task plans. It gives the model a small set of explicitly registered tools, validates tool arguments, executes only those tools, sends their results back to the model, and records an in-memory audit trail. The available tools are arithmetic, current UTC time, task-plan management, and (when memory is enabled) saved-note search. It does not expose shell or arbitrary code execution. File access is off by default; an explicitly configured workspace can enable bounded listing and reading, and writing requires an additional opt-in flag.

## Run

Requires Python 3.11 or newer and an OpenAI-compatible chat-completions endpoint. The default endpoint is `http://localhost:1234/v1`, suitable for a local server configured on that address.

From this folder, install the project in editable mode:

```powershell
python -m pip install -e .
```

Then start Ariadne:

```powershell
ariadne
```

Or run it without installing the command entry point:

```powershell
python -m ariadne
```

Configuration can be set in the current PowerShell session:

```powershell
$env:ARIADNE_BASE_URL = "http://localhost:1234/v1"
$env:ARIADNE_MODEL = "your-model-id"
$env:ARIADNE_API_KEY = "your-key-if-required"
```

The API key is optional and is sent only to the endpoint configured by `ARIADNE_BASE_URL`. Ariadne does not start a model server or download a model.

Commands: `/reset` clears the in-memory conversation, plans, and audit; `/tasks` lists plans; `/audit` shows tool calls from this session; `/quit` exits; `/help` lists commands.

## Optional local memory

Persistent memory is off by default. Enable it only by specifying a database path:

```powershell
ariadne --memory-db "$env:LOCALAPPDATA\Ariadne\memory.sqlite3"
```

You can also set `ARIADNE_MEMORY_DB` in the current shell. Only explicit `/remember <note>` commands save content. Saved notes are marked as user-provided, and `/recall <words>` searches them. Ariadne can also search saved notes when the model decides they may help. `/forget <id>` retires a note so it no longer appears in recall; `/restore <id>` makes it active again. `/reset` does not remove saved notes.

Memory is local to the selected SQLite file and is not encrypted. No saved note is sent to the model unless the model requests the registered search tool.

## Optional workspace tools

By default Ariadne cannot access project files. Give it read access to one directory with `--workspace`:

```powershell
ariadne --workspace "C:\Users\miche\Documents\Codex\Ariadne"
```

This enables `list_workspace_files` and `read_workspace_file`. To also allow creating and replacing UTF-8 text files within that directory, explicitly add `--allow-workspace-writes`:

```powershell
ariadne --workspace "C:\Users\miche\Documents\Codex\Ariadne" --allow-workspace-writes
```

Workspace tools reject absolute paths, parent-directory traversal, and access to `.git`; they skip symlinks when listing and reject paths that resolve outside the workspace. Reads and writes are limited to 200 KB. Ariadne cannot run commands or delete files. With writes enabled, Ariadne asks for your approval before each file creation or replacement. Only enable writes when you want the configured model to propose file edits in that workspace.

## Current implementation

- Cognitive controller with a bounded model/tool loop.
- In-session task plans with step status and required evidence notes for completion.
- OpenAI-compatible chat-completions adapter with function-call support.
- Explicitly registered calculator and UTC-time tools; optional saved-note search and scoped workspace file tools.
- In-memory conversation and audit history for one process.
- Optional local SQLite notes with explicit save, search, retirement, and restore.
- No background learning, parameter updates, model growth, or automatic promotion yet.

See [docs/STATUS.md](docs/STATUS.md) for the implementation boundary and next milestones.
