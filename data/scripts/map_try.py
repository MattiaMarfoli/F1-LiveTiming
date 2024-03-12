import requests,json

index_url="https://livetiming.formula1.com/static/2023/Index.json"
mv_url="https://api.f1mv.com/api/v1/circuits/"
year="2023"

contents=requests.get(url=index_url)
events=json.loads(contents.content)

MAPS_DICT=json.load(open("data/MAPS.json"))

for meeting in events["Meetings"]:
  circuit_key=meeting["Circuit"]["Key"]
  circuit_name=meeting["Name"]
  circuit_response=requests.get(mv_url+str(circuit_key)+"/"+year)
  circuit_info=json.loads(circuit_response.content)
  print(circuit_name," ",circuit_key)
  if "test" not in circuit_name.lower():
    MAPS_DICT[circuit_name]["corners"]=circuit_info["corners"]
    MAPS_DICT[circuit_name]["marshalLights"]=circuit_info["marshalLights"]
    MAPS_DICT[circuit_name]["marshalSectors"]=circuit_info["marshalSectors"]
    MAPS_DICT[circuit_name]["x"]=circuit_info["x"]
    MAPS_DICT[circuit_name]["y"]=circuit_info["y"]
    MAPS_DICT[circuit_name]["circuit_length"]=0
json.dump(MAPS_DICT,open("data/MAPS2.json","w"),indent=2)