import dearpygui.dearpygui as dpg
import time
import threading
import datetime
import numpy as np
import SignalR_LS as SR_LS
import scipy
import json
import cv2

from config import _config


class GUI:
  def __init__(self, FORCE_UPDATE: bool=False):
    
    # to be taken from buttons 
    self._YEAR           = "none"            
    self._RACE           = "none"           
    self._SESSION        = "none"
    self._FORCE_UPDATE   = FORCE_UPDATE  
    self._filename_feeds = _config.FILENAME_FEEDS
    self._filename_urls  = _config.FILENAME_URLS
    self._LIVESIM_READY=False
    self._LIVE_SIM=_config.LIVE_SIM
    self._DEBUG_PRINT=_config.DEBUG_PRINT
    
    self._parser = _config.DATABASE._parser 
    self._database = _config.DATABASE
    self._client = SR_LS.SignalRClient(filename="data/PROVA.txt",timeout=_config.TIMEOUT_SR_LS)
    
    self._map_width=630
    self._map_height=480
    self._drivers_prev_position={}
    
    #if self._FORCE_UPDATE:
    #  self._parser.update_urls()
    # Only in LT_sim mode
    
    # Initialize the GUI
    self._MAX_WIDTH,self._MAX_HEIGHT = int(_config.MAX_WIDTH),int(_config.MAX_HEIGHT)
    self._BUTTONS_HEIGHT = _config.BUTTONS_HEIGHT
    self._BUTTONS_WIDTH  = _config.BUTTONS_WIDTH
    self._BUTTONS_ROWS = _config.BUTTONS_ROWS
    self._BOTTOM_BAR_HEIGHT = _config.BOTTOM_BAR_HEIGHT
    self._TOP_BAR_HEIGHT = _config.TOP_BAR_HEIGHT
    self._TEL_OTHER_RATIO = _config.TEL_OTHER_RATIO
    self._WINDOW_DISPLAY_LENGTH = _config.WINDOW_DISPLAY_LENGTH
    self._WINDOW_DISPLAY_PROPORTION_RIGHT = _config.WINDOW_DISPLAY_PROPORTION_RIGHT
    self._WINDOW_DISPLAY_PROPORTION_LEFT = 1 - _config.WINDOW_DISPLAY_PROPORTION_RIGHT
    self._DRIVERS_INFO = _config.COLOR_DRIVERS
    self._watchlist_drivers = _config.WATCHLIST_DRIVERS
    self._watchlist_teams = _config.WATCHLIST_TEAMS
    self._maps = _config.MAPS
    if not self._LIVE_SIM:
      self._IO_thread = threading.Thread(target=self._client.start)
    dpg.create_context()
    if _config.TERMINAL_MODE:
      self._TERMINAL_SPACE=_config.TERMINAL_SPACE
      dpg.create_viewport(title='Custom Title', width=self._MAX_WIDTH,height=self._TERMINAL_SPACE,decorated=False)
    else:
      self._TERMINAL_SPACE=0
      dpg.create_viewport(title='Custom Title', width=self._MAX_WIDTH,height=self._MAX_HEIGHT - self._BOTTOM_BAR_HEIGHT - self._TOP_BAR_HEIGHT - self._TERMINAL_SPACE,decorated=False)
    self._VIEWPORT_WIDTH = max(dpg.get_viewport_width(),1920)
    self._VIEWPORT_HEIGHT = max(dpg.get_viewport_height(),1080)
    dpg.show_viewport()
    dpg.setup_dearpygui()
    self._TEL_PLOTS_HEIGHT = _config.TELEMETRY_PLOTS_HEIGHT
    self._TEL_PLOTS_WIDTH  = _config.TELEMETRY_PLOTS_WIDTH
    
    # Useful variables (Datetime)
    self._last_message_DT                    = None
    self._last_message_displayed_DT          = None
    self._last_message_displayed_DT_position = None
    self._first_message_DT                   = None
    self._time_skipped                       = 0
    self._time_paused                        = 0
    self._BaseTimestamp                      = None
    self._seconds_to_skip                    = 5
    self._delay_T                            = _config.DELAY
    self._TIME_UPDATE_TELEMETRY_PLOT         = 1./_config.FREQ_UPDATE_PLOT
    self._TIME_UPDATE_POSITION_PLOT          = 1./_config.FREQ_UPDATE_PLOT
    self._PRINT_TIMES                        = _config.PRINT_TIMES

    self._mapScaleX = 1
    self._mapScaleY = 1
    self._angle     = 0
    self._Xoff      = 0
    self._Yoff      = 0
    
    self._StopUpdateThread = threading.Event()
    self._task_state = "running"
    self._hide_label = []
    self._driver_compare = [ None , None]
    self._sleeptime  = _config.SLEEPTIME
    self._start_compare = False
    self._start_position = False
    
    self._update_telemetry_thread = threading.Thread(target=self.update_telemetry_plot)
    self._compare_telemetry_thread = threading.Thread(target=self.Compare_Telemetry)
    self._update_position_thread = threading.Thread(target=self.update_position_plot)
    #self._process = multiprocessing.Process(target=self.update_telemetry_plot)
    #self._thread_cl = threading.Thread(target=self.update_classifier)
    #self._thread_lap = threading.Thread(target=self.update_laps)
    
    self._laps=None
    
    self._session_name,self._event_name,self._meeting_key = "","",""
    
    if self._LIVE_SIM:
      self._tabs={"choose_race": "Race_Selector",
                  "update_telemetry": "Telemetry_view",
                  "compare_telemetry": "Telemetry_compare_view"}
    else:
      self._tabs={"update_telemetry": "Telemetry_view",
                  "compare_telemetry": "Telemetry_compare_view"}
 
    
  def choose_session(self):
    """
    Brief: 
      Create GUI dropdowns to select race. Automatically detects changes in buttons before and updates 
      next buttons based on these.
    """
    race_combo_exist=dpg.does_item_exist("race")
    session_combo_exist=dpg.does_item_exist("session")
    final_button_exist=dpg.does_item_exist("final_button")

    if final_button_exist:
      dpg.delete_item(item="final_button")

    if self._YEAR!=dpg.get_value("year"):
      self._YEAR=dpg.get_value("year")
      if race_combo_exist:
        self._RACE="none"
        dpg.delete_item("race")
        if session_combo_exist:
          self._SESSION="none"
          dpg.delete_item(item="session")
      dpg.add_combo(parent="Race_Selector",items=list(self._parser._sessions_dict[self._YEAR].keys()),tag="race",default_value="None",callback=self.choose_session)
    else:
      if self._RACE!=dpg.get_value("race"):
        self._RACE=dpg.get_value("race")
        if session_combo_exist:
          self._SESSION="none"
          dpg.delete_item(item="session")
        dpg.add_combo(parent="Race_Selector",items=self._parser._sessions_dict[self._YEAR][self._RACE],tag="session",default_value="None",callback=self.choose_session)
      else:
        self._SESSION=dpg.get_value("session")
        dpg.add_button(parent="Race_Selector",tag="final_button",label="New Window",height=self._BUTTONS_HEIGHT,width=self._BUTTONS_WIDTH,callback=self.new_window)

  def new_window(self):
    """
    Brief:
      Close choose_race window and create a live_stream object. Initialize drivers list and
      set LIVESIM_READY to true. 
      Needs changes..
    """
    dpg.configure_item("Race_Selector",show=False)
    if self._LIVE_SIM:
      self._database.merger(YEAR=self._YEAR,NAME=self._RACE,SESSION=self._SESSION)
    else:
      pass
      #self._client.start()
    
    while self._database.get_drivers_list()==None:
      if self._DEBUG_PRINT:
        print("Stuck inside new_window in GUI...")
      time.sleep(1)
    
    self._drivers_list=sorted(self._database.get_drivers_list(),key=int)
    self.initialize_plot()
    print("Plot initialized!")
    self._LIVESIM_READY=True
    #for driver in self._drivers_list:
    #  if driver not in self._LS._analyzer._laptimes_2.keys():
    #    self._LS._analyzer._laptimes_2[driver]={}



  # def skip_interesting_event(self,sender):
  #   #print(sender, " ",dpg.get_value(item=sender)," ")
  #   for _,tag in dpg.get_item_children(sender).items():
  #     if len(tag)!=0:
  #       self._skip_to_time=dpg.get_value(item=tag[0]) # horrible...
  #       break
  #   self._LS.reset_telemetry_dictionary()
  #   self.reset_indices()
  #   self._index=self.from_time_to_index(self._skip_to_time-self._window_display_proportion_left*self._window_display_length)
    

####################################### REWORK NEEDED ################################################
  def update_classifier(self):
    while not self._LIVESIM_READY:
      time.sleep(self._sleeptime)
    while True:
      while self._task_state=="pause":
        time.sleep(self._sleeptime)
      while self._index_clas<=self._index:
        #print(self._index_clas," ",self._index)
        time_ms=self._times[self._index_clas]
        value=self._LS._full_data[time_ms]
        if "TimingAppData" in self._LS._full_data[time_ms].keys():
          self._LS._analyzer.msg_sorter(value)
          #if self._index-self._index_clas<10:
          #    print("Classification: ", self._LS._analyzer._classification, " ",self._LS._analyzer._laptimes)
        self._index_clas+=1

  def update_laps(self):
    while not self._LIVESIM_READY:
      time.sleep(self._sleeptime)
    while True:
      while self._task_state=="pause":
        time.sleep(self._sleeptime)
      while self._index_lap<=self._index:
        #print(self._index_lap," ",self._index)
        time_ms=self._times[self._index_lap]
        value=self._LS._full_data[time_ms]
        if "TimingDataF1" in self._LS._full_data[time_ms].keys():
          self._LS._analyzer.msg_sorter(value)
          #if self._index-self._index_lap<10:
          #print("Laptimes2: ",self._LS._analyzer._laptimes_2)
        self._index_lap+=1

