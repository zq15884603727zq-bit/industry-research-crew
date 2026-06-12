"""
行业研究助手 — 基于 CrewAI 的多 Agent 行业研究系统

用法：
    python main.py "AI芯片"                          # 基础研究
    python main.py "AI芯片" --format docx            # 导出 Word
    python main.py "AI芯片" --format all             # 导出所有格式
    python main.py --history "新能源汽车"            # 搜索历史报告
    python main.py --list                            # 列出所有历史报告
    python main.py --topic "光伏产业" --quiet         # 静默模式
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── 确保项目根目录在 sys.path 中 ─────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewai import Crew, Process

from config.settings import OUTPUT_DIR
from agents.researcher import create_research_agent
from agents.analyst import create_analyst_agent
from agents.writer import create_writer_agent
from agents.reviewer import create_reviewer_agent
from tasks.research_task import create_research_task
from tasks.analysis_task import create_analysis_task
from tasks.writing_task import create_writing_task
from tasks.review_task import create_review_task
from tools.bocha_search_tool import create_bocha_search_tool as create_search_tool


def _safe_pause():
    """安全暂停——兼容交互终端和管道输入场景。"""
    try:
        input("\n按 Enter 键退出...")
    except (EOFError, KeyboardInterrupt):
        print()


def _gui_format_picker() -> str:
    """
    弹出格式选择窗口（3 级回退）。

    级别 1：Windows 原生 MessageBox（最可靠，双击场景下不会闪退）
    级别 2：tkinter GUI（跨平台，有按钮更直观）
    级别 3：终端 input()（纯文本，兼容性最好）

    Returns:
        "md" | "docx" | "pdf" | "html" | "all" | "cancel"
        "cancel" 表示用户不想导出，直接退出
    """
    # ── 级别 1: Windows 原生对话框 ──────────────────────
    try:
        import ctypes
        result = ctypes.windll.user32.MessageBoxW(
            0,
            "报告已生成！Markdown 原稿已自动保存。\n\n"
            "是 → 导出 Word 文档 (.docx) ★ 推荐\n"
            "否 → 仅保留 Markdown (.md)\n"
            "取消 → 不导出，直接退出",
            "行业研究助手 — 选择导出格式",
            3 + 32  # MB_YESNOCANCEL + MB_ICONQUESTION
        )
        fmt_map = {
            6: "docx",   # IDYES
            7: "md",     # IDNO
            2: "cancel", # IDCANCEL → 取消
        }
        choice = fmt_map.get(result, "docx")
        print(f"\n   已选择: {choice}")
        return choice
    except Exception:
        pass

    # ── 级别 2: tkinter GUI ──────────────────────────────
    try:
        import tkinter as tk
        from tkinter import ttk

        result = {"fmt": "cancel"}  # 默认取消（点 X 关闭窗口时）

        def on_select(fmt):
            result["fmt"] = fmt
            root.destroy()

        # 窗口关闭 = 取消
        def on_close():
            root.destroy()

        root = tk.Tk()
        root.title("行业研究助手 — 选择导出格式")
        root.geometry("460x380")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", on_close)
        root.update_idletasks()
        x = (root.winfo_screenwidth() - 460) // 2
        y = (root.winfo_screenheight() - 380) // 2
        root.geometry(f"+{x}+{y}")

        tk.Label(
            root, text="报告已生成！请选择导出格式",
            font=("Microsoft YaHei", 13, "bold"), pady=16,
        ).pack()
        tk.Label(
            root, text="Markdown 原稿已自动保存，选择额外导出格式",
            font=("Microsoft YaHei", 9), fg="#666",
        ).pack()

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=12)

        options = [
            ("Markdown (.md)", "md", "在线预览 / GitHub"),
            ("Word (.docx) ★", "docx", "提交 / 打印 / 编辑"),
            ("PDF (.pdf)", "pdf", "正式交付"),
            ("HTML (.html)", "html", "浏览器打开"),
            ("全部格式", "all", "一键生成以上所有"),
        ]
        for label, fmt, hint in options:
            row = tk.Frame(btn_frame)
            row.pack(fill="x", pady=3)
            ttk.Button(
                row, text=label, width=20,
                command=lambda f=fmt: on_select(f),
            ).pack(side="left", padx=(24, 8))
            tk.Label(row, text=hint, font=("Microsoft YaHei", 8), fg="#999").pack(side="left")

        # 取消按钮
        cancel_frame = tk.Frame(root)
        cancel_frame.pack(pady=10)
        ttk.Button(
            cancel_frame, text="取消，不导出", width=20,
            command=lambda: on_select("cancel"),
        ).pack()

        tk.Label(
            root,
            text="关闭窗口或点击「取消」则仅保留 MD 原稿\npython main.py --list 可查看历史",
            font=("Microsoft YaHei", 8), fg="#aaa", pady=8,
        ).pack(side="bottom")

        root.focus_force()
        root.mainloop()
        print(f"\n   已选择导出格式: {result['fmt']}")
        return result["fmt"]
    except Exception:
        pass

    # ── 级别 3: 终端输入 ─────────────────────────────────
    print("\n  Markdown 原稿已自动保存。请选择额外导出格式：")
    print("    [1] Markdown  [2] Word (推荐)  [3] PDF  [4] HTML  [5] 全部")
    print("    [0] 取消，不导出")
    try:
        choice = input("  输入选项 [0-5]（默认 2）> ").strip()
        fmt_map = {"0": "cancel", "1": "md", "2": "docx", "3": "pdf", "4": "html", "5": "all"}
        return fmt_map.get(choice, "docx")
    except (EOFError, KeyboardInterrupt):
        return "cancel"


# ═══════════════════════════════════════════════════════
# 核心 Pipeline
# ═══════════════════════════════════════════════════════

def run_pipeline(topic: str, verbose: bool = True) -> str:
    """运行完整的行业研究 Pipeline。"""

    print(f"\n{'='*60}")
    print(f"  行业研究助手 — 多 Agent 协作系统")
    print(f"  研究主题：{topic}")
    print(f"  启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    print("[1/5] 初始化 Agent 团队...")
    search_tool = create_search_tool()
    researcher = create_research_agent(topic=topic, tools=[search_tool])
    analyst = create_analyst_agent()
    writer = create_writer_agent()
    reviewer = create_reviewer_agent()
    print(f"   Researcher : {researcher.role}")
    print(f"   Analyst    : {analyst.role}")
    print(f"   Writer     : {writer.role}")
    print(f"   Reviewer   : {reviewer.role}")

    print("\n[2/5] 创建任务链...")
    research_task = create_research_task(researcher, topic)
    analysis_task = create_analysis_task(analyst, research_task)
    writing_task = create_writing_task(writer, analysis_task)
    review_task = create_review_task(reviewer, writing_task)
    print(f"   research_task → analysis_task → writing_task → review_task")
    print(f"   context 链已建立，数据将自动流转")

    print("\n[3/5] 组装 Crew（顺序执行模式）...")
    crew = Crew(
        agents=[researcher, analyst, writer, reviewer],
        tasks=[research_task, analysis_task, writing_task, review_task],
        process=Process.sequential,
        verbose=verbose,
    )

    print("\n[4/5] 开始执行研究 Pipeline...")
    print("-" * 60)
    print("阶段：资料搜集 → 信息分析 → 报告撰写 → 审核修订")
    print("-" * 60)

    result = crew.kickoff()

    print("\n[5/5] 保存报告...")
    return str(result)


def save_report(content: str, topic: str, output_path: str = None) -> Path:
    """保存 Markdown 报告到 output/ 目录。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_path:
        filepath = Path(output_path)
    else:
        safe_topic = topic.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = OUTPUT_DIR / f"{safe_topic}_{timestamp}.md"

    filepath.write_text(content, encoding="utf-8")
    return filepath


