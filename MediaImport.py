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

# Define Plex Webhook listener
@app.route("/webhook/plex",methods=["GET","POST"])
def plex_webhook():
    data = json.loads(request.form['payload'])
    if data["event"] == "library.new":
        from plexapi.server import PlexServer
        myplex = PlexServer(plexUrl,plexToken)
        medias = myplex.library.section("Movies").search(filters = {"label!":excludedlabels, "contentRating|":contentrating})
        medias = medias + myplex.library.section("Films").search(filters = {"label!":excludedlabels, "contentRating|":contentrating})
        medias = medias + myplex.library.section("TV Shows").search(filters = {"label!":excludedlabels, "contentRating|":contentrating, "audioLanguage|":audiolanguage})
        medias = medias + myplex.library.section("Séries TV").search(filters = {"label!":excludedlabels, "contentRating|":contentrating, "audioLanguage|":audiolanguage})
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
                pushover=PushoverAPI(pushoverToken)
                pushover.send_message(pushoverKey, f"Label Enfants added to : {media.title}", title="MediaImport")
        logging.info(f"Completed labeling")
    return ''

# Define Radarr Webhook listener
@app.route("/webhook/radarr",methods=["POST"])
def radarr_webhook():
    data = request.get_json(silent=True)
    if "Test Title" not in  data["movie"]["title"]: # If this is a Test from Radarr GUI, if yes, don't proceed
        if "[VF2]" in data["movieFile"]["relativePath"]: # Verify if [VF2] in file name, if yes, extract streams from file
            result = subprocess.run([f"ffprobe -v quiet -print_format json -show_streams -i {data['movieFile']['path']}"], capture_output=True, text=True, shell=True)
            probe_output = json.loads(result.stdout)
            logging.info(f"{probe_output}")
            streams = probe_output["streams"]
            audiovff = []
            for stream in streams:
                if stream["codec_type"] == "audio" and any(sub in stream["tags"]["title"].lower() for sub in ["vff","france","truefrench"]) : # Verifié if streams are audio and French (France)
                    audiovff.append(stream["index"])
            logging.info(f"Audio Track(s) to remove : {audiovff}")
            for track in audiovff: # Remove all French (France) tracks
                result=subprocess.run([f"ffmpeg -hide_banner -i {data['movieFile']['path']} -map 0 -map -0:{track} -y -c copy {data['movie']['folderPath']}/TMP_{data['movieFile']['relativePath']}"], capture_output=True, text=True, shell=True)
                shutil.move(f"{data['movie']['folderPath']}/TMP_{data['movieFile']['relativePath']}", f"{data['movieFile']['path']}")
                logging.info(f"Track {track} removed from {data['movie']['title']}")
            logging.info(f"VFF removed from {data['movie']['title']}")
            pushover = PushoverAPI(pushoverToken)
            pushover.send_message(pushoverKey, f"VFF removed from {data['movie']['title']}", title="MediaImport")
    return ''

# Main
if __name__ == "__main__":
  app.run(host="0.0.0.0", port=flaskPort, debug=True)
