"""LAYER 3: skills. Procedure and judgment, in prose, for the model to read.

A skill is a folder with a SKILL.md and nothing else. A child skill is a folder inside its
parent's folder and is read after it. Skills hold no values, no criteria and no guardrail
rules; `lint` enforces that.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# A policy value has no place in a skill: money, percentages, basis points, day counts.
VALUE = re.compile(r"\$\s?\d|\d\s?%|\d+\s?(?:bp|bps|pts?|points?|days?|months?|years?)\b", re.I)
TOOL_REF = re.compile(r"`([a-z_]+)`")


@dataclass
class Skill:
    id: str
    description: str
    body: str
    path: Path
    parent: "Skill | None" = None
    children: list["Skill"] = field(default_factory=list)

    @property
    def chain(self) -> list["Skill"]:
        return (self.parent.chain if self.parent else []) + [self]


def load(root: Path) -> dict[str, Skill]:
    by_path: dict[Path, Skill] = {}
    out: dict[str, Skill] = {}
    for md in sorted(Path(root).rglob("SKILL.md"), key=lambda p: len(p.parts)):
        _, fm, body = md.read_text().split("---", 2)
        meta = yaml.safe_load(fm)
        s = Skill(meta["name"], meta["description"], body.strip(), md.parent)
        anc = md.parent.parent
        while anc != Path(root).parent and anc not in by_path:
            anc = anc.parent
        if anc in by_path:
            s.parent = by_path[anc]
            by_path[anc].children.append(s)
        by_path[md.parent] = out[s.id] = s
    return out


def lint(skills: dict[str, Skill], tool_names: list[str], skill_ids: list[str] | None = None) -> list[str]:
    """Problems that mean a skill has drifted out of its layer."""
    problems = []
    known = set(tool_names) | set(skill_ids or skills)
    for s in skills.values():
        extra = [f.name for f in s.path.iterdir() if f.is_file() and f.name != "SKILL.md"]
        if extra:
            problems.append(f"{s.id}: a skill folder holds only SKILL.md, found {extra}")
        for n, line in enumerate(s.body.splitlines(), start=1):
            hit = VALUE.search(line)
            if hit:
                problems.append(f"{s.id} line {n}: policy value in a skill ('{hit.group(0).strip()}'). "
                                "Move it to the policy pack and let a tool return it.")
        for ref in TOOL_REF.findall(s.body):
            if ref not in known:
                problems.append(f"{s.id}: refers to `{ref}`, which is not a tool or a skill")
    return problems
