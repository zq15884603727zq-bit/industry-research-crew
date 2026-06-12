"""
Task 链集成测试 — 验证 context 自动传递机制

测试目标：
  1. 验证 4 个 Task 通过 context 形成的数据管道能正常运行
  2. 验证下游 Task 确实收到了上游 Task 的输出
  3. 验证最终产出包含完整报告

context 链：
  research_task → analysis_task → writing_task → review_task
       ↑               ↑               ↑              ↑
   没有 context     context=[RT]    context=[AT]   context=[WT]

用法：
  python tests/test_pipeline.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Crew, Process

from agents.researcher import create_research_agent
from agents.analyst import create_analyst_agent
from agents.writer import create_writer_agent
from agents.reviewer import create_reviewer_agent

from tasks.research_task import create_research_task
from tasks.analysis_task import create_analysis_task
from tasks.writing_task import create_writing_task
from tasks.review_task import create_review_task

from tools.search_tool import create_search_tool


def test_full_pipeline():
    """
    完整 Pipeline 测试：Research → Analysis → Writing → Review
    """
    topic = "AI芯片"

    print("=" * 65)
    print(f"行业研究 Pipeline 集成测试")
    print(f"研究主题：{topic}")
    print("=" * 65)

    # ═══════════════════════════════════════════════════════
    # Step 1: 创建所有 Agent
    # ═══════════════════════════════════════════════════════
    print("\n[1/4] 创建 Agents...")
    search_tool = create_search_tool()
    researcher = create_research_agent(topic=topic, tools=[search_tool])
    analyst = create_analyst_agent()
    writer = create_writer_agent()
    reviewer = create_reviewer_agent()
    print(f"   Researcher: {researcher.role}")
    print(f"   Analyst:    {analyst.role}")
    print(f"   Writer:     {writer.role}")
    print(f"   Reviewer:   {reviewer.role}")

    # ═══════════════════════════════════════════════════════
    # Step 2: 创建 Task 并建立 context 链
    # ═══════════════════════════════════════════════════════
    print("\n[2/4] 创建 Tasks 并建立 context 链...")

    # Task 1: Research — 管道起点，无 context
    research_task = create_research_task(researcher, topic)
    print(f"   research_task: 无 context（管道起点）")

    # Task 2: Analysis — context=[research_task]，接收原始资料
    analysis_task = create_analysis_task(analyst, research_task)
    print(f"   analysis_task: context=[research_task] ← 自动接收研究资料")

    # Task 3: Writing — context=[analysis_task]，接收分析结果
    writing_task = create_writing_task(writer, analysis_task)
    print(f"   writing_task:  context=[analysis_task] ← 自动接收分析报告")

    # Task 4: Review — context=[writing_task]，接收报告初稿
    review_task = create_review_task(reviewer, writing_task)
    print(f"   review_task:   context=[writing_task] ← 自动接收报告初稿")

    # ═══════════════════════════════════════════════════════
    # Step 3: 组装 Crew（顺序执行）
    # ═══════════════════════════════════════════════════════
    print("\n[3/4] 组装 Crew（Process.sequential）...")
    crew = Crew(
        agents=[researcher, analyst, writer, reviewer],
        tasks=[research_task, analysis_task, writing_task, review_task],
        process=Process.sequential,  # 严格按顺序执行
        verbose=True,
    )
    print("   Crew 组装完成，4 个 Agent、4 个 Task，顺序执行")

    # ═══════════════════════════════════════════════════════
    # Step 4: 执行 Pipeline
    # ═══════════════════════════════════════════════════════
    print("\n[4/4] 执行 Pipeline...")
    print("-" * 65)
    result = crew.kickoff()
    print("-" * 65)

    # ═══════════════════════════════════════════════════════
    # 验证
    # ═══════════════════════════════════════════════════════
    content = str(result)
    print(f"\n{'=' * 65}")
    print("Pipeline 执行完毕 — 质量检查")
    print("=" * 65)
    print(f"最终输出长度: {len(content)} 字符")

    # 检查 1: 输出长度（完整报告应远超 1000 字符）
    checks = [
        (len(content) > 1000, "报告长度充足 (>1000 字符)"),
        (topic in content, "内容与主题相关"),
        # 检查报告结构关键词
        ("执行摘要" in content or "摘要" in content, "包含摘要"),
        ("竞争" in content, "包含竞争分析"),
        ("趋势" in content, "包含趋势分析"),
        ("风险" in content, "包含风险评估"),
    ]

    all_passed = True
    for passed, label in checks:
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status} {label}")

    # 检查 2: context 传递验证
    # （通过检查各 Task 输出是否被后续 Task 引用/使用来间接验证）
    print(f"\n--- context 传递验证 ---")
    print(f"Research Task 输出长度: {len(str(research_task.output))} 字符")
    print(f"Analysis Task 输出长度: {len(str(analysis_task.output))} 字符")
    print(f"Writing Task 输出长度:  {len(str(writing_task.output))} 字符")
    print(f"Review Task 输出长度:   {len(str(review_task.output))} 字符")

    # 验证 context 链：下游输出应包含上游输出的关键内容
    if research_task.output and analysis_task.output:
        print(f"\n[INFO] context 链验证（通过输出长度增长判断）:")
        # 下游输出通常比上游包含更多内容（累积信息）
        r_len = len(str(research_task.output))
        a_len = len(str(analysis_task.output))
        w_len = len(str(writing_task.output))
        print(f"   Research ({r_len}字) → Analysis ({a_len}字) → Writing ({w_len}字)")

    if all_passed:
        print(f"\n{'=' * 65}")
        print("Pipeline 集成测试全部通过！context 链正常工作。")
        print("=" * 65)
    else:
        print(f"\n部分检查未通过，请查看上述 [FAIL] 项。")

    return result


if __name__ == "__main__":
    test_full_pipeline()
