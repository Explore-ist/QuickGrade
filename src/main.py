import cv2
import numpy as np
import json

class ExamGradeConfigurator:
    def __init__(self):
        self.template_img = None
        self.selected_regions = []
        self.current_region = None
        self.drawing = False
        self.ix,self.iy = -1,-1

    def _mouse_callback(self, event, x, y, flags, param):
        #鼠标回调函数
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix,self.iy = x,y
            self.current_region = (x,y,0,0)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                temp_img=self.template_img.copy()
                cv2.rectangle(temp_img,(self.ix,self.iy),(x,y),(0,255,0),2)
                cv2.imshow("Select_region",temp_img)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            x1,y1=min(self.ix,x),min(self.iy,y)
            x2,y2=max(self.ix,x),max(self.iy,y)
            self.current_region = (x1,y1,x2-x1,y2-y1)

    def select_region(self,template_path):
        #控制函数
        #1打开样板试卷
        self.template_img = cv2.imread(template_path)
        if self.template_img is None:
            raise FileNotFoundError(f"{template_path} not found")

        #2交互界面：
        cv2.namedWindow("Select_region")
        cv2.setMouseCallback("Select_region",self._mouse_callback)

        while True:
            #3显示图像
            display_img=self.template_img.copy()
            for region in self.selected_regions:
                x,y,w,h=region
                cv2.rectangle(display_img,(x,y),(x+w,y+h),(0,0,255),2)
            cv2.imshow("Select_region",display_img)

            #4键盘等待
            key = cv2.waitKey(1) & 0xFF
            if key == 13:#如果划线区域满意->回车键
                if self.current_region:
                    #展示预览：
                    x,y,w,h=self.current_region
                    cropped=self.template_img[y:y+h,x:x+w]
                    cv2.imshow("Select_region",cropped)
                    #等待确认
                    confirm_key = cv2.waitKey(0) & 0xFF
                    if confirm_key == 13:
                        self.selected_regions.append(self.current_region)
                        print(f"已保存: {self.current_region}")
                    elif confirm_key == 27:
                        self.current_region = None
                        cv2.destroyWindows("Preview")
            elif key == 27:
                break

        cv2.destroyAllWindows()
        self.save_config("config.json")
        print('配置已保存')
        return self.selected_regions

    def save_config(self,config_path):
        #保存选区位置
        config={
            "regions":[
                {
                    "x":r[0],
                    "y":r[1],
                    "width":r[2],
                    "height":r[3]
                }for r in self.selected_regions
            ]
        }
        with open(config_path,"w") as f:
            json.dump(config,f,indent=2)

    @staticmethod
    def load_config(config_path):
        with open(config_path) as f:
            config=json.load(f)
            return [
                (r['x'],r['y'],r['width'],r['height'])
                for r in config['regions']
            ]

if __name__ == '__main__':
    configurator = ExamGradeConfigurator()

    try:
        regions = configurator.select_region("template.png")

        config = configurator.load_config("config.json")
        student=cv2.imread("student1.jpg")
        for idx,(x,y,w,h) in enumerate(config):
            cropped=student[y:y+h,x:x+w]
            gray=cv2.cvtColor(cropped,cv2.COLOR_BGR2GRAY)
            cv2.imshow(f"Questions",gray)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    except FileNotFoundError:
        print(f'发生错误:{str(e)}')
    finally:
        cv2.destroyAllWindows()