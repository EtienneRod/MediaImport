#!/usr/bin/python3

from flask import Flask, json, request
from pushover_complete import PushoverAPI
from datetime import date
import logging, lzma, tarfile, os, shutil, subprocess, sys, tomllib


# Set logging settings
logging.basicConfig(
  format="%(asctime)s %(levelname)-8s %(message)s",
  level=logging.INFO,
  datefmt="%Y-%m-%d %H:%M:%S")

# Define Variables
plexUrl=f"http://{os.environ.get('PLEX_IP')}:{os.environ.get('PLEX_PORT')}"
plexToken=f"{os.environ.get('PLEX_TOKEN')}"
pushoverKey=f"{os.environ.get('PUSHOVER_KEY')}"
pushoverToken=f"{os.environ.get('PUSHOVER_TOKEN')}"
flaskPort=f"{os.environ.get('FLASK_PORT')}"
vfqstrings=f"{os.environ.get('VFQ_STRINGS')}".casefold().split(',')

# Define Flask
app = Flask(__name__)

# Function removevff
def removevff(media, message):
    
    logging.info(f"------------------------------------------------------------")
    logging.info(f"Starting RemoveVFF")
    audio_streams = media.media[0].parts[0].audioStreams()
    vfq=[]
    notvfq=[]
    for stream in audio_streams:
        logging.info(f"Audio Title: {stream.title} - Language: {stream.languageCode}")
        if f"{stream.languageCode}" == f"fra" and f"{stream.title}":
            foundvfq=False
            for vfqstring in vfqstrings:
                if f"{vfqstring}" in f"{stream.title}".casefold():
                  vfq.append(f"{stream.index}")
                  foundvfq=True
            if foundvfq == False:
                notvfq.append(f"{stream.index}")
    if vfq and notvfq:
        mapstring=""
        for stream in notvfq:
            mapstring=f"-map -0:{stream}"
        mediapath = os.path.dirname(f"{media.media[0].parts[0].file}")
        mediafilename = os.path.basename(f"{media.media[0].parts[0].file}")
        logging.info(f"Path: {mediapath} - Filename: {mediafilename} - MapString: {mapstring}")
        result=subprocess.run([f"ffmpeg -hide_banner -i '{media.media[0].parts[0].file}' -map 0 {mapstring} -y -c copy '{mediapath}/TMP_{mediafilename}'"],
                              capture_output=True, text=True, shell=True)
        shutil.move(f"{mediapath}/TMP_{mediafilename}",f"{media.media[0].parts[0].file}")
        message=message+f"All non VFQ's French tracks removed from {media.title}\n"
    elif vfq and not notvfq:
        logging.info(f"All French audio tracks are VFQ in {media.title}, Nothing to do")
    elif not vfq and notvfq:
        logging.info(f"No French audio tracks are VFQ in {media.title}, Nothing to do")
    else:
        logging.info(f"No French audio tracks in {media.title}, Nothing to do")
    logging.info(f"Completed RemoveVFF")
    logging.info(f"------------------------------------------------------------")
    return message

# Function labeling
def labeling(plex, message):
    logging.info(f"------------------------------------------------------------")
    logging.info(f"Starting Labeling")
    with open("config/MediaImport.toml", "rb") as f:
        LabelConfig = tomllib.load(f)
    for kid in LabelConfig["Kid"]:
        kidname=kid["Name"]
        contentrating=kid["ContentRating"].split(',')
        commonsenseage = (date.today().year - kid["BDay"].year - ((date.today().month,date.today().day) < (kid["BDay"].month,kid["BDay"].day))) + kid["CommonSenseAgeOffset"]
        audiolanguage=kid["AudioLanguage"].split(',')
        excludedlabels=kid["Excluded_Labels"].split(',')
        excludedlabels.append(kidname)
        medias = []
        medias = medias + plex.library.section(f"Movies").search(filters = {f"label!":excludedlabels,
                                                                            f"audioLanguage__icontains|":audiolanguage})
        medias = medias + plex.library.section(f"Films").search(filters = {f"label!":excludedlabels,
                                                                           f"audioLanguage__icontains|":audiolanguage})
        medias = medias + plex.library.section(f"TV Shows").search(filters = {f"label!":excludedlabels,
                                                                              f"audioLanguage__icontains|":audiolanguage})
        medias = medias + plex.library.section(f"Séries TV").search(filters = {f"label!":excludedlabels,
                                                                               f"audioLanguage__icontains|":audiolanguage})
        labeled = False
        for media in medias:
            label = False
            if media.contentRating in contentrating:
                label = True
            elif media.commonSenseMedia != None:
                if media.commonSenseMedia.ageRatings[0].age <= commonsenseage :
                    label = True
            if label == True:
                labeled = True
                media.addLabel(kidname,locked=False)
                logging.info(f"Adding {kidname} label to : {media.title} in Library : {media.librarySectionTitle}")
                message=f"{message}"+f"Label {kidname} added to : {media.title} in Library : {media.librarySectionTitle}\n"
    if labeled == False:
        logging.info(f"No media needed labeling")
    logging.info(f"Completed labeling")
    logging.info(f"------------------------------------------------------------")
    return message

# Define Plex Webhook listener
@app.route(f"/webhook/plex",methods=[f"GET",f"POST"])
def plex_webhook():
    pushovermsg=f""
    data = json.loads(f"{request.form['payload']}")
    if f"{data["event"]}" == f"library.new" and (f"{data["Metadata"]["librarySectionTitle"]}" == f"Films" or f"{data["Metadata"]["librarySectionTitle"]}" == f"Séries TV"):
        from plexapi.server import PlexServer
        myplex = PlexServer(f"{plexUrl}",f"{plexToken}",timeout=120)
        plexmedia = myplex.fetchItem(f"{data["Metadata"]["key"]}")
        if f"{plexmedia.type}" == f"episode":
            logging.info(f"------------------------------------------------------------")
            logging.info(f"Show: {plexmedia.grandparentTitle} - Episode: {plexmedia.title} - Type: {plexmedia.type}")
        elif f"{plexmedia.type}" == f"movie":
            logging.info(f"------------------------------------------------------------")
            logging.info(f"Movie: {plexmedia.title} - Type: {plexmedia.type}")
        if f"{plexmedia.type}" == f"episode" or f"{plexmedia.type}" == f"movie":
            pushovermsg = removevff(plexmedia, f"{pushovermsg}")
        pushovermsg = labeling(myplex, f"{pushovermsg}")
        if pushovermsg:
            pushover = PushoverAPI(f"{pushoverToken}")
            logging.info(f"Pushover Message to send: {pushovermsg}")
            logging.info(f"------------------------------------------------------------")
            pushover.send_message(f"{pushoverKey}", f"{pushovermsg}", title=f"MediaImport")
        del pushovermsg
    return ''

# Main
if __name__ == "__main__":
  app.run(host="0.0.0.0", port=flaskPort, debug=True)
