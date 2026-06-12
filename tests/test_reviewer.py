"""
Reviewer Agent 专项测试

测试 Reviewer 的审核能力——向它提交一份故意植入了 6 个错误的模拟报告，
验证 Reviewer 能否发现这些问题。

植入的错误：
  1. 数据矛盾：摘要说 500 亿，正文说 800 亿
  2. 缺失维度：缺少政策环境章节
  3. 来源模糊：关键数据未标注来源
  4. 口语化表达：「太牛了」「简直是降维打击」
  5. 标题不准确：标题说「竞争格局」，内容却是技术分析
  6. 计算错误：增长率算错

用法：
  python tests/test_reviewer.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Task, Crew
from agents.reviewer import create_reviewer_agent


# ── 模拟报告（故意植入 6 个错误）──────────────────────
FLAWED_DRAFT = """
# 新能源汽车行业研究报告

**报告日期：** 2025年6月

## 执行摘要

新能源汽车市场简直太牛了，2025年全球市场规模预计达到500亿美元，
行业发展势如破竹，各大车企纷纷入局，简直是降维打击。

## 第一章：行业概况

2025年全球新能源汽车市场规模约为800亿美元，同比增长35%。
中国市场表现尤为突出，占全球市场份额超过60%。

## 第二章：竞争格局

新能源汽车的核心技术路线分为纯电动（BEV）、插电混动（PHEV）
和燃料电池（FCEV）三种。其中BEV占据主导地位，市场份额约70%。
电池技术方面，磷酸铁锂和三元锂电池是两大主流路线，
固态电池被认为是下一代关键技术，但量产时间仍不确定。

## 第三章：风险分析

行业面临的主要风险包括：
- 原材料价格波动风险
- 补贴退坡风险
- 产能过剩风险

---

**免责声明：** 本报告仅供参考，不构成投资建议。
"""


def test_reviewer_catches_errors():
    """核心测试：验证 Reviewer 能否发现植入的 6 个错误"""

    print("=" * 65)
    print("Reviewer Agent 专项测试")
    print("验证：审核能力（逻辑一致性、完整性、准确性、表达、格式）")
    print("=" * 65)

    # 1. 创建 Reviewer Agent
    reviewer = create_reviewer_agent()
    print(f"\n[1/3] Agent 创建成功: {reviewer.role}")

    # 2. 创建 Review Task — 直接嵌入模拟报告
    task = Task(
        description=(
            "你收到了一份行业研究报告初稿，内容如下：\n\n"
            "---报告开始---\n"
            f"{FLAWED_DRAFT}\n"
            "---报告结束---\n\n"
            "请严格按照「三阶段审核流程」进行审核：\n"
            "阶段一：逐章核查（逻辑、完整性、数据、表达、格式）\n"
            "阶段二：综合评分（每个维度 1-5 分）\n"
            "阶段三：输出审核报告 + 修订后报告\n\n"
            "审核报告需逐条列出发现的问题，标注位置、严重等级和修改建议。\n"
            "修订后报告必须是完整的、所有问题已修正的最终版本。"
        ),
        expected_output=(
            "## 审核报告\n"
            "综合评分表 + 逐条问题\n\n"
            "## 修订后报告\n"
            "完整的修订后报告\n\n"
            "用中文输出。"
        ),
        agent=reviewer,
    )

    print("[2/3] Task 创建成功（含模拟缺陷报告）")

    # 3. 执行
    crew = Crew(
        agents=[reviewer],
        tasks=[task],
        verbose=True,
    )

    print("[3/3] 开始审核...\n")
    result = crew.kickoff()

    # ── 自动验证 ────────────────────────────────────
    content = str(result)
    print("\n" + "=" * 65)
    print("质量验证：检查 Reviewer 是否发现了植入的错误")
    print("=" * 65)

    # 定义期望发现的问题
    expected_findings = [
        (
            "数据矛盾",
            ("500" in content and "800" in content),
            "摘要说 500 亿，正文说 800 亿——数据不一致"
        ),
        (
            "缺失维度",
            any(kw in content for kw in ["政策环境", "政策", "遗漏"]),
            "报告缺少政策环境章节"
        ),
        (
            "来源标注",
            any(kw in content for kw in ["来源", "数据来源", "标注"]),
            "关键数据未标注来源"
        ),
        (
            "口语化表达",
            any(kw in content for kw in ["口语", "太牛", "降维打击", "情绪", "不专业"]),
            "执行摘要存在口语化、情绪化表达"
        ),
        (
            "标题不匹配",
            any(kw in content for kw in ["标题", "不准确", "章节内容", "竞争格局"]),
            "竞争格局章节内容与标题不匹配"
        ),
        (
            "计算准确性",
            any(kw in content for kw in ["计算", "增长率", "百分比"]),
            "审核涉及数据计算检查"
        ),
    ]

    found_count = 0
    for name, passed, description in expected_findings:
        status = "[PASS]" if passed else "[MISS]"
        if passed:
            found_count += 1
        print(f"{status} {name}: {description}")

    # ── 检查输出结构 ─────────────────────────────────
    print(f"\n--- 结构完整性检查 ---")
    has_review_section = "审核报告" in content
    has_revised_section = "修订后报告" in content
    has_scoring = any(kw in content for kw in ["评分", "分/5", "/5"])

    checks = [
        (has_review_section, "包含「审核报告」章节"),
        (has_revised_section, "包含「修订后报告」章节"),
        (has_scoring, "包含综合评分"),
        (len(content) > 500, f"输出长度充足 ({len(content)} 字符)"),
    ]
    for passed, label in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {label}")

    # ── 总结 ─────────────────────────────────────────
    print(f"\n{'=' * 65}")
    print(f"Reviewer 测试总结: 发现 {found_count}/{len(expected_findings)} 类问题")
    if found_count >= 4:
        print("Reviewer Agent 审核能力验证通过！")
    else:
        print("Reviewer 审核能力需进一步调优。")
    print("=" * 65)

    return result


if __name__ == "__main__":
    test_reviewer_catches_errors()
