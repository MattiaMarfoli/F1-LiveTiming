import json
import requests
import zlib
import base64 
import arrow
import datetime
from config import _config, paths

class PARSER:
    """
    
    
    
    """

    def __init__(self):
      
      # Loading jsons and useful infos from config file
      self._base_url=_config.BASE_URL
      self._index_endpoint=_config.INDEX_ENDPOINT
      self._filename_feeds=_config.FILENAME_FEEDS
      self._filename_urls=_config.FILENAME_URLS
      self._feeds=json.load(open(paths.JSONS_PATH / self._filename_feeds,"r"))
      self._urls=json.load(open(paths.JSONS_PATH / self._filename_urls,"r"))
      self._years = _config.YEARS
      self._sessions_dict=self.get_sessions_dict()
      self._logger=_config.LOGGER
      self._logger_file=_config.LOGGER_FILE
      
      # Initializing 
      self._isFirstMsg = True
      self._DT_BASETIME=None
    
    def get_session_url(self,YEAR: str,NAME: str,SESSION: str):
      """ 
      Brief: 
        Returns the session URL

      Args:
        YEAR (str): year of session (eg '2023')
        NAME (str): name of event (eg 'Bahrain_Grand_Prix')
        SESSION (str): name of session (eg 'race')
      """
      KEY=YEAR+"_"+NAME.replace(" ","_")
      return self._base_url+self._urls[KEY][SESSION.replace(" ","_")]
    
    def update_urls(self):
      """
      Brief: 
        Updates in order:
        -) SESSION_URLS.json from the base_url 
        -) Reloads the new URLs in self._urls
      """
      print("Updating URLs from {0}".format(self._base_url))
      self.update_session_urls()
      self._urls=json.load(open(paths.JSONS_PATH / self._filename_urls,"r"))

    def get_sessions_dict(self):
      """
      Returns:
          dict: Dictionary with all sessions. 
                Keys in order: Year -> Race -> Sessions
      """
      sessions_dict={}
      for key in self._urls.keys():
        year=key[:4]
        race=key[5:]
        if year not in sessions_dict.keys():
          sessions_dict[year]={}
        if race not in sessions_dict[year].keys():
          sessions_dict[year][race]=[]
        for session in self._urls[key]:
          sessions_dict[year][race].append(session)
      return sessions_dict

    def get_feed(self,feed: str,type: str="json"):
      """
      Brief: 
        Returns the selected string from the FEEDS config file      

      Args:
        feed (str): feed name (eg 'SessionInfo')
        type (str, optional): 'json' (last call) or 
                              'jsonStream' (all the stream). 
                              Defaults to "json".

      Raises:
        Exception: type not supported.

      Returns:
        str: selected feed name with extension
      """
      if type=="json":
        key="KeyFramePath"
      elif type=="jsonStream":
        key="StreamPath"
      else:
        raise Exception("type (str) not 'json' or 'jsonStream' in PARSER.get_feed method!")
      return self._feeds[feed][key]
    
    def get_interesting_times(self,YEAR: str,NAME: str,SESSION: str):
      """
      NOT USED ANYMORE!
      
      Brief:
        Returns a list with interesting times in ms from the start of the stream
        if SessionStatus is categorized in either one of the following status:
          -) Started: Session is started or resumed (eg from a RedFlag)
          -) Aborted: Red Flag
          -) Finished: Chequered Flag. In quali there is a call for each quali session (Q1,Q2,Q3)
      Args:
        YEAR (str): year of session (eg '2023')
        NAME (str): name of event (eg 'Bahrain_Grand_Prix')
        SESSION (str): name of session (eg 'race')

      Returns:
        list: each entry is [time_ms,status]
      """
      time_ms_events=self.jsonStream_parser(FEED="SessionStatus",YEAR=YEAR,NAME=NAME,SESSION=SESSION)
      Int_Times=[]
      for time_ms,value in time_ms_events.items():
        status=value["SessionStatus"]["Status"]
        if status not in ["Inactive","Ends","Finalised"]:
          Int_Times.append([time_ms,status])
      return Int_Times

    def get_drivers_dict(self,YEAR: str,NAME: str,SESSION: str):
      """
      NOT USED ANYMORE!
      
      Brief:
        Return the drivers list as the last call of DriverList.json

      Args:
        YEAR (str): year of session (eg '2023')
        NAME (str): name of event (eg 'Bahrain_Grand_Prix')
        SESSION (str): name of session (eg 'race')

      Returns:
          dict: dictionary with multiple items for each driver. 
                keys method of this dict is a list with all driver numbers as strings
      """
      line = self.get_response_content(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FEED="DriverList",TYPE="json")
      drivers=self.OneLineParser(line=line,feed="DriverList")
      return drivers
    
    def get_response_content(self,YEAR: str,NAME: str,SESSION: str,FEED: str,TYPE: str="json"):
      """
      Brief:
        Response content for each feed URL

      Args:
        YEAR (str): year of session (eg '2023')
        NAME (str): name of event (eg 'Bahrain_Grand_Prix')
        SESSION (str): name of session (eg 'race')
        feed (str): feed name (eg 'SessionInfo')
        type (str, optional): 'json' (last call) or 
                              'jsonStream' (all the stream). 
                              Defaults to "json".

      Returns:
          request.get(url).content: if status_code is 200 (ok), else return -1
      """
      url=self.get_session_url(YEAR=YEAR,NAME=NAME,SESSION=SESSION)+self.get_feed(feed=FEED,type=TYPE)
      response = requests.get(url)
      if response.status_code==200:
        return response.content
      else:
        return -1
        
    def pako_inflate_raw(self,data):
      """
      Brief:
        simply decode the .z response of certain feed (eg 'RaceData.z' and 'Position.z')
      
      Args:
        data (str): encrypted message
        
      Returns:
        str: decompressed input string
      """
      decompress = zlib.decompressobj(-15)
      decompressed_data = decompress.decompress(data)
      decompressed_data += decompress.flush()
      return decompressed_data

    def live_parser(self,feed: str, line: str, date:str):
      """
      Brief: 
        Used for LiveStreaming only. See jsonStream_parser and OneLineParser methods  
        for simulated live sessions.
        Convert timestamp of the message in ms (from the start of stream)
        and decode the message if needed. For nested messages create a key for 
        each entry. 

      Args:
        feed (str): feed name
        line (str): message (depends on feed)
        date (str): timestamp (format: yyyy-mm-ddThh:mm:ss.SSSZ , read with arrow pkg)

      Returns:
        list: [string (feed), dict (msg_content), Datetime (UTC of the msg)]
      """
      try:
        if feed[-2:]==".z":
          body_exp=[]
          body=json.loads(self.pako_inflate_raw(base64.b64decode(line)).decode('utf-8'))
          for entry in body[list(body.keys())[0]]:
            time_entry=arrow.get(entry[list(entry.keys())[0]]).datetime
            body_exp.append([feed,entry[list(entry.keys())[1]],time_entry])
          return body_exp
        else:
          DT=arrow.get(date).datetime
          body_exp=line
          return [feed,body_exp,DT]    
      except Exception as err:
        _config.WRITE_EXCEPTION(err)

    def OneLineParser(self,line: str,feed: str):
      """
      Brief: 
        Used for LiveStreaming simulation only. See live_parser method for 
        live sessions.
        Divide line in time and message.
        Convert timestamp of the message in ms (from the start of stream)
        and decode the message if needed. For nested messages create an key for 
        each entry. 

        *  It also extract drivers list (altough it is now taken from another api)
           and extract the BASE_TIMESTAMP (the 'zero' 00:00:00.000 of the session) from
           the first .z message. 
      Args:
        feed (str): feed name
        line (str): containing time and message (depends on feed)
  
      Returns:
        list: [string (feed), dict (msg_content), Datetime (UTC of the msg)]
       """
      try:
        line_noBOM=line.decode("utf-8")
        if feed[-2:]==".z":
          body_exp=[]
          line_noBOM=line_noBOM.split('"')
          date=line_noBOM[0].replace("\ufeff","")
          body=line_noBOM[1]
          body=json.loads(self.pako_inflate_raw(base64.b64decode(body)).decode('utf-8'))
          if _config.DATABASE._drivers_list==None:
            self.extract_drivers_list(body)
          for entry in body[list(body.keys())[0]]:
            #print(entry[list(entry.keys())[0]])
            time_entry=arrow.get(entry[list(entry.keys())[0]]).datetime
            if self._isFirstMsg:
              sec_from_first_message=self.get_sec_from_date(date=date)
              self._DT_BASETIME = time_entry-datetime.timedelta(seconds=sec_from_first_message)
              _config.DATABASE._DT_BASETIME = time_entry-datetime.timedelta(seconds=sec_from_first_message)
              _config.DATABASE._DT_BASETIME_TIMESTAMP =  _config.DATABASE._DT_BASETIME.timestamp()
              print("\n BaseTime: ",_config.DATABASE._DT_BASETIME," \n")
              self._isFirstMsg=False
            body_exp.append([feed,entry[list(entry.keys())[1]],time_entry])
          return body_exp
        elif feed=="Heartbeat":
          line_noBOM=line_noBOM.replace("\ufeff","")
          date=datetime.datetime.strptime(line_noBOM[:12],"%H:%M:%S.%f")
          body=json.loads(line_noBOM[12:])
          first_DT=arrow.get(body["Utc"]).datetime
          return [feed,first_DT,date]
        else:
          line_noBOM=line_noBOM.replace("\ufeff","")
          date=datetime.datetime.strptime(line_noBOM[:12],"%H:%M:%S.%f")
          DateTime=self._DT_BASETIME+datetime.timedelta(hours=date.hour,minutes=date.minute,seconds=date.second,microseconds=date.microsecond)
          body=json.loads(line_noBOM[12:])
          return [feed,body,DateTime]
      except Exception as err:
        _config.WRITE_EXCEPTION(err)
    
    def get_sec_from_date(self,date: str):
      """
      Brief:
        Convert date from 'hh:mm:ss.SSS' format to seconds

      Args:
        date (str): timestamp of 'hh:mm:ss.SSS'

      Raises:
        Exception: date not in 'hh:mm:ss.SSS' format

      Returns:
        int: converted date in seconds
      """
      sec=0
      splitted_date=date.split(":")
      if len(splitted_date)==3:
        sec=int(int(splitted_date[0])*60*60 + int(splitted_date[1])*60 + float(splitted_date[2]))
      else:
         raise Exception("Date format not hh:mm:ss.SSS in PARSER.get_sec_from_date method!")
      return sec
        
    def get_ms_from_date(self,date: str):
      """
      Brief:
        Convert date from 'hh:mm:ss.SSS' format to ms

      Args:
        date (str): timestamp of 'hh:mm:ss.SSS'

      Raises:
        Exception: date not in 'hh:mm:ss.SSS' format

      Returns:
        int: converted date in ms
      """
      ms=0
      splitted_date=date.split(":")
      if len(splitted_date)==3:
        ms=int(int(splitted_date[0])*60*60*1000 + int(splitted_date[1])*60*1000 + float(splitted_date[2])*1000)
      else:
         raise Exception("Date format not hh:mm:ss.SSS in PARSER.get_ms_from_date method!")
      return ms 

    def extract_drivers_list(self,msg):
      """ 
        Extract driver list from one of the .z messages
      """
      for entry in msg[list(msg.keys())[0]]:
        for key,value in entry.items():
          if key=="Entries" or key=="Cars":
            DT=arrow.get(entry[list(entry.keys())[0]]).datetime
            _config.DATABASE.update_drivers_list(DT,list(value.keys()))
            return True
      return False


    def jsonStream_parser(self,YEAR: str,NAME: str,SESSION: str,FEED: str):
      """
      Brief:
        Loop over response content and read each line
        with OneLineParser if response content status code
        is accepted.

      Args:
        YEAR (str): year of sessmsgion (eg '2023')
        NAME (str): name of event (eg 'Bahrain_Grand_Prix')
        SESSION (str): name of session (eg 'race')
        FEED (str): feed name (eg 'SessionInfo')

      Returns:
          dict: time_ms: msg decrypted (could be a list or another dictionary,
                it depends on the feed) if response_content is accepted, otherwise
                returns -1
      """
      jsonStream_txt=self.get_response_content(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FEED=FEED,TYPE="jsonStream")
      if jsonStream_txt!=-1: 
        if FEED!="Heartbeat":
          msgs=[]
          for line in jsonStream_txt.splitlines():
            msg=self.OneLineParser(line,FEED)
            if len(msg)>0:
              if type(msg[0])==list:
                for m in msg:
                  msgs.append(m)
              else:
                msgs.append(msg)
          return msgs
        else:
          line=jsonStream_txt.splitlines()[0]
          return self.OneLineParser(line,FEED)
      else:
         return -1
    
    
    def update_session_urls(self):
      """
      Brief:
        Loop over all endopoints for each year (>=2018) and detect each session 
        URL for the event, then saves it on session_urls json file.
      """
      SESSION_URLS={}
      for YEAR in self._years:
        INDEX_URL=self._base_url+YEAR+self._index_endpoint
        response = requests.get(INDEX_URL)
        INDEX_JSON=json.loads(response.content)
        for meeting in INDEX_JSON["Meetings"]:
          print("\n\t Meeting: {0} - {1} ".format(YEAR,meeting["Name"].replace(" ","_")))
          n=0
          #if "test" not in meeting["Name"].lower():
          for session in meeting["Sessions"]:
            if "Path" in session.keys():
              RACE_DATE=session["Path"][5:15]
              RACE_DATE_FOUND=True
              break
                             
          if not RACE_DATE_FOUND:
            print("\t\t RACE DATE not found!")
          for session in meeting["Sessions"]:
            if session["Key"]!=-1:
              n+=1                
              print("\t\t Session {0}: {1}".format(n,session["Name"].replace(" ","_")))
              if YEAR+"_"+meeting["Name"].replace(" ","_") not in SESSION_URLS.keys():
                SESSION_URLS[YEAR+"_"+meeting["Name"].replace(" ","_")]={}
              PATH=YEAR+"/"+RACE_DATE+"_"+meeting["Name"].replace(" ","_")+"/"+session["StartDate"][:10]+"_"+session["Name"].replace(" ","_")+"/"
              if "Path" not in session.keys() or PATH==session["Path"]:
                SESSION_URLS[YEAR+"_"+meeting["Name"].replace(" ","_")][session["Name"].replace(" ","_")]=PATH
              elif "Path" in session.keys():
                SESSION_URLS[YEAR+"_"+meeting["Name"].replace(" ","_")][session["Name"].replace(" ","_")]=session["Path"]
              else:
                print(YEAR," ",meeting["Name"]," path not found!")
                #logger
          
      with open(paths.JSONS_PATH / self._filename_urls,"w") as outfile:
          json.dump(SESSION_URLS, outfile,indent=3)

#  https://livetiming.formula1.com/static/2023/2023-09-24_Japanese_Grand_Prix/2023-09-24_Race/CarData.z.jsonStream