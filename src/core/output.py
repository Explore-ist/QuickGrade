"""
--+--output
  +--输出脚本  v2.1  （成绩导表 + 自动“标分上图”）
===================================================================
1. **成绩导表** (`export_excel`) —— 与 v1.8 相同，默认仅导出大题列，`EXPORT_SUBS=True` 可含小题。
2. **自动标分 & 批注写图** (`save_all_marked_images`)
   * 读取 `src/data/configs/default.json`（若有 `questions.json` 优先）的大题/小题坐标。
   * 读取 `result.json` 的 `scores` 矩阵 → 每题 / 小题得分。
   * 在 `src/data/stitched/1.png、2.png…` 原卷上：
       - 用红框圈出大题区块，并在左上角写“大题总分”。
       - 在每个小题框左上角写对应得分（绿色）。
   * 叠加手工自由曲线记号：`result.json['marks']` 中的 `"stu|q|sub"` → 点集数组。
   * 输出至 `src/data/save/{学生序号}_{原文件名}`，目录自动创建。

依赖：pandas、openpyxl、opencv-python、numpy
===================================================================
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
import pandas as pd

from path import CONFIGS_PATH, RESULTS_PATH, DATA_PATH, STUDENTS_PATH, STITCHED_PATH, WORK_PATH

# -------------------------------------------------- 常量 --------------------------------------------------
RESULT_JSON = Path(CONFIGS_PATH) / "result.json"
RESULT_XLSX = Path(RESULTS_PATH) / "result.xlsx"
SAVE_DIR = Path(DATA_PATH) / "save"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

_RED = (0, 0, 255)     # BGR
_GREEN = (0, 255, 0)
_BLUE = (255, 0, 0)
_THICK = 2
_FONT = cv2.FONT_HERSHEY_SIMPLEX

EXPORT_SUBS = False  # True → Excel 里包含小题列

# -------------------------------------------------- 工具 --------------------------------------------------

def _pretty_path(p: Path) -> str:
    for base in (WORK_PATH, Path.cwd()):
        try:
            return str(p.relative_to(base))
        except ValueError:
            continue
    return str(p)


def _nat_key(seg: str):
    return int(seg) if seg.isdigit() else seg


def _natural_sort(cols: List[str]) -> List[str]:
    others = [c for c in cols if c not in ("学生", "总分")]
    others.sort(key=lambda x: tuple(_nat_key(s) for s in x.split('.')))
    return ["学生"] + others + (["总分"] if "总分" in cols else [])

# -------------------------------------------------- JSON 读取 --------------------------------------------------

def _load_result_raw() -> Dict[str, Any]:
    if not RESULT_JSON.exists():
        raise FileNotFoundError("未找到 result.json！请先运行批改流程。")
    with open(RESULT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _from_matrix(obj: Dict[str, Any]) -> List[Dict]:
    mat: List[List[List[Any]]] = obj.get("scores", [])
    total_q: int = obj.get("total_questions", 0)
    res: List[Dict] = []
    for s_idx, stu_q_scores in enumerate(mat, 1):
        scores_flat: Dict[str, float] = {}
        for q_idx in range(total_q):
            subs = stu_q_scores[q_idx] if q_idx < len(stu_q_scores) else []
            if not isinstance(subs, list):
                subs = []
            big_id = str(q_idx + 1)
            scores_flat[big_id] = sum(subs)
            for sub_idx, val in enumerate(subs, 1):
                scores_flat[f"{big_id}.{sub_idx}"] = val
        res.append({"student": f"学生{s_idx}", "scores": scores_flat})
    return res


def _load_result_for_excel() -> List[Dict]:
    raw = _load_result_raw()
    if "scores" in raw and isinstance(raw["scores"], list):
        return _from_matrix(raw)
    raise ValueError("当前版本仅支持批改流程导出的矩阵格式 result.json！")

# -------------------------------------------------- Excel 导出 --------------------------------------------------

def export_excel():
    rows = []
    for stu in _load_result_for_excel():
        row = {"学生": stu["student"]}
        for k, v in stu["scores"].items():
            if not EXPORT_SUBS and "." in k:
                continue
            row[k] = v
        row["总分"] = sum(v for k, v in row.items() if k.isdigit())
        rows.append(row)

    cols = _natural_sort(list({c for r in rows for c in r}))
    df = pd.DataFrame(rows)[cols]
    RESULT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(RESULT_XLSX, sheet_name="Sheet1", index=False)
    print("✔ 成绩表已导出 →", _pretty_path(RESULT_XLSX))

# -------------------------------------------------- 题目坐标 --------------------------------------------------

def _load_questions_cfg() -> Dict[str, Any]:
    cfg_file = Path(CONFIGS_PATH, "questions.json") if Path(CONFIGS_PATH, "questions.json").exists() else Path(CONFIGS_PATH, "default.json")
    with open(cfg_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(q["id"]): q for q in data["questions"]}

# -------------------------------------------------- 图片 I/O --------------------------------------------------

def _read_stitched(stu_idx: int) -> Tuple[np.ndarray, Path]:
    base = Path(STITCHED_PATH, f"{stu_idx+1}")
    for ext in (".png", ".jpg", ".jpeg", ".bmp"):
        p = base.with_suffix(ext)
        if p.exists():
            img = cv2.imread(str(p))
            return img, p
    raise FileNotFoundError(f"未找到学生卷面：{base}.[png/jpg/jpeg/bmp]")

# -------------------------------------------------- 批注绘制 --------------------------------------------------

def _draw_scores(img: np.ndarray, q_cfg: Dict, scores: List[Any]):
    big_total = sum(scores)
    # 大题块
    for seg in q_cfg.get("segments", []):
        x, y, w, h = seg
        cv2.rectangle(img, (x, y), (x + w, y + h), _RED, _THICK)
        cv2.putText(img, str(big_total), (x + 5, y + 30), _FONT, 1.0, _GREEN, 2)
    # 小题
    for sub_idx, sub_cfg in enumerate(q_cfg.get("subs", []), 1):
        if sub_idx > len(scores):
            break
        val = scores[sub_idx - 1]
        for seg in sub_cfg.get("segments", []):
            x, y, w, h = seg
            cv2.putText(img, str(val), (x + 5, y + 25), _FONT, 0.8, _GREEN, 2)


def _draw_polyline(img: np.ndarray, pts: List[List[int]]):
    if len(pts) < 2:
        return
    arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
    cv2.polylines(img, [arr], isClosed=False, color=_BLUE, thickness=_THICK)

# -------------------------------------------------- 主批注函数 --------------------------------------------------

def save_all_marked_images():
    raw = _load_result_raw()
    scores_mat: List[List[List[Any]]] = raw["scores"]
    marks_dict: Dict[str, Any] = raw.get("marks", {})
    q_map = _load_questions_cfg()

    total_students = len(scores_mat)
    for stu_idx in range(total_students):
        try:
            img, src_path = _read_stitched(stu_idx)
        except FileNotFoundError as e:
            print("⚠", e)
            continue

        # ---- 自动标分 ----
        for q_idx, q_scores in enumerate(scores_mat[stu_idx]):
            q_cfg = q_map.get(str(q_idx + 1))
            if q_cfg:
                _draw_scores(img, q_cfg, q_scores)

        # ---- 叠加手工 marks ----
        for key, strokes in marks_dict.items():
            try:
                s, q, sub = map(int, key.split("|"))
            except ValueError:
                continue
            if s != stu_idx:
                continue
            for stroke in strokes:
                _draw_polyline(img, stroke)

        # ---- 保存 ----
        dst = SAVE_DIR / f"{stu_idx+1}_{src_path.name}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dst), img)
        print("✔ 批注图已保存 →", _pretty_path(dst))

# -------------------------------------------------- CLI --------------------------------------------------
if __name__ == "__main__":
    export_excel()
    save_all_marked_images()
