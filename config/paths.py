from pathlib import Path
import sys

# main
MAIN_PATH       =  Path(__file__).parent.parent 
sys.path.append(str(MAIN_PATH)) 

# src
SRC_PATH        =  MAIN_PATH / "src"
sys.path.append(str(SRC_PATH))

# data
DATA_PATH       =  MAIN_PATH / "data"
JSONS_PATH      =  MAIN_PATH / "data/jsons"
MAPS_PATH       =  MAIN_PATH / "data/maps"
sys.path.append(str(DATA_PATH))
sys.path.append(str(JSONS_PATH))
sys.path.append(str(MAPS_PATH))

# config
CONFIG_PATH     =  MAIN_PATH / "config"
sys.path.append(str(CONFIG_PATH))

# log
LOG_PATH        =  MAIN_PATH / "log"
sys.path.append(str(LOG_PATH))

# Assets
ASSETS_PATH     =  MAIN_PATH / "Assets"
HEADSHOTS_PATH  =  MAIN_PATH / "Assets/HeadShots"
ICONS_PATH      =  MAIN_PATH / "Assets/Icons"
TYRES_PATH      =  MAIN_PATH / "Assets/Icons/Tyres"
sys.path.append(str(ASSETS_PATH))
sys.path.append(str(HEADSHOTS_PATH))
sys.path.append(str(ICONS_PATH))
sys.path.append(str(TYRES_PATH))






