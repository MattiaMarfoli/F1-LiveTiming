import requests
import fastf1 as ff1
import matplotlib.pyplot as plt
import json

year = 2023
session = "qualifying"
my_dpi=96
FIG_X,FIG_Y = 630,480

headers={
    "apikey": "t3DrvCuXvjDX8nIvPpcSNTbB9kae1DPs",
    "locale" : "en"
}

url = "https://api.formula1.com/v1/editorial-eventlisting/events?season="+str(year)

####################################################################################

content=requests.get(url=url,headers=headers)
events=content.json() 

all_grand_prix = [event["meetingName"] for event in events["events"] if (event["type"]=="race" and "eventStatusOverride" not in event.keys())]
i=1

maps={}

for grand_prix in all_grand_prix:
  print("\n *************************************\n")
  print("          ",grand_prix,"                ")
  print("\n *************************************\n")
  
  race = ff1.get_session(year, grand_prix, session)
  race.load()

  lps=race.laps
  drivers=race.drivers

  total_X = []
  total_Y = []

  for driver in drivers:
    lp=lps.pick_driver(driver).pick_fastest()
    pd=race.pos_data[driver]

    Time_end=lp["Time"]
    Lap_time=lp["LapTime"]
    try:
      pd_lap=pd[(pd["Time"]>=Time_end-Lap_time) & (pd["Time"]<=Time_end)]

      pd_lap=dict(pd_lap)

      X,Y,Z = pd_lap["X"].to_numpy()/10. , pd_lap["Y"].to_numpy()/10. , pd_lap["Z"].to_numpy()/10.

      for x,y in zip(X,Y):
        total_X.append(x)
        total_Y.append(y)
    except:
      pass
  
  maps[grand_prix]={
      "X":total_X,
      "Y":total_Y
  }

MAPS = {}

for event,positions in maps.items():
  plt.figure(figsize=(FIG_X/my_dpi, FIG_Y/my_dpi), dpi=my_dpi)
  plt_name="data/"+event+"_"+str(year)+"_plot.png"
  fig,ax=plt.subplots()
  x=positions["X"]
  y=positions["Y"]
  #plt.gca().invert_yaxis()"
  ax.plot(x,y,c="grey",alpha=0.25)
  #x_len=ax.axes.get
  ax.axis("off")
  #plt.show()

  MAPS[event]={
    "map":event+"_"+str(year)+"_plot.png",
    "xlim": ax.axes.get_xlim(),
    "ylim": ax.axes.get_ylim(),
    "xscale" : (ax.axes.get_xlim()[1] - ax.axes.get_xlim()[0])/FIG_X,
    "yscale" : (ax.axes.get_ylim()[1] - ax.axes.get_ylim()[0])/FIG_Y,  
    "corners": [],
    "marshallSectors": []
  }
  plt.savefig(plt_name, transparent=True,bbox_inches='tight', pad_inches = 0)
  plt.close()
  
with open("MAPS.json","w") as fp:
  json.dump(MAPS,fp=fp,indent=3)