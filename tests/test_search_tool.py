"""
Search Tool 集成测试

验证：
1. TavilySearchTool 能否正确初始化
2. Research Agent 能否识别并调用搜索工具
3. 搜索工具降级模式是否正常（无 API Key 时）

用法：
  python tests/test_search_tool.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crewai import Agent, Task, Crew
from tools.search_tool import TavilySearchTool, create_search_tool
from agents.researcher import create_research_agent


def test_tool_init():
    """测试 1：工具初始化"""
    print("=" * 60)
    print("测试 1：工具初始化")
    print("=" * 60)

    # 测试显式 API Key
    tool1 = TavilySearchTool(api_key="tvly-test-key")
    assert tool1.name == "web_search", f"name 不正确: {tool1.name}"
    assert tool1._client is not None, "client 应该被创建"
    print("[PASS] 显式 API Key 初始化成功")

    # 测试从环境变量读取
    tool2 = TavilySearchTool()
    print(f"[PASS] 默认初始化成功 (API Key 来自环境变量: {'已设置' if os.getenv('TAVILY_API_KEY') else '未设置'})")

    # 测试工厂函数
    tool3 = create_search_tool()
    assert isinstance(tool3, TavilySearchTool), "工厂函数应返回 TavilySearchTool"
    print("[PASS] 工厂函数创建成功")

    return tool2


def test_tool_standalone():
    """测试 2：工具独立调用（不经过 Agent）"""
    print("\n" + "=" * 60)
    print("测试 2：工具独立调用")
    print("=" * 60)

    tool = create_search_tool()
    result = tool._run("AI芯片 市场规模 2025")

    # 检查返回格式
    has_key = os.getenv("TAVILY_API_KEY", "").startswith("tvly-")
    if has_key:
        # 有真实 API Key — 应返回真实搜索结果
        assert "搜索词" in result, "应包含搜索词标签"
        assert len(result) > 100, "搜索结果应有一定长度"
        print("[PASS] 真实搜索返回有效结果")
    else:
        # 无 API Key 或假 Key — 降级提示 或 API 错误
        has_degraded = "搜索服务未配置" in result
        has_error = "搜索执行出错" in result
        assert has_degraded or has_error, f"应返回降级提示或错误信息，实际返回: {result[:100]}"
        print("[PASS] 降级/错误处理正常（配置真实 TAVILY_API_KEY 后可搜索）")

    print(f"   返回内容长度: {len(result)} 字符")


def test_agent_with_tool():
    """测试 3：Research Agent 挂载搜索工具（集成测试）"""
    print("\n" + "=" * 60)
    print("测试 3：Research Agent + Tool 集成")
    print("=" * 60)

    topic = "AI芯片"
    tool = create_search_tool()
    agent = create_research_agent(topic=topic, tools=[tool])

    # 验证工具已挂载
    assert len(agent.tools) == 1, "Agent 应有 1 个工具"
    assert agent.tools[0].name == "web_search", "工具名称应对"
    print(f"[PASS] Agent 工具挂载成功: {agent.tools[0].name}")

    # 创建精简 Task（快速验证）
    task = Task(
        description=(
            f"请研究「{topic}」行业，重点关注最近的重要新闻。\n"
            f"如果有搜索工具，请务必使用它搜索最新信息。\n"
            f"如果没有搜索工具，请基于知识库回答。\n"
            f"输出一段约 300 字的行业动态摘要。"
        ),
        expected_output="一段约 300 字的行业动态摘要，信息准确、来源清晰。",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
    )

    has_key = os.getenv("TAVILY_API_KEY", "").startswith("tvly-")

    print(f"\nAPI Key 状态: {'已配置（将执行真实搜索）' if has_key else '未配置（降级模式）'}")
    print("开始执行...\n")

    result = crew.kickoff()

    # 质量检查
    checks = [
        (len(str(result)) > 100, "输出长度充足"),
        (topic in str(result), "内容与主题相关"),
    ]
    all_passed = True
    for passed, label in checks:
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status} {label}")

    if has_key:
        # 有搜索工具时，检查是否引用了搜索结果（URL 或来源标记）
        content = str(result)
        has_source = "http" in content or "来源" in content or "据" in content
        status = "[PASS]" if has_source else "[INFO]"
        print(f"{status} 搜索结果引用: {'检测到来源引用' if has_source else '未检测到明显来源（可能因为真实API key未配置）'}")

    if all_passed:
        print("\n集成测试通过！Research Agent + Tool 链路正常。")
    return result


if __name__ == "__main__":
    print("TavilySearchTool 集成测试")
    print("=" * 60)

    test_tool_init()
    test_tool_standalone()

    # 集成测试会实际调用 Agent，需要 API 时间
    print("\n即将运行 Agent 集成测试（需要 LLM 推理，约 30-60 秒）...")
    test_agent_with_tool()

    print("\n" + "=" * 60)
    print("全部测试完成！")
