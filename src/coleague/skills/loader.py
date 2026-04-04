"""技能加载器"""

import json
from pathlib import Path
from typing import Any


class SkillLoader:
    def __init__(self, skill_dir: Path | str):
        self.skill_dir = Path(skill_dir)

    def load_skill(self, skill_name: str) -> dict[str, Any]:
        skill_path = self.skill_dir / f"{skill_name}.json"
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_name}")
        with open(skill_path, encoding="utf-8") as f:
            return json.load(f)

    def load_colleague_skill(self) -> dict[str, Any]:
        return self.load_skill("同事")

    def list_skills(self) -> list[str]:
        return [p.stem for p in self.skill_dir.glob("*.json")]
