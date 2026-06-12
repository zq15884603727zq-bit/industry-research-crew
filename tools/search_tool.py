"""
Tavily Search Tool — 为 Agent 提供实时网络搜索能力

基于 Tavily Search API（专为 AI Agent 设计的搜索引擎），
封装为 CrewAI BaseTool，支持 Research Agent 直接调用。

Tool 调用机制（ReAct 循环）：
  1. CrewAI 将工具的 name + description 注入 Agent 的 System Prompt
  2. Agent 推理时，如果判断需要外部信息，输出 Tool Call 指令
  3. CrewAI 拦截 Tool Call，执行 _run() 方法
  4. 工具返回结果后，CrewAI 将结果交还给 Agent 继续推理
  5. Agent 可多次调用工具（受 max_iter 限制），直到完成任务
"""

import os
from typing import Type

from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tavily import TavilyClient


# ── 输入 Schema：定义工具的参数约束 ────────────────────────
# Pydantic 模型会被 CrewAI 自动转换为 LLM 可理解的函数签名。
# Field(description=...) 是写给 LLM 看的——帮助它决定传什么参数。
class TavilySearchInput(BaseModel):
    """搜索工具的输入参数"""
    query: str = Field(
        description=(
            "搜索查询字符串。请使用中文或英文关键词，"
            "尽量具体，包含行业名称、时间范围等信息。"
            "例如：'2025年AI芯片市场规模 英伟达' 或 '新能源汽车 政策 欧洲 2025'"
        )
    )


# ── Tool 实现 ────────────────────────────────────────────
class TavilySearchTool(BaseTool):
    """
    Tavily 搜索工具 — 为 Agent 提供实时网络信息检索能力。

    使用方式：
        tool = TavilySearchTool(api_key="tvly-xxx")
        # 或从环境变量 TAVILY_API_KEY 自动读取

    在 CrewAI Agent 中使用：
        agent = Agent(
            tools=[TavilySearchTool()],
            ...
        )
    """

    # ── 元信息：LLM 通过这两个字段决定是否调用、何时调用 ──────
    # 注意：name 必须是 ASCII 字符（CrewAI 会将其转为 OpenAI function name，
    # 非 ASCII 字符会被清洗掉导致空字符串错误）
    name: str = "web_search"
    description: str = (
        "网络搜索工具：使用搜索引擎获取互联网上的实时信息和最新数据。"
        "在以下情况下应使用此工具：\n"
        "1. 需要查找行业最新动态、新闻或事件（特别是近期的）\n"
        "2. 需要获取市场规模、增长率等具体数据\n"
        "3. 需要了解特定企业的战略动作、财报数据\n"
        "4. 需要查找政策法规的原文或解读\n"
        "5. 需要核实某个事实或数据的准确性\n\n"
        "输入：具体的搜索查询词（关键词越精确，结果越有价值）\n"
        "输出：带来源链接的结构化搜索结果，包含标题、内容和发布时间"
    )

    # ── 参数 Schema：告诉 LLM 工具接受什么参数 ──────────────
    args_schema: Type[BaseModel] = TavilySearchInput

    # ── 内部状态 ──────────────────────────────────────────
    _client: TavilyClient = None

    def __init__(self, api_key: str = None, **kwargs):
        """
        初始化 Tavily 搜索工具。

        Args:
            api_key: Tavily API Key（可选）。
                     如果不传，则从环境变量 TAVILY_API_KEY 读取。
                     免费额度：1000 次/月，足够开发使用。
                     获取地址：https://app.tavily.com
        """
        super().__init__(**kwargs)
        key = api_key or os.getenv("TAVILY_API_KEY", "")
        self._client = TavilyClient(api_key=key) if key else None

    # ── 核心方法：Agent 调用工具时执行 ──────────────────────
    def _run(self, query: str) -> str:
        """
        执行搜索并返回格式化结果。

        这是 CrewAI 引擎在 Agent 发起 Tool Call 时调用的入口。
        返回值会直接交还给 Agent，作为其后续推理的上下文。

        Args:
            query: 搜索查询词（由 Agent 决定传入什么）

        Returns:
            格式化后的搜索结果字符串，包含标题、链接、内容和来源
        """
        # 无 API Key 时的降级处理
        if not self._client:
            return (
                "⚠️ 搜索服务未配置。请设置 TAVILY_API_KEY 环境变量。\n"
                "获取免费 API Key: https://app.tavily.com\n\n"
                f"你搜索的是: {query}\n"
                "请基于你的知识库回答，并注明这是知识库信息而非实时搜索结果。"
            )

        try:
            # 调用 Tavily Search API
            # search_depth="advanced": 深度搜索模式，返回更丰富的内容
            # max_results=5: 每次返回 5 条，平衡信息量和效率
            response = self._client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True,  # Tavily 会生成一个综合回答摘要
            )
            return self._format_results(response)

        except Exception as e:
            return (
                f"搜索执行出错: {str(e)}\n"
                f"请尝试换个关键词重试，或基于已有知识回答。"
            )

    # ── 结果格式化：将 API 返回的 JSON 转为 Agent 易读的文本 ──
    def _format_results(self, response: dict) -> str:
        """
        将 Tavily API 返回的结构化数据格式化为 Agent 可读的文本。

        Tavily 返回格式：
        {
            "query": "搜索词",
            "answer": "综合回答摘要（如果 include_answer=True）",
            "results": [
                {
                    "title": "...",
                    "url": "...",
                    "content": "...",
                    "score": 0.95,
                    "published_date": "..."
                },
                ...
            ]
        }

        格式化原则：
        - 保留来源 URL（Agent 后续引用时需要）
        - 截断过长内容（避免超出 LLM 上下文窗口）
        - 结构化编号（Agent 容易按序号引用）
        """
        query = response.get("query", "未知查询")
        lines = [f"搜索词: {query}", "=" * 50]

        # 优先展示 Tavily 的综合摘要（通常质量较高）
        answer = response.get("answer")
        if answer:
            lines.append(f"\n📊 综合摘要:\n{answer}\n")

        # 逐条展示搜索结果
        results = response.get("results", [])
        if not results:
            lines.append("\n未找到相关结果，请尝试更换搜索词。")
            return "\n".join(lines)

        lines.append(f"共找到 {len(results)} 条结果:\n")

        for i, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            url = result.get("url", "")
            content = result.get("content", "")

            # 截断过长内容，保留 300 字符足够 Agent 判断相关性
            if len(content) > 300:
                content = content[:300] + "..."

            lines.append(f"{i}. {title}")
            lines.append(f"   链接: {url}")
            lines.append(f"   内容: {content}")
            lines.append("")

        return "\n".join(lines)


# ── 工厂函数：便于统一创建 ────────────────────────────────
def create_search_tool() -> TavilySearchTool:
    """
    创建搜索工具实例。

    自动从环境变量 TAVILY_API_KEY 读取密钥。
    如果未设置，工具仍可创建但会以降级模式运行（提示用户配置）。
    """
    return TavilySearchTool()
