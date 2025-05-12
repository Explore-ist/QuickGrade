# -*- coding: utf-8 -*-
"""
改卷主程 ‑ Freehand 记号版
========================================
**新增功能**
🔹 记号从“直线”升级为**自由曲线**：左键按住拖动即实时绘制，抬起鼠标结束一条曲线；右键撤销最近一条曲线。
🔹 曲线数据以点集形式保存 `[(x1,y1), (x2,y2), ...]`，后续可精确复现。
🔹 Ctrl+滚轮缩放、题‑小题‑学生遍历、多位分数输入等既有功能保持不变。

依赖：OpenCV‑Python ≥4.6、NumPy、dataclasses（Py3.7+ 标准库）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from path import CONFIGS_PATH, STITCHED_PATH
from input import StudentProcessing, Question, SubQuestion, Region


class Teacher:
    WIN = "question"

    def __init__(self):
        # ---------- 载入配置 ----------
        self.questions: List[Question] = StudentProcessing.load(Path(CONFIGS_PATH, "default.json"))
        self.total_questions = len(self.questions)
        self.total_students = self._count_students()

        self.present_question = 0
        self.present_sub = 0
        self.present_student = 0

        # ---------- 成绩 & 记号 ----------
        max_sub = max(max(len(q.subs), 1) for q in self.questions)
        self.score_matrix = np.zeros((self.total_students, self.total_questions, max_sub), dtype=int)
        # marks[(stu, q, sub)] -> List[List[(x,y)]]  (每条曲线是点集)
        self.marks: Dict[Tuple[int, int, int], List[List[Tuple[int, int]]]] = {}

        # ---------- 显示 ----------
        self.zoom = 1.0
        self._curr_img: Optional[np.ndarray] = None
        self._stroke: Optional[List[Tuple[int, int]]] = None   # 正在绘制的曲线 (原始坐标)

        cv2.namedWindow(self.WIN)
        cv2.setMouseCallback(self.WIN, self._mouse_cb)

    # -------------------------------------------------- 运行主循环 --------------------------------------------------
    def run(self):
        while self.present_question < self.total_questions:
            q = self.questions[self.present_question]
            sub_cnt = max(1, len(q.subs))

            while self.present_sub < sub_cnt:
                while self.present_student < self.total_students:
                    self._grade_item(q, self.present_sub)
                    self.present_student += 1

                self.present_student = 0
                self.present_sub += 1

            self.present_sub = 0
            self.present_question += 1

        self._finish()

    # -------------------------------------------------- 批改单项 --------------------------------------------------
    def _grade_item(self, q: Question, sub_idx: int):
        img, origin = self._crop(q, sub_idx)
        self._show(img)

        score = self._read_score()
        self.score_matrix[self.present_student, self.present_question, sub_idx] = score

        # 将曲线坐标平移到整卷坐标
        key = (self.present_student, self.present_question, sub_idx)
        if key in self.marks:
            self.marks[key] = [[(x+origin[0], y+origin[1]) for (x, y) in stroke] for stroke in self.marks[key]]

    # -------------------------------------------------- 裁剪题/小题 --------------------------------------------------
    def _crop(self, q: Question, sub_idx: int):
        stu_img = self._read_stitched(self.present_student)
        if stu_img is None:
            raise FileNotFoundError("无法读取学生卷面！")

        if not q.subs:
            seg = q.segments[sub_idx] if len(q.segments) > 1 else q.segments[0]
        else:
            seg = q.subs[sub_idx].segments[0]
        x, y, w, h = seg.to_tuple()
        return stu_img[y:y+h, x:x+w], (x, y)

    # -------------------------------------------------- 分数输入 --------------------------------------------------
    def _read_score(self):
        buf = ""
        font = cv2.FONT_HERSHEY_SIMPLEX
        while True:
            disp = self._apply_zoom(self._render_with_marks())
            cv2.putText(disp, f"Score: {buf}", (10, 30), font, 1, (0, 0, 255), 2)
            cv2.imshow(self.WIN, disp)
            key = cv2.waitKey(0) & 0xFF
            if ord("0") <= key <= ord("9"):
                buf += chr(key)
            elif key in (8, 127):
                buf = buf[:-1]
            elif key == 13 and buf:
                return int(buf)

    # -------------------------------------------------- 渲染当前图 + 记号 --------------------------------------------------
    def _render_with_marks(self):
        if self._curr_img is None:
            return np.zeros((10, 10, 3), dtype=np.uint8)
        img = self._curr_img.copy()
        key = (self.present_student, self.present_question, self.present_sub)
        for stroke in self.marks.get(key, []):
            if len(stroke) >= 2:
                pts = np.array(stroke, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(img, [pts], False, (0, 0, 255), 2)
        # 若正在绘制
        if self._stroke and len(self._stroke) >= 2:
            pts = np.array(self._stroke, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [pts], False, (0, 0, 255), 1)
        return img

    # -------------------------------------------------- 显示 --------------------------------------------------
    def _apply_zoom(self, img: np.ndarray):
        if abs(self.zoom - 1.0) < 1e-3:
            return img
        return cv2.resize(img, None, fx=self.zoom, fy=self.zoom,
                          interpolation=cv2.INTER_AREA if self.zoom < 1 else cv2.INTER_LINEAR)

    def _show(self, img: np.ndarray):
        self._curr_img = img
        cv2.imshow(self.WIN, self._apply_zoom(self._render_with_marks()))

    # -------------------------------------------------- 鼠标回调 --------------------------------------------------
    def _mouse_cb(self, event, x, y, flags, param):
        # ---- 缩放 Ctrl+滚轮 ----
        if event == cv2.EVENT_MOUSEWHEEL and (flags & cv2.EVENT_FLAG_CTRLKEY):
            delta = (flags >> 16)
            if delta > 32767:
                delta -= 65536
            self.zoom *= 1.1 if delta > 0 else 1/1.1
            self.zoom = max(0.2, min(5.0, self.zoom))
            if self._curr_img is not None:
                cv2.imshow(self.WIN, self._apply_zoom(self._render_with_marks()))
            return

        # ---- 自由曲线记号 ----
        real_pt = (int(x / self.zoom), int(y / self.zoom))

        if event == cv2.EVENT_LBUTTONDOWN:
            self._stroke = [real_pt]
        elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):
            if self._stroke is not None:
                # 避免太密：只有距离大于1像素才记录
                if np.hypot(real_pt[0]-self._stroke[-1][0], real_pt[1]-self._stroke[-1][1]) >= 1:
                    self._stroke.append(real_pt)
                cv2.imshow(self.WIN, self._apply_zoom(self._render_with_marks()))
        elif event == cv2.EVENT_LBUTTONUP and self._stroke is not None:
            key = (self.present_student, self.present_question, self.present_sub)
            self.marks.setdefault(key, []).append(self._stroke)
            self._stroke = None
            self._show(self._curr_img)  # 重绘
        elif event == cv2.EVENT_RBUTTONDOWN:
            key = (self.present_student, self.present_question, self.present_sub)
            if self.marks.get(key):
                self.marks[key].pop()
                self._show(self._curr_img)

    # -------------------------------------------------- 读 stitched --------------------------------------------------
    def _read_stitched(self, idx: int):
        base = Path(STITCHED_PATH, f"{idx+1}")
        for ext in (".png", ".jpg", ".jpeg", ".bmp"):
            p = base.with_suffix(ext)
            if p.exists():
                return cv2.imread(str(p))
        return None

    # -------------------------------------------------- 学生数 --------------------------------------------------
    def _count_students(self):
        return len([p for p in Path(STITCHED_PATH).iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}])

    # -------------------------------------------------- 结束 --------------------------------------------------
    def _finish(self):
        # 曲线序列化：[[[x,y], ...], ...]
        serial_marks = {"|".join(map(str, k)): [list(map(list, stroke)) for stroke in v] for k, v in self.marks.items()}
        result = {
            "total_students": int(self.total_students),
            "total_questions": int(self.total_questions),
            "scores": self.score_matrix.tolist(),
            "marks": serial_marks,
        }
        Path(CONFIGS_PATH).mkdir(parents=True, exist_ok=True)
        with open(Path(CONFIGS_PATH, "result.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=Fal0se, indent=2)
        cv2.destroyAllWindows()
        print("✔ 批改完成，结果已保存到 result.json")


if __name__ == "__main__":
    Teacher().run()
