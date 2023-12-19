# [x] Colori nei plot 
# [x] Etichette sulle velocità
# [x] Label nei plot (legenda) 
# [x] Nomi a posto dei numeri nelle checkbox
# [ ] Fix sui crash nelle tab
# [x] Zoom nel compare
# [ ] Corner analysis nel compare
# [x] Numeri dei corner nel compare
# [x] LapTime vs LapNumber plot
# [ ] Mappa posizione 
# [x] Check quali,FP,shootout,Sprint..
# [ ] Weather info, Race control msgs..
# [ ] Restyle all windows! Divide all plots in windows and anchor them to the point thy belong.
# [ ] Let right part of the screen in telemetry plot follow the y-scrolling. To do so, update the y of the items!
# [x] Display 1 telemetry plot for each driver
# [x] Probably subplot possible to use.. redo the style.
# [ ] Don't write multiple times the same part of code: redo the compare telemetry such that we can add >2 drivers automatically
# [ ] Use a main script for DPG and divide all the analysis in multiple classes.
# [ ] If any problem with CPU -> parallelize multiple connections, each one with its own feed to analyze.
# [ ] New database? Pandas for now and interpolate with NaN values.
# [ ] LapTimes and Ranking with gaps
# [ ] Minisectors
# [ ] Race Clock for pit-stop (last thing)
  
  
# import arrow,zlib,base64

# prev_msgs_datetime=[]
# LENGTH_QUEUE_MSGS=1
# is_first_msg=True
# DB=[]
# def sort_msg(msg):
#   #print(msg_to_send)
#   CURR_DT=arrow.get(msg[2]).datetime
#   FB=False
#   #print(CURR_DT," ",msg)
#   #print(len(prev_msgs_datetime))
#   if len(prev_msgs_datetime)>=LENGTH_QUEUE_MSGS:
#     msg_to_send=prev_msgs_datetime.pop(0)[1]
#     body_exp=live_parser(feed=msg_to_send[0],line=msg_to_send[1],date=msg_to_send[2])
#     DB.append([body_exp,msg_to_send[0]])
#     #print("A",CURR_DT," ",msg_to_send)
#   else:
#     prev_msgs_datetime.append([CURR_DT,msg])
#     #print("B",CURR_DT," ",msg)
#   for index in range(len(prev_msgs_datetime)):
#     if CURR_DT < prev_msgs_datetime[index][0]:
#         prev_msgs_datetime.insert(index,[CURR_DT,msg])
#         FB=True
#         break
#   if not FB:
#     prev_msgs_datetime.append([CURR_DT,msg])

# def pako_inflate_raw(data):
#       """
#       Brief:
#         simply decode the .z response of certain feed (eg 'RaceData.z' and 'Position.z')
      
#       Args:
#         data (str): encrypted message
        
#       Returns:
#         str: decompressed input string
#       """
#       decompress = zlib.decompressobj(-15)
#       decompressed_data = decompress.decompress(data)
#       decompressed_data += decompress.flush()
#       return decompressed_data
# p=[]
# def live_parser(feed: str, line: str, date:str):
#       """
#       Brief: 
#         Used for LiveStreaming only. See jsonStream_parser and OneLineParser methods  
#         for simulated live sessions.
#         Convert timestamp of the message in ms (from the start of stream)
#         and decode the message if needed. For nested messages create an key for 
#         each entry. 

#       Args:
#         feed (str): feed name
#         line (str): message (depends on feed)
#         date (str): timestamp (format: yyyy-mm-ddThh:mm:ss.SSSZ , read with arrow pkg)

#       Returns:
#         dict: datetime: msg
#       """
      
