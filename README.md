# ich_iel-Bot

A bot for Fluxer which posts a post from ich_iel every hour.

## Installation:

```
git clone https://git.scrunkly.cat/Michelle/ich_iel-Bot.git
```

```
docker compose build
docker compose up -d
```

Or if you prefer running it without docker:
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```