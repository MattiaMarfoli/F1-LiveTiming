import logging
from config import _config


for i in range(10):
  try:
      if i==0:
        printf(i)
      elif i==1:
        1/0
      elif i==2:
        print(12+"1"+int("proav"))
      elif i==3:
        print(a)
  except Exception as err:
      _config.WRITE_EXCEPTION(err)
