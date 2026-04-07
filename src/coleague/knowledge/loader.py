import logging
from pathlib import Path


class KnowledgeLoader:
    def __init__(self, knowledge_dir: str | Path):
        self.knowledge_dir = Path(knowledge_dir)
        self.logger = logging.getLogger("coleague.knowledge")

    def load_all(self) -> str:
        if not self.knowledge_dir.exists():
            self.logger.warning(f"知识库目录不存在: {self.knowledge_dir}")
            return ""

        docs: list[str] = []
        for md_file in sorted(self.knowledge_dir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8").strip()
                if content:
                    rel = md_file.relative_to(self.knowledge_dir)
                    docs.append(f"## [{rel}]\n\n{content}")
                    self.logger.debug(f"已加载知识文档: {rel}")
            except Exception as e:
                self.logger.warning(f"加载知识文档失败 {md_file}: {e}")

        if not docs:
            return ""

        self.logger.info(f"知识库加载完成: {len(docs)} 个文档")
        return "\n\n---\n\n".join(docs)

    def build_system_context(self) -> str:
        content = self.load_all()
        if not content:
            return ""
        return f"# 设备知识库\n\n以下是工厂设备的参考知识，回答问题时可以参考：\n\n{content}"
