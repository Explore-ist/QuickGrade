#!/usr/bin/env python3
"""
QuickGrade 主入口（src/main.py）
================================================
运行方式：
    python main.py [command]

如果不带参数，默认直接启动批改界面（teacher）。

可用子命令：
  stitch   —— 将正/反面等『页』文件夹纵向拼接成 stitched/ 学生整卷
  define   —— 交互式划分大题 / 小题区域并生成 data/configs/default.json
  teacher  —— 启动批改 UI（核心改卷程序）
  export   —— 读取 result.json 导出成绩表（Excel）
  mark     —— 把总分 / 小题分与批注写回图片，输出到 data/save/
  all      —— 按顺序依次执行 stitch → teacher → export → mark

依赖：见 core/path.py 中的技术栈说明。
"""

import argparse
import runpy
import sys
from pathlib import Path

# ------------------------------------------------------------------
#  确保可以 import core —— src 与 core 同级，故直接把 src 加入 PYTHONPATH
# ------------------------------------------------------------------
CUR_DIR = Path(__file__).resolve().parent
if str(CUR_DIR) not in sys.path:
    sys.path.insert(0, str(CUR_DIR))

# ------------------------ 核心对象 / 函数 -------------------------
from core import Redistricting, StudentProcessing, Teacher  # type: ignore
from core.output import export_excel, save_all_marked_images  # type: ignore

# ------------------------ 子命令实现 -----------------------------

def _cmd_stitch() -> None:
    """运行 core.stitched 脚本，生成 stitched/ 下的整卷图片"""
    runpy.run_module("core.stitched", run_name="__main__")


def _cmd_define() -> None:
    """交互式划分题目区域并保存为 default.json"""
    red = Redistricting()          # 自动在 stitched/ 中找首张图
    questions = red.run()          # 手动框选大/小题
    StudentProcessing(questions, config_name="default.json").save()


def _cmd_teacher() -> None:
    """启动核心批改 UI（手打 / 判分）"""
    Teacher().run()


def _cmd_export() -> None:
    """将 result.json 中的成绩导出为 Excel"""
    export_excel()


def _cmd_mark() -> None:
    """在原卷上写入分数 / 批注，输出到 data/save/"""
    save_all_marked_images()


def _cmd_all() -> None:
    """全流程：拼接 → 批改 → 导表 → 批注写图"""
    _cmd_stitch()
    _cmd_teacher()
    _cmd_export()
    _cmd_mark()

# ------------------------ CLI 入口 -------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="QuickGrade",
        description="QuickGrade 项目统一入口 (src/main.py)",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="teacher",
        choices=["stitch", "define", "teacher", "export", "mark", "all"],
        help="要执行的操作 (默认: teacher)",
    )
    args = parser.parse_args()

    dispatch = {
        "stitch": _cmd_stitch,
        "define": _cmd_define,
        "teacher": _cmd_teacher,
        "export": _cmd_export,
        "mark": _cmd_mark,
        "all": _cmd_all,
    }

    dispatch[args.command]()


if __name__ == "__main__":
    main()
