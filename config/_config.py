import logging
from src import Database
import subprocess
import json
import paths
# https://api.f1mv.com/api/v1/circuits/63/2023 63=Bahrain

# Timing in GUI
DELAY     = 0.    #seconds # TODO 
SLEEPTIME = 0.05  #seconds
FREQ_UPDATE_PLOT = 60 #Hz

# Useful URLs
BASE_URL="https://livetiming.formula1.com/static/"
LS_URL="https://livetiming.formula1.com/signalr"
INDEX_ENDPOINT="/Index.json"

# Useful filenames
FILENAME_FEEDS="FEEDS.json"
FILENAME_URLS="SESSION_URLS.json"
FILENAME_COLORS="COLORS.json"
FILENAME_MAPS="MAPS.json"
FILENAME_DURATION="SESSION_DURATION.json"
FILENAME_LOGGER="log/myapp.log"

# Logger Info
import logging
logging.basicConfig(filename=FILENAME_LOGGER,filemode="a+", level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
LOGGER=logging.getLogger(__name__)
LOGGER_FILE=open(FILENAME_LOGGER,mode="a+")
def EMPTY_LOGGER(filepath: str=FILENAME_LOGGER):
  f=open(filepath,"w")  
  f.close()
def WRITE_EXCEPTION(err: Exception):
  LOGGER.exception(err)
  LOGGER_FILE.write("\n")
  LOGGER_FILE.flush()

# Parser
FORCE_UPDATE=False

# Database  
FEED_LIST=["CarData.z",  # CarData.z needs to be the first 
           "Position.z", # ALWAYS (base_timestamp for now taken from this)!!
           "RaceControlMessages", # this before sessionStatus!!!
           "TimingDataF1",
           "WeatherData",
           "SessionStatus",
           "TimingAppData"] 

# Live Stream Real Time
QUEUE_LENGTH_LS   = 5   # Number of messages in cache before put send them to analyzer
TIMEOUT_SR_LS     = 600 # sec
LIVE_SIM          = True # True -> simulation / False -> Real live data 
SUPERVISE_VERBOSE = 5 # sec

#GUI
MAX_WIDTH,MAX_HEIGHT = 9000,9000 #subprocess.Popen('xrandr | grep "\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE).communicate()[0].decode("utf-8").replace("\n","").split("x")
BUTTONS_HEIGHT = 20
BUTTONS_WIDTH  = 50
BUTTONS_ROWS = 4
BOTTOM_BAR_HEIGHT = 0
TOP_BAR_HEIGHT = 25 # main.panel.height in gnome-shell.css
TEL_OTHER_RATIO = 3./4.
TELEMETRY_PLOTS_WIDTH,TELEMETRY_PLOTS_HEIGHT = 635,345
FREQUENCY_TELEMETRY_UPDATE = 6 #Hz
LAPS_TO_DISPLAY            = 3 #n of laps to display
AVG_LAP_LENGTH             = 90 #s
WINDOW_DISPLAY_LENGTH = AVG_LAP_LENGTH * LAPS_TO_DISPLAY   # in s
WINDOW_DISPLAY_PROPORTION_RIGHT = 1./10
WINDOW_DISPLAY_PROPORTION_LEFT = 1. - WINDOW_DISPLAY_PROPORTION_RIGHT 
TERMINAL_SPACE = 600
TERMINAL_MODE  = True
DEBUG_PRINT    = True
DEBUG_TYRES    = False
PRINT_TIMES    = False
COLOR_DRIVERS  = json.load(open(paths.DATA_PATH / FILENAME_COLORS,"r"))
MAPS  = json.load(open(paths.DATA_PATH / FILENAME_MAPS,"r"))
SESSION_DURATION =  json.load(open(paths.DATA_PATH / FILENAME_DURATION,"r"))
WATCHLIST_DRIVERS = [str(i) for i in range(1,100)] # all drivers
WATCHLIST_TEAMS   = ["Red Bull","Ferrari","Mercedes","McLaren","Aston Martin","Alpine","AlphaTauri","Williams","Alfa Romeo","Haas"]
YEARS=["2018","2019","2020","2021","2022","2023","2024"]

DATABASE=Database.DATABASE(FEED_LIST=FEED_LIST,logger=LOGGER,logger_file=LOGGER_FILE)