# ═══════════════════════════════════════════════════════
# 新增：导出 & 记忆
# ═══════════════════════════════════════════════════════

def handle_export(report: str, topic: str, fmt: str):
    """处理报告导出"""
    from utils.exporter import export_report
    print(f"\n  导出格式: {fmt}")
    export_report(report, topic, fmt=fmt)


def handle_memory_save(report: str, topic: str, filepath: Path):
    """将报告存入记忆库"""
    try:
        from utils.memory import get_memory
        memory = get_memory()
        memory.add_report(topic=topic, content=report, filepath=str(filepath))
    except Exception as e:
        print(f"   ⚠️  记忆存储失败: {e}")


def handle_memory_check(topic: str):
    """检查是否有相似历史报告"""
    try:
        from utils.memory import get_memory
        memory = get_memory()
        similar = memory.search_similar_topics(topic, n_results=3)
        if similar:
            print(f"\n   📚 发现 {len(similar)} 份相似历史报告:")
            for r in similar:
                print(f"      - {r['topic']} ({r['created_at'][:10]})")
            print(f"   💡 将继续执行新研究，历史报告可作为参考。")
    except Exception:
        pass  # 记忆检查失败不影响主流程


def handle_history(query: str):
    """搜索历史报告"""
    try:
        from utils.memory import get_memory
        memory = get_memory()
        results = memory.search(query, n_results=5)
        stats = memory.get_stats()

        print(f"\n{'='*60}")
        print(f"  记忆库搜索: {query}")
        print(f"  记忆库总量: {stats['total_reports']} 份报告")
        print(f"{'='*60}\n")

        if results:
            for i, r in enumerate(results, 1):
                print(f"  {i}. [{r['topic']}]  {r['created_at'][:10]}")
                print(f"     {r['content_preview'][:120]}...")
                print()
        else:
            print("  未找到相关报告。")

        _safe_pause()
    except Exception as e:
        print(f"  搜索失败: {e}")
        _safe_pause()


