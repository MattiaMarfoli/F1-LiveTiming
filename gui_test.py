import dearpygui.dearpygui as dpg
import os,json
from config import paths

######################################################################################################

    
##################################### Timing in GUI ############################################
DELAY     = 0.    #seconds # TODO 
SLEEPTIME = 0.05  #seconds
FREQ_UPDATE_PLOT = 60 #Hz

####################################### Useful filenames #######################################
FILENAME_FEEDS="FEEDS.json"
FILENAME_URLS="SESSION_URLS.json"
FILENAME_COLORS="COLORS.json"
FILENAME_MAPS="MAPS2.json"
FILENAME_SEGMENTS="segmentsStatus.json"
FILENAME_DURATION="SESSION_DURATION.json"
FILENAME_LOGGER="log/myapp.log"


############################################## GUI ##############################################
  
  # Primary Window - Viewport
MAX_WIDTH,MAX_HEIGHT = 1920,1080 #subprocess.Popen('xrandr | grep "\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE).communicate()[0].decode("utf-8").replace("\n","").split("x")

  # Buttons 
BUTTONS_HEIGHT = 20
BUTTONS_WIDTH  = 50
BUTTONS_ROWS   = 4

  # Scrollbar
SCR_SIZE       = 6

  # Track Map
MAP_WIDTH  = 520
MAP_HEIGHT = 400

  # PNG HeadShots (width=height)
SIDE_OF_HEADSHOTS_PNG = 93

  # Top - Bottom bar
BOTTOM_BAR_HEIGHT = 0
TOP_BAR_HEIGHT = 25 # main.panel.height in gnome-shell.css

  # Telemetry Tab
TEL_OTHER_RATIO = 3./4.
TELEMETRY_PLOTS_WIDTH,TELEMETRY_PLOTS_HEIGHT = int((MAX_WIDTH-MAP_WIDTH-SCR_SIZE)/2.),345 #635,345
print(TELEMETRY_PLOTS_WIDTH)
FREQUENCY_TELEMETRY_UPDATE = 6 #Hz
LAPS_TO_DISPLAY            = 3 #n of laps to display
AVG_LAP_LENGTH             = 90 #s
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



#######################################################################################################


_MAX_WIDTH,_MAX_HEIGHT            = int(MAX_WIDTH),int(MAX_HEIGHT)

_BUTTONS_HEIGHT                        = BUTTONS_HEIGHT
_BUTTONS_WIDTH                         = BUTTONS_WIDTH
_BUTTONS_ROWS                          = BUTTONS_ROWS

_BOTTOM_BAR_HEIGHT                     = BOTTOM_BAR_HEIGHT
_TOP_BAR_HEIGHT                        = TOP_BAR_HEIGHT

_TEL_OTHER_RATIO                       = TEL_OTHER_RATIO
_FREQUENCY_TELEMETRY_UPDATE            = FREQUENCY_TELEMETRY_UPDATE
_LAPS_TO_DISPLAY                       = LAPS_TO_DISPLAY
_AVG_LAP_LENGTH                        = AVG_LAP_LENGTH
_WINDOW_DISPLAY_LENGTH                 = WINDOW_DISPLAY_LENGTH
_WINDOW_DISPLAY_PROPORTION_RIGHT       = WINDOW_DISPLAY_PROPORTION_RIGHT
_WINDOW_DISPLAY_PROPORTION_LEFT        = 1. - WINDOW_DISPLAY_PROPORTION_RIGHT





dpg.create_context()
_TERMINAL_SPACE=0
dpg.create_viewport(title='Custom Title', width=_MAX_WIDTH,height=_MAX_HEIGHT - _BOTTOM_BAR_HEIGHT - _TOP_BAR_HEIGHT - _TERMINAL_SPACE,decorated=False)

_VIEWPORT_WIDTH  = max(dpg.get_viewport_width(),1920)
_VIEWPORT_HEIGHT = max(dpg.get_viewport_height(),1080)

# Still initial configurations
dpg.show_viewport()
_TEL_PLOTS_HEIGHT = TELEMETRY_PLOTS_HEIGHT
_TEL_PLOTS_WIDTH  = TELEMETRY_PLOTS_WIDTH

