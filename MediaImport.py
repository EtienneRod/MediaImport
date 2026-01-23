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
excludedlabels=f"{os.environ.get('EXCLUDED_LABLES')}".split(',')

# Define Flask
app = Flask(__name__)

# Function removevff
def removevff(plex, mediaid):
    global pushovermsg
    media = plex.fetchItem(f"{mediaid}")
    filename=f"{media.media[0].parts[0].file}"
    logging.info(f"Title: {media.title} - Filename: {filename}")
    print(repr({filename}))
    if f"[VF2]" in f"{filename}":
        result = subprocess.run([f"ffprobe -v quiet -print_format json -show_streams -i '{filename}'"],
                                capture_output=True, text=True, shell=True)
        probe_output = json.loads(result.stdout)
        streams = probe_output["streams"]
        audiovff = []
        for stream in streams:
            if stream["codec_type"] == "audio" and any(sub in stream["tags"]["title"].lower() for sub in
                                                       ["vff","france","truefrench"]) :
                audiovff.append(stream["index"])
        logging.info(f"Audio Track(s) to remove : {audiovff}")
        for track in audiovff: # Remove all French (France) tracks
            mediapath = os.path.dirname(f"{filename}")
            mediafilename = os.path.basename(f"{filename}")
            logging.info(f"Path: {mediapath} - Filename: {mediafilename}")
            result=subprocess.run(
                    [f"ffmpeg -hide_banner -i '{filename}' -map 0 -map -0:{track} -y -c copy '{mediapath}/TMP_{mediafilename}'"],
                    capture_output=True, text=True, shell=True)
            shutil.move(f"{mediapath}/TMP_{mediafilename}",f"{filename}")
            shutil.move(f"{filename}",filename.replace(f"[VF2]", f""))
            logging.info(f"Track {track} removed from {media.title}")
        logging.info(f"VFF removed from {media.title}")
        pushovermsg=pushovermsg+f"VFF removed from {media.title}\n"

# Function labeling
def labeling(plex):
    global pushovermsg
    medias = plex.library.section("Movies").search(filters = {"label!":excludedlabels,
                                                               "contentRating|":contentrating})
    medias = medias + plex.library.section("Films").search(filters = {"label!":excludedlabels,
                                                               "contentRating|":contentrating})
    medias = medias + plex.library.section("TV Shows").search(filters = {"label!":excludedlabels,
                                                                             "contentRating|":contentrating,
                                                                             "audioLanguage|":audiolanguage})
    medias = medias + plex.library.section("Séries TV").search(filters = {"label!":excludedlabels,
                                                                             "contentRating|":contentrating,
                                                                             "audioLanguage|":audiolanguage})
    for media in medias:
        label = False
        if media.commonSenseMedia != None:
            if media.commonSenseMedia.ageRatings[0].age <= commonsenseage:
                label = True
        else:
            label = True
        if label == True:
            media.addLabel("Enfants",locked=False)
            logging.info(f"Adding Enfants label to : {media.title}")
            pushovermsg=pushovermsg+f"Label Enfants added to : {media.title}\n"
    logging.info(f"Completed labeling")

# Define Plex Webhook listener
@app.route("/webhook/plex",methods=["GET","POST"])
def plex_webhook():
    headers = dict(request.headers)
    print("--- Headers ---")
    for key, value in headers.items():
        print(f"{key}: {value}")
    print("---------------")
    data = json.loads(request.form['payload'])
    if data["event"] == "library.new":
        from plexapi.server import PlexServer
        myplex = PlexServer(plexUrl,plexToken)
        removevff(myplex,data["Metadata"]["key"])
        labeling(myplex)
        pushover = PushoverAPI(pushoverToken)
        logging.info(f"Pushover Message to send: {pushovermsg}")
        pushover.send_message(pushoverKey, f"{pushovermsg}", title="MediaImport")
    return ''

# Main
if __name__ == "__main__":
  app.run(host="0.0.0.0", port=flaskPort, debug=True)
