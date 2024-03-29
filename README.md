# shrimpbot
Shrimpbot on Discord

## Usage Instructions
To add my instance of the bot to your server, follow this link and authorize the bot with the prompted roles:  https://discord.com/api/oauth2/authorize?client_id=418136901401182208&permissions=1409416416&scope=bot.

There are a few relatively minor functions that require server-owner level permissions.  Those are mostly for my own server, so if you don't feel comfortable granting those permissions, feel free to deny them--everything you actually want will still work fine.

Alternatively, you can run your own bot using this source code if you're comfortable doing that.  To do this, you'll need to request a bot token from Discord Developer Portal (essentially, you would create your own bot account with Discord, and power it with this code).
 * link here: https://discordapp.com/developers/applications/
 * steps documented here: https://www.writebots.com/discord-bot-token/
 
Copy the bot's token and paste it into a blank file named privatekey.dsc in the top-level directory of the shrimpbot.

## Logging and Retention Disclosure
Shrimpbot logs all message traffic that it sees for troubleshooting and performance & traffic monitoring.  These logs have a six-month retention.  Log entries look like this:

INFO:root:[Wed Mar 17 10:21:24 2021 | Star Wars: Armada | rules-discussions | Ardaedhel] Good night.

## Fair Use Statement
I am not a lawyer.  If you object to any of the content of this bot on legal grounds, please don't sue me--just talk to me.  

This software may include without permission copyrighted material from Star Wars Armada, developed by Fantasy Flight Games and Atomic Mass Games and published by Asmodeee, as licensed to them by Disney.  I have no association with any of these entities, and have no claim on any of their intellectual property.  Any images or other IP owned by AMG, FFG, Asmodee, Disney, Lucasfilm, or anyone else is their property, and is reproduced here under the Fair Use Doctrine (Section 107, US Copyright Act) for commentary and teaching purposes.
