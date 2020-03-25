#!/usr/bin/python3

import asyncio
import cardpop
import discord
import hashlib
import listbuilder
import logging
import os
import random
import re
import requests
import shutil
import sqlite3
import time

from discord import emoji
from discord.ext import commands


logging.basicConfig(filename="/var/log/shrimp.log", level=logging.DEBUG)

TOKEN_PATH = "/home/ardaedhel/bin/shrimpbot/privatekey.dsc"
CARD_IMG_PATH = "/home/ardaedhel/bin/shrimpbot/img/"
CARD_LOOKUP = "/home/ardaedhel/bin/shrimpbot/cards.txt"
ACRO_LOOKUP = "/home/ardaedhel/bin/shrimpbot/acronyms.txt"
BOT_OWNER = discord.User()
BOT_OWNER.id = "236683961831653376"


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
        acronym, definition = line.split(";")
        acronym_dict[acronym.strip()] = definition.strip()

bot = commands.Bot(command_prefix="&")
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


@bot.command()
async def list():
    """Lists every word the bot can explain."""
    i = 0
    msg = ""
    for word in acronym_dict:
        if i > 30:
            await bot.say(msg)
            i = 0
            msg = ""
        msg += "\n" + word.upper() + ": " + acronym_dict.get(word.upper(), "ERROR!")
        i += 1
    await bot.say(msg)
    await bot.say("------------------")
    await bot.say(str(len(acronym_dict)) + " words")


@bot.command()
async def status():
    """Checks the status of the bot."""
    await bot.say("Shrimpbot info:")
    await bot.say("Bot name: " + bot.user.name)
    await bot.say("Bot ID: " + str(bot.user.id))
    if enabled:
        await bot.say("The bot is enabled.")
    else:
        await bot.say("The bot is disabled.")


@bot.command()
async def toggle():
    """Toggles if the bot is allowed to explain the stuff."""
    global enabled
    enabled = not enabled
    if enabled:
        await bot.say("The bot is now enabled.")
    else:
        await bot.say("The bot is now disabled.")


@bot.event
async def on_ready():
    logging.info("Logged in as")
    logging.info(bot.user.name)
    logging.info(bot.user.id)
    logging.info("------")

    await bot.change_presence(game=note)

    # ~ await bot.edit_profile(username="ShrimpBot")


