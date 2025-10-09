FROM python:3-slim

ENV TZ=America/Toronto FLASK_PORT=5000 PLEX_PORT=32400

RUN ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && echo ${TZ} > /etc/timezone

RUN apt update && apt -y dist-upgrade && apt -y install ffmpeg netcat-traditional && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 MediaImport && useradd -u 1000 -g MediaImport -ms /bin/bash MediaImport

USER MediaImport

RUN pip install plexapi Flask pushover-complete

HEALTHCHECK CMD nc -z localhost ${FLASK_PORT}  || exit 1

COPY --chown=1000:1000 MediaImport.py /home/MediaImport/MediaImport.py

CMD ["python","/home/MediaImport/MediaImport.py"]
