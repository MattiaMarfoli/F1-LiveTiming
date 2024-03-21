import urllib.request
import requests

## Run this from the base directory (where main.py lives!!!) ###

season="2024"
base_url = "https://api.formula1.com/v1"
eventListing_url="editorial-eventlisting"
sessionResults_url="fom-results"
headers = {
            "apikey": "t3DrvCuXvjDX8nIvPpcSNTbB9kae1DPs",
            "locale": "en"
          }

print("Checking year: ",season)

events_query="events?season="+season
events_url="/".join([base_url,eventListing_url,events_query])
events_request=requests.get(events_url, headers=headers)
if events_request.ok:
  events=events_request.json()["events"]
  for event in events:
    if "type" in event.keys():
      if event["type"].lower()=="race":
        countryFlag_filename = event["countryFlag"].split("/")[-1]
        urllib.request.urlretrieve(event["countryFlag"], "Assets/CountryFlags/"+countryFlag_filename) 
        print(countryFlag_filename, " saved in Assets/CountryFlags/ successfully!")


