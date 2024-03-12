import requests
import fastf1 as ff1
import matplotlib.pyplot as plt

base_circuit_url="https://api.f1mv.com/api/v1/circuits/" # 151/2022
base_meetings_url="https://api.f1mv.com/api/v1/meetings/" #1113

years = ["2022"]

headers={
    "apikey": "t3DrvCuXvjDX8nIvPpcSNTbB9kae1DPs",
    "locale" : "en"
}
meetingKeys = {}
for year in years:
  print("\n",year,"\n")
  meetingKeys[year]={}
  url = "https://api.formula1.com/v1/editorial-eventlisting/events?season="+str(year)

  content=requests.get(url=url,headers=headers)
  events=content.json() 

  for event in events["events"]:
    if event["type"]=="race" and "eventStatusOverride" not in event.keys():
      #print(event)
      meetingKeys[year][event["meetingName"].replace(" ","_")] = event["meetingKey"]
  
      content=requests.get(url=base_meetings_url+event["meetingKey"],headers=headers)     
      meeting=content.json()
       
      meetingKeys[year][event["meetingName"].replace(" ","_")] = meeting["MeetingInfo"]["Circuit"]["Key"]
      print("\t ",event["meetingName"],"\t\t",event["meetingKey"],"\t",meeting["MeetingInfo"]["Circuit"]["Key"])
            