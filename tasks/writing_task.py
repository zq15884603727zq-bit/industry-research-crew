"""
Writing Task — 报告撰写任务

职责：驱动 Writer Agent 将 Analyst 的结构化分析转化为专业 Markdown 报告。
通过 context=[analysis_task] 自动接收上游分析结果。
"""

from crewai import Task, Agent


def create_writing_task(agent: Agent, analysis_task: Task) -> Task:
    """
    创建报告撰写任务。

    Args:
        agent:          Writer Agent 实例
        analysis_task:  上游 Analysis Task（其输出自动注入）

    Returns:
        CrewAI Task 实例，context 已绑定

    context 链路：
        research_task → analysis_task → writing_task（本 Task）
                         ↑
                     analysis_task.output 自动注入
    """

    description = (
        "你已经收到了一份行业分析报告（见上下文）。"
        "请基于这份分析，撰写一份完整的、可直接交付的行业研究报告。\n\n"
        "## 报告结构（严格遵循）\n\n"
        "### 封面\n"
        "```markdown\n"
        "# [行业名称] 行业研究报告\n"
        "**报告日期：** [当前日期]\n"
        "**研究机构：** AI 行业研究团队\n"
        "**密级：** 内部参考\n"
        "```\n\n"
        "### 执行摘要（300 字以内）\n"
        "用 5-7 句话概括报告的核心发现，让决策者能在 1 分钟内了解全貌。\n"
        "结构：行业现状一句话 + 3 个关键趋势 + 最重要的机会 + 最大的风险。\n\n"
        "### 第一章：行业概况\n"
        "- 1.1 行业定义与边界\n"
        "- 1.2 市场规模与增长（含具体数据）\n"
        "- 1.3 发展阶段与驱动因素\n\n"
        "### 第二章：竞争格局\n"
        "- 2.1 竞争全景图\n"
        "- 2.2 头部企业深度对比\n"
        "- 2.3 竞争态势展望\n\n"
        "### 第三章：技术分析\n"
        "- 3.1 主流技术路线\n"
        "- 3.2 技术前沿与突破\n"
        "- 3.3 技术演进方向\n\n"
        "### 第四章：政策环境\n"
        "- 4.1 监管框架\n"
        "- 4.2 政策影响分析\n\n"
        "### 第五章：趋势与展望\n"
        "- 5.1 短期趋势（未来 1 年）\n"
        "- 5.2 中期趋势（未来 3 年）\n"
        "- 5.3 关键不确定性\n\n"
        "### 第六章：机会与风险\n"
        "- 6.1 投资/进入机会\n"
        "- 6.2 主要风险与应对\n\n"
        "### 附录\n"
        "- 数据来源汇总\n"
        "- 研究方法说明\n\n"
        "## 写作要求\n"
        "- 专业客观，用数据和事实说话\n"
        "- 每个章节开头用一句话概括核心观点\n"
        "- 关键数据加粗突出\n"
        "- 使用表格对比多维度信息\n"
        "- 总字数不少于 2500 字"
    )

    expected_output = (
        "一份完整的 Markdown 格式行业研究报告，严格遵循上述九章结构。\n"
        "封面包含标题和日期，执行摘要精炼有力，各章节数据翔实、逻辑清晰。\n"
        "不少于 2500 字。用中文输出。"
    )

    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
        context=[analysis_task],  # ← 自动接收分析结果
    )
