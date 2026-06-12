"""
Bocha（博查）Search Tool — 中文搜索首选

基于博查 Web Search API（专为 AI Agent 设计的中文搜索引擎），
封装为 CrewAI BaseTool，替换 Tavily 作为默认搜索工具。

为什么选博查：
  - 中文搜索质量优于 Tavily / Serper
  - 免费试用 1000 次，按量付费 0.036 元/次（约为 Bing 的 1/3）
  - 无需海外信用卡，微信扫码即可注册
  - 响应速度约 0.15 秒

注册地址：https://bochaai.com
API 文档：https://bocha-ai.feishu.cn/wiki/HmtOw1z6vik14Fkdu5uc9VaInBb
"""

import os
import json
from typing import Type

import requests
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


# ── 输入 Schema ────────────────────────────────────────
class BochaSearchInput(BaseModel):
    """博查搜索输入参数"""
    query: str = Field(
        description=(
            "搜索查询词。支持自然语言，可使用中文或英文。"
            "建议包含具体关键词以提高精度。"
            "例如：'2025年AI芯片市场规模 英伟达' 或 '新能源汽车 最新政策 2025'"
        )
    )


# ── Tool 实现 ────────────────────────────────────────────
class BochaSearchTool(BaseTool):
    """
    博查搜索工具 — 为 Agent 提供中文网络搜索能力。

    使用方式：
        tool = BochaSearchTool(api_key="sk-xxx")
        # 或从环境变量 BOCHA_API_KEY 读取

    在 Agent 中使用：
        agent = Agent(tools=[BochaSearchTool()], ...)
    """

    name: str = "web_search"
    description: str = (
        "【网络搜索工具】使用博查搜索引擎搜索互联网实时信息。\n"
        "在以下情况下必须使用此工具：\n"
        "1. 需要查找行业最新动态、新闻或事件（特别是近期的）\n"
        "2. 需要获取市场规模、增长率等具体数据\n"
        "3. 需要了解特定企业的战略动作、财报信息\n"
        "4. 需要查找政策法规原文或最新解读\n"
        "5. 需要核实某个事实或数据的准确性\n\n"
        "输入：具体的关键词搜索查询\n"
        "输出：带来源链接的结构化搜索结果，含标题、摘要、网站名称和发布时间"
    )

    args_schema: Type[BaseModel] = BochaSearchInput

    _api_key: str = ""

    def __init__(self, api_key: str = None, **kwargs):
        """
        初始化博查搜索工具。

        Args:
            api_key: 博查 API Key（sk-xxx 格式）。
                     不传则从 BOCHA_API_KEY 环境变量读取。
                     注册地址：https://bochaai.com
        """
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("BOCHA_API_KEY", "")

    def _run(self, query: str) -> str:
        """
        执行博查搜索。

        CrewAI 在 Agent 发起 Tool Call 时调用此方法，
        返回结果直接交还给 Agent 继续推理。
        """
        if not self._api_key:
            return (
                "搜索服务未配置。请前往 https://bochaai.com 注册获取 API Key，\n"
                "然后在 .env 文件中设置 BOCHA_API_KEY=sk-xxx。\n"
                "免费试用 1000 次，无需信用卡。\n\n"
                f"你搜索的是: {query}\n"
                "请基于你的知识库回答，并在回复中注明这是知识库信息而非实时搜索结果。"
            )

        try:
            response = requests.post(
                "https://api.bochaai.com/v1/web-search",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "summary": True,       # 返回网页正文摘要
                    "freshness": "oneYear", # 优先近一年的内容
                    "count": 3,            # 每次 3 条，避免上下文过大
                },
                timeout=10,               # 10 秒超时，避免卡死
            )
            response.raise_for_status()
            data = response.json()
            return self._format_results(data)

        except requests.exceptions.Timeout:
            return f"搜索超时，请尝试简化查询词或稍后重试。查询: {query}"
        except requests.exceptions.RequestException as e:
            return f"搜索请求失败: {e}。请检查网络连接和 API Key 是否有效。"

    def _format_results(self, data: dict) -> str:
        """
        格式化博查 API 返回结果。

        返回格式：
        {
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "标题",
                            "url": "链接",
                            "snippet": "简短摘要",
                            "summary": "详细摘要",
                            "siteName": "网站名",
                            "datePublished": "发布时间"
                        }
                    ]
                }
            }
        }
        """
        try:
            web_pages = data.get("data", {}).get("webPages", {}).get("value", [])
        except (AttributeError, KeyError):
            return "搜索结果解析失败，请尝试更换关键词。"

        if not web_pages:
            return "未找到相关结果，请尝试更换搜索词或扩大搜索范围。"

        lines = ["=" * 55]
        lines.append(f"共找到 {len(web_pages)} 条结果:\n")

        for i, page in enumerate(web_pages, 1):
            title = page.get("name", "无标题")
            url = page.get("url", "")
            snippet = page.get("snippet", "")
            summary = page.get("summary", "")
            site = page.get("siteName", "未知来源")
            date = page.get("datePublished", "")

            # 优先使用详细摘要，回退到简短摘要
            content = summary or snippet
            if len(content) > 350:
                content = content[:350] + "..."

            lines.append(f"{i}. {title}")
            lines.append(f"   来源: {site}")
            if date:
                lines.append(f"   时间: {date}")
            lines.append(f"   链接: {url}")
            lines.append(f"   摘要: {content}")
            lines.append("")

        return "\n".join(lines)


# ── 工厂函数 ────────────────────────────────────────────
def create_bocha_search_tool() -> BochaSearchTool:
    """创建博查搜索工具实例（从环境变量读取 API Key）"""
    return BochaSearchTool()
