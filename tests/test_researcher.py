"""
Research Agent 单元测试

验证 Agent 能否：
1. 正确理解角色和任务
2. 输出结构化的研究资料
3. 在没有工具的情况下，基于自身知识给出合理回答

用法：python tests/test_researcher.py
"""

import sys
from pathlib import Path

# 把项目根目录加入 sys.path，保证能从 tests/ 目录 import 项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Task, Crew
from agents.researcher import create_research_agent


def test_researcher():
    """测试 Research Agent 是否能正常执行"""

    # 1. 创建 Agent
    topic = "AI芯片"
    agent = create_research_agent(topic=topic)

    print(f"Agent 创建成功: {agent.role}")
    print(f"Goal: {agent.goal[:60]}...")
    print(f"LLM: {agent.llm.model}")
    print("-" * 60)

    # 2. 创建 Task — 注意 Task 的 expected_output 会约束 Agent 的产出格式
    task = Task(
        description=(
            f"请研究「{topic}」行业的最新动态。\n"
            f"由于你暂时没有搜索工具，请基于你的知识库，\n"
            f"整理一份涵盖以下方面的研究简报：\n"
            f"1. 行业概况（市场规模、发展阶段）\n"
            f"2. 主要玩家（国内外头部企业及各自优势）\n"
            f"3. 技术趋势（当前主流技术路线和前沿方向）\n"
            f"4. 近期重要事件（过去一年内的重大新闻）\n"
            f"5. 政策环境（相关国家政策和监管动态）\n\n"
            f"每条信息请注明你的判断依据。"
        ),
        expected_output=(
            "一份结构化的行业研究简报，按行业概况、主要玩家、技术趋势、"
            "近期事件、政策环境五个章节组织，语言专业、信息密度高。"
            "不少于 800 字。用中文输出。"
        ),
        agent=agent,
    )

    # 3. 创建 Crew（即使只有一个 Agent，也要通过 Crew 运行）
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )

    # 4. 执行
    print("\n开始执行 Research Agent...\n")
    result = crew.kickoff()

    # 5. 输出结果
    print("\n" + "=" * 60)
    print("最终输出:")
    print("=" * 60)
    print(result)

    # 6. 基础质量检查
    content = str(result)
    checks = [
        ("芯片" in content, "内容相关性"),
        (len(content) > 400, "输出长度充足"),
        ("市场" in content, "包含市场分析"),
        ("技术" in content, "包含技术趋势"),
    ]
    all_passed = True
    for passed, label in checks:
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status} {label}")

    if all_passed:
        print("\n所有检查通过！Research Agent 工作正常。")
    else:
        print("\n部分检查未通过，请检查 Agent 输出。")
    return result


if __name__ == "__main__":
    test_researcher()
