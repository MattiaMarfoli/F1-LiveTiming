class analyzer:

    def __init__(self):
        self._classification=[]
        self._laptimes=[]

        
    def pos(self,dict_to_unpack: dict):
        """ 
            dict_to_unpack:  key:  
                                number of the driver(str): value: dict with keys:
                                    keys: "Status": "OnTrack" , ...
                                          "X","Y","Z" : coordinates (int) (3 different keys)    
        """
        return dict_to_unpack 


    def weather(self,dict_to_unpack: dict):
        pass 

    def racemessages(self,dict_to_unpack: dict):
        pass

    def TDF1(self, dict_to_unpack: dict):
        for driver in set(dict_to_unpack["Lines"].keys()):
            lap_times = dict_to_unpack["Lines"][driver]
            key_set = set(lap_times.keys())
            if "NumberOfLaps" in key_set and "LastLapTime" in key_set:
                number_of_laps = lap_times["NumberOfLaps"]
                last_lap_time = lap_times["LastLapTime"]["Value"]
                self._laptimes_2[driver][number_of_laps] = last_lap_time


    #def TDF1(self,dict_to_unpack: dict):
    #    for driver in set(dict_to_unpack["Lines"].keys()):
    #        keys=set(dict_to_unpack["Lines"][driver].keys())
    #        if "NumberOfLaps" in keys and "LastLapTime" in keys:
    #            self._laptimes_2[driver][dict_to_unpack["Lines"][driver]["NumberOfLaps"]]=dict_to_unpack["Lines"][driver]["LastLapTime"]["Value"]

        
    def TAD(self,dict_to_unpack: dict):
        """
        Structure:

        "Lines" -> #Driv (eg "1") -> "Line" -> position (int) #when overtaken
                    (Also 2+)     -> "GridPos" (just at beginning, with "Line") -> as str(int)
                                  -> "RacingNumber" (just at beginning, with "Stints") -> same of #Driv (?)
                                  -> "Stints" -> #NumbStint (eg "0","1"..) /-> "TotalLaps" -> int
                                                                           |-> "Compound" -> eg ("Hard")                                       
                                                                           |-> "LapFlags": 0/1 bho
                                                                           |-> "New" -> "false"/"true"
                                                                           |-> "TyresNotChanged" -> 0/1
                                                                           |-> "TotalLaps" -> int
                                                                           |-> "StartLaps" -> int
                                                                           \-> "LapTime" -> "m:ss.SSS"         
                                                                           \-> "LapNumber"-> int
                                                                           \-> "LapFlags"-> 0/1      


        Exceptions found:
            - ...                                                                
                                                                           
        """
        drivers_in_msg=list(dict_to_unpack["Lines"].keys())
        for driver in drivers_in_msg:
            short_dict=dict_to_unpack["Lines"][driver]
            keys=list(short_dict.keys())
            #print("TDA (keys): ",keys)
            if "GridPos" in keys:
                if driver in self._classification:
                    self._classification.remove(driver)
                self._classification.insert(int(short_dict["GridPos"])-1,driver)
            if "Line" in keys:
                if driver in self._classification:
                    self._classification.remove(driver)
                self._classification.insert(short_dict["Line"]-1,driver)
            if "Stints" in keys :
                #print("TDA (dict?): ",short_dict["Stints"])
                if driver not in self._laptimes.keys():
                    self._laptimes[driver]={}
                    #self._laptimes[driver]["LapTimes"]=[]
                if type(short_dict["Stints"])==dict:
                    stints=list(short_dict["Stints"].keys())
                    for stint in stints:
                        #print("TDA (stints): ",short_dict["Stints"][stint])
                        if "Compound" in short_dict["Stints"][stint] and "TotalLaps" in short_dict["Stints"][stint]:
                            self._laptimes[driver]["CurrentTyres"]=[short_dict["Stints"][stint]["Compound"],
                                                                    short_dict["Stints"][stint]["TotalLaps"]]
                            #print("TDA (Compound): ",self._laptimes[driver]["CurrentTyres"])
                        if "LapNumber" in short_dict["Stints"][stint] and "LapTime" in short_dict["Stints"][stint]:
                            tyre,lap_tyre_changed = self._laptimes[driver]["CurrentTyres"]
                            LapInfo="_".join([str(short_dict["Stints"][stint]["LapNumber"]),
                                              tyre,str(lap_tyre_changed)])
                            self._laptimes[driver][LapInfo]=short_dict["Stints"][stint]["LapTime"]
                            #print("TDA (LapNumber): ",LapInfo)
                elif type(short_dict["Stints"])==list:
                    if len(short_dict["Stints"])==1:
                        short_dict["Stints"]=short_dict["Stints"][0]
                        #print("TDA (stints): ",short_dict["Stints"])
                        if "Compound" in short_dict["Stints"] and "TotalLaps" in short_dict["Stints"]:
                            self._laptimes[driver]["CurrentTyres"]=[short_dict["Stints"]["Compound"],
                                                                    short_dict["Stints"]["TotalLaps"]]
                            #print("TDA (Compound): ",self._laptimes[driver]["CurrentTyres"])
                        if "LapNumber" in short_dict["Stints"] and "LapTime" in short_dict["Stints"]:
                            tyre,lap_tyre_changed = self._laptimes[driver]["CurrentTyres"]
                            LapInfo="_".join([str(short_dict["Stints"]["LapNumber"]),
                                              tyre,str(lap_tyre_changed)])
                            self._laptimes[driver][LapInfo]=short_dict["Stints"]["LapTime"]
                            #print("TDA (LapNumber): ",LapInfo)
                    else:
                        raise Exception("Length of stints in list is more then 1 item! I'm going on but 100'%' something is gonna break :(")    
                else:
                    raise Exception("Type of short_dict['Stints'] not dict or list! I'm going on but 100'%' something is gonna break :(")
                

    def get_starting_time_session(self,interesting_times: list):
        for time_ms,status in interesting_times:
            if status=="Started":
                return time_ms
    
