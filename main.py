from config import paths
from src import GUI as gui

if __name__ == "__main__":
    
    G = gui.GUI()
    G.run()

    #print(P.get_interesting_times("2023","Singapore_Grand_Prix","Race"),"\n\n")
    #try:
    #    for key,value in P.jsonStream_parser("2023","Singapore_Grand_Prix","Race","TyreStintSeries").items():
    #        print(key," ",value)
    #except:
    #    print(P.jsonStream_parser("2023","Singapore_Grand_Prix","Race","TyreStintSeries"))
    #print(P.jsonStream_parser("2023","Italian_Grand_Prix","Qualifying","TimingData").keys())

# time_ms -> "LapSeries" -> #Driv. (eg "1") -> "LapPosition" -> #Lap (str) -> Position after the lap (str)
# NB!! #Driv. can be more than 1 key to "LapSeries"  and also #Lap to "LapPosition" (especially if lapped in race)

# time_ms -> "TimingAppData" -> "Lines" -> #Driv (eg "1") -> "Line" -> position (int) #when overtaken
#                                                         -> "Stints" -> #NumbStint (eg "0","1"..) -> "TotalLaps" -> int
#                                                                                                 |-> "Compound" -> eg ("Hard")                                       
#                                                                                                 |-> "LapFlags": 0/1 bho
#                                                                                                 |-> "New" -> "false"/"true"
#                                                                                                 |-> "TyresNotChanged" -> 0/1
#                                                                                                 |-> "TotalLaps" -> int
#                                                                                                 |-> "StartLaps" -> int
#                                                                                                 \-> "LapTime" -> "m:ss.SSS"         
#                                                                                                 \-> "LapNumber"-> int
#                                                                                                 \-> "LapFlags"-> 0/1      
#       

#useful to run iteratively: 
#   SessionData: cool: time,dictionary 
#   TimingDataF1: maybe interesting for IntervaltoPositionAhead. Other no: time,dictionary 
#   LapSeries: useful. LapPosition of each driver when crossing lines: time,ditcionary
#   TimingAppData: prob useful. Something about stints and Laptime and other stuff: time,dictionary
#   CarData.z  yes:  time inside dictionary  "Entries": list -> zeroth entry: {"Utc":'2023-09-03T12:01:04.442827Z',"Cars":{}} etc.
#   Position.z  yes: time inside dictionary  "Position": list -> zeroth entry: {"TimeStamp":same above,"Entries":{}} etc.
#   SessionStatus: yes. Little calls and say when race start,finish etc. time,dict
#   DriverRaceInfo: Huge. Gap and interval for each driver. time,dict
#   LapCount: name self-explanatory. time,dict  (only in race)
#   HeartBeat: time,utctime useful.
#   WeatherData: time,weather
#   TeamRadio: restriced sample
#   TlaRcm - RaceControlMessages: same. Tla simplier. time,dict
#   CurrentTyres: cool but prob not updated. ? dunno
# 