pause_icon=str(paths.ASSETS_PATH / ("Icons/pause_icon.png"))
width, height, channels, data = dpg.load_image(pause_icon)
#_map_width,_map_height=width,height
with dpg.texture_registry():
  dpg.add_static_texture(width=width, height=height, default_value=data, tag="pause_icon")


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
      
      # Plot styling
      dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding,        5,4,   category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_LabelPadding,       2,0,   category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_LegendPadding,     10,10,  category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_LegendInnerPadding, 5,5,   category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_LegendSpacing,      5,0,   category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_MousePosPadding,   10,10,  category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_AnnotationPadding,  2,2,   category=dpg.mvThemeCat_Plots)
      dpg.add_theme_style(dpg.mvPlotStyleVar_FitPadding,         0,0,   category=dpg.mvThemeCat_Plots)

dpg.bind_theme("Global_Theme")

dpg.setup_dearpygui()


_DRIVERS_INFO                          = COLOR_DRIVERS
_watchlist_drivers                     = WATCHLIST_DRIVERS
_watchlist_teams                       = WATCHLIST_TEAMS
_maps                                  = MAPS
_segments                              = SEGMENTS
_sessions_duration                     = SESSION_DURATION

_seconds_to_skip  =  5
_delay_T          =  0

drivers_list=[
              "1","11",
              "16","55",
              "44","63",
              "14","18",
              "4","81",
              "20","27",
              "22","3",
              "10","31",
              "23","2",
              "77","24"
              ]

tabs={"update_telemetry":  "Telemetry_view",
      "compare_telemetry":  "Telemetry_compare_view",
      "timing":             "Timing_view"}

YEAR,RACE,SESSION = "2024", "Jeddah", "Race"
_event_name="Saudi Arabian Grand Prix"

def kill_button(self):
  dpg.destroy_context()

