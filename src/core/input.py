"""
--+----------input
  +---选区划分（方案②：缩放 + 反算坐标）
  +---批量处理

本版本包含：
* 自动缩放（Fit‑to‑Window），鼠标坐标 ↔ 原图坐标双向映射。
* 大题 / 小题 / 连续大题划分逻辑。
* JSON 结构化保存 & 读取。

依赖：OpenCV‑Python ≥4.6、NumPy。
"""
from __future__ import annotations

import ctypes
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from path import CONFIGS_PATH, STITCHED_PATH

# --------------------------------------------------
# 数据结构
# --------------------------------------------------

@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return self.x, self.y, self.w, self.h

    def contains(self, other: "Region") -> bool:
        return (
            other.x >= self.x
            and other.y >= self.y
            and other.x + other.w <= self.x + self.w
            and other.y + other.h <= self.y + self.h
        )


@dataclass
class SubQuestion:
    index: int  # 1‑based
    segments: List[Region] = field(default_factory=list)

    @property
    def id(self) -> str:  # 仅返回小题序号，完整 ID 由上级补全
        return str(self.index)


@dataclass
class Question:
    id: int
    segments: List[Region] = field(default_factory=list)
    subs: List[SubQuestion] = field(default_factory=list)

    def add_segment(self, r: Region):
        self.segments.append(r)

    def add_sub(self, r: Region):
        sq = SubQuestion(len(self.subs) + 1)
        sq.segments.append(r)
        self.subs.append(sq)

    def contains(self, r: Region) -> bool:
        return any(seg.contains(r) for seg in self.segments)

# --------------------------------------------------
# 选区划分 GUI（OpenCV）
# --------------------------------------------------

