import PARSER
import datetime
import arrow
import requests
import threading
import logging
import json
import numpy as np
import scipy

class DATABASE:
  """
  
  
  
  """
  
  def __init__(self,FEED_LIST: str,logger: logging,logger_file):
    
    # Initializing
    self._parser=PARSER.PARSER()
    self._feed_list=FEED_LIST
    self._logger=logger
    self._logger_file=logger_file
    
    # Lock system to access the database from multiple threads safely
    self._lock= threading.Lock()
    
    # Initializing DateTimes
    self._first_starting_msg_DT = None
    self._first_datetime        = None
    self._last_datetime         = None
    self._DT_BASETIME_TIMESTAMP = None
    self._DT_BASETIME           = None
    self._session_start_DT      = None
    
    # Initializing flags
    self._is_first_RD_msg       = False
    self._is_merge_ended        = False
    self._Display_LapTimes      = False
    self._first_message_flag    = False
   
    # Initializing useful dicts / lists to speed up searches
    self._last_tyres_fitted     = {}
    self._list_of_msgs=[]
    self._sample_position_list               = [] # exploiting the fact that positions data are given with the same Datetime for every driver
    self._sample_position_list_SC            = []
    self._sample_cardata_list                = [] # exploiting the fact that cardata are given with the same Datetime for every driver
    self._sample_driver                      = ""
    self._sample_driver_SC                   = ""
    self._SafetyCar_Ranges                   = []
    self._last_cardata_index_checked         = {}
      # TODO
      # since the timing_2.0 these are not needed anymore probably. Need to check
    self._last_datetime_checked_position     = 0
    self._last_datetime_checked_position_SC  = 0
    self._last_datetime_checked_cardata      = 0
    self._last_position_index_found          = 0
    self._last_position_index_found_SC       = 0
    self._last_racedata_starting_index_found = 0 
    
    # Drivers list
    self._drivers_list             = None
    self._drivers_list_provisional = set()
    self._drivers_list_api         = []
    
    # Ta-Daa the database..
    self._CarData={}
    self._Position={}
    self._Position_SC={}
    self._LeaderBoard={}
    self._Laps={}
    self._Tyres={}
    self._Weather={}
    self._RaceMessages = {}
    
    # Session status. Hard to make it work if a user jumps in in the middle of the session...
    self._last_aborted_is_compatible = False
    self._list_of_not_resuming_datetimes=[]
    self._LiveSessionStatus="Unknown"
    self._RunningStatus={
                          #1:                       # nr of restart
                          #{
                          #  "StartDateTime": 0,
                          #  "EndDateTime":   0,    # just as an example
                          #  "Duration":      0
                          #}  
                          }
    self._detected_session_type,self._event_name,self._meeting_key,self._meeting_name,self._session_name_api = "","","","",""
    self._meeting_country_name = ""
    self._Nof_Restarts=0
    self._finish_count=1
    self._finish_status={
                          "Qualifying":{
                                        1: "Q1",
                                        2: "Q2",
                                        3: "Q3"
                          },
                          "Sprint Shootout":{
                                        1: "SQ1",
                                        2: "SQ2",
                                        3: "SQ3"
                          },
                          "Race":{
                                        1: "Race"
                          },
                          "Sprint":{
                                        1: "Sprint Race"
                          },
                          "Practice 1":{
                                        1: "FP1"
                          },
                          "Practice 2":{
                                        1: "FP2"
                          },
                          "Practice 3":{
                                        1: "FP3"
                          },
                        }
  
    # TODO
    self._Laps[None]={} # no idea why it is here. Check if it is needed 
    
    # api requests to identify session played
    self._available_years=["2024","2023","2022","2021","2020","2019","2018"]
    self._base_url = "https://api.formula1.com/v1"
    self._eventListing_url="editorial-eventlisting"
    self._sessionResults_url="fom-results"
    self._headers = {
      "apikey": "t3DrvCuXvjDX8nIvPpcSNTbB9kae1DPs",
      "locale": "en"
               }
    
    # TODO
    # For Live. Probably not needed anymore since Timing_2.0. Check it 
    self._last_lapnumber_found               = {}
    self._last_stint_found                   = {}
    self._PitIn                              = {}
    
    
  def datetime_parser(self,json_dict):
    """ 
      First rude implementation of retrieving telemetry and useful infos from json files saved.
      Not used for now.
    """
    for (key, value) in json_dict.items():
      if key=="Time":
        json_dict[key]=[]
        for t in value:
          json_dict[key].append(arrow.get(t))
      elif type(value)==dict:
        for k,v in value.items():
          if type(v)==dict:
            if "DateTime" in v.keys():
              json_dict[key][k]["DateTime"]=arrow.get(json_dict[key][k]["DateTime"])
        
    return json_dict  
    
  def retrieve_dictionaries(self):
    """ 
      First rude implementation of retrieving telemetry and useful infos from json files saved.
      Not used for now.
    """
    year,race,session=self.get_year(),self.get_session_type(),self.get_event_name()
    print("Base file name: ",year+"_"+race+"_"+session+"_")
    try:
      print("Retrieving tyres")
      self._Tyres=json.load(open(year+"_"+race+"_"+session+"_tyres.json","r"),object_hook=self.datetime_parser)
      print("Tyres retrieved!")
    except Exception as err:
      self._logger.exception(err)
      self._logger_file.write("\n")
      self._logger_file.flush()
    try:
      print("Retrieving Laps")
      self._Laps=json.load(open(year+"_"+race+"_"+session+"_laps.json","r"),object_hook=self.datetime_parser)
      print("Laps retrieved!")
    except Exception as err:
      self._logger.exception(err)
      self._logger_file.write("\n")
      self._logger_file.flush()
    #try:
    #  print("Retrieving CarData")
    #  self._CarData=json.load(open(year+"_"+race+"_"+session+"_telemetry.json","r"),object_hook=self.datetime_parser)
    #  print("Telemetry retrieved!")
    #  if len(self._CarData.keys())>0:
    #    if "Time" in self._CarData[list(self._CarData.keys())[0]].keys():
    #      self._DT_BASETIME_TIMESTAMP=self._CarData[list(self._CarData.keys())[0]]["Time"][0].timestamp()
    #      self._first_datetime=self._CarData[list(self._CarData.keys())[0]]["Time"][0]
    #  self._sample_driver=list(self._CarData.keys())[0]
    #  self._sample_cardata_list=self._CarData[list(self._CarData.keys())[0]]["Time"]
    #except Exception as err:
    #  self._logger.exception(err)
    #  self._logger_file.write("\n")
    #  self._logger_file.flush()  
    
  def get_feeds(self):
    """
    Brief:
      Returns a list of feeds
    """
    return list(self._parser._feeds.keys())

  def feed_list(self,feed: str,YEAR: str,NAME: str,SESSION: str):
    """
    Brief:
      Basically overrides jsonStream_parser of Parser class.
    """
    f_list=self._parser.jsonStream_parser(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FEED=feed)
    if f_list!=-1:
      return f_list
    else:
      return -1 

  def update_drivers_list(self,DT: datetime.datetime,driv_list: list):
    """ 
      Update driver lists in the database and detect session type from the api.
    """
    with self._lock:
      self._drivers_list=driv_list
      self._detected_session_type,self._event_name,self._meeting_key,self._year,self._meeting_name,self._session_name_api = self.detect_session_type(DT)
      self._drivers_list.sort()

  def update_database(self,msg_decrypted: dict,feed: str): # lock
    """
    Live Simulations: called at the beginning to store all the infos useful to make analysis.
    Live: called at each message received.
    
    It is needed to make analysis irl/replayed. Probably with the advent of timing_2.0 we only need 
    laps, tyres and telemetry. (maybe position to do some interesting analysis?). Weather and RaceMsgs 
    are also storable since they are easy to manipulate
    
    CarData.z:
      Car telemetry channels:
      - 0: Engine RPM
      - 2: Speed (km/h)
      - 3: Gear (0 = neutral, 1-8 = forward gears, >9 = reverse gears)
      - 4: Throttle (0-100%, 104 when unavailable?)
      - 5: Brake (boolean 0-1, 104 when unavailable?)
      - 45: DRS (0-14, odd is disabled, even is enabled)

      credits to: MultiviewerF1 
    
    Position.z:
      I'll update it one day...
    """
    with self._lock:
      #print(self._first_datetime," ",self._DT_BASETIME_TIMESTAMP)
      try:
        if feed=="CarData.z":
          for DT,RD in msg_decrypted.items():
            #print(self._first_datetime," ",DT," ",msg_decrypted.keys())
            #print("A ",self._first_datetime)
            #print("A ",self._first_message_flag)
              
              ##print(DT.timestamp()," ",self._DT_BASETIME_TIMESTAMP)
            #print(DT,RD)
            for driver,channels in RD.items():
              #print(driver," ",channels)
              #print("aaa ",driver)
              self._drivers_list_provisional.add(driver)
              if driver not in self._CarData.keys():
                self._CarData[driver]={}
                self._CarData[driver]["Time"]=[]
                self._CarData[driver]["TimeStamp"]=[]
                self._CarData[driver]["RPM"]=[]
                self._CarData[driver]["Speed"]=[]
                self._CarData[driver]["Gear"]=[]
                self._CarData[driver]["Throttle"]=[]
                self._CarData[driver]["Brake"]=[]
                self._CarData[driver]["DRS"]=[]
                if self._sample_driver == "":
                  self._sample_driver = driver
              self._CarData[driver]["Time"].append(DT)
              self._CarData[driver]["TimeStamp"].append(DT.timestamp()-self._DT_BASETIME_TIMESTAMP)
              self._CarData[driver]["RPM"].append(channels["Channels"]["0"])
              self._CarData[driver]["Speed"].append(channels["Channels"]["2"])
              self._CarData[driver]["Gear"].append(channels["Channels"]["3"])
              self._CarData[driver]["Throttle"].append(channels["Channels"]["4"] if channels["Channels"]["4"]<101 else 0)
              self._CarData[driver]["Brake"].append(int(channels["Channels"]["5"]) if int(channels["Channels"]["5"])<101 else 0)
              self._CarData[driver]["DRS"].append(1 if channels["Channels"]["45"] in [10,12,14] else 0)
              if driver == self._sample_driver:
                self._sample_cardata_list.append(DT)
              #print(self._CarData[driver].keys())
            self._is_first_RD_msg=True
            #self._last_datetime=DT
          #print(self._drivers_list,self._drivers_list_provisional)
          if self._drivers_list==None:
            self._drivers_list=list(self._drivers_list_provisional)
            self._drivers_list.sort()
        elif feed=="Position.z":
          for DT,P in msg_decrypted.items():
            if DT.timestamp()-self._DT_BASETIME_TIMESTAMP<0:
              print(DT, " in Position.z in update_database is discarded: message sent before the first CarData message!")
            #elif self._last_datetime!=None:
            elif DT.timestamp()-self._last_datetime.timestamp()>120:
                print(DT, " in Position.z in update_database is discarded: message sent after the last CarData message!")
            else:
              for DRIVER,P_dict in P.items():
                if len(DRIVER)<3:
                  if DRIVER not in self._Position.keys():
                      self._Position[DRIVER]={}
                      self._Position[DRIVER]["Time"]=[]
                      self._Position[DRIVER]["TimeStamp"]=[]
                      self._Position[DRIVER]["XYZ"]=[]
                      if self._sample_driver == "":
                        self._sample_driver = DRIVER
                  self._Position[DRIVER]["Time"].append(DT)
                  self._Position[DRIVER]["TimeStamp"].append(DT.timestamp()-self._DT_BASETIME_TIMESTAMP)
                  self._Position[DRIVER]["XYZ"].append([P_dict["X"],P_dict["Y"],P_dict["Z"]])
                  if DRIVER == self._sample_driver:
                    self._sample_position_list.append(DT)
                elif len(DRIVER)>2:
                  if DRIVER not in self._Position_SC.keys():
                      self._Position_SC[DRIVER]={}
                      self._Position_SC[DRIVER]["Time"]=[]
                      self._Position_SC[DRIVER]["TimeStamp"]=[]
                      self._Position_SC[DRIVER]["XYZ"]=[]
                      self._Position_SC[DRIVER]["Range"]=[DT,DT]
                      if self._sample_driver_SC == "":
                        self._sample_driver_SC = DRIVER
                  self._Position_SC[DRIVER]["Time"].append(DT)
                  self._Position_SC[DRIVER]["TimeStamp"].append(DT.timestamp()-self._DT_BASETIME_TIMESTAMP)
                  self._Position_SC[DRIVER]["XYZ"].append([P_dict["X"],P_dict["Y"],P_dict["Z"]])
                  self._Position_SC[DRIVER]["Range"][1]=DT
                  if DRIVER == self._sample_driver_SC:
                    self._sample_position_list_SC.append(DT)
                #print(DRIVER," ",P_dict["X"],P_dict["Y"],P_dict["Z"])
        elif feed=="TimingDataF1":
          for DT,TDF1 in msg_decrypted.items():
            if DT.timestamp()-self._last_datetime.timestamp()>120:
              print(DT, " in TimingDataF1 in update_database is discarded: message sent after the last CarData message!")
            else:
              if "Lines" in TDF1.keys():
                for driver,stints in TDF1["Lines"].items():
                   if "LastLapTime" in stints.keys() or "NumberOfLaps" in stints.keys() or "inPit" in stints.keys() or "PitOut" in stints.keys() or "NumberOfPitStops" in stints.keys():
                      #print("\n",stints,"\n")
                      if driver not in self._Laps.keys():
                        self._Laps[driver]={}
                      if driver not in self._last_stint_found.keys():
                        self._last_stint_found[driver]=0
                      if driver not in self._last_lapnumber_found.keys():
                        self._last_lapnumber_found[driver]=0
                      if driver not in self._PitIn.keys():
                        self._PitIn[driver]=False
                      if "InPit" in stints.keys():
                        self._PitIn[driver]=stints["InPit"]
                      if "NumberOfLaps" in stints.keys():
                        LAP=stints["NumberOfLaps"]
                        self._last_lapnumber_found[driver]=LAP
                        if LAP not in self._Laps[driver].keys() and LAP!=1:
                          #print("Lap: ",LAP," for driver: ",driver," already present! Maybe it is ok.")
                        #else:
                          self._Laps[driver][LAP]={"DateTime":          DT,
                                                   "ValueInt_sec":      0,
                                                   "ValueString":       "",
                                                   "TimeStamp":        DT.timestamp()-self._DT_BASETIME_TIMESTAMP,
                                                   "Stint":             self._last_stint_found[driver],
                                                   "PitOutLap":         False,
                                                   "PitInLap":          False,
                                                   "DRS":               False,
                                                   "Slice":             False,
                                                   "Avg_Speed":          0,
                                                   "Std_Speed":          0,
                                                   "FullThrottle_Perc":  0,
                                                   "Braking_Perc":       0,
                                                   "Cornering_Perc":     0,
                                                   "LiftCoast_Perc":     0,
                                                   "Max_Speed":          0,
                                                   "Min_Speed":          0
                                                   }
                          if LAP==2:
                            self._Laps[driver][LAP]["PitOutLap"]=True
                        elif LAP!=1:
                          if "PitInLap" not in self._Laps[driver][LAP].keys():
                            self._Laps[driver][LAP]["PitInLap"]=False
                          if "PitOutLap" not in self._Laps[driver][LAP].keys():
                            self._Laps[driver][LAP]["PitOutLap"]=False

                      if "LastLapTime" in stints.keys():
                        if "Value" in stints["LastLapTime"].keys():
                          Value=stints["LastLapTime"]["Value"]
                          if Value!="":
                            mins,secs=Value.split(":")
                            Value_int=int(mins)*60. + float(secs) # s
                          else:
                            Value_int=0
                          if self._last_lapnumber_found[driver] in self._Laps[driver].keys():
                            if self._Laps[driver][self._last_lapnumber_found[driver]]["ValueString"]=="":                         
                              self._Laps[driver][self._last_lapnumber_found[driver]]["ValueString"]=Value
                              self._Laps[driver][self._last_lapnumber_found[driver]]["ValueInt_sec"]=Value_int
                              self._Laps[driver][self._last_lapnumber_found[driver]]["DateTime"]=DT
                              self._Laps[driver][self._last_lapnumber_found[driver]]["TimeStamp"]=DT.timestamp()-self._DT_BASETIME_TIMESTAMP
                              
                              #print(driver,"\t",self._last_lapnumber_found[driver])
                              slice_tel=self.get_slice_between_times(start_time=DT-datetime.timedelta(seconds=Value_int),end_time=DT,update_DB_flag=True,driver=driver)
                              slice_tel=slice(slice_tel.start-1,slice_tel.stop+1)
                              speed_bef_int         = np.array(self._CarData[driver]["Speed"][slice_tel])
                              drs_bef_int           = np.array(self._CarData[driver]["DRS"][slice_tel])
                              brake_bef_int         = np.array(self._CarData[driver]["Brake"][slice_tel])
                              throttle_bef_int      = np.array(self._CarData[driver]["Throttle"][slice_tel])
                              times_bef_int         = np.array(self._CarData[driver]["TimeStamp"][slice_tel])
                              
                              times                 = np.copy(times_bef_int)
                              times=np.insert(times,1,(DT-datetime.timedelta(seconds=Value_int)).timestamp()-self._DT_BASETIME_TIMESTAMP)
                              times=np.insert(times,len(times)-1,DT.timestamp()-self._DT_BASETIME_TIMESTAMP)

                              speeds    = scipy.interpolate.Akima1DInterpolator(times_bef_int,speed_bef_int)(times)
                              Throttles = scipy.interpolate.Akima1DInterpolator(times_bef_int,throttle_bef_int)(times) 
                              Brakes    = scipy.interpolate.Akima1DInterpolator(times_bef_int,brake_bef_int)(times)
                              Drs       = scipy.interpolate.Akima1DInterpolator(times_bef_int,drs_bef_int)(times)
                              
                              Times=[TS-times[1] for TS in times]
                              #print(Times,"\n")
                              Times     = Times[1:-1]
                              speeds    = speeds[1:-1]   
                              Throttles = Throttles[1:-1] 
                              Brakes    = Brakes[1:-1]   
                              Drs       = Drs[1:-1]   
                              
                              space = scipy.integrate.cumulative_trapezoid(speeds/3.6,Times,initial=0)  
                              dx    = np.diff(space)
                              Total_space = np.sum(dx)
                              
                              throttle_medium = np.convolve(Throttles,np.array([0.5, 0.5]), mode='valid')
                              speed_medium    = np.convolve(speeds,np.array([0.5, 0.5]), mode='valid')
                              brake_medium    = np.convolve(Brakes,np.array([0.5, 0.5]), mode='valid')
                              
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Slice"]             = slice_tel
                              self._Laps[driver][self._last_lapnumber_found[driver]]["DRS"]               = bool(np.any(Drs == 1))
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Avg_Speed"]         = np.mean(speeds)
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Std_Speed"]         =  np.std(speeds)
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Max_Speed"]         =  float(speeds.max())
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Min_Speed"]         =  float(speeds.min())
                              self._Laps[driver][self._last_lapnumber_found[driver]]["FullThrottle_Perc"] = np.sum(dx[throttle_medium>98]) / Total_space * 100
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Braking_Perc"]      = np.sum(dx[brake_medium>98]) / Total_space * 100
                              self._Laps[driver][self._last_lapnumber_found[driver]]["Cornering_Perc"]    = np.sum(dx[(throttle_medium>=5) & (throttle_medium<=98)]) / Total_space * 100
                              self._Laps[driver][self._last_lapnumber_found[driver]]["LiftCoast_Perc"]    = np.sum(dx[ (speed_medium>10) & (throttle_medium<5) & (brake_medium < 1) ]) / Total_space * 100
                            
                            else:
                              #print(driver,"\t",self._last_lapnumber_found[driver])
                              slice_tel=self.get_slice_between_times(start_time=DT-datetime.timedelta(seconds=Value_int),end_time=DT,update_DB_flag=True,driver=driver)
                              slice_tel=slice(slice_tel.start-1,slice_tel.stop+1)
                              speed_bef_int         = np.array(self._CarData[driver]["Speed"][slice_tel])
                              drs_bef_int           = np.array(self._CarData[driver]["DRS"][slice_tel])
                              brake_bef_int         = np.array(self._CarData[driver]["Brake"][slice_tel])
                              throttle_bef_int      = np.array(self._CarData[driver]["Throttle"][slice_tel])
                              times_bef_int         = np.array(self._CarData[driver]["TimeStamp"][slice_tel])
                              
                              times                 = np.copy(times_bef_int)
                              times=np.insert(times,1,(DT-datetime.timedelta(seconds=Value_int)).timestamp()-self._DT_BASETIME_TIMESTAMP)
                              times=np.insert(times,len(times)-1,DT.timestamp()-self._DT_BASETIME_TIMESTAMP)

                              speeds    = scipy.interpolate.Akima1DInterpolator(times_bef_int,speed_bef_int)(times)
                              Throttles = scipy.interpolate.Akima1DInterpolator(times_bef_int,throttle_bef_int)(times) 
                              Brakes    = scipy.interpolate.Akima1DInterpolator(times_bef_int,brake_bef_int)(times)
                              Drs       = scipy.interpolate.Akima1DInterpolator(times_bef_int,drs_bef_int)(times)
                              
                              Times=[TS-times[1] for TS in times]
                              #print(Times,"\n")
                              Times     = Times[1:-1]
                              speeds    = speeds[1:-1]   
                              Throttles = Throttles[1:-1] 
                              Brakes    = Brakes[1:-1]   
                              Drs       = Drs[1:-1]   
                              
                              space = scipy.integrate.cumulative_trapezoid(speeds/3.6,Times,initial=0)  
                              dx    = np.diff(space)
                              Total_space = np.sum(dx)
                              
                              throttle_medium = np.convolve(Throttles,np.array([0.5, 0.5]), mode='valid')
                              speed_medium    = np.convolve(speeds,np.array([0.5, 0.5]), mode='valid')
                              brake_medium    = np.convolve(Brakes,np.array([0.5, 0.5]), mode='valid')
                              
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Slice"]             = slice_tel
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["DRS"]               = bool(np.any(Drs == 1))
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Avg_Speed"]         = np.mean(speeds)
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Std_Speed"]         =  np.std(speeds)
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Max_Speed"]         =  float(speeds.max())
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Min_Speed"]         =  float(speeds.min())
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["FullThrottle_Perc"] = np.sum(dx[throttle_medium>98]) / Total_space * 100
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Braking_Perc"]      = np.sum(dx[brake_medium>98]) / Total_space * 100
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["Cornering_Perc"]    = np.sum(dx[(throttle_medium>=5) & (throttle_medium<=98)]) / Total_space * 100
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]["LiftCoast_Perc"]    = np.sum(dx[(speed_medium>10) & (throttle_medium<5) & (brake_medium < 1) ]) / Total_space * 100
                              
                              self._Laps[driver][self._last_lapnumber_found[driver]+1]={"DateTime":          DT,
                                                                                        "ValueInt_sec":      Value_int,
                                                                                        "ValueString":       Value,
                                                                                        "TimeStamp":         DT.timestamp()-self._DT_BASETIME_TIMESTAMP,
                                                                                        "Stint":             self._last_stint_found[driver],
                                                                                        #"PitOutLap":         False,
                                                                                        #"PitInLap":          self._PitIn[driver]}
                                                                                        }    
                              self._last_lapnumber_found[driver]+=1
                          elif self._last_lapnumber_found[driver]==0:
                            self._last_lapnumber_found[driver]+=1
                            print("Skipping lap 1 for driver: ",driver, "! Should be correct but maybe it will require further checks.")
                          else:
                            print("Weird problem! LastLapTime is coming firstly with respect to NumberOfLaps!\n Maybe at the start of the jsonStream...")                               
                      if "NumberOfPitStops" in stints.keys():
                        if "InPit" in stints.keys():
                          if self._last_lapnumber_found[driver] in self._Laps[driver].keys() and stints["InPit"]==True:                    
                            self._Laps[driver][self._last_lapnumber_found[driver]+1]={"DateTime":          DT,
                                                                                      "ValueInt_sec":      0,
                                                                                      "ValueString":       "",
                                                                                      "TimeStamp":        DT.timestamp()-self._DT_BASETIME_TIMESTAMP,
                                                                                      "Stint":             stints["NumberOfPitStops"]-1,
                                                                                      "PitOutLap":         False,
                                                                                      "PitInLap":          True}
                            self._last_lapnumber_found[driver]+=1
                          else:
                            print("\nCase not understood! Last number of lap not in the lap dict when InPit is true... need to check! \n Driver: ",driver, " Lap: ",self._last_lapnumber_found[driver],"\n")
                        self._last_stint_found[driver]=stints["NumberOfPitStops"]
                      if "PitOut" in stints.keys():
                        if stints["PitOut"]==True:
                          self._Laps[driver][self._last_lapnumber_found[driver]+1]={"DateTime":            DT,
                                                                                      "ValueInt_sec":      0,
                                                                                      "ValueString":       "",
                                                                                      "TimeStamp":        DT.timestamp()-self._DT_BASETIME_TIMESTAMP,
                                                                                      "Stint":             self._last_stint_found[driver],
                                                                                      "PitOutLap":         True,
                                                                                      #"PitInLap":          self._PitIn[driver]
                                                                                      }
                          if self._last_lapnumber_found[driver]!=1:
                            if self._Laps[driver][self._last_lapnumber_found[driver]]["PitInLap"]==False:
                              self._Laps[driver][self._last_lapnumber_found[driver]]["PitInLap"]=True
                          self._last_lapnumber_found[driver]+=1
                    
        elif feed=="TimingAppData":
          for DT,TAD in msg_decrypted.items():
            if DT.timestamp()-self._last_datetime.timestamp()>120:
              print(DT, " in TimingAppData in update_database is discarded: message sent after the last CarData message!")
            else:
              if "Lines" in TAD.keys():
                for driver,stints in TAD["Lines"].items():
                  if "Stints" in stints.keys():
                    if type(stints["Stints"])==dict: 
                      info_stint=stints["Stints"]
                      if driver not in self._Tyres.keys():
                        self._Tyres[driver]={}
                      for stint,info_stint in info_stint.items():
                        if stint not in self._Tyres[driver].keys():
                          if len(self._Tyres[driver])==0:
                            self._Tyres[driver][stint]={"TotalLaps":0,
                                                        "Compound":"Unknown",
                                                        "New":False,
                                                        "CompoundAge":0,
                                                        "StartingLap":2 ,
                                                        "EndingLap":1,
                                                        "StartingStint_DateTime": DT}
                          else:
                            self._Tyres[driver][stint]={"TotalLaps":0,
                                                        "Compound":"Unknown",
                                                        "New":False,
                                                        "CompoundAge":0,
                                                        "StartingLap":2 if stint=="0" else self._Tyres[driver][str(int(stint)-1)]["EndingLap"]+1,
                                                        "EndingLap":1,
                                                        "StartingStint_DateTime": DT}
                        if "Compound" in info_stint.keys():
                          self._Tyres[driver][stint]["Compound"]=info_stint["Compound"]
                          self._last_tyres_fitted[driver]=[info_stint["Compound"],False,0,0]
                          if "New" in info_stint.keys():
                            self._Tyres[driver][stint]["New"] = True if info_stint["New"]=="true" else False
                            self._last_tyres_fitted[driver][1]=True if info_stint["New"]=="true" else False
                          if "StartLaps" in info_stint.keys():
                            self._Tyres[driver][stint]["CompoundAge"] = info_stint["StartLaps"]
                            self._Tyres[driver][stint]["New"] = (0 == info_stint["StartLaps"])
                            self._last_tyres_fitted[driver][2]=info_stint["StartLaps"]
                        if "TotalLaps" in info_stint.keys():
                          self._Tyres[driver][stint]["EndingLap"]=self._Tyres[driver][stint]["StartingLap"]+(info_stint["TotalLaps"]-1)-self._Tyres[driver][stint]["CompoundAge"]
                          self._Tyres[driver][stint]["TotalLaps"]=info_stint["TotalLaps"]-self._Tyres[driver][stint]["CompoundAge"]
                          #current_lap[driver]+=1

        elif feed=="WeatherData":
          for DT,WeatherDict in msg_decrypted.items():
            if DT.timestamp()-self._last_datetime.timestamp()>120:
              print(DT, " in WeatherData in update_database is discarded: message sent after the last CarData message!")
            else:
              self._Weather[DT]=WeatherDict    
            
        elif feed=="SessionStatus": # more checks needed
          for DT,Status in msg_decrypted.items():
            if DT.timestamp()-self._last_datetime.timestamp()>120:
              print(DT, " in SessionStatus in update_database is discarded: message sent after the last CarData message!")
            else:
              if Status["Status"]=="Started": 
                if self._first_starting_msg_DT==None:
                  self._first_starting_msg_DT=DT
                # displayed instantly as zero time remaining in telemetry tab even if race message arrives 
                # seconds later.. do not know a fast solution right now. Therefore for now it will remain
                # as it is 
                if self._last_aborted_is_compatible:
                  if DT>self._list_of_not_resuming_datetimes[0]:
                    self._last_aborted_is_compatible = False
                    self._RunningStatus[self._finish_count][self._Nof_Restarts]["Is_session_completed"]=True
                    self._list_of_not_resuming_datetimes.pop(0)
                    self._finish_count+=1
                    self._Nof_Restarts=0
                  else:
                    self._last_aborted_is_compatible = False

                self._Nof_Restarts+=1
                self._LiveSessionStatus=self._finish_status[self._detected_session_type][self._finish_count]

                if self._finish_count not in self._RunningStatus.keys():
                  self._RunningStatus[self._finish_count]={}
                if self._Nof_Restarts not in self._RunningStatus[self._finish_count].keys():
                  self._RunningStatus[self._finish_count][self._Nof_Restarts]={}

                self._RunningStatus[self._finish_count][self._Nof_Restarts]["StartDateTime"]=DT
                self._RunningStatus[self._finish_count][self._Nof_Restarts]["EndDateTime"]=None
                self._RunningStatus[self._finish_count][self._Nof_Restarts]["Duration"]=None
                self._RunningStatus[self._finish_count][self._Nof_Restarts]["Is_session_completed"]=False
                self._RunningStatus[self._finish_count][self._Nof_Restarts]["Type"]=self._finish_status[self._detected_session_type][self._finish_count]

              elif Status["Status"]=="Aborted":
                self._LiveSessionStatus="Off"
                if self._Nof_Restarts==0:
                  self._RunningStatus[self._finish_count][1]["StartDateTime"]=self._first_datetime
                  self._RunningStatus[self._finish_count][1]["EndDateTime"]=DT
                  self._RunningStatus[self._finish_count][1]["Duration"]=DT.timestamp()-self._first_datetime.timestamp()
                  self._RunningStatus[self._finish_count][1]["Is_session_completed"]=False
                  self._RunningStatus[self._finish_count][1]["Type"]=self._finish_status[self._detected_session_type][self._finish_count]
                else:
                  self._RunningStatus[self._finish_count][self._Nof_Restarts]["EndDateTime"]=DT
                  self._RunningStatus[self._finish_count][self._Nof_Restarts]["Duration"]=DT.timestamp()-self._RunningStatus[self._finish_count][self._Nof_Restarts]["StartDateTime"].timestamp()

                if len(self._list_of_not_resuming_datetimes)>0:
                  if DT<self._list_of_not_resuming_datetimes[0]:
                    self._last_aborted_is_compatible=True

              elif Status["Status"]=="Finished":  
                self._LiveSessionStatus="Off"
                if self._Nof_Restarts==0:
                  self._RunningStatus[self._finish_count][1]["StartDateTime"]=self._first_datetime
                  self._RunningStatus[self._finish_count][1]["EndDateTime"]=DT
                  self._RunningStatus[self._finish_count][1]["Duration"]=DT.timestamp()-self._first_datetime.timestamp()
                  self._RunningStatus[self._finish_count][1]["Is_session_completed"]=True
                  self._RunningStatus[self._finish_count][1]["Type"]=self._finish_status[self._detected_session_type][self._finish_count]
                else:
                  self._RunningStatus[self._finish_count][self._Nof_Restarts]["EndDateTime"]=DT
                  self._RunningStatus[self._finish_count][self._Nof_Restarts]["Duration"]=DT.timestamp()-self._RunningStatus[self._finish_count][self._Nof_Restarts]["StartDateTime"].timestamp()
                  self._RunningStatus[self._finish_count][self._Nof_Restarts]["Is_session_completed"]=True

                self._last_aborted_is_compatible=False
                self._finish_count+=1
                self._Nof_Restarts=0

              else:
                self._LiveSessionStatus = "Off"
       
        elif feed=="RaceControlMessages":
          for DT,Message in msg_decrypted.items():
            if DT.timestamp()-self._last_datetime.timestamp()>120:
              print(DT, " in RaceControlMessages in update_database is discarded: message sent after the last CarData message!")
            else:
              if "Messages" in Message.keys():
                if type(Message["Messages"])==list:
                  i=0
                  for msg in Message["Messages"]:
                    Message_dict={str(i):msg}
                    i+=1
                elif type(Message["Messages"])==dict:
                  Message_dict=Message["Messages"]
                else:
                  print("\n\n\n Type of the message not dict or list but: ",type(Message["Messages"]),"\n\n\n")
                  Message_dict={}
                for nrMsg,Msg in Message_dict.items():
                  n=1
                  nrThisMsg=nrMsg
                  while nrThisMsg in Msg.keys():
                    nrThisMsg=str(int(nrThisMsg)+n)
                    n+=1
                  if "Message" in Msg.keys() and "Category" in Msg.keys():
                    if "Flag" in Msg.keys():
                      category=Msg["Category"]+"_"+Msg["Flag"]
                    else:
                      category=Msg["Category"]
                    self._RaceMessages[nrThisMsg]={"Time":     DT,
                                                   "TimeStamp": DT.timestamp(), # needs checks!
                                                   "Category":  category,
                                                   "Message":   Msg["Message"]}
                    if "WILL NOT BE RESUMED" in Msg["Message"]:
                      self._list_of_not_resuming_datetimes.append(DT)
                    if Msg["Category"].upper()=="SAFETYCAR":
                      if Msg["Mode"].upper()=="SAFETY CAR":
                        if Msg["Status"].upper()=="DEPLOYED":
                          self._SafetyCar_Ranges.append([DT])
                        elif Msg["Status"].upper()=="IN THIS LAP":
                          self._SafetyCar_Ranges[-1].append(DT)
        else: # TODO: update this
          DT=msg_decrypted[list(msg_decrypted.keys())[0]]
      except Exception as err:
        self._logger.exception(err)
        self._logger_file.write("\n")
        self._logger_file.flush()
        
  def get_number_of_restarts(self):
    """ 
      Dunno if this works. Use it with caution.
    """
    with self._lock:
      return self._Nof_Restarts
  
  def get_actual_session_status(self,DT: datetime.datetime):
    """ 
      Dunno if this works. Use it with caution. Probably better to see updaters in GUI.
    """
    with self._lock:
      # For replay live timing we have all the data available.
      # So we know if the given time is inside a running window...
      for session,nr_of_restarts_dict in self._RunningStatus.items():
        for nr_of_restart,Times in nr_of_restarts_dict.items():
          if Times["EndDateTime"]!=None:
            if DT.timestamp()>Times["StartDateTime"].timestamp() and DT.timestamp()<Times["EndDateTime"].timestamp():
              return Times["Type"]
          else:
            return self._LiveSessionStatus
      return "Off"
      
  def get_passed_time_into_session(self,DT: datetime.datetime):
    """ 
      Dunno if this works. Use it with caution.
    """
    with self._lock:
      time_passed=0
      for n_session,session_dict in self._RunningStatus.items():
        time_passed=0
        for n_restart,timing_info in session_dict.items():
          if timing_info["EndDateTime"]!=None:
            if DT.timestamp()>=timing_info["StartDateTime"].timestamp():
              if DT.timestamp()<=timing_info["EndDateTime"].timestamp():
                return time_passed+DT.timestamp()-timing_info["StartDateTime"].timestamp()
              else:
                time_passed+=timing_info["Duration"]
            else:
              return time_passed
          else:
            return time_passed+(DT.timestamp()-timing_info["StartDateTime"].timestamp())
      return time_passed
          
  def is_first_RD_arrived(self):
    with self._lock:
      return self._is_first_RD_msg
  
  def is_merge_ended(self):
    with self._lock:
      return self._is_merge_ended
  
  def get_driver_tyres(self,driver: str,sel_time: datetime.datetime):
    """ 
      Returns [Compound (string), isNew (bool), stint_nr (string, convertible to int), something related to the actual lap [it can be modified to return basically whatever one wants] (int)]
    """
    with self._lock:
      sel_lap=None
      if driver in self._Laps.keys() and driver in self._Tyres.keys():
        for lap,info_lap in self._Laps[driver].items():
          if sel_time.timestamp()-info_lap["DateTime"].timestamp()>0:
            sel_lap=int(lap)
            sel_stint=str(info_lap["Stint"])
          else:
            break
        if sel_lap==None:
          return["-","-","-","-"]
        if sel_stint in self._Tyres[driver].keys():
          info_stint=self._Tyres[driver][sel_stint]
          return [info_stint["Compound"],info_stint["New"],sel_stint,sel_lap-info_stint["StartingLap"]+info_stint["CompoundAge"]]
        #for stint,info_stint in self._Tyres[driver].items():
        #  if sel_lap >= info_stint["StartingLap"] and sel_lap <= info_stint["EndingLap"]:
        #    return [info_stint["Compound"],info_stint["New"],stint,sel_lap-info_stint["StartingLap"]+info_stint["CompoundAge"]]
        ####if driver in self._last_tyres_fitted.keys():
        ####  return self._last_tyres_fitted[driver]
        #print("Cannot find lap number ",sel_lap," in Tyres dict for driver: ",driver," !")
      return ["Unknown","Unknown","Unknown","Unknown"]
  
  def get_slice_between_times(self,start_time: datetime.datetime,end_time: datetime.datetime,update_DB_flag: bool=False,driver: str=""):
    """ 
      Return a slice. It is found from telemetry dict (CarData.z).
      The returned slice starts from the first index just after (or equal to, very improbable) start_time and 
      finishes at the first index just before (or equal to, very improbable) end_time.
      
      TLDR: all the indices inside the [start_time,end_time] window.
    """
    
    # DANGEROUS! It is outside of the lock! You can call this method with update_DB_flag on True only (ONLY!) if  
    # lock is already active and remains active until the return of this method! Otherwise you can end with the list chaning
    # while is is looping over it and it will crash.
    if update_DB_flag:
      if driver not in self._last_cardata_index_checked.keys():
        self._last_cardata_index_checked[driver]=0
      first_index_flag=True
      for index,Time in zip(range(self._last_cardata_index_checked[driver],len(self._sample_cardata_list)),self._sample_cardata_list[self._last_cardata_index_checked[driver]:]): 
        #print("\t\t",Time)
        if first_index_flag and Time.timestamp()>=start_time.timestamp():
          self._last_racedata_starting_index_found=index
          first_index_flag=False
          #print("\n\n OK \n\n")
        elif Time.timestamp()>=end_time.timestamp():
          break
      self._last_cardata_index_checked[driver]=index-10    
      return slice(self._last_racedata_starting_index_found,index)
    
    with self._lock:
      if not update_DB_flag:
        first_index_flag=True
        for index,Time in enumerate(self._sample_cardata_list): 
          if first_index_flag and Time.timestamp()>=start_time.timestamp():
            self._last_racedata_starting_index_found=index
            first_index_flag=False
          elif Time.timestamp()>=end_time.timestamp():
            return slice(self._last_racedata_starting_index_found,index)

        return slice(self._last_racedata_starting_index_found,index)

  def get_race_messages_before_time(self,sel_time: datetime.datetime):
    """ 
      Return a string with every race msg before sel_time. Each msg is separated from the following 
      with a double '\ n'
    """
    with self._lock:
      msgs=""
      for msg_nr,msg_content in self._RaceMessages.items(): # Time TimeStamp Category Message
        if msg_content["Time"].timestamp()-sel_time.timestamp()<0:
          msgs += msg_nr + " - " + msg_content["Time"].strftime("%H:%M:%S") + " - " + msg_content["Category"].split("_")[-1] + " : " + msg_content["Message"] +" \n\n" 
        else:
          return msgs
      return msgs

  def get_position_index_before_time(self,sel_time: datetime.datetime):
    """ 
      Not used anymore after timing 2.0
    """
    with self._lock:
      if sel_time.timestamp()-self._last_datetime_checked_position.timestamp()>0:
        for index,Time in zip(range(self._last_position_index_found,len(self._sample_position_list)),self._sample_position_list[self._last_position_index_found:]):
          if Time.timestamp()-sel_time.timestamp()<0:
            self._last_position_index_found=index
            self._last_datetime_checked_position=Time
          else:
            break
        return self._last_position_index_found
      else:
        for index,Time in enumerate(self._sample_position_list): 
          if Time.timestamp()-sel_time.timestamp()<0:
            self._last_position_index_found=index
            self._last_datetime_checked_position=Time
          else:
            break
        return self._last_position_index_found
    # check if sel_time>last_time_check -> start from last_index_found the search in THE list
    # otherwise do this above

  def get_last_msg_before_time(self,feed: str,sel_time: datetime.datetime): # returns last index for position!
    """ 
      Return last msg sent before sel_time. Only 'Weatherdata' and 'RaceControlMessages' are available as feed.
    """
    with self._lock:
      if feed=="WeatherData":
        s_it={}
        for DT,ITEM in self._Weather.items():
          #print(DT,sel_time)
          #DT=DT.replace(tzinfo=self._utc)
          if DT.timestamp()-sel_time.timestamp()<0:
            s_DT=DT
            s_it=ITEM
          else:
            return s_it
        return {}
      elif feed=="RaceControlMessages":
        msg=""
        for msg_nr,msg_content in self._RaceMessages.items(): # Time TimeStamp Category Message
          if msg_content["Time"].timestamp()-sel_time.timestamp()<0:
            msg = msg_nr + " - " + msg_content["Time"].strftime("%H:%M:%S") + " - " + msg_content["Category"].split("_")[-1] + " : " + msg_content["Message"] +" \n\n" 
          else:
            return msg
        return msg
      else:
        print(feed, " not in get_last_msg_before_time")
        return {}

  def get_dictionary(self,feed: str):
    """ 
      Return the whole dict for the selected feed from the database.
    """
    with self._lock:
      if feed=="CarData.z":
        return self._CarData
      elif feed=="Position.z":
        return self._Position
      elif feed=="TimingDataF1":
        return self._Laps
      elif feed=="WeatherData":
        return self._Weather
      elif feed=="SessionStatus":
        return self._RunningStatus
      elif feed=="RaceControlMessages":
        return self._RaceMessages
      elif feed=="TimingAppData":
        return self._Tyres
      elif feed=="PositionSC.z":
        return self._Position_SC
      else:
        return None
  
  def get_drivers_list(self):
    with self._lock:
      return self._drivers_list
  
  def get_first_datetime(self):
    """ 
      Return first datetime (UTC) or None if no msg has arrived
    """
    with self._lock:
      return self._first_datetime # None if no msgs have arrived
  
  def get_last_datetime(self):
    """ 
      Last datetime from the cardata.z feed in UTC
    """
    with self._lock:
      return self._last_datetime # last message's datetime

  def get_base_timestamp(self):
    """ 
      First msg in timestamp
    """
    with self._lock:
      return self._DT_BASETIME_TIMESTAMP # First message's in timestamp

  def find_DT_BASETIME(self,YEAR: str,NAME: str,SESSION: str):
    """ 
      Not used anymore. It extrapolated 00:00:00.000 from HeartBeat module. 
      Unfortunately I found that it is not compatible with the 00:00:00.000 found from position.z/cardata.z feed
    """
    with self._lock:
      feed,DT_utc,DT_passed=self._parser.jsonStream_parser(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FEED="Heartbeat")
      date_splitted=DT_passed.strftime(format="%H:%M:%S.%f").split(":")
      sec_from_first_heartbeat_message=int(date_splitted[0])*3600+int(date_splitted[1])*60+float(date_splitted[2])
      self._DT_BASETIME=DT_utc-datetime.timedelta(seconds=sec_from_first_heartbeat_message)
      self._DT_BASETIME_TIMESTAMP=self._DT_BASETIME.timestamp()
      print("\n BaseTime: ",self._DT_BASETIME," \n")
      return self._DT_BASETIME
    
  def get_DT_Basetime(self):
    with self._lock:
      return self._DT_BASETIME
  
  def get_DT_Basetime_timestamp(self):
    with self._lock:
      return self._DT_BASETIME_TIMESTAMP
  
  def merger(self,YEAR: str,NAME: str,SESSION: str):
    """
    Brief:
      Loops over feeds_list, retrieve the response for each feed
      and updates database.

    Args:
      YEAR (str): year of session (eg '2023')
      NAME (str): name of event (eg 'Bahrain_Grand_Prix')
      SESSION (str): name of session (eg 'race')
    
    Returns:
      Nothing. It sets: _is_merge_ended flag to True when it finishes. In the process it fills _list_of_msgs list.
    """
    #self._parser._DT_BASETIME=self.find_DT_BASETIME(YEAR=YEAR,NAME=NAME,SESSION=SESSION)
    print("Starting the merge..")
    for feed in self._feed_list:
      print("Preparing the merge of feed: ", feed, "...",end="")
      F_L=self.feed_list(feed=feed,YEAR=YEAR,NAME=NAME,SESSION=SESSION)
      print("Length of list_of_msgs before adding: ", len(self._list_of_msgs),". Length of feed ",feed,": ",len(F_L))
      if F_L!=-1:
        for msg in F_L:
          self._list_of_msgs.append(msg)
          self.update_database(msg_decrypted={msg[2]:msg[1]},feed=msg[0])
        print(" Done!")
      if feed=="CarData.z":
        self._last_datetime=msg[2]
        print("Last Datetime: ",self._last_datetime)
      print("Length of list_of_msgs after adding: ", len(self._list_of_msgs))
    print("Sorting the list...",end="")
    self._list_of_msgs.sort(key=lambda x: x[2])
    print(" ended!")
    #for ind,content in enumerate(self._list_of_msgs):
    #  if content[0]=="Position.z":
    #    print("First Position.z at index: ",ind," of: ",len(self._list_of_msgs), " with a DT of: ",content[2])
    #    print("First CarData.z at index: ",0," of: ",len(self._list_of_msgs), " with a DT of: ",self._list_of_msgs[0][2])
    #    break
    self._is_merge_ended=True

  def detect_session_type(self,first_datetime):
    """ 
      Loop over the api and return the detected session from the datetime given. 
      If it is not inside the session it detects the closer session available. 
    """
    print(first_datetime)
    for season in self._available_years:
      print("Checking year: ",season)
      events_query="events?season="+season
      events_url="/".join([self._base_url,self._eventListing_url,events_query])
      events_request=requests.get(events_url, headers=self._headers)
      if events_request.ok:
        events=events_request.json()["events"]
        for event in events:
          if "type" in event.keys():
            if event["type"].lower()=="race":
              start_DT=arrow.get(event["meetingStartDate"]).datetime-datetime.timedelta(hours=int(event["gmtOffset"].split(":")[0]))-datetime.timedelta(hours=2) # just to include Practice 1 if the live timing data inflow starts some minutes before the first official datetime's session! 
              end_DT=arrow.get(event["meetingEndDate"]).datetime-datetime.timedelta(hours=int(event["gmtOffset"].split(":")[0]))
              if (first_datetime-start_DT).total_seconds()>0 and (first_datetime-end_DT).total_seconds()<0:
                event_name=event["meetingOfficialName"]
                meeting_key=event["meetingKey"]
                meeting_name=event["meetingName"]
                self._meeting_country_name=event["meetingCountryName"]
                timetables_query="timetables?meeting="+event["meetingKey"]+"&season="+season
                timetables_url="/".join([self._base_url,self._sessionResults_url,timetables_query])
                proceed_flag=True
                break
              else:
                proceed_flag=False
          else:
            proceed_flag=False
        if proceed_flag:
          sessions=requests.get(timetables_url, headers=self._headers).json()["timetables"]
          max_time=1e9
          for session in sessions:
            start_DT=arrow.get(session["startTime"]).datetime-datetime.timedelta(hours=int(session["gmtOffset"].split(":")[0]))
            end_DT=arrow.get(session["endTime"]).datetime-datetime.timedelta(hours=int(session["gmtOffset"].split(":")[0]))
            if (first_datetime-start_DT).total_seconds()>=0 and (first_datetime-end_DT).total_seconds()<=0:
              if "day" in session["description"].lower():
                session_name_api="practice "+session["description"].split(" ")[-1]
              elif "shootout" in session["description"].lower():
                session_name_api="-".join(session["description"].lower().split(" "))
              else:
                session_name_api=session["description"].lower()
              session_name=session["description"]
              inside_outside="inside the event!"
              self._session_start_DT=start_DT
              print("Session found! It is ",inside_outside," \nSession: ",session_name, "of ", event_name,". \n Meeting Key: ",meeting_key)
              return session_name,event_name,meeting_key,season,meeting_name,session_name_api
            else:
              if abs((first_datetime-start_DT).total_seconds())<max_time and (first_datetime-end_DT).total_seconds()<=0:
                max_time=abs((first_datetime-start_DT).total_seconds())
                if "day" in session["description"].lower():
                  session_name_api="practice "+session["description"].split(" ")[-1]
                elif "shootout" in session["description"].lower():
                  session_name_api="-".join(session["description"].lower().split(" "))
                else:
                  session_name_api=session["description"].lower()
                session_name=session["description"]
                self._session_start_DT=start_DT
                inside_outside="close to the event, just "+str(round(max_time/60.))+" minutes away from the start!"
                print(session["description"]," ",abs((first_datetime-start_DT).total_seconds())," ",(first_datetime-end_DT).total_seconds())
          print("Session found! It is ",inside_outside," \nSession: ",session_name, "of ", event_name,". \n Meeting Key: ",meeting_key, "\n Meeting Name: ",meeting_name)
          return session_name,event_name,meeting_key,season,meeting_name,session_name_api
      print("...failed search. Passing to next year!")
    print("Session not found! There is evidently a problem since you are seeing data from a session...")    
    return "Unknown","Unknown","Unknown","Unknown","Unknown","Unknown"

  def get_session_type(self):
    with self._lock:
      return self._detected_session_type
  
  def get_event_name(self):
    with self._lock:
      return self._event_name
  
  def get_meeting_key(self):
    with self._lock:
      return self._meeting_key
  
  def get_year(self):
    with self._lock:
      return self._year
  
  def get_meeting_name(self):
    with self._lock:
      return self._meeting_name
  
  def get_meetingCountry_name(self):
    with self._lock:
      return self._meeting_country_name
    
  def update_drivers_list_from_api(self):
    """ 
      Used for live replays. Sometimes the first cardata.z msgs contain wrong drivers inside.
      Example: jeddah 2024 during the race the first msgs contain Sainz (55) instead of Bearman (38).
      This is more reliable instead. 
      
      As of now, it is not used for live since this endpoint stores the final ranking and it is created
      once the session is finished.  
    """
    with self._lock:
      base_url="https://api.formula1.com/v1/fom-results/"
      query_url =self._session_name_api.split(" ")[0]+"?meeting="+str(self._meeting_key)+"&season="+str(self._year)+"&session="
      session_num="1"
      for char in self._session_name_api:
        if char.isdigit():
          session_num=str(char)
          break
      final_url=base_url+query_url+session_num
      results_request=requests.get(final_url, headers=self._headers)
      keyDict_parts=[word.capitalize() for word in self._session_name_api.replace("-"," ").split(" ")]
      keyDict="raceResults"+"".join(keyDict_parts)
      if results_request.ok:
        if keyDict in results_request.json().keys():
          results=results_request.json()[keyDict]["results"]
          for driver_dict in results:
            driverTLA=driver_dict["driverTLA"]             # Three char abbreviation
            teamColourCode=driver_dict["teamColourCode"]   # HEX
            teamName=driver_dict["teamName"]               # Full name
            racingNumber=driver_dict["racingNumber"]       # eg 28
            driverFirstName=driver_dict["driverFirstName"] # Full name
            driverLastName=driver_dict["driverLastName"]   # Full surname 
            self._drivers_list_api.append(racingNumber)
        else:
          print("Wrong keyDict: ",keyDict," . Components: ",keyDict_parts)
      
  def get_drivers_list_from_api(self):
    with self._lock:
      self._drivers_list_api.sort()
      return self._drivers_list_api
      
  def isSC_deployed(self,sel_time: datetime.datetime):
    with self._lock:
      for SC in self._SafetyCar_Ranges:
        if len(SC)==1:
          startingTime=SC[0]
          if sel_time.timestamp()-startingTime.timestamp()>0:
            return True
        elif len(SC)==2:
          startingTime = SC[0]
          endingTime   = SC[1]
          if sel_time.timestamp()-startingTime.timestamp()>0 and sel_time.timestamp()-endingTime.timestamp()<0:
            return True
        else:
          print("Length of Safety Car ranges elements is neither 0 or 1 but: ",len(SC))
      return False
  
  def get_position_index_before_time_SC(self,sel_time: datetime.datetime):    
    with self._lock:
      if self._sample_driver_SC in self._Position_SC.keys():
        if sel_time.timestamp()-self._Position_SC[self._sample_driver_SC]["Range"][0].timestamp()>0 and sel_time.timestamp()-self._Position_SC[self._sample_driver_SC]["Range"][1].timestamp()<0:
          if sel_time.timestamp()-self._last_datetime_checked_position_SC.timestamp()>0:
            for index,Time in zip(range(self._last_position_index_found_SC,len(self._sample_position_list_SC)),self._sample_position_list_SC[self._last_position_index_found_SC:]):
              if Time.timestamp()-sel_time.timestamp()<0:
                self._last_position_index_found_SC=index
                self._last_datetime_checked_position_SC=Time
              else:
                break
            return self._last_position_index_found_SC
          else:
            for index,Time in enumerate(self._sample_position_list_SC): 
              if Time.timestamp()-sel_time.timestamp()<0:
                self._last_position_index_found_SC=index
                self._last_datetime_checked_position_SC=Time
              else:
                break
            return self._last_position_index_found_SC
  
  def get_first_startingSession_DT(self):
    with self._lock:
      TD=300.
      print("Session starting at: ",self._session_start_DT ,"  but returning: ",self._session_start_DT - datetime.timedelta(seconds=TD) )
      return self._session_start_DT - datetime.timedelta(seconds=TD) 
      
  def get_list_of_msgs(self):
    with self._lock:
      return self._list_of_msgs
  
  def append_msg_to_full_list(self,msg):
    with self._lock:
      self._list_of_msgs.append(msg)