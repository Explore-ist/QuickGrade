import image_processor as ip
import database as db
img_path=r"D:\System\Desktop\py\QuickGrade\test\2.jpg"
test=db.Exam('114514','test',[],0)
test.img = ip.open_image(img_path)
test.img = ip.exponential_transformation(test.img)
ip.show_image(img_path,test.img)