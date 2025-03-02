from dataclasses import dataclass, field
from typing import List,Dict,Optional
@dataclass
class Question:                                                 #题目
    question_id: str                                            #题型
    question_type: str                                          #题型
    score: float                                                #总分
    position:Dict[str,int]                                      #题目位置
    metadata:Dict[str,str]=field(default_factory=dict)          #扩展

@dataclass
class Exam:
    exam_id: str                                                #id
    exam_name:str                                               #名称
    questions: List[Question]                                   #题目列表
    full_score: float                                           #总分
    img=None
    metadata: Dict[str, str] = field(default_factory=dict)      #扩展

@dataclass
class StudentAnswer:
    question_id: str                                            #id
    cropped_img_path:str                                        #路径
    score: Optional[float]                                      #分数
    metadata: Dict[str, str] = field(default_factory=dict)      #扩展

@dataclass
class StudentPaper:
    student_id: str                                             #id
    student_name:str                                            #姓名
    exam_id:str                                                 #考号
    original_image:str                                          #原始图像
    trimmed_img_path:Optional[str]                              #增强图像
    answer: List[StudentAnswer] = field(default_factory=dict)   #扩展
