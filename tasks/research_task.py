"""
Research Task — 资料搜集任务

职责：驱动 Researcher Agent 全面搜集指定行业的最新资料。
这是整个 Pipeline 的起点，输出将自动传递给 Analyst Task。
"""

from crewai import Task, Agent


def create_research_task(agent: Agent, topic: str) -> Task:
    """
    创建资料搜集任务。

    Args:
        agent:    Researcher Agent 实例（需已绑定搜索工具）
        topic:    研究主题，如 "AI芯片"、"新能源汽车"

    Returns:
        CrewAI Task 实例

    设计要点：
        - description 给 Agent 下达具体指令，包含搜索策略和覆盖维度
        - expected_output 约束产出格式，下游 Analyst 依赖这个格式
        - 不设 context（这是 Pipeline 的起点）
    """

    description = (
        f"你的任务是全面研究「{topic}」行业。\n\n"
        "请按照以下步骤执行：\n\n"
        "## 第一步：全景扫描\n"
        f"使用 web_search 工具搜索「{topic} 行业 最新动态 2025」，了解行业概况。\n\n"
        "## 第二步：分维度深入\n"
        f"针对以下每个维度，分别搜索并整理信息：\n"
        f"1. 市场规模与增长趋势 → 搜索「{topic} 市场规模 增长率 预测」\n"
        f"2. 竞争格局与主要企业 → 搜索「{topic} 头部企业 市场份额 竞争」\n"
        f"3. 技术趋势与创新 → 搜索「{topic} 技术突破 创新趋势」\n"
        f"4. 政策法规环境 → 搜索「{topic} 政策 法规 监管」\n"
        f"5. 风险与挑战 → 搜索「{topic} 行业风险 挑战」\n\n"
        "## 第三步：整理归档\n"
        "将搜集到的所有信息按以下结构整理：\n"
        "- 每条信息标注来源和日期\n"
        "- 区分事实（搜索结果原文）与你的理解（分析标注）\n"
        "- 如果某维度信息不足，明确说明\n\n"
        "## 注意事项\n"
        "- 每个维度至少搜索 1 次，确保信息充分\n"
        "- 优先使用中文关键词搜索，必要时补充英文搜索\n"
        "- 如果搜索工具未配置，请基于知识库回答并明确标注"
    )

    expected_output = (
        "一份结构化的行业研究资料汇编，包含以下章节：\n\n"
        "## 一、市场概况\n"
        "- 市场规模数据（注明来源与发布时间）\n"
        "- 增长率与预测\n"
        "- 发展阶段判断\n\n"
        "## 二、竞争格局\n"
        "- 头部企业列表及市场份额\n"
        "- 各企业战略动向\n"
        "- 竞争态势总结\n\n"
        "## 三、技术趋势\n"
        "- 当前主流技术路线\n"
        "- 前沿技术方向\n"
        "- 技术突破事件\n\n"
        "## 四、政策法规\n"
        "- 相关政策列表\n"
        "- 监管动态\n"
        "- 政策影响分析\n\n"
        "## 五、风险与挑战\n"
        "- 主要风险因素\n"
        "- 行业面临的挑战\n\n"
        "格式要求：Markdown 格式，每条信息标注来源和日期。"
        "不少于 1500 字。用中文输出。"
    )

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )
