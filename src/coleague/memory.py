"""memory.py — MemPalace 记忆集成模块。

提供对话记忆的搜索和存储，基于 MemPalace 的 ChromaDB 语义搜索。
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from mempalace.config import MempalaceConfig
from mempalace.palace import get_collection
from mempalace.searcher import search_memories


logger = logging.getLogger("coleague.memory")


class Memory:
    def __init__(self, palace_path: str | None = None, wing: str = "coleague"):
        cfg = MempalaceConfig()
        self.palace_path = palace_path or cfg.palace_path
        self.wing = wing
        # 确保 palace 目录存在
        Path(self.palace_path).mkdir(parents=True, exist_ok=True)

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """语义搜索相关记忆，返回结果列表。"""
        try:
            result = search_memories(
                query=query,
                palace_path=self.palace_path,
                wing=self.wing,
                n_results=n_results,
            )
            if "error" in result:
                logger.debug("记忆搜索无结果: %s", result["error"])
                return []
            hits = result.get("results", [])
            # ChromaDB cosine distance 范围 0~2，similarity = 1 - distance
            # 经过 hybrid rank 后 similarity 可能为 0，用 distance < 1.5 过滤
            return [h for h in hits if h.get("distance", 2) < 1.5]
        except Exception as e:
            logger.debug("记忆搜索失败: %s", e)
            return []

    def store(self, user_msg: str, assistant_msg: str) -> None:
        """将一轮对话存入 palace。"""
        content = f"> {user_msg}\n{assistant_msg}"
        if len(content.strip()) < 30:
            return
        try:
            col = get_collection(self.palace_path)
            drawer_id = f"drawer_{self.wing}_chat_{hashlib.sha256(content.encode()).hexdigest()[:24]}"
            col.upsert(
                documents=[content],
                ids=[drawer_id],
                metadatas=[{
                    "wing": self.wing,
                    "room": "chat",
                    "source_file": "feishu_live",
                    "chunk_index": 0,
                    "added_by": "coleague",
                    "filed_at": datetime.now().isoformat(),
                    "ingest_mode": "live",
                }],
            )
            logger.debug("记忆已存储: %s...", user_msg[:50])
        except Exception as e:
            logger.warning("记忆存储失败: %s", e)

    def format_context(self, hits: list[dict]) -> str:
        """将搜索结果格式化为 system prompt 片段。"""
        if not hits:
            return ""
        parts = []
        for h in hits:
            parts.append(h.get("text", "").strip())
        joined = "\n---\n".join(parts)
        return f"# 相关记忆\n\n以下是与当前话题相关的历史对话记忆：\n\n{joined}"
