import requests,json,datetime,arrow



base_url = "https://api.formula1.com/v1"

eventListing_url="editorial-eventlisting"

sessionResults_url="fom-results"

headers = {
  "apikey": "t3DrvCuXvjDX8nIvPpcSNTbB9kae1DPs",
  "locale": "en"
           }

season="2023"
DT=arrow.get("2023-07-01T09:30:00").datetime
print(DT,DT+datetime.timedelta(hours=2),int("+02:00".split(":")[0]))

events_query="events?season="+season
#timetables_query="timetables?"

events_url="/".join([base_url,eventListing_url,events_query])
#timetables_url=

events=requests.get(events_url, headers=headers).json()["events"]
for event in events:
  start_DT=arrow.get(event["meetingStartDate"]).datetime
  end_DT=arrow.get(event["meetingEndDate"]).datetime
  if (DT-start_DT).total_seconds()>0 and (DT-end_DT).total_seconds()<0:
    #print(event["meetingOfficialName"]," ",event["meetingKey"])
    event_name=event["meetingOfficialName"]
    meeting_key=event["meetingKey"]
    timetables_query="timetables?meeting="+event["meetingKey"]+"&season="+season
    timetables_url="/".join([base_url,sessionResults_url,timetables_query])
    proceed_flag=True
    break
  else:
    proceed_flag=False

if proceed_flag:
  sessions=requests.get(timetables_url, headers=headers).json()["timetables"]
  max_time=1e9
  for session in sessions:
    start_DT=arrow.get(session["startTime"]).datetime
    end_DT=arrow.get(session["endTime"]).datetime
    if (DT-start_DT).total_seconds()>=0 and (DT-end_DT).total_seconds()<=0:
      session_name=session["description"]
      inside_outside="inside the event!"
      break
    else:
      if abs((DT-start_DT).total_seconds())<max_time and (DT-end_DT).total_seconds()<=0:
        max_time=abs((DT-start_DT).total_seconds())
        session_name=session["description"]
        inside_outside="close to the event, just "+str(round(max_time/60.))+" minutes away from the start!"
        #print(session["description"]," ",abs((DT-start_DT).total_seconds())," ",(DT-end_DT).total_seconds())
  print("Session found! It is ",inside_outside," \nSession: ",session_name, "of ", event_name,". \n Meeting Key: ",meeting_key)
else:
  print("Datetime: ",DT, " not inside an event")