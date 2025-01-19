from pathlib import Path
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = Path(BASE_DIR)
DATAPATH = PATH / 'data'