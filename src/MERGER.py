import PARSER
from config import _config

class MERGER:
  """
  
  
  
  """

  def __init__(self,filename_feeds: str="FEEDS.json",filename_urls: str="SESSION_URLS.json"):

    self._parser=PARSER.PARSER()
    self._feed_list=_config.FEED_LIST
    
  def get_feeds(self):
    """
    Brief:
      Returns a list of feeds
    """
    return list(self._parser._feeds.keys())

  def feed_dictionary(self,feed: str,YEAR: str,NAME: str,SESSION: str):
    """
    Brief:
      Basically overrides jsonStream_parser of Parser class.
    """
    f_dict=self._parser.jsonStream_parser(YEAR=YEAR,NAME=NAME,SESSION=SESSION,FEED=feed)
    if f_dict!=-1:
      return f_dict
    else:
      return -1 

  def merger(self,YEAR: str,NAME: str,SESSION: str):
    """
    Brief:
      Loops over feeds_list, retrieve the dictionary response for each feed
      and merge each dictionary.

    Args:
      YEAR (str): year of session (eg '2023')
      NAME (str): name of event (eg 'Bahrain_Grand_Prix')
      SESSION (str): name of session (eg 'race')
    
    Returns:
      dict: merged dictionary for all feeds in feeds_list. Sorted for time of arrival
            of the messages.
    """
    print("Starting the merge..")
    list_of_feeds=self.get_feeds()
    merged_dict={}
    for feed in list_of_feeds:
      print("Preparing the merge of feed: ", feed, "...",end="")
      if feed in self._feed_list:
        feed_dict=self.feed_dictionary(feed=feed,YEAR=YEAR,NAME=NAME,SESSION=SESSION)
        if feed_dict != -1:
          merged_dict=merged_dict | feed_dict
          print("MERGED!")
        else:
          print("Failed to retrieve data..")
      else:
        print("SKIPPED!")
    return dict(sorted(merged_dict.items()))
