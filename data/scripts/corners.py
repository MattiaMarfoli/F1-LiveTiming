import cv2
import numpy as np 
import matplotlib.pyplot as plt
import json
import tqdm

corner=[255,0,0]
key_points=[0,0,255]
sectors=[0,255,0]
bckg=[255,255,255]

def distance(x1,y1,x2,y2):
  return np.sqrt((x2-x1)**2 + (y2-y1)**2)

def find_next_point(p1,points):
  min_dist=1e6
  for p2 in points:
    dist=distance(p1[0],p1[1],p2[0],p2[1])
    if dist<min_dist:
      min_dist=dist
      next_p=p2
  return next_p

path="/home/marfo99/Projects/F1_LiveTiming/Maps/"
name="LasVegas_22.png"
image = cv2.imread(path+name)
POINTS=[]
CORNERS=[]
SECTORS=[]
START=[]
print(len(image[:,0,0]))
print(len(image[0,:,0]))
for x in range(len(image[:,0,0])):
  for y in range(len(image[0,:,0])):
    point=image[x,y,:]
    #print(point)
    if (point!=bckg).any():
      POINTS.append([x,y])
    if (point==corner).all():
      CORNERS.append([x,y])
    if (point==key_points).all():
      START.append([x,y]) 
    if (point==sectors).all():
      SECTORS.append([x,y]) 
print(len(POINTS))
POP_CORNER=[]
for i in range(1,len(CORNERS)):
  if distance(CORNERS[i-1][0],CORNERS[i-1][1],CORNERS[i][0],CORNERS[i][1])<5:
    POP_CORNER.append(CORNERS[i])
for c in POP_CORNER:
  CORNERS.remove(c)
z=1
for c in CORNERS:
  print(z,c)
  z+=1
POINTS.remove(START[0])
POINTS.insert(0,START[0])
PATH=[]
PATH.append(POINTS[0])
NPOINTS=len(POINTS)
i=1
CORNERS_SORTED=[]
#print(i," ",POINTS[0])
for i in tqdm.tqdm(range(NPOINTS)):
  i+=1
  p1=POINTS[0]
  POINTS.remove(p1)
  if len(POINTS)>0:
    p2=find_next_point(p1,POINTS)
    PATH.append(p2)
    POINTS.remove(p2)
    POINTS.insert(0,p2)
    #print(i," ",p2)
    if p2 in CORNERS:
      CORNERS_SORTED.append(p2)
PATH.append(PATH[0])

cumulative_distances = np.zeros(len(PATH))
for i in range(1, len(PATH)):
    cumulative_distances[i] = cumulative_distances[i - 1] + np.linalg.norm(np.array(PATH[i]) - np.array(PATH[i - 1]))

rel_distances=cumulative_distances/cumulative_distances[-1]

INDEX_CORNERS=[]
for index,point in zip(range(len(PATH)),PATH):
  if point in CORNERS_SORTED:
    INDEX_CORNERS.append(index+1)

z=1
# track length in meters
if name=="LasVegas_23.png":
  TRUE_DIST=6201 
elif name=="LasVegas_22.png":
  TRUE_DIST=6201
elif name=="Brazil_23.png":
  TRUE_DIST=4309

Map_json={"rel_distance": {},
          "distance": {}}
for i in INDEX_CORNERS:  
  Map_json["rel_distance"][z]=rel_distances[i]
  Map_json["distance"][z]=rel_distances[i]*TRUE_DIST
  z+=1

f=open("data/"+name.split(".")[0]+".json","w")
json.dump(Map_json,f,indent=2)
f.close()

my_dpi=96
plt.figure(figsize=(500/my_dpi, 500/my_dpi), dpi=my_dpi)
plt_name="data/"+name.split(".")[0]+"_plot.png"
fig,ax=plt.subplots()
x=[point[0] for point in PATH]
y=[point[1] for point in PATH]
#plt.gca().invert_yaxis()
ax.plot(y,x,c="grey",alpha=0.25)
for corner in CORNERS_SORTED:
  ax.plot(corner[1],corner[0],ls="",marker="x",c="red")
ax.axis("off")
#plt.show()
plt.savefig(plt_name, transparent=True)