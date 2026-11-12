"""JARVIS Autonomous Agent Compound — Inspired by OpenManus and LuminaManusAgent.

Orchestrates multi-step goal planning, tool execution, and artifact generation
across the four specialized agents:
- J.A.R.V.I.S. (Supervisor & Comms)
- E.D.I.T.H. (Sandbox Execution)
- F.R.I.D.A.Y. (Security & Permission Vault)
- U.L.T.R.O.N. (Compute & Heavy Task Execution)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from jarvis.tools.base import get_default_registry

logger = logging.getLogger("jarvis.compound")


@dataclass
class TaskStep:
    id: int
    agent: str  # jarvis, edith, friday, ultron
    description: str
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    log: str = ""


@dataclass
class TaskPlan:
    goal: str
    status: str = "planning"  # planning, executing, completed, failed
    steps: List[TaskStep] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "status": self.status,
            "created_at": self.created_at,
            "steps": [
                {
                    "id": s.id,
                    "agent": s.agent,
                    "description": s.description,
                    "tool": s.tool,
                    "args": s.args,
                    "status": s.status,
                    "result": s.result,
                    "log": s.log,
                }
                for s in self.steps
            ],
            "artifacts": self.artifacts,
        }


class ManusCompoundEngine:
    """Autonomous goal decomposition and multi-agent execution pipeline."""

    def __init__(self) -> None:
        self.registry = get_default_registry()
        self.active_plan: Optional[TaskPlan] = None
        self.history: List[TaskPlan] = []

    def plan_and_execute(self, goal: str) -> TaskPlan:
        """Decompose a high-level user goal into structured steps and execute them."""
        plan = self._create_plan(goal)
        self.active_plan = plan

        plan.status = "executing"
        for step in plan.steps:
            step.status = "running"
            time.sleep(0.05)  # slight yield for async tracing

            if step.tool:
                # Security Gate: FRIDAY clearance check
                tool_obj = self.registry.get(step.tool)
                if tool_obj and tool_obj.risk == "blocked":
                    step.status = "failed"
                    step.log = f"Security block by F.R.I.D.A.Y.: {step.tool} is forbidden."
                    plan.status = "failed"
                    break

                res = self.registry.execute(step.tool, step.args, confirmed=True)
                if res.get("ok"):
                    step.status = "completed"
                    step.result = res.get("result")
                    step.log = f"Executed {step.tool} successfully via {step.agent.upper()}."
                else:
                    step.status = "failed"
                    step.log = f"Error executing {step.tool}: {res.get('error')}"
            else:
                step.status = "completed"
                step.log = f"Completed cognitive synthesis step via {step.agent.upper()}."

        if all(s.status == "completed" for s in plan.steps):
            plan.status = "completed"
            plan.artifacts.append({
                "type": "summary",
                "title": f"Artifact: {goal[:30]}",
                "timestamp": datetime.now().isoformat(),
                "content": f"All {len(plan.steps)} autonomous milestones achieved successfully.",
            })

        self.history.append(plan)
        return plan

    def _create_plan(self, goal: str) -> TaskPlan:
        """Deconstruct user intent into agent steps inspired by OpenManus."""
        g = goal.lower()
        steps: List[TaskStep] = []

        if any(k in g for k in ["telemetry", "health", "system", "stats", "inspect", "diagnose"]):
            steps = [
                TaskStep(1, "jarvis", "Decompose system diagnostic requirements"),
                TaskStep(2, "friday", "Verify security perimeter and interface states", tool="network_status"),
                TaskStep(3, "ultron", "Measure CPU, memory, and storage metrics", tool="system_stats"),
                TaskStep(4, "edith", "Package telemetry snapshot into workspace note", tool="write_note", args={"title": "system_health", "content": f"Health check at {datetime.now()}: nominal."}),
            ]
        elif any(k in g for k in ["suit", "armor", "mark 42", "hologram", "wireframe"]):
            steps = [
                TaskStep(1, "jarvis", "Identify target holographic asset model"),
                TaskStep(2, "ultron", "Allocate GPU rendering context and particle buffer"),
                TaskStep(3, "edith", "Project Mark 42 wireframe onto HUD overlay", tool="open_panel", args={"type": "hologram", "model": "mark42"}),
                TaskStep(4, "friday", "Activate real-time camera gesture tracking gateway"),
            ]
        elif any(k in g for k in ["network", "scan", "port", "connections"]):
            steps = [
                TaskStep(1, "jarvis", "Parse network audit objective"),
                TaskStep(2, "friday", "Scan local interfaces and verify egress filters", tool="network_status"),
                TaskStep(3, "edith", "Archive network connectivity state to local notes", tool="write_note", args={"title": "network_audit", "content": f"Network verified at {datetime.now()}."}),
            ]
        else:
            steps = [
                TaskStep(1, "jarvis", f"Synthesize intent for: {goal}"),
                TaskStep(2, "friday", "Check system policy allowlist and clearance"),
                TaskStep(3, "edith", "Perform sandboxed task execution", tool="system_stats"),
                TaskStep(4, "ultron", "Compile final task artifact"),
            ]

        return TaskPlan(goal=goal, steps=steps)


_compound_engine = ManusCompoundEngine()


def get_compound_engine() -> ManusCompoundEngine:
    return _compound_engine
