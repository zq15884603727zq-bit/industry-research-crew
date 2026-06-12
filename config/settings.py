"""
集中管理所有配置：LLM 实例、模型参数、路径常量。

所有 Agent 共用同一个 LLM 实例，避免重复初始化。
修改模型或参数只需改这一个文件。

环境变量加载策略（3 级回退）：
  1. 如果 DEEPSEEK_API_KEY 已在系统中，直接使用（如 export 设置的）
  2. 尝试 find_dotenv() 自动搜索 .env
  3. 回退到基于 __file__ 的显式路径（可能因中文路径转码失败）
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from crewai import LLM


# ── 1. 加载环境变量（3 级回退） ──────────────────────────
if not os.getenv("DEEPSEEK_API_KEY"):
    # 级别 1：自动搜索（在模块导入路径正常时有效）
    env_path = find_dotenv(usecwd=True)

    # 级别 2：基于 __file__ 的显式路径
    if not env_path or not os.path.exists(env_path):
        env_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", ".env"
        )

    # 级别 3：基于 sys.argv[0] 的入口脚本路径
    if not os.path.exists(env_path) and sys.argv[0]:
        env_path = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), ".env"
        )

    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print(
            "⚠️  未找到 .env 文件，请通过 export DEEPSEEK_API_KEY=xxx 设置环境变量"
        )

# ── 2. 路径常量 ──────────────────────────────────────────
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 3. DeepSeek LLM 实例（全局唯一） ──────────────────────
#    temperature=0.3：保证输出有一定创造性但不偏离主题
#    max_tokens=4096：单次输出上限，留给 Agent 足够的表达空间
llm = LLM(
    model="deepseek/deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.3,
    max_tokens=4096,
)
