This is a python script to automatically manage labeling in Plex and remove unwanted french track when more than one french track exists in a media during 
import in Radarr.

This use Webhooks from both Plex and Radarr in order to do so.

Here is an example of Docker-Compose (compose.yaml) to launch it :

```yaml
services:
  mediaimport:
    container_name: mediaimport
    build: https://github.com/EtienneRod/MediaImport.git
    restart: unless-stopped
    user: "1000:1000" # Optionnal User that will be used in contrainer
    Ports:
      - "5000:5000" # Ports that flask will use in container
    environment:
      - TZ=America/Toronto # Optionnal, Default to America/Toronto, Change to you Timezone
      - PLEX_IP="0.0.0.0" # Required, Change to your Plex instance IP or FQDN
      - PLEX_PORT=32400 # Optionnal, Default to 32400, Change to your Plex instance listening port
      - PLEX_TOKEN="abc123" # Required, Change to your Plex toker https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token
      - PUSHOVER_KEY="abc123" # Required, Change to your Pushover key
      - PUSHOVER_TOKEN="abc123" # Required, Change to your Pushover token
      - FLASK_PORT=5000 # Optionnal, Default to 5000, Set Flask port inside contrainer
    volumes:
      - /mnt/Share/Medias:/mnt/Share/Medias  # Required, Change to your Media root folder
