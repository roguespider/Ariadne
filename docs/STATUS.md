# Implementation status

The full adaptive architecture is a proposal, not an implemented system. This status file tracks what currently exists so planned capabilities are not mistaken for working ones.

## Working agent slice

- Cognitive controller with bounded model/tool cycles.
- In-memory conversation history, task plans, and session tool audit.
- Replaceable model protocol and OpenAI-compatible function-call adapter.
- Explicit task planning and step updates; completing a step requires an evidence note.
- Tool argument validation and limits on tool calls per round and model/tool rounds.
- Explicit system guidance for honesty, uncertainty, and treating tool results as data.
- Calculator and UTC-time tools; optional saved-note search.
- Optional local SQLite notes, disabled unless configured, with user-provided provenance and reversible retirement.

## Not implemented

- Persistent task plans or long-term skill execution.
- Hardware/resource monitoring.
- Experience consolidation, relationship indexes, or a persistent learning ledger.
- Adapter training, candidate evaluation, or architecture growth.
- Versioned model registry, promotion, or rollback.
- Independent neural model training.

## Suggested next sequence

1. Connect the local model server and confirm that the chosen model can call tools reliably.
2. Add a repeatable evaluation baseline for planning, tool use, memory retrieval, and failure handling.
3. Add hardware/resource reporting before background work is introduced.
4. Build provenance-aware learning records and tested reusable skills.
5. Consider adapter learning and model growth only after measured gaps justify them.
