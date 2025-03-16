import cv2
import argparse
from pathlib import Path
from typing import List,Dict
from src.gui.selector import RegionSelector
from src.core.config import ConfigManager
from src.utils.fileio import FileManager
from src.utils.logger import setup_logger

logger = setup_logger()

def process_single_student(student_path: Path, config: Dict, output_dir: Path)->None:
    try:
        # 加载学生试卷
        student_img = FileManager.safe_imread(student_path)
        student_id = student_path.stem.split("_")[-1]

        # 创建学生专属目录
        student_output = output_dir / f"student_{student_id}"
        student_output.mkdir(exist_ok=True)

        # 处理每个区域
        for idx, region in enumerate(config["regions"], start=1):
            x, y, w, h = region["x"], region["y"], region["width"], region["height"]

            # 截取并保存区域
            cropped = student_img[y:y + h, x:x + w]
            output_path = student_output / f"Q{idx:02d}.png"
            cv2.imwrite(str(output_path), cropped)

        logger.info(f"处理完成: {student_id}")

    except Exception as e:
        logger.error(f"处理失败 [{student_path.name}]: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="QuickGrade")
    parser.add_argument("--template",
                        default=r"D:\System\Desktop\py\QuickGrade\data\templates\template.png",
                        help="样板试卷路径")
    parser.add_argument("--config", default="data/configs/default.json", help="配置文件路径")
    parser.add_argument("--input", default="data/students", help="学生试卷目录")
    parser.add_argument("--output", default="data/results", help="输出目录")
    args = parser.parse_args()
    #初始化：
    config_manager = ConfigManager(args.config)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        #模式选择
        if not Path(args.config).exists():
            logger.info("未找到配置文件，进入区域标注模式")
            selector = RegionSelector()
            regions = selector.run(args.template)
            config_manager.save_config(regions)
            logger.info(f"配置已保存至 {args.config}")
        #批量处理模式
        logger.info("启动批量处理流程")
        config = config_manager.load_config()
        student_files = FileManager.find_student_files(args.input)
        # 并行处理
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as executor:
            for student_file in student_files:
                executor.submit(
                    process_single_student,
                    student_file,
                    config,
                    output_dir
                )
        logger.info(f"处理完成，结果保存在 {output_dir}")

    except Exception as e:
        logger.critical(f"程序运行失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()