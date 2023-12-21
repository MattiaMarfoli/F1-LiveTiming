import PARSER
import Analyzer
import datetime
import threading
import logging

class DATABASE:
  """
  
  
  
  """
  
  def __init__(self,FEED_LIST: str,logger: logging,logger_file):

    self._parser=PARSER.PARSER()
    self._analyzer=Analyzer.analyzer()
    self._feed_list=FEED_LIST
    self._logger=logger
    self._logger_file=logger_file
    
    self._lock= threading.Lock()
    self._first_datetime   = None
    self._last_datetime    = None
    self._BaseTimestamp    = None
    self._is_first_RD_msg  = False
    self._is_merge_ended   = False
    self._Display_LapTimes = False
    
    self._drivers_list = None
    self._drivers_list_provisional = set()
    self._CarData={}
    self._Position={}
    self._LeaderBoard={}
    self._Laps={}
    self._Weather={}
    self._Laps[None]={}
    
    
  def get_feeds(self):
    """
    Brief:
      Returns a list of feeds
    """
    return list(self._parser._feeds.keys())

  def feed_dictionary(self,feed: str,YEAR: str,NAME: str,SESSION: str):
    """
    Brief:
      Basically overrides jsonStream_parser of Parser class.
    """
    f_dict=self._parser.jsonStream_parser(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FEED=feed)
    if f_dict!=-1:
      return f_dict
    else:
      return -1 

  def update_database(self,msg_decrypted: dict,feed: str): # lock
    """
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

    """
    with self._lock:
      #print(self._first_datetime," ",self._BaseTimestamp)
      try:
        if feed=="CarData.z":
          for DT,RD in msg_decrypted.items():
            #print(self._first_datetime," ",DT," ",msg_decrypted.keys())
            if self._first_datetime==None:
              self._first_datetime=DT
              self._BaseTimestamp=DT.timestamp()
              #print(DT.timestamp()," ",self._BaseTimestamp)
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
              self._CarData[driver]["Time"].append(DT)
              self._CarData[driver]["TimeStamp"].append(DT.timestamp()-self._BaseTimestamp)
              self._CarData[driver]["RPM"].append(channels["Channels"]["0"])
              self._CarData[driver]["Speed"].append(channels["Channels"]["2"])
              self._CarData[driver]["Gear"].append(channels["Channels"]["3"])
              self._CarData[driver]["Throttle"].append(channels["Channels"]["4"] if channels["Channels"]["4"]<101 else 0)
              self._CarData[driver]["Brake"].append(int(channels["Channels"]["5"]) if int(channels["Channels"]["5"])<101 else 0)
              self._CarData[driver]["DRS"].append(1 if channels["Channels"]["45"]%2==0 else 0)
              #print(self._CarData[driver].keys())
            self._is_first_RD_msg=True
          #print(self._drivers_list,self._drivers_list_provisional)
          if self._drivers_list==None:
            self._drivers_list=list(self._drivers_list_provisional)
            self._drivers_list.sort()
        elif feed=="Position.z":
          for DT,P in msg_decrypted.items():
            if DT.timestamp()-self._BaseTimestamp<0:
              print(DT, " in Position.z in update_database is discarded: message sent before the first CarData message!")
            else:
              for DRIVER,P_dict in P.items():
                if DRIVER not in self._Position.keys():
                    self._Position[DRIVER]={}
                    self._Position[DRIVER]["Time"]=[]
                    self._Position[DRIVER]["TimeStamp"]=[]
                    self._Position[DRIVER]["XYZ"]=[]
                self._Position[DRIVER]["Time"].append(DT)
                self._Position[DRIVER]["TimeStamp"].append(DT.timestamp()-self._BaseTimestamp)
                self._Position[DRIVER]["XYZ"].append([P_dict["X"],P_dict["Y"],P_dict["Z"]])
                #print(DRIVER," ",P_dict["X"],P_dict["Y"],P_dict["Z"])
        elif feed=="TimingDataF1":
          for DT,TDF1 in msg_decrypted.items():
            for LAP in TDF1:
              #print(LAP)
              driver=LAP[0]
              NLap=LAP[1]
              Value=LAP[2]
              if self._Display_LapTimes:
                print(driver,NLap,Value)
              if driver not in self._Laps:
                self._Laps[driver]={}
              mins,secs=Value.split(":")
              Value_int=int(mins)*60. + float(secs) # s
              self._Laps[driver][NLap]={"DateTime":       DT, 
                                        "ValueString":    Value,
                                        "ValueInt_sec":   Value_int,
                                        "TimeStamp": DT.timestamp()-self._BaseTimestamp}
        elif feed=="WeatherData":
          for DT,WeatherDict in msg_decrypted.items():
            self._Weather[DT]=WeatherDict    
          #for key,value in a.items():
          #  if "Lines" in value.keys():
          #    for lines,lines_value in value.items():
          #      if lines!="Withheld":
          #      #print(key,lines,lines_value)
          #        for driver,stints in lines_value.items():
          #          if "LastLapTime" in stints.keys() and "NumberOfLaps" in stints.keys():
          #            if driver not in b.keys():
          #              b[driver]={}
          #            
          #            b[driver][stints["NumberOfLaps"]]=stints["LastLapTime"]["Value"]

        #elif feed=="DriverList" and self._driver_list_flag==False:
        #  self._driver_list=
        else: # TODO: update this
          DT=msg_decrypted[list(msg_decrypted.keys())[0]]
        self._last_datetime=DT
      except Exception as err:
        self._logger.exception(err)
        self._logger_file.write("\n")
        self._logger_file.flush()
        
      
  
  def is_first_RD_arrived(self):
    with self._lock:
      return self._is_first_RD_msg
  
  def is_merge_ended(self):
    with self._lock:
      return self._is_merge_ended
  
  def get_slice_between_times(self,feed: str,start_time: datetime.datetime,end_time: datetime.datetime):
    with self._lock:
      first_index_flag=True
      if feed=="CarData.z":
        dictionary=self._CarData
      elif feed=="Position.z":
        dictionary=self._Position
      #print("AAAA: ",dictionary[list(dictionary.keys())[0]])
      first_index=0
      for index,Time in enumerate(dictionary[list(dictionary.keys())[0]]["Time"]): # Check if CarData are given even for crashed drivers
        #print(Time, " ",start_time," ",end_time)
        #print(Time, " ",end_time)
        if first_index_flag and Time>=start_time:
          first_index=index
          self._first_index_RD=index #TODO optimization with this for next search
          first_index_flag=False
          #print(first_index)
        elif Time>=end_time:
          last_index=index # index not included so it should work like this!
          #print(first_index,last_index,slice(first_index,last_index))
          return slice(first_index,last_index)
        
      return slice(first_index,first_index)
      
      #return (self._CarData[driver]["Time"][ST_to_ET],self._CarData[driver]["RPM"][ST_to_ET],
      #        self._CarData[driver]["Speed"][ST_to_ET],self._CarData[driver]["Gear"][ST_to_ET],
      #        self._CarData[driver]["Throttle"][ST_to_ET],self._CarData[driver]["Brake"][ST_to_ET],
      #        self._CarData[driver]["DRS"][ST_to_ET])

  def get_last_msg_before_time(self,feed: str,sel_time: datetime.datetime):
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
      elif feed=="Position.z":
        s_it={}
        for Driver,P_dict in self._Position.items():
          s_XYZ=[0,0,0]
          for DT,XYZ in zip(P_dict["Time"],P_dict["XYZ"]):
            if DT.timestamp()-sel_time.timestamp()<0:
              s_XYZ=XYZ
            else:
              s_it[Driver]=s_XYZ
              break
        return s_it
      else:
        print(feed, " not in case in get_last_msg_before_time")
        return {}

  def get_dictionary(self,feed: str):
    with self._lock:
      if feed=="CarData.z":
        return self._CarData
      elif feed=="Position.z":
        return self._Position
      elif feed=="TimingDataF1":
        return self._Laps
      elif feed=="WeatherData":
        return self._Weather
      else:
        return None
  
  def get_drivers_list(self):
    with self._lock:
      return self._drivers_list
  
  def get_first_datetime(self):
    with self._lock:
      return self._first_datetime # None if still no msgs have arrived
  
  def get_last_datetime(self):
    with self._lock:
      return self._last_datetime # last message's datetime

  def get_base_timestamp(self):
    with self._lock:
      return self._BaseTimestamp # First message's in timestamp

  def merger(self,YEAR: str,NAME: str,SESSION: str):
    """
    Brief:
      Loops over feeds_list, retrieve the dictionary response for each feed
      and merge each dictionary.

    Args:
      YEAR (str): year of session (eg '2023')
      NAME (str): name of event (eg 'Bahrain_Grand_Prix')
      SESSION (str): name of session (eg 'race')
    
    Returns:
      dict: merged dictionary for all feeds in feeds_list. Sorted for time of arrival
            of the messages.
    """
    print("Starting the merge..")
    list_of_feeds=self._feed_list
    for feed in list_of_feeds:
      print("Preparing the merge of feed: ", feed, "...",end="")
      if feed in self._feed_list:
        feed_dict=self.feed_dictionary(feed=feed,YEAR=YEAR,NAME=NAME,SESSION=SESSION)
        if feed_dict!=-1:
          self.update_database(msg_decrypted=feed_dict,feed=feed)
          print("MERGED!")
        else:
          print("Failed to retrieve data..")
      else:
        print("SKIPPED!")
    self._is_merge_ended=True


  