import asyncio
import concurrent.futures
import requests
import time
from config import _config
import arrow
import base64,json


from fastf1.signalr_aio import Connection

#import fastf1


class SignalRClient:
  """ Base structure taken from FAST-F1 package. 
      Updated with additional checks when receiving messages.
  """
  def __init__(self, filename: str, timeout: int = 20):

    self.headers = {'User-agent': 'BestHttp',
            'Accept-Encoding': 'gzip, identity',
            'Connection': 'keep-alive, Upgrade'}

    #self.topics = ["Heartbeat", "CarData.z", "Position.z",
    #         "ExtrapolatedClock", "TopThree", "RcmSeries",
    #         "TimingStats", "TimingAppData",
    #         "WeatherData", "TrackStatus", "DriverList",
    #         "RaceControlMessages", "SessionInfo",
    #         "SessionData", "LapCount", "TimingData"]
    
    self.topics=_config.FEED_LIST

    self.database = _config.DATABASE
    self.parser= self.database._parser
    self._connection_url = _config.LS_URL
    self._first_connection_time = 0
    self._timeout_restart=7200-60*10 #after 2 hours it will restart.
    self.is_first_msg=True
    # TODO: Save LS in a file with correct name.
    self._drivers_list_downloaded=False
    self.filename = filename
    self.filemode = "w"
    self.timeout = timeout
    self._connection = None

    self._output_file = None
    self._t_last_message = time.time()
    self.logger=_config.LOGGER # should work.. check after
    self.debug=False
    self._verbose = _config.SUPERVISE_VERBOSE 
    _config.EMPTY_LOGGER() 
    
    self._prev_msgs_datetime=[]
    self._is_already_inserted = False
    self.LENGTH_QUEUE_MSGS = _config.QUEUE_LENGTH_LS

  def _to_file(self, msg):
    self._output_file.write(msg + '\n')
    self._output_file.flush()

  def _to_terminal(self,msg):
    print(msg)
  
  async def _on_do_nothing(self, msg):
    # just do nothing with the message; intended for debug mode where some
    # callback method still needs to be provided
    pass

  def _sort_msg(self,msg):
    if not self._drivers_list_downloaded:
      if msg[0]=="CarData.z" or msg[0]=="Position.z":
        DR_EX=json.loads(self.parser.pako_inflate_raw(base64.b64decode(msg[1])).decode('utf-8'))
        self._drivers_list_downloaded=self.parser.extract_drivers_list(DR_EX)
        self.database._DT_BASETIME=arrow.get(msg[2])
        self.database._DT_BASETIME_TIMESTAMP=arrow.get(msg[2]).timestamp()
    else:
      #print(msg_to_send)
      self._is_already_inserted=False
      CURR_DT=arrow.get(msg[2]).datetime
      #print(CURR_DT," ",msg)
      if len(self._prev_msgs_datetime)>=self.LENGTH_QUEUE_MSGS:
        msg_to_send=self._prev_msgs_datetime.pop(0)[1]
        msg_parsed=self.parser.live_parser(feed=msg_to_send[0],line=msg_to_send[1],date=msg_to_send[2])
        if msg_to_send[0][-2:]==".z":
          #print(msg_parsed)
          for MSG in msg_parsed:
            self.database.append_msg_to_full_list(MSG)
            #print("\n",MSG)
            self.database._last_datetime=MSG[2]
            self.database.update_database(msg_decrypted={MSG[2]:MSG[1]},feed=MSG[0])
        else:
          self.database.append_msg_to_full_list(msg_parsed)
          self.database.update_database(msg_decrypted={msg_parsed[2]:msg_parsed[1]},feed=msg_parsed[0])
        #print("A",CURR_DT," ",msg_to_send)
      else:
        self._prev_msgs_datetime.append([CURR_DT,msg])
        #print("B",CURR_DT," ",msg)
        if self.is_first_msg:
          self.database._first_datetime=CURR_DT
          self.database._BaseTimestamp=CURR_DT.timestamp()
          #self.database._detected_session_type,self.database._event_name,self.database._meeting_key,self.database._year,self.database._meeting_name,self.database._session_name_api = self.database.detect_session_type(CURR_DT)
          #self.database.retrieve_dictionaries()
          self.is_first_msg=False
      for index in range(len(self._prev_msgs_datetime)):
        if CURR_DT < self._prev_msgs_datetime[index][0]:
            self._prev_msgs_datetime.insert(index,[CURR_DT,msg])
            self._is_already_inserted=True
            break
      if not self._is_already_inserted:
        self._prev_msgs_datetime.append([CURR_DT,msg])
  
  async def _on_print(self, msg):
    """
        Brief: Handles connection to server
    """
    print(msg)
  
  
  async def _on_status_recap(self, **data):
    """ 
        Handles the first recap message with "R"
    """
    #print(data)
    #msg_json=json.loads(data)
    if "R" in data.keys():
      if "ExtrapolatedClock" in data["R"].keys():  
        self.database._DT_BASETIME=arrow.get(data["R"]["ExtrapolatedClock"]["Utc"])
        self.database._DT_BASETIME_TIMESTAMP=arrow.get(data["R"]["ExtrapolatedClock"]["Utc"]).timestamp()
      if "DriverList" in data["R"].keys() and "Heartbeat" in data["R"].keys():
        drvs_list=[nr for nr in data["R"]["DriverList"].keys() if nr.isdigit()]
        current_DT=arrow.get(data["R"]["Heartbeat"]["Utc"]).datetime
        self.database.update_drivers_list(current_DT,drvs_list)
        self._drivers_list_downloaded=True
      for feed,value in data["R"].items():  
        if feed not in ["CarData.z","Position.z","DriverList"]:
          self.database.initialize_liveFeeds_to_currentSituation(feed,value)
      #    self.database.update_database(msg_decrypted={arrow.utcnow().datetime:value},feed=feed)
      #    # this works but create a specific function in database to handle this message appearing at the beginning!
      #    # furthemore create a flag that handles this message just the first time and than stops checking the "R" in data.keys()
      #    #print(feed," ",type(value)," ",arrow.utcnow().datetime)
  
  async def _on_message(self, msg):
    """
        Brief: Handles connection to server
    """
    self._t_last_message = time.time()
    loop = asyncio.get_running_loop()
    try:
      with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(
          pool, self._sort_msg, msg)
        await loop.run_in_executor(
          pool, self._to_file, str(msg))    
        await loop.run_in_executor(
          pool, self._on_print, str(msg))                              
    except Exception as err:
      _config.WRITE_EXCEPTION(err)

  async def _on_debug(self, **data):
    if 'M' in data and len(data['M']) > 0:
      self._t_last_message = time.time()
    #elif "R" in data and len(data["R"]) > 0:
    #  print(data)
    #  # self._sort_msg(json.load(data)["R"])

    loop = asyncio.get_running_loop()
    try:
      with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(
          pool, self._to_file, str(data)
        )
    except Exception:
      self.logger.exception("Exception while writing message to file")

  async def _run(self):
    """
        Brief: Handles connection to server
    """
    self._output_file = open(self.filename, self.filemode)
    # Create connection
    session = requests.Session()
    session.headers = self.headers
    self._connection = Connection(self._connection_url, session=session)
    self._first_connection_time=time.time()
    print("Connection started at: ",self._first_connection_time)
    # Register hub
    hub = self._connection.register_hub('Streaming')

    if self.debug:
      # Assign error handler
      self._connection.error += self._on_debug
      # Assign debug message handler to save raw responses
      self._connection.received += self._on_debug
      hub.client.on('feed', self._on_do_nothing)  # need to connect an async method
    else:
      # Assign hub message handler
      hub.client.on('feed', self._on_message) # here it passes msg in this function self._on_message
      self._connection.received += self._on_status_recap
      #hub.client.on('feed', self._on_print)
    #try:
    hub.server.invoke("Subscribe", self.topics)
    #print(self._connection.received._handlers)
    #except Exception as e:
    #  print("An error occurred while subscribing to topics:", e)
    #  hub.server.invoke("Subscribe", self.topics.remove("LapCount"))

    # Start the client
    self.loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
      await self.loop.run_in_executor(pool, self._connection.start)

  async def _supervise(self):
    #self._t_last_message = time.time()
    i=0
    while True:
      if (   (self.timeout != 0 and time.time() - self._t_last_message > self.timeout) 
          or (time.time() - self._first_connection_time > self._timeout_restart and self._first_connection_time!=0) ):
        self.logger.warning(f"Timeout - received no data for more "
                  f"than {self.timeout} seconds!")
        self._first_connection_time=0
        self._t_last_message=0
        self._connection.close()
        return
      #elif int(time.time()-self._t_last_message)%self._verbose==0:
      #  print("{0}s passed without messages...".format(i*self._verbose))
      #  i+=1
      await asyncio.sleep(1)

  async def _async_start(self):
    await asyncio.gather(asyncio.ensure_future(self._supervise()),
               asyncio.ensure_future(self._run()))
    self._output_file.close()
    self.logger.warning("Exiting...")

  async def start_async(self):
    """Connect to the data stream and start writing the data to a file."""
    try:
      while True:
        print("Started listening..")
        await self._async_start()
        print("finished! Closing all..\n Restarting...")
    except KeyboardInterrupt:
        self.logger.warning("Keyboard interrupt - exiting...")
        return

  def start(self):
        """Start the asyncio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            asyncio.run(self.start_async())
        finally:
            loop.close()
#if __name__ == '__main__':
#    client = SignalRClient(filename="0710-SprintRace.txt")
#    client.start()

