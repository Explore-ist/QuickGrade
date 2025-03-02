import cv2 as cv
import numpy as np

#基本画布创建
img=np.zeros((512,512,3),np.uint8)
#插入形状
cv.line(img,(0,0),(512,512),(255,0,0),5)
cv.rectangle(img,(384,0),(510,128),(255,0,0),3)
#字体输入
font = cv.FONT_HERSHEY_SIMPLEX
cv.putText(img,'OpenCV',(100,100),font,1,(255,255,255),2)
#图片展示，等待与销毁
cv.imshow('img',img)
cv.waitKey(0)
cv.destroyAllWindows()

