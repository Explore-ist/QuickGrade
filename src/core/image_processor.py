import cv2 as cv
import numpy as np
import database as db
#加载试卷

def open_image(image_path):
    img = cv.imread(image_path, cv.IMREAD_GRAYSCALE)
    if img is None:
        return
    else:
        return img

def show_image(image_path,img):
    if img is None:
        return
    else:
        cv.imshow(image_path, img)
        cv.waitKey(0)
        cv.destroyAllWindows()


#图片处理：非线性增强图片
def exponential_transformation(image, c=255):
    # 指数变换
    normalized_image = image / 255.0
    exp_image = c * (np.exp(normalized_image) - 1)
    exp_image = np.clip(exp_image, 0, 255).astype(np.uint8)
    return exp_image

def image_segmentation():
    #将图片分割后得到问题集的坐标集
    problem_list=[]
    return problem_list