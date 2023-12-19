"""

Idea:

    Sender: 
        LT:     -) Read the messages in order of arrival and decipher if needed. 
                   Create a queue of N msgs too for checks. 
                -) Checks if previous msg's datetime is lower than current's
                    -) If not (current msg is sent after but happend before the previous one): 
                        remind to append before the previous msg
                    -) If yes: go on
                -) After all checks: include msg to database
                x) Reading  -> SignalR_LS.on_message 
                        [x]: Implement queue of messages 
                        [x]: Checks datetime flow
                        [x]: Adjust this function after live_parser is fixed 
                   Decipher -> PARSER.live_parser 
                        [x]: Implement the database for LS. 
                              Could be done by a class where parser is called.
                

        LT-sim: -) Read the messages from the database and decipher if needed.
                -) Checks already done on merge
                -) Simply do nothing. LiveTime simulation is done when updating the GUI!
                x) Reading&Decipher  -> PARSER.jsonStream_parser
                   Merge             -> MERGER.merger
                   
                   


    Receiver:   -) Read from database if there is an update (only needed in LT, LT-sim keeps running whatever happens).  
                   To track if there is an update available to retrieve use an index in the loop.
                   Finally send the msg to the right handler.
                x) Receiver: currently not implemented
                        TODO: implement the receiver: just one class for both LS and LS-sim
                   
    Handlers:   -) Reading the msg and updating front-end values + analysis.
                   Retrieving under request to be plotted / displayed.
                -) If LS-sim sleep, then IF NOT PAUSED update GUI. 
                   Here we handle also FW/BW and GoTo.
                -) For plotting think about an fps limiter to not update 
                   every msg received
                x) Analysis: Analyzer class
                    TODO: Rework of the class. 
                          Now pieces are shuttered between GUI and LIVE_SIMULATION 
                   Front-End: GUI class
                   
    Play Manager: (This has to be done for each handler!)

        Pause/Play button:  Simply a bool flag 

        FW/BW X seconds:    TL;DR: Use of another index to set the Desired_Index (DI).
                            Pause the loop.
                            DI is found by setting Desired_Time (DT) equal to Current_Time (CT)
                            plus or minus X seconds. Then an auxiliary function loop over the 
                            analyzed msgs to detect the DI and update the Current_Index (CI) to it. 
                            Then resume the loop.       

        GoTo Y second:      Same of above but with DT set to the time given by user.

        Resume LS:          Set index to be last analyzed index.

    TODO think of doing a database class as a parent and multiple instances for each database in order to speed locks up 
    [x] Create the Database class in config and pass it to each one that needs it (so to create only one instance)
    [x] Use Locks in the database in order to prevent concurrencies
    [x] Update_database to put data in the databae and Retrieve_subset_database to get data from the database (with locks)
    [x] Then Analyzer class will make calls to the database 
    


GUI -> needs data processed, ordered ready to be plotted
Analyzer -> needs raw data (not encrypted) and returns processed data
Sender -> reads from signalr and returns raw data (not encrypted)


GUI ->  inizialize everything
    ->  start telemetry plotting
        How:
            -> LT: when first_time_msg is not none anymore
            -> LT-sim: immediately
    ->  Flow control:
        What dictate time flows?
            -> DateTimes! Basically telemetry will update every tot seconds = sleeps for seconds in between
               and calls get_DB_between_times.
            -> Pause: before entering in a dead loop it has to get the current time 
               and keep tracking of it because when it resumes it has to start from that 
               time where it stopped independently of what time is now.
               time_now is needed in LT when one wants to go to a time that has not been reached yet.
        Interesting Times:
            -> Time_now      = last_message_DT
            -> Time_play     = last_message_displayed_DT. It wants to go to Time_desired or Time_now if resume is pressed
            -> Time_desired  = Time_play and called by callbacks in FW/BW/GoTo (these only updates Time_desired)
            -> Delay_Time    = To be subtracted at the start to all Times. 
                               If updated watch out to delta between Delay_Time_now and Delay_Time_before.
                               Sanity checks needed ofc.
"""

# import pandas as pd
# import numpy as np

# prova = {
#     "1": {
        
#         "Time": np.array([1,2,3]),
#         "Throttle": np.array([4,5,6]),
#         "Speed": np.array([7,8,9]),
#         "Out": 0,
#     },
#     "2": {
        
#         "Time": np.array([10,20,30]),
#         "Throttle": np.array([40,50,60]),
#         "Speed": np.array([70,80,90]),
#         "Out": 1,
#     }
# }
# prova_pd=pd.DataFrame(prova["1"])

# print(prova_pd)

# new_row=pd.DataFrame({"Time":123,"Throttle":456,"Speed":789},index=[0])

# prova_pd=pd.concat((prova_pd,new_row),ignore_index=True)

# print(prova_pd[prova_pd["Out"].isna()])

# prova2=pd.DataFrame(columns=["Time",])

import pandas as pd
import numpy as np
import timeit
n=1000
# Function to test appending to a DataFrame
def test_append():
    df = pd.DataFrame(columns=['A', 'B'])
    for _ in range(n):
        new_data = {'A': [np.random.randint(1, 100)],
                    'B': [np.random.randint(1, 100)]}
        df = pd.concat((df,pd.DataFrame.from_dict(new_data)), ignore_index=True)
    print(len(df["A"]))
# Function to test overwriting from a dictionary
def test_overwrite():
    data = {'A': [], 'B': []}
    for _ in range(n):
        data['A'].append(np.random.randint(1, 100))
        data['B'].append(np.random.randint(1, 100))
        df = pd.DataFrame.from_dict(data)
    print(len(df["A"]))

# Measure time for appending
append_time = timeit.timeit(test_append, number=10)
print(f"Time taken for appending: {append_time:.5f} seconds")

# Measure time for overwriting
overwrite_time = timeit.timeit(test_overwrite, number=10)
print(f"Time taken for overwriting: {overwrite_time:.5f} seconds")
