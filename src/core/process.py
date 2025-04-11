"""
--+--process
  +--+--老师
     +--改卷程序
"""

import os
import cv2
import json
import numpy as np
from typing import List, Tuple

class Teacher:
    """
    老师类
    是主要的改卷程序，按小题或者按学生批改试卷
    读取学生的试卷，并给分保存
    """
    PY_PATH = os.path.abspath(__file__)
    TEMPLATE_IMG_PATH = '..\\data\\templates'
    STUDENT_IMG_PATH = '..\\data\\students'
    CONFIG_PATH = '..\\data\\configs'
    RESULT_PATH = '..\\data\\results'
    def __init__(self):
        self.total_num_questions = 0
        self.total_num_students = 0
        self.present_question = 0
        self.present_student = 0
        self.img = None
        self.score_matrix = np.zeros((self.total_num_students, self.total_num_questions))
        self.region : List[Tuple[int,int,int,int]] = []
        self.student_name_list : List[str] = []

    def run(self):
        self.init()
        while 0 <= self.present_question < self.total_num_questions:
            while 0 <= self.present_student < self.total_num_students:
                self.open_question(self.student_name_list[self.present_student],
                                   self.present_question)
                self.wait_keyboard()
            self.present_student = 0
            self.present_question += 1
        self.end_correction()

    def init(self):
        if self.is_new():
            self.lode_config(is_new=True)
            self.count_student()
            self.score_matrix = np.zeros((self.total_num_students, self.total_num_questions))
        else:
            #等设计完保存config格式再写
            self.lode_config(is_new=False)

    def end_correction(self):
        cv2.destroyAllWindows()
        cv2.imshow('end!', self.img)
        print('c：检查模式\nenter/q:保存退出')
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord('q'):
                self.check_mode()
            elif key == 13 or key == 27:
                self.save_score(if_correct=True)
                break

    def open_question(self,student,questions):
        temp = cv2.imread(f'..\\data\\students\\{student}')#找学生
        x,y,w,h = self.region[questions]#找题目
        cv2.imshow('question',temp[y:y+h,x:x+w])#打开题目

    def wait_keyboard(self):
        print(r'输入数字视为保存分数，输入q为暂停并保存改卷，输入\'<-\'视为回跳上一题:')
        while True:
            key = cv2.waitKey(0) & 0xFF

            if key == ord('q'):
                self.save_score(if_correct=False)
                break
            elif key == 8:#删除键
                if self.present_question - 1 >= 0:
                    self.present_question -= 1
                else:
                    print('开头不可退回')
                    break
            elif ord('0') <= key <= ord('9') :
                self.score_matrix[self.present_student][self.present_question]= key - ord('0')
                self.present_student += 1
                break

    def lode_config(self,is_new=True):
        self.img = cv2.imread('..\\data\\templates\\template.png')
        with open('..\\data\\configs\\default.json', 'r', encoding="utf-8") as sf:
            data = json.load(sf)

        regions_data = data.get('regions', [])
        self.total_num_questions = data['total_regions']
        self.region = [
            (item["x"], item["y"], item["width"], item["height"])
            for item in regions_data
        ]

        if is_new:
            self.present_question = 0
            self.present_student = 0
        else:
            config_name = '\\result.json'
            with open(self.CONFIG_PATH + config_name, 'r', encoding="utf-8") as sf:
                data = json.load(sf)

            self.total_num_questions = data.get('total_questions', 0)
            self.total_num_students = data.get('total_students', 0)
            self.present_question = data.get('present_question', 0)
            self.present_student = data.get('present_student', 0)
            score_data = data.get('score_matrix', [])
            self.score_matrix = np.array(score_data)if score_data else np.zeros((self.total_num_students, self.total_num_questions))

    def is_new(self):
        return not os.path.exists('..\\data\\configs\\result.json')

    def count_student(self):
        student_dic = '..\\data\\students'
        files = os.listdir(student_dic)
        self.total_num_students=len(files)
        self.student_name_list = files

    def check_mode(self):
        print('还没写完捏')

    def save_score(self,if_correct = False):
        config_name = '\\result.json'
        config = {
            'if_corrected': if_correct,
            'total_students': self.total_num_students,
            'total_questions': self.total_num_questions,
            'present_question': self.present_question,
            'present_student': self.present_student,
            'score_matrix': self.score_matrix.tolist()
        }
        with open(self.CONFIG_PATH + config_name,'w',encoding="utf-8") as sf:
            json.dump(config,sf,ensure_ascii=False,indent=4)

if __name__ == '__main__':
    test = Teacher()
    test.run()