import asyncio
import concurrent.futures
import requests
import time
from config import _config
import arrow


from fastf1.signalr_aio import Connection

import fastf1


class SignalRClient:
  """A client for receiving and saving F1 timing data which is streamed
  live over the SignalR protocol.

  During an F1 session, timing data and telemetry data are streamed live
  using the SignalR protocol. This class can be used to connect to the
  stream and save the received data into a file.

  The data will be saved in a raw text format without any postprocessing.
  It is **not** possible to use this data during a session. Instead, the
  data can be processed after the session using the :mod:`fastf1.api` and
  :mod:`fastf1.core`

  Args:
    filename: filename (opt. with path) for the output file
    filemode: one of 'w' or 'a'; append to or overwrite
      file content it the file already exists. Append-mode may be useful
      if the client is restarted during a session.
    debug: When set to true, the complete SignalR
      message is saved. By default, only the actual data from a
      message is saved.
    timeout: Number of seconds after which the client
      will automatically exit when no message data is received.
      Set to zero to disable.
    logger: By default, errors are logged to the console. If you wish to
      customize logging, you can pass an instance of
      :class:`logging.Logger` (see: :mod:`logging`).
  """
  def __init__(self, filename: str, timeout: int = 5):

    self.headers = {'User-agent': 'BestHTTP',
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
    self.is_first_msg=True
    # TODO: Save LS in a file with correct name.
    self.filename = filename
    self.filemode = "w"
    self.timeout = timeout
    self._connection = None

    self._output_file = None
    self._t_last_message = None
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

  # [x] check if this work!
  def _sort_msg(self,msg):
    #print(msg_to_send)
    self._is_already_inserted=False
    CURR_DT=arrow.get(msg[2]).datetime
    #print(CURR_DT," ",msg)
    if len(self._prev_msgs_datetime)>=self.LENGTH_QUEUE_MSGS:
      msg_to_send=self._prev_msgs_datetime.pop(0)[1]
      body_exp=self.parser.live_parser(feed=msg_to_send[0],line=msg_to_send[1],date=msg_to_send[2])
      self.database.update_database(msg_decrypted=body_exp,feed=msg_to_send[0])
      #print("A",CURR_DT," ",msg_to_send)
    else:
      self._prev_msgs_datetime.append([CURR_DT,msg])
      #print("B",CURR_DT," ",msg)
      if self.is_first_msg:
        self.database._first_datetime=CURR_DT
        self.database._BaseTimestamp=CURR_DT.timestamp()
        self.is_first_msg=False
    for index in range(len(self._prev_msgs_datetime)):
      if CURR_DT < self._prev_msgs_datetime[index][0]:
          self._prev_msgs_datetime.insert(index,[CURR_DT,msg])
          self._is_already_inserted=True
          break
    if not self._is_already_inserted:
      self._prev_msgs_datetime.append([CURR_DT,msg])
  
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
    except Exception as err:
      _config.WRITE_EXCEPTION(err)

  async def _on_debug(self, **data):
    if 'M' in data and len(data['M']) > 0:
      self._t_last_message = time.time()

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
      #hub.client.on('feed', self._on_print)
    hub.server.invoke("Subscribe", self.topics)

    # Start the client
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
      await loop.run_in_executor(pool, self._connection.start)

  async def _supervise(self):
    self._t_last_message = time.time()
    i=0
    while True:
      if (self.timeout != 0
          and time.time() - self._t_last_message > self.timeout):
        self.logger.warning(f"Timeout - received no data for more "
                  f"than {self.timeout} seconds!")
        self._connection.close()
        return
      #elif int(time.time()-self._t_last_message)%self._verbose==0:
      #  print("{0}s passed without messages...".format(i*self._verbose))
      #  i+=1
      await asyncio.sleep(1)

  async def _async_start(self):
    self.logger.info(f"Starting FastF1 live timing client "
             f"[v{fastf1.__version__}]")
    await asyncio.gather(asyncio.ensure_future(self._supervise()),
               asyncio.ensure_future(self._run()))
    self._output_file.close()
    self.logger.warning("Exiting...")

  def start(self):
    """Connect to the data stream and start writing the data to a file."""
    try:
      print("Started listening..")
      asyncio.run(self._async_start())
    except KeyboardInterrupt:
      self.logger.warning("Keyboard interrupt - exiting...")
      return

#if __name__ == '__main__':
#    client = SignalRClient(filename="0710-SprintRace.txt")
#    client.start()