########################################################################################################

  def add_buttons(self):
    """
      Initialize all buttons.
    """
    #int_times=self._LS._interesting_times
    with dpg.group(label="buttons1",tag="buttons1",horizontal=True,pos=(10,0)):
      PLAY_LABEL="Pause" if self._task_state=="running" else "Start"
      dpg.add_button(label=PLAY_LABEL,tag="PLAY_BUTTON",width=self._BUTTONS_WIDTH,height=self._BUTTONS_HEIGHT,callback=self.pause_button)
      dpg.add_button(label="-"+str(self._seconds_to_skip)+"s",width=self._BUTTONS_WIDTH,height=self._BUTTONS_HEIGHT,tag="backward",callback=self.backward_button)
      dpg.add_button(label="+"+str(self._seconds_to_skip)+"s",width=self._BUTTONS_WIDTH,height=self._BUTTONS_HEIGHT,tag="forward",callback=self.forward_button)
      dpg.add_button(label="kill",width=self._BUTTONS_WIDTH,height=self._BUTTONS_HEIGHT,callback=self.kill_button)
      #dpg.add_button(label="Laptimes",width=self._BUTTONS_WIDTH,height=self._BUTTONS_HEIGHT,callback=self.display_laptimes)
    with dpg.group(label="buttons2",tag="buttons2",horizontal=True,pos=(10,self._BUTTONS_HEIGHT)):  
      dpg.add_input_int(label="Update +/- [s]",tag="skip_seconds",default_value=self._seconds_to_skip,width=self._BUTTONS_WIDTH,min_value=1,max_value=300,min_clamped=True,max_clamped=True,step=0,step_fast=0,on_enter=True,callback=self.set_skip_time)
      dpg.add_input_int(label="Delay [s]",tag="delay",width=self._BUTTONS_WIDTH,min_value=0,max_value=300,default_value=self._delay_T,min_clamped=True,max_clamped=True,step=0,step_fast=0,on_enter=True,callback=self.set_delay_time)
      dpg.add_combo(tag="Race_Map",default_value="None",items=list(self._maps.keys()),width=self._BUTTONS_WIDTH,callback=self.change_map_background)
      #dpg.add_input_float(label="Map_Scale_X",tag="mapScaleX",width=50,min_value=10,max_value=100,default_value=50,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="Map_Scale_Y",tag="mapScaleY",width=50,min_value=10,max_value=100,default_value=50,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="X-Off",tag="XOFF",width=50,min_value=-640,max_value=640,default_value=320,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="Y-Off",tag="YOFF",width=50,min_value=-480,max_value=480,default_value=240,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="angle",tag="angle",width=50,min_value=0,max_value=360,default_value=0,min_clamped=True,max_clamped=True,step=0,step_fast=0,on_enter=True,callback=self.rotate_map)
    n_rows=len(self._drivers_list) // 8 + (len(self._drivers_list) % 8 > 0)
    for n_row in range(1,n_rows+1):
      with dpg.group(label="buttons"+str(2+n_row),tag="buttons"+str(2+n_row),horizontal=True,height=self._BUTTONS_HEIGHT,pos=(10,self._BUTTONS_HEIGHT*(1+n_row))):
        self.show_telemetry_button(row_number=n_row)
        self._BUTTONS_ROWS=2+n_row

  def pause_button(self):
    if self._task_state == "running":
      self._task_state = "pause"
      dpg.set_item_label(item="PLAY_BUTTON",label="Play")
      print("Pausing..")
    else:
      self._task_state="running"
      dpg.set_item_label(item="PLAY_BUTTON",label="Pause")
      print("Resuming..")

  def set_skip_time(self):
    self._seconds_to_skip=dpg.get_value("skip_seconds")
    dpg.configure_item(item="backward",label="-"+str(self._seconds_to_skip)+"s")
    dpg.configure_item(item="forward",label="+"+str(self._seconds_to_skip)+"s")
    # dpg.set_item_label(item="backward",label="-"+self._seconds_to_skip+"s")
    # dpg.set_item_label(item="forward",label="+"+self._seconds_to_skip+"s")
      
  def set_delay_time(self):
    if dpg.get_value("delay")<self._delay_T:
      self._time_skipped+=(self._delay_T-dpg.get_value("delay"))
    else:
      self._time_paused+=(dpg.get_value("delay")-self._delay_T)
    self._delay_T=dpg.get_value("delay")    
    
    
  def forward_button(self):
    """
      Forward 5s
    """
    if self._DEBUG_PRINT:
      print(self._last_message_displayed_DT.timestamp()," ",self._time_skipped," ",self._seconds_to_skip," ",self._BaseTimestamp," ",self._last_message_DT.timestamp()," ",self._last_message_displayed_DT.timestamp()+self._seconds_to_skip," ",round(self._BaseTimestamp)+round(self._last_message_DT.timestamp()))
    if self._last_message_displayed_DT.timestamp()+self._seconds_to_skip<=self._last_message_DT.timestamp():
      self._time_skipped+=self._seconds_to_skip
     
  def backward_button(self):
    """
      Back 5s
    """
    if self._DEBUG_PRINT:
      print(self._last_message_displayed_DT.timestamp()," ",self._time_skipped," ",self._seconds_to_skip," ",self._BaseTimestamp," ",self._first_message_DT.timestamp()," ",self._first_message_DT.timestamp()-self._seconds_to_skip," ",self._BaseTimestamp+self._first_message_DT.timestamp())
    if self._last_message_displayed_DT.timestamp()-self._seconds_to_skip>=self._first_message_DT.timestamp():
      self._time_skipped-=self._seconds_to_skip
    
  def show_telemetry_button(self,row_number):
    selected_teams=self._watchlist_teams[4*(row_number-1):4*row_number]
    for team in selected_teams:
      for driver in self._drivers_list:
        if team==self._DRIVERS_INFO[driver]["team"]:
          if driver in self._watchlist_drivers:
            dpg.add_checkbox(label=self._DRIVERS_INFO[driver]["abbreviation"],tag=driver+"ST",default_value=True)
          else:
            dpg.add_checkbox(label=self._DRIVERS_INFO[driver]["abbreviation"],tag=driver+"ST",default_value=False)
      #dpg.add_bool_value(default_value=True,source=driver+"ST")

  def kill_button(self):
    self._StopUpdateThread.set()
    dpg.destroy_context()

  # def print_button(self): # ???
  #   print("Tel: ",dpg.get_item_height(item="Tel"),"  ","Buttons: ",dpg.get_item_height(item="buttons"))

  def hide_show_tel(self,driver):
    if dpg.get_value(driver+"ST"):
      dpg.show_item(driver+"s")
      dpg.show_item(driver+"t")
      dpg.show_item(driver+"b")
    else:    
      dpg.hide_item(driver+"s")
      dpg.hide_item(driver+"t")
      dpg.hide_item(driver+"b")

  def display_laptimes(self):
    displayed_laptimes={}
    db_laps=self._database.get_dictionary(feed="TimingDataF1")
    for driver,laps in db_laps.items():
      if driver not in displayed_laptimes.keys():
        displayed_laptimes[driver]={}
      for lap,data_lap in db_laps[driver].items():
        displayed_laptimes[driver][lap]={"DT": data_lap["DateTime"].ctime(),
                                         "VS": data_lap["ValueString"],
                                         "VS_s": data_lap["ValueInt_sec"]}
    print(json.dumps(displayed_laptimes,indent=2))

  def move_menu_bar_when_scrolling(self):
    current_y_scroll=dpg.get_y_scroll(item="Primary window")
    #dpg.set_item_pos(item="weather1",pos=(dpg.get_item_pos(item="weather1")[0],dpg.get_item_pos(item="weather1")[1]+current_y_scroll-self._y_scroll))
    #dpg.set_item_pos(item="weather2",pos=(dpg.get_item_pos(item="weather2")[0],dpg.get_item_pos(item="weather2")[1]+current_y_scroll-self._y_scroll))
    #dpg.set_item_pos(item="Track_Map",pos=(dpg.get_item_pos(item="Track_Map")[0],dpg.get_item_pos(item="Track_Map")[1]+current_y_scroll-self._y_scroll))
    #dpg.set_item_pos(item="menu_bar_buttons_weather",pos=(dpg.get_item_pos(item="menu_bar_buttons_weather")[0],dpg.get_item_pos(item="menu_bar_buttons_weather")[1]+current_y_scroll-self._y_scroll))
    #n_button=1
    #while True:
    #  if dpg.does_item_exist(item="buttons"+str(n_button)):
    #    #print(n_button,dpg.get_item_children(item="buttons"+str(n_button)))
    #    dpg.set_item_pos(item="buttons"+str(n_button),pos=(dpg.get_item_pos(item="buttons"+str(n_button))[0],dpg.get_item_pos(item="buttons"+str(n_button))[1]+current_y_scroll-self._y_scroll))
    #    n_button+=1
    #  else:
    self._y_scroll=current_y_scroll
    #    return 


