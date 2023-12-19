from pathlib import Path
import sys

MAIN_PATH      =  Path(__file__).parent.parent  
SRC_PATH       =  MAIN_PATH / "src"
DATA_PATH      =  MAIN_PATH / "data"
CONFIG_PATH    =  MAIN_PATH / "config"
LOG_PATH       =  MAIN_PATH / "log"

sys.path.append(str(MAIN_PATH))
sys.path.append(str(SRC_PATH))
sys.path.append(str(DATA_PATH))
sys.path.append(str(LOG_PATH))
sys.path.append(str(CONFIG_PATH))
