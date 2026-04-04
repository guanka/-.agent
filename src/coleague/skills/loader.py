"""技能加载器"""

import json
from pathlib import Path
from typing import Any


class SkillData:
    def __init__(self, meta: dict[str, Any], system_prompt: str, skill_dir: Path):
        self.meta = meta
        self.system_prompt = system_prompt
        self.skill_dir = skill_dir


class SkillLoader:
    def __init__(self, skill_dir: Path | str):
        self.skill_dir = Path(skill_dir)

    def find_skill_dir(self) -> Path:
        for item in self.skill_dir.iterdir():
            if item.is_dir() and item.suffix == ".skill":
                return item
        raise FileNotFoundError(f"No .skill directory found in {self.skill_dir}")

    def load_skill(self) -> SkillData:
        skill_path = self.find_skill_dir()
        meta_path = skill_path / "meta.json"
        skill_md_path = skill_path / "SKILL.md"

        if not meta_path.exists():
            raise FileNotFoundError(f"meta.json not found in {skill_path}")
        if not skill_md_path.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        with open(skill_md_path, encoding="utf-8") as f:
            content = f.read()
            start = content.find("---")
            end = content.find("---", start + 3)
            if start != -1 and end != -1:
                system_prompt = content[end + 3:].strip()
            else:
                system_prompt = content.strip()

        return SkillData(meta=meta, system_prompt=system_prompt, skill_dir=skill_path)

    def load_colleague_skill(self) -> SkillData:
        return self.load_skill()

    def list_skills(self) -> list[str]:
        return [d.name for d in self.skill_dir.iterdir() if d.is_dir() and d.suffix == ".skill"]
