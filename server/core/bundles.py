"""Portable declarative skill packs. Import never executes code, installs dependencies or grants tools."""

import json
import time
import uuid
from typing import Literal

from pydantic import Field, model_validator

from server.core.automation import Agent, Skill, Strict, Workflow


class Bundle(Strict):
    format: Literal["soloos-pack-v1"] = "soloos-pack-v1"
    title: str = Field(min_length=1, max_length=200)
    skills: dict[str, Skill] = Field(default_factory=dict, max_length=50)
    agents: dict[str, Agent] = Field(default_factory=dict, max_length=20)
    workflows: dict[str, Workflow] = Field(default_factory=dict, max_length=30)

    @model_validator(mode="after")
    def references(self):
        if len(self.model_dump_json()) > 500000:
            raise ValueError("Gói vượt giới hạn 500 KB.")
        for agent in self.agents.values():
            if any(key not in self.skills for key in agent.skills):
                raise ValueError("Trợ lý tham chiếu kỹ năng không có trong gói.")
        for workflow in self.workflows.values():
            if workflow.agent_id and workflow.agent_id not in self.agents:
                raise ValueError("Quy trình tham chiếu trợ lý không có trong gói.")
        return self


def install(store, bundle):
    mappings = {
        kind: {key: uuid.uuid4().hex for key in getattr(bundle, kind)}
        for kind in ("skills", "agents", "workflows")
    }
    with store.db() as db:
        db.execute("BEGIN IMMEDIATE")
        for kind in mappings:
            for key, body in getattr(bundle, kind).items():
                data = body.model_dump()
                # Pack data is imported disabled. Enabling and granting connections is an owner action.
                data["enabled"] = False
                if kind == "agents":
                    data["skills"] = [mappings["skills"][s] for s in data["skills"]]
                    data["connectors"] = []
                if kind == "workflows" and data["agent_id"]:
                    data["agent_id"] = mappings["agents"][data["agent_id"]]
                db.execute(
                    "INSERT INTO definitions VALUES(?,?,?,?)",
                    (mappings[kind][key], kind, json.dumps(data), time.time()),
                )
    return {
        "title": bundle.title,
        "imported": {k: len(v) for k, v in mappings.items()},
        "enabled": False,
    }


def export(store):
    result = {"format": "soloos-pack-v1", "title": "SoloOS workspace pack"}
    for kind in ("skills", "agents", "workflows"):
        result[kind] = {
            row["id"]: {k: v for k, v in row.items() if k != "id"}
            for row in store.definitions(kind)
        }
    return result
