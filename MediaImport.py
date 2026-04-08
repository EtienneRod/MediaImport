#!/usr/bin/python3

from flask import Flask, json, request
from pushover_complete import PushoverAPI
import logging, lzma, tarfile, os, shutil, subprocess, sys


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
contentrating=f"{os.environ.get('CONTENT_RATING')}".split(',')
commonsenseage=int(f"{os.environ.get('COMMONSENSE_AGE')}")
audiolanguage=f"{os.environ.get('AUDIO_LANGUAGE')}".split(',')
excludedlabels=f"{os.environ.get('EXCLUDED_LABELS')}".split(',')
vfqstrings=f"{os.environ.get('VFQ_STRINGS')}".split(',')

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
        if stream.languageCode == f"fra" and stream.title:
            if stream.title.casefold() in vfqstrings.casefold():
                vfq.append(f"{stream.index}")
            else:
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
    medias = plex.library.section("Films").search(filters = {"label!":excludedlabels,
                                                                      "contentRating|":contentrating,
                                                                      "audioLanguage|":audiolanguage})
    medias = medias + plex.library.section("Séries TV").search(filters = {"label!":excludedlabels,
                                                                          "contentRating|":contentrating,
                                                                          "audioLanguage|":audiolanguage})
    labeled = False
    for media in medias:
        label = False
        if media.commonSenseMedia != None:
            if media.commonSenseMedia.ageRatings[0].age <= commonsenseage:
                label = True
        else:
            label = True
        if label == True:
            labeled = True
            media.addLabel("Enfants",locked=False)
            logging.info(f"Adding Enfants label to : {media.title} in Library : {media.librarySectionTitle}")
            message=message+f"Label Enfants added to : {media.title} in Library : {media.librarySectionTitle}\n"
    if labeled == False:
        logging.info(f"No media needed labeling")
    logging.info(f"Completed labeling")
    logging.info(f"------------------------------------------------------------")
    return message

# Define Plex Webhook listener
@app.route("/webhook/plex",methods=["GET","POST"])
def plex_webhook():
    pushovermsg=f""
    data = json.loads(request.form['payload'])
    if data["event"] == f"library.new" and (data["Metadata"]["librarySectionTitle"] == f"Films" or data["Metadata"]["librarySectionTitle"] == f"Séries TV"):
        from plexapi.server import PlexServer
        myplex = PlexServer(plexUrl,plexToken)
        plexmedia = myplex.fetchItem(data["Metadata"]["key"])
        if f"{plexmedia.type}" == "episode":
            logging.info(f"------------------------------------------------------------")
            logging.info(f"Show: {plexmedia.grandparentTitle} - Episode: {plexmedia.title} - Type: {plexmedia.type}")
        elif f"{plexmedia.type}" == "movie":
            logging.info(f"------------------------------------------------------------")
            logging.info(f"Movie: {plexmedia.title} - Type: {plexmedia.type}")
        if f"{plexmedia.type}" == "episode" or f"{plexmedia.type}" == "movie":
            pushovermsg = removevff(plexmedia, pushovermsg)
        pushovermsg = labeling(myplex, pushovermsg)
        if pushovermsg:
            pushover = PushoverAPI(pushoverToken)
            logging.info(f"Pushover Message to send: {pushovermsg}")
            logging.info(f"------------------------------------------------------------")
            pushover.send_message(pushoverKey, f"{pushovermsg}", title="MediaImport")
        del pushovermsg
    return ''

# Main
if __name__ == "__main__":
  app.run(host="0.0.0.0", port=flaskPort, debug=True)
