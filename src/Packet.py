import asyncio
import concurrent.futures
import json
import logging
import requests
import time
from typing import Iterable, Optional, Callable

from fastf1.signalr_aio import Connection


import fastf1

import zlib
import base64
b = base64.b64encode(bytes('your string', 'utf-8')) # bytes
base64_str = b.decode('utf-8') # convert bytes to string

def decompress_time_series(data: str) -> dict:
    """Decompresses a time series data string.

    Args:
        data: A string containing the compressed time series data.

    Returns:
        A dictionary containing the decompressed time series data.
    """

    decompressed_data = zlib.decompress(base64.b64encode(bytes(data, 'utf-8')))
    return json.loads(decompressed_data.decode("utf-8"))



def messages_from_raw(r: Iterable):
    """Extract data messages from raw recorded SignalR data.

    This function can be used to extract message data from raw SignalR data
    which was saved using :class:`SignalRClient` in debug mode.

    Args:
        r: Iterable containing raw SignalR responses.
    """
    ret = list()
    errorcount = 0
    for data in r:
        # fix F1's not json compliant data
        data = data.replace("'", '"') \
            .replace('True', 'true') \
            .replace('False', 'false')
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            errorcount += 1
            continue
        messages = data['M'] if 'M' in data and len(data['M']) > 0 else {}
        for inner_data in messages:
            hub = inner_data['H'] if 'H' in inner_data else ''
            if hub.lower() == 'streaming':
                # method = inner_data['M']
                message = inner_data['A']
                ret.append(message)

    return ret, errorcount


class SignalRClient:
    """A client for receiving and processing F1 timing data which is streamed
    live over the SignalR protocol.

    During an F1 session, timing data and telemetry data are streamed live
    using the SignalR protocol. This class can be used to connect to the
    stream and process the received data in real time.

    Args:
        on_message: A callback function that will be called when a new message is received from the SignalR server. The callback function will be passed the message as a parameter.
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
    _connection_url = 'https://livetiming.formula1.com/signalr'

    def __init__(self, filename: str, filemode: str = 'w', debug: bool = False,
                 timeout: int = 5):

        self.headers = {'User-agent': 'BestHTTP',
                        'Accept-Encoding': 'gzip, identity',
                        'Connection': 'keep-alive, Upgrade'}

        self.topics = ["Heartbeat", "CarData.z", "Position.z",
                       "ExtrapolatedClock", "TopThree", "RcmSeries",
                       "TimingStats", "TimingAppData",
                       "WeatherData", "TrackStatus", "DriverList",
                       "RaceControlMessages", "SessionInfo",
                       "SessionData", "LapCount", "TimingData"]

        self.debug = debug
        self.timeout = timeout
        self.filename = filename
        self.filemode = filemode
        self._connection = None

        #if not logger:
        #    logging.basicConfig(
        #        format="%(asctime)s - %(levelname)s: %(message)s"
        #    )
        #    self.logger = logging.getLogger('SignalR')
        #else:
        #    self.logger = logger

        self._t_last_message = time.time()

    #Prolly useless
    def _to_file(self, msg):
        self._output_file.write(msg + '\n')
        self._output_file.flush()

    async def _on_do_nothing(self, msg):
        # just do nothing with the message; intended for debug mode where some
        # callback method still needs to be provided
        pass

    async def _on_message(self, msg):
        #msg[1]=decompress_time_series(msg[1])
        #print(msg)
        self._t_last_message = time.time()
        loop = asyncio.get_running_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, self._to_file, str(msg)
                )
        except Exception:
            self.logger.exception("Exception while writing message to file")

    async def _process_message(msg):
        # Process the message here
        print(msg)

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
            hub.client.on('feed', self._on_message)

        hub.server.invoke("Subscribe", self.topics)

        # Start the client
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, self._connection.start)

    async def _supervise(self):
        self._t_last_message = time.time()
        while True:
            if (self.timeout != 0
                    and time.time() - self._t_last_message > self.timeout):
                self.logger.warning(f"Timeout - received no data for more "
                                    f"than {self.timeout} seconds!")
                self._connection.close()
                return
            await asyncio.sleep(1)

    async def _async_start(self):
        #self.logger.info(f"Starting FastF1 live timing client "
        #                 f"[v{fastf1.__version__}]")
        await asyncio.gather(asyncio.ensure_future(self._supervise()),
                             asyncio.ensure_future(self._run()))
        self._output_file.close()
        #self.logger.warning("Exiting...")

    def start(self):
        """Connect to the data stream and start writing the data to a file."""
        try:
            asyncio.run(self._async_start())
        except KeyboardInterrupt:
            self.logger.warning("Keyboard interrupt - exiting...")
            return

def pako_inflate_raw(data):
    decompress = zlib.decompressobj(-15)
    decompressed_data = decompress.decompress(data)
    decompressed_data += decompress.flush()
    return decompressed_data

if __name__ == '__main__':
    client = SignalRClient(filename="ahahahahah.txt")
    client.start()
    #import gzip
#
    #prova = "7ZSxCgIxDIbfJbNKkqZt7Cq+gS6Kg4igIDeo23HvrlfXIiW3KHRJS+lP+v8pXw/r7nm/nh+Q9j1snydIwMhujss5uw365EMiWkhgFZYdzGB1vL9v90BjWV2OXXe+5QOEhDPgXF2ukqv/7MdlGPKFCh2hZGVeR62OWjH2JLQKrS7J/NQwIR9S61BKAZForGzMdVMtNHYT7LI1ZI4lu4iusrGzfguxfkSps1p+rvfF6cZafZgypFjKusay2kJ+S7+RLDAr6bKRrJGskayR7I9JpoGjutBI1kjWSNZI9tskOwwv"
    #prova2="7ZM7DsIwDEDv4rmgxEnaODszSHTgI4YKdahQW0TDVOXuFC5APMHgxVKkN9gvejPsxqmL3ThAOM9Qd307xaa/QwBUaFaKVmhq5YIrg9ZrY4i88icoYDPER9dOEGbQ77GPTXwuT9gO9aO53hbkAEEVcPzM0zJTAZiP2nxUKwbL2FZzdigZrGcYY9yGDL1oGCzDA1b5rGH8hWV4sIx9nctnS4aziuHBZ3tIqfheqXNEtrJSqVQqlf5tpWTIeyqlUqlUKv3TSnGtK/LOoFQqlUqlv6n0kl4="
    #prova3="7ZS/CsIwEMbf5eYql/vTplnFN9BFcShSUJAO6lb67rYpOAWJ6aKQ5RJCPi7fd+HXw7Z73q/tA9yxh/3zDA4IiVdYr4h3qE6tI7M2wlqSHKCATXMfb/dgprK5NF3X3vwBgsMCyFf2VXzVeT8udhj8hQidQfFKv7618n1PnHQGU4UJLmdh8lPLBfkYm9iVQgEZsVVkY4qbaqAxL7BLqSFTFbKLyJGNOfVbSOpHlDir4eeqBqdbxerLJUOqQlnHWLZpIY/STyQTYh3PM8kyyTLJMsn+mGRqWepSM8kyyTLJMsl+m2Sn4QU="
    ##decoded_bytes = base64.b64decode(prova2)
    ##print(decoded_bytes)
    ##decoded_string = decoded_bytes.decode("utf-8")
    #json_str = json.loads(pako_inflate_raw(base64.b64decode(prova3)).decode('utf-8'))
    #print(json_str["Entries"][0]["Cars"]["1"])