#########################################################################################################

  def change_map_background(self):
    if dpg.does_item_exist(item="map_background"):
      dpg.delete_item(item="map_background") 
      dpg.delete_item(item="map_background_texture")
    
    map_dict=str(_config.paths.DATA_PATH / self._maps[dpg.get_value("Race_Map")]["map"])
    width, height, channels, data = dpg.load_image(map_dict)

    #self._mapScaleX = self._maps[dpg.get_value("Race_Map")]["mapScaleX"]
    #self._mapScaleY = self._maps[dpg.get_value("Race_Map")]["mapScaleY"]
    #self._Xoff      = self._maps[dpg.get_value("Race_Map")]["X-Off"]
    #self._Yoff      = self._maps[dpg.get_value("Race_Map")]["Y-Off"]
    #self._angle     = self._maps[dpg.get_value("Race_Map")]["angle"]
    
    #self._map_width,self._map_height=width,height
    with dpg.texture_registry():
      dpg.add_static_texture(width=width, height=height, default_value=data, tag="map_background_texture")

    
    dpg.draw_image(texture_tag="map_background_texture",tag="map_background",parent="drawlist_map_position",pmin=(0,0),pmax=(630,480),show=True)

  def transform_position_from_F1_to_dpg(self,x,y):
    xlims=self._maps[dpg.get_value("Race_Map")]["xlim"]
    ylims=self._maps[dpg.get_value("Race_Map")]["ylim"]
    x_shifted=x-xlims[0]
    x_scaled=x_shifted/self._maps[dpg.get_value("Race_Map")]["xscale"]

    y_shifted=y-ylims[0]
    y_scaled=y_shifted/self._maps[dpg.get_value("Race_Map")]["yscale"]
    y_updown=self._map_height-y_scaled

    return x_scaled,y_updown

  def add_driver_tel_plot(self,number,parent,driver):
    nr=int(number) # 0 -> 19 !
    x_pos=self._TEL_PLOTS_WIDTH*(nr%2) 
    y_pos=self._TEL_PLOTS_HEIGHT*(nr//2)+self._TOP_BAR_HEIGHT
    with dpg.group(pos=(x_pos,y_pos),width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT,tag="wdw"+driver,parent=parent):
      with dpg.subplots(rows=3,columns=1,row_ratios=(3,1,1),link_all_x=True,no_align=False,no_resize=False,label=self._DRIVERS_INFO[driver]["full_name"],tag=self._DRIVERS_INFO[driver]["full_name"],width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT):
        with dpg.plot(tag="speed"+driver,anti_aliased=True):    
          dpg.add_plot_axis(dpg.mvXAxis,tag="x_axis_SPEED"+driver,time=True,no_tick_labels=True,no_tick_marks=True)
          dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis_SPEED"+driver)
          dpg.set_axis_limits("y_axis_SPEED"+driver, -2, 399)
          dpg.add_line_series(x=[0],y=[0],label=driver+"s",parent="y_axis_SPEED"+driver,tag=driver+"s")
          #dpg.set_item_label(item=driver+"s",label=self._DRIVERS_INFO[driver]["abbreviation"])
          dpg.bind_item_theme(driver+"s",driver+"_color")
          
        with dpg.plot(tag="throttle"+driver,anti_aliased=True):    
          dpg.add_plot_axis(dpg.mvXAxis,tag="x_axis_THROTTLE"+driver,time=True,no_tick_labels=True,no_tick_marks=True)
          dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis_THROTTLE"+driver,no_tick_labels=True,no_tick_marks=True)
          dpg.set_axis_limits("y_axis_THROTTLE"+driver, -2, 101)
          dpg.add_line_series(x=[0],y=[0],label=driver+"t",parent="y_axis_THROTTLE"+driver,tag=driver+"t")
          #dpg.add_plot_legend(show=False)
          dpg.bind_item_theme(driver+"t",driver+"_color")
            
        with dpg.plot(tag="brake"+driver,anti_aliased=True):    
          dpg.add_plot_axis(dpg.mvXAxis,tag="x_axis_BRAKE"+driver)
          dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis_BRAKE"+driver,no_tick_labels=True,no_tick_marks=True)
          dpg.set_axis_limits("y_axis_BRAKE"+driver, -2, 101)
          dpg.add_line_series(x=[0],y=[0],label=driver+"b",parent="y_axis_BRAKE"+driver,tag=driver+"b")
          #dpg.add_plot_legend(show=False)
          dpg.bind_item_theme(driver+"b",driver+"_color")

  def initialize_plot(self):
    # telemetry view tab    
    with dpg.group(label=self._YEAR+"-"+" ".join(self._RACE.split("_"))+"-"+self._SESSION,tag="Telemetry_view",show=True,parent="Primary window"):
      
      with dpg.window(label="menu_bar_buttons_weather",tag="menu_bar_buttons_weather",width=630,height=self._BUTTONS_HEIGHT*self._BUTTONS_ROWS,pos=(self._TEL_PLOTS_WIDTH*2+10,self._TOP_BAR_HEIGHT),no_title_bar=True,no_resize=True,no_move=True):
        # weather group
        with dpg.group(label="Weather1",tag="weather1",horizontal=False,pos=(7.3*self._BUTTONS_WIDTH,0)):  
          dpg.add_text(default_value="AirTemp:",  tag="AirTemp")
          dpg.add_text(default_value="TrackTemp:",tag="TrackTemp")
          dpg.add_text(default_value="Humidity:", tag="Humidity")
          dpg.add_text(default_value="WindDirection:", tag="WindDirection")
        with dpg.group(label="Weather2",tag="weather2",horizontal=False,pos=(7.3*self._BUTTONS_WIDTH+130,0)):
          dpg.add_text(default_value="WindSpeed:",tag="WindSpeed")
          dpg.add_text(default_value="Pressure:", tag="Pressure")
          dpg.add_text(default_value="Rainfall:", tag="Rainfall")
        with dpg.group(label="Session_Info",tag="sessioninfo",horizontal=False,pos=(7.75*self._BUTTONS_WIDTH,self._BUTTONS_HEIGHT*(self._BUTTONS_ROWS-0.8))):
          dpg.add_text(default_value="Current Time:", tag="Actual_Time")
          dpg.add_text(default_value="Status:", tag="Session_Status")
          dpg.add_text(default_value="Session: "+self._database.get_session_type(), tag="Session_Name")
          # if you add or delete some texts inside "weather" change the value of 
          # 7 in add_drawlist below!

        # buttons
        self._drivers_list=sorted(self._drivers_list,key=int)
        self.add_buttons()
        self._y_scroll=dpg.get_y_scroll(item="Primary window")
      
      with dpg.window(label="Track_Map",tag="Track_Map",width=630,height=480,pos=(self._TEL_PLOTS_WIDTH*2+10,self._TOP_BAR_HEIGHT+self._BUTTONS_HEIGHT*self._BUTTONS_ROWS+10),no_title_bar=True,no_resize=True,no_move=True):
        #with dpg.window(width=640,height=480,pos=(),tag="map_window"):
          dpg.add_drawlist(width=630,height=480,pos=(0,0),tag="drawlist_map_position")
          #dpg.draw_circle(color=(255,0,0,255),center=(100,100),radius=5,fill=(255,0,0,255),tag="circle",parent="drawlist_map_position")
      
      with dpg.window(label="RaceMessages",tag="Race_Messages",width=630/2,height=420,pos=(self._TEL_PLOTS_WIDTH*2+10+630/2,self._TOP_BAR_HEIGHT+self._BUTTONS_HEIGHT*self._BUTTONS_ROWS+10+485+5),no_title_bar=True,no_resize=True,no_move=True):
        #with dpg.window(width=640,height=480,pos=(),tag="map_window"):
          dpg.add_text(tag="race_msgs",default_value="",wrap=308)
          #dpg.draw_circle(color=(255,0,0,255),center=(100,100),radius=5,fill=(255,0,0,255),tag="circle",parent="drawlist_map_position")
      
      # telemetry plots
      self._annotations_telemetry_plot = {}
      self._drivers_watchlist_telemetry=[]
      for team in self._watchlist_teams:
        for driver in self._drivers_list:
          self._annotations_telemetry_plot[driver]=[] # [[time,speed,id,tag=("min"/"max")],[...]]
          # initialize dict that is needed later for keeping
          # track of latest id of the annotations in telemetry
          if team==self._DRIVERS_INFO[driver]["team"]:
            self._drivers_watchlist_telemetry.append(driver)
      for nr,driver in zip(range(len(self._drivers_list)),self._drivers_watchlist_telemetry):
        self.add_driver_tel_plot(number=nr,parent="Telemetry_view",driver=driver)

  def is_personal_fastest_up_to_now(self,Laps,laptime,driver):
    for nlap,lap in Laps[driver].items():
      if lap["TimeStamp"]<self._last_message_displayed_DT.timestamp()-self._BaseTimestamp:
        if laptime>lap["ValueInt_sec"]:
          return False
    return True
      
  def is_overall_fastest_up_to_time(self,Laps,laptime):    
    for driver in self._drivers_list:
      for nlap,lap in Laps[driver].items():
        if lap["TimeStamp"]<self._last_message_displayed_DT.timestamp()-self._BaseTimestamp:
          if laptime>lap["ValueInt_sec"]:
            return False
    return True 

  def update_telemetry_plot(self):
    if self._LIVE_SIM:
      while not self._LIVESIM_READY: # LiveSim ready to be updated
        print("Waiting for LIVESIM_READY to turn on in GUI...")
        time.sleep(1)
    while self._database.get_first_datetime() is None: # Waiting for first message to arrive
      if self._DEBUG_PRINT:
        print("Waiting for first_datetime to arrive in GUI...")
      #print("Still no messages..")
      time.sleep(1)
    # ok now we can start..
    # .. maybe.. (weird but for now it should works)
    while self._database.get_drivers_list() is None:
      #print(self._database.get_dictionary("CarData.z"))
      if self._DEBUG_PRINT:
        print("Waiting for drivers_list to arrive in GUI...")
      #print("Still no drivers list..")
      time.sleep(1)
    
    print("Driver list arrived!")
    while not self._database.is_first_RD_arrived():
      if self._DEBUG_PRINT:
        print("Waiting for first RD message to arrive..")
      time.sleep(1)
    
    if self._LIVE_SIM:
      while not self._database.is_merge_ended():
        if self._DEBUG_PRINT:
          print("Waiting for DB to finish the merge..")
        time.sleep(0.25)
    
    self._drivers_list=self._database.get_drivers_list()
    
    if not self._LIVE_SIM:
      self.initialize_plot()
      
    self._first_message_DT        = self._database.get_first_datetime()
    self._BaseTimestamp           = self._database.get_base_timestamp()
    self._first_message_DT_myTime = datetime.datetime.now() 
    
    # sleep initial delay
    time.sleep(self._delay_T)
    self._time_paused+=self._delay_T
    self._start_compare=True
    self._start_position=True
    # ok now we have everything and we can start!
    while True:
      while self._task_state=="pause":
        time.sleep(self._sleeptime)
        self._last_message_DT = self._database.get_last_datetime()
        self._time_paused+=self._sleeptime
        # if it's paused than... sleep
        if self._StopUpdateThread.is_set():
          # if kill_buttons is called then we kill the run..
          break      
      if self._StopUpdateThread.is_set():
        # .. maybe redundant but this prevent the GUI to not kill itself if the run is paused. 
        break      
      # works only for LT
      self._last_message_DT            = self._database.get_last_datetime()
      #self._last_message_displayed_DT = self._database.get_last_datetime()     
      self._last_message_displayed_DT  = self._first_message_DT + datetime.timedelta(seconds=self._time_skipped) + (datetime.datetime.now() - datetime.timedelta(seconds=self._time_paused) - self._first_message_DT_myTime)
      
      dpg.set_value(item="Actual_Time",value="Current Time: "+self._last_message_displayed_DT.strftime("%H:%M:%S"))
      dpg.set_value(item="Session_Status",value="Status: "+str(self._database.get_actual_session_status(self._last_message_displayed_DT)))
      
      #print("BBB")
      slice_between_times = self._database.get_slice_between_times(
                                  start_time=self._last_message_displayed_DT-datetime.timedelta(seconds=self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_LEFT),
                                  end_time=self._last_message_displayed_DT)
      Telemetry_to_be_plotted = self._database.get_dictionary(feed="CarData.z")
      Laps = self._database.get_dictionary(feed="TimingDataF1")
      
      
      minx=max(self._first_message_DT.timestamp()-self._BaseTimestamp,self._last_message_displayed_DT.timestamp()-self._BaseTimestamp-self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_LEFT)
      maxx=max(self._first_message_DT.timestamp()-self._BaseTimestamp+self._WINDOW_DISPLAY_LENGTH,self._last_message_displayed_DT.timestamp()-self._BaseTimestamp+self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_RIGHT)
      
      #print("\n ",self._database.get_dictionary(feed="RaceControlMessages"),"\n")
      
      x_label=[]
      minute=None
      for Timestamp in np.arange(int(minx),int(maxx),1):
        DT=datetime.datetime.fromtimestamp(Timestamp+self._BaseTimestamp)
        if DT.second%10==0:
          hour=str(DT.hour).zfill(2)
          prev_minute=minute
          minute=str(DT.minute).zfill(2)
          second=str(DT.second).zfill(2)
          if DT.minute!=prev_minute and prev_minute!=None:
            x_label.append(("\n"+hour+"-"+minute,Timestamp-int(second)))
          x_label.append((second,Timestamp))
            
      x_label=tuple(x_label)
      
      for driver,telemetry in Telemetry_to_be_plotted.items():
        if driver in self._drivers_list:
          speeds=telemetry["Speed"][slice_between_times]
          times=telemetry["TimeStamp"][slice_between_times]
          
          maxima=scipy.signal.argrelextrema(np.array(speeds), np.greater,order=3)[0]
          minima=scipy.signal.argrelextrema(np.array(speeds), np.less,order=3)[0]
          
          # 1. check if old anns are also in new anns
            # 2. if true: skip
            # 3. if false and if old ann lower min(new anns) -> delete ann
          # 4. plot all new anns that are greater than max(old anns)
          last_time_ann=0
          first_time_ann=1e11
          last_id_min=0
          last_id_max=0
          ann_to_pop=[]
          #print("\n",driver," ",self._annotations_telemetry_plot[driver])
          for j,old_annotation in zip(range(len(self._annotations_telemetry_plot[driver])),self._annotations_telemetry_plot[driver]):
            #print(old_annotation)
            t,speed,id,tag = old_annotation
            t=float(t)
            if t not in times and dpg.does_item_exist(item=driver+"_"+tag+"_"+str(id)):
              dpg.delete_item(item=driver+"_"+tag+"_"+str(id))
              ann_to_pop.append(j)
            
            #print(t,type(t),times[0],type(times[0]))
            if t>last_time_ann:
              last_time_ann=t
            if t<first_time_ann:
              first_time_ann=t
              
            if tag=="min":
              last_id_min=id
            elif tag=="max":
              #print("driver",driver,id,type(id),last_id_max,type(last_id_max))
              last_id_max=id
          
          ann_to_pop.sort(reverse=True)
          for ann in ann_to_pop:
            self._annotations_telemetry_plot[driver].remove(self._annotations_telemetry_plot[driver][ann])
          
          for i,idx in zip(range(1,len(maxima)+1),maxima):
            if times[idx]>last_time_ann or times[idx]<first_time_ann: 
              # print("driver",driver,type(driver))
              # print("time",times[idx],type(times[idx]))
              # print("speed",speeds[idx],type(speeds[idx]))
              # print("last_id",last_id_max,type(last_id_max))
              if driver in self._watchlist_drivers:
                dpg.add_plot_annotation(label=str(int(speeds[idx])),tag=driver+"_max_"+str(last_id_max+i), default_value=(times[idx],speeds[idx]), offset=(0,-5), color=[0,0,0,0],parent="speed"+driver)
              self._annotations_telemetry_plot[driver].append([times[idx],speeds[idx],last_id_max+i,"max"])
              
          for i,idx in zip(range(1,len(minima)+1),minima):
            if times[idx]>last_time_ann or times[idx]<first_time_ann: 
              if driver in self._watchlist_drivers:
                dpg.add_plot_annotation(label=str(int(speeds[idx])),tag=driver+"_min_"+str(last_id_min+i), default_value=(times[idx],speeds[idx]), offset=(0,+5), color=[0,0,0,0],parent="speed"+driver)
              self._annotations_telemetry_plot[driver].append([times[idx],speeds[idx],last_id_min+i,"min"])
          
          if driver in Laps.keys():
            if len(Laps[driver].keys())>0:
              for nlap,lap in Laps[driver].items():
                # if it's inside window displayed
                if lap["TimeStamp"]>minx and lap["TimeStamp"]<self._last_message_displayed_DT.timestamp()-self._BaseTimestamp and driver in self._watchlist_drivers:
                  # if it does not exist, draw it based on wheter it's fastest etc
                  if not dpg.does_item_exist(item="vline"+driver+lap["ValueString"]):
                    dpg.add_vline_series(x=[lap["TimeStamp"]],tag="vline"+driver+lap["ValueString"],label=str(nlap)+" "+lap["ValueString"],parent="y_axis_SPEED"+driver)
                    dpg.add_plot_annotation(label=lap["ValueString"],tag="vline"+driver+lap["ValueString"]+"_ann", default_value=(lap["TimeStamp"],dpg.get_axis_limits("y_axis_SPEED"+driver)[1]-5), offset=(2,), color=[0,0,0,0],parent="speed"+driver)
                  if self.is_overall_fastest_up_to_time(Laps,lap["ValueInt_sec"]):
                    if dpg.get_item_theme(item="vline"+driver+lap["ValueString"])!=dpg.get_alias_id(alias="BestOverallLap"):
                      dpg.bind_item_theme("vline"+driver+lap["ValueString"],"BestOverallLap") 
                  elif self.is_personal_fastest_up_to_now(Laps,lap["ValueInt_sec"],driver):
                    if dpg.get_item_theme(item="vline"+driver+lap["ValueString"])!=dpg.get_alias_id(alias="BestPersonalLap"):
                      dpg.bind_item_theme("vline"+driver+lap["ValueString"],"BestPersonalLap")
                  else:
                    if dpg.get_item_theme(item="vline"+driver+lap["ValueString"])!=dpg.get_alias_id(alias="NormalLap"):
                      dpg.bind_item_theme("vline"+driver+lap["ValueString"],"NormalLap")
                # if it is outside the displayed area delete it
                else:
                  if dpg.does_item_exist(item="vline"+driver+lap["ValueString"]):
                    dpg.delete_item(item="vline"+driver+lap["ValueString"])
                    dpg.delete_item(item="vline"+driver+lap["ValueString"]+"_ann")
          self.hide_show_tel(driver)
          
          dpg.set_value(item=driver+"s", value=[times,speeds])
          dpg.set_value(item=driver+"t", value=[times,telemetry["Throttle"][slice_between_times]])
          dpg.set_value(item=driver+"b", value=[times,telemetry["Brake"][slice_between_times]])
          dpg.set_axis_limits("x_axis_BRAKE"+driver, minx, maxx)
          dpg.set_axis_ticks(axis="x_axis_BRAKE"+driver,label_pairs=x_label)
          dpg.set_axis_ticks(axis="x_axis_THROTTLE"+driver,label_pairs=x_label)
          dpg.set_axis_ticks(axis="x_axis_SPEED"+driver,label_pairs=x_label)
          
          compound,isnew,stint,age=self._database.get_driver_tyres(driver,self._last_message_displayed_DT)
          dpg.set_item_label(item=self._DRIVERS_INFO[driver]["full_name"],label=self._DRIVERS_INFO[driver]["full_name"]+" "+compound+" "+str(isnew)+" "+str(stint)+" "+str(age))
          
      #print(minx," ",maxx," " ,x_label[:10])
      msgs=self._database.get_race_messages_before_time(self._last_message_displayed_DT)
      if msgs!=dpg.get_value(item="race_msgs"):
        dpg.set_value(item="race_msgs",value=msgs)
        dpg.set_y_scroll(item="Race_Messages",value=dpg.get_y_scroll_max(item="Race_Messages"))  
      
      weather_data=self._database.get_last_msg_before_time(feed="WeatherData",sel_time=self._last_message_displayed_DT)
      for key,value in weather_data.items():
        #print(key)
        if key in ["AirTemp","TrackTemp","Humidity","WindSpeed","WindDirection","Pressure","Rainfall"]:
          dpg.set_value(item=key,value=str(key)+":"+str(value))
      
      if self._PRINT_TIMES:
        print(self._last_message_displayed_DT.timestamp()," ",minx, " ",maxx," ",dpg.get_axis_limits("x_axis_SPEED"))
              
      time.sleep(self._TIME_UPDATE_TELEMETRY_PLOT)

#####################################################################################s

  def Set_Corners(self):
    map_dict=json.load(open(_config.paths.DATA_PATH / (self._maps[dpg.get_value("map")]["corners"]),"r"))
    self._xTurns=[]
    offset_value=dpg.get_value("slide_corner")
    for corner,position in map_dict["rel_distance"].items():
      self._xTurns.append((corner,round(position+offset_value,5)))
    self._xTurns=tuple(self._xTurns)
    #print(self._xTurns)
  
  def print_speed_drivers(self):
    if dpg.get_value("LAP-1")!="None" and dpg.get_value("DRV-1")!="None":
      x_compare=dpg.get_value("speed_compare_line")+self._OffSet_1
      for x,i in zip(self._Space1/self._Total_space1+self._OffSet_1,range(len(self._Space1))):
        if x_compare<x:
          if i!=0:
            dpg.set_value(item="DRV-1-SPEED_TEXT",value=self._DRIVERS_INFO[dpg.get_value("DRV-1")]["abbreviation"]+" "+str(int(self._Speeds1[i-1])))
          else:
            dpg.set_value(item="DRV-1-SPEED_TEXT",value=self._DRIVERS_INFO[dpg.get_value("DRV-1")]["abbreviation"]+" "+str(int(self._Speeds1[i])))
          break
        #print(x_compare,x)
    if dpg.get_value("LAP-2")!="None" and dpg.get_value("DRV-2")!="None":
      x_compare=dpg.get_value("speed_compare_line")+self._OffSet_2
      for x,i in zip(self._Space2/self._Total_space2+self._OffSet_2,range(len(self._Space2))):
        if x_compare<x:
          if i!=0:
            dpg.set_value(item="DRV-2-SPEED_TEXT",value=self._DRIVERS_INFO[dpg.get_value("DRV-2")]["abbreviation"]+" "+str(int(self._Speeds2[i-1])))
          else:
            dpg.set_value(item="DRV-2-SPEED_TEXT",value=self._DRIVERS_INFO[dpg.get_value("DRV-2")]["abbreviation"]+" "+str(int(self._Speeds2[i])))
          break

  def Set_Offset_Space(self,sender):
    if sender=="OFF_DRV1":
      self._OffSet_1=dpg.get_value("OFF_DRV1")
      if type(self._arg_maxima1)!=str: 
        if (dpg.get_value("DRV-1")!=self._DRV1 or int(dpg.get_value("LAP-1").split(" ")[0])!=self._LAP1):
          for i in range(len(self._arg_maxima1)):
            dpg.delete_item(item=self._DRV1+"_max1_"+str(i))
          self._update_ann1=True
      if type(self._arg_minima1)!=str:
        if (dpg.get_value("DRV-1")!=self._DRV1 or int(dpg.get_value("LAP-1").split(" ")[0])!=self._LAP1):
          for i in range(len(self._arg_minima1)):
            dpg.delete_item(item=self._DRV1+"_min1_"+str(i))
      self._update_ann1=True
    elif sender=="OFF_DRV2":
      self._OffSet_2=dpg.get_value("OFF_DRV2")
      if type(self._arg_maxima2)!=str: 
        if (dpg.get_value("DRV-2")!=self._DRV2 or int(dpg.get_value("LAP-2").split(" ")[0])!=self._LAP2):
          for i in range(len(self._arg_maxima2)):
            dpg.delete_item(item=self._DRV2+"_max2_"+str(i))
          self._update_ann2=True
      if type(self._arg_minima2)!=str:
        if (dpg.get_value("DRV-2")!=self._DRV2 or int(dpg.get_value("LAP-2").split(" ")[0])!=self._LAP2):
          for i in range(len(self._arg_minima2)):
            dpg.delete_item(item=self._DRV2+"_min2_"+str(i))
          self._update_ann2=True 
    else:
      print(sender, " case not specifiec in Set_Offset_Space...")         
   
  def Select_Driver_Compare(self,sender):
    laps=self._database.get_dictionary(feed="TimingDataF1")  # Driver -> Nlap ->  {DateTime,ValueString,ValueInt_sec}
    
    if sender=="DRV-1":
      ITEM="LAP-1"
      dpg.set_value(item="DRV-1-DRV_TEXT",value=self._DRIVERS_INFO[dpg.get_value(sender)]["abbreviation"]+":  ")
    elif sender=="DRV-2":
      ITEM="LAP-2"
      dpg.set_value(item="DRV-2-DRV_TEXT",value=self._DRIVERS_INFO[dpg.get_value(sender)]["abbreviation"]+":  ")
    else:
      print(sender, " not picked..")
    if dpg.get_value(sender) in laps.keys():
      laps_to_show=[str(nlap)+" "+lap_dict["ValueString"]  for nlap,lap_dict in laps[dpg.get_value(sender)].items() if lap_dict["DateTime"]<self._last_message_displayed_DT]
      print(laps[dpg.get_value(sender)][list(laps[dpg.get_value(sender)].keys())[0]]["DateTime"],self._last_message_displayed_DT)
      dpg.configure_item(item=ITEM,items=laps_to_show,default_value=None)
    # if i change the driver then laps need to go to default value again

          
  def Compare_Telemetry(self):
    while not self._start_compare:
      #print(self._database.get_dictionary("CarData.z"))
      if self._DEBUG_PRINT:
        print("Waiting for drivers_list to arrive in GUI...")
      #print("Still no drivers list..")
      time.sleep(1)
    self._xTurns=[(str(round(tick,2)),round(tick,2)) for tick in np.linspace(0,1,11)]
    self._xTurns=tuple(self._xTurns)
    self._arg_maxima1="None"
    self._arg_maxima2="None"
    self._arg_minima1="None"
    self._arg_minima2="None"
    self._update_ann1=True
    self._update_ann2=True
    self._OffSet_1=0
    self._OffSet_2=0
    minx1=0
    maxx1=1
    minx2=0
    maxx2=1
    ymin_LT=60 #
    ymax_LT=61
    xmin_LT=0  #
    xmax_LT=1
    with dpg.group(label="Compare Telemetry View",tag="Telemetry_compare_view",show=False,parent="Primary window"):
      with dpg.group(label="map_buttons",tag="map_buttons",horizontal=True):
        dpg.add_combo(items=list(self._maps.keys()),tag="map",width=150,default_value=None,callback=self.Set_Corners)
        dpg.add_input_double(label="Offset_Turns",tag="slide_corner",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=self.Set_Corners)
      with dpg.group(label="offset_drivers",tag="offset_drivers",horizontal=True):
        dpg.add_input_double(label="Offset_Driver1",tag="OFF_DRV1",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=self.Set_Offset_Space)
        dpg.add_input_double(label="Offset_Driver2",tag="OFF_DRV2",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=self.Set_Offset_Space)            
      with dpg.group(label="speeds_text_1",tag="speeds_text_1",horizontal=True):  
        dpg.add_text(default_value="Driver 1:",tag="DRV-1-DRV_TEXT")
        dpg.add_text(default_value="Driver 1 speed",tag="DRV-1-SPEED_TEXT")
      with dpg.group(label="speeds_text_2",tag="speeds_text_2",horizontal=True):  
        dpg.add_text(default_value="Driver 2:",tag="DRV-2-DRV_TEXT")
        dpg.add_text(default_value="Driver 2 speed",tag="DRV-2-SPEED_TEXT")
      with dpg.group(label="driver1_buttons",tag="driver1_buttons",horizontal=True):
        dpg.add_combo(items=list(self._drivers_list),tag="DRV-1",width=150,default_value=None,callback=self.Select_Driver_Compare)
        dpg.add_combo(items=[],tag="LAP-1",width=150,default_value=None)
      with dpg.group(label="driver2_buttons",tag="driver2_buttons",horizontal=True):
        dpg.add_combo(items=list(self._drivers_list),tag="DRV-2",default_value=None,width=150,callback=self.Select_Driver_Compare)
        dpg.add_combo(items=[],tag="LAP-2",width=150,default_value=None)
      with dpg.group(label="compare_buttons",tag="compare_buttons",horizontal=True):
        dpg.add_combo(items=list(self._drivers_list),tag="DRV-1-LapTimes",width=150,default_value=None)
        dpg.add_combo(items=list(self._drivers_list),tag="DRV-2-LapTimes",width=150,default_value=None)
      with dpg.plot(label="CompareSpeed",tag="CompareSpeed",width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT*3./5.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_SPEED_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Speed [km/h]", tag="y_axis_SPEED_Compare")
        dpg.set_axis_limits("y_axis_SPEED_Compare", -2, 380)
        dpg.set_axis_limits("x_axis_SPEED_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_SPEED_Compare",self._xTurns)
        dpg.add_drag_line(label="speed_compare_line",tag="speed_compare_line", color=[255, 0, 0, 255], default_value=0.5, callback=self.print_speed_drivers)
        
      with dpg.plot(label="CompareThrottle",width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT/5.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_THROTTLE_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Throttle [%]", tag="y_axis_THROTTLE_Compare")
        dpg.set_axis_limits("y_axis_THROTTLE_Compare", -2, 101)
        dpg.set_axis_limits("x_axis_THROTTLE_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_THROTTLE_Compare",self._xTurns)

      with dpg.plot(label="CompareBrake",width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT/5.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_BRAKE_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Brake [on/off]", tag="y_axis_BRAKE_Compare")
        dpg.set_axis_limits("y_axis_BRAKE_Compare", -2, 101)
        dpg.set_axis_limits("x_axis_BRAKE_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_BRAKE_Compare",self._xTurns)

      with dpg.plot(label="CompareDeltaTime",width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_DELTA_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Delta [s]", tag="y_axis_DELTA_Compare")
        dpg.set_axis_limits("y_axis_DELTA_Compare", -3, 3)
        dpg.set_axis_limits("x_axis_DELTA_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_DELTA_Compare",self._xTurns)

      with dpg.plot(label="CompareLaps",width=self._TEL_PLOTS_WIDTH,height=self._TEL_PLOTS_HEIGHT,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="LapNumber",tag="x_axis_LAPS_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="LapTime [s]", tag="y_axis_LAPS_Compare")
        dpg.set_axis_limits("y_axis_LAPS_Compare", ymin_LT, ymax_LT)
        dpg.set_axis_limits("x_axis_LAPS_Compare", xmin_LT, xmax_LT)
      
      with dpg.plot(label="ZoomCompare",width=self._VIEWPORT_WIDTH-self._TEL_PLOTS_WIDTH,height=3/5*self._TEL_PLOTS_HEIGHT,pos=(self._TEL_PLOTS_WIDTH,0),no_title=True,anti_aliased=True):
        dpg.add_plot_axis(dpg.mvXAxis,tag="x_axis_ZOOM",no_tick_marks=True,no_tick_labels=True)
        dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis_ZOOM",no_tick_marks=True,no_tick_labels=True)
        
      
      for drv in self._drivers_list:
        dpg.add_line_series(x=[0],y=[0],label=drv+"s_c",parent="y_axis_SPEED_Compare",tag=drv+"s_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"t_c",parent="y_axis_THROTTLE_Compare",tag=drv+"t_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"b_c",parent="y_axis_BRAKE_Compare",tag=drv+"b_c")
        dpg.add_scatter_series(x=[0],y=[0],label=drv+"l_c",parent="y_axis_LAPS_Compare",tag=drv+"l_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"l_c_line",parent="y_axis_LAPS_Compare",tag=drv+"l_c_line")
        dpg.add_line_series(x=[0],y=[0],label=drv+"z_c",parent="y_axis_ZOOM",tag=drv+"z_c")
        dpg.bind_item_theme(drv+"s_c",drv+"_color")
        dpg.bind_item_theme(drv+"t_c",drv+"_color")
        dpg.bind_item_theme(drv+"z_c",drv+"_color")
        dpg.bind_item_theme(drv+"b_c",drv+"_color")
        dpg.bind_item_theme(drv+"l_c",drv+"plot_marker")
        dpg.bind_item_theme(drv+"l_c_line",drv+"_color")
        dpg.set_item_label(item=drv+"s_c",label=self._DRIVERS_INFO[drv]["abbreviation"])
        dpg.set_item_label(item=drv+"t_c",label=self._DRIVERS_INFO[drv]["abbreviation"])
        dpg.set_item_label(item=drv+"z_c",label=self._DRIVERS_INFO[drv]["abbreviation"])
        dpg.set_item_label(item=drv+"b_c",label=self._DRIVERS_INFO[drv]["abbreviation"])
        dpg.set_item_label(item=drv+"l_c",label=self._DRIVERS_INFO[drv]["abbreviation"])
      
      dpg.add_line_series(x=[0],y=[0],label="DeltaCompareLine",parent="y_axis_DELTA_Compare",tag="DeltaCompareLine")
      dpg.bind_item_theme("DeltaCompareLine","white")
      dpg.set_item_label(item="DeltaCompareLine",label="")
      
      while True:
        LAPS=self._database.get_dictionary(feed="TimingDataF1")
        if type(self._arg_maxima1)!=str and dpg.get_value("LAP-1").split(" ")[0]!="None":
          if (dpg.get_value("DRV-1")!=self._DRV1 or int(dpg.get_value("LAP-1").split(" ")[0])!=NLAP1):
            if self._DEBUG_PRINT:
              print("Here deleting annotations for driver 1 maxima...")
            for i in range(len(self._arg_maxima1)):
              dpg.delete_item(item=self._DRV1+"_max1_"+str(i))
            self._update_ann1=True
        if type(self._arg_minima1)!=str and dpg.get_value("LAP-1").split(" ")[0]!="None":
          if (dpg.get_value("DRV-1")!=self._DRV1 or int(dpg.get_value("LAP-1").split(" ")[0])!=NLAP1):
            if self._DEBUG_PRINT:
              print("Here deleting annotations for driver 1 minima...")
            for i in range(len(self._arg_minima1)):
              dpg.delete_item(item=self._DRV1+"_min1_"+str(i))
            self._update_ann1=True
        if dpg.get_value("LAP-1")!="None" and dpg.get_value("DRV-1")!="None":
          self._DRV1=dpg.get_value("DRV-1")
          #print(type(self._DRV1))
          #print(dpg.get_value("LAP-1"))
          NLAP1=int(dpg.get_value("LAP-1").split(" ")[0])
          self._LAP1=LAPS[self._DRV1][NLAP1] # DateTime , ValueString , ValueInt_sec are the keys
          LapTime1_s=self._LAP1["ValueInt_sec"]
          SLICE1=self._database.get_slice_between_times(start_time=self._LAP1["DateTime"]-datetime.timedelta(seconds=LapTime1_s),end_time=self._LAP1["DateTime"])
          ##SLICE1_pos=self._database.get_slice_between_times(feed="Position.z",start_time=self._LAP1["DateTime"]-datetime.timedelta(seconds=LapTime1_s),end_time=self._LAP1["DateTime"])
          TEL1=self._database.get_dictionary(feed="CarData.z")[self._DRV1]
          ##P1=self._database.get_dictionary(feed="Position.z")[self._DRV1]
          ##X1,Y1,Z1=[],[],[]
          ##for xyz in P1["XYZ"][SLICE1_pos]:
          ##  X1.append(xyz[0])
          ##  Y1.append(xyz[1])
          ##  Z1.append(xyz[2])
          Times1=[TS-TEL1["TimeStamp"][SLICE1][0] for TS in TEL1["TimeStamp"][SLICE1]]
          self._Speeds1=np.array(TEL1["Speed"][SLICE1])
          Throttles1=TEL1["Throttle"][SLICE1]
          Brakes1=TEL1["Brake"][SLICE1]
          self._Space1 = scipy.integrate.cumulative_trapezoid(self._Speeds1/3.6,Times1,initial=0)  
          ##self._Space1 =  np.sqrt(np.power(np.diff(np.array((np.array(X1),np.array(Y1),np.array(Z1))).T,axis=0),2).sum(axis=1)).cumsum()
          ##self._Total_space1 = self._Space1[-1]
          self._Total_space1 = self._Space1[-1]
          dpg.set_value(item=self._DRV1+"s_c", value=[self._Space1/self._Total_space1+self._OffSet_1,self._Speeds1])
          dpg.set_value(item=self._DRV1+"t_c", value=[self._Space1/self._Total_space1+self._OffSet_1,Throttles1])
          dpg.set_value(item=self._DRV1+"z_c", value=[self._Space1/self._Total_space1+self._OffSet_1,self._Speeds1])
          dpg.set_value(item=self._DRV1+"b_c", value=[self._Space1/self._Total_space1+self._OffSet_1,Brakes1])
          dpg.set_axis_ticks(axis="x_axis_SPEED_Compare",label_pairs=self._xTurns)
          dpg.set_axis_ticks(axis="x_axis_THROTTLE_Compare",label_pairs=self._xTurns)
          dpg.set_axis_ticks(axis="x_axis_BRAKE_Compare",label_pairs=self._xTurns)
          minx1=min(self._Space1/self._Total_space1+self._OffSet_1)
          maxx1=max(self._Space1/self._Total_space1+self._OffSet_1)
          self._arg_maxima1=scipy.signal.argrelextrema(self._Speeds1, np.greater_equal,order=10)[0]
          self._arg_minima1=scipy.signal.argrelextrema(self._Speeds1, np.less_equal,order=10)[0]
          if self._update_ann1:
            for arg,i in zip(self._arg_maxima1,range(len(self._arg_maxima1))):
              dpg.add_plot_annotation(label=str(int(self._Speeds1[arg])),tag=self._DRV1+"_max1_"+str(i), default_value=(self._Space1[arg]/self._Total_space1+self._OffSet_1,self._Speeds1[arg]), offset=(-0.05,-10), color=self._DRIVERS_INFO[self._DRV1]["color"],parent="CompareSpeed")
            for arg,i in zip(self._arg_minima1,range(len(self._arg_minima1))):
              dpg.add_plot_annotation(label=str(int(self._Speeds1[arg])),tag=self._DRV1+"_min1_"+str(i), default_value=(self._Space1[arg]/self._Total_space1+self._OffSet_1,self._Speeds1[arg]), offset=(-0.05,+10), color=self._DRIVERS_INFO[self._DRV1]["color"],parent="CompareSpeed")
            self._update_ann1=False
          #print(self._DRV1,Space1)
        
        
        if type(self._arg_maxima2)!=str and dpg.get_value("LAP-2").split(" ")[0]!="None": 
          if (dpg.get_value("DRV-2")!=self._DRV2 or int(dpg.get_value("LAP-2").split(" ")[0])!=NLAP2):
            if self._DEBUG_PRINT:
              print("Here deleting annotations for driver 2 maxima...")
            for i in range(len(self._arg_maxima2)):
              dpg.delete_item(item=self._DRV2+"_max2_"+str(i))
            self._update_ann2=True
        if type(self._arg_minima2)!=str and dpg.get_value("LAP-2").split(" ")[0]!="None":
          if (dpg.get_value("DRV-2")!=self._DRV2 or int(dpg.get_value("LAP-2").split(" ")[0])!=NLAP2):
            if self._DEBUG_PRINT:
              print("Here deleting annotations for driver 2 minima...")
            for i in range(len(self._arg_minima2)):
              dpg.delete_item(item=self._DRV2+"_min2_"+str(i))
            self._update_ann2=True 
        if dpg.get_value("LAP-2")!="None" and dpg.get_value("DRV-2")!="None":
          self._DRV2=dpg.get_value("DRV-2")
          NLAP2=int(dpg.get_value("LAP-2").split(" ")[0])
          self._LAP2=LAPS[self._DRV2][NLAP2] # DateTime , ValueString , ValueInt_sec are the keys
          LapTime2_s=self._LAP2["ValueInt_sec"]
          SLICE2=self._database.get_slice_between_times(start_time=self._LAP2["DateTime"]-datetime.timedelta(seconds=LapTime2_s),end_time=self._LAP2["DateTime"])
          TEL2=self._database.get_dictionary(feed="CarData.z")[self._DRV2]     
          Times2=[TS-TEL2["TimeStamp"][SLICE2][0] for TS in TEL2["TimeStamp"][SLICE2]]
          self._Speeds2=np.array(TEL2["Speed"][SLICE2])
          #Speeds2_smooth=scipy.signal.savgol_filter(Speeds2, 8, 2) 
          Throttles2=TEL2["Throttle"][SLICE2]
          Brakes2=TEL2["Brake"][SLICE2]
          self._Space2 = scipy.integrate.cumulative_trapezoid(self._Speeds2/3.6,Times2,initial=0)  
          self._Total_space2 = self._Space2[-1]
          ##SLICE2_pos=self._database.get_slice_between_times(feed="Position.z",start_time=self._LAP2["DateTime"]-datetime.timedelta(seconds=LapTime2_s),end_time=self._LAP2["DateTime"])
          ##P2=self._database.get_dictionary(feed="Position.z")[self._DRV2]
          ##X2,Y2,Z2=[],[],[]
          ##for xyz in P2["XYZ"][SLICE2_pos]:
          ##  X2.append(xyz[0])
          ##  Y2.append(xyz[1])
          ##  Z2.append(xyz[2])
          ##self._Space2 =  np.sqrt(np.power(np.diff(np.array((np.array(X2),np.array(Y2),np.array(Z2))).T,axis=0),2).sum(axis=1)).cumsum()
          ##self._Total_space2 = self._Space2[-1]      
          dpg.set_value(item=self._DRV2+"s_c", value=[self._Space2/self._Total_space2+self._OffSet_2,self._Speeds2])
          dpg.set_value(item=self._DRV2+"z_c", value=[self._Space2/self._Total_space2+self._OffSet_2,self._Speeds2])
          dpg.set_value(item=self._DRV2+"t_c", value=[self._Space2/self._Total_space2+self._OffSet_2,Throttles2])
          dpg.set_value(item=self._DRV2+"b_c", value=[self._Space2/self._Total_space2+self._OffSet_2,Brakes2])
          #print(self._xTurns)
          dpg.set_axis_ticks(axis="x_axis_SPEED_Compare",label_pairs=self._xTurns)
          dpg.set_axis_ticks(axis="x_axis_THROTTLE_Compare",label_pairs=self._xTurns)
          dpg.set_axis_ticks(axis="x_axis_BRAKE_Compare",label_pairs=self._xTurns)
          minx2=min(self._Space2/self._Total_space2+self._OffSet_2)
          maxx2=max(self._Space2/self._Total_space2+self._OffSet_2)
          self._arg_maxima2=scipy.signal.argrelextrema(self._Speeds2, np.greater_equal,order=10)[0]
          self._arg_minima2=scipy.signal.argrelextrema(self._Speeds2, np.less_equal,order=10)[0]
          if self._update_ann2:
            for arg,i in zip(self._arg_maxima2,range(len(self._arg_maxima2))):
              dpg.add_plot_annotation(label=str(int(self._Speeds2[arg])),tag=self._DRV2+"_max2_"+str(i), default_value=(self._Space2[arg]/self._Total_space2+self._OffSet_2,self._Speeds2[arg]), offset=(+0.05,-10), color=self._DRIVERS_INFO[self._DRV2]["color"],parent="CompareSpeed")
            for arg,i in zip(self._arg_minima2,range(len(self._arg_minima2))):
              dpg.add_plot_annotation(label=str(int(self._Speeds2[arg])),tag=self._DRV2+"_min2_"+str(i), default_value=(self._Space2[arg]/self._Total_space2+self._OffSet_2,self._Speeds2[arg]), offset=(+0.05,+10), color=self._DRIVERS_INFO[self._DRV2]["color"],parent="CompareSpeed")
            self._update_ann2=False
          #print(self._DRV2,Space2)
        
        if dpg.get_value("DRV-1-LapTimes")!="None":
          lap_to_pop=[]
          self._DRV1_LTs=dpg.get_value("DRV-1-LapTimes")
          LAPNUMBERS1=list(LAPS[self._DRV1_LTs].keys())
          LAPTIMES1=[lap["ValueInt_sec"] if lap["ValueInt_sec"]<200 else lap_to_pop.append(nlap) for nlap,lap in LAPS[self._DRV1_LTs].items()]
          for nlap in lap_to_pop:
            LAPNUMBERS1.remove(nlap)
            LAPTIMES1.remove(None)
          #print(self._DRV1_LTs," ",LAPNUMBERS1, LAPTIMES1)
          #print(self._DRV1_LTs+"l_c",LAPNUMBERS1,LAPTIMES1)
          dpg.set_value(item=self._DRV1_LTs+"l_c", value=[LAPNUMBERS1,LAPTIMES1])
          dpg.set_value(item=self._DRV1_LTs+"l_c_line", value=[LAPNUMBERS1,LAPTIMES1])
          if int(max(LAPTIMES1))+5>ymax_LT:
            ymax_LT=int(max(LAPTIMES1))+5
          if int(max(LAPNUMBERS1))+1>xmax_LT:
            xmax_LT=int(max(LAPNUMBERS1))+1
          
        if dpg.get_value("DRV-2-LapTimes")!="None":
          lap_to_pop=[]
          self._DRV2_LTs=dpg.get_value("DRV-2-LapTimes")
          LAPNUMBERS2=list(LAPS[self._DRV2_LTs].keys())
          LAPTIMES2=[lap["ValueInt_sec"] if lap["ValueInt_sec"]<200 else lap_to_pop.append(nlap) for nlap,lap in LAPS[self._DRV2_LTs].items()]
          for nlap in lap_to_pop:
            LAPNUMBERS2.remove(nlap)
            LAPTIMES2.remove(None)
          #print(self._DRV2_LTs," ",LAPNUMBERS2, LAPTIMES2)
          dpg.set_value(item=self._DRV2_LTs+"l_c", value=[LAPNUMBERS2,LAPTIMES2])
          dpg.set_value(item=self._DRV2_LTs+"l_c_line", value=[LAPNUMBERS2,LAPTIMES2])
          if int(max(LAPTIMES2))+5>ymax_LT:
            ymax_LT=int(max(LAPTIMES2))+5
          if int(max(LAPNUMBERS2))+1>xmax_LT:
            xmax_LT=int(max(LAPNUMBERS2))+1
       
        if dpg.get_value("LAP-1")!="None" and dpg.get_value("DRV-1")!="None" and dpg.get_value("LAP-2")!="None" and dpg.get_value("DRV-2")!="None":
          sp1=self._Space1/self._Total_space1
          sp2=self._Space2/self._Total_space2
          Space_x=np.linspace(0,1,500)
          t1=scipy.interpolate.Akima1DInterpolator(sp1,Times1)(Space_x)
          t2=scipy.interpolate.Akima1DInterpolator(sp2,Times2)(Space_x)
          #t1_chi=scipy.interpolate.PchipInterpolator(sp1,Times1)(Space_x)
          #t2_chi=scipy.interpolate.PchipInterpolator(sp2,Times2)(Space_x)
          #t1_cub=scipy.interpolate.CubicSpline(sp1,Times1)(Space_x)
          #t2_cub=scipy.interpolate.CubicSpline(sp2,Times2)(Space_x)
          #t1_lin=np.interp(Space_x, sp1, Times1)
          #t2_lin=np.interp(Space_x, sp2, Times2)
          
          # Merge y1 and y2 based on merged indices using numpy
          Delta     =    t1  -   t2
          #Delta_chi = t1_chi - t2_chi
          #Delta_lin = t1_lin - t2_lin 
          #Delta_cub = t1_cub - t2_cub
          #print("Akima: ",Delta[-1],"  Chi: ",Delta_chi[-1],"  Lin: ",Delta_lin[-1],"  Cub: ",Delta_cub[-1])
          
          dpg.set_value(item="DeltaCompareLine", value=[Space_x,Delta])
          dpg.set_axis_ticks(axis="x_axis_DELTA_Compare",label_pairs=self._xTurns)
          dpg.set_axis_limits("y_axis_DELTA_Compare", min(Delta)-0.2,max(Delta)+0.2)
          
        dpg.set_axis_limits("x_axis_SPEED_Compare",min([0,minx1,minx2]),max([1,maxx1,maxx2]))
        dpg.set_axis_limits("x_axis_THROTTLE_Compare",min([0,minx1,minx2]),max([1,maxx1,maxx2]))
        dpg.set_axis_limits("x_axis_BRAKE_Compare",min([0,minx1,minx2]),max([1,maxx1,maxx2]))
        dpg.set_axis_limits("x_axis_LAPS_Compare",xmin_LT,xmax_LT)
        dpg.set_axis_limits("y_axis_LAPS_Compare",ymin_LT,ymax_LT)
        if dpg.is_item_hovered(item="CompareSpeed"):
          mouse_pos=dpg.get_plot_mouse_pos()
          dpg.set_axis_limits("x_axis_ZOOM",ymin=mouse_pos[0]-0.1,ymax=mouse_pos[0]+0.1)
          dpg.set_axis_limits("y_axis_ZOOM",ymin=mouse_pos[1]-50,ymax=mouse_pos[1]+50)
        
        for driver in self._drivers_list:
          if driver==dpg.get_value("DRV-1") or driver==dpg.get_value("DRV-2"):
            dpg.show_item(driver+"s_c")
            dpg.show_item(driver+"z_c")
            dpg.show_item(driver+"t_c")
            dpg.show_item(driver+"b_c")
          else:
            dpg.hide_item(driver+"s_c")
            dpg.hide_item(driver+"z_c")
            dpg.hide_item(driver+"t_c")
            dpg.hide_item(driver+"b_c")
          if driver==dpg.get_value("DRV-1-LapTimes") or driver==dpg.get_value("DRV-2-LapTimes"):
            dpg.show_item(driver+"l_c")
            dpg.show_item(driver+"l_c_line")
          else:
            dpg.hide_item(driver+"l_c")
            dpg.hide_item(driver+"l_c_line")
        time.sleep(self._TIME_UPDATE_TELEMETRY_PLOT)
      # Add slider to fix times offset
      # Add while loop
      # Slice telemetry and remove starting time to TimeStamp at each point

  
###################################################################################################################  
  
  def update_position_plot(self):
    while not self._start_position:
      time.sleep(0.5)
    while True:
      while self._task_state=="pause":
        time.sleep(self._sleeptime)
      self._last_message_displayed_DT_position = self._first_message_DT + datetime.timedelta(seconds=self._time_skipped) + (datetime.datetime.now() - datetime.timedelta(seconds=self._time_paused) - self._first_message_DT_myTime)
      if dpg.get_value("Race_Map")!="None" and dpg.does_item_exist("drawlist_map_position"):
        pos_dict=self._database.get_dictionary(feed="Position.z")
        last_index_msg =self._database.get_position_index_before_time(sel_time=self._last_message_displayed_DT_position)
        for driver,full_position in pos_dict.items():
          xyz=full_position["XYZ"][last_index_msg]
          xyz_dpg=self.transform_position_from_F1_to_dpg(xyz[0]/10.,xyz[1]/10.)
          if not dpg.does_item_exist("node"+driver):
            with dpg.draw_node(tag="node"+driver,parent="drawlist_map_position"):
              dpg.draw_circle(color=self._DRIVERS_INFO[driver]["color"],center=(xyz_dpg[0],xyz_dpg[1]),radius=12,fill=self._DRIVERS_INFO[driver]["color"],tag="circle"+driver)
              dpg.draw_text(tag="text"+driver,pos=(xyz_dpg[0]-12/2,xyz_dpg[1]-12/2.),text=self._DRIVERS_INFO[driver]["abbreviation"],color=[255,255,255])
              dpg.bind_item_font(item="text"+driver,font="drawNodeFont")
          else:
            prev_pos=dpg.get_item_configuration("circle"+driver)['center']
            dpg.apply_transform(item="node"+driver, transform=dpg.create_translation_matrix([xyz_dpg[0]-prev_pos[0], 
                                                                                             xyz_dpg[1]-prev_pos[1]]))
            
      time.sleep(self._TIME_UPDATE_POSITION_PLOT)
    
  
  def showTab(self,sender):
    print(sender," show set to True")
    dpg.configure_item(self._tabs[sender],show=True)
    for tab in self._tabs.keys():
      if tab!=sender:
        print(self._tabs[tab]," show set to False")
        dpg.configure_item(self._tabs[tab],show=False)


  def run(self):
    """
      Rewrite this. Needs to create in order: Window to choose race if necessary, 
      telemetry display of all drivers and comparison plot. Last 2 need to be built 
      in 2 tabs in the same window. 
    """
    
    if not self._LIVE_SIM:
      self._IO_thread.start()
    # No bring focus is a temporary workaround. It will be fixed in the future with the windows restyle                                                                                                  
    with dpg.window(tag="Primary window",width=self._VIEWPORT_WIDTH,height=self._VIEWPORT_HEIGHT,pos=[0,0],no_bring_to_front_on_focus=True):
      with dpg.menu_bar():
        with dpg.tab_bar():
          for tab in self._tabs.keys():
            dpg.add_tab_button(label=tab,tag=tab,callback=self.showTab)
          #dpg.add_tab_button(label="Telemetry")
          #dpg.add_tab_button(label="Compare Telemetry")
      if self._LIVE_SIM:
        with dpg.group(label="Race selector",tag="Race_Selector",show=True):
          dpg.add_combo(items=list(self._parser._sessions_dict.keys()),tag="year",default_value="None",callback=self.choose_session)
    
    # Colors for laps based on laptime
    with dpg.theme(tag="BestOverallLap"): 
        with dpg.theme_component():
          dpg.add_theme_color(dpg.mvPlotCol_Line, [255,0,255] , category=dpg.mvThemeCat_Plots)
    with dpg.theme(tag="BestPersonalLap"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvPlotCol_Line, [0,255,0] , category=dpg.mvThemeCat_Plots)
    with dpg.theme(tag="NormalLap"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvPlotCol_Line, [204,204,0] , category=dpg.mvThemeCat_Plots)
    
    # Colors for drivers in plots
    for driver,info in self._DRIVERS_INFO.items():
      with dpg.theme(tag=driver+"_color"):
        with dpg.theme_component():
          dpg.add_theme_color(dpg.mvPlotCol_Line, info["color"] , category=dpg.mvThemeCat_Plots)
      
      with dpg.theme(tag=driver+"plot_marker"):
        with dpg.theme_component(dpg.mvScatterSeries):
          dpg.add_theme_color(dpg.mvPlotCol_Line, info["color"], category=dpg.mvThemeCat_Plots)
          dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, info["color"] , category=dpg.mvThemeCat_Plots)
          dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Cross,category=dpg.mvThemeCat_Plots)
          dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 7, category=dpg.mvThemeCat_Plots)
    with dpg.theme(tag="white"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvPlotCol_Line, [255,255,255,255] , category=dpg.mvThemeCat_Plots)
    
    with dpg.font_registry():
      # first argument ids the path to the .ttf or .otf file
      dpg.add_font("Fonts/Roboto-Bold.ttf", 40,tag="drawNodeFont")
    
    dpg.set_primary_window(window="Primary window",value=True)
    dpg.configure_item("Primary window", horizontal_scrollbar=True) # work-around for a known dpg bug!
    
    self._update_telemetry_thread.start()    
    self._compare_telemetry_thread.start()
    self._update_position_thread.start()
    
    with dpg.theme() as global_theme:
      with dpg.theme_component(dpg.mvAll):
        # Core Style
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0,0, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 3,1, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 2,2, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 4,3, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 1, category=dpg.mvThemeCat_Core)

        # Plot Style
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding, 0,0, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_LabelPadding, 0,0, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 1.2, category=dpg.mvThemeCat_Plots)
    
    dpg.bind_theme(global_theme)
    
    #dpg.show_style_editor()
    dpg.start_dearpygui()  
    dpg.destroy_context()
  