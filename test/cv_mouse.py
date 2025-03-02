import cv2 as cv
import numpy as np
#鼠标所有可用事件
#alt,ctrl,左键，中键，右键，shift
# event = [i for i in dir(cv) if 'EVENT' in i]
# print(event)

#鼠标跟踪
drawing=False
mode=True
ix,iy=255,255
drawn_shapes = []
def draw_circle(event, x, y, flags, param):
    global ix,iy,drawing,mode
    img=param

    if event == cv.EVENT_LBUTTONDOWN:
        drawing=True
        ix,iy=x,y
    elif event == cv.EVENT_MOUSEMOVE:
        if drawing:
            img[:] = 0
            for shape in drawn_shapes:
                if shape['type']=='rectangle':
                     cv.rectangle(img, (ix, iy), (x, y), (0, 255, 0), 5)
                elif shape['type']=='circle':
                    cv.circle(img, (ix, iy), 5, (0, 0, 255), 2)
            if mode:
                cv.rectangle(img, (ix, iy), (x, y), (0, 255, 0), 5)
            else:
                cv.circle(img, (ix, iy), 5, (0, 0, 255), 2)
    elif event == cv.EVENT_LBUTTONUP:
        drawing=False
        if mode:
            drawn_shapes.append({'type':'rectangle', 'start':(ix,iy), 'end':(x,y),'color':(0,255,0)})
            cv.rectangle(img, (ix, iy), (x, y), (0, 255, 0), 5)
        else:
            drawn_shapes.append({'type':'circle', 'center':(x,y), 'radius':5,'color':(0,255,0)})
            cv.circle(img, (x, y), 5, (0, 0, 255), -1)

draw = np.zeros((512, 512, 3), np.uint8)
cv.imshow('img',draw)
cv.setMouseCallback('img',draw_circle,draw)
while True:
    cv.imshow('img',draw)
    key=cv.waitKey(1) & 0xFF
    if key == ord('m'):
        mode=not mode
    elif key == 27:
        break

cv.destroyAllWindows()