class Redistricting:
    cname = "Redistricting"
    color = {"saved": (0, 0, 0), "temp": (0, 0, 0), "text": (0, 0, 0)}
    wit = {"saved": 1, "temp": 2, "text": 1}

    # ---- 屏幕分辨率 & 缩放因子 ---- #
    _user32 = ctypes.windll.user32
    _SCREEN_W = _user32.GetSystemMetrics(0)
    _SCREEN_H = _user32.GetSystemMetrics(1)

    @classmethod
    def _calc_scale(cls, img_w: int, img_h: int, margin: int = 80) -> float:
        rw = (cls._SCREEN_W - margin) / img_w
        rh = (cls._SCREEN_H - margin) / img_h
        return min(1.0, rw, rh)

    # -------------------------------- #

    def __init__(self, template_img: Optional[str] = None):
        self.template_path = template_img or self._auto_find_template()
        self.template_img = cv2.imread(str(self.template_path))
        if self.template_img is None:
            raise FileNotFoundError(f"无法加载模板图片：{self.template_path}")

        h, w = self.template_img.shape[:2]
        self.scale = self._calc_scale(w, h)

        self.base_display = cv2.resize(
            self.template_img,
            None,
            fx=self.scale,
            fy=self.scale,
            interpolation=cv2.INTER_AREA if self.scale < 1 else cv2.INTER_LINEAR,
        )

        # 状态量
        self.questions: List[Question] = []
        self.temp_region: Optional[Region] = None
        self.drawing = False
        self.start_pt = (-1, -1)
        self.merge_next = False

        cv2.namedWindow(self.cname)
        cv2.setMouseCallback(self.cname, self._mouse_cb)

    # ---------- 坐标映射 ---------- #
    def _to_display(self, x: int, y: int) -> Tuple[int, int]:
        s = self.scale
        return int(x * s), int(y * s)

    def _to_origin(self, x: int, y: int) -> Tuple[int, int]:
        s = 1.0 / self.scale
        return int(x * s), int(y * s)

    # ---------- 主循环 ---------- #
    def run(self) -> List[Question]:
        while True:
            cv2.imshow(self.cname, self._draw())
            if not self._wait_key():
                break
        cv2.destroyAllWindows()
        return self.questions

    # ---------- 鼠标 ---------- #
    def _mouse_cb(self, event, x, y, flags, param):
        real_x, real_y = self._to_origin(x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_pt = (real_x, real_y)
            self.temp_region = Region(real_x, real_y, 0, 0)
        elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
            x0, y0 = self.start_pt
            self.temp_region = Region(
                x=min(x0, real_x),
                y=min(y0, real_y),
                w=abs(real_x - x0),
                h=abs(real_y - y0),
            )
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False

    # ---------- 绘制 ---------- #
    def _draw(self) -> np.ndarray:
        disp = self.base_display.copy()
        for q in self.questions:
            self._draw_question(disp, q)
        if self.temp_region:
            p1 = self._to_display(self.temp_region.x, self.temp_region.y)
            p2 = self._to_display(self.temp_region.x + self.temp_region.w, self.temp_region.y + self.temp_region.h)
            cv2.rectangle(disp, p1, p2, self.color["temp"], self.wit["temp"])
        cv2.putText(
            disp,
            "↵ 保存 / esc 退出 / r 撤销 / c 并入上一题",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            self.color["text"],
            1,
        )
        return disp

    def _draw_question(self, canvas: np.ndarray, q: Question):
        for seg in q.segments:
            self._rect_with_label(canvas, seg, str(q.id))
        for sub in q.subs:
            label = f"{q.id}.{sub.index}"
            for seg in sub.segments:
                self._rect_with_label(canvas, seg, label)

    def _rect_with_label(self, canvas: np.ndarray, seg: Region, label: str):
        p1 = self._to_display(seg.x, seg.y)
        p2 = self._to_display(seg.x + seg.w, seg.y + seg.h)
        cv2.rectangle(canvas, p1, p2, self.color["saved"], self.wit["saved"])
        cv2.putText(
            canvas,
            label,
            (p1[0] + 5, p1[1] + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6 if "." not in label else 0.5,
            self.color["text"],
            1,
        )

    # ---------- 键盘 ---------- #
    def _wait_key(self) -> bool:
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # ↵
            self._confirm_region()
        elif key == 27:  # esc
            return False
        elif key == ord("r"):
            self.temp_region = None
        elif key == ord("c"):
            self.merge_next = True
        return True

    def _confirm_region(self):
        if not self.temp_region or self.temp_region.w * self.temp_region.h == 0:
            return
        r = self.temp_region
        preview = self.template_img[r.y : r.y + r.h, r.x : r.x + r.w]
        cv2.imshow("preview", preview)
        if cv2.waitKey(0) & 0xFF != 13:
            cv2.destroyWindow("preview")
            self.temp_region = None
            self.merge_next = False
            return
        cv2.destroyWindow("preview")
        self._dispatch_region(r)
        self.temp_region = None

    # ---------- 逻辑分派 ---------- #
    def _dispatch_region(self, r: Region):
        # 优先并入上一题（按 'c' 键）
        if self.questions:
            last_q = self.questions[-1]
            if self.merge_next:
                last_q.add_segment(r)
                self.merge_next = False
                return

        # ----- ① 判断是否落在任何已有大题内 -----
        for q in reversed(self.questions):  # 倒序更符合“离得近优先”
            if q.contains(r):
                q.add_sub(r)
                self.merge_next = False
                return

        # ----- ② 若 self.questions 为空 → 第 1 题 -----
        if not self.questions:
            self.questions.append(Question(1, segments=[r]))
            return

        # ----- ③ 否则作为全新大题 -----
        new_id = self.questions[-1].id + 1
        self.questions.append(Question(new_id, segments=[r]))
        self.merge_next = False

    # ---------- 辅助 ---------- #
    @staticmethod
    def _auto_find_template() -> str:
        d = Path(STITCHED_PATH)
        if not d.exists():
            raise FileNotFoundError("未找到 stitched 目录！")
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.bmp"):
            imgs = sorted(d.glob(pattern))
            if imgs:
                return str(imgs[0])
        raise FileNotFoundError("stitched 目录下无图片！")

# --------------------------------------------------
# JSON 读 / 写
# --------------------------------------------------

class StudentProcessing:
    def __init__(self, questions: List[Question], target_dir: str = CONFIGS_PATH, config_name: str = "default.json"):
        self.questions = questions
        self.target_dir = Path(target_dir)
        self.config_name = config_name

    def save(self):
        obj = {"questions": [self._q2d(q) for q in self.questions]}
        self.target_dir.mkdir(parents=True, exist_ok=True)
        with open(self.target_dir / self.config_name, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        print(f"已写入 {self.target_dir / self.config_name}")

    @staticmethod
    def load(path: str | Path) -> List[Question]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [StudentProcessing._d2q(item) for item in data.get("questions", [])]

    # --------- 序列化辅助 --------- #
    @staticmethod
    def _q2d(q: Question):
        return {
            "id": q.id,
            "segments": [seg.to_tuple() for seg in q.segments],
            "subs": [
                {
                    "id": f"{q.id}.{sub.index}",
                    "segments": [seg.to_tuple() for seg in sub.segments],
                }
                for sub in q.subs
            ],
        }

    @staticmethod
    def _d2q(d: dict) -> Question:
        q = Question(d["id"])
        q.segments = [Region(*t) for t in d.get("segments", [])]
        for sub_d in d.get("subs", []):
            idx = int(sub_d["id"].split(".")[1])
            sub = SubQuestion(idx)
            sub.segments = [Region(*t) for t in sub_d.get("segments", [])]
            q.subs.append(sub)
        return q

# -------------------- 自测 -------------------- #
if __name__ == "__main__":
    red = Redistricting()  # 自动找模板并计算缩放
    qs = red.run()

    sp = StudentProcessing(qs, config_name="default.json")
    sp.save()

    loaded = StudentProcessing.load(Path(CONFIGS_PATH, "default.json"))
    print("Loaded:")
    for q in loaded:
        print(q)