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


# Define Flask
app = Flask(__name__)

# Define Plex Webhook listener
@app.route("/webhook/plex",methods=["GET","POST"])
def plex_webhook():
    data = json.loads(request.form['payload'])
    if data["event"] == "library.new": # verify if Webhook has been reached bacause of a Plex new item
        from plexapi.server import PlexServer
        myplex = PlexServer(plexUrl,plexToken)
        if data["Metadata"]["librarySectionTitle"]=="Movies": # verify if it's a movie
            logging.info("Labeling Movies...")
            for media in myplex.library.section("Movies").search(filters = {"label!":["Enfants","Exclude"],"contentRating|":["G","PG","TV-G","TV-PG","TV-Y","ca/G","ca/PG","ca/TV-PG","ca/TV-Y7"],"audioLanguage|":["French","french-canadian"]}): # Add Enfants label to movies for kids
                media.addLabel("Enfants",locked=False)
                logging.info(f"Adding Enfants label to movie : {media.title}")
                pushover=PushoverAPI(pushoverToken)
                pushover.send_message(pushoverKey, f"Label Enfants added to movie : {media.title}", title="MediaImport")
        elif data["Metadata"]["librarySectionTitle"]=="TV Shows": # verify if it's a TV Show
            logging.info("Labeling TV Show...")
            for media in myplex.library.section("TV Shows").search(filters = {"label!":["Enfants","Exclude"],"contentRating|":["G","PG","TV-G","TV-PG","TV-Y","ca/G","ca/PG","ca/TV-PG","ca/TV-Y7"],"audioLanguage|":["French","french-canadian"]}): # Add Enfants label to TV Shows for kids
                media.addLabel("Enfants",locked=False)
                logging.info(f"Adding Enfants label to TV show : {media.title}")
                pushover = PushoverAPI(pushoverToken)
                pushover.send_message(pushoverKey, f"Label Enfants added to TV show {media.title}", title="MediaImport")
    return ''

# Define Radarr Webhook listener
@app.route("/webhook/radarr",methods=["POST"])
def radarr_webhook():
    data = request.json
    if "Test Title" not in  data["movie"]["title"]: # If this is a Test from Radarr GUI, if yes, don't proceed
        if "[VF2]" in data["movieFile"]["relativePath"]: # Verify if [VF2] in file name, if yes, extract streams from file
            result = subprocess.check_output([
                f"ffprobe",
                f"-v",
                f"quiet",
                f"-print_format",
                f"json",
                f"-show_streams",
                f"-i",
                f"{data['movieFile']['path']}",
            ])
            probe_output = json.loads(result)
            streams = probe_output["streams"]
            audiovff = []
            for stream in streams:
                if stream["codec_type"] == "audio" and any(sub in stream["tags"]["title"].lower() for sub in ["vff","france","truefrench"]) : # Verifié if streams are audio and French (France)
                    audiovff.append(stream["index"])
            logging.info(f"Audio Track(s) to remove : {audiovff}")
            for track in audiovff: # Remove all French (France) tracks
                result=subprocess.call([
                    f"ffmpeg",
                    f"-hide_banner",
                    f"-i",
                    f"{data['movieFile']['path']}",
                    f"-map",
                    f"0",
                    f"-map",
                    f"-0:{track}",
                    f"-y",
                    f"-c",
                    f"copy",
                    f"{data['movie']['folderPath']}/TMP_{data['movieFile']['relativePath']}"
                ])
                shutil.move(f"{data['movie']['folderPath']}/TMP_{data['movieFile']['relativePath']}",f"{data['movieFile']['path']}")
                logging.info(f"Track {track} removed from {data['movie']['title']}")
            logging.info(f"VFF removed from {data['movie']['title']}")
            pushover = PushoverAPI(pushoverToken)
            pushover.send_message(pushoverKey, f"VFF removed from {data['movie']['title']}", title="MediaImport")
    return ''

# Main
if __name__ == "__main__":
  app.run(host="0.0.0.0", port=flaskPort, debug=True) 