#       if feed[-2:]==".z":
#         body=json.loads(pako_inflate_raw(base64.b64decode(line)).decode('utf-8'))
#         body_exp={}
#         for entry in body[list(body.keys())[0]]: 
#           # entry -> RaceData: "Utc" and  "Cars" -> "n" -> "Channels" -> "0","2","3","4","5","45"
#           #       -> Position: "Timestamp" and  "Entries" -> "n" -> "Status" , "X" , "Y" , "Z"
#           time_entry=arrow.get(entry[list(entry.keys())[0]]).datetime
#           body_exp[time_entry]=entry[list(entry.keys())[1]]
#         return body_exp
#       #elif feed=="DriverList":
#       #  date_body=str(line).split("{")
#       #  body=""
#       #  for term in date_body[1:]:
#       #    body+="{"+term
#       #  body=json.loads(body)
#       #  return body
#       elif feed=="TimingDataF1":
#         #print(line,date)
#         DT=arrow.get(date).datetime
#         body_exp={DT: [] }
#         line=line.replace("True","1").replace("False","0")
#         body=json.loads(line)
#         for Lines,TDF1 in body.items():
#           if Lines!="Withheld":
#             for Driver,Updates in TDF1.items():
#               if "LastLapTime" in Updates.keys() and "NumberOfLaps" in Updates.keys():
#                 driver=Driver
#                 NLap=Updates["NumberOfLaps"]
#                 Value_dict=Updates["LastLapTime"]
#                 try:
#                   if type(Value_dict)==dict:
#                     Value=Updates["LastLapTime"]["Value"]
#                 except:
#                   print("Live Parser: Value_dict not a dict -> ", Value_dict)      
#                 body_exp[DT].append([driver,NLap,Value])
#                 #print(driver,NLap,Value)
#         return body_exp
#       elif feed=="WeatherData":
#         DT=arrow.get(date).datetime
#         body_exp=line
#         return {DT:body_exp}        
#       else:
#         try:
#           body=json.loads(line)
#           date_in = arrow.get(date).datetime
#           return {date_in:body}
#         except:
#           print(feed, " not well parsed")
#           date_in = arrow.get(date).datetime
#           return {date_in: None }    

# import json
# f=open("/home/marfo99/Projects/F1_LiveTiming/data/PROVA_LV_RACE.txt","r")
# lines=f.readlines()
# msgs=[]

# body_exp={}
# TD=0
# CD=0
# WD=0
# for line in lines:
#   line_nobom=line.replace("\ufeff","").replace("'",'"').replace("\n","").replace(" ","")
#   line_nobom_splitted=line_nobom.split(",")
#   F=(line_nobom_splitted[0]).replace("[","").replace('"',"")
#   D=(line_nobom_splitted[-1]).replace("]","").replace('"',"")
#   B=",".join(line_nobom_splitted[1:-1])
#   msgs.append([F,B,D])
#   if F=="TimingDataF1":
#     TD+=1
#   elif F=="CarData.z":
#     CD+=1
#   elif F=="WeatherData":
#     WD+=1
              
# for msg in msgs:
#   sort_msg(msg)

# # for key,value in body_exp.items():
# #   print(key)
# #   for lap in value:
# #     print("\t",lap[1]," ",lap[2])    
# z=0
# n=0
# Laps={}
# D=list(DB[0][0].keys())[0]
# for msg in DB:
#   if D<=list(msg[0].keys())[0]:
#     D=list(msg[0].keys())[0]
#     F=msg[1]
#     #print("True..")
#   else:
#     print("False..",D," ",list(msg[0].keys())[0]," ",F)
#     n+=1
#     D=list(msg[0].keys())[0]
#     F=msg[1]
#   if msg[1]=="TimingDataF1" and msg[0]!=None:
#     for V in msg[0].values():
#       for L in V:
#         if L[0] not in Laps.keys():
#           Laps[L[0]]=[]
#         Laps[L[0]].append([L[1],L[2]])
# print(z)
# print(len(msgs),len(lines),CD,TD,WD,CD+TD+WD,len(p),len(DB),len(prev_msgs_datetime),n)  


# for D,Ls in Laps.items():
#   print(D)
#   for l in Ls:
#     print("\t",l)
# #json.loads("{'Lines': {'23': {'Sectors': {'2': {'Value': '53.807'}}, 'LastLapTime': {'Value': '1:53.936'}}}}".replace("'",'"'))

# import dearpygui.dearpygui as dpg
# dpg.create_context()

# width, height, channels, data = dpg.load_image("/home/marfo99/Projects/F1_LiveTiming/data/LasVegas_22_plot.png")

