import MERGER
import PARSER
import src.Analyzer as Analyzer
from matplotlib.collections import LineCollection
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import matplotlib.pyplot as plt
import time
from pynput import keyboard
import re
import dearpygui.dearpygui as dpg

class LIVE_SIM:
    
    def __init__(self,  YEAR:           str, 
                        NAME:           str, 
                        SESSION:        str, 
                        filename_feeds: str="FEEDS.json",
                        filename_urls:  str="SESSION_URLS.json"):
        
        self._parser=PARSER.PARSER(filename_feeds=filename_feeds,filename_urls=filename_urls)
        self._merger=MERGER.MERGER(filename_feeds=filename_feeds,filename_urls=filename_urls)
        #self._scheduler = BackgroundScheduler()
        self._task_state = "running"
        self._YEAR=YEAR
        self._NAME=NAME
        self._SESSION=SESSION
        self._full_data = self._merger.merger(YEAR=YEAR,NAME=NAME,SESSION=SESSION)
        self._analyzer=Analyzer.analyzer()

        self._drivers_dict = self._parser.get_drivers_dict(YEAR=YEAR,NAME=NAME,SESSION=SESSION)
        
        self._drivers_list=list(self._drivers_dict.keys())
        self._drivers_list.sort()
        self._drivers_colors=[self._drivers_dict[driver]["TeamColour"] for driver in self._drivers_list]

        self._interesting_times=self._parser.get_interesting_times(YEAR=YEAR,NAME=NAME,SESSION=SESSION)
        self._starting_time_session=self._analyzer.get_starting_time_session(self._interesting_times)

        self.sim_time = 0.
        self._lines_tel={}
        self._lines_tel["Speed"] = {}
        self._lines_tel["Throttle"] = {}
        self._lines_tel["Brake"] = {}
        self._lines_tel["Time"] = {}
        self._x={}
        self._y={}

        #self.KB=keyboard()

    # Coroutine to listen for keyboard events
    #async def listen_for_keyboard_events(self):
    #    while True:
    #        key = await asyncio.get_event_loop().run_in_executor(None, input)
    #        #print("\n\n\n\n\n",key,"\n\n\n\n\n\n")
    #        if key == "p":
    #            if self._task_state=="running":
    #                self._task_state="pause"
    #            else:
    #                self._task_state="running"
    #        elif key== "f":
    #            self._task_state="forward"
    #        elif key== "b":
    #            self._task_state="backward"
    #        elif key=="s":
    #            self._task_state="setting"
    
    def on_press(self,key):
        try:
            if key.char == "p":
                if self._task_state=="running":
                    self._task_state="pause"
                else:
                    self._task_state="running"
            elif key.char== "f":
                    self._task_state="forward"
            elif key.char== "b":
                    self._task_state="backward"
            elif key.char=="s":
                    self._task_state="setting"
        except AttributeError:
            #print('special key {0} pressed'.format(key))
            pass


    # Coroutine to execute a task
    async def execute(self,time_ms, value):
        await asyncio.sleep(time_ms/1000.)
        print("\n",time_ms/1000.," ",value)
        
    def get_plot_index(self,feed: str):
        """
        index:
            - 1: WeatherData
            - 2: RaceControlMessages
            - 3: CarData.z
            - 4: Position.z
            - ...
        """
        if feed=="WeatherData":
            return 1
        elif feed=="RaceControlMessages":
            return 2
        elif feed=="CarData.z":
            return 3
        elif feed=="Position.z":
            return 4
        else:
            raise Exception("Wrong feed: ",feed)


    async def plot_speed(self,time_ms,value):
        # Add the current time to the x- and y-coordinate list
        await asyncio.sleep(time_ms/1000.)
        temp_flag=False
        if "CarData.z" not in value.keys():
            temp_flag=True
        else:
            prova= await self._analyzer.cardata(value["CarData.z"])
            prova=prova["1"]["Speed"]
    
        print(time_ms," ",value," ",len(self._x))
        if len(self._x)<300:
            if temp_flag:
                self._y.append(0)    
            else:
                self._y.append(prova)
            self._x.append(time_ms)
            
        else:
            self._x=self._x[1:]
            self._y=self._y[1:]
            if temp_flag:
                self._y.append(0)
            else:
                self._y.append(prova)
            self._x.append(time_ms)
        self._figure.canvas.restore_region(self._ax_bkg)
        # Update the line object with the new data
        self._line.set_data(self._x, self._y)
        self._ax.draw_artist(self._line)
        self._ax.relim()
        self._ax.autoscale_view()
        self._figure.canvas.blit(self._ax.bbox)
        # Draw the plot
        #self._figure.canvas.draw()
        self._figure.canvas.flush_events()
        # Pause for a short time to allow the plot to update

    def initialize_plot_telemetry(self):
        plt.ion()
        self._fig_tel,(self._ax_sp,self._ax_thr,self._ax_br) = plt.subplots(3,1,gridspec_kw={"height_ratios":[3,1,1]},sharex=True)  # n rows and m col to be fixed
        self._lines_tel["Speed"] = {}
        self._lines_tel["Throttle"] = {}
        self._lines_tel["Brake"] = {}
        self._lines_sp_AD=[]
        self._lines_thr_AD=[]
        self._lines_br_AD=[]
        self._ax_sp.set_ylim(-0.1, 380)
        self._ax_thr.set_ylim(-0.1,101)
        self._ax_br.set_ylim(-0.1,1.1)
        self._fig_tel.canvas.draw()
        self._ax_bkg_tel_sp=self._fig_tel.canvas.copy_from_bbox(self._ax_sp.bbox)
        self._ax_bkg_tel_thr=self._fig_tel.canvas.copy_from_bbox(self._ax_thr.bbox)
        self._ax_bkg_tel_br=self._fig_tel.canvas.copy_from_bbox(self._ax_thr.bbox)
        plt.show(block=False)
    
    def reset_telemetry_dictionary(self):
        for driver in self._drivers_list:
            self._lines_tel["Speed"][driver]    = []
            self._lines_tel["Throttle"][driver] = []
            self._lines_tel["Brake"][driver]    = []
            self._lines_tel["Time"][driver]     = []

    def update_list(self,time_ms: int,msg_sorted: dict):
        for driver,telemetry in msg_sorted.items():
            if driver not in self._lines_tel["Speed"].keys():
                self._lines_tel["Speed"][driver]    = []
                self._lines_tel["Throttle"][driver] = []
                self._lines_tel["Brake"][driver]    = []
                self._lines_tel["Time"][driver]     = []
            if len(self._lines_tel["Speed"][driver])>300:
                self._lines_tel["Speed"][driver]=self._lines_tel["Speed"][driver][1:]
                self._lines_tel["Throttle"][driver]=self._lines_tel["Throttle"][driver][1:]
                self._lines_tel["Brake"][driver]=self._lines_tel["Brake"][driver][1:]
                self._lines_tel["Time"][driver]=self._lines_tel["Time"][driver][1:]
            self._lines_tel["Speed"][driver].append(telemetry["Speed"])
            self._lines_tel["Throttle"][driver].append(telemetry["Throttle"])
            self._lines_tel["Brake"][driver].append(telemetry["Brake"])
            self._lines_tel["Time"][driver].append(time_ms)
        return self._lines_tel
        
    def update_plot_tel(self,time_ms: int,msg_sorted: dict):
        self._lines_sp_AD=[]
        self._lines_thr_AD=[]
        self._lines_br_AD=[]
        self._lines_col=[]
        for driver,telemetry in msg_sorted.items():
            if driver in ["1","16","11","55"]:
                
                if driver not in self._lines_tel["Speed"].keys():
                    self._lines_tel["Speed"][driver]    = []
                    self._lines_tel["Throttle"][driver] = []
                    self._lines_tel["Brake"][driver]    = []
                if len(self._lines_tel["Speed"][driver])>300:
                    self._lines_tel["Speed"][driver]=self._lines_tel["Speed"][driver][1:]
                    self._lines_tel["Throttle"][driver]=self._lines_tel["Throttle"][driver][1:]
                    self._lines_tel["Brake"][driver]=self._lines_tel["Brake"][driver][1:]

                self._lines_tel["Speed"][driver].append([time_ms,telemetry["Speed"]])
                self._lines_tel["Throttle"][driver].append([time_ms,telemetry["Throttle"]])
                self._lines_tel["Brake"][driver].append([time_ms,telemetry["Brake"]])
                    
                # Update the line object with the new data
                self._lines_sp_AD.append(self._lines_tel["Speed"][driver])
                self._lines_thr_AD.append(self._lines_tel["Throttle"][driver])
                self._lines_br_AD.append(self._lines_tel["Brake"][driver])
                self._lines_col.append(self._color[driver])
        lines_sp=LineCollection(self._lines_sp_AD,colors=self._lines_col)
        lines_thr=LineCollection(self._lines_thr_AD,colors=self._lines_col)
        lines_br=LineCollection(self._lines_br_AD,colors=self._lines_col)
        
        self._fig_tel.canvas.restore_region(self._ax_bkg_tel_sp)
        self._ax_sp.add_collection(lines_sp)
        self._fig_tel.draw_artist(self._ax_sp)
        self._fig_tel.canvas.blit(self._ax_sp.bbox)

        self._fig_tel.canvas.restore_region(self._ax_bkg_tel_thr)
        self._ax_thr.add_collection(lines_thr)
        self._fig_tel.draw_artist(self._ax_thr)
        self._fig_tel.canvas.blit(self._ax_thr.bbox)
                
        self._fig_tel.canvas.restore_region(self._ax_bkg_tel_br)
        self._ax_br.add_collection(lines_br)
        self._fig_tel.draw_artist(self._ax_br)
        self._fig_tel.canvas.blit(self._ax_br.bbox)
        
        self._ax_sp.autoscale(True,axis="x")
        self._fig_tel.canvas.flush_events()
        # Updat the line object with the new data
                    

    #async def simulate_live_asyncio(self):
    #    for time_ms,value in self._full_data.items():
    #        asyncio.create_task(self.plot_speed(time_ms,value))
    #    asyncio.create_task(self.listen_for_keyboard_events())
    #    await asyncio.gather(*asyncio.all_tasks())

    #async def sim_run2(self):
    #    asyncio.create_task(self.listen_for_keyboard_events())
    #    asyncio.create_task(self.run_2())
    #    await asyncio.gather(*asyncio.all_tasks())
    #    #self.listen_for_keyboard_events()
    #    #self.run_2()

    def initialize_plot2(self):
        # Initialize the GUI
        self._lines_tel["Speed"] = {}
        self._lines_tel["Throttle"] = {}
        self._lines_tel["Brake"] = {}
        self._lines_tel["Time"] = {}
        dpg.create_context()

        with dpg.window(label="Tutorial",tag="win",width=800,height=600):
            self.plot = dpg.plot(label="Plot")
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="x",tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis")
            dpg.add_line_series(x=[0],y=[0],label="1",parent="y_axis",tag="series_tag")
                

    def run2(self):
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        prev_time=list(self._full_data.keys())[0]
        self.initialize_plot2()
        dpg.create_viewport(title='Custom Title', width=850, height=640)
        dpg.setup_dearpygui()
        # Start the GUI loop
        dpg.show_viewport()
        while dpg.is_dearpygui_running():

            for time_ms,value in self._full_data.items():
                if self._task_state=="forward":
                    self.sim_time+=5000
                    self._task_state="running"
                #elif self._task_state=="backward":  # to be fixed
                #    self.sim_time-=5000
                #    self._task_state="running"
                elif self._task_state=="setting":
                    self.sim_time=int(re.sub("[^0-9]","",input("Set time to go:")))
                    self._task_state="running"
                elif self._task_state=="running" and self.sim_time>time_ms:
                    print(self.sim_time," ",time_ms)
                    prev_time=time_ms
                else:
                    time.sleep((time_ms-prev_time)/1000)
                    self.sim_time=time_ms
                    prev_time=time_ms
                    print("\n",self._task_state," ",time_ms," ",value)
                    if list(value.keys())[0] == "CarData.z":
                        xy_dict=self.update_list(time_ms=time_ms,msg_sorted=self._analyzer.msg_sorter(value))
                        x=xy_dict["Time"]["1"]
                        y=xy_dict["Speed"]["1"]

                        # Add the new data to the plot widget
                        dpg.clear_plot(self.plot)

                        # Add the new data to the plot widget
                        dpg.add_plot_series(self.plot, x, y)

                        # Render the GUI
                        dpg.render_dearpygui_frame()

                    while self._task_state=="pause":
                        time.sleep(0.01)

            dpg.destroy_context()



    def run(self):
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        prev_time=list(self._full_data.keys())[0]
        self.initialize_plot_telemetry()
        for time_ms,value in self._full_data.items():
            if self._task_state=="forward":
                self.sim_time+=5000
                self._task_state="running"
            #elif self._task_state=="backward":  # to be fixed
            #    self.sim_time-=5000
            #    self._task_state="running"
            elif self._task_state=="setting":
                self.sim_time=int(re.sub("[^0-9]","",input("Set time to go:")))
                self._task_state="running"
            elif self._task_state=="running" and self.sim_time>time_ms:
                print(self.sim_time," ",time_ms)
                prev_time=time_ms
            else:
                time.sleep((time_ms-prev_time)/1000)
                self.sim_time=time_ms
                prev_time=time_ms
                if list(value.keys())[0] == "CarData.z":
                    self.update_plot_tel(time_ms=time_ms,msg_sorted=self._analyzer.msg_sorter(value))
                print("\n",self._task_state," ",time_ms," ",value)
                while self._task_state=="pause":
                    time.sleep(0.01)
        
        # update everything (position_handler,cardata_handler,racecontroll_handler..)
        # each_handler -> update each driver if needed

        # handler -> take packed value and redirect to Analyzer 
        # Analyzer -> redirect packed msg to correct de-packed method (in class analyzer) and 
        #              return un-packed object with better keys and message ready to handle
        # handler -> un-packed back to handler that update plot/messages to front-end
                


    #def run(self):
    #    #asyncio.run(self.simulate_live_asyncio())
    #    asyncio.run(self.plotter())

    #def simulate_live(self,YEAR: str,NAME: str,SESSION: str,FORCE_UPDATE: bool=False):
    #    full_dictionary = self._merger.merger(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FORCE_UPDATE=FORCE_UPDATE)
    #    # Schedule the function to be called at each key in the dictionary.
    #    
    #    now=datetime.datetime.now()+datetime.timedelta(seconds=10)
    #    
    #    print(full_dictionary)
    #    print("Starting Live Simulation at: ", now)
    #    for key in full_dictionary.keys():
    #        run_time=now+datetime.timedelta(milliseconds=key)  # Calculate seconds value
    #        self._scheduler.add_job(self.print_value, args=(full_dictionary, key), trigger='date', run_date=run_time)
    #
    #    # Start the scheduler.
    #    self._scheduler.start()
    #
    #    while True:
    #        pass

    #def print_value(self,dictionary, key):
    #    # Print the value of the dictionary at the specified time.
    #    print(dictionary[key])

