import dearpygui.dearpygui as dpg
import time
import threading
import datetime
import numpy as np
import SignalR_LS as SR_LS
import scipy
import json
import collections
import re
import os


from config import _config


class GUI:
  def __init__(self, FORCE_UPDATE: bool=False):
    
    # to be taken from buttons 
    self._YEAR           = "none"          
    self._detected_year  = None  
    self._RACE           = "none"           
    self._SESSION        = "none"
    
    # Keep it quiet we are not ready to show off.
    self._LIVESIM_READY  = False
    
    # From config
    self._FORCE_UPDATE           =  FORCE_UPDATE  
    self._filename_feeds         = _config.FILENAME_FEEDS
    self._filename_urls          = _config.FILENAME_URLS
    self._filename_urls          = _config.FILENAME_URLS
    self._filename_urls          = _config.FILENAME_URLS 
    self._LIVE_SIM               = _config.LIVE_SIM
    self._LIVE                   =  not self._LIVE_SIM
    self._DEBUG_PRINT            = _config.DEBUG_PRINT
    
    self._parser    = _config.DATABASE._parser 
    self._database  = _config.DATABASE            # need to update filename txt..
    self._client    = SR_LS.SignalRClient(filename="data/PROVA.txt",timeout=_config.TIMEOUT_SR_LS)
    
    # hardcoding for life. These need to be updated...
    self._map_width   = 460
    self._map_height  = 400
    
    # Not used for now. But this gui doesn't track all the window 
    # i created (maybe it does but i still didn't found it). Therefore 
    # here i list all windows tag (as str) 
    self._windows_manager=[] 
    
    # Initialize the GUI. Length of windows and other parameters that can be found in config
    self._MAX_WIDTH,self._MAX_HEIGHT            = int(_config.MAX_WIDTH),int(_config.MAX_HEIGHT)
    
    self._BUTTONS_HEIGHT                        = _config.BUTTONS_HEIGHT
    self._BUTTONS_WIDTH                         = _config.BUTTONS_WIDTH
    self._BUTTONS_ROWS                          = _config.BUTTONS_ROWS
    
    self._BOTTOM_BAR_HEIGHT                     = _config.BOTTOM_BAR_HEIGHT
    self._TOP_BAR_HEIGHT                        = _config.TOP_BAR_HEIGHT
    
    self._TEL_OTHER_RATIO                       = _config.TEL_OTHER_RATIO
    self._FREQUENCY_TELEMETRY_UPDATE            = _config.FREQUENCY_TELEMETRY_UPDATE
    self._LAPS_TO_DISPLAY                       = _config.LAPS_TO_DISPLAY
    self._AVG_LAP_LENGTH                        = _config.AVG_LAP_LENGTH
    self._WINDOW_DISPLAY_LENGTH                 = _config.WINDOW_DISPLAY_LENGTH
    self._WINDOW_DISPLAY_PROPORTION_RIGHT       = _config.WINDOW_DISPLAY_PROPORTION_RIGHT
    self._WINDOW_DISPLAY_PROPORTION_LEFT        = 1. - _config.WINDOW_DISPLAY_PROPORTION_RIGHT
    
    self._DRIVERS_INFO                          = _config.COLOR_DRIVERS
    self._watchlist_drivers                     = _config.WATCHLIST_DRIVERS
    self._watchlist_teams                       = _config.WATCHLIST_TEAMS
    self._maps                                  = _config.MAPS
    self._segments                              = _config.SEGMENTS
    self._sessions_duration                     = _config.SESSION_DURATION
    
    # Initializing the listener (signalr). Only if we are not simulating a session
    if not self._LIVE_SIM:
      self._IO_thread = threading.Thread(target=self._client.start)
    
    # Let's start
    dpg.create_context()
    if _config.TERMINAL_MODE:
      self._TERMINAL_SPACE=_config.TERMINAL_SPACE
      dpg.create_viewport(title='Custom Title', width=self._MAX_WIDTH,height=self._TERMINAL_SPACE,decorated=True)
    else:
      self._TERMINAL_SPACE=0
      dpg.create_viewport(title='Custom Title', width=self._MAX_WIDTH,height=self._MAX_HEIGHT - self._BOTTOM_BAR_HEIGHT - self._TOP_BAR_HEIGHT - self._TERMINAL_SPACE,decorated=True)
    
    # debug
    self._PRINT_TIMES = _config.PRINT_TIMES # flag that it is not used anymore.
    
    # TODO
    # Need to be updated
    print("Viewport:" ,dpg.get_viewport_width()," " ,dpg.get_viewport_height())
    self._VIEWPORT_WIDTH  = max(dpg.get_viewport_width(),1920)
    self._VIEWPORT_HEIGHT = max(dpg.get_viewport_height(),1080)
    
    # Still initial configurations
    dpg.show_viewport()
    dpg.setup_dearpygui()
    self._TEL_PLOTS_HEIGHT = _config.TELEMETRY_PLOTS_HEIGHT
    self._TEL_PLOTS_WIDTH  = _config.TELEMETRY_PLOTS_WIDTH
    
    # Useful variables (Datetimes and constant variables)
    self._last_message_DT                     = None
    self._last_message_displayed_UTC          = None
    self._last_message_displayed_UTC_position = None
    self._first_message_DT                    = None
    self._starting_session_DT                 = None
    
    self._time_skipped                        = 0
    self._time_paused                         = 0
    self._BaseTimestamp                       = None
    self._seconds_to_skip                     = 5
    self._delay_T                             = _config.DELAY
    self._TIME_UPDATE_TELEMETRY_PLOT          = 1./_config.FREQ_UPDATE_PLOT
    self._TIME_UPDATE_POSITION_PLOT           = 1./_config.FREQ_UPDATE_PLOT
    self._sleeptime                           = _config.SLEEPTIME
     
    self._last_session_status                 = "Inactive"
    self._task_state                          = "running"
    self._session_name                        = ""
    self._event_name                          = ""
    self._meeting_key                         = ""
    
    # Kill button. Needs to be reworked.
    self._StopUpdateThread = threading.Event()
    
    # Flags 
    self._DriverInTimingView                  = []
    self._start_compare                       = False
    self._start_timing                        = False
    self._start_position                      = False
    self._drivers_prev_position               = {}
    
    # Analysis thread and time_flow_handler threads
    self._compare_telemetry_thread = threading.Thread(target=self.Compare_Telemetry_2)
    self.iterator = threading.Thread(target=self.time_flow_handler)
    
    # Tabs for GUI 
    if self._LIVE_SIM:
      self._tabs={"choose_race":       "Race_Selector",
                  "update_telemetry":  "Telemetry_view",
                  "compare_telemetry": "Telemetry_compare_view",
                  "timing":            "Timing_view"}
    else:
      self._tabs={"update_telemetry":  "Telemetry_view",
                  "compare_telemetry": "Telemetry_compare_view",
                  "timing":            "Timing_view"}
    
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
    print("Plot initialized!")
    self._LIVESIM_READY=True
    #for driver in self._drivers_list:
    #  if driver not in self._LS._analyzer._laptimes_2.keys():
    #    self._LS._analyzer._laptimes_2[driver]={}


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
      dpg.add_button(label="tel",tag="tel",callback=self.save_telemetry)
      #dpg.add_combo(tag="Race_Map",default_value="None",items=list(self._maps.keys()),width=self._BUTTONS_WIDTH,callback=self.change_map_background)
      #dpg.add_input_float(label="Map_Scale_X",tag="mapScaleX",width=50,min_value=10,max_value=100,default_value=50,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="Map_Scale_Y",tag="mapScaleY",width=50,min_value=10,max_value=100,default_value=50,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="X-Off",tag="XOFF",width=50,min_value=-640,max_value=640,default_value=320,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="Y-Off",tag="YOFF",width=50,min_value=-480,max_value=480,default_value=240,min_clamped=True,max_clamped=True,step=0,step_fast=0)
      #dpg.add_input_float(label="angle",tag="angle",width=50,min_value=0,max_value=360,default_value=0,min_clamped=True,max_clamped=True,step=0,step_fast=0,on_enter=True,callback=self.rotate_map)
    n_rows=len(self._drivers_list) // 8 + (len(self._drivers_list) % 8 > 0)
    #for n_row in range(1,n_rows+1):
    #  with dpg.group(label="buttons"+str(2+n_row),tag="buttons"+str(2+n_row),horizontal=True,height=self._BUTTONS_HEIGHT,pos=(10,self._BUTTONS_HEIGHT*(1+n_row))):
    #    self.show_telemetry_button(row_number=n_row)
    #    self._BUTTONS_ROWS=2+n_row

  def pause_button(self):
    if self._task_state == "running":
      self._task_state = "pause"
      dpg.set_item_label(item="PLAY_BUTTON",label="Play")
      print("Pausing..")
    else:
      self._task_state="running"
      dpg.set_item_label(item="PLAY_BUTTON",label="Pause")
      print("Resuming..")

  def save_telemetry(self):
    """ 
      Saves Tyres, Laps and Telemetry retrieved from the database as jsons.
      Filenames: year+"_"+race+"_"+session+"_"(tyres,laps,telemetry)+".json"
    """
    #print(self._driver_infos)
    tyres=self._database.get_dictionary("TimingAppData")
    laps=self._database.get_dictionary("TimingDataF1")
    telemetry=self._database.get_dictionary("CarData.z")
    
    year,race,session=self._database.get_year(),self._database.get_session_type(),self._database.get_event_name()
    
    save_file = open(year+"_"+race+"_"+session+"_tyres.json", "w")  
    json.dump(tyres, save_file, indent = 2,default=str)  
    save_file.close()
    
    save_file = open(year+"_"+race+"_"+session+"_laps.json", "w")  
    json.dump(laps, save_file, indent = 2,default=str)  
    save_file.close()
    
    save_file = open(year+"_"+race+"_"+session+"_telemetry.json", "w")  
    json.dump(telemetry, save_file, indent = 2,default=str)  
    save_file.close()

  def set_skip_time(self):
    """ 
      CallBack. It updates skip time.
    """
    self._seconds_to_skip=dpg.get_value("skip_seconds")
    dpg.configure_item(item="backward",label="-"+str(self._seconds_to_skip)+"s")
    dpg.configure_item(item="forward",label="+"+str(self._seconds_to_skip)+"s")
    # dpg.set_item_label(item="backward",label="-"+self._seconds_to_skip+"s")
    # dpg.set_item_label(item="forward",label="+"+self._seconds_to_skip+"s")
      
  def set_delay_time(self):
    """ 
      CallBack. Never tried lol. It updates delay time.
    """
    if dpg.get_value("delay")<self._delay_T:
      self._time_skipped+=(self._delay_T-dpg.get_value("delay"))
    else:
      self._time_paused+=(dpg.get_value("delay")-self._delay_T)
    self._delay_T=dpg.get_value("delay")    
    
    
  def forward_button(self):
    """
      Forward skip_time seconds. It cycles through every msgs from current_time to current_time+skip_time
    """
    dpg.set_item_callback(item="forward",callback=None)
    dpg.set_item_callback(item="backward",callback=None)
    
    if self._last_message_displayed_UTC.timestamp()+self._seconds_to_skip<=self._last_message_DT.timestamp():
      self._task_state = "pause"
      time.sleep(0.5) #let the time_flow handler enter in the pause state

      time_start_timestamp = self._last_message_displayed_UTC.timestamp()
      time_end_timestamp   = (self._last_message_displayed_UTC+datetime.timedelta(seconds=self._seconds_to_skip)).timestamp()  # !! #
      self._time_skipped+=self._seconds_to_skip
      self._last_message_displayed_UTC+=datetime.timedelta(seconds=self._seconds_to_skip) 
      #self._car_data_chrono_flag=False

      #self._minx_tel=max(self._first_message_UTC.timestamp()-self._BaseTimestamp,time_end_timestamp-self._BaseTimestamp-self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_LEFT)
      ##maxx_tel=max(self._first_message_UTC.timestamp()-self._BaseTimestamp+self._WINDOW_DISPLAY_LENGTH,self._last_message_displayed_UTC.timestamp()-self._BaseTimestamp+self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_RIGHT)
      #if (time_start_timestamp-self._BaseTimestamp)>self._minx_tel:
      #  if self._DEBUG_PRINT:
      #    print("Chrono flag set to True. Appending telemetry to the existent one")
      #  self._car_data_chrono_flag=True

      #self.Initialize_Updaters_FWBW(self._car_data_chrono_flag)

      list_of_msgs=self._database.get_list_of_msgs().copy()
      #list_of_msgs_reversed=[]
      
      list_of_ann_to_delete=[]
      for driver in self._drivers_list:
        for subitem,listofchildrens in dpg.get_item_children(item="speed"+driver).items():
          for ch in listofchildrens:
            item_name=dpg.get_item_alias(ch)
            if "axis" not in item_name and item_name!=(driver+"s"):
              list_of_ann_to_delete.append(ch)
        
      for item in list_of_ann_to_delete:
        dpg.delete_item(item=item)
      
      for index,content in zip(range(self._last_index,len(list_of_msgs)),list_of_msgs[self._last_index:]): # last_index based on FW,BW also
        feed,msg,T = content[0],content[1],content[2]
        if T.timestamp()<time_end_timestamp:
          self._last_index_checked=index
          if feed=="RaceControlMessages":
            self.update_variables_RaceControlMessages(feed,msg) # need to be in chrono order
          elif feed=="TimingAppData":
            self.update_variables_TimingAppData(feed,msg)
          elif feed=="TimingDataF1":
            self.update_variables_TimingDataF1(T,feed,msg)
          elif feed=="CarData.z":
            self.update_telemetry_FWBW(T,msg,True)
          elif feed=="WeatherData":
            self.update_variables_WeatherData(msg)
        else:
          break
        
      dpg.set_value(item="race_msgs",value=self._msgs_string)
      self._last_index=self._last_index_checked
      
      dpg.set_item_callback(item="forward",callback=self.forward_button)
      dpg.set_item_callback(item="backward",callback=self.backward_button)
      
      self._task_state = "running"


    
  def backward_button(self):
    """
      Backward skip_time seconds. It cycles through every msgs from the beginning to current_time-skip_time
    """
    dpg.set_item_callback(item="forward",callback=None)
    dpg.set_item_callback(item="backward",callback=None)
    
    if self._last_message_displayed_UTC.timestamp()-self._seconds_to_skip>=self._first_message_UTC.timestamp():
      self._task_state = "pause"
      time.sleep(0.5) #let the time_flow handler enter in the pause state

      time_start_timestamp     = self._first_message_UTC.timestamp()
      time_end_timestamp       = (self._last_message_displayed_UTC-datetime.timedelta(seconds=self._seconds_to_skip)).timestamp()  # !! #
      time_start_tel_timestamp = (self._last_message_displayed_UTC-datetime.timedelta(seconds=self._seconds_to_skip)).timestamp()-self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_LEFT
      self._time_skipped-=self._seconds_to_skip
      self._last_message_displayed_UTC-=datetime.timedelta(seconds=self._seconds_to_skip) 
      
      #self.Initialize_Updaters_FWBW(self._car_data_chrono_flag)

      list_of_msgs=self._database.get_list_of_msgs().copy()
      #list_of_msgs_reversed=[]

      self._msgs_string=""
      
      list_of_ann_to_delete=[]
      for driver in self._drivers_list:
        for subitem,listofchildrens in dpg.get_item_children(item="speed"+driver).items():
          for ch in listofchildrens:
            item_name=dpg.get_item_alias(ch)
            if "axis" not in item_name and item_name!=(driver+"s"):
              list_of_ann_to_delete.append(ch)
        
      for item in list_of_ann_to_delete:
        dpg.delete_item(item=item)
      
      self.Initialize_Updaters()
      for index,content in zip(range(0,len(list_of_msgs)),list_of_msgs): # last_index based on FW,BW also
        feed,msg,T = content[0],content[1],content[2]
        if T.timestamp()<time_end_timestamp:
          self._last_index_checked=index
          if feed=="RaceControlMessages":
            self.update_variables_RaceControlMessages(feed,msg) # need to be in chrono order
          elif feed=="TimingAppData":
            self.update_variables_TimingAppData(feed,msg)
          elif feed=="TimingDataF1":
            self.update_variables_TimingDataF1(T,feed,msg)
          elif feed=="CarData.z" and T.timestamp()>time_start_tel_timestamp:
            self.update_telemetry_FWBW(T,msg,True)
          elif feed=="WeatherData":
            self.update_variables_WeatherData(msg)
        else:
          break
        
      dpg.set_value(item="race_msgs",value=self._msgs_string)
      self._last_index=self._last_index_checked
      
      dpg.set_item_callback(item="forward",callback=self.forward_button)
      dpg.set_item_callback(item="backward",callback=self.backward_button)
      
      self._task_state = "running"
    
  def show_telemetry_button(self,row_number):
    """ 
      Not used anymore.
    """
    selected_teams=self._watchlist_teams[4*(row_number-1):4*row_number]
    for team in selected_teams:
      for driver in self._drivers_list:
        if team==self._DRIVERS_INFO[driver]["team"]:
          if driver in self._watchlist_drivers:
            dpg.add_checkbox(label=self._DRIVERS_INFO[driver]["abbreviation"],tag=driver+"STB",default_value=True)
          else:
            dpg.add_checkbox(label=self._DRIVERS_INFO[driver]["abbreviation"],tag=driver+"STB",default_value=False)
      #dpg.add_bool_value(default_value=True,source=driver+"ST")

  def kill_button(self):
    self._StopUpdateThread.set()
    dpg.destroy_context()

  
  def hide_show_tel(self,driver):
    """ 
      Not used anymore
    """
    if dpg.get_value(driver+"STB"):
      dpg.show_item(driver+"s")
      dpg.show_item(driver+"t")
      dpg.show_item(driver+"b")
    else:    
      dpg.hide_item(driver+"s")
      dpg.hide_item(driver+"t")
      dpg.hide_item(driver+"b")

  

