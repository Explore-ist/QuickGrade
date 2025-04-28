"""
--+--output
  +--输出脚本 (升级版 v1.8)
------------------------------------------------------
### 修正
* **修复 `DataFrame` 对象被错误调用**（多余 `(rows)[all_cols]`）。
* **整理 `export_excel()` 逻辑**，去掉重复代码、修正缩进。
* 默认仍只导出大题列；如需小题改 `EXPORT_SUBS = True`。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import pandas as pd

from path import CONFIGS_PATH, RESULTS_PATH, DATA_PATH, STUDENTS_PATH, WORK_PATH

RESULT_JSON = Path(CONFIGS_PATH) / "result.json"
RESULT_XLSX = Path(RESULTS_PATH) / "result.xlsx"
SAVE_DIR = Path(DATA_PATH) / "save"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# 数据加载与归一化
# --------------------------------------------------

def _from_matrix(obj: Dict[str, Any]) -> List[Dict]:
    scores_mat: List[List[List[Any]]] = obj.get("scores", [])
    total_q: int = obj.get("total_questions", 0)
    students: List[Dict] = []
    for s_idx, stu_q_scores in enumerate(scores_mat, start=1):
        scores_flat: Dict[str, float] = {}
        for q_idx in range(total_q):
            subs = stu_q_scores[q_idx] if q_idx < len(stu_q_scores) else []
            if not isinstance(subs, list):
                subs = []
            big_id = str(q_idx + 1)
            for sub_idx, val in enumerate(subs, start=1):
                scores_flat[f"{big_id}.{sub_idx}"] = val
            scores_flat[big_id] = sum(subs)
        students.append({"student": f"学生{s_idx}", "scores": scores_flat, "marks": []})
    return students


def _normalize_entry(name: str, entry: Any) -> Dict:
    if isinstance(entry, dict):
        student = entry.get("student", name) or name
        scores = {str(k): v for k, v in entry.get("scores", entry).items() if isinstance(v, (int, float, dict))}
        marks = entry.get("marks", [])
    else:
        student = name
        scores = {str(k): v for k, v in (entry if isinstance(entry, dict) else {}).items()}
        marks = []
    return {"student": student, "scores": scores, "marks": marks}


def _load_result() -> List[Dict]:
    if not RESULT_JSON.exists():
        raise FileNotFoundError(f"找不到 {RESULT_JSON}")
    with open(RESULT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("scores"), list):
        return _from_matrix(data)
    if isinstance(data, list):
        return [_normalize_entry(f"stu{i+1}", itm) for i, itm in enumerate(data)]
    if isinstance(data, dict):
        return [_normalize_entry(name, itm) for name, itm in data.items()]
    raise ValueError("result.json 格式无法识别！")

# --------------------------------------------------
# 工具函数
# --------------------------------------------------

def _pretty_path(p: Path) -> str:
    for base in (WORK_PATH, Path.cwd()):
        try:
            return str(p.relative_to(base))
        except ValueError:
            continue
    return str(p)


def _nat_key_seg(seg: str):
    return int(seg) if seg.isdigit() else seg


def _natural_sort(cols: List[str]) -> List[str]:
    others = [c for c in cols if c not in ("学生", "总分")]
    others.sort(key=lambda c: tuple(_nat_key_seg(s) for s in c.split('.')))
    result = ["学生"] + others + (["总分"] if "总分" in cols else [])
    return result

# --------------------------------------------------
# Excel 导出
# --------------------------------------------------

EXPORT_SUBS = False  # 改成 True 可导出小题列


def _is_sub(col: str) -> bool:
    return '.' in col


def export_excel():
    data = _load_result()

    # ---- 构建行 ----
    rows: List[Dict[str, Any]] = []
    for stu in data:
        row: Dict[str, Any] = {"学生": stu["student"]}
        for k, v in stu["scores"].items():
            if not EXPORT_SUBS and _is_sub(k):
                continue
            row[k] = v
        row["总分"] = sum(val for key, val in row.items() if key.isdigit())
        rows.append(row)

    # ---- 计算列顺序 ----
    col_set = {c for r in rows for c in r}
    if not EXPORT_SUBS:
        col_set = {c for c in col_set if not _is_sub(c) or c in ("学生", "总分")}
    all_cols = _natural_sort(list(col_set))

    # ---- 写 Excel ----
    df = pd.DataFrame(rows)[all_cols]
    RESULT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(RESULT_XLSX, sheet_name="Sheet1", index=False)
    print(f"✔ 成绩已导出 → {_pretty_path(RESULT_XLSX)}")

# --------------------------------------------------
# 批注写图（增强实现）
# --------------------------------------------------

_RED = (0, 0, 255)
_GREEN = (0, 255, 0)
_THICK = 2


def _draw_marks(img: np.ndarray, marks: List[Dict]):
    """根据 marks 列表在 img 上作图。支持 rect / point / text / polyline。"""
    for m in marks:
        tp = m.get("type", "rect")
        if tp == "rect":
            x, y, w, h = m["xywh"]
            cv2.rectangle(img, (x, y), (x + w, y + h), _RED, _THICK)
        elif tp == "point":
            x, y = m["xy"]
            cv2.circle(img, (x, y), 6, _GREEN, -1)
        elif tp == "text":
            x, y = m["xy"]
            cv2.putText(img, m.get("content", "√"), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, _RED, 2)
        elif tp == "polyline":  # 自由曲线
            pts = np.array(m["points"], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [pts], isClosed=False, color=_GREEN, thickness=_THICK)
        else:
            print(f"⚠ 未知记号类型：{tp}")


def _iter_image_marks(stu_marks: List[Any]):
    """兼容两种格式：
    1. [{"img":"...","marks":[...]}, ...]
    2. [{"img":"...","type":"rect",...}, ...]  # 全部同一张图
    """
    if not stu_marks:
        return
    # 情况 1：每项都带 marks 列表
    if all(isinstance(it, dict) and "marks" in it for it in stu_marks):
        for itm in stu_marks:
            yield itm["img"], itm["marks"]
    else:
        # 情况 2：把所有标注视为同一个文件（必须每条都带 img）
        by_img: Dict[str, List] = {}
        for m in stu_marks:
            img_path = m.get("img")
            if not img_path:
                continue
            by_img.setdefault(img_path, []).append(m)
        for img_path, marks in by_img.items():
            yield img_path, marks


def save_all_marked_images():
    data = _load_result()
    for stu in data:
        for rel_img_path, marks in _iter_image_marks(stu.get("marks", [])):
            src = Path(STUDENTS_PATH) / rel_img_path
            img = cv2.imread(str(src))
            if img is None:
                print(f"⚠ 无法读取 {src}")
                continue
            _draw_marks(img, marks)
            dst_name = f"{stu['student']}_{src.name}"
            dst = SAVE_DIR / dst_name
            dst.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(dst), img)
            print(f"✔ 批注已写入 → {_pretty_path(dst)}")

# --------------------------------------------------
if __name__ == "__main__":
    export_excel()
    save_all_marked_images()