@bot.command()
async def cheat():
    """Flag to set all of Ard's blacks to hit/crit."""
    global cheating
    cheating = not cheating


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    # logging
    logging.info(
        "[{} | {} | {} | {}] {}".format(
            time.ctime(),
            message.server,
            message.channel.name,
            message.author.name,
            message.content,
        )
    )

    # don't read our own message or do anything if not enabled
    # ONLY the dice roller should respond to other bots

    if message.author.id == bot.user.id:
        return
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
                await bot.send_message(
                    dicechannel, message.author.mention + " is a dirty cheater."
                )
                await bot.send_message(dicechannel, out)
            else:
                await bot.send_message(dicechannel, message.author.mention)
                await bot.send_message(dicechannel, out)

    # don't read any bot's messages

    if message.author.bot:
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
        await bot.add_reaction(message, "\U0001f990")

    if findIn(["HAIL SHRIMPBOT"], message.content):
        me = None

        for server in bot.servers:
            for member in server.members:
                if member.name == bot.user.name:
                    me = member
        if me:
            await bot.change_nickname(me, nickname="ShrimpBot")

        # No ponies for Truthiness
        # if message.author.id == "264163431408467978":
        #    await bot.send_message(message.channel, "No more ponies for "+message.author.name+".  Heretic!")
        #    await bot.change_nickname(me,nickname="AcronymBot")
        # else:
        await bot.send_message(
            message.channel,
            "His chitinous appendages reach down and grant "
            + message.author.name
            + " a pony.  :racehorse:",
        )
        await bot.change_nickname(me, nickname="AcronymBot")

    if findIn(["DATA FOR THE DATA GOD"], message.content):
        # if findIn(["FOR"],message.content):
        # if findIn(["GOD"],message.content):

        await bot.send_message(
            message.channel,
            "Statistics, likelihoods, and probabilities mean everything to men, nothing to Shrimpbot.",
        )

    #   garmBot(message.content,bot)
    if findIn(["GARM"], message.content):
        await bot.add_reaction(message, "\U000026ab")
        await bot.add_reaction(message, "\U0001f534")
        await bot.add_reaction(message, "\U0001f535")
        await bot.add_reaction(message, "\U0001f525")

    #   acronymExplain(message.content,bot)
    if findIn(["!ACRONYM", "!ACRO", "!DEFINE"], message.content):
        sent = False
        for word in message.content.split():
            word = word.strip(special_chars)
            if word.upper() in acronym_dict:
                await bot.send_message(
                    message.author,
                    word.upper() + ": " + acronym_dict.get(word.upper(), "ERROR!"),
                )
                sent = True
        if not sent:
            await bot.send_message(
                message.author,
                "Sorry, it doesn't look like that is in my list.  Message Ardaedhel if you think it should be.",
            )

    #   acronymExplain(new syntax)
    if equalsAny([key + "?" for key in acronym_dict.keys()], message.content):
        sent = False
        for word in message.content.split():
            word = word.strip(special_chars)
            if word.upper() in acronym_dict:
                await bot.send_message(
                    message.author,
                    "It looks like you're asking for the definition of "
                    + word.upper()
                    + ": "
                    + acronym_dict.get(
                        word.upper(),
                        "Hi, sorry to bother you.  It looks like you have triggered an error in AcronymBot. Please pm Ardaedhel so he can fix it.",
                    ),
                )

    #   cardLookup(message.content,bot)
    if findIn(["!LOOKUP", "!CARD"], message.content):
        sent = False
        searchterm = "".join(
            [x for x in message.content.split() if not x.startswith("!")]
        )
        for char in special_chars:
            searchterm = searchterm.replace(
                char, ""
            )  # this is super hacky, lrn2regex, scrub
        searchterm = searchterm.upper()
        logging.info("Looking for {}".format(searchterm))

        # maybe return SURPRISE MOTHERFUCKER instead of Surprise Attack
        if searchterm == "SURPRISEATTACK" and random.random() > 0.5:
            try:
                filepath = os.path.join(CARD_IMG_PATH, "surprisemofo.png")
                logging.info("Sending Surprise Motherfucker...")
                await bot.send_file(destination=message.channel, fp=filepath)
                sent = True
            except:
                logging.info("Surprise Motherfucker broke.")
        elif searchterm in cardlookup:
            # Post the image to requested channel
            filepath = os.path.join(CARD_IMG_PATH, str(cardlookup[searchterm]))
            logging.info("Looking in {}".format(filepath))
            await bot.send_file(destination=message.channel, fp=filepath)
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

                await bot.send_file(destination=message.channel, fp=tmp_img_path)
                # await bot.send_message(message.author, "I didn't have that image in my database, so I tried finding it on the Wiki.  Was this the picture you wanted?")
                # await bot.send_message(message.author, "[!yes/!no]")
                sent = True

        if not sent:
            await bot.send_message(
                message.author,
                "Sorry, it doesn't look like that is in my list.  Message Ardaedhel if you think it should be.",
            )
            await bot.send_message(
                message.author,
                "Please keep in mind that my search functionality is pretty rudimentary at the moment, so you might re-try using a different common name.  Generally I should recognize the full name as printed on the card, with few exceptions.",
            )

    if findIn(["!YES"], message.content):
        pass

    if findIn(["!NO"], message.content):
        pass
    #   listBuilder
    if len(message.content) >= 7:
        if findIn(["!VASSAL"], message.content):
            try:
                await bot.send_message(
                    message.channel, "Generating a VASSAL list, hang on..."
                )
                logging.info("1")

                liststr = message.content.strip()[7::].strip()
                if not liststr:
                    raise Exception("List test not found. Did you forget the list?")
                h = hashlib.new("md5")
                h.update(str(time.time()).encode())
                guid = h.hexdigest()[0:16]
                logging.info("2")

                listbuilderpath = os.path.abspath("/home/ardaedhel/bin/shrimpbot/")
                workingpath = os.path.join(listbuilderpath, "working/")
                outpath = os.path.join(listbuilderpath, "out/")
                vlbdirpath = os.path.join(listbuilderpath, "vlb/")
                vlbfilepath = os.path.join(vlbdirpath, guid + ".vlb")
                vlogfilepath = os.path.join(outpath, guid + ".vlog")
                databasepath = os.path.join(listbuilderpath, "vlb_pieces.vlo")
                logging.info("3")

                conn = sqlite3.connect(databasepath)
                if (
                    "pieces"
                    not in conn.execute(
                        "select name from sqlite_master where type='table'"
                    ).fetchall()[0]
                ):
                    logging.critical(
                        "Database at {}, {}, is corrupted or nonexistent.".format(
                            databasepath, conn
                        )
                    )
                else:
                    logging.info(
                        "Database at {}, {}, found...".format(databasepath, conn)
                    )
                logging.info("4")

                success, last_item = listbuilder.import_from_list(
                    liststr, vlbfilepath, workingpath, conn
                )
                logging.info("5")

                if not success:
                    logging.info("[!] LISTBUILDER ERROR | {}".format(last_item))
                    await bot.send_message(
                        BOT_OWNER, "[!] LISTBUILDER ERROR | {}".format(last_item)
                    )
                    await bot.send_message(
                        BOT_OWNER, "POC: {}".format(message.author.name)
                    )
                    await bot.send_message(
                        BOT_OWNER, "List: \n{}".format(message.content)
                    )
                    await bot.send_message(
                        message.channel,
                        "Sorry, there was an error. I have reported it to Ardaedhel to fix it.",
                    )
                    await bot.send_message(
                        message.channel,
                        "Details - The error was in parsing this line: ",
                    )
                    await bot.send_message(message.channel, last_item)

                else:
                    listbuilder.export_to_vlog(vlogfilepath, vlbfilepath, workingpath)
                    logging.info("6")
                    await bot.send_file(destination=message.channel, fp=vlogfilepath)
                    logging.info("7")
                del h

            except Exception as inst:
                logging.info(inst)
                await bot.send_message(
                    BOT_OWNER, "[!] LISTBUILDER ERROR | {}".format(inst)
                )
                await bot.send_message(
                    message.channel,
                    "Sorry, there was an error. I have reported it to Ardaedhel to fix it.",
                )
                await bot.send_message(message.channel, "Details - Runtime Error:")
                await bot.send_message(message.channel, inst)


bot.run(BOT_TOKEN)