#########################################################################################################

  def change_map_background(self):
    """ 
      Sets the track map.
    """
    if dpg.does_item_exist(item="map_background"):
      dpg.delete_item(item="map_background") 
      dpg.delete_item(item="map_background_texture")
    
    map_dict=str(_config.paths.MAPS_PATH / self._maps[self._event_name]["map"])
    width, height, channels, data = dpg.load_image(map_dict)
    #print(width,height)
    
    #self._map_width,self._map_height=width,height
    with dpg.texture_registry():
      dpg.add_static_texture(width=width, height=height, default_value=data, tag="map_background_texture")

    
    dpg.draw_image(texture_tag="map_background_texture",tag="map_background",parent="drawlist_map_position",pmin=(0,0),pmax=(self._map_width,self._map_height),show=True)

  def transform_position_from_F1_to_dpg(self,x,y):
    """ 
      From x,y in F1 coordinates (Position.z) to x,y in DPG coordinates (Pixels).
    """
    xlims=self._maps[self._event_name]["xlim"]
    ylims=self._maps[self._event_name]["ylim"]
    x_shifted=x-xlims[0]
    x_scaled=x_shifted/self._maps[self._event_name]["xscale"] * (self._map_width / 630)

    y_shifted=y-ylims[0]
    y_scaled=y_shifted/self._maps[self._event_name]["yscale"] * (self._map_height / 480)
    y_updown=self._map_height-y_scaled

    return x_scaled,y_updown

  def add_driver_tel_plot(self,number,parent,driver):
    """ 
      Adds subplots with speed,throttle and brakes (can easily add the remaining) for the given driver.  
    """
    nr=int(number) # 0 -> 19 !
    x_pos=self._TEL_PLOTS_WIDTH*(nr%2) 
    x_pos_headshot = (self._TEL_PLOTS_WIDTH-95) + self._TEL_PLOTS_WIDTH*(nr%2) 
    y_pos=self._TEL_PLOTS_HEIGHT*(nr//2)+self._TOP_BAR_HEIGHT
    add_name_over_photo=False
    with dpg.group(pos=(x_pos,y_pos),height=self._TEL_PLOTS_HEIGHT,tag="wdw"+driver,parent=parent,horizontal=True):
      with dpg.subplots(rows=3,columns=1,row_ratios=(3,1,1),no_title=True,link_all_x=True,no_align=False,no_resize=False,label=self._DRIVERS_INFO[driver]["full_name"],tag=self._DRIVERS_INFO[driver]["full_name"],width=self._TEL_PLOTS_WIDTH-95,height=self._TEL_PLOTS_HEIGHT):
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
      with dpg.group(pos=(x_pos_headshot,y_pos),tag=driver+"drivers_info_telemetry",horizontal=False):
        with dpg.drawlist(width=95,height=95,pos=(0,0),tag=driver+"HeadShotUrl_drawlist"):
          map_dict=str(_config.paths.HEADSHOTS_PATH / (self._DRIVERS_INFO[driver]["full_name"]+"headshot.png"))
          if map_dict.split("/")[-1] in os.listdir(str(_config.paths.HEADSHOTS_PATH)) or map_dict.split("\\")[-1] in os.listdir(str(_config.paths.HEADSHOTS_PATH)):
            width, height, channels, data = dpg.load_image(map_dict)
            #self._map_width,self._map_height=width,height
            with dpg.texture_registry():
              dpg.add_static_texture(width=width, height=height, default_value=data, tag=driver+"HeadShotUrl")
            dpg.draw_image(texture_tag=driver+"HeadShotUrl",tag=driver+"HeadShotUrl_image",parent=driver+"HeadShotUrl_drawlist",pmin=(0,0),pmax=(width,height),show=True)
          else:
            add_name_over_photo=True
            print(map_dict," not found!")
        if add_name_over_photo:
          dpg.add_text(default_value=map_dict.split("/")[-1][-12],tag=driver+"_nameOverImage",pos=(x_pos_headshot+10,y_pos+10))
      with dpg.group(pos=(x_pos_headshot+30,y_pos+110),tag=driver+"drivers_info_telemetry_tyre",horizontal=False):
        with dpg.drawlist(width=34,height=34,pos=(0,0),tag=driver+"Tyres_drawlist"):
          with dpg.texture_registry():
            dpg.add_dynamic_texture(width=34, height=34, default_value=self.Tyres_Texture["Unknown"], tag=driver+"tyre")
          dpg.draw_image(texture_tag=driver+"tyre",tag=driver+"tyre_image",parent=driver+"Tyres_drawlist",pmin=(0,0),pmax=(34,34),show=True)
        #dpg.add_text(default_value="Tyre: ",tag=driver+"_tyreFitted",pos=(x_pos_headshot,y_pos+95+20*0))
      with dpg.group(pos=(x_pos_headshot,y_pos+150),tag=driver+"drivers_info_telemetry_tyre_text",horizontal=False):
        dpg.add_text(default_value="Tyre Age: ",tag=driver+"_agetyreFitted",pos=(x_pos_headshot+8,y_pos+140+15))
        dpg.add_text(default_value="Drs: ",tag=driver+"_drs",pos=(x_pos_headshot+8,y_pos+140+35))
        
  def Initialize_Plot(self):
    """ 
      Initialize Telemetry Tab plots, buttons , track map and menu 
    """
    # telemetry view tab    
    with dpg.group(label=self._YEAR+"-"+" ".join(self._RACE.split("_"))+"-"+self._SESSION,tag="Telemetry_view",show=True,parent="Primary window"):
      
      self._windows_manager.append("menu_bar_buttons_weather")
      with dpg.window(label="menu_bar_buttons_weather",tag="menu_bar_buttons_weather",width=self._map_width,height=self._BUTTONS_HEIGHT*self._BUTTONS_ROWS,pos=(self._TEL_PLOTS_WIDTH*2+10,self._TOP_BAR_HEIGHT),no_title_bar=True,no_resize=True,no_move=True):
        # weather group
        with dpg.group(label="Column1",tag="column1",horizontal=False,pos=(7.3*self._BUTTONS_WIDTH,0)):  
          dpg.add_text(default_value="AirTemp:",  tag="AirTemp") #
          dpg.add_text(default_value="TrackTemp:",tag="TrackTemp") #
          dpg.add_text(default_value="Rainfall:", tag="Rainfall") #
          dpg.add_text(default_value="Current Time:", tag="Actual_Time")
          dpg.add_text(default_value="Session: "+self._database.get_session_type(), tag="Session_Name")
          dpg.add_text(default_value="Session time remaining: ", tag="Session_TimeRemaining")
          #dpg.add_text(default_value="WindDirection:", tag="WindDirection") 
        with dpg.group(label="Column2",tag="column2",horizontal=False,pos=(7.3*self._BUTTONS_WIDTH+130,0)):
          dpg.add_text(default_value="WindSpeed:",tag="WindSpeed") #
          dpg.add_text(default_value="Humidity:", tag="Humidity") #
          dpg.add_text(default_value="Status:", tag="Session_Status")
          #dpg.add_text(default_value="Pressure:", tag="Pressure") 

        # buttons
        self._drivers_list=sorted(self._drivers_list,key=int)
        self.add_buttons()
        self._y_scroll=dpg.get_y_scroll(item="Primary window")
        if self._LIVE_SIM:
          self._detected_year = self._database.get_year()
        else:
          self._detected_year = str(datetime.datetime.now().year)
      
      self._windows_manager.append("Track_Map")
      with dpg.window(label="Track_Map",tag="Track_Map",width=self._map_width,height=self._map_height,pos=(self._TEL_PLOTS_WIDTH*2+10,self._TOP_BAR_HEIGHT+self._BUTTONS_HEIGHT*self._BUTTONS_ROWS+10),no_title_bar=True,no_resize=True,no_move=True):
        #with dpg.window(width=640,height=480,pos=(),tag="map_window"):
          dpg.add_drawlist(width=self._map_width,height=self._map_height,pos=(0,0),tag="drawlist_map_position")
          #dpg.draw_circle(color=(255,0,0,255),center=(100,100),radius=5,fill=(255,0,0,255),tag="circle",parent="drawlist_map_position")
      self._event_name=self._database.get_meeting_name()
      self.change_map_background()
      
      self._windows_manager.append("Race_Messages")
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


  def WaitingForAllPreStartChecks(self):
    """ 
      Pre checks before starting:
        -) Merge Completed (replays only)
        -) Driver list
    """
    if not self._LIVE: # We are in a simulation
      while not self._database.is_merge_ended():
        print("Merge not completed")
        time.sleep(5)
      if self._database.get_drivers_list()==None:
        print("No driver list... fail")
      self._list_of_msgs=self._database.get_list_of_msgs()
    
    else: # We are in a live
      while self._database.get_drivers_list()==None:
        print("Waiting for drivers list to arrive..")
        time.sleep(0.25)
    
    #self._drivers_list=self._database.get_drivers_list()
    #print("Driver list: ")
    #for driver in self._drivers_list:
    #  print("\t ",driver," : ",self._DRIVERS_INFO[driver]["full_name"])
    #print("\n")
    self._database.update_drivers_list_from_api()  
    self._drivers_list=self._database.get_drivers_list_from_api()
    for driver in self._database.get_drivers_list_from_api():
      print("\t ",driver," : ",self._DRIVERS_INFO[driver]["full_name"])
      
    self._start_compare=True
    return True

  def Initialize_DateTimes(self):
    """ 
      Initialize datetimes after pre starting checks are completed.
    """
    time.sleep(self._delay_T)
    self._time_paused+=self._delay_T
    
    self._first_message_UTC          = self._database.get_DT_Basetime()
    self._BaseTimestamp              = self._database.get_DT_Basetime_timestamp()
    self._first_message_DT_myTime    = datetime.datetime.now() 
    self._last_message_displayed_UTC = self._database.get_DT_Basetime() 
    self._last_index                 = 0
    self._last_index_checked         = 0
    
    if self._LIVE_SIM:
      self._last_message_displayed_UTC =   self._database.get_first_startingSession_DT()
      self._time_skipped               =   self._database.get_first_startingSession_DT().timestamp() \
                                         - self._first_message_UTC.timestamp()

  def recursive_children(self,object_dict,n_tab):
    """ 
      Not used for now. Useful to display all the parenting of groups and windows recursively. 
    """
    n_tab+=1
    tabbing="\t"*n_tab
    for slot,items_list in dpg.get_item_children(object_dict).items():
      for item in items_list:
        n_ch=0
        for sl,it_lsts in dpg.get_item_children(object_dict).items():
          for it in it_lsts:
            n_ch+=1
        print(tabbing,dpg.get_item_alias(item),"  ",n_ch)
        n_ch=0
        self.recursive_children(item,n_tab)
    #print(tabbing,dpg.get)

  def time_flow_handler(self):
    """ 
      Where all the magic happens.
      
      1) Initializes everything it needs to operate.
      2) Initializes TimingView tab
      3) at each iteration it updates the current time and calls the iterator to process msgs in 
         the window: (last_iteration_EndDT , last_iteration_EndDT + Time_passed_from_last_iteration)
      4) sleeps for a bit
    """
    self.WaitingForAllPreStartChecks()
    self.Initialize_Plot()
    self.Initialize_DateTimes()
    self.Timing_View()
    self.Initialize_Updaters()
    
    while True:
      while self._task_state=="pause":
        time.sleep(self._sleeptime)
        self._time_paused+=self._sleeptime
        # if it's paused than... sleep
        if self._StopUpdateThread.is_set():
          # if kill_buttons is called then we kill the run..
          break      
      if self._StopUpdateThread.is_set():
        # .. maybe redundant but this prevent the GUI to not kill itself if the run is paused. 
        break      
      
      ### here i manage the flow of time ###
      self._last_message_DT            = self._database.get_last_datetime() # maybe dont needed
      
      self._previous_message_displayed_UTC = self._last_message_displayed_UTC
      
      self._last_message_displayed_UTC  =  self._first_message_UTC \
                                         + (datetime.datetime.now() - self._first_message_DT_myTime) \
                                         - datetime.timedelta(seconds=self._time_paused) \
                                         + datetime.timedelta(seconds=self._time_skipped) 
                                         
      self.iteration(time_start = self._previous_message_displayed_UTC, \
                     time_end   = self._last_message_displayed_UTC)
      #print(self._previous_message_displayed_UTC," ",self._last_message_displayed_UTC)
      time.sleep(self._TIME_UPDATE_TELEMETRY_PLOT)
      #print(self._previous_message_displayed_UTC," ",self._last_message_displayed_UTC)
    return True
  
  def iteration(self, time_start, time_end):
    """
      It is called from the time_flow_handler. Cycles through msgs and process the ones in the
      window.
    
      list_of_msgs is a list of sorted messages in time [DateTime,Feed,Body] where:
        -) DateTime has the following format: '%H:%M:%S.%f'
        -) Feed is the string taken from the official F1 livetiming site
        -) Body is a dictionary. Originally it is a string where json.loads is applied.
           !! NB: If the feed contains .z (CarData and Position) then before applying 
                  json.loads a decription passage is performed.   
    """ 
    time_start_timestamp=time_start.timestamp()
    time_end_timestamp=time_end.timestamp()
    
    if self._LIVE:
      self._list_of_msgs=self._database.get_list_of_msgs().copy()
      #sorted(self._list_of_msgs,key=lambda x: x[2])
    
    for index,content in zip(range(self._last_index,len(self._list_of_msgs)),self._list_of_msgs[self._last_index:]): # last_index based on FW,BW also
      feed,msg,T = content[0],content[1],content[2]
      time_timestamp = T.timestamp()
      #print(T," ",time_start,"-",time_end)
      
      if time_timestamp>time_start_timestamp and time_timestamp<=time_end_timestamp:
        ### Here I update the constants ready to be displayed ###
        #print(index," ",feed)
        self.DisplayUpdater(T,feed,msg) 
        self._last_index_checked=index
        #print("iteration: ",time_start," ",time_end)
      
      elif time_timestamp>time_end_timestamp:
        break
        # saving last_index for speeding purposes
    
    #self._last_datetime_processed=time
    self._last_index=self._last_index_checked
    return True
  
  def DisplayUpdater(self,T,feed,msg):
    """ 
      The processor manager. Just a filter for each feed.
    """
    # All Database updates are now done while merging. Just to have all analysis already available when
    # performing a replay of a session
    
    # feed filtering
    if feed=="CarData.z":
      self.update_variables_CarData(T,msg) #
      #self.update_database_CarData(feed,T,msg)
        
    elif feed=="Position.z":
      self.update_variables_Position(msg)
      #self.update_database_Position(feed,T,msg)
      
    elif feed=="TimingDataF1":
      self.update_variables_TimingDataF1(T,feed,msg) 
      #self.update_database_TimingDataF1(feed,T,msg)  
            
    elif feed=="WeatherData":
      self.update_variables_WeatherData(msg) 
      
    elif feed=="SessionStatus":
      self.update_variables_SessionStatus(msg) 
      
    elif feed=="RaceControlMessages":
      self.update_variables_RaceControlMessages(feed,msg) 
      
    elif feed=="TimingAppData":
      self.update_variables_TimingAppData(feed,msg)  
      #self.update_database_TimingAppData(feed,T,msg)   
      
    else:
      return None
  
  def Initialize_Updaters_FWBW(self,cardata_chrono_flag):
    """ 
      Useful to eliminate all the infos already stored when called a backward application.
    """
    self._driver_infos_check_flags={}
    self._driver_infos_check_flags["TotalChecks"]=16*len(self._drivers_list)
    for driver in self._drivers_list:
      self._driver_infos_check_flags[driver]={}
      self._driver_infos_check_flags[driver]["InPit"]                   = False
      self._driver_infos_check_flags[driver]["PitOut"]                  = False
      self._driver_infos_check_flags[driver]["Sectors"]                 = {}
      for sector in ["0","1","2"]:
        self._driver_infos_check_flags[driver]["Sectors"][sector]= False
        
      self._driver_infos_check_flags[driver]["LastLapTime"]             = False  
      self._driver_infos_check_flags[driver]["LastLapTime_s"]           = False  
      self._driver_infos_check_flags[driver]["Position"]                = False
      self._driver_infos_check_flags[driver]["TimeDiffToFastest"]       = False
      self._driver_infos_check_flags[driver]["TimeDiffToPositionAhead"] = False
      self._driver_infos_check_flags[driver]["Retired"]                 = False
      self._driver_infos_check_flags[driver]["Compound"]                = False
      self._driver_infos_check_flags[driver]["New"]                     = False    
      self._driver_infos_check_flags[driver]["Stint"]                   = False
      self._driver_infos_check_flags[driver]["TotalLaps"]               = False
      self._driver_infos_check_flags[driver]["StartLaps"]               = False
      if not cardata_chrono_flag:
        self._CarData[driver]={}
        self._CarData[driver]["DateTime"]  = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["TimeStamp"] = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["Speed"]     = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["Throttle"]  = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["Brake"]     = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["RPM"]       = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["DRS"]       = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
        self._CarData[driver]["Gear"]      = collections.deque([],maxlen=self._MAX_LEN_DEQUES)        

  
  def AddDriverToTracker(self,driver):
    """ 
      Initialization of the displayed objects in the GUI: telemetry and timing view.
      Also adds entry for each driver in timing_view
    """
    self._CarData[driver]={}
    self._CarData[driver]["DateTime"]  = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["TimeStamp"] = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["Speed"]     = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["Throttle"]  = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["Brake"]     = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["RPM"]       = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["DRS"]       = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    self._CarData[driver]["Gear"]      = collections.deque([],maxlen=self._MAX_LEN_DEQUES)
    
    # DriverInfos
    self._driver_infos[driver]={}
    self._driver_infos[driver]["InPit"]                   = False
    self._driver_infos[driver]["PitOut"]                  = False
    self._driver_infos[driver]["Sectors"]                 = {}
    self._driver_infos[driver]["BestSectors"]             = {}
    for sector in ["0","1","2"]:
      self._driver_infos[driver]["Sectors"][sector]={"Value":    "-",
                                                     "Segment":  {}}
      self._driver_infos[driver]["BestSectors"][sector]="120.00"
    self._driver_infos[driver]["LastLapTime"]             = "-"
    self._driver_infos[driver]["LastLapTime_s"]           = 1e6
    self._driver_infos[driver]["BestLapTime"]             = "-"
    self._driver_infos[driver]["BestLapTime_s"]           = 1e6
    self._driver_infos[driver]["Position"]                = "-"
    self._driver_infos[driver]["TimeDiffToFastest"]       = "-"
    self._driver_infos[driver]["TimeDiffToPositionAhead"] = "-"
    self._driver_infos[driver]["Retired"]                 = False
    self._driver_infos[driver]["Compound"]                = "unknown"
    self._driver_infos[driver]["New"]                     = "-"    
    self._driver_infos[driver]["Stint"]                   = 0
    self._driver_infos[driver]["TotalLaps"]               = 0
    self._driver_infos[driver]["StartLaps"]               = 0
    self._driver_infos[driver]["I1"]                      = "-"
    self._driver_infos[driver]["I2"]                      = "-"
    self._driver_infos[driver]["FL"]                      = "-"
    self._driver_infos[driver]["ST"]                      = "-"
    
    # TimingView
    if driver not in self._DriverInTimingView:
      self.AddDriverToTimingView(driver)
      self._DriverInTimingView.append(driver)
  
  def Initialize_Updaters(self):
    """ 
      DateTime Speed Throttle Brake RPM DRS Gear all deques (about 6Hz) * lap_length (about 90s) * n_laps (3)
      self._driver_infos[driver] inPit PitOut Sectors Segments LastLapTime BestLapTime Position TimeDiffToFastest TimeDiffToPositionAhead Retired all strings
                                  -) Compound New Stint TotalLaps StartLaps strings
      self.session_status="Inactive"
      self._msgs string
      self._Best_OverallLap
    """
    
    # frequency (about 6Hz) * lap_length (about 90s) * n_laps (3)
    self._MAX_LEN_DEQUES = int(self._FREQUENCY_TELEMETRY_UPDATE * self._AVG_LAP_LENGTH * (self._LAPS_TO_DISPLAY+0.25))
    self._CarData={}
    self._driver_infos={}
    for driver in self._drivers_list:
      self.AddDriverToTracker(driver)
      
    self._Best_OverallLap = ["",1e6]
    # SessionStatus
    self._sessions_status="Inactive"
    
    # RaceControlMessages
    self._msgs_string=""
  
  #####################################################################################
  
  def find_maxmin_indices(self,arr: np.array,maximum: bool):
    """ 
      Helper function to get the local maxima/minima of the array.
      The -5 is VITAL otherwise it detects the final index as max/min at each call.
      Cons: lags a bit in displaying maxima/minima (those 5 indices)
    """
    if maximum:
      arrExtrema=scipy.signal.argrelextrema(arr, np.greater_equal,order=3)[0]
    else:
      arrExtrema=scipy.signal.argrelextrema(arr, np.less_equal,order=3)[0]
    # otherwise the last value will always be an extrema and with multiple iteration is gonna write all values lol
    arrExtrema_New=np.array([i for i in arrExtrema if i<len(arr)-5]) 
    if len(arrExtrema_New)>0:
      diff = np.diff(arrExtrema_New, prepend=arrExtrema_New[0])
      #diff = np.pad(diff, (0, 1), constant_values=False)  # Pad with False at the end
      mask = diff != 1
      indices = arrExtrema_New[mask]
    else:
      indices=np.array([])
    return indices
  
  #####       CarData.z     #####
  def update_variables_CarData(self,T,msg):
    """
    need to update telemetry data for all drivers. How are they composed? 
      Dictionary with keys as drivers
      Each driver is a dictionary with the following keys:
        DateTime
        Speed
        Throttle
        Brake
        RPM
        DRS
          0 = Off
          1 = Off
          2 = (?)
          3 = (?)
          8 = Detected, Eligible once in Activation Zone (Noted Sometimes)
          10 = On (Unknown Distinction)
          12 = On (Unknown Distinction)
          14 = On (Unknown Distinction)
        Gear
      These are all deques. 
      The length is based on freq (about 6Hz) * lap_length (about 90s) * n_laps (3)
    """
    for driver,channels in msg.items():
      # updating the telemetry
      #print(driver," ",time)
      if driver not in self._CarData.keys() and len(driver)<3:
          self.AddDriverToTracker(driver)
      elif len(driver)>2:
        return True
      
      self._CarData[driver]["DateTime"].append(T)
      self._CarData[driver]["TimeStamp"].append(T.timestamp()-self._first_message_UTC.timestamp())
      self._CarData[driver]["RPM"].append(channels["Channels"]["0"])
      self._CarData[driver]["Speed"].append(channels["Channels"]["2"])
      self._CarData[driver]["Gear"].append(channels["Channels"]["3"])
      self._CarData[driver]["Throttle"].append(channels["Channels"]["4"] if channels["Channels"]["4"]<101 else 0)
      self._CarData[driver]["Brake"].append(int(channels["Channels"]["5"]) if int(channels["Channels"]["5"])<101 else 0)
      self._CarData[driver]["DRS"].append(1 if channels["Channels"]["45"] in [10,12,14] else 0)
      #print(channels["Channels"]["45"])
      drs= "On" if channels["Channels"]["45"] in [10,12,14] else "Off"
      dpg.set_value(item=driver+"_drs",value="Drs: "+drs)
      #print(driver, " ",T.timestamp()-self._first_message_UTC.timestamp()," ",channels["Channels"]["2"])
    
    
    # updating the display. Minx,Maxx are called for updates x_limits. For the first seconds the telemetry 
    # needs to fill the plot from 0 to _WINDOW_DISPLAY_LENGTH-_WINDOW_DISPLAY_PROPORTION_RIGHT
    minx=max(self._first_message_UTC.timestamp()-self._BaseTimestamp,self._last_message_displayed_UTC.timestamp()-self._BaseTimestamp-self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_LEFT)
    maxx=max(self._first_message_UTC.timestamp()-self._BaseTimestamp+self._WINDOW_DISPLAY_LENGTH,self._last_message_displayed_UTC.timestamp()-self._BaseTimestamp+self._WINDOW_DISPLAY_LENGTH*self._WINDOW_DISPLAY_PROPORTION_RIGHT)
    
    #print(minx,maxx)
    #print("\n ",self._database.get_dictionary(feed="RaceControlMessages"),"\n")
    
    # DPG doesn't handle properly times as labels. So i have to construct it myself.
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
    
    # calling the maxima/minima function for each driver and display the annotations 
    # on the plot. Checks also if these annotations are now out of the axis limits and
    # eliminate them if true.
    for driver,telemetry in self._CarData.items():
      if driver in self._drivers_list:
        speeds_tel=list(telemetry["Speed"])
        times=list(telemetry["TimeStamp"])
        #print(driver,speeds_tel[0])
        if len(speeds_tel)>5:
          
          maxInd=self.find_maxmin_indices(arr=np.array(speeds_tel),maximum=True)
          minInd=self.find_maxmin_indices(arr=np.array(speeds_tel),maximum=False)
          
          # Write annotations
          # While writing check if some of them are already displayed, if yes do nothing
          for idx in maxInd:
            if not dpg.does_item_exist(driver+"_max_"+str(times[idx])) and times[idx]>minx:
              dpg.add_plot_annotation(label=str(int(speeds_tel[idx])),tag=driver+"_max_"+str(times[idx]), default_value=(times[idx],speeds_tel[idx]), offset=(0,-5), color=[0,0,0,0],parent="speed"+driver)
          for idx in minInd:
            if not dpg.does_item_exist(driver+"_min_"+str(times[idx])) and times[idx]>minx:
              dpg.add_plot_annotation(label=str(int(speeds_tel[idx])),tag=driver+"_min_"+str(times[idx]), default_value=(times[idx],speeds_tel[idx]), offset=(0,+5), color=[0,0,0,0],parent="speed"+driver)
          
          # Delete annotations outside the minx maxx area
          list_of_ann_to_delete=[]
          for subitem,listofchildrens in dpg.get_item_children(item="speed"+driver).items():
            for ch in listofchildrens:
              if "_min_" in dpg.get_item_alias(ch) or "_max_" in dpg.get_item_alias(ch):
                pos_x=dpg.get_value(ch)[0]
                if pos_x<minx:
                  list_of_ann_to_delete.append(ch)
            
          for item in list_of_ann_to_delete:
            dpg.delete_item(item=item)
        
        # Checks if laptimes annotations are out of the limits and deletes it  
        list_of_items_to_delete=[]
        for subitem,listofchildrens in dpg.get_item_children(item="y_axis_SPEED"+driver).items():
          for ch in listofchildrens:
            ch_name=dpg.get_item_alias(ch)
            if "vline" in ch_name:
              pos_x=dpg.get_value(ch)[0][0]
              if pos_x<minx:
                list_of_items_to_delete.append(ch_name)
                if dpg.does_item_exist(ch_name+"_ann"):
                  dpg.delete_item(ch_name+"_ann")
                
        for item in list_of_items_to_delete:
          dpg.delete_item(item=item)
        
        # Updating telemetry
        dpg.set_value(item=driver+"s", value=[list(self._CarData[driver]["TimeStamp"]),list(self._CarData[driver]["Speed"])])
        dpg.set_value(item=driver+"t", value=[list(self._CarData[driver]["TimeStamp"]),list(self._CarData[driver]["Throttle"])])
        dpg.set_value(item=driver+"b", value=[list(self._CarData[driver]["TimeStamp"]),list(self._CarData[driver]["Brake"])])

        # Updating axis
        dpg.set_axis_limits("x_axis_BRAKE"+driver, minx, maxx)
        dpg.set_axis_ticks(axis="x_axis_BRAKE"+driver,label_pairs=x_label)
        dpg.set_axis_ticks(axis="x_axis_THROTTLE"+driver,label_pairs=x_label)
        dpg.set_axis_ticks(axis="x_axis_SPEED"+driver,label_pairs=x_label)
          
  
  def update_database_CarData(self,feed,T,msg):
    """ 
      All the update_database are not used now. Switched to:
        -) replays: merge at the beginning
        -) lives  : update when receiving msgs directly in the signalr package 
    """
    self._database.update_database({T:msg},feed)
  
  #####      Position.z     #####
  def update_variables_Position(self,msg):
    """ 
      To display position we only need the last information available. 
      So it will be a dictionary with a list of [x,y].
      NB: x,y are already measured in pixels.
    """
    for driver,positions in msg.items():
      self.update_position_driver(driver,self.transform_position_from_F1_to_dpg(positions["X"]/10.,positions["Y"]/10.))
  
  def update_database_Position(self,feed,T,msg):
    """ 
      All the update_database are not used now. Switched to:
        -) replays: merge at the beginning
        -) lives  : update when receiving msgs directly in the signalr package 
    """
    self._database.update_database({T:msg},feed)
  
  def update_position_driver(self,driver,xyz_dpg):
    """ 
      Helper function.
    """
    if not dpg.does_item_exist("node"+driver):
      with dpg.draw_node(tag="node"+driver,parent="drawlist_map_position"):
        dpg.draw_circle(color=self._DRIVERS_INFO[driver]["color"],center=(xyz_dpg[0],xyz_dpg[1]),radius=12,fill=self._DRIVERS_INFO[driver]["color"],tag="circle"+driver)
        dpg.draw_text(tag="text"+driver,pos=(xyz_dpg[0]-12/2,xyz_dpg[1]-12/2.),text=self._DRIVERS_INFO[driver]["abbreviation"],color=[255,255,255])
        dpg.bind_item_font(item="text"+driver,font="drawNodeFont")
    else:
      prev_pos=dpg.get_item_configuration("circle"+driver)['center']
      dpg.apply_transform(item="node"+driver, transform=dpg.create_translation_matrix([xyz_dpg[0]-prev_pos[0], 
                                                                                                 xyz_dpg[1]-prev_pos[1]]))
  
  
  #####     TimingDataF1    #####
  def AdjustOtherDisplayedLaptimes(self,driver: str, laptime_str: str,ColorLine: str):
    """ 
      This function adjust the color (green, purple, yellow) of previous laps that are displayed
      when a lap better than yellow is set from a driver.
    """
    if ColorLine=="NormalLap":
      pass
    elif ColorLine=="BestPersonalLap":
      # make all other laps of the driver yellow
      for subitem,listofchildrens in dpg.get_item_children(item="y_axis_SPEED"+driver).items():
        for ch in listofchildrens:
          vline_name=dpg.get_item_alias(ch)
          if "vline" in vline_name and laptime_str not in vline_name:
            #print(driver, " set previous lap of: ",dpg.get_item_alias(ch)," to yellow")
            dpg.bind_item_theme(dpg.get_item_alias(ch),"NormalLap")
    elif ColorLine=="BestOverallLap":
      # make the last BestOverallLap a BestPersonalLap
      drv=self._prev_Best_OverallLap[0]
      if drv in self._drivers_list:
        for subitem,listofchildrens in dpg.get_item_children(item="y_axis_SPEED"+drv).items():
          for ch in listofchildrens:
            if dpg.get_item_alias(dpg.get_item_theme(ch))=="BestOverallLap" and dpg.get_item_alias(ch)!="vline"+driver+laptime_str:
              # check if lap is already displayed as BestOverall and turn BestPersonal IF IT IS NOT the one just set from the fastest driver
              # This is to prevent that a fastest lap from a driver who already had the fastest lap, is set to Green instead of purple
              #print(drv, " set previous lap of: ",dpg.get_item_alias(ch)," to green")
              dpg.bind_item_theme(dpg.get_item_alias(ch),"BestPersonalLap")
          
  def update_variables_TimingDataF1(self,T,feed,msg):
    """
      Useful infos: 
        -) inPit
        -) PitOut
        -) Sectors
        -) Segments
        -) LastLapTime
        -) BestLapTime
        -) Position
        -) TimeDiffToFastest
        -) TimeDiffToPositionAhead
        -) Retired
        -) GapToLeader
        -) IntervalToPositionAhead -> {"Value":"+2.259"}
        -) Speeds {"I1", "I2","FL","ST"} -> "Value": str , "PersonalFastest": bool
        
    """
    if type(msg)==dict:
      if "Lines" in msg.keys():
        for driver,info_driver in msg["Lines"].items():
          if driver not in self._CarData.keys() and len(driver)<3:
            self.AddDriverToTracker(driver)
          elif len(driver)>2:
            return True
          for info,value in info_driver.items():
            if info=="InPit":
              self._driver_infos[driver]["InPit"]=value
            elif info=="PitOut":
              self._driver_infos[driver]["PitOut"]=value
            elif info=="Sectors":
              if type(value)==list:
                for nsector,info_sector in enumerate(value):
                  if "Value" in info_sector.keys():
                    if info_sector["Value"].replace('.','',1).isdigit():
                      if float(info_sector["Value"])<float(self._driver_infos[driver]["BestSectors"][str(nsector)]):
                        self._driver_infos[driver]["BestSectors"][str(nsector)]=info_sector["Value"]
                        dpg.set_value(driver+"Bestsector"+str(int(nsector)+1),info_sector["Value"])
                    self._driver_infos[driver]["Sectors"][str(nsector)]["Value"]=info_sector["Value"]
                    dpg.set_value(item=driver+"sector"+str(int(nsector)+1),value=info_sector["Value"])
                  if "Segments" in info_sector.keys():
                    for segment,status in info_sector["Segments"].items():
                      self._driver_infos[driver]["Sectors"][str(nsector)]["Segment"][str(segment)]=self._segments[str(status["Status"])] # for now not decrypted
                      if not dpg.does_item_exist(driver+"segments"+str(1+int(nsector))+"musec"+str(segment)):
                        dpg.add_button(label="",tag=driver+"segments"+str(1+int(nsector))+"musec"+str(segment),parent=driver+"segments"+str(1+int(nsector))+"musec")
                      dpg.bind_item_theme(item=driver+"segments"+str(1+int(nsector))+"musec"+str(segment),theme=self._segments[str(status["Status"])] )
              elif type(value)==dict:
                for nsector,info_sector in value.items():
                  if "Value" in info_sector.keys():
                    if info_sector["Value"].replace('.','',1).isdigit():
                      if float(info_sector["Value"])<float(self._driver_infos[driver]["BestSectors"][str(nsector)]):
                        self._driver_infos[driver]["BestSectors"][str(nsector)]=info_sector["Value"]
                        dpg.set_value(driver+"Bestsector"+str(int(nsector)+1),info_sector["Value"])
                    self._driver_infos[driver]["Sectors"][nsector]["Value"]=info_sector["Value"]
                    dpg.set_value(item=driver+"sector"+str(int(nsector)+1),value=info_sector["Value"])
                  if "Segments" in info_sector.keys():
                    if type(info_sector["Segments"])==dict:
                      for segment,status in info_sector["Segments"].items():
                        self._driver_infos[driver]["Sectors"][nsector]["Segment"][segment]=self._segments[str(status["Status"])] # for now not decrypted
                        if not dpg.does_item_exist(driver+"segments"+str(1+int(nsector))+"musec"+str(segment)):
                          dpg.add_button(label="",tag=driver+"segments"+str(1+int(nsector))+"musec"+str(segment),parent=driver+"segments"+str(1+int(nsector))+"musec")
                        dpg.bind_item_theme(item=driver+"segments"+str(1+int(nsector))+"musec"+str(segment),theme=self._segments[str(status["Status"])] )
                        #print("Color changed at: ",driver+"segments"+str(1+int(nsector))+"musec"+str(segment),"  to: ",self._segments[str(status["Status"])])
                    elif type(info_sector["Segments"])==list:
                      for segment,status in enumerate(info_sector["Segments"]):
                        self._driver_infos[driver]["Sectors"][str(nsector)]["Segment"][str(segment)]=self._segments[str(status["Status"])] # for now not decrypted
                        if not dpg.does_item_exist(driver+"segments"+str(1+int(nsector))+"musec"+str(segment)):
                          dpg.add_button(label="",tag=driver+"segments"+str(1+int(nsector))+"musec"+str(segment),parent=driver+"segments"+str(1+int(nsector))+"musec")
                        dpg.bind_item_theme(item=driver+"segments"+str(1+int(nsector))+"musec"+str(segment),theme=self._segments[str(status["Status"])] )
            elif info=="LastLapTime":
              if "Value" in value.keys():
                self._driver_infos[driver]["LastLapTime"]=value["Value"]
                dpg.set_value(item=driver+"LastLapTime",value=value["Value"])
                ColorLine="NormalLap" # "BestOverallLap" "BestPersonalLap" 
                if value["Value"]!="":
                  mins,secs=value["Value"].split(":")
                  Value_int=round(int(mins)*60. + float(secs),3) # s
                  if not dpg.does_item_exist("vline"+driver+value["Value"]):
                    #print(driver,"  at: ",T.timestamp()-self._first_message_UTC.timestamp()," with: ",value["Value"])
                    dpg.add_vline_series(x=[T.timestamp()-self._first_message_UTC.timestamp()],tag="vline"+driver+value["Value"],label=value["Value"],parent="y_axis_SPEED"+driver)
                    dpg.add_plot_annotation(label=value["Value"],tag="vline"+driver+value["Value"]+"_ann", default_value=(T.timestamp()-self._first_message_UTC.timestamp(),dpg.get_axis_limits("y_axis_SPEED"+driver)[1]-5), offset=(2,), color=[0,0,0,0],parent="speed"+driver) 
                  self._driver_infos[driver]["LastLapTime_s"] = Value_int
                  if Value_int<self._driver_infos[driver]["BestLapTime_s"]:
                    self._driver_infos[driver]["BestLapTime"]   = value["Value"]
                    self._driver_infos[driver]["BestLapTime_s"] = Value_int
                    dpg.set_value(item=driver+"BestLapTime",value=value["Value"])
                    ColorLine="BestPersonalLap"
                    #print(driver,ColorLine)
                  if Value_int<self._Best_OverallLap[1]:
                    self._prev_Best_OverallLap=self._Best_OverallLap.copy()
                    self._Best_OverallLap=[driver,Value_int]
                    ColorLine="BestOverallLap"
                    #print(driver,ColorLine)
                  #print(self._Best_OverallLap," ",driver,": ",self._driver_infos[driver]["BestLapTime"]," ",ColorLine)
                  dpg.bind_item_theme("vline"+driver+value["Value"],ColorLine)
                  #print("vline"+driver+value["Value"]," set to: ",ColorLine)
                  self.AdjustOtherDisplayedLaptimes(driver,value["Value"],ColorLine)
            elif info=="BestLapTime":
              #if "Value" in value.keys():
              #  self._driver_infos[driver]["BestLapTime"]=value["Value"]
              #  if value["Value"]!="":
              #    mins,secs=value["Value"].split(":")
              #    Value_int=int(mins)*60. + float(secs) # s
              #    self._driver_infos[driver]["BestLapTime_s"] = Value_int
              #    if Value_int<self._Best_OverallLap[1]:
              #      self._Best_OverallLap=[driver,Value_int]
              pass
            elif info=="Position":
              self._driver_infos[driver]["Position"]=value
              dpg.set_value(item=driver+"Position",value=value)
            elif info=="TimeDiffToFastest" or info=="GapToLeader":
              self._driver_infos[driver]["TimeDiffToFastest"]=value
              dpg.set_value(item=driver+"gap",value=value)
            elif info=="TimeDiffToPositionAhead" or info=="IntervalToPositionAhead":
              if type(value)==dict:
                if "Value" in value.keys():
                  self._driver_infos[driver]["TimeDiffToPositionAhead"]=str(value["Value"])
                  dpg.set_value(item=driver+"int",value=str(value["Value"]))
              else:
                self._driver_infos[driver]["TimeDiffToPositionAhead"]=value
                dpg.set_value(item=driver+"int",value=value)
            elif info=="Retired":
              self._driver_infos[driver]["Retired"]=value
            elif info=="Speeds":
              for speedPoint,speedPoint_info in value.items():
                if "Value" in speedPoint_info.keys():
                  self._driver_infos[driver][speedPoint]=speedPoint_info["Value"]
                  if "PersonalFastest" in speedPoint_info.keys():
                    if speedPoint_info["PersonalFastest"]==True:
                      dpg.set_value(driver+speedPoint,speedPoint_info["Value"])
              
  def update_database_TimingDataF1(self,feed,T,msg):
    """ 
      All the update_database are not used now. Switched to:
        -) replays: merge at the beginning
        -) lives  : update when receiving msgs directly in the signalr package 
    """    
    self._database.update_database({T:msg},feed)
  
  #####      WeatherData    #####
  def update_variables_WeatherData(self,msg):
    for key,value in msg.items():
      #print(key)
      if dpg.does_item_exist(item=key):
        dpg.set_value(item=key,value=str(key)+":"+str(value))
  
  #####     SessionStatus   #####
  def update_variables_SessionStatus(self,msg):
    if msg["Status"]=="Inactive":
      self.session_status="Inactive"
    elif msg["Status"]=="Started":
      self.session_status="Green Flag"
    elif msg["Status"]=="Aborted":
      self.session_status="Red Flag"
    elif msg["Status"]=="Finished":
      self.session_status="Chequered Flag"
    else:
      self.session_status=msg["Status"]
  
  ##### RaceControlMessages #####
  def update_variables_RaceControlMessages(self,feed,msg):
    """ 
      Could be optimized to extrapolate infos from raceControlMessages instead of 
      only displaying them as plain text. 
    """
    if "Messages" in msg.keys():
      if type(msg["Messages"])==list:
        i=0
        for msg in msg["Messages"]:
          Message_dict={str(i):msg}
          i+=1
      elif type(msg["Messages"])==dict:
        Message_dict=msg["Messages"]
      else:
       print("\n\n\n Type of the message not dict or list but: ",type(msg["Messages"]),"\n\n\n")
       Message_dict={}
      for nrMsg,Msg in Message_dict.items():
        if "Message" in Msg.keys() and "Category" in Msg.keys() and "Utc" in Msg.keys():
          if "Flag" in Msg.keys():
            category=Msg["Category"]+"_"+Msg["Flag"]
          else:
            category=Msg["Category"]
          self._msgs_string += nrMsg + " - " + Msg["Utc"] + " - " + category.split("_")[-1] + " : " + Msg["Message"] +" \n\n" 
    
    dpg.set_value(item="race_msgs",value=self._msgs_string)
    dpg.set_y_scroll(item="Race_Messages",value=dpg.get_y_scroll_max(item="Race_Messages")) 
  
  #####     TimingAppData   #####
  def update_variables_TimingAppData(self,feed,msg):
    """ 
      Useful infos: 
        -) Compound
        -) New
        -) Stint
        -) TotalLaps
        -) StartLaps
    """
    if type(msg)==dict:
      if "Lines" in msg.keys():
        for driver,info_driver in msg["Lines"].items():
          if driver not in self._CarData.keys() and len(driver)<3:
            self.AddDriverToTracker(driver)
          elif len(driver)>2:
            return True
          if type(info_driver)==dict:
            if "Stints" in info_driver.keys():
              if type(info_driver["Stints"])==dict:
                for stint,info_stint in info_driver["Stints"].items():
                  self._driver_infos[driver]["Stint"]=stint
                  if "Compound" in info_stint.keys():
                    self._driver_infos[driver]["Compound"]=info_stint["Compound"]
                  if "New" in info_stint.keys():
                    self._driver_infos[driver]["New"]=info_stint["New"]
                  if "StartLaps" in info_stint.keys():
                    self._driver_infos[driver]["StartLaps"]=info_stint["StartLaps"]
                  if "TotalLaps" in info_stint.keys():
                    self._driver_infos[driver]["TotalLaps"]=info_stint["TotalLaps"]
          #dpg.set_item_label(item=self._DRIVERS_INFO[driver]["full_name"],label=self._DRIVERS_INFO[driver]["full_name"]+" "+self._driver_infos[driver]["Compound"]+" "+str(self._driver_infos[driver]["New"])+" "+str(self._driver_infos[driver]["Stint"])+" "+str(int(self._driver_infos[driver]["StartLaps"])+int(self._driver_infos[driver]["TotalLaps"])))
          dpg.set_value(driver+"tyre",self.Tyres_Texture[self._driver_infos[driver]["Compound"].capitalize()])
          dpg.set_value(item=driver+"_agetyreFitted",value="Tyre Age: "+str(int(self._driver_infos[driver]["StartLaps"])+int(self._driver_infos[driver]["TotalLaps"])))
  
  def update_database_TimingAppData(self,feed,T,msg):
    """ 
      All the update_database are not used now. Switched to:
        -) replays: merge at the beginning
        -) lives  : update when receiving msgs directly in the signalr package 
    """    
    self._database.update_database({T:msg},feed)
  
  #####################################################################################
  
  def update_displayer_FWBW(self,T,feed,msg):
    """ 
      Not used anymore. Could be improved for performance optimizations, but for now
      it is not required.
    """
    if feed=="TimingDataF1":
      if type(msg)==dict:
        if "Lines" in msg.keys():
          for driver,info_driver in msg["Lines"].items():
            for info,value in info_driver.items():
              
              if info=="InPit" and not self._driver_infos_check_flags[driver]["InPit"] and not self._driver_infos_check_flags[driver]["PitOut"]:
                self._driver_infos[driver]["InPit"]=value
                self._driver_infos[driver]["PitOut"]=not value
                self._driver_infos_check_flags[driver]["InPit"]=True
                self._driver_infos_check_flags[driver]["PitOut"]=True
                self._driver_infos_check_flags["TotalChecks"]-=2
              
              elif info=="PitOut" and not self._driver_infos_check_flags[driver]["InPit"] and not self._driver_infos_check_flags[driver]["PitOut"]:
                self._driver_infos[driver]["PitOut"]=value
                self._driver_infos[driver]["InPit"]=not value
                self._driver_infos_check_flags[driver]["InPit"]=True
                self._driver_infos_check_flags[driver]["PitOut"]=True
                self._driver_infos_check_flags["TotalChecks"]-=2
                              
              elif info=="Sectors":
                if type(value)==list:
                  for nsector,info_sector in enumerate(value):
                    
                    if "Value" in info_sector.keys() and not self._driver_infos_check_flags[driver]["Sectors"][str(nsector)]:
                      self._driver_infos[driver]["Sectors"][str(nsector)]["Value"]=info_sector["Value"]
                      self._driver_infos_check_flags[driver]["Sectors"][str(nsector)]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
                
                elif type(value)==dict:
                  for nsector,info_sector in value.items():
                    
                    if "Value" in info_sector.keys() and not self._driver_infos_check_flags[driver]["Sectors"][str(nsector)]:
                      self._driver_infos[driver]["Sectors"][nsector]["Value"]=info_sector["Value"]
                      self._driver_infos_check_flags[driver]["Sectors"][str(nsector)]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
              
              elif info=="LastLapTime":
                if "Value" in value.keys():
                  if not self._driver_infos_check_flags[driver]["LastLapTime"]:
                    self._driver_infos[driver]["LastLapTime"]=value["Value"]
                    self._driver_infos_check_flags["TotalChecks"]-=1
                  self._driver_infos_check_flags[driver]["LastLapTime"]=True
                  ColorLine="NormalLap" # "BestOverallLap" "BestPersonalLap" 
                  if value["Value"]!="":
                    mins,secs=value["Value"].split(":")
                    Value_int=round(int(mins)*60. + float(secs),3) # s
                    if not dpg.does_item_exist("vline"+driver+value["Value"]):
                      dpg.add_vline_series(x=[T.timestamp()-self._first_message_UTC.timestamp()],tag="vline"+driver+value["Value"],label=value["Value"],parent="y_axis_SPEED"+driver)
                      dpg.add_plot_annotation(label=value["Value"],tag="vline"+driver+value["Value"]+"_ann", default_value=(T.timestamp()-self._first_message_UTC.timestamp(),dpg.get_axis_limits("y_axis_SPEED"+driver)[1]-5), offset=(2,), color=[0,0,0,0],parent="speed"+driver) 
                    if not self._driver_infos_check_flags[driver]["LastLapTime_s"]:
                      self._driver_infos_check_flags["TotalChecks"]-=1
                      self._driver_infos[driver]["LastLapTime_s"] = Value_int
                    self._driver_infos_check_flags[driver]["LastLapTime_s"]=True
                    if Value_int<self._driver_infos[driver]["BestLapTime_s"]:
                      self._driver_infos[driver]["BestLapTime"]   = value["Value"]
                      self._driver_infos[driver]["BestLapTime_s"] = Value_int
                      ColorLine="BestPersonalLap"
                      #print(driver,ColorLine)
                    if Value_int<self._Best_OverallLap[1]:
                      self._prev_Best_OverallLap=self._Best_OverallLap.copy()
                      self._Best_OverallLap=[driver,Value_int]
                      ColorLine="BestOverallLap"
                      #print(driver,ColorLine)
                    #print(self._Best_OverallLap," ",driver,": ",self._driver_infos[driver]["BestLapTime"]," ",ColorLine)
                    dpg.bind_item_theme("vline"+driver+value["Value"],ColorLine)
                    #print("vline"+driver+value["Value"]," set to: ",ColorLine)
                    self.AdjustOtherDisplayedLaptimes(driver,value["Value"],ColorLine)

              elif info=="Position" and not self._driver_infos_check_flags[driver]["Position"]:
                self._driver_infos[driver]["Position"]=value
                self._driver_infos_check_flags[driver]["Position"]=True
                self._driver_infos_check_flags["TotalChecks"]-=1
              
              elif (info=="TimeDiffToFastest" or info=="GapToLeader") and not self._driver_infos_check_flags[driver]["TimeDiffToFastest"]:
                self._driver_infos[driver]["TimeDiffToFastest"]=value
                self._driver_infos_check_flags[driver]["TimeDiffToFastest"]=True
                self._driver_infos_check_flags["TotalChecks"]-=1
              
              elif (info=="TimeDiffToPositionAhead" or info=="IntervalToPositionAhead") and not self._driver_infos_check_flags[driver]["TimeDiffToPositionAhead"]:
                if type(value)==dict:
                  if "Value" in value.keys():
                    self._driver_infos[driver]["TimeDiffToPositionAhead"]=str(value["Value"])
                else:
                  self._driver_infos[driver]["TimeDiffToPositionAhead"]=value
                self._driver_infos_check_flags[driver]["TimeDiffToPositionAhead"]=True
                self._driver_infos_check_flags["TotalChecks"]-=1
              
              elif info=="Retired" and not self._driver_infos_check_flags[driver]["Position"]:
                self._driver_infos[driver]["Retired"]=value
                self._driver_infos_check_flags[driver]["Retired"]=True
                self._driver_infos_check_flags["TotalChecks"]-=1
    
    elif feed=="TimingAppData":
      if type(msg)==dict:
        if "Lines" in msg.keys():
          for driver,info_driver in msg["Lines"].items():
            if type(info_driver)==dict:
              if "Stints" in info_driver.keys():
                if type(info_driver["Stints"])==dict:
                  for stint,info_stint in info_driver["Stints"].items():
                    
                    if not self._driver_infos_check_flags[driver]["Stint"]:
                      self._driver_infos[driver]["Stint"]=stint
                      self._driver_infos_check_flags[driver]["Stint"]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
                    
                    if "Compound" in info_stint.keys() and not self._driver_infos_check_flags[driver]["Compound"]:
                      self._driver_infos[driver]["Compound"]=info_stint["Compound"]
                      self._driver_infos_check_flags[driver]["Stint"]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
                      
                    if "New" in info_stint.keys() and not self._driver_infos_check_flags[driver]["New"]:
                      self._driver_infos[driver]["New"]=info_stint["New"]
                      self._driver_infos_check_flags[driver]["New"]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
                      
                    if "StartLaps" in info_stint.keys() and not self._driver_infos_check_flags[driver]["StartLaps"] :
                      self._driver_infos[driver]["StartLaps"]=info_stint["StartLaps"]
                      self._driver_infos_check_flags[driver]["StartLaps"]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
                      
                    if "TotalLaps" in info_stint.keys() and not self._driver_infos_check_flags[driver]["TotalLaps"]:
                      self._driver_infos[driver]["TotalLaps"]=info_stint["TotalLaps"]
                      self._driver_infos_check_flags[driver]["TotalLaps"]=True
                      self._driver_infos_check_flags["TotalChecks"]-=1
  
  def update_telemetry_FWBW(self,T,msg,chrono_flag):
    """ 
      Same of update_variables_cardata but without displaying them.
      It is called when a FW or BW instance is made. Just to update the telemetry variables quickly.
    """
    if chrono_flag:
      for driver,channels in msg.items():
        # updating the telemetry
        #print(driver," ",time)
        if driver not in self._CarData.keys() and len(driver)<3:
          self.AddDriverToTracker(driver)
        elif len(driver)>2:
          return True
        self._CarData[driver]["DateTime"].append(T)
        self._CarData[driver]["TimeStamp"].append(T.timestamp()-self._first_message_UTC.timestamp())
        self._CarData[driver]["RPM"].append(channels["Channels"]["0"])
        self._CarData[driver]["Speed"].append(channels["Channels"]["2"])
        self._CarData[driver]["Gear"].append(channels["Channels"]["3"])
        self._CarData[driver]["Throttle"].append(channels["Channels"]["4"] if channels["Channels"]["4"]<101 else 0)
        self._CarData[driver]["Brake"].append(int(channels["Channels"]["5"]) if int(channels["Channels"]["5"])<101 else 0)
        self._CarData[driver]["DRS"].append(1 if channels["Channels"]["45"] in [10,12,14] else 0)
        #print(driver, " ",T.timestamp()-self._first_message_UTC.timestamp()," ",channels["Channels"]["2"])
    else:
      if (T.timestamp()-self._BaseTimestamp)<self._minx_tel:
        if self._DEBUG_PRINT:
          print("Telemetry switching to false ",(T.timestamp()-self._BaseTimestamp)," ",self._minx_tel)
        self._TelemetryFlag=True
      else:
        for driver,channels in msg.items():
          # updating the telemetry
          #print(driver," ",T)
          if driver not in self._CarData.keys() and len(driver)<3:
            self.AddDriverToTracker(driver)
          elif len(driver)>2:
            return True

          self._CarData[driver]["DateTime"].appendleft(T)
          self._CarData[driver]["TimeStamp"].appendleft(T.timestamp()-self._first_message_UTC.timestamp())
          self._CarData[driver]["RPM"].appendleft(channels["Channels"]["0"])
          self._CarData[driver]["Speed"].appendleft(channels["Channels"]["2"])
          self._CarData[driver]["Gear"].appendleft(channels["Channels"]["3"])
          self._CarData[driver]["Throttle"].appendleft(channels["Channels"]["4"] if channels["Channels"]["4"]<101 else 0)
          self._CarData[driver]["Brake"].appendleft(int(channels["Channels"]["5"]) if int(channels["Channels"]["5"])<101 else 0)
          self._CarData[driver]["DRS"].appendleft(1 if channels["Channels"]["45"]%2==0 else 0)

  
  
  #####################################################################################
  
  def laptime_from_string_to_seconds(self,laptime_str):
    splitted_laptime=laptime_str.split(":")
    if len(splitted_laptime)>2:
      return "-"
    elif len(splitted_laptime)==1:
      return float(splitted_laptime[0])
    elif len(splitted_laptime)==2:
      return float(splitted_laptime[0])*60. + float(splitted_laptime[1])
    
#####################################################################################s

  def Set_Corners(self):
    """ 
      CallBack. Set corners and sectors in x_axis_SPEED_Compare 
    """
    map_dict=self._maps[dpg.get_value("map")]
    circuit_length=map_dict["circuit_length"]
    self._xTurns=[]
    offset_value=dpg.get_value("slide_corner")
    for corner in map_dict["corners"]:
      self._xTurns.append((str(corner["number"]),round(corner["length"]/circuit_length,5)))
    self._xTurns=tuple(self._xTurns)
    self._xSectors=[]
    if "sectors" in map_dict.keys():
      for nsector,position in map_dict["sectors"].items():
        self._xSectors.append(round(position/circuit_length,5))
      dpg.set_value(item="speed_sectors",value=[self._xSectors])
    dpg.set_axis_ticks("x_axis_SPEED_Compare",self._xTurns)
    #print(self._xTurns)          

#############################################################################################################################  
  
  def Compare_Telemetry_2(self):
    """ 
      Second Telemetry thread: comparing laps and long runs.
    """
    while not self._start_compare:
      #print(self._database.get_dictionary("CarData.z"))
      #if self._DEBUG_PRINT:
      #  print("Waiting for drivers_list to arrive in GUI...")
      #print("Still no drivers list..")
      time.sleep(1)
    
    # Much of these is not needed anymore. Check it.
    self._n_drivers=4
    self._xTurns=[(str(round(tick,2)),round(tick,2)) for tick in np.linspace(0,1,11)]
    self._xTurns=tuple(self._xTurns)
    self._saved_drivers={}
    self._arg_maxima1="None"
    self._arg_maxima2="None"
    self._arg_minima1="None"
    self._arg_minima2="None"
    self._update_ann1=True
    self._update_ann2=True
    self._offset={}
    minx1=0
    maxx1=1
    minx2=0
    maxx2=1
    ymin_LT=60 #
    ymax_LT=61
    xmin_LT=0  #
    xmax_LT=1
    width=900
    height=400
    
    # Initialization
    with dpg.group(label="Compare Telemetry View",tag="Telemetry_compare_view",show=False,parent="Primary window"):
      with dpg.group(label="map_buttons",tag="map_buttons",horizontal=True):
        dpg.add_combo(items=list(self._maps.keys()),tag="map",width=150,default_value=None,callback=self.Set_Corners)
        #dpg.add_input_double(label="Offset_Turns",tag="slide_corner",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=self.Set_Corners)
      with dpg.group(label="offset_drivers",tag="offset_drivers",horizontal=True):
        for i in range(self._n_drivers):
          dpg.add_input_double(label="Offset_Driver"+str(i),tag="OFF_DRV-"+str(i),min_value=-20,max_value=20,default_value=0,width=150,min_clamped=True,max_clamped=True,step=1,callback=self.Add_Driver_to_LaptimePlot)
      with dpg.group(label="offset_drivers_tel",tag="offset_drivers_tel",horizontal=True):
        for i in range(self._n_drivers):
          dpg.add_input_double(label="Offset_Turns"+str(i),tag="slide_corner-"+str(i),min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.05,callback=self.Display_Lap_2)
      #    #dpg.add_input_double(label="Offset_Driver2",tag="OFF_DRV2",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=self.Set_Offset_Space)            
      #with dpg.group(label="speeds_text",tag="speeds_text",horizontal=True):  
      #  for i in range(self._n_drivers):
      #    dpg.add_text(default_value="Driver "+str(i)+":",tag="DRV-"+str(i)+"-DRV_TEXT")
      #    #dpg.add_text(default_value="Driver 1 speed",tag="DRV-1-SPEED_TEXT")
      with dpg.group(label="clear_buttons",tag="clear_buttons",horizontal=True):
        dpg.add_button(label="Clear Annotations",tag="clear_ann",callback=self._clear_annotations)
        dpg.add_button(label="Clear Plot",tag="clear_plot",callback=self._clear_plot)
        dpg.add_checkbox(label="Adjust Speed Limits",tag="Adjust Speed Limits",callback=self._set_yspeed_limits)
        
      for i in range(self._n_drivers):
        with dpg.group(label="drivers_buttons"+str(i),tag="drivers_buttons"+str(i),horizontal=True):
          dpg.add_combo(items=list(self._drivers_list),tag="DRV-"+str(i),width=150,default_value=None,callback=self.Select_Driver_Compare_2)
          dpg.add_combo(items=[],tag="LAP-"+str(i),width=150,default_value=None,callback=self.Display_Lap_2)
      with dpg.group(label="compare_buttons",tag="compare_buttons",horizontal=True):
        for i in range(self._n_drivers):
          dpg.add_combo(items=list(self._drivers_list),tag="DRV-"+str(i)+"-LapTimes",width=150,default_value=None,callback=self.Add_Driver_to_LaptimePlot)
          #dpg.add_combo(items=list(self._drivers_list),tag="DRV-2-LapTimes",width=150,default_value=None)
      
      with dpg.plot(label="CompareSpeed",tag="CompareSpeed",width=width,height=height,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_SPEED_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Speed [km/h]", tag="y_axis_SPEED_Compare")
        dpg.set_axis_limits("y_axis_SPEED_Compare", -2, 380)
        dpg.set_axis_limits("x_axis_SPEED_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_SPEED_Compare",self._xTurns)
        dpg.add_drag_line(label="speed_compare_line",tag="speed_compare_line", color=[255, 0, 0, 255],thickness=0.25, default_value=0.5)
      dpg.add_vline_series(x=[],tag="speed_sectors",parent="y_axis_SPEED_Compare")
      dpg.bind_item_theme(item="speed_sectors",theme="line_weight")
        
        
      with dpg.plot(label="CompareThrottle",width=width,height=height/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_THROTTLE_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Throttle [%]", tag="y_axis_THROTTLE_Compare")
        dpg.set_axis_limits("y_axis_THROTTLE_Compare", -2, 101)
        dpg.set_axis_limits("x_axis_THROTTLE_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_THROTTLE_Compare",self._xTurns)

      with dpg.plot(label="CompareBrake",width=width,height=height/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_BRAKE_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Brake [on/off]", tag="y_axis_BRAKE_Compare")
        dpg.set_axis_limits("y_axis_BRAKE_Compare", -2, 101)
        dpg.set_axis_limits("x_axis_BRAKE_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_BRAKE_Compare",self._xTurns)

      with dpg.plot(label="CompareDeltaTime",width=width,height=height/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_DELTA_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Delta [s]", tag="y_axis_DELTA_Compare")
        dpg.set_axis_limits("y_axis_DELTA_Compare", -3, 3)
        dpg.set_axis_limits("x_axis_DELTA_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_DELTA_Compare",self._xTurns)

      with dpg.plot(label="CompareRPM",width=width,height=height/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_RPM_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="RPM", tag="y_axis_RPM_Compare")
        dpg.set_axis_limits("y_axis_RPM_Compare", -2, 19000)
        dpg.set_axis_limits("x_axis_RPM_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_RPM_Compare",self._xTurns)
      
      with dpg.plot(label="CompareGear",width=width,height=height/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_GEAR_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="Gear", tag="y_axis_GEAR_Compare")
        dpg.set_axis_limits("y_axis_GEAR_Compare", -0.2, 9)
        dpg.set_axis_limits("x_axis_GEAR_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_GEAR_Compare",self._xTurns)
      
      with dpg.plot(label="CompareDrs",width=width,height=height/3.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_DRS_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="DRS [on/off]", tag="y_axis_DRS_Compare")
        dpg.set_axis_limits("y_axis_DRS_Compare", -0.2, 1.2)
        dpg.set_axis_limits("x_axis_DRS_Compare", ymin=minx1 ,ymax=maxx1)
        dpg.set_axis_ticks("x_axis_DRS_Compare",self._xTurns)

      with dpg.plot(label="CompareLaps",width=width,height=height/3.*4.,no_title=True,anti_aliased=True):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="LapNumber",tag="x_axis_LAPS_Compare")
        dpg.add_plot_axis(dpg.mvYAxis, label="LapTime [s]", tag="y_axis_LAPS_Compare")
        #dpg.set_axis_limits("y_axis_LAPS_Compare", ymin_LT, ymax_LT)
        #dpg.set_axis_limits("x_axis_LAPS_Compare", xmin_LT, xmax_LT)
      
      with dpg.plot(label="ZoomCompare",width=300,height=300,pos=(width,height/1.5),no_title=True,anti_aliased=True):
        dpg.add_plot_axis(dpg.mvXAxis,tag="x_axis_ZOOM",no_tick_marks=True,no_tick_labels=True)
        dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis_ZOOM",no_tick_marks=True,no_tick_labels=True)
        dpg.add_drag_line(label="speed_compare_line2",tag="speed_compare_line2", color=[255, 0, 0, 255],thickness=0.25, default_value=0.5)
      
      self._drivers_list_fictitious=self._drivers_list.copy()
      self._drivers_list_fictitious.append("100")
      for drv in self._drivers_list_fictitious:
        dpg.add_line_series(x=[0],y=[0],label=drv+"s_c",parent="y_axis_SPEED_Compare",tag=drv+"s_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"t_c",parent="y_axis_THROTTLE_Compare",tag=drv+"t_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"b_c",parent="y_axis_BRAKE_Compare",tag=drv+"b_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"r_c",parent="y_axis_RPM_Compare",tag=drv+"r_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"g_c",parent="y_axis_GEAR_Compare",tag=drv+"g_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"d_c",parent="y_axis_DRS_Compare",tag=drv+"d_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"z_c",parent="y_axis_ZOOM",tag=drv+"z_c")
        dpg.add_line_series(x=[0],y=[0],label=drv+"cmpl",parent="y_axis_DELTA_Compare",tag=drv+"cmpl")
        
        if drv=="100":
          dpg.bind_item_theme(drv+"s_c","white")
          dpg.bind_item_theme(drv+"t_c","white")
          dpg.bind_item_theme(drv+"z_c","white")
          dpg.bind_item_theme(drv+"b_c","white")
          dpg.bind_item_theme(drv+"r_c","white")
          dpg.bind_item_theme(drv+"g_c","white")
          dpg.bind_item_theme(drv+"d_c","white")
          #dpg.bind_item_theme(drv+"l_c",drv+"plot_marker")
          #dpg.bind_item_theme(drv+"l_c_line",drv+"_color")
          dpg.bind_item_theme(drv+"cmpl","white")
        else:
          dpg.add_scatter_series(x=[0],y=[0],label=drv+"l_c",parent="y_axis_LAPS_Compare",tag=drv+"l_c")
          dpg.add_line_series(x=[0],y=[0],label=drv+"l_c_line",parent="y_axis_LAPS_Compare",tag=drv+"l_c_line")
          
          dpg.bind_item_theme(drv+"s_c",drv+"_color")
          dpg.bind_item_theme(drv+"t_c",drv+"_color")
          dpg.bind_item_theme(drv+"z_c",drv+"_color")
          dpg.bind_item_theme(drv+"b_c",drv+"_color")
          dpg.bind_item_theme(drv+"r_c",drv+"_color")
          dpg.bind_item_theme(drv+"g_c",drv+"_color")
          dpg.bind_item_theme(drv+"d_c",drv+"_color")
          dpg.bind_item_theme(drv+"l_c",drv+"plot_marker")
          dpg.bind_item_theme(drv+"l_c_line",drv+"_color")
          dpg.bind_item_theme(drv+"cmpl",drv+"_color")

          dpg.set_item_label(item=drv+"s_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"t_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"z_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"b_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"r_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"d_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"g_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"l_c", label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"cmpl",label=self._DRIVERS_INFO[drv]["abbreviation"])
          dpg.set_item_label(item=drv+"l_c_line", label="")
      
      self._annotations_speed={}
      ann_index=0
    while True:
      # This adds annotations when the speed plot is right clicked.
      # If you right click again close to the annotation, it deletes it.
      # In the future this will be automatized to display maxima/minima without 
      # the need of clicking
      try:
        if dpg.is_item_hovered(item="CompareSpeed"):
          if not dpg.is_item_shown("speed_compare_line"):
            dpg.show_item("speed_compare_line")
            dpg.show_item("speed_compare_line2")
          ann_deleted=False
          mouse_pos=dpg.get_plot_mouse_pos()
          mouse_pos_text=dpg.get_mouse_pos()
          dpg.set_axis_limits("x_axis_ZOOM",ymin=mouse_pos[0]-0.1,ymax=mouse_pos[0]+0.1)
          dpg.set_axis_limits("y_axis_ZOOM",ymin=mouse_pos[1]-50,ymax=mouse_pos[1]+50)
          dpg.set_value(item="speed_compare_line",value=mouse_pos[0])
          dpg.set_value(item="speed_compare_line2",value=mouse_pos[0])
          if dpg.is_item_clicked("CompareSpeed"):
            print("Clicked", mouse_pos, " ",mouse_pos_text)
            key_to_pop=None
            for x_ann,ann_info in self._annotations_speed.items():
              #print(mouse_pos,dpg.get_item_info(item=ann_info["ann_name"]))
              if mouse_pos[0]>=ann_info["xLimits"][0] and mouse_pos[0]<=ann_info["xLimits"][1]:
                for i in range(self._n_drivers):
                  if dpg.does_item_exist(item=ann_info["ann_name"]+str(i)):
                    dpg.delete_item(item=ann_info["ann_name"]+str(i))
                key_to_pop=x_ann
                ann_deleted=True
                break
            self._annotations_speed.pop(key_to_pop,"")
            if not ann_deleted:
              self._annotations_speed[mouse_pos_text[0]]={"ann_name":"ann_"+str(ann_index),
                                                          "Text": [],
                                                          "xLimits": [mouse_pos[0]-0.01,mouse_pos[0]+0.01],
                                                          }
              ann_index+=1
              max_speed=-10
              for n_drv,drv_info in self._saved_drivers.items(): 
                sp=self.get_y_from_x_plot(x_point=mouse_pos[0],x_array=drv_info["Space"],y_array=drv_info["Speed"])
                if sp>max_speed:
                  max_speed=sp
                  DRV=drv_info["Driver"]
              if max_speed!=-10:
                self._annotations_speed[mouse_pos_text[0]]["Text"].append([DRV,(self._DRIVERS_INFO[DRV]["abbreviation"]+": "+str(int(max_speed)).rjust(3," ")+"\n")])
              for n_drv,drv_info in self._saved_drivers.items(): #DRV-i, keys: Driver,Space,Speed
                if drv_info["Driver"]!=DRV:
                  sp=self.get_y_from_x_plot(x_point=mouse_pos[0],x_array=drv_info["Space"],y_array=drv_info["Speed"])
                  speed_text=str(int(self.get_y_from_x_plot(x_point=mouse_pos[0],x_array=drv_info["Space"],y_array=drv_info["Speed"])-max_speed))
                  if speed_text[0]!="-":
                    speed_text="-"+speed_text
                  self._annotations_speed[mouse_pos_text[0]]["Text"].append([drv_info["Driver"],(self._DRIVERS_INFO[drv_info["Driver"]]["abbreviation"]+": "+speed_text.rjust(3," ")+"\n")])
              for index,txt in enumerate(self._annotations_speed[mouse_pos_text[0]]["Text"]):
                drv=txt[0]
                text=txt[1]
                #dpg.add_text(default_value=text,tag=self._annotations_speed[mouse_pos_text[0]]["ann_name"]+str(index),color=self._DRIVERS_INFO[drv]["color"],parent="Telemetry_compare_view",pos=(mouse_pos_text[0],mouse_pos_text[1]+dpg.get_text_size(text=text)[1]*index),show=True)
                dpg.add_plot_annotation(label=text,tag=self._annotations_speed[mouse_pos_text[0]]["ann_name"]+str(index),default_value=(mouse_pos[0]-0.01,mouse_pos[1]+dpg.get_text_size(text=text)[1]*(len(self._annotations_speed[mouse_pos_text[0]]["Text"])-index)),color=self._DRIVERS_INFO[drv]["color"],parent="CompareSpeed")
        else:
          if dpg.is_item_shown("speed_compare_line"):
            dpg.hide_item(item="speed_compare_line")
            dpg.hide_item(item="speed_compare_line2")
            
      except Exception as err:
        print("Error... Fix it. Probably a driver not found in some dictionary.")
        _config.LOGGER.exception(err)
        _config.LOGGER_FILE.write("\n")
        _config.LOGGER_FILE.flush()
        
      time.sleep(1./60.)


  # Fix stints and add annotations where i click with mouse. So save [space,speeds] for all drivers.
  def _clear_plot(self):
    for driver in self._drivers_list_fictitious:
      dpg.set_value(item=driver+"s_c", value=[[0],[0]])
      dpg.set_value(item=driver+"z_c", value=[[0],[0]])
      dpg.set_value(item=driver+"t_c", value=[[0],[0]])
      dpg.set_value(item=driver+"b_c", value=[[0],[0]])
      dpg.set_value(item=driver+"d_c", value=[[0],[0]])
      dpg.set_value(item=driver+"g_c", value=[[0],[0]])
      dpg.set_value(item=driver+"r_c", value=[[0],[0]])
      dpg.hide_item(driver+"cmpl")
    for i in range(self._n_drivers):
      dpg.set_value(item="DRV-"+str(i),value="None")
      dpg.set_value(item="LAP-"+str(i),value="None")
    self._saved_drivers={}
      
  def _set_yspeed_limits(self):
    if dpg.get_value(item="Adjust Speed Limits"):
      dpg.set_axis_limits("y_axis_SPEED_Compare", 50, 350)
    else:
      dpg.set_axis_limits("y_axis_SPEED_Compare", -2, 380)

  def _clear_annotations(self):
    for key,value in self._annotations_speed.items():
      for i in range(self._n_drivers):
        if dpg.does_item_exist(item=value["ann_name"]+str(i)):
          dpg.delete_item(item=value["ann_name"]+str(i))
    self._annotations_speed={}

  def Add_Driver_to_LaptimePlot(self):
    """ 
      Add long runs to the plot at the bottom with some restrictions based on the value of the plot.
    """
    for i in range(self._n_drivers):
      if dpg.get_value("DRV-"+str(i)+"-LapTimes")!="None":
        lap_to_pop=[]        
        LAPS=self._database.get_dictionary(feed="TimingDataF1").copy()
        driver=dpg.get_value("DRV-"+str(i)+"-LapTimes")
        offset=dpg.get_value("OFF_DRV-"+str(i))
        LAPNUMBERS=list(LAPS[driver].keys())
        LAPTIMES=[lap["ValueInt_sec"] if (lap["ValueInt_sec"]<110 and lap["ValueInt_sec"]>10 and lap["DateTime"]<self._last_message_displayed_UTC) else lap_to_pop.append(nlap) for nlap,lap in LAPS[driver].items()]
        for nlap in lap_to_pop:
          LAPNUMBERS.remove(nlap)
          LAPTIMES.remove(None)
        LAPNUMBERS_OFFSETTED=[nlap-offset for nlap in LAPNUMBERS]
        #print(self._DRV2_LTs," ",LAPNUMBERS2, LAPTIMES2)
        dpg.set_value(item=driver+"l_c", value=[LAPNUMBERS_OFFSETTED,LAPTIMES])
        dpg.set_value(item=driver+"l_c_line", value=[LAPNUMBERS_OFFSETTED,LAPTIMES])
        list_of_drivers=[dpg.get_value("DRV-"+str(n_driver)+"-LapTimes") for n_driver in range(self._n_drivers)]
        for driver in self._drivers_list:
          if driver in list_of_drivers:
            dpg.show_item(driver+"l_c_line")
            dpg.show_item(driver+"l_c")
          else:
            dpg.hide_item(driver+"l_c_line")
            dpg.hide_item(driver+"l_c")
        #if int(max(LAPTIMES2))+5>ymax_LT:
        #  ymax_LT=int(max(LAPTIMES2))+5
        #if int(max(LAPNUMBERS2))+1>xmax_LT:
        #  xmax_LT=int(max(LAPNUMBERS2))+1

  def Select_Driver_Compare_2(self,sender):
    """ 
      Callback. Handler for selecting the laptimes to be displayed when a driver is selected from the dropdown button.
    """
    laps=self._database.get_dictionary(feed="TimingDataF1").copy()  # Driver -> Nlap ->  {DateTime,ValueString,ValueInt_sec}
    n_drv=sender.split("-")[-1]
    ITEM="LAP-"+n_drv
    drv_already_present=False
    #dpg.set_value(item="DRV-"+n_drv+"-DRV_TEXT",value=self._DRIVERS_INFO[dpg.get_value(sender)]["abbreviation"]+":  ")
    if dpg.get_value(sender) in laps.keys():
      driver=dpg.get_value(sender)
      laps_to_show=[str(nlap)+" "+lap_dict["ValueString"]  for nlap,lap_dict in laps[driver].items() if lap_dict["DateTime"]<self._last_message_displayed_UTC]
      print(laps[driver][list(laps[driver].keys())[0]]["DateTime"],self._last_message_displayed_UTC)
      dpg.configure_item(item=ITEM,items=laps_to_show,default_value=None)
      for key,value in self._saved_drivers.items():
        if dpg.get_value(sender)==value["Driver"]:
          drv_already_present=True
      if not drv_already_present:
        self._saved_drivers[sender]={}
        self._saved_drivers[sender]["Driver"]=driver
        self._saved_drivers[sender]["Driverlabel"]=driver
        dpg.set_value(item=driver+"s_c", value=[[0],[0]])
        dpg.set_value(item=driver+"z_c", value=[[0],[0]])
        dpg.set_value(item=driver+"t_c", value=[[0],[0]])
        dpg.set_value(item=driver+"b_c", value=[[0],[0]])
        dpg.set_value(item=driver+"d_c", value=[[0],[0]])
        dpg.set_value(item=driver+"g_c", value=[[0],[0]])
        dpg.set_value(item=driver+"r_c", value=[[0],[0]])
             
        dpg.hide_item(driver+"s_c")
        dpg.hide_item(driver+"z_c")
        dpg.hide_item(driver+"t_c")
        dpg.hide_item(driver+"b_c")
        dpg.hide_item(driver+"d_c")
        dpg.hide_item(driver+"r_c")
        dpg.hide_item(driver+"g_c")
        dpg.hide_item(driver+"cmpl")
      else:
        self._saved_drivers[sender]={}
        self._saved_drivers[sender]["Driver"]=driver
        self._saved_drivers[sender]["Driverlabel"]="100"
        dpg.set_value(item="100s_c", value=[[0],[0]])
        dpg.set_value(item="100z_c", value=[[0],[0]])
        dpg.set_value(item="100t_c", value=[[0],[0]])
        dpg.set_value(item="100b_c", value=[[0],[0]])
        dpg.set_value(item="100d_c", value=[[0],[0]])
        dpg.set_value(item="100g_c", value=[[0],[0]])
        dpg.set_value(item="100r_c", value=[[0],[0]])
          
        dpg.hide_item("100s_c")
        dpg.hide_item("100z_c")
        dpg.hide_item("100t_c")
        dpg.hide_item("100b_c")
        dpg.hide_item("100d_c")
        dpg.hide_item("100r_c")
        dpg.hide_item("100g_c")
        dpg.hide_item("100cmpl")
      
  def Display_Lap_2(self,sender):
    """ 
      CallBack. This adds the telemetry to the plot when a lap is selected. Adds also the delta.
    """
    laps=self._database.get_dictionary(feed="TimingDataF1").copy()
    n_drv=sender.split("-")[-1]
    driver_tag=dpg.get_value("DRV-"+n_drv)
    driver=driver_tag.split("-")[0]
    offset=dpg.get_value("slide_corner-"+str(n_drv))
    #self._offset[n_drv]=dpg.get_value("OFF_DRV-"+n_drv)
    driver_label=self._saved_drivers["DRV-"+n_drv]["Driverlabel"]
    NLAP=int(dpg.get_value("LAP-"+n_drv).split(" ")[0])
    LAP=laps[driver][NLAP] # DateTime , ValueString , ValueInt_sec are the keys
    LapTime_s=LAP["ValueInt_sec"]
    print(driver," ",NLAP," ",LAP["DateTime"]," ",LapTime_s)
    SLICE=self._database.get_slice_between_times(start_time=LAP["DateTime"]-datetime.timedelta(seconds=LapTime_s)+datetime.timedelta(seconds=offset),end_time=LAP["DateTime"]+datetime.timedelta(seconds=offset))
    SLICE=slice(SLICE.start-1,SLICE.stop+1)
    TEL=self._database.get_dictionary(feed="CarData.z")[driver].copy()
    # Save all before interpolating to add first and last DT
    times_before_interp     = np.array(TEL["TimeStamp"][SLICE])
    speeds_before_interp    = np.array(TEL["Speed"][SLICE])
    Throttles_before_interp = np.array(TEL["Throttle"][SLICE])
    Brakes_before_interp    = np.array(TEL["Brake"][SLICE])
    Rpm_before_interp       = np.array(TEL["RPM"][SLICE])
    Gear_before_interp      = np.array(TEL["Gear"][SLICE])
    Drs_before_interp       = np.array(TEL["DRS"][SLICE])
    # Add first and last DT to the lap to make it lasts the exact time.
    times                   = np.copy(times_before_interp)
    times=np.insert(times,1,(LAP["DateTime"]-datetime.timedelta(seconds=LapTime_s)+datetime.timedelta(seconds=offset)).timestamp()-self._BaseTimestamp)
    times=np.insert(times,len(times)-1,(LAP["DateTime"]+datetime.timedelta(seconds=offset)).timestamp()-self._BaseTimestamp)
    
    # Interpolate all telemetry to the news times array
    #print("\n",len(times_before_interp),len(speeds_before_interp),len(times))
    #print("times: ",times,"\n")
    #print("times (bi): ",times_before_interp)
    #print("speeds (bi): ",speeds_before_interp)
    speeds    = scipy.interpolate.Akima1DInterpolator(times_before_interp,speeds_before_interp)(times)
    Throttles = scipy.interpolate.Akima1DInterpolator(times_before_interp,Throttles_before_interp)(times) 
    Brakes    = scipy.interpolate.Akima1DInterpolator(times_before_interp,Brakes_before_interp)(times)
    Rpm       = scipy.interpolate.Akima1DInterpolator(times_before_interp,Rpm_before_interp)(times)
    Gear      = scipy.interpolate.Akima1DInterpolator(times_before_interp,Gear_before_interp)(times)
    Drs       = scipy.interpolate.Akima1DInterpolator(times_before_interp,Drs_before_interp)(times)
    
    #print("\n Telemetry starting and ending DT: ",times[0]," ",times[-1])
    #print("\n Effective starting and ending DT: ",LAP["DateTime"]-datetime.timedelta(seconds=LapTime_s)," ",LAP["DateTime"])
    Times=[TS-times[1] for TS in times]
    #print(Times,"\n")
    Times     = Times[1:-1]
    speeds    = speeds[1:-1]   
    Throttles = Throttles[1:-1] 
    Brakes    = Brakes[1:-1]   
    Rpm       = Rpm[1:-1]      
    Gear      = Gear[1:-1]     
    Drs       = Drs[1:-1]   
    print(driver," - LapTime: ",LapTime_s," - Diff In Times: ",Times[-1]-Times[0],"\n")
    #print(speeds,"\n")   

    space = scipy.integrate.cumulative_trapezoid(speeds/3.6,Times,initial=0)  
    #print("\n",driver,space,"\n")
    # print(space,"\n")
    Total_space = space[-1]
    self._saved_drivers["DRV-"+n_drv]["Space"]=space/Total_space
    self._saved_drivers["DRV-"+n_drv]["Speed"]=speeds
    self._saved_drivers["DRV-"+n_drv]["Times"]=Times
    self._saved_drivers["DRV-"+n_drv]["LapTime"]=LapTime_s
    
    dpg.set_value(item=driver_label+"s_c", value=[space/Total_space,speeds])
    dpg.set_value(item=driver_label+"z_c", value=[space/Total_space,speeds])
    dpg.set_value(item=driver_label+"t_c", value=[space/Total_space,Throttles])
    dpg.set_value(item=driver_label+"b_c", value=[space/Total_space,Brakes])
    dpg.set_value(item=driver_label+"d_c", value=[space/Total_space,Drs])
    dpg.set_value(item=driver_label+"g_c", value=[space/Total_space,Gear])
    dpg.set_value(item=driver_label+"r_c", value=[space/Total_space,Rpm])
    #print(self._xTurns)
    dpg.set_axis_ticks(axis="x_axis_SPEED_Compare",label_pairs=self._xTurns)
    dpg.set_axis_ticks(axis="x_axis_THROTTLE_Compare",label_pairs=self._xTurns)
    dpg.set_axis_ticks(axis="x_axis_BRAKE_Compare",label_pairs=self._xTurns)
    dpg.set_axis_ticks(axis="x_axis_RPM_Compare",label_pairs=self._xTurns)
    dpg.set_axis_ticks(axis="x_axis_GEAR_Compare",label_pairs=self._xTurns)
    dpg.set_axis_ticks(axis="x_axis_DRS_Compare",label_pairs=self._xTurns)
    
    dpg.set_axis_limits("x_axis_SPEED_Compare",0,1)
    dpg.set_axis_limits("x_axis_THROTTLE_Compare",0,1)
    dpg.set_axis_limits("x_axis_BRAKE_Compare",0,1)
    dpg.set_axis_limits("x_axis_GEAR_Compare",0,1)
    dpg.set_axis_limits("x_axis_DRS_Compare",0,1)
    dpg.set_axis_limits("x_axis_RPM_Compare",0,1)
    
    dpg.set_item_label(item=driver_label+"s_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"t_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"z_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"b_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"r_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"d_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"g_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"l_c", label=self._DRIVERS_INFO[driver]["abbreviation"])
    dpg.set_item_label(item=driver_label+"cmpl",label=self._DRIVERS_INFO[driver]["abbreviation"])
    #dpg.set_axis_limits("x_axis_LAPS_Compare",xmin_LT,xmax_LT)
    #dpg.set_axis_limits("y_axis_LAPS_Compare",ymin_LT,ymax_LT)
    max_LT=1e6
    for driver,info_driver_laps in self._saved_drivers.items(): 
      if "LapTime" in info_driver_laps.keys():
        if info_driver_laps["LapTime"]<max_LT:
          max_LT=info_driver_laps["LapTime"]
          max_driver=info_driver_laps["Driver"]
          max_driver_id=driver
          max_space=info_driver_laps["Space"]
          max_speed=info_driver_laps["Speed"]
          max_times=info_driver_laps["Times"]
    minx,maxx=1e6,-1e6
    for driver,info_driver_laps in self._saved_drivers.items():
      if "Space" in info_driver_laps.keys():
        sp1=max_space
        sp2=info_driver_laps["Space"]
        #print("\n",driver ,":",sp2)
        #print(sp1)
        Space_x=np.linspace(0,1,500)
        t1=scipy.interpolate.Akima1DInterpolator(sp1,max_times)(Space_x)
        t2=scipy.interpolate.Akima1DInterpolator(sp2,info_driver_laps["Times"])(Space_x)
        Delta     =    t2  -   t1
        dpg.set_value(item=info_driver_laps["Driverlabel"]+"cmpl", value=[Space_x,Delta])
        dpg.set_axis_ticks(axis="x_axis_DELTA_Compare",label_pairs=self._xTurns)
        if min(Delta)<minx:
          minx=min(Delta)
        if max(Delta)>maxx:
          maxx=max(Delta)
    
    dpg.set_axis_limits("y_axis_DELTA_Compare", minx-0.05,maxx+0.05)  
    list_of_drivers=[info_drv["Driverlabel"] for driverid,info_drv in self._saved_drivers.items()]
      
    for driver in self._drivers_list_fictitious:
      if driver in list_of_drivers:
        dpg.show_item(driver+"s_c")
        dpg.show_item(driver+"z_c")
        dpg.show_item(driver+"t_c")
        dpg.show_item(driver+"b_c")
        dpg.show_item(driver+"r_c")
        dpg.show_item(driver+"g_c")
        dpg.show_item(driver+"d_c")
        dpg.show_item(driver+"cmpl")
      else:
        dpg.hide_item(driver+"s_c")
        dpg.hide_item(driver+"z_c")
        dpg.hide_item(driver+"t_c")
        dpg.hide_item(driver+"b_c")
        dpg.hide_item(driver+"d_c")
        dpg.hide_item(driver+"r_c")
        dpg.hide_item(driver+"g_c")
        dpg.hide_item(driver+"cmpl")
    
  def get_y_from_x_plot(self,x_point: float,x_array: np.array,y_array: np.array):
    """ 
      Helper function to retrieve the y from the point just before x_point
    """
    y=y_array[0]
    for index,x in enumerate(x_array):
      if x<=x_point:
        y=y_array[index]
      else:
        return y

###################################################################################################################  
  def custom_sort(self,array):
      item=array[1]
      #print(item)
      if item == "-":
        #print("-")
        return float('inf')  # "-" will be considered larger than any number  
      elif re.match(r'^\d+$', item):
        #print("int")
        return int(item)
      elif re.match(r'^\d{1,2}:\d{2}\.\d{3}$', item):
        #print("mm:ss.sss")
        value_splitted=item.split(":")
        return int(value_splitted[0])*60+float(value_splitted[1])
      elif re.match(r'^\d+(\.\d+)?$', item):
        #print("ss.sss")
        return float(item)
      else: 
        #print("bho")
        return float('inf')
  
  def sort_callback(self,sender, sort_specs):
    """ 
      Callback. To sort the timing view tab. 
    """
    # sort_specs scenarios:
    #   1. no sorting -> sort_specs == None
    #   2. single sorting -> sort_specs == [[column_id, direction]]
    #   3. multi sorting -> sort_specs == [[column_id, direction], [column_id, direction], ...]
    #
    # notes:
    #   1. direction is ascending if == 1
    #   2. direction is ascending if == -1

    # no sorting case
    if sort_specs is None: return

    rows = dpg.get_item_children(sender, 1)
    column_name=dpg.get_item_alias(sort_specs[0][0])
    # create a list that can be sorted based on first cell
    # value, keeping track of row and value used to sort
    sortable_list = []
    for row in rows:
      for cell in dpg.get_item_children(row, 1):
        if column_name in dpg.get_item_alias(cell):
          sortable_list.append([row, dpg.get_value(cell)])
          break

    if column_name in ["I1","I2","FL","ST"]:
      sortable_list.sort(key=self.custom_sort,reverse=True)
    else:
      sortable_list.sort(key=self.custom_sort)
    
    # create list of just sorted row ids
    new_order = []
    for pair in sortable_list:
      new_order.append(pair[0])

    dpg.reorder_items(sender, 1, new_order)

  def AddDriverToTimingView(self,driver):
    with dpg.table_row(parent="TableTimingView"):
      for nr_column,column_name in enumerate(self._table_column): 
        if column_name=="Full Name":
          dpg.add_text(default_value=self._DRIVERS_INFO[driver]["full_name"],tag=driver+column_name)
        elif "segments" in column_name:
          dpg.add_group(label=driver+column_name+"musec",tag=driver+column_name+"musec",horizontal=True,width=10)
            #if "segments" in self._maps[self._event_name].keys():
            #  nsegments=self._maps[self._event_name]["segments"][column_name[-1]]
            #else:
            #  nsegments=10
            #for i in range(nsegments):
            #  dpg.add_button(label="",tag=driver+column_name+"musec"+str(i))
        else:
          #print(driver+column_name)
          dpg.add_text(default_value="-",tag=driver+column_name)

  def Timing_View(self):    
    """ 
      Set up of the table in timing view tab.
    """
    time.sleep(0.5)
    with dpg.group(label="Timing View",tag="Timing_view",show=False,parent="Primary window"):
      with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit, resizable=True, no_host_extendX=True,tag="TableTimingView",parent="Timing_view",
                    borders_innerV=True, borders_outerV=True, borders_outerH=True,sortable=True, callback=self.sort_callback):

        self._table_column=["Position","Full Name","BestLapTime","LastLapTime","gap","int","Bestsector1","sector1","segments1","Bestsector2","sector2","segments2","Bestsector3","sector3","segments3","I1","I2","FL","ST"]
        
        for column_name in self._table_column:
          dpg.add_table_column(label=column_name,tag=column_name)
        
        #for driver in self._drivers_list:
        #  self.AddDriverToTimingView(driver)
          
      
###################################################################################################      
  
  def showTab(self,sender):
    """ 
      CallBack. Needed to change what tab is displayed when clicked.
    """
    print(sender," show set to True")
    dpg.configure_item(self._tabs[sender],show=True)
    for tab in self._tabs.keys():
      if tab!=sender:
        print(self._tabs[tab]," show set to False")
        dpg.configure_item(self._tabs[tab],show=False)

  def initialize_themes_and_fonts(self):
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
    
    # Microsectors colors
    with dpg.theme(tag="green"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, [0,255,0,255] , category=dpg.mvThemeCat_Core)
    with dpg.theme(tag="purple"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, [85,26,139,255] , category=dpg.mvThemeCat_Core)
    with dpg.theme(tag="yellow"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, [234,240,23,255] , category=dpg.mvThemeCat_Core)
    with dpg.theme(tag="transparent"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, [128,128,128,100] , category=dpg.mvThemeCat_Core)
    with dpg.theme(tag="blue"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, [0,0,255,255] , category=dpg.mvThemeCat_Core)
    with dpg.theme(tag="red"):
      with dpg.theme_component():
        dpg.add_theme_color(dpg.mvThemeCol_Button, [255,0,0,255] , category=dpg.mvThemeCat_Core)
    
    with dpg.theme(tag="line_weight"):
      with dpg.theme_component(dpg.mvVLineSeries):
       dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 4, category=dpg.mvThemeCat_Plots)
    
    with dpg.font_registry():
      # first argument ids the path to the .ttf or .otf file
      dpg.add_font("Fonts/Roboto-Bold.ttf", 40,tag="drawNodeFont")
    
    with dpg.theme(tag="Global_Theme"):
      with dpg.theme_component(dpg.mvAll):
        # Main
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,       0,0,     category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,        4,2,     category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_CellPadding,         0,0,     category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,         1,1,     category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing,    1,1,     category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing,       21,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize,       6,  category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize,         7,       category=dpg.mvThemeCat_Core)
                                                                                
        # Borders                                                           
        dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize,    1,       category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize,     1,       category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_PopupBorderSize,     1,       category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize,     0,       category=dpg.mvThemeCat_Core)
                                                                           
        # Rounding                                                     
        dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,      12,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,        6,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,       12,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_PopupRounding,        0,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding,    6,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,        12,      category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_TabRounding,          6,      category=dpg.mvThemeCat_Core)
        
        # Alignment
        dpg.add_theme_style(dpg.mvStyleVar_WindowTitleAlign,     0,0,    category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign,    0.5,0.5,  category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_SelectableTextAlign,  0,0,    category=dpg.mvThemeCat_Core)
        
        # Plot styling
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize,   0,      category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MinorAlpha,      0.15,    category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MajorTickLen,   10,10,    category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MinorTickLen,    3,3,     category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MajorTickSize,   1,1,     category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MinorTickSize,   1,1,     category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MajorGridSize,   1,1,     category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MinorGridSize,   1,1,     category=dpg.mvThemeCat_Plots)
        
        # Plot padding
        dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding,        5,4,   category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_LabelPadding,       0,0,   category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_LegendPadding,     10,10,  category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_LegendInnerPadding, 5,5,   category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_LegendSpacing,      5,0,   category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MousePosPadding,   10,10,  category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_AnnotationPadding,  0,0,   category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_FitPadding,         0,0,   category=dpg.mvThemeCat_Plots)
  
    dpg.bind_theme("Global_Theme")
    
  def initialize_windows_and_tabs(self):
    if not self._LIVE_SIM:
      self._IO_thread.start()
    # No bring focus is a temporary workaround. It will be fixed in the future with the windows restyle                                                                                                  
    self._windows_manager.append("Primary window")
    with dpg.window(tag="Primary window",width=self._VIEWPORT_WIDTH,height=self._VIEWPORT_HEIGHT,pos=[0,0],no_bring_to_front_on_focus=True):
      with dpg.menu_bar():
        with dpg.tab_bar():
          for tab in self._tabs.keys():
            dpg.add_tab_button(label=tab,tag=tab,callback=self.showTab)
          #dpg.add_tab_button(label="Telemetry")
          #dpg.add_tab_button(label="Compare Telemetry")
      if self._LIVE_SIM:
        if _config.FORCE_UPDATE:
          self._parser.update_urls()
          self._parser._urls=json.load(open(_config.paths.JSONS_PATH / self._parser._filename_urls,"r"))
        with dpg.group(label="Race selector",tag="Race_Selector",show=True):
          dpg.add_combo(items=list(self._parser._sessions_dict.keys()),tag="year",default_value="None",callback=self.choose_session)
  
  def initialize_textures(self):
    self.Tyres_Texture={}
    for tyre in os.listdir(_config.paths.TYRES_PATH):
      width, height, channels, data = dpg.load_image(str(_config.paths.TYRES_PATH / tyre))
      self.Tyres_Texture[tyre.split(".")[0].capitalize()]=data
      #dpg.add_static_texture(width=width, height=height, default_value=data, tag="tyre_"+tyre.split(".")[0])
  
  def run(self):
    """
      Everything starts from here. This is the only thing called in the main file.
    """
    
    self.initialize_windows_and_tabs()
    self.initialize_themes_and_fonts()
    self.initialize_textures()
    
    dpg.set_primary_window(window="Primary window",value=True)
    dpg.configure_item("Primary window", horizontal_scrollbar=True) # work-around for a known dpg bug!
    
    self.iterator.start()   
    self._compare_telemetry_thread.start()
    
    #dpg.show_style_editor()
    dpg.start_dearpygui()  
    dpg.destroy_context()
  