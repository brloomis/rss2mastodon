#!/usr/bin/env python3

"""
RSS -> Fediverse gateway

AI6YR - Nov 2022
"""
# imports (obviously)
import configparser
from mastodon import Mastodon
import requests
import time
from datetime import datetime
import dateutil
import json
import feedparser
from bs4 import BeautifulSoup
import re
import tempfile
import shutil
from PIL import Image
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
import html
import magic
import argparse
import os
import html
import sys

def read_timefile(timefile: str) -> int:
    if os.path.exists(timefile):
        with open(timefile, "rb") as f:
            raw_val = f.read()
            try:
                return int(raw_val, 10)
            except ValueError:
                print("Read garbage from the time file:", raw_val)
                return 0
    return 0
def write_timefile(timefile: str, spottime: int) -> None:
    with open(timefile, "w") as f:
        f.write(str(int(spottime)))


# Load the config
config = configparser.ConfigParser()
parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Config file", dest="config_file", default="config.ini")
parser.add_argument("--timefile", help="Timestamp file", dest="timefile", default=None)
parser.add_argument("--dryrun", help="Dry run, do not post anything", dest="dryrun", action="store_true")
args = parser.parse_args()

if not os.path.exists(args.config_file):
   print("No config file found")
   parser.print_usage()
   sys.exit()
config.read(args.config_file)

feedurl = config['feed']['feed_url']
feedname = config['feed']['feed_name']
feedvisibility = config['feed']['feed_visibility']
feedtags = config['feed']['feed_tags']
try:
   max_image_size  = int(config['mastodon']['max_image_size'])
except:
   max_image_size = 1600
try:
   feeddelay  = int(config['feed']['feed_delay'])
except:
   feeddelay = 180
try:
   linkfeed  = config['feed']['feed_link'].lower()
except:
   linkfeed = "false"
try:
   usetitle  = config['feed']['use_title'].lower()
except:
   usetitle = "false"

print (feedurl)
print (feedname)
# connect to mastodon
mastodonBot = Mastodon(
    access_token=config['mastodon']['access_token'],
    api_base_url=config['mastodon']['app_url']
)

print ("Starting RSS watcher:" + feedname)
lastpost = ""
maxspottime = 0
lastspottime = 0
if args.timefile:
    print(f"Using {args.timefile} as starting time")
    lastspottime = read_timefile(args.timefile)
    print(f"Read {lastspottime}")
else:
    lastspottime = datetime.now().timestamp()
    print(f"No timefile, using {lastspottime} as starting time")
while(1):
   try:
    data = (feedparser.parse(feedurl))
    entries = data["entries"]
    for entry in entries:
  #       print ("----------------")
#        print (entry)
         link = ""
         if (linkfeed == "true"):
             try:
                link = entry['link']
             except:
                pass
         if (usetitle == "true"):
            clean = re.sub("<.*?>", "", entry['title'])
         else:
            clean = re.sub("<.*?>", "", entry['summary'])
         clean = html.unescape(clean)
         clean = clean.replace("&amp;","&")
         clean = clean.replace(" nitter.net","https://nitter.net")
         clean = clean.replace(" nitter.poast.org","https://nitter.poast.org")
         clean = clean.replace(" go.usa.gov","https://go.usa.gov")
         clean = clean.replace(" wpc.ncep.noaa.gov","https://wpc.ncep.noaa.gov")
         clean = clean.replace(" weather.gov"," https://weather.gov")
         clean = clean.replace(" nwschat.weather.gov"," https://nwschat.weather.gov")
         clean = clean.replace(" bit.ly"," https://bit.ly")
         clean = clean.replace(" owl.ly"," https://owl.ly")
         clean = clean.replace(" t.co"," https://t.co")
         tootText = clean + feedtags 
         tootText = clean[:474] + " " + link
         spottime = dateutil.parser.parse(entry['published']).timestamp()
         if (spottime > maxspottime):
            maxspottime = spottime
         title = entry['title']
         firsttwo = title[:2]
         firstthree = title[:3]
         #print("debug: spottime:",spottime)
         #print("debug: lastspottime:",lastspottime)
         if (spottime > lastspottime):
        # if (1):
        #   print (tootText)
        #   time.sleep(10)
           if (clean == lastpost):
               print ("skip: retweet")
           elif ("RT" in firsttwo):
               print ("skip: retweet")
           elif ("Re" in firstthree):
               print ("skip: reply")
           else:
              isposted = False
              print (clean)
              soup = BeautifulSoup(entry['summary'], 'html.parser')
              medialist = []
              for video in soup.findAll('source'):
                print("***VIDEO:",video.get('src'))
                imgfile = video.get('src')
                temp = tempfile.NamedTemporaryFile()
                res = requests.get(imgfile, stream = True)
                if res.status_code == 200:
                    shutil.copyfileobj(res.raw, temp)
                    print('Image sucessfully Downloaded')
                    print (temp.name)
                    if(False == args.dryrun):
                      try:
                        mediaid = mastodonBot.media_post(temp.name, mime_type="video/mp4")
                        medialist.append(mediaid)
                      except Exception as e:
                        print (e)
                        print ("Unable to upload video")
                    else:
                      print("Dry run: Not posting media from", temp.name)

                else:
                       print('Video Couldn\'t be retrieved')
                temp.close()
              for img in soup.findAll('img'):
                print("***IMAGE:",img.get('src'))
                imgfile = img.get('src')
                temp = tempfile.NamedTemporaryFile()
                res = requests.get(imgfile, stream = True)
                if res.status_code == 200:
                    shutil.copyfileobj(res.raw, temp)
                    print('Image sucessfully Downloaded')
                    print (temp.name)
                    #ensure image will fit on server
                    image = Image.open(temp.name)
                    if ((image.size[0]>max_image_size) or (image.size[1]>max_image_size)):
                        origx = image.size[0]
                        origy = image.size[1]
                        if (origx>origy):
                             newx = int(max_image_size)
                             newy = int(origy * (max_image_size/origx))
                        else:
                             newy = int(max_image_size)
                             newx = int(origx * (max_image_size/origy))
                        image = image.resize((newx,newy))
                        print ("new image size",image.size)
                        image.save(temp, format="png")
                    if(False == args.dryrun):
                     try:
                        mediaid = mastodonBot.media_post(temp.name, mime_type="image/png")
                        medialist.append(mediaid)
                     except Exception as e:
                        print ("Unable to upload image.")
                        print (e)
                    else:
                      print("Dry run: Not posting media from", temp.name)
                else:
                       print('Image Couldn\'t be retrieved')
                temp.close()
              if (isposted == False):
                   if(False == args.dryrun):
                     try:
                        postedToot = mastodonBot.status_post(tootText,None,medialist,False,feedvisibility)
                        lastpost = postedToot
                     except Exception as e:
                        print(e)
                   else:
                     print("Dry run: Not posting toot text:", tootText)
                     print("Dry run: Not posting toot media:", medialist)
         else:
            print("not posting", entry['title'], spottime)
                    
    lastspottime = maxspottime #set last update to the newest update we saw in the list
    if(args.timefile and (not args.dryrun)):
        print(f"Writing {lastspottime} to timefile")
        write_timefile(args.timefile, lastspottime)
    #print("debug: lastspottime now ",lastspottime)
   except Exception as e:
      print (e) 
   time.sleep(feeddelay)