def add_driver_tel_plot(number,parent,driver):
  """ 
    Adds subplots with speed,throttle and brakes (can easily add the remaining) for the given driver.  
  """
  nr=int(number) # 0 -> 19 !
  x_pos=_TEL_PLOTS_WIDTH*(nr%2) 
  x_pos_headshot = (_TEL_PLOTS_WIDTH-SIDE_OF_HEADSHOTS_PNG) + _TEL_PLOTS_WIDTH*(nr%2) 
  y_pos=_TEL_PLOTS_HEIGHT*(nr//2)+_TOP_BAR_HEIGHT
  add_name_over_photo=False
  with dpg.group(pos=(x_pos,y_pos),height=_TEL_PLOTS_HEIGHT,tag="wdw"+driver,parent=parent,horizontal=True):
    with dpg.subplots(rows=3,columns=1,row_ratios=(3,1,1),no_title=True,link_all_x=True,no_align=False,no_resize=False,label=_DRIVERS_INFO[driver]["full_name"],tag=_DRIVERS_INFO[driver]["full_name"],width=_TEL_PLOTS_WIDTH-95,height=_TEL_PLOTS_HEIGHT):
      with dpg.plot(tag="speed"+driver,anti_aliased=True):    
        dpg.add_plot_axis(dpg.mvXAxis,tag="x_axis_SPEED"+driver,time=True,no_tick_labels=True,no_tick_marks=True)
        dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis_SPEED"+driver)
        dpg.set_axis_limits("y_axis_SPEED"+driver, -2, 399)
        dpg.add_line_series(x=[0],y=[0],label=driver+"s",parent="y_axis_SPEED"+driver,tag=driver+"s")
        #dpg.set_item_label(item=driver+"s",label=_DRIVERS_INFO[driver]["abbreviation"])
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
      with dpg.drawlist(width=SIDE_OF_HEADSHOTS_PNG,height=SIDE_OF_HEADSHOTS_PNG,pos=(0,0),tag=driver+"HeadShotUrl_drawlist"):
        map_dict=str(paths.HEADSHOTS_PATH / (_DRIVERS_INFO[driver]["full_name"]+"headshot.png"))
        if map_dict.split("/")[-1] in os.listdir(str(paths.HEADSHOTS_PATH)):
          width, height, channels, data = dpg.load_image(map_dict)
          #_map_width,_map_height=width,height
          with dpg.texture_registry():
            dpg.add_static_texture(width=width, height=height, default_value=data, tag=driver+"HeadShotUrl")
          dpg.draw_image(texture_tag=driver+"HeadShotUrl",tag=driver+"HeadShotUrl_image",parent=driver+"HeadShotUrl_drawlist",pmin=(0,0),pmax=(width,height),show=True)
        else:
          add_name_over_photo=True
          print(map_dict," not found!")
      if add_name_over_photo:
        dpg.add_text(default_value=map_dict.split("/")[-1][-12],tag=driver+"_nameOverImage",pos=(x_pos_headshot+10,y_pos+10))
      dpg.add_text(default_value="Tyre: ",tag=driver+"_tyreFitted",pos=(x_pos_headshot,y_pos+SIDE_OF_HEADSHOTS_PNG+20*0))
      dpg.add_text(default_value="Tyre Age: ",tag=driver+"_agetyreFitted",pos=(x_pos_headshot,y_pos+SIDE_OF_HEADSHOTS_PNG+20))
      dpg.add_text(default_value="Drs: ",tag=driver+"_drs",pos=(x_pos_headshot,y_pos+SIDE_OF_HEADSHOTS_PNG+20*2))

def showTab(sender):
    """ 
      CallBack. Needed to change what tab is displayed when clicked.
    """
    print(sender," show set to True")
    dpg.configure_item(tabs[sender],show=True)
    for tab in tabs.keys():
      if tab!=sender:
        print(tabs[tab]," show set to False")
        dpg.configure_item(tabs[tab],show=False)
    
def change_map_background():
    """ 
      Sets the track map.
    """
    if dpg.does_item_exist(item="map_background"):
      dpg.delete_item(item="map_background") 
      dpg.delete_item(item="map_background_texture")
    
    map_dict=str(paths.MAPS_PATH / _maps[_event_name]["map"])
    width, height, channels, data = dpg.load_image(map_dict)
    
    print(width,height)
    
    #_map_width,_map_height=width,height
    with dpg.texture_registry():
      dpg.add_static_texture(width=width, height=height, default_value=data, tag="map_background_texture")

    
    dpg.draw_image(texture_tag="map_background_texture",tag="map_background",parent="drawlist_map_position",pmin=(0,0),pmax=(width,height),show=True)    
        
def add_buttons():
    """
      Initialize all buttons.
    """
    #int_times=_LS._interesting_times
    dpg.add_image_button(texture_tag="pause_icon",label="",tag="pause_button",parent="menu")
    dpg.add_button(label="Pause",tag="PLAY_BUTTON",width=_BUTTONS_WIDTH,height=_BUTTONS_HEIGHT,small=True,parent="menu")
    dpg.add_button(label="-"+str(_seconds_to_skip)+"s",width=_BUTTONS_WIDTH,height=_BUTTONS_HEIGHT,tag="backward",parent="menu")
    dpg.add_button(label="+"+str(_seconds_to_skip)+"s",width=_BUTTONS_WIDTH,height=_BUTTONS_HEIGHT,tag="forward",parent="menu")
    dpg.add_button(label="kill",width=_BUTTONS_WIDTH,height=_BUTTONS_HEIGHT,callback=kill_button,parent="menu")
    dpg.add_input_int(label="Update +/- [s]",tag="skip_seconds",default_value=_seconds_to_skip,width=_BUTTONS_WIDTH,min_value=1,max_value=300,min_clamped=True,max_clamped=True,step=0,step_fast=0,on_enter=True,parent="menu")
    dpg.add_input_int(label="Delay [s]",tag="delay",width=_BUTTONS_WIDTH,min_value=0,max_value=300,default_value=_delay_T,min_clamped=True,max_clamped=True,step=0,step_fast=0,on_enter=True,parent="menu")
    dpg.add_button(label="tel",tag="tel",parent="menu")
    
 
########################################### PRIMARY WINDOW  ################################ 
 
with dpg.window(tag="Primary window",width=_VIEWPORT_WIDTH,height=_VIEWPORT_HEIGHT,pos=[0,0],no_bring_to_front_on_focus=True):
  with dpg.menu_bar():
    with dpg.tab_bar():
      for tab in tabs.keys():
        dpg.add_tab_button(label=tab,tag=tab,callback=showTab) 
 
 
    
############################## COMPARE TEL ############################################# 
_n_drivers=4    
width=900
height=400
minx1=0
maxx1=1
# Initialization
with dpg.group(label="Compare Telemetry View",tag="Telemetry_compare_view",show=False,parent="Primary window"):
  with dpg.group(label="map_buttons",tag="map_buttons",horizontal=True):
    dpg.add_combo(items=list(_maps.keys()),tag="map",width=150,default_value=None)
    #dpg.add_input_double(label="Offset_Turns",tag="slide_corner",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=Set_Corners)
  with dpg.group(label="offset_drivers",tag="offset_drivers",horizontal=True):
    for i in range(_n_drivers):
      dpg.add_input_double(label="Offset_Driver"+str(i),tag="OFF_DRV-"+str(i),min_value=-20,max_value=20,default_value=0,width=150,min_clamped=True,max_clamped=True,step=1)
  with dpg.group(label="offset_drivers_tel",tag="offset_drivers_tel",horizontal=True):
    for i in range(_n_drivers):
      dpg.add_input_double(label="Offset_Turns"+str(i),tag="slide_corner-"+str(i),min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.05)
  #    #dpg.add_input_double(label="Offset_Driver2",tag="OFF_DRV2",min_value=-0.5,max_value=0.5,default_value=0,width=150,min_clamped=True,max_clamped=True,step=0.0005,callback=Set_Offset_Space)            
  #with dpg.group(label="speeds_text",tag="speeds_text",horizontal=True):  
  #  for i in range(_n_drivers):
  #    dpg.add_text(default_value="Driver "+str(i)+":",tag="DRV-"+str(i)+"-DRV_TEXT")
  #    #dpg.add_text(default_value="Driver 1 speed",tag="DRV-1-SPEED_TEXT")
  with dpg.group(label="clear_buttons",tag="clear_buttons",horizontal=True):
    dpg.add_button(label="Clear Annotations",tag="clear_ann")
    dpg.add_button(label="Clear Plot",tag="clear_plot")
    dpg.add_checkbox(label="Adjust Speed Limits",tag="Adjust Speed Limits")
    
  for i in range(_n_drivers):
    with dpg.group(label="drivers_buttons"+str(i),tag="drivers_buttons"+str(i),horizontal=True):
      dpg.add_combo(items=list(drivers_list),tag="DRV-"+str(i),width=150,default_value=None)
      dpg.add_combo(items=[],tag="LAP-"+str(i),width=150,default_value=None)
  with dpg.group(label="compare_buttons",tag="compare_buttons",horizontal=True):
    for i in range(_n_drivers):
      dpg.add_combo(items=list(drivers_list),tag="DRV-"+str(i)+"-LapTimes",width=150,default_value=None)
      #dpg.add_combo(items=list(_drivers_list),tag="DRV-2-LapTimes",width=150,default_value=None)
  
  with dpg.plot(label="CompareSpeed",tag="CompareSpeed",width=width,height=height,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_SPEED_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="Speed [km/h]", tag="y_axis_SPEED_Compare")
    dpg.set_axis_limits("y_axis_SPEED_Compare", -2, 380)
    dpg.set_axis_limits("x_axis_SPEED_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_SPEED_Compare",_xTurns)
    dpg.add_drag_line(label="speed_compare_line",tag="speed_compare_line", color=[255, 0, 0, 255],thickness=0.25, default_value=0.5)
  dpg.add_vline_series(x=[],tag="speed_sectors",parent="y_axis_SPEED_Compare")
  dpg.bind_item_theme(item="speed_sectors",theme="line_weight")
    
    
  with dpg.plot(label="CompareThrottle",width=width,height=height/3.,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_THROTTLE_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="Throttle [%]", tag="y_axis_THROTTLE_Compare")
    dpg.set_axis_limits("y_axis_THROTTLE_Compare", -2, 101)
    dpg.set_axis_limits("x_axis_THROTTLE_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_THROTTLE_Compare",_xTurns)
  with dpg.plot(label="CompareBrake",width=width,height=height/3.,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_BRAKE_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="Brake [on/off]", tag="y_axis_BRAKE_Compare")
    dpg.set_axis_limits("y_axis_BRAKE_Compare", -2, 101)
    dpg.set_axis_limits("x_axis_BRAKE_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_BRAKE_Compare",_xTurns)
  with dpg.plot(label="CompareDeltaTime",width=width,height=height/3.,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_DELTA_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="Delta [s]", tag="y_axis_DELTA_Compare")
    dpg.set_axis_limits("y_axis_DELTA_Compare", -3, 3)
    dpg.set_axis_limits("x_axis_DELTA_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_DELTA_Compare",_xTurns)
  with dpg.plot(label="CompareRPM",width=width,height=height/3.,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_RPM_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="RPM", tag="y_axis_RPM_Compare")
    dpg.set_axis_limits("y_axis_RPM_Compare", -2, 19000)
    dpg.set_axis_limits("x_axis_RPM_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_RPM_Compare",_xTurns)
  
  with dpg.plot(label="CompareGear",width=width,height=height/3.,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_GEAR_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="Gear", tag="y_axis_GEAR_Compare")
    dpg.set_axis_limits("y_axis_GEAR_Compare", -0.2, 9)
    dpg.set_axis_limits("x_axis_GEAR_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_GEAR_Compare",_xTurns)
  
  with dpg.plot(label="CompareDrs",width=width,height=height/3.,no_title=True,anti_aliased=True):
    dpg.add_plot_legend()
    dpg.add_plot_axis(dpg.mvXAxis, label="Turns",tag="x_axis_DRS_Compare")
    dpg.add_plot_axis(dpg.mvYAxis, label="DRS [on/off]", tag="y_axis_DRS_Compare")
    dpg.set_axis_limits("y_axis_DRS_Compare", -0.2, 1.2)
    dpg.set_axis_limits("x_axis_DRS_Compare", ymin=minx1 ,ymax=maxx1)
    #dpg.set_axis_ticks("x_axis_DRS_Compare",_xTurns)
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
  

########################################### TIMING VIEW #####################################
  
with dpg.group(label="Timing View",tag="Timing_view",show=False,parent="Primary window"):
  with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit, resizable=True, no_host_extendX=True,tag="TableTimingView",parent="Timing_view",
                borders_innerV=True, borders_outerV=True, borders_outerH=True,sortable=True):
    _table_column=["Position","Full Name","BestLapTime","LastLapTime","gap","int","Bestsector1","sector1","segments1","Bestsector2","sector2","segments2","Bestsector3","sector3","segments3","I1","I2","FL","ST"]
    
    for column_name in _table_column:
      dpg.add_table_column(label=column_name,tag=column_name)
    
    for driver in drivers_list:
      with dpg.table_row():
        for nr_column,column_name in enumerate(_table_column): 
          if column_name=="Full Name":
            dpg.add_text(default_value=_DRIVERS_INFO[driver]["full_name"],tag=driver+column_name)
          elif "segments" in column_name:
            dpg.add_group(label=driver+column_name+"musec",tag=driver+column_name+"musec",horizontal=True,width=10)
            nsegments=10
            for i in range(nsegments):
              dpg.add_button(label="",tag=driver+column_name+"musec"+str(i))
          else:
            #print(driver+column_name)
            dpg.add_text(default_value="-",tag=driver+column_name)



            
