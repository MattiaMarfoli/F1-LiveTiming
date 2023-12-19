import json
import requests
import time
import zlib
import base64

def pako_inflate_raw(data):
    decompress = zlib.decompressobj(-15)
    decompressed_data = decompress.decompress(data)
    decompressed_data += decompress.flush()
    return decompressed_data




#Prova="https://livetiming.formula1.com/static/2023/2023-09-03_Italian_Grand_Prix/2023-09-03_Race/CarData.z.jsonStream"
#response = requests.get(Prova)
#roba=response.content

#print(roba.splitlines()[1020])
#text="5ZjPbtswDMbfRee04B9RpHwt9gbbZcMOxVBgA4Ycut6CvPtsWSnUmpkbHVp3BYIkcPyZ4kfqZzqH8Gn/cP/r7k8Yvh3Cl4cfYQgExFeQr4A/Iw1o4+s6xgSc8WvYhZvb+/HsQ8Dp7ebn7X5/97scgDBkFNoFCgOK7AKHIe5CDAPsgozHYPyM05fjsZzkyHMuvxBxkWuRcy76Vh0dNRQpFCE0cVsdQq/QS5dFa7pxIX6aLXYvODlCBFGcjcpa5FbkJebzC9jlkaEU6LxVspItecVFSGbzotNc3XR20cTOBdRIZrdJm+aavH8u73Wb9ALh05zZa5CXxIyezwhczcKcilyKPNNS7yU7mg2p6rE1yzFbxGvtTHOHMa4knrxaZZ1qPIVXa5Yvy52sL7McIdbYsRFbn+mj9F+wG60DjLYGOzOrOQr2wI4oObCLTodsA3bx1JH02rATcGCXl720IdZFqYBO0hT3AtbJB2JdlHkjEcQGFp5ZZ2Bn8QQ77YOdznMHr2Xuw85OY8B0mcf1p2X0DcLOTLLy+mSXEtZRR7tgx/C+JjvObwS7+P5gl6iuOeU+2CX6OLDTLBV22gU7pFgfkiCtXOAM7E6307Vqu7BDwNPWMG7iK2+fdvmaSTKsTnYj7GqKPNeIL4QdepMd21ZhF9PckulVWTe6XBvRrEGdG3g7rNNcF63Yx7rHG4u1rFs+1/0HrEOqfweVDdEz2HGuOwnXYOmzzrTquY91Wsd4zLwS/21g9/34Fw=="

#json_str = json.loads(pako_inflate_raw(base64.b64decode(text)).decode('utf-8'))

#print(json_str)