# def move_circle():
#   x,y=dpg.get_item_configuration("circle")['center']
#   dpg.delete_item("circle")
#   dpg.draw_circle(color=(255, 0, 0, 255),center=(x+10,y+10),radius=6,fill=(255,0,0,255),tag="circle",parent="drawlist")
#   print(x,y)
  

# print(width,height,channels)
# with dpg.texture_registry(show=True):
#     dpg.add_static_texture(width=width, height=height, default_value=data, tag="texture_tag")

# with dpg.window(label="Tutorial"):
#   dpg.add_button(tag="prova",width=20,height=20,callback=move_circle)
#   with dpg.drawlist(width=640, height=480,tag="drawlist"):  # or you could use dpg.add_drawlist and set parents manually

#         dpg.draw_image("texture_tag",pmin=(0,0),pmax=(640,480))
#         dpg.draw_line((10, 10), (100, 100), color=(255, 0, 0, 255), thickness=1)
#         dpg.draw_text((0, 0), "Origin", color=(250, 250, 250, 255), size=15)
#         dpg.draw_arrow((50, 70), (100, 65), color=(0, 200, 255), thickness=1, size=10)
  
#         dpg.draw_circle(color=(255, 0, 0, 255),center=(200,80),radius=6,fill=(255,0,0,255),tag="circle")


# dpg.create_viewport(title='Custom Title', width=800, height=600)
# dpg.setup_dearpygui()
# dpg.show_viewport()
# dpg.start_dearpygui()
# dpg.destroy_context()

# Step 1: Import the necessary modules

# import pickle
# import numpy as np
# from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary
# from sqlalchemy.orm import declarative_base, sessionmaker
# import datetime

# # Step 2: Establish a database connection
# database_url = 'sqlite:///your_database_name2.db'
# engine = create_engine(database_url)

# # Will return the engine instance
# Base = declarative_base()

# # Step 3: Define your data model
# class User(Base):
#     __tablename__ = 'users'

#     id = Column(Integer, primary_key=True)
#     username = Column(String(50), unique=True, nullable=False)
#     email = Column(String(100), unique=True, nullable=False)
#     password = Column(LargeBinary, nullable=False)  # Store NumPy arrays as LargeBinary
#     created_at = Column(DateTime, default=datetime.datetime.utcnow)

# # Step 4: Create the database tables
# Base.metadata.create_all(engine)

# # Step 5: Insert data into the database
# Session = sessionmaker(bind=engine)
# session = Session()

# # Example: Inserting a new user with a NumPy array
# data_array = np.array([1, 2, 3, 4, 5])
# serialized_array = pickle.dumps(data_array)

# new_user = User(username='Sandy', email='sandy@gmail.com', password=serialized_array)
# session.add(new_user)
# session.commit()

# # Step 6: Query data from the database
# all_users = session.query(User).all()

# # Example: Deserialize the NumPy array from the stored binary data
# queried_user = all_users[0]
# deserialized_array = pickle.loads(queried_user.password)
# print(f"Queried user's array: {deserialized_array}")

# # Step 7: Close the session
# session.close()


from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import threading
import time

# Connect to the SQLite database
database_url = 'sqlite:///example.db'
engine = create_engine(database_url)

# Will return the engine instance
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(Integer, unique=True, nullable=False)
    email = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Create the database tables
Base.metadata.create_all(engine)

def insert_user(username, email):
    # Create a session for each thread
    Session = sessionmaker(bind=engine)
    session = Session()
    session.query(User).delete()
    for i in range(100):
      # Insert a new user
      new_user = User(username=i+1000, email=i)
      session.add(new_user)
      session.commit()
      time.sleep(1)

    # Close the session
    session.close()

def query_users():
    # Create a session for each thread
    Session = sessionmaker(bind=engine)
    session = Session()
    session.query(User).delete()
    while True:
      # Query all users
      all_users = session.query(User).all()
      for user in all_users:
          print(f"User: {user.username}, {user.email}, {user.created_at}")
      time.sleep(1)


# Create and start two threads
thread1 = threading.Thread(target=insert_user, args=('User1', 'user1@example.com'))
thread2 = threading.Thread(target=query_users)

thread1.start()
thread2.start()

# Wait for both threads to finish
thread1.join()
thread2.join()
