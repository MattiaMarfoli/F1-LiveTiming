import requests,json,os

index_url="https://livetiming.formula1.com/static/"
years=["2022","2023"]
feed="TimingDataF1.jsonStream"

session_urls=json.load(open("data/jsons/SESSION_URLS.json"))

for key,event in session_urls.items():
  Skip_to_next_race=False
  if key[:4] in years and "Testing" not in key:
    for session,url in event.items():
      print("\n",key)
      response = requests.get(index_url+url+feed).content
      for line in response.splitlines():
        line_noBOM=line.decode("utf-8")
        line_noBOM_noufeff=line_noBOM.replace("\ufeff","")
        body=json.loads(line_noBOM_noufeff[12:])
        if "Lines" in body.keys():
          for driver,sectors in body["Lines"].items():
            if type(sectors)==dict:
              if "Sectors" in sectors.keys():
                if type(sectors["Sectors"])==dict:
                  for sector,sector_dict in sectors["Sectors"].items():
                    if type(sector_dict)==dict:
                      if "Segments" in sector_dict.keys():
                        if type(sector_dict["Segments"])==list:
                          print("\t Sector number: ",sector," has ",len(sector_dict["Segments"])," segments")
                  Skip_to_next_race=True
                  break
        elif Skip_to_next_race:
          break
      break
                          
                          