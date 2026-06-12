"""
Analysis Task — 信息分析任务

职责：驱动 Analyst Agent 对 Research Task 输出的原始资料进行深度分析。
这是 context 机制的核心示范——本 Task 通过 context=[research_task] 自动接收上游输出。

context 机制原理：
  当 Task B 设置了 context=[task_a]：
  1. CrewAI 等待 task_a 执行完毕
  2. 读取 task_a.output（Research Task 的完整输出文本）
  3. 将其注入到 Task B 的 prompt 中，作为「参考上下文」
  4. Agent B 看到的内容 = 本 Task 的 description + Task A 的 output
"""

from crewai import Task, Agent


def create_analysis_task(agent: Agent, research_task: Task) -> Task:
    """
    创建信息分析任务。

    Args:
        agent:          Analyst Agent 实例
        research_task:  上游 Research Task（其输出将自动注入本 Task）

    Returns:
        CrewAI Task 实例，context 已绑定到 research_task

    context 传递的数据流：
        research_task.output  →  CrewAI 自动注入  →  analysis_task 的 agent 看到
    """

    description = (
        "你已经收到了一份行业研究资料汇编（见上下文）。"
        "请对这份资料进行深度结构化分析。\n\n"
        "## 分析框架\n\n"
        "### 一、趋势提炼（至少 3 条）\n"
        "从资料中识别正在形成的行业趋势。每条趋势应包含：\n"
        "- 趋势描述（一句话概括）\n"
        "- 支撑数据（从资料中提取的具体数字、事件、时间线）\n"
        "- 趋势强度判断（强/中/弱，说明理由）\n\n"
        "### 二、竞争格局分析\n"
        "- 绘制竞争全景图：按市场份额或技术实力将企业分为领导者/挑战者/利基者\n"
        "- 分析各企业的战略意图和竞争优势\n"
        "- 识别正在发生的竞争攻防（谁在进攻？谁在防守？）\n\n"
        "### 三、机会识别（至少 3 个）\n"
        "- 描述每个机会的具体形态\n"
        "- 评估机会窗口（时间紧迫性）\n"
        "- 指出机会背后的驱动因素\n\n"
        "### 四、风险评估（至少 3 个）\n"
        "- 区分系统性风险（影响全行业）和可规避风险（特定企业/环节）\n"
        "- 评估每个风险的发生概率和影响程度\n"
        "- 给出风险应对的方向性建议\n\n"
        "## 分析要求\n"
        "- 每个结论必须引用资料中的具体信息作为证据\n"
        "- 对于资料中缺失的信息，明确标注「资料不足，无法判断」\n"
        "- 分析应超越资料表面，给出你的专业洞察"
    )

    expected_output = (
        "一份结构化的行业分析报告，包含：\n\n"
        "## 一、核心趋势\n"
        "至少 3 条趋势，每条含描述、数据支撑、强度判断\n\n"
        "## 二、竞争格局\n"
        "企业分层 + 竞争动态分析\n\n"
        "## 三、市场机会\n"
        "至少 3 个机会，含窗口期和驱动因素\n\n"
        "## 四、风险评估\n"
        "至少 3 个风险，含概率/影响评估和应对方向\n\n"
        "格式：Markdown，用中文输出，不少于 1200 字。"
    )

    # ═══════════════════════════════════════════════════════
    # context 参数——这是整个 Pipeline 的核心连接点
    # ═══════════════════════════════════════════════════════
    # 当 context=[research_task] 时：
    #   - CrewAI 将 research_task.output 注入本 Task 的提示词
    #   - Analyst Agent 能「看到」Researcher 收集的所有原始资料
    #   - 不需要手动拼接字符串或读写文件
    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
        context=[research_task],  # ← 核心：自动接收上游输出
    )
