from pathlib import Path
import cv2
import numpy as np


class FileManager:
    @staticmethod
    def find_student_files(input_dir:str) -> list:
        path = Path(input_dir)
        return list(path.glob("student*.png"))+list(path.glob("student*.jpg"))

    @staticmethod
    def safe_imread(path:str) -> np.ndarray:
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"无法读取文件图像：{path}")
        return img