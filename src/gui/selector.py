import cv2
import numpy as np
from typing import Optional, Tuple, List

class RegionSelector:
    """交互式区域选择器

    Attributes:
        WINDOW_NAME (str): 主窗口名称
        PREVIEW_WINDOW (str): 预览窗口名称
        COLOR_PALETTE (dict): 颜色配置
    """
    WINDOW_NAME="Region_selector"
    PREVIEW_WINDOW="Region_preview"
    COLOR_PALETTE={
        "current": (0, 255, 0),  # 当前选区颜色 (BGR)
        "confirmed": (0, 0, 255),  # 已确认选区颜色
        "text": (0, 255, 255)  # 文字颜色
    }
    LINE_WIDTH = 2
    def __init__(self):
        self._template_img: Optional[np.ndarray] = None
        self._confirmed_regions: List[Tuple[int,int,int,int]] = []
        self._current_regions: Optional[Tuple[int,int,int,int]] = None
        self._drawing=False
        self._start_point=(0,0)

    def _init_windows(self)->None:
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.WINDOW_NAME, self._mouse_handler)

    def _mouse_handler(self, event:int,x:int,y:int,*_) -> None:
        """鼠标事件处理器

        Args:
            event: OpenCV 鼠标事件类型
            x: 鼠标X坐标
            y: 鼠标Y坐标
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self._start_selection(x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            self._update_selection(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self._finalize_selection(x, y)

    def _start_selection(self, x: int, y: int) -> None:
        """开始选区操作"""
        self._drawing = True
        self._start_point = (x, y)
        self._current_region = (x, y, 0, 0)

    def _update_selection(self, x: int, y: int) -> None:
        """更新选区状态"""
        if self._drawing and self._template_img is not None:
            temp_img = self._template_img.copy()
            cv2.rectangle(temp_img, self._start_point, (x, y),
                          self.COLOR_PALETTE["current"], self.LINE_WIDTH)
            cv2.imshow(self.WINDOW_NAME, temp_img)

    def _finalize_selection(self, x: int, y: int) -> None:
        """完成选区操作"""
        self._drawing = False
        if self._template_img is None:
            return

        x1, y1 = min(self._start_point[0], x), min(self._start_point[1], y)
        x2, y2 = max(self._start_point[0], x), max(self._start_point[1], y)
        width, height = x2 - x1, y2 - y1

        if width > 0 and height > 0:
            self._current_region = (x1, y1, width, height)
        else:
            self._current_region = None

    def _draw_ui(self)->None:
        """绘制主界面"""
        if self._template_img is None:
            return
        display_img = self._template_img.copy()
        for region in self._confirmed_regions:
            x,y,w,h=region
            cv2.rectangle(display_img, (x,y), (x+w,y+h),
                          self.COLOR_PALETTE["confirmed"], self.LINE_WIDTH)
        cv2.putText(display_img,
                    "Enter: Confirm Region | Esc: Exit | R: Reset",
                    (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    self.COLOR_PALETTE["text"],1)
        cv2.imshow(self.WINDOW_NAME, display_img)

    def _handle_keyboard(self)->bool:
        key = cv2.waitKey(1) & 0xFF

        if key == 13:  # Enter键
            self._confirm_region()
        elif key == 27:  # Esc键
            return False
        elif key == ord('r'):  # 重置当前选区
            self._current_region = None
        return True

    def _confirm_region(self)->None:
        """确认选区"""
        if self._current_region is None or self._template_img is None:
            return
        x, y, w, h = self._current_region
        preview = self._template_img[y:y + h, x:x + w]

        cv2.imshow(self.PREVIEW_WINDOW, preview)
        key = cv2.waitKey(0) & 0xFF

        if key == 13:  # 二次确认
            self._confirmed_regions.append(self._current_region)
            print(f"Region confirmed: {self._current_region}")
        elif key == 27:  # 取消选择
            print("Region selection canceled")

        cv2.destroyWindow(self.PREVIEW_WINDOW)
        self._current_region = None

    def run(self,template_path:str)->List[Tuple[int,int,int,int]]:
        """运行选区程序
        Args:
            template_path: 模板图片路径
        Returns:
            已确认的选区坐标列表 (x, y, width, height)
        Raises:
             FileNotFoundError: 模板图片加载失败
        """
        self._template_img = cv2.imread(template_path)
        if self._template_img is None:
            raise FileNotFoundError(f"无法加载模板图片: {template_path}")

        self._init_windows()

        while True:
            self._draw_ui()
            if not self._handle_keyboard():
                break

        cv2.destroyAllWindows()
        return self._confirmed_regions