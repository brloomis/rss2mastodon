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
feeddelay = int(config['feed']['feed_delay'])
if (feeddelay < 60):
     feeddelay = 300
max_image_size  = int(config['mastodon']['max_image_size'])
print (feedurl)
print (feedname)
# connect to mastodon
mastodonBot = Mastodon(
    access_token=config['mastodon']['access_token'],
    api_base_url=config['mastodon']['app_url']
)

print ("Starting RSS watcher:" + feedname)
lastpost = ""
lastspottime = 0

if args.timefile:
    print(f"Using {args.timefile} as starting time")
    lastspottime = read_timefile(args.timefile)
    print(f"Read {lastspottime}")
else:
    lastspottime = datetime.now().timestamp()
    print(f"No timefile, using {lastspottime} as starting time")

maxspottime = 0

while(1):
    data = (feedparser.parse(feedurl))
    entries = data["entries"]
#    print (entries)
    # sort entries by timestamp (oldest first)
    entries_sorted = sorted(entries, key=lambda x: dateutil.parser.parse(x['published']).timestamp(), reverse=False)
    for entry in entries_sorted:
         #print (entry['summary'])
         try:
           link = entry['link']
         except:
           link = ""
         #print("**RAW summary:", entry['summary'])
         clean = re.sub("<.*?>", "", entry['summary'])
         #print("***CLEAN html:", clean)
         clean = clean.replace("&amp;" ,"&")
         clean = clean.replace("&nbsp;" ," ")
         #print("***CLEAN subbed:", clean)
         clean = html.unescape(clean)

         spottime = dateutil.parser.parse(entry['published']).timestamp()
         if spottime > maxspottime:
            maxspottime = spottime
         firsttwo = clean[:2]
         firstthree = clean[:3]
#         if (1):
         if (spottime > lastspottime):
           if (clean == lastpost):
               print ("skip: retweet")
           elif ("RT" in firsttwo):
               print ("skip: retweet")
           elif ("Re" in firstthree):
               print ("skip: reply")
           else:
              isposted = False
              print (clean)
              tootText = clean + " " + feedtags 
              tootText = tootText[:475]
              tootText = tootText + " " + link
              soup = BeautifulSoup(entry['summary'], 'html.parser')
              medialist = []
              for img in soup.findAll('img'):
                print("***IMAGE:",img.get('src'))
                imgfile = img.get('src')
                temp = tempfile.NamedTemporaryFile()
                res = requests.get(imgfile, stream = True)
                if res.status_code == 200:
                    shutil.copyfileobj(res.raw, temp)
                    print('Image sucessfully Downloaded')
                    print (temp.name)
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
                        mediaid = mastodonBot.media_post(temp.name, mime_type="image/jpeg")
                        medialist.append(mediaid)
                    else:
                        print("Dry run: Not posting media from", temp.name)
                else:
                       print('Image Couldn\'t be retrieved')
                temp.close()

              try:
                if(False == args.dryrun):
                    postedToot = mastodonBot.status_post(tootText,None,medialist,False,feedvisibility)
                    lastpost = clean
                else:
                    print("Dry run: Not posting toot text:", tootText)
                    print("Dry run: Not posting toot media:", medialist)
              except Exception as e:
                    print(e)
         else:
            print(entry["title"], "article time of",spottime, "is earlier than lastspottime", lastspottime)
            print(datetime.fromtimestamp(spottime), "<", datetime.fromtimestamp(lastspottime))
                    
    #lastspottime = datetime.now().timestamp()
    lastspottime = maxspottime
    if(args.timefile and (not args.dryrun)):
        print(f"Writing {lastspottime} to timefile")
        write_timefile(args.timefile, lastspottime)
    print("maxspot:", lastspottime)
#    print ("time:",now)
    time.sleep(feeddelay)
