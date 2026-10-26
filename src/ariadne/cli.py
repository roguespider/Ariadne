"""Command-line interface for an interactive Ariadne agent session."""

import argparse
import os
from pathlib import Path

from .core import Assistant
from .memory import MemoryStore
from .openai_compatible import OpenAICompatibleModel
from .tasks import TaskManager
from .tools import build_tool_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with Ariadne.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("ARIADNE_BASE_URL", "http://localhost:1234/v1"),
        help="OpenAI-compatible API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("ARIADNE_MODEL", "local-model"),
        help="Model identifier sent to the API (default: %(default)s)",
    )
    parser.add_argument(
        "--memory-db",
        default=os.getenv("ARIADNE_MEMORY_DB"),
        help="Optional SQLite path for explicit /remember notes (or ARIADNE_MEMORY_DB)",
    )
    parser.add_argument(
        "--workspace",
        help="Optional directory Ariadne may list and read files from",
    )
    parser.add_argument(
        "--allow-workspace-writes",
        action="store_true",
        help="Also allow Ariadne to create and replace text files inside --workspace",
    )
    args = parser.parse_args()
    if args.allow_workspace_writes and not args.workspace:
        parser.error("--allow-workspace-writes requires --workspace")
    if args.workspace:
        workspace_path = Path(args.workspace).expanduser()
        if not workspace_path.is_dir():
            parser.error("--workspace must be an existing directory")
        args.workspace = str(workspace_path.resolve())

    model = OpenAICompatibleModel(
        base_url=args.base_url,
        model=args.model,
        api_key=os.getenv("ARIADNE_API_KEY"),
    )
    memory = MemoryStore(args.memory_db) if args.memory_db else None
    task_manager = TaskManager()

    def confirm_workspace_write(relative_path: str, replacing: bool) -> bool:
        action = "replace" if replacing else "create"
        answer = input(f"Ariadne wants to {action} {relative_path}. Allow? [y/N] ")
        return answer.strip().casefold() == "y"

    tool_registry = build_tool_registry(
        memory,
        task_manager,
        args.workspace,
        args.allow_workspace_writes,
        confirm_workspace_write if args.allow_workspace_writes else None,
    )
    agent = Assistant(model, tool_registry, task_manager=task_manager)
    print("Ariadne is ready. Type /help for commands.")
    print(f"Endpoint: {args.base_url}  Model: {args.model}")
    print(f"Persistent memory: {'enabled at ' + args.memory_db if memory else 'off'}")
    print(f"Workspace access: {args.workspace or 'off'}")
    if args.workspace:
        print(f"Workspace writes: {'enabled' if args.allow_workspace_writes else 'off'}")
    print(f"Available tools: {', '.join(tool_registry.names)}")

    while True:
        try:
            message = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAriadne session ended.")
            return

        command = message.lower()
        if command in {"/quit", "/exit"}:
            print("Ariadne session ended.")
            return
        if command == "/help":
            print("Commands: /reset, /remember <note>, /recall <words>, /forget <id>, /restore <id>, /tasks, /audit, /quit")
            continue
        if command == "/reset":
            agent.reset()
            print("Ariadne> Session, task plans, and in-memory audit cleared.")
            continue
        if command == "/tasks":
            plans = task_manager.list_plans()
            if not plans:
                print("Ariadne> No task plans in this session.")
            for plan in plans:
                print(f"[{plan['id']}] {plan['title']} ({plan['status']})")
                for step in plan["steps"]:
                    print(f"  {step['number']}. [{step['status']}] {step['title']}")
                    if step["evidence"]:
                        print(f"     Evidence: {step['evidence']}")
            continue
        if command == "/audit":
            if not agent.audit:
                print("Ariadne> No tool calls in this session.")
            for entry in agent.audit:
                status = "ok" if entry.succeeded else "failed"
                print(f"{entry.time_utc} {entry.name}: {status}")
            continue
        if command.startswith("/remember "):
            if memory is None:
                print("Ariadne> Memory is off. Start with --memory-db <path> to enable it.")
                continue
            try:
                record = memory.save(message[len("/remember "):])
            except ValueError as exc:
                print(f"Ariadne> {exc}")
            else:
                print(f"Ariadne> Saved note {record.id} as user-provided memory.")
            continue
        if command.startswith("/recall "):
            if memory is None:
                print("Ariadne> Memory is off. Start with --memory-db <path> to enable it.")
                continue
            try:
                records = memory.search(message[len("/recall "):])
            except ValueError as exc:
                print(f"Ariadne> {exc}")
                continue
            if not records:
                print("Ariadne> No matching saved notes.")
            for record in records:
                print(f"[{record.id}] {record.content} (source: {record.source}; {record.evidence_status})")
            continue
        if command.startswith("/forget "):
            if memory is None:
                print("Ariadne> Memory is off. Start with --memory-db <path> to enable it.")
                continue
            record_id = message[len("/forget "):].strip()
            if memory.retire(record_id):
                print(f"Ariadne> Retired note {record_id}; use /restore {record_id} to undo.")
            else:
                print("Ariadne> No active note found with that ID.")
            continue
        if command.startswith("/restore "):
            if memory is None:
                print("Ariadne> Memory is off. Start with --memory-db <path> to enable it.")
                continue
            record_id = message[len("/restore "):].strip()
            if memory.restore(record_id):
                print(f"Ariadne> Restored note {record_id}.")
            else:
                print("Ariadne> No retired note found with that ID.")
            continue
        if message.startswith("/"):
            print("Ariadne> Unknown command. Type /help to see commands.")
            continue
        if not message:
            continue

        try:
            print(f"Ariadne> {agent.respond(message)}")
        except (RuntimeError, OSError, ValueError) as exc:
            print(f"Ariadne> I couldn't complete that request: {exc}")


if __name__ == "__main__":
    main()
