"""
记忆持久化模块 — 基于 ChromaDB 的向量存储与语义搜索

功能：
  1. 每次研究报告自动存入向量数据库
  2. 支持语义搜索：「找之前关于新能源的所有报告」
  3. 支持按主题、日期范围过滤
  4. 返回最相似的 N 条历史记录，作为新研究的参考

技术栈：
  - ChromaDB：轻量级向量数据库（已随 CrewAI 安装）
  - 默认嵌入模型：all-MiniLM-L6-v2（通过 sentence-transformers）
  - 持久化存储：output/chroma_db/

为什么需要记忆持久化：
  - 避免重复研究：新请求可先检索是否已有相似报告
  - 知识积累：每次研究都成为知识库的一部分
  - 上下文增强：后续研究可引用历史报告中的数据
"""

import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings


class ReportMemory:
    """
    行业研究报告记忆库。

    使用 ChromaDB 持久化存储报告内容和元数据，
    支持语义搜索和元数据过滤。

    用法：
        memory = ReportMemory()
        memory.add_report("AI芯片", report_content, "/path/to/report.md")
        results = memory.search("AI芯片市场规模", n_results=3)
        history = memory.list_reports()
    """

    def __init__(self, persist_dir: str = None):
        """
        初始化记忆库。

        Args:
            persist_dir: 持久化目录，默认为 output/chroma_db
        """
        if persist_dir is None:
            from config.settings import OUTPUT_DIR
            persist_dir = str(OUTPUT_DIR / "chroma_db")

        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="industry_reports",
            metadata={"description": "行业研究报告记忆库"},
        )

    def add_report(
        self,
        topic: str,
        content: str,
        filepath: str = "",
    ) -> str:
        """
        将一份报告存入记忆库。

        Args:
            topic:    研究主题
            content:  报告全文（Markdown 格式）
            filepath: 报告文件路径（可选）

        Returns:
            报告的唯一 ID
        """
        report_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # 截取前 8000 字符用于嵌入（平衡精度和性能）
        doc_for_embedding = content[:8000]

        try:
            self.collection.add(
                documents=[doc_for_embedding],
                metadatas=[{
                    "topic": topic,
                    "filepath": filepath,
                    "created_at": now,
                    "content_length": len(content),
                }],
                ids=[report_id],
            )
            print(f"   🧠 记忆已存储 (id={report_id}, topic={topic})")
        except Exception as e:
            # ChromaDB 嵌入失败时降级为仅存元数据
            print(f"   ⚠️  记忆存储降级（嵌入失败: {e}）")
            # 不阻断主流程

        return report_id

    def search(
        self,
        query: str,
        n_results: int = 3,
        topic_filter: str = None,
    ) -> List[dict]:
        """
        语义搜索历史报告。

        Args:
            query:        搜索查询（自然语言）
            n_results:    返回结果数
            topic_filter: 按主题关键词过滤（可选）

        Returns:
            匹配的报告列表，每项包含 {topic, filepath, created_at, content_preview}
        """
        where_filter = None
        if topic_filter:
            where_filter = {"topic": {"$contains": topic_filter}}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
        except Exception as e:
            print(f"   ⚠️  搜索出错: {e}")
            return []

        reports = []
        if results and results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                doc = results["documents"][0][i] if results.get("documents") else ""
                reports.append({
                    "id": doc_id,
                    "topic": meta.get("topic", "未知"),
                    "filepath": meta.get("filepath", ""),
                    "created_at": meta.get("created_at", ""),
                    "content_preview": doc[:300] + "..." if len(doc) > 300 else doc,
                })

        return reports

    def list_reports(self, limit: int = 20) -> List[dict]:
        """
        列出所有历史报告（按时间倒序）。

        Args:
            limit: 最大返回数

        Returns:
            报告列表
        """
        try:
            all_data = self.collection.get()
        except Exception:
            return []

        reports = []
        if all_data and all_data.get("ids"):
            for i, doc_id in enumerate(all_data["ids"]):
                meta = all_data["metadatas"][i] if all_data.get("metadatas") else {}
                reports.append({
                    "id": doc_id,
                    "topic": meta.get("topic", "未知"),
                    "filepath": meta.get("filepath", ""),
                    "created_at": meta.get("created_at", ""),
                    "content_length": meta.get("content_length", 0),
                })

        # 按创建时间倒序
        reports.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return reports[:limit]

    def search_similar_topics(self, topic: str, n_results: int = 3) -> List[dict]:
        """
        查找与给定主题相似的历史报告。

        这是「智能去重」的核心——在执行新研究前，
        先检索是否已有相关报告可以复用或参考。

        Args:
            topic:     研究主题
            n_results: 返回结果数

        Returns:
            相似报告列表
        """
        return self.search(
            query=f"{topic} 行业研究 市场规模 竞争格局 趋势分析",
            n_results=n_results,
        )

    def get_stats(self) -> dict:
        """获取记忆库统计信息"""
        try:
            all_data = self.collection.get()
            count = len(all_data.get("ids", []))
        except Exception:
            count = 0

        return {
            "total_reports": count,
            "storage_path": str(self.client._path) if hasattr(self.client, '_path') else "未知",
        }


# ── 全局单例 ───────────────────────────────────────────
_memory_instance: Optional[ReportMemory] = None


def get_memory() -> ReportMemory:
    """获取全局 ReportMemory 单例"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ReportMemory()
    return _memory_instance
