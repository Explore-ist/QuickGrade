"""
--+----------input
  +---选区划分
  +---批量处理
"""
import cv2
import os
import numpy as np
from typing import List, Tuple, Optional

import json
from pathlib import Path

class Redistricting:
    """
    选区划分类
    对样卷的选区，保存配置
    """
    cname='Redistricting'
    color={
        'saved':(0,0,255),
        'temp':(0,255,0),
        'text':(0,255,255)
    }
    wit={
        'saved':1,
        'temp':2,
        'text':1
    }
    def __init__(self,template_img:str):
        self.template_img = cv2.imread(template_img)
        if self.template_img is None:
            raise FileNotFoundError(f'无法加载{template_img}')

        self.saved_region : List[Tuple[int,int,int,int]]=[]
        self.temp_region : Optional[Tuple[int,int,int,int]]=None

        self.startpoint= (-1,-1)
        self.drawing = False

    def run(self)->List[Tuple[int,int,int,int]]:
        """
        主函数
        -读取
        -初始化，绑定鼠标回调函数
        -画每一帧
        -判断

        :return:返回已保存的选区列表(x,y,width,height)
        """
        cv2.namedWindow(self.cname)
        cv2.setMouseCallback(self.cname,self.mouse)

        while True:
            display=self.draw()
            cv2.imshow(self.cname,display)

            if not self.wait():
                break

        cv2.destroyAllWindows()
        return self.saved_region

    def mouse(self,event,x,y,flags,param)->None:
        """
        鼠标回调函数，用于更新临时选区
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.startpoint= (x,y)
            self.temp_region=(x,y,0,0)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                x0,y0=self.startpoint
                self.temp_region=(
                    min(x0, x),
                    min(y0, y),
                    abs(x - x0),
                    abs(y - y0)
                )

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            # if self.temp_region and self.temp_region[2]>0 and self.temp_region[3]>0 :
            #     self.confirm_region()
            # else:
            #     self.temp_region=None


    def draw(self)->np.ndarray:
        """一帧要绘制的：
        提示词，已选择区域
        """
        display_img=self.template_img.copy()
        # 绘制已选择区域
        for idx,(x,y,w,h) in enumerate(self.saved_region,1):
            cv2.rectangle(display_img, (x,y), (x+w,y+h),self.color['saved'],self.wit['saved'])
            cv2.putText(display_img, str(idx), (x + 5, y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color['text'], 1)

        if self.temp_region :
            x,y,w,h=self.temp_region
            cv2.rectangle(display_img,
                          (x, y), (x+w, y+h),
                          self.color['temp'], self.wit['temp'])

        cv2.putText(display_img,
                    '用鼠标选择区域，回车确认，esc退出，r重选',
                    (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    self.color['text'],
                    self.wit['text'])

        return display_img

    def wait(self)->bool:
        """
        监听用户按键
        Enter（13） -> 确认保存当前 temp_region
        ESC（27）   -> 退出程序
        R           -> 重置当前 temp_region
        """
        key = cv2.waitKey(1) & 0xFF

        if key == 13:  # Enter键
            self.confirm_region()
        elif key == 27:  # Esc键
            return False
        elif key == ord('r'):  # 重置当前选区
            self.temp_region = None
        return True

    def confirm_region(self)->None:
        """
        当用户按下回车（Enter）后，先显示一个预览窗口，如果再按回车就确认保存该区域。
        按ESC则取消此次选择。
        """
        if self.temp_region is None or self.template_img is None:
            return

        x,y,w,h=self.temp_region
        preview=self.template_img[y:y+h,x:x+w]
        cv2.imshow('preview',preview)

        key = cv2.waitKey(0) & 0xFF
        if key == 13:
            self.saved_region.append(self.temp_region)
            print(f"已保存坐标{self.temp_region}")
            self.temp_region=None
        elif key == 27:
            self.temp_region = None
            print("已取消选择")

        cv2.destroyWindow('preview')



class StudentProcessing:
    """
    学生预处理类
    对每一张卷子生成一个对应名称的文件夹，保存一个json文件，并将原试卷放入
    每次读取小题时，读取json即可
    完成改卷后，生成一个记录的最终试卷
    """
    def __init__(self,_saved_region:List[Tuple[int,int,int,int]], target_dir: str,config_name: str):
        self.target_dir = target_dir
        self.saved_region = _saved_region
        self.config_name = config_name

    def save_region(self)->None:
        """
            保存区域信息到 JSON 配置文件中
            regions 中每个元素为 (x, y, width, height)
        """
        config={
            "total_regions":len(self.saved_region),
            "regions":[
                {
                    "order": idx + 1,
                    "x": r[0],
                    "y": r[1],
                    "width": r[2],
                    "height": r[3]
                }
                for idx,r in enumerate(self.saved_region)
            ]
        }
        path=Path(self.target_dir,self.config_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path,'w',encoding='utf-8') as f:
            json.dump(config,f,ensure_ascii=False,indent=2)
        print(f"区域信息已写入 {self.target_dir}")

    def lode_config(self)->List[Tuple[int,int,int,int]]:
        """
            从 JSON 配置文件中读取区域信息
            返回 List[Tuple[int,int,int,int]]，每个元素为 (x, y, width, height)
        """
        file_path = Path(self.target_dir, self.config_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            config=json.load(f)

        regions_data=config.get("regions",[])
        regions=[
            (item["x"], item["y"], item["width"], item["height"])
            for item in regions_data
        ]
        return regions


if __name__ == '__main__':
    script_dir=os.path.dirname(os.path.abspath(__file__))

    template_path=os.path.join(script_dir,'..','data','templates','template.png')
    template_path=os.path.normpath(template_path)

    config_path=os.path.join(script_dir,'..','data','configs')
    config_path=os.path.normpath(config_path)


    try:
        redistricting = Redistricting(template_path)
        saved_region = redistricting.run()
        print(saved_region)
        student_process = StudentProcessing(
            saved_region,
            config_path,
            'default.json'
        )
        student_process.save_region()
        print(student_process.lode_config())
    except FileNotFoundError as e:
        print(f'{e}')
