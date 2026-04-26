# shrimpbot

A Discord bot for the Star Wars: Armada community. It rolls dice, looks up card images, explains acronyms, and generates [VASSAL](https://vassalengine.org/) game files from fleet lists posted in chat.

## Features

| Command | What it does |
|---|---|
| `!ROLL 3red 2blue 1black` | Rolls Armada attack dice and posts results with emoji |
| `!CARD <name>` / `!LOOKUP <name>` | Posts the card image for a ship, squadron, or upgrade |
| `!ACRO <term>` / `!DEFINE <term>` | DMs you the definition of an Armada acronym |
| `!VASSAL` + fleet list | Generates a VASSAL `.vlog` file from a pasted fleet list |
| `!listhelp` | DMs instructions for loading a generated VASSAL file |

`!VASSAL` accepts lists from Armada Warlords, Ryan Kingston's fleet builder, Armada Fleets Designer, and Fab's Fleet Builder. Paste the full list text after the command.

## Adding the hosted bot to your server

[Invite link](https://discord.com/oauth2/authorize?client_id=418136901401182208&permissions=1409416416&scope=bot)

A few functions require server-owner permissions. These are mostly for my own server — if you'd rather not grant them, decline them; everything you actually want will still work.

## Self-hosting

### Prerequisites

- Python 3.10+
- A Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))
- The Armada VASSAL module file (`.vmod`) — available from [vassalengine.org](https://vassalengine.org/wiki/Module:Star_Wars:_Armada)

### Setup

```sh
git clone git@github.com:sprintska/shrimpbot.git /opt/shrimpbot
cd /opt/shrimpbot

# Create and activate virtual environment
python3 -m venv .venv/shrimpbot
source .venv/shrimpbot/bin/activate
pip install -r requirements.txt

# Add your Discord bot token
echo "your-token-here" > privatekey.dsc

# Place your .vmod file in vmods/ and build the piece database
mkdir -p vmods data
# copy your .vmod into vmods/, then:
scripts/update_listbuilder.py -m vmods/
```

### Deployment (systemd)

Wire up the symlinks and service files with the included setup script:

```sh
sudo deploy/setup.sh
sudo systemctl enable shrimpbot shrimpbot-api
sudo systemctl start shrimpbot shrimpbot-api
```

The API is served by gunicorn behind a reverse proxy. See `deploy/shrimpbot-api.service` for the bind address and `deploy/shrimpbot.service` for the bot process configuration.

### Updating

```sh
update
```

The `update` script (symlinked to `/usr/sbin/update` by `setup.sh`) pulls the latest code, updates dependencies, rebuilds the piece database from the most recent `.vmod` in `vmods/`, and restarts the services.

## Project structure

```
shrimpbot/
├── shrimpbot.py          # Discord bot entry point
├── api.py                # Flask REST API entry point
├── wsgi.py               # gunicorn entry point
├── cardpop.py            # Wiki image fallback for card lookup
├── data/                 # Static data (acronyms, card index, piece database, card images, vmods)
├── libs/                 # Internal libraries (listbuilder, updater, cardpop)
├── scripts/              # Maintenance scripts
├── deploy/               # Deployment config (systemd units, update script, setup)
├── test/                 # Tests
└── var/                  # Runtime state (gitignored except templates)
    ├── working/          # Scratch space and VASSAL boilerplate templates
    └── out/              # Generated .vlog output files
```

## Logging and Retention Disclosure

Shrimpbot logs all message traffic it sees for troubleshooting and monitoring. Logs are retained for six months. Log entries look like:

```
INFO:root:[Wed Mar 17 10:21:24 2021 | Server Name | channel-name | Username] Message content.
```

## Fair Use Statement

I am not a lawyer. If you have legal concerns about this bot's content, please reach out rather than litigating.

This software may include copyrighted material from Star Wars: Armada, developed by Fantasy Flight Games and Atomic Mass Games, published by Asmodee, and licensed from Disney/Lucasfilm. I have no association with any of these entities and make no claim on their intellectual property. Any such material is reproduced under the Fair Use Doctrine (17 U.S.C. § 107) for commentary and educational purposes.
