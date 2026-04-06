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
    user: "1000:1000" # Optional. User that will be used in contrainer
    ports:
      - "5000:5000" # Optional, Default to 5000. Ports for Flask
    environment:
      - TZ=America/Toronto # Optional, Default to America/Toronto. Change to you Timezone
      - PLEX_IP="0.0.0.0" # Required. Change to your Plex instance IP or FQDN
      - PLEX_PORT=32400 # Optional. Default to 32400, Change to your Plex instance listening port
      - PLEX_TOKEN="abc123" # Required. Change to your Plex toker https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token
      - PUSHOVER_KEY="abc123" # Required. Change to your Pushover key
      - PUSHOVER_TOKEN="abc123" # Required. Change to your Pushover token
      - FLASK_PORT=5000 # Optional, Default to 5000. Set Flask port inside contrainer, make sure this port is forwarded
      - CONTENT_RATING="G,PG,TV-G,TV-PG,TV-Y,ca/G,ca/PG,ca/TV-PG,ca/TV-Y7" # Optionnal, Default to "G,PG,TV-G,TV-PG,TV-Y,ca/G,ca/PG,ca/TV-PG,ca/TV-Y7". Content rating neede to label Enfants based on Plex content rating filters
      - COMMONSENSE_AGE=12 # Optional, Default to 12. Maximum Common Sense Age Rating in order to add label Enfants
      - AUDIO_LANGUAGE="French,french-canadian" #Optionnal, Default to "French,french-canadian". Language needed to add label Enfants
      - VFQ_STRINGS = "VFQ,Québécois" #Optionnal, default to "VFQ,Québécois"
      - EXCLUDED_LABLES="Enfants,ExcludeEnfants" #Optionnal, Default to "Enfants,ExcludedEnfants". Labels to exclude when searching for new content to label
    volumes:
      - /mnt/Share/Medias:/mnt/Share/Medias  # Required. Change to your Media root folder
