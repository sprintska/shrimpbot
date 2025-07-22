#!/usr/bin/env python3

import asyncio
import cardpop
import discord
import hashlib
import listbuilder
import logging
import logging.handlers
import os
import random
import re
import requests
import shutil
import sqlite3
import time
import update_listbuilder

from discord import emoji
from discord.ext import commands
from fuzzywuzzy import fuzz

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)

PWD = os.path.dirname(__file__)
TOKEN_PATH = PWD + "/privatekey.dsc"
CARD_IMG_PATH = PWD + "/img/"
CARD_LOOKUP = PWD + "/cards.txt"
ACRO_LOOKUP = PWD + "/acronyms.txt"
BOT_OWNER_ID = 236683961831653376


with open(TOKEN_PATH) as t:
    BOT_TOKEN = t.read().strip()

enabled = True
cheating = False  # Changes on login to default to False
special_chars = "~`@#$%^&* ()_-+=|\\{}[]:;\"'<>,.?/!"

cardlookup = {}
with open(CARD_LOOKUP) as cardslist:
    for line in cardslist.readlines():
        filename, key = line.split(";")
        cardlookup[key.rstrip()] = os.path.join(CARD_IMG_PATH, filename)

acronym_dict = {}
with open(ACRO_LOOKUP) as acros:
    for line in acros.readlines():
        acronym, definition = line.split(";", 1)
        acronym_dict[acronym.strip()] = definition.strip()

bot = commands.Bot(command_prefix="&", intents=discord.Intents.all())
note = discord.Game(name="'!acro' for definitions")


def findIn(findMe, findInMe):
    for word in findMe:
        if word.upper() in findInMe.upper():
            return True
    return False


def equalsAny(findUs, inMe):
    for word in findUs:
        if word.upper() == inMe.upper():
            return True
    return False


def searchFor(search_term, search_set, match_threshold=100):
    ratios = [
        (x, fuzz.token_set_ratio(search_term, x), fuzz.token_sort_ratio(search_term, x))
        for x in search_set
    ]
    matches = sorted(
        [r for r in ratios], key=lambda ratio: ratio[1] + ratio[2], reverse=True
    )
    #    if ((int(matches[0][1] + matches[0][2])) > match_threshold) or (int(matches[0][0]) == 100):
    # logging.info(str(matches[0][1]),str(matches[0][2]))
    if ((int(matches[0][1] + matches[0][2])) > match_threshold) or (
        int(matches[0][1]) == 100
    ):
        logging.info("FOUND MATCHES")
        logging.info(
            str(
                "[+] Card lookup found potential matches for {}. Top 3:".format(
                    search_term
                )
            )
        )
        logging.info(str("[+]   {}".format(str(matches[0:3]))))
        return matches
    logging.info("NO MATCHES")
    logging.info(
        str(
            "[-] Card lookup failed to find matches for {} with fuzzy lookup.".format(
                search_term
            )
        )
    )
    logging.info(str("[*]  {}".format(str(matches[0:3]))))

    return False


@bot.command()
async def list(ctx):
    """Lists every word the bot can explain."""
    i = 0
    msg = ""
    for word in acronym_dict:
        if i > 30:
            await ctx.send(msg)
            i = 0
            msg = ""
        msg += "\n" + word.upper() + ": " + acronym_dict.get(word.upper(), "ERROR!")
        i += 1
    await ctx.send(msg)
    await ctx.send("------------------")
    await ctx.send(str(len(acronym_dict)) + " words")


@bot.command()
async def status(ctx):
    """Checks the status of the bot."""
    await ctx.send("Shrimpbot info:")
    await ctx.send("Bot name: " + bot.user.name)
    await ctx.send("Bot ID: " + str(bot.user.id))
    if enabled:
        await ctx.send("The bot is enabled.")
    else:
        await ctx.send("The bot is disabled.")


@bot.command()
async def toggle(ctx):
    """Toggles if the bot is allowed to explain the stuff."""
    global enabled
    enabled = not enabled
    if enabled:
        await ctx.send("The bot is now enabled.")
    else:
        await ctx.send("The bot is now disabled.")


