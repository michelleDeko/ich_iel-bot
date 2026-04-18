# ich_iel-Bot

A bot for Fluxer which posts a post from ich_iel every hour.

## Installation:

Clone repo:
```
git clone https://git.scrunkly.cat/Michelle/ich_iel-Bot.git
```

Check .env file and add your FLUXER_TOKEN.

Then start the container:
```
docker compose up -d
```

Or if you prefer running it without docker:
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```