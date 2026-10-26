"""In-process task plans for Ariadne's goal-directed controller."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(slots=True)
class TaskStep:
    number: int
    title: str
    status: str = "pending"
    evidence: str = ""


@dataclass(slots=True)
class TaskPlan:
    id: str
    title: str
    created_at: str
    steps: list[TaskStep] = field(default_factory=list)

    @property
    def status(self) -> str:
        if all(step.status == "completed" for step in self.steps):
            return "completed"
        if any(step.status == "blocked" for step in self.steps):
            return "blocked"
        if any(step.status in {"in_progress", "completed"} for step in self.steps):
            return "in_progress"
        return "pending"


class TaskManager:
    """Creates and updates bounded plans for the current Ariadne process."""

    _STEP_STATUSES = {"pending", "in_progress", "completed", "blocked"}

    def __init__(self) -> None:
        self._plans: dict[str, TaskPlan] = {}

    def create(self, title: str, steps: list[str]) -> dict:
        if not isinstance(title, str) or not isinstance(steps, list):
            raise ValueError("task title must be text and steps must be a list")
        if any(not isinstance(step, str) for step in steps):
            raise ValueError("every plan step must be text")
        task_title = title.strip()
        normalized = [step.strip() for step in steps if step.strip()]
        if not task_title:
            raise ValueError("task title must not be empty")
        if len(task_title) > 160:
            raise ValueError("task title must be 160 characters or fewer")
        if not normalized:
            raise ValueError("a plan must include at least one non-empty step")
        if len(normalized) > 12:
            raise ValueError("a plan may contain at most 12 steps")
        if any(len(step) > 240 for step in normalized):
            raise ValueError("each plan step must be 240 characters or fewer")

        plan = TaskPlan(
            id=uuid4().hex[:12],
            title=task_title,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            steps=[TaskStep(number=i, title=step) for i, step in enumerate(normalized, 1)],
        )
        self._plans[plan.id] = plan
        return self.describe(plan)

    def update_step(
        self,
        plan_id: str,
        step_number: int,
        status: str,
        evidence: str = "",
    ) -> dict:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise ValueError("task plan not found")
        if not isinstance(status, str) or status not in self._STEP_STATUSES:
            raise ValueError("unsupported step status")
        if not isinstance(step_number, int) or isinstance(step_number, bool):
            raise ValueError("step number must be an integer")
        if step_number < 1 or step_number > len(plan.steps):
            raise ValueError("step number is outside this plan")
        if not isinstance(evidence, str):
            raise ValueError("evidence must be text")
        note = evidence.strip()
        if status == "completed" and not note:
            raise ValueError("include a brief evidence note before completing a step")
        if len(note) > 1000:
            raise ValueError("evidence note must be 1000 characters or fewer")
        step = plan.steps[step_number - 1]
        step.status = status
        step.evidence = note
        return self.describe(plan)

    def list_plans(self) -> list[dict]:
        return [self.describe(plan) for plan in self._plans.values()]

    def clear(self) -> None:
        self._plans.clear()

    @staticmethod
    def describe(plan: TaskPlan) -> dict:
        return {
            "id": plan.id,
            "title": plan.title,
            "status": plan.status,
            "created_at": plan.created_at,
            "steps": [
                {
                    "number": step.number,
                    "title": step.title,
                    "status": step.status,
                    "evidence": step.evidence,
                }
                for step in plan.steps
            ],
        }