@bot.event
async def on_ready():
    BOT_OWNER = bot.get_user(BOT_OWNER_ID)

    logging.info("Logged in as")
    logging.info(bot.user.name)
    logging.info(bot.user.id)
    logging.info("------")
    logging.info("Owner is")
    logging.info(BOT_OWNER.name)
    logging.info(BOT_OWNER.id)
    logging.info("------")
    logging.info("Servers using Shrimpbot")
    for guild in bot.guilds:
        print("Checking guild {}".format(str(guild)))
        logging.info(" {}".format(str(guild)))
        logging.info(" - ID: {}".format(str(guild.id)))
        if guild.id == 697833083201650689:
            print("leaving that one guild")
            await guild.leave()
            logging.info(" [!] LEFT {}".format(str(guild)))
        if guild.id != 669698762402299904:  # Steel Strat Server are special snowflakes
            print("Fixing nick in {}".format(str(guild)))
            await guild.me.edit(nick="Shrimpbot")
        time.sleep(1)
        print("\n")
    logging.info("======")

    await bot.change_presence(status=discord.Status.online, activity=note)

    # ~ await bot.edit_profile(username="ShrimpBot")


@bot.command()
async def cheat(ctx):
    """Flag to set all of Ard's blacks to hit/crit."""
    global cheating
    cheating = not cheating


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.channel.type is not discord.ChannelType.private:
        # logging
        logging.info(
            "[{} | {} | {} | {}] {}".format(
                time.ctime(),
                message.guild,
                message.channel.name,
                message.author.name,
                message.content,
            )
        )

    # don't read our own message or do anything if not enabled
    # ONLY the dice roller should respond to other bots

    # if ((message.author.id == bot.user.id) and ("card" not in message.content)):
    #     return
    if not enabled:
        return

    #   rollDice(message.content,bot)
    if findIn(["!ROLL"], message.content):
        out = ""
        reds = [
            "<:redblank:522785582284275755>",
            "<:redblank:522785582284275755>",
            "<:redacc:522785555847577610>",
            "<:redhit:522785530958577701>",
            "<:redhit:522785530958577701>",
            "<:redcrit:522785616707059713>",
            "<:redcrit:522785616707059713>",
            "<:reddbl:522784255722651670>",
        ]
        blues = [
            "<:bluehit:522785736500576266>",
            "<:bluehit:522785736500576266>",
            "<:bluehit:522785736500576266>",
            "<:bluehit:522785736500576266>",
            "<:bluecrit:522785721153748996>",
            "<:bluecrit:522785721153748996>",
            "<:blueacc:522785704917467137>",
            "<:blueacc:522785704917467137>",
        ]
        blacks = [
            "<:blackhit:522785658062766090>",
            "<:blackhit:522785658062766090>",
            "<:blackhit:522785658062766090>",
            "<:blackhit:522785658062766090>",
            "<:blackblank:522785641310847024>",
            "<:blackblank:522785641310847024>",
            "<:blackhitcrit:522785681156866063>",
            "<:blackhitcrit:522785681156866063>",
        ]
        redcount = 0
        bluecount = 0
        blackcount = 0

        for word in message.content.split(" "):
            word = word.upper().rstrip("S")

            if word[-3::] == "RED":
                try:
                    redcount += int(word[:-3])
                except:
                    pass
            if word[-4::] == "BLUE":
                try:
                    bluecount += int(word[:-4])
                except:
                    pass
            if word[-5::] == "BLACK":
                try:
                    blackcount += int(word[:-5])
                except:
                    pass

        if (redcount + bluecount + blackcount) < 50:
            if cheating:
                for _ in range(redcount):
                    if message.author.id == "419956366703329281":
                        out += reds[0]
                        out += " "
                    else:
                        out += random.sample(reds, 1)[0]
                        out += " "
                for _ in range(bluecount):
                    if message.author.id == "419956366703329281":
                        out += blues[7]
                        out += " "
                    else:
                        out += random.sample(blues, 1)[0]
                        out += " "
                for _ in range(blackcount):
                    if message.author.id == "236683961831653376":
                        out += blacks[7]
                        out += " "
                    elif message.author.id == "419956366703329281":
                        out += blacks[5]
                        out += " "
                    else:
                        out += random.sample(blacks, 1)[0]
                        out += " "
            else:
                for _ in range(redcount):
                    out += random.sample(reds, 1)[0]
                    out += " "
                for _ in range(bluecount):
                    out += random.sample(blues, 1)[0]
                    out += " "
                for _ in range(blackcount):
                    out += random.sample(blacks, 1)[0]
                    out += " "
        else:
            out = "Real funny there, funny guy."

        dicechannel = [
            channel
            for channel in [server for server in bot.servers][0].channels
            if channel.id == "534871344395845657"
        ][
            0
        ]  # dedicated dice roller channel

        if out:
            if cheating and message.author.id == "236683961831653376":
                await dicechannel.send(message.author.mention + " is a dirty cheater.")
                # await bot.send_message(dicechannel, out)
            else:
                await dicechannel.send(message.author.mention)
                # await bot.send_message(dicechannel, out)

    # don't read any bot's messages

    if message.author.bot and ("card" not in message.content):
        return

    #   shrimpBot(message.content,bot)
    if findIn(
        [
            "SHRIMP",
            "SHRIMPBOT",
            "MC30",
            "MC30T",
            "MC30S",
            "MC30'S",
            "MC-30",
            "MC-30S",
            "MC-30'S",
        ],
        message.content,
    ):
        time.sleep(1)
        await message.add_reaction("\U0001f990")

    if findIn(["HAIL SHRIMPBOT"], message.content):
        await message.channel.send(
            "His chitinous appendages reach down and grant "
            + message.author.name
            + " a pony.  :racehorse:",
        )

    if findIn(["DATA FOR THE DATA GOD"], message.content):
        await message.channel.send(
            "Statistics, likelihoods, and probabilities mean everything to men, nothing to Shrimpbot.",
        )

    #   garmBot(message.content,bot)
    if findIn(["GARM"], message.content):
        time.sleep(1)
        await message.add_reaction("\U000026ab")
        await message.add_reaction("\U0001f534")
        await message.add_reaction("\U0001f535")
        await message.add_reaction("\U0001f525")

    #   foxBot
    if findIn(["DOOKU"], message.content):
        time.sleep(1)
        await message.add_reaction("\U0001f98a")

    #   acronymExplain(message.content,bot)
    if findIn(["!ACRONYM", "!ACRO", "!DEFINE"], message.content):
        sent = False
        for word in message.content.split():
            word = word.strip(special_chars)
            if word.upper() in acronym_dict:
                await message.author.send(
                    word.upper() + ": " + acronym_dict.get(word.upper(), "ERROR!"),
                )
                sent = True
        if not sent:
            await message.author.send(
                "Sorry, it doesn't look like that is in my list.  Message Ardaedhel if you think it should be.",
            )

    #   acronymExplain(new syntax)
    if equalsAny([key + "?" for key in acronym_dict.keys()], message.content):
        sent = False
        for word in message.content.split():
            word = word.strip(special_chars)
            if word.upper() in acronym_dict:
                await message.author.send(
                    "It looks like you're asking for the definition of "
                    + word.upper()
                    + ": "
                    + acronym_dict.get(
                        word.upper(),
                        "Hi, sorry to bother you.  It looks like you have triggered an error in AcronymBot. Please pm Ardaedhel so he can fix it.",
                    ),
                )

    #   cardLookup(message.content,bot)
    if findIn(["!LOOKUP", "!CARD"], message.content) and message.content.startswith(
        "!"
    ):
        sent = False
        searchterm = " ".join(
            [x for x in message.content.split() if not x.startswith("!")]
        )
        for char in special_chars:
            searchterm = searchterm.replace(
                char, " "
            )  # this is super hacky, lrn2regex, scrub
        searchterm = searchterm.upper()
        logging.info("Looking for {}".format(searchterm))

        card_matches = searchFor(searchterm, cardlookup, match_threshold=140)

        # maybe return SURPRISE MOTHERFUCKER instead of Surprise Attack
        if searchterm == "SURPRISE ATTACK" and random.random() > 0.9:
            try:
                filepath = os.path.join(CARD_IMG_PATH, "surprisemofo.png")
                logging.info(
                    "Sending to channel {} - Surprise Motherfucker...".format(
                        message.channel
                    )
                )
                await message.channel.send(file=discord.File(filepath))
                sent = True
            except:
                logging.info("Surprise Motherfucker broke.")
        elif card_matches:
            # Post the image to requested channel
            filepath = os.path.join(CARD_IMG_PATH, str(cardlookup[card_matches[0][0]]))
            # logging.info("Looking in {}".format(filepath))
            logging.info("Sending to channel {} - {}".format(message.channel, filepath))
            await message.channel.send(file=discord.File(filepath))
            sent = True
        else:
            logging.info("Didn't find it.  Failing over to wiki search.")
            # logging.info(cardlookup)

            wikisearchterm = " ".join(
                [x for x in message.content.split() if not x.startswith("!")]
            )
            wiki_img_url = cardpop.autoPopulateImage(wikisearchterm)
            if wiki_img_url:
                tmp_img_path = CARD_IMG_PATH + "tmp/" + searchterm + ".png"
                with requests.get(wiki_img_url, stream=True) as r:
                    with open(tmp_img_path, "wb") as out_file:
                        shutil.copyfileobj(r.raw, out_file)
                        logging.info(
                            "Wiki image retrieval - {} - {}".format(
                                wikisearchterm, wiki_img_url
                            )
                        )

                logging.info(
                    "Sending to channel {} - {}".format(message.channel, tmp_img_path)
                )
                await message.channel.send(file=discord.File(tmp_img_path))
                # await bot.send_message(message.author, "I didn't have that image in my database, so I tried finding it on the Wiki.  Was this the picture you wanted?")
                # await bot.send_message(message.author, "[!yes/!no]")
                sent = True

        if not sent:
            await message.author.send(
                "Sorry, it doesn't look like that is in my list.  Message Ardaedhel if you think it should be.",
            )
            await message.author.send(
                "Please keep in mind that my search functionality is pretty rudimentary at the moment, so you might re-try using a different common name.  Generally I should recognize the full name as printed on the card, with few exceptions.",
            )

    if findIn(["!YES"], message.content):
        pass

    if findIn(["!NO"], message.content):
        pass
    #   listBuilder

    if findIn(["!listhelp"], message.content):
        await message.author.send(
            "To use a generated Vassal fleet:"
            + "\n\t1. Click to download the .vlog file I provided you."
            + "\n\t2. Start a new game in Vassal as normal."
            + "\n\t3. Tools > Load Continuation... > Select the downloaded .vlog file > Open"
            + "\n\t\t*note: accept the warning in the popup"
            + "\n\t4. Click the 'Step forward through logfile' (shown) in the upper left corner of the Star Wars Armada Controls dialog box until your whole list is visible."
        )
        await message.author.send(file=discord.File(PWD + "/img/arrowed.png"))

    if len(message.content) >= 7:
        if findIn(["!VASSAL"], message.content):
            try:
                await message.channel.send("Generating a VASSAL list, hang on...")

                liststr = message.content.strip()[7::].strip()
                if not liststr:
                    raise Exception("List not found. Did you forget the list?")
                guid_hash = hashlib.new("md5")
                guid_hash.update(str(time.time()).encode())
                guid = guid_hash.hexdigest()[0:16]

                listbuilderpath = os.path.dirname(__file__)
                workingpath = os.path.join(listbuilderpath, "working/")
                outpath = os.path.join(listbuilderpath, "out/")
                vlbdirpath = os.path.join(listbuilderpath, "vlb/")
                vlbfilepath = os.path.join(vlbdirpath, guid + ".vlb")
                vlogfilepath = os.path.join(outpath, guid + ".vlog")
                databasepath = os.path.join(listbuilderpath, "vlb_pieces.vlo")

                conn = databasepath

                success, last_item = listbuilder.import_from_list(
                    liststr, vlbfilepath, workingpath, conn
                )

                if not success:
                    logging.info("[!] LISTBUILDER ERROR | {}".format(last_item))
                    await bot.get_user(BOT_OWNER_ID).send(
                        "[!] LISTBUILDER ERROR | {}".format(last_item)
                    )
                    await bot.get_user(BOT_OWNER_ID).send(
                        "POC: {}".format(message.author.name)
                    )
                    await bot.get_user(BOT_OWNER_ID).send(
                        "List: \n{}".format(message.content)
                    )
                    await message.channel.send(
                        "Sorry, there was a list parsing error. I have reported it to Ardaedhel to fix it.",
                    )
                    await message.channel.send(
                        "Details - My best guess is, the error was in or near this line: ",
                    )
                    await message.channel.send(last_item)

                else:
                    listbuilder.export_to_vlog(vlogfilepath, vlbfilepath, workingpath)
                    await message.channel.send(file=discord.File(vlogfilepath))
                    await message.author.send(
                        "For usage instructions, pm me '!listhelp'."
                    )
                del guid_hash

            except Exception as inst:
                logging.info(inst)
                await bot.get_user(BOT_OWNER_ID).send(
                    "[!] LISTBUILDER ERROR | {}".format(inst)
                )
                await bot.get_user(BOT_OWNER_ID).send("Details - Runtime Error:")
                await bot.get_user(BOT_OWNER_ID).send(inst)

                await message.channel.send(
                    "Sorry, there was an application error. I have reported it to Ardaedhel to fix it.",
                )

    if findIn(["!testy"], message.content):
        await message.channel.send(
            "Bananas.",
        )
        await message.channel.send(str(bot.guilds))


bot.run(BOT_TOKEN)
