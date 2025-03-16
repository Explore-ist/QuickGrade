import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GradeConfig:
    total_regions:int
    regions:list

class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None

    def load_config(self)->GradeConfig:
        with open(self.config_path, "r", encoding='utf-8') as f:
            config = json.load(f)
        return GradeConfig(
            total_regions=config["total_regions"],
            regions=config["regions"]
        )
    def save_config(self,regions:list) -> None:
        #保存选区位置
        config={
            "total_regions":len(regions),
            "regions":[
                {
                    "order":idx+1,
                    "x":r[0],
                    "y":r[1],
                    "width":r[2],
                    "height":r[3]
                }for idx,r in enumerate(regions)
            ]
        }
        config_path = Path(self.config_path)
        # 如果父目录不存在，自动创建
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path,"w",encoding='utf-8') as f:
            json.dump(config,f,indent=2,ensure_ascii=False)
        print(f"配置已写入{self.config_path}")