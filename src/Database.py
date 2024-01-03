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
    self._RaceMessages = {}
    self._LiveSessionStatus="Unknown"
    self._RunningStatus={
                          #1:                       # nr of restart
                          #{
                          #  "StartDateTime": 0,
                          #  "EndDateTime":   0,    # just as an example
                          #  "Duration":      0
                          #}  
                        }
    self._Nof_Restarts=0
    self._PrevSessionDatetime=0
    self._PrevSessionStatus=0
    self._Laps[None]={}
    
    self._sample_position_list               = [] # exploiting the fact that positions data are given with the same Datetime for every driver
    self._sample_cardata_list                = [] # exploiting the fact that cardata are given with the same Datetime for every driver
    self._sample_driver                      = ""
    
    self._last_datetime_checked_position     = 0
    self._last_datetime_checked_cardata      = 0
    self._last_position_index_found          = 0
    
    self._last_racedata_starting_index_found = 0
    
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
              self._last_datetime_checked_cardata  = DT
              self._last_datetime_checked_position = DT
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
                if self._sample_driver == "":
                  self._sample_driver = driver
              self._CarData[driver]["Time"].append(DT)
              self._CarData[driver]["TimeStamp"].append(DT.timestamp()-self._BaseTimestamp)
              self._CarData[driver]["RPM"].append(channels["Channels"]["0"])
              self._CarData[driver]["Speed"].append(channels["Channels"]["2"])
              self._CarData[driver]["Gear"].append(channels["Channels"]["3"])
              self._CarData[driver]["Throttle"].append(channels["Channels"]["4"] if channels["Channels"]["4"]<101 else 0)
              self._CarData[driver]["Brake"].append(int(channels["Channels"]["5"]) if int(channels["Channels"]["5"])<101 else 0)
              self._CarData[driver]["DRS"].append(1 if channels["Channels"]["45"]%2==0 else 0)
              if driver == self._sample_driver:
                self._sample_cardata_list.append(DT)
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
                    if self._sample_driver == "":
                      self._sample_driver = DRIVER
                self._Position[DRIVER]["Time"].append(DT)
                self._Position[DRIVER]["TimeStamp"].append(DT.timestamp()-self._BaseTimestamp)
                self._Position[DRIVER]["XYZ"].append([P_dict["X"],P_dict["Y"],P_dict["Z"]])
                if DRIVER == self._sample_driver:
                  self._sample_position_list.append(DT)
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
            
        elif feed=="SessionStatus": # more checks needed
          for DT,Status in msg_decrypted.items():
            # if finished => before was running. Updating dict
            if Status["Status"]=="Finished" or Status["Status"]=="Aborted" or Status["Status"]=="Finalised" or Status["Status"]=="Ends":
              if self._Nof_Restarts==0:
                self._PrevSessionDatetime=self._first_datetime
                self._Nof_Restarts=1
              self._LiveSessionStatus="Inactive"    
              self._RunningStatus[self._Nof_Restarts]={}
              self._RunningStatus[self._Nof_Restarts]["StartDateTime"]=self._PrevSessionDatetime
              self._RunningStatus[self._Nof_Restarts]["EndDateTime"]=DT
              self._RunningStatus[self._Nof_Restarts]["Duration"]=DT.timestamp()-self._PrevSessionDatetime.timestamp()
            elif Status["Status"]=="Started":
                self._PrevSessionDatetime=DT
                self._Nof_Restarts+=1
                self._LiveSessionStatus="Running"    
        elif feed=="RaceControlMessages":
          for DT,Message in msg_decrypted.items():
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
        else: # TODO: update this
          DT=msg_decrypted[list(msg_decrypted.keys())[0]]
        self._last_datetime=DT
      except Exception as err:
        self._logger.exception(err)
        self._logger_file.write("\n")
        self._logger_file.flush()
        
  def get_number_of_restarts(self):
    with self._lock:
      return self._Nof_Restarts
  
  def get_actual_session_status(self,DT: datetime.datetime):
    with self._lock:
      # For replay live timing we have all the data available.
      # So we know if the given time is inside a running window...
      for Nr_of_restart,Times in self._RunningStatus.items():
        if DT.timestamp()>Times["StartDateTime"].timestamp() and DT.timestamp()<Times["EndDateTime"].timestamp():
          return "Running"
      # ...otherwise we can be in LiveTiming: then LiveSessionStatus is the way
      # or we are in replay live timing outside the window. Then all the data are 
      # processed and  the last message of SessionStatus.jsonStream is "Ends" with 
      # 100% certainty (I hope!). 
      return self._LiveSessionStatus
  
  def is_first_RD_arrived(self):
    with self._lock:
      return self._is_first_RD_msg
  
  def is_merge_ended(self):
    with self._lock:
      return self._is_merge_ended
  
  def get_slice_between_times(self,start_time: datetime.datetime,end_time: datetime.datetime):
    with self._lock:
      first_index_flag=True
      
      if start_time.timestamp()-self._last_datetime_checked_cardata.timestamp()>0:
        for index,Time in zip(range(self._last_racedata_starting_index_found,len(self._sample_cardata_list)),self._sample_cardata_list[self._last_racedata_starting_index_found:]):
          if first_index_flag and Time>=start_time:
            self._last_racedata_starting_index_found=index
            self._last_datetime_checked_cardata = Time
            first_index_flag=False
          elif Time>=end_time:
            return slice(self._last_racedata_starting_index_found,index)
     
      else:
        for index,Time in enumerate(self._sample_cardata_list): 
          if first_index_flag and Time>=start_time:
            self._last_racedata_starting_index_found=index
            self._last_datetime_checked_cardata = Time
            first_index_flag=False
          elif Time>=end_time:
            return slice(self._last_racedata_starting_index_found,index)

      return slice(self._last_racedata_starting_index_found,index)

  def get_race_messages_before_time(self,sel_time: datetime.datetime):
    with self._lock:
      msgs=""
      for msg_nr,msg_content in self._RaceMessages.items(): # Time TimeStamp Category Message
        if msg_content["Time"].timestamp()-sel_time.timestamp()<0:
          msgs += msg_nr + " - " + msg_content["Time"].strftime("%H:%M:%S") + " - " + msg_content["Category"].split("_")[-1] + " : " + msg_content["Message"] +" \n\n" 
        else:
          return msgs
      return msgs

  def get_position_index_before_time(self,sel_time: datetime.datetime):
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


  