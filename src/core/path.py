import os

def _work_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

WORK_PATH = _work_root()
SRC_PATH = os.path.join(WORK_PATH,'src')

CORE_PATH = os.path.join(SRC_PATH, 'core')
DATA_PATH = os.path.join(SRC_PATH, 'data')

CONFIGS_PATH = os.path.join(DATA_PATH, 'configs')
RESULTS_PATH = os.path.join(DATA_PATH, 'results')
STUDENTS_PATH = os.path.join(DATA_PATH, 'students')
STITCHED_PATH = os.path.join(DATA_PATH, 'stitched')