def handle_list():
    """列出所有历史报告"""
    try:
        from utils.memory import get_memory
        memory = get_memory()
        reports = memory.list_reports()
        stats = memory.get_stats()

        print(f"\n{'='*60}")
        print(f"  记忆库 — 历史报告列表")
        print(f"  总计: {stats['total_reports']} 份报告")
        print(f"{'='*60}\n")

        if reports:
            for i, r in enumerate(reports, 1):
                print(f"  {i}. [{r['topic']}]")
                print(f"     日期: {r['created_at'][:10]} | "
                      f"长度: {r.get('content_length', 0):,} 字符")
                if r.get('filepath'):
                    print(f"     文件: {r['filepath']}")
                print()
        else:
            print("  记忆库为空。运行一次研究即可自动存入。")

        _safe_pause()
    except Exception as e:
        print(f"  获取列表失败: {e}")
        _safe_pause()


# ═══════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="行业研究助手 — 基于 CrewAI 的多 Agent 行业研究系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "AI芯片"                         # 研究 + MD 导出
  python main.py "AI芯片" --format docx           # 研究 + Word 导出
  python main.py "AI芯片" --format all            # 研究 + 全格式导出
  python main.py --history "市场规模"             # 搜索历史报告
  python main.py --list                           # 列出所有历史报告
        """,
    )
    parser.add_argument(
        "topic", nargs="?",
        help="研究主题（如 'AI芯片'、'新能源汽车'）",
    )
    parser.add_argument(
        "--topic", "-t", dest="topic_named",
        help="研究主题（命名参数形式）",
    )
    parser.add_argument(
        "--output", "-o",
        help="自定义输出文件路径",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["md", "docx", "html", "pdf", "all"],
        default="md",
        help="导出格式（默认 md）",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="减少详细日志输出",
    )
    parser.add_argument(
        "--history",
        metavar="QUERY",
        help="搜索历史报告（不执行新研究）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有历史报告（不执行新研究）",
    )

    args = parser.parse_args()

    # ── 模式 1: 搜索历史 ──────────────────────────────
    if args.history:
        handle_history(args.history)
        return

    # ── 模式 2: 列出历史 ──────────────────────────────
    if args.list:
        handle_list()
        return

    # ── 模式 3: 研究模式（默认） ──────────────────────
    topic = args.topic or args.topic_named

    # 交互模式（双击打开）
    is_interactive = False
    if not topic:
        is_interactive = True
        print("=" * 60)
        print("  行业研究助手 — 基于 CrewAI 的多 Agent 行业研究系统")
        print("=" * 60)
        print()
        print("  命令行用法：")
        print("    python main.py \"AI芯片\" --format docx")
        print("    python main.py --history \"市场规模\"")
        print("    python main.py --list")
        print()
        print("  或在下方直接输入研究主题：")
        print()
        try:
            topic = input("  请输入研究主题 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            _safe_pause()
            sys.exit(0)

        if not topic:
            print("未输入主题，已取消。")
            _safe_pause()
            sys.exit(0)

        # 交互模式：先跑 Pipeline，报告生成后用 GUI 弹窗选格式
        quiet = False
        export_fmt = "__gui__"   # 标记：稍后弹出 GUI 选择
    else:
        quiet = args.quiet
        export_fmt = args.format

    # 检查历史记忆
    handle_memory_check(topic)

    # 运行 Pipeline
    try:
        report = run_pipeline(topic=topic, verbose=not quiet)
    except KeyboardInterrupt:
        print("\n\n用户中断。")
        _safe_pause()
        sys.exit(0)
    except Exception as e:
        print(f"\n执行出错: {e}")
        import traceback
        traceback.print_exc()
        _safe_pause()
        sys.exit(1)

    # 保存 Markdown
    md_path = save_report(report, topic, args.output)

    # 导出其他格式
    if export_fmt == "__gui__":
        # 交互模式：弹出 GUI 格式选择框
        try:
            export_fmt = _gui_format_picker()
        except Exception as e:
            print(f"\n   ⚠️  GUI 弹窗失败: {e}")
            print(f"   自动回退为 Word 导出...")
            export_fmt = "docx"

        if export_fmt == "cancel":
            print(f"\n   ⏭️  已取消格式导出，仅保留 Markdown 原稿。")
        else:
            handle_export(report, topic, fmt=export_fmt)
    elif export_fmt != "md":
        handle_export(report, topic, fmt=export_fmt)

    # 存入记忆
    handle_memory_save(report, topic, md_path)

    # 输出摘要
    print(f"\n{'='*60}")
    print(f"  Markdown 报告: {md_path}")
    _print_output_files(md_path)
    print(f"  报告长度: {len(report):,} 字符")
    print(f"  完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 交互模式：自动打开 output 文件夹
    if is_interactive:
        _open_output_folder(md_path.parent)
        _safe_pause()

    return report


def _print_output_files(md_path: Path):
    """列出 output 目录下同时生成的所有关联文件"""
    stem = md_path.stem
    parent = md_path.parent
    related = sorted(parent.glob(f"{stem}.*"))
    if len(related) > 1:
        print(f"  生成文件:")
        for f in related:
            ext = f.suffix.upper()
            size = f.stat().st_size
            size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
            print(f"    {ext:5s}  {size_str:>10s}  {f.name}")


def _open_output_folder(folder: Path):
    """在文件管理器中打开 output 文件夹"""
    import platform
    try:
        if platform.system() == "Windows":
            import os
            os.startfile(str(folder))
        elif platform.system() == "Darwin":
            import subprocess
            subprocess.run(["open", str(folder)])
        else:
            import subprocess
            subprocess.run(["xdg-open", str(folder)])
        print(f"\n  已打开文件夹: {folder}")
    except Exception as e:
        print(f"\n  报告文件夹: {folder}")


if __name__ == "__main__":
    main()