dpg.set_primary_window(window="Primary window",value=True)
dpg.configure_item("Primary window", horizontal_scrollbar=True) # work-around for a known dpg bug!
    
    
with dpg.group(label=YEAR+"-"+" ".join(RACE.split("_"))+"-"+SESSION,tag="Telemetry_view",show=True,parent="Primary window"):
  
  with dpg.window(label="menu_bar_buttons_weather",tag="menu_bar_buttons_weather",width=MAP_WIDTH,height=_VIEWPORT_HEIGHT,pos=(_VIEWPORT_WIDTH-MAP_WIDTH-SCR_SIZE,_TOP_BAR_HEIGHT),no_title_bar=True,no_resize=True,no_move=True):
    with dpg.group(label="menu_row",tag="menu",horizontal=True,pos=(0,0)):
      add_buttons()
    with dpg.group(label="Column1",tag="column1",horizontal=False,pos=(0,_BUTTONS_HEIGHT)):  
      dpg.add_text(default_value="AirTemp:",  tag="AirTemp") #
      dpg.add_text(default_value="TrackTemp:",tag="TrackTemp") #
      dpg.add_text(default_value="Rainfall:", tag="Rainfall") #
      dpg.add_text(default_value="Current Time:", tag="Actual_Time")
      dpg.add_text(default_value="Session: ", tag="Session_Name")
      dpg.add_text(default_value="Session time remaining: ", tag="Session_TimeRemaining")
      #dpg.add_text(default_value="WindDirection:", tag="WindDirection")
    with dpg.group(label="Column2",tag="column2",horizontal=False,pos=(_BUTTONS_WIDTH*2,_BUTTONS_HEIGHT)):
      dpg.add_text(default_value="WindSpeed:",tag="WindSpeed") #
      dpg.add_text(default_value="Humidity:", tag="Humidity") #
      dpg.add_text(default_value="Status:", tag="Session_Status")
      #dpg.add_text(default_value="Pressure:", tag="Pressure")
    
    #with dpg.window(label="Track_Map",tag="Track_Map",width=MAP_WIDTH,height=MAP_HEIGHT,pos=(_VIEWPORT_WIDTH-MAP_WIDTH-SCR_SIZE,_TOP_BAR_HEIGHT+_BUTTONS_HEIGHT*(_BUTTONS_ROWS+2)),no_title_bar=True,no_resize=True,no_move=True):
    #with dpg.window(width=640,height=480,pos=(),tag="map_window"):
    with dpg.group(label="Map",tag="Map_Track",horizontal=False,pos=(0,140),width=MAP_WIDTH,height=MAP_HEIGHT):
      dpg.add_drawlist(width=MAP_WIDTH,height=MAP_HEIGHT,pos=(0,0),tag="drawlist_map_position")
      #dpg.draw_circle(color=(255,0,0,255),center=(100,100),radius=5,fill=(255,0,0,255),tag="circle",parent="drawlist_map_position")
    change_map_background()
  
    with dpg.group(label="RaceMessages",tag="Race_Messages",width=MAP_WIDTH,height=_VIEWPORT_HEIGHT-TOP_BAR_HEIGHT-MAP_HEIGHT-140,pos=(0,_VIEWPORT_HEIGHT-MAP_HEIGHT-140)):
      dpg.add_text(tag="Race_MSG_HEADER",default_value=" RACE MESSAGES:",wrap=308)
      dpg.add_text(tag="race_msgs",default_value=" asfasf asfaf \n asfafèjjs \n asfblnf \n adf \n pporororo ",wrap=308)
      #dpg.draw_circle(color=(255,0,0,255),center=(100,100),radius=5,fill=(255,0,0,255),tag="circle",parent="drawlist_map_position")
  
  # telemetry plots
  annotations_telemetry_plot = {}
  drivers_watchlist_telemetry=[]
  for team in _watchlist_teams:
    for driver in drivers_list:
      annotations_telemetry_plot[driver]=[] # [[time,speed,id,tag=("min"/"max")],[...]]
      # initialize dict that is needed later for keeping
      # track of latest id of the annotations in telemetry
      if team==_DRIVERS_INFO[driver]["team"]:
        drivers_watchlist_telemetry.append(driver)
  for nr,driver in zip(range(len(drivers_list)),drivers_watchlist_telemetry):
    add_driver_tel_plot(number=nr,parent="Telemetry_view",driver=driver)

#dpg.show_style_editor()

print(dpg.get_viewport_width()," ",dpg.get_viewport_height())
print(dpg.mvStyleVar_ScrollbarSize)

#dpg.show_style_editor()
dpg.start_dearpygui()  
dpg.destroy_context()