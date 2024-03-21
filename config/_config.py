import logging
from src import Database
import json
import paths
import os

##################################### Timing in GUI ############################################
DELAY     = 0.    #seconds # TODO 
SLEEPTIME = 0.05  #seconds
FREQ_UPDATE_PLOT = 60 #Hz

###################################### Useful URLs #############################################
BASE_URL="https://livetiming.formula1.com/static/"
LS_URL="https://livetiming.formula1.com/signalr"
INDEX_ENDPOINT="/Index.json"

####################################### Useful filenames #######################################
FILENAME_FEEDS="FEEDS.json"
FILENAME_URLS="SESSION_URLS.json"
FILENAME_COLORS="COLORS.json"
FILENAME_MAPS="MAPS2.json"
FILENAME_SEGMENTS="segmentsStatus.json"
FILENAME_DURATION="SESSION_DURATION.json"
FILENAME_LOGGER="log/myapp.log"

####################################### Logger Info #############################################
import logging
if "log" not in os.listdir():
  os.mkdir("log")
logging.basicConfig(filename=FILENAME_LOGGER,filemode="w", level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
LOGGER=logging.getLogger(__name__)
LOGGER_FILE=open(FILENAME_LOGGER,mode="w")
def EMPTY_LOGGER(filepath: str=FILENAME_LOGGER):
  f=open(filepath,"w")  
  f.close()
def WRITE_EXCEPTION(err: Exception):
  LOGGER.exception(err)
  LOGGER_FILE.write("\n")
  LOGGER_FILE.flush()

####################################### Updating Urls ###########################################
FORCE_UPDATE=False

##################################### Feeds to retrieve #########################################

FEED_LIST=["CarData.z",  # CarData.z needs to be the first 
           "Position.z", # ALWAYS (base_timestamp for now taken from this)!!
           "RaceControlMessages", # this before sessionStatus!!!
           "TimingDataF1",
           "WeatherData",
           "SessionStatus",
           "TimingAppData"] 

###################################### Live Stream Real Time ####################################
QUEUE_LENGTH_LS   = 5   # Number of messages in cache before put send them to analyzer
TIMEOUT_SR_LS     = 600 # sec
LIVE_SIM          = True # True -> simulation / False -> Real live data 
SUPERVISE_VERBOSE = 5 # sec

############################################## GUI ##############################################
  
  # Primary Window - Viewport
MAX_WIDTH,MAX_HEIGHT = 1920,1080 #subprocess.Popen('xrandr | grep "\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE).communicate()[0].decode("utf-8").replace("\n","").split("x")

  # Fixed Lengths
    # PNG HeadShots (width=height)
SIDE_OF_HEADSHOTS_PNG = 95

    # PNG Tyres
SIDE_OF_TYRES_PNG     = 34

    # Top - Bottom bar  # Need checks
BOTTOM_BAR_HEIGHT = 0
TOP_BAR_HEIGHT = 25 # main.panel.height in gnome-shell.css 

    # Ratio between tabs and menu
TEL_OVER_MENU_RATIO = 3./4. 

    # Infos on subplots displaying telemetry
FREQUENCY_TELEMETRY_UPDATE = 6 #Hz
LAPS_TO_DISPLAY            = 3 #n of laps to display
AVG_LAP_LENGTH             = 90 #s

  # Map
MAP_WIDTH  = int( MAX_WIDTH * (1. - TEL_OVER_MENU_RATIO) )
MAP_HEIGHT = int( 0.75 * MAP_WIDTH  )

  # Buttons 
BUTTONS_HEIGHT_MENU     = 30
BUTTONS_SPACE_MENU      = max(int(0.00625 * MAP_WIDTH),2)
BUTTONS_WIDTH_MENU      = int(0.0625 * MAP_WIDTH) # 30 over map_width=520 
BUTTONS_WIDTH_FWBW      = int(0.0825 * MAP_WIDTH)
BUTTONS_WIDTH_SAVE_TEL  = int(0.0625 * 2 * MAP_WIDTH)
BUTTONS_WIDTH_FLAG_COU  = int(0.0625 * 2 * MAP_WIDTH)
BUTTONS_WIDTH_FLAG_STA  = int(0.19  * MAP_WIDTH)
BUTTONS_WIDTH_SKIP_SEL  = int(0.23 * MAP_WIDTH)

  # Telemetry Tab
TELEMETRY_PLOTS_WIDTH  = int( (MAX_WIDTH * TEL_OVER_MENU_RATIO) / 2. - SIDE_OF_HEADSHOTS_PNG ) 
TELEMETRY_PLOTS_HEIGHT = int( (MAX_HEIGHT - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT) / 3. )
WINDOW_DISPLAY_LENGTH = AVG_LAP_LENGTH * LAPS_TO_DISPLAY   # in s
WINDOW_DISPLAY_PROPORTION_RIGHT = 1./10
WINDOW_DISPLAY_PROPORTION_LEFT = 1. - WINDOW_DISPLAY_PROPORTION_RIGHT 

  # Compare Tab
  
  # Timing Tab

  
  # Flags
TERMINAL_SPACE = 600
TERMINAL_MODE  = False
DEBUG_PRINT    = True
DEBUG_TYRES    = False
PRINT_TIMES    = False

#################################### Loading Dictionaries #######################################
COLOR_DRIVERS        = json.load(open( paths.JSONS_PATH / FILENAME_COLORS   ,"r"))
MAPS                 = json.load(open( paths.JSONS_PATH / FILENAME_MAPS     ,"r"))
SEGMENTS             = json.load(open( paths.JSONS_PATH / FILENAME_SEGMENTS ,"r"))
SESSION_DURATION     = json.load(open( paths.JSONS_PATH / FILENAME_DURATION ,"r"))

#################################### Preferences to display #####################################
WATCHLIST_DRIVERS = [str(i) for i in range(1,100)] # all drivers
WATCHLIST_TEAMS   = [
                     "Red Bull",        #  1             
                     "Ferrari",         #  2     
                     "Mercedes",        #  3      
                     "McLaren",         #  4     
                     "Aston Martin",    #  5          
                     "Alpine",          #  6    
                     "AlphaTauri",      #  7        
                     "Williams",        #  8      
                     "Alfa Romeo",      #  9        
                     "Haas"             # 10
                     ]              

##################################### Initialization ############################################
YEARS=["2018","2019","2020","2021","2022","2023","2024"]
DATABASE=Database.DATABASE(FEED_LIST=FEED_LIST,logger=LOGGER,logger_file=LOGGER_FILE)
