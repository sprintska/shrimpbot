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


logging.basicConfig(filename='/var/log/shrimp.log',level=logging.DEBUG)

TOKEN_PATH = '/home/ardaedhel/bin/shrimpbot/privatekey.dsc'
CARD_IMG_PATH = '/home/ardaedhel/bin/shrimpbot/img/'
CARD_LOOKUP = '/home/ardaedhel/bin/shrimpbot/cards.txt'
BOT_OWNER = discord.User()
BOT_OWNER.id = "236683961831653376"


with open(TOKEN_PATH) as t:
    BOT_TOKEN = t.read().strip()

enabled = True
cheat = False # Changes on login to default to False
special_chars = "~`@#$%^&* ()_-+=|\\{}[]:;\"\'<>,.?/!"
bot = commands.Bot(command_prefix='&')
note = discord.Game(name="'!acro' for definitions")

cardlookup = {}


with open(CARD_LOOKUP) as cardslist:
    for line in cardslist.readlines():
        filename,key = line.split(";")
        cardlookup[key.rstrip()] = os.path.join(CARD_IMG_PATH,filename)
        

acronym_dict = {
    "AA": "Anti-aircraft, i.e. anti-squadron--as distinct from Anti-ship or AS.",
    "AAA": "Anti-aircraft artillery, i.e. anti-squadron--as distinct from Anti-ship or AS.",
    "ACKBARSLASH": "A tactic: rushing through an opponent's battle line while firing both broadsides.",
    "ACEHOLES": "A successful fleet build archetype relying on General Rieekan and numerous Rebel unique squadrons.",
    "ACM": "Assault Concussion Missiles upgrade card.",
    "ACMS": "Assault Concussion Missiles upgrade card.",
    "AF2": "Assault Frigate Mark II. See also Guppy, Potato, RAF and Whale.",
    "AFII": "Assault Frigate Mark II. See also Guppy, Potato, RAF and Whale.",
    "AFMK2": "Assault Frigate Mark II. See also Guppy, Potato, RAF and Whale.",
    "AFMKII": "Assault Frigate Mark II. See also Guppy, Potato, RAF and Whale.",
    "AFFM": "All Fighters, Follow Me! upgrade card.",
    "AP": "Advanced Projectors upgrade card.",
    "APT": "Assault Proton Torpedoes upgrade card.",
    "APTS": "Assault Proton Torpedoes upgrade card.",
    "AS": "Anti-squadron, generally referring to a ship's dice. See also AA.",
    "BCC": "Bomber Command Center upgrade card.",
    "BT": "Boarding Troopers upgrade card.",
    "BTA": "An Imperial-class Star Destroyer equipped with both the Boarding Troopers and Avenger upgrade cards.",
    "BTAVENGER": "An Imperial-class Star Destroyer equipped with both the Boarding Troopers and Avenger upgrade cards.",
    "BTVENGER": "An Imperial-class Star Destroyer equipped with both the Boarding Troopers and Avenger upgrade cards.",
    "CAP": "Combat Air Patrol, referring to starfighter squadrons deployed as a screen against enemy squadrons.",
    "CHIRPY": "Admiral Chiraneau.",
    "CF": "Concentrate Fire command.",
    "CLONISHER": "A successful fleet build designed by forum member Clontrooper5 around Demolisher.",
    "DC": "Disposable Capacitors upgrade card.",
    "DCS": "Disposable Capacitors upgrade card.",
    "DCAP": "Disposable Capacitors upgrade card.",
    "DCAPS": "Disposable Capacitors upgrade card.",
    "DCO": "Damage Control Officer upgrade card.",
    "DCOS": "Damage Control Officer upgrade card.",
    "DEMSU": "Demolisher and Multiple Small Units, referring to a fleet build.",
    "DOUBLETAP": "Any mechanic enabling two successive attacks against a target by a single unit; see also Triple Tap.",
    "DTT": "Dual Turbolaser Turrets upgrade card.",
    "DTTS": "Dual Turbolaser Turrets upgrade card.",
    "EA": "Enhanced Armament upgrade card.",
    "EAS": "Enhanced Armament upgrade card.",
    "EDSEL-BLERG": "An observation on the rocks-paper-scissors-like effect of squadrons in fleet builds.",
    "ECM": "Electronic Countermeasures upgrade card.",
    "ECMS": "Electronic Countermeasures upgrade card.",
    "EF": "Entrapment Formation! upgrade card.",
    "ET": "normally, Engine Techs upgrade card.",
    "FAQ": "Frequently Asked Questions document.",
    "FC": "normally, Flight Controllers upgrade card, although sometimes refers to Flight Commander instead.",
    "FCT": "normally, Fighter Coordination Team upgrade card, although sometimes refers to Fire Control Team instead.",
    "FCS": "normally, Flight Controllers upgrade card, although sometimes refers to Flight Commander instead.",
    "FCTS": "normally, Fighter Coordination Team upgrade card, although sometimes refers to Fire Control Team instead.",
    "FFG": "Fantasy Flight Games.",
    "FIREBALL": "A bomber formation consisting of Major Rhymer and a number of Firespray-31s. See also Rhymerball.",
    "FLGS": "Friendly Local Games Store. See also LGS.",
    "FT": "Flechette Torpedoes upgrade card.",
    "GENCONSPECIAL": "A squadronless fleet build based on a VSD and three GSDs, very successful during the Wave 1 era.",
    "GLAD": "Gladiator-class Star Destroyer.",
    "GSD": "Gladiator-class Star Destroyer. See also Glad.",
    "GUPPY": "Assault Frigate Mark II. See also AF2, RAF, Potato and Whale.",
    "HH": "Hammerhead Corvette.",
    "HMC80": "Home One-type MC80 Cruiser. Contrast LMC80.",
    "HTT": "Heavy Turbolaser Turrets upgrade card.",
    "IF": "Intensify Firepower! upgrade card.",
    "IFF": "Intensify Forward Firepower, a now-defunct podcast dedicated to Armada.",
    "INTERDOCTOR": "An Interdictor used to protect other ships. Often involves PE and/or TS.",
    "IO": "Intel Officer.",
    "ISD": "Imperial-class Star Destroyer.",
    "ISD1": "Imperial I-class Star Destroyer.",
    "ISD2": "Imperial II-class Star Destroyer.",
    "ISDC": "Imperial Cymoon-class Star Destroyer.",
    "ISD-C": "Imperial Cymoon-class Star Destroyer.",
    "ISDK": "Imperial Kuat-class Star Destroyer.",
    "ISD-K": "Imperial Kuat-class Star Destroyer.",
    "JJ": "Moff Jerjerrod. See also Jerry/MoffyJ.",
    "JERRY": "Moff Jerjerrod. See also JJ/MoffyJ.",
    "LGS": "Local Game Store. See also FLGS.",
    "LIFEBOAT": "A flotilla equipped with the commander, typically to avoid engagement. Now errata'd to be illegal.",
    "LMC80": "Liberty-type MC80 Cruiser. Contrast HMC80. See also MC80L.",
    "LMSU": "Large MSU, referring to a fleet build. Several small ships plus a large with Strategic Advisor. See MSU.",
    "LOS": "Line of sight.",
    "LTP": "Learn To Play document summarising the basic rules of Armada.",
    "META": "The current local or global strategic trends, such as predominant fleet archetypes.",
    "MC80L": "Liberty-type MC80 Cruiser. See also LMC80 and HMC80.",
    "MM": "Mon Mothma.",
    "MOFFYJ": "Moff Jerjerrod. See also JJ.",
    "MOTTISCALE": "A measure of fleet robustness: the sum of 1pt per small ship + 2pt per med + 3pt per lg in a fleet.",
    "MOV": "Margin Of Victory, generally used in the context of tournament scoring.",
    "MSU": "Multiple (or Many) Small Units, referring to a fleet build. See also DeMSU.",
    "NAKED": "A ship with no upgrades.",
    "NEB": "Nebulon-B Frigate.",
    "NEBB": "Nebulon-B Frigate.",
    "OE": "Ordnance Experts upgrade card.",
    "OP": "May refer to: a thread's original post(er), an overpowered card or ability, or the Overload Pulse upgrade.",
    "OS": "Opening Salvo objective card.",
    "PE": "Projection Experts",
    "PIC": "Planetary Ion Cannon",
    "PICKLE": "Home One-type MC80 cruiser.",
    "POTATO": "Assault Frigate Mark II. See also AF2, Guppy and Whale.",
    "PROC": "To trigger a game effect requiring specific conditions to activate.",
    "PROCCING": "To trigger a game effect requiring specific conditions to activate.",
    "PROJEX": "Projection Experts",
    "QBT": "Quad Battery Turrets upgrade card.",
    "QLT": "Quad Laser Turrets upgrade card.",
    "QTC": "Quad Turbolaser Cannons upgrade card.",
    "RAF": "Rebel Assault Frigate, aka Assault Frigate Mark II. See also AF2, Guppy, Potato and Whale.",
    "RAI": "Rules As Intended, i.e. what the rules were designed to do. Compare with RAW.",
    "RAW": "Rules As Written, i.e. what the rules actually do. Compare with RAI.",
    "RBD": "Reinforced Blast Doors upgrade card.",
    "RLB": "Rapid Launch Bays upgrade card.",
    "RNG": "Random Number Generator. May refer to dice, cards, software or any other way of randomising results.",
    "RRG": "Rules Reference Guide document.",
    "RHYMERBALL": "A bomber formation consisting of Major Rhymer and a number of other squadrons. See also Fireball.",
    "RS": "Ruthless Strategists upgrade card.",
    "SFO": "Skilled First Officer upgrade card.",
    "SHRIMP": "MC30c Frigate.",
    "SQUID": "An aquatic cephalopod.  Completely unrelated to the MC30.",
    "SSD": "Super Star Destroyer, often specifically referring to an Executor-class ship.",
    "STM": "Shields to Maximum! upgrade card.",
    "SWA": "Star Wars Armada.",
    "SWM20": "A legendary ghost ship. Alternatively, the SKU for an as yet unreleased Armada product. See also SSD.",
    "TABLING": "Destroying all of a player's ships, often resulting in a 10-1 win.",
    "TFA": "Task Force Antilles upgrade card.",
    "TFO": "Task Force Organa upgrade card.",
    "TRC": "Turbolaser Reroute Circuits upgrade card.",
    "TRC90": "CR90 Corvette equipped with Turbolaser Reroute Circuits.",
    "TRIPLETAP": "Any mechanic enabling three successive attacks against a target by a single unit; see also Double Tap.",
    "TS": "Targeting Scramblers",
    "VSD": "Victory-class Star Destroyer.",
    "WAB": "Wide-Area Barrage upgrade card.",
    "WHALE": "Assault Frigate Mark II. See also AF2, Guppy, Potato and RAF."
}


def findIn(findMe,findInMe):
    for word in findMe:
        if word.upper() in findInMe.upper():
            return True
    return False


def equalsAny(findUs,inMe):
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
        i+=1
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
    logging.info('Logged in as')
    logging.info(bot.user.name)
    logging.info(bot.user.id)
    logging.info('------')

    await bot.change_presence(game=note)

    #~ await bot.edit_profile(username="ShrimpBot")
    
@bot.command()
async def cheat():
    """Flag to set all of Ard's blacks to hit/crit."""
    global cheat
    cheat = not cheat


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    # logging
    logging.info("["+time.ctime()+"] "+message.author.name+": "+message.content)

    # don't read our own message or do anything if not enabled
    # ONLY the dice roller should respond to other bots
    
    if message.author.id == bot.user.id:
        return
    if not enabled:
        return

#   rollDice(message.content,bot)
    if findIn(["!ROLL"],message.content):
        out = ""
        reds = ["<:redblank:522785582284275755>",
                "<:redblank:522785582284275755>",
                "<:redacc:522785555847577610>",
                "<:redhit:522785530958577701>",
                "<:redhit:522785530958577701>",
                "<:redcrit:522785616707059713>",
                "<:redcrit:522785616707059713>",
                "<:reddbl:522784255722651670>"]
        blues = ["<:bluehit:522785736500576266>",
                 "<:bluehit:522785736500576266>",
                 "<:bluehit:522785736500576266>",
                 "<:bluehit:522785736500576266>",
                 "<:bluecrit:522785721153748996>",
                 "<:bluecrit:522785721153748996>",
                 "<:blueacc:522785704917467137>",
                 "<:blueacc:522785704917467137>"]
        blacks = ["<:blackhit:522785658062766090>",
                  "<:blackhit:522785658062766090>",
                  "<:blackhit:522785658062766090>",
                  "<:blackhit:522785658062766090>",
                  "<:blackblank:522785641310847024>",
                  "<:blackblank:522785641310847024>",
                  "<:blackhitcrit:522785681156866063>",
                  "<:blackhitcrit:522785681156866063>"]
        redcount = 0
        bluecount = 0
        blackcount = 0

        for word in message.content.split(" "):
            word = word.upper().rstrip("S")
            
            if word[-3::] == "RED":
                try: redcount += int(word[:-3])
                except: pass
            if word[-4::] == "BLUE":
                try: bluecount += int(word[:-4])
                except: pass
            if word[-5::] == "BLACK":
                try: blackcount += int(word[:-5])
                except: pass

        if (redcount+bluecount+blackcount) < 50:
            if cheat:
                for red in range(redcount):
                    if message.author.id == "419956366703329281":
                        out += reds[0]
                        out += " "
                    else:
                        out += random.sample(reds,1)[0]
                        out += " "
                for blue in range(bluecount):
                    if message.author.id == "419956366703329281":
                        out += blues[7]
                        out += " "
                    else:
                        out += random.sample(blues,1)[0]
                        out += " "
                for black in range(blackcount):
                    if message.author.id == "236683961831653376":
                        out += blacks[7]
                        out += " "
                    elif message.author.id == "419956366703329281":
                        out += blacks[5]
                        out += " "
                    else:
                        out += random.sample(blacks,1)[0]
                        out += " "
            else:
                for red in range(redcount):
                    out += random.sample(reds,1)[0]
                    out += " "
                for blue in range(bluecount):
                    out += random.sample(blues,1)[0]
                    out += " "
                for black in range(blackcount):
                    out += random.sample(blacks,1)[0]
                    out += " "
        else:
            out = "Real funny there, funny guy."
        
        dicechannel = [channel for channel in [server for server in bot.servers][0].channels if channel.id == "534871344395845657"][0] # dedicated dice roller channel
        
        if out:
            if cheat and message.author.id == "236683961831653376":
                await bot.send_message(dicechannel, message.author.mention + " is a dirty cheater.")
                await bot.send_message(dicechannel, out)
            else:
                await bot.send_message(dicechannel, message.author.mention)
                await bot.send_message(dicechannel, out)


    # don't read any bot's messages

    if message.author.bot:
        return

#   shrimpBot(message.content,bot)
    if findIn(["SHRIMP","SHRIMPBOT","MC30","MC30T","MC30S","MC30'S","MC-30","MC-30S","MC-30'S"],message.content):
        await bot.add_reaction(message,"\U0001f990")

    if findIn(["HAIL SHRIMPBOT"],message.content):
        me = None

        for server in bot.servers:
            for member in server.members:
                if member.name == bot.user.name:
                    me = member
        if me:
            await bot.change_nickname(me,nickname="ShrimpBot")

        # No ponies for Truthiness
        #if message.author.id == "264163431408467978":
        #    await bot.send_message(message.channel, "No more ponies for "+message.author.name+".  Heretic!")
        #    await bot.change_nickname(me,nickname="AcronymBot")
        #else:
        await bot.send_message(message.channel, "His chitinous appendages reach down and grant "+message.author.name+" a pony.  :racehorse:")
        await bot.change_nickname(me,nickname="AcronymBot")
            
    if findIn(["DATA FOR THE DATA GOD"],message.content):
        # if findIn(["FOR"],message.content):
            # if findIn(["GOD"],message.content):

        await bot.send_message(message.channel, "Statistics, likelihoods, and probabilities mean everything to men, nothing to Shrimpbot.")

#   garmBot(message.content,bot)
    if findIn(["GARM"],message.content):
        await bot.add_reaction(message,"\U000026ab")
        await bot.add_reaction(message,"\U0001f534")
        await bot.add_reaction(message,"\U0001f535")
        await bot.add_reaction(message,"\U0001f525")

#   acronymExplain(message.content,bot)
    if findIn(["!ACRONYM", "!ACRO", "!DEFINE"],message.content):
        sent = False
        for word in message.content.split():
            word = word.strip(special_chars)
            if word.upper() in acronym_dict:
                await bot.send_message(message.author, word.upper() + ": " + acronym_dict.get(word.upper(), "ERROR!"))
                sent = True
        if not sent:
            await bot.send_message(message.author, "Sorry, it doesn't look like that is in my list.  Message Ardaedhel if you think it should be.")

#   acronymExplain(new syntax)
    if equalsAny([key+"?" for key in acronym_dict.keys()],message.content):
        sent = False
        for word in message.content.split():
            word = word.strip(special_chars)
            if word.upper() in acronym_dict:
                await bot.send_message(message.author, "It looks like you're asking for the definition of "+word.upper()+": " + acronym_dict.get(word.upper(),"Hi, sorry to bother you.  It looks like you have triggered an error in AcronymBot. Please pm Ardaedhel so he can fix it."))

#   cardLookup(message.content,bot)
    if findIn(["!LOOKUP", "!CARD"],message.content):
        sent = False
        searchterm = "".join([x for x in message.content.split() if not x.startswith("!")])
        for char in special_chars:
            searchterm = searchterm.replace(char,"")  # this is super hacky, lrn2regex, scrub
        searchterm = searchterm.upper()
        logging.info("Looking for {}".format(searchterm))
        
        # maybe return SURPRISE MOTHERFUCKER instead of Surprise Attack
        if searchterm == "SURPRISEATTACK" and random.random() > .5:
            try:
                filepath = os.path.join(CARD_IMG_PATH,"surprisemofo.png")
                logging.info("Sending Surprise Motherfucker...")
                await bot.send_file(destination=message.channel,fp=filepath)
                sent = True
            except:
                logging.info("Surprise Motherfucker broke.")
        elif searchterm in cardlookup:
            # Post the image to requested channel
            filepath = os.path.join(CARD_IMG_PATH,str(cardlookup[searchterm]))
            logging.info("Looking in {}".format(filepath))
            await bot.send_file(destination=message.channel,fp=filepath)
            sent = True
        else:
            logging.info("Didn't find it.  Failing over to wiki search.")
            # logging.info(cardlookup)
            
            wikisearchterm = " ".join([x for x in message.content.split() if not x.startswith("!")])
            wiki_img_url = cardpop.autoPopulateImage(wikisearchterm)
            if wiki_img_url:
                tmp_img_path = CARD_IMG_PATH + "tmp/" + searchterm + ".png"
                with requests.get(wiki_img_url, stream=True) as r:
                    with open(tmp_img_path, 'wb') as out_file:
                        shutil.copyfileobj(r.raw, out_file)
                        logging.info("Wiki image retrieval - {} - {}".format(wikisearchterm,wiki_img_url))
                
                await bot.send_file(destination=message.channel,fp=tmp_img_path)
                # await bot.send_message(message.author, "I didn't have that image in my database, so I tried finding it on the Wiki.  Was this the picture you wanted?")
                # await bot.send_message(message.author, "[!yes/!no]")
                sent = True
            
        if not sent:
            await bot.send_message(message.author, "Sorry, it doesn't look like that is in my list.  Message Ardaedhel if you think it should be.")
            await bot.send_message(message.author, "Please keep in mind that my search functionality is pretty rudimentary at the moment, so you might re-try using a different common name.  Generally I should recognize the full name as printed on the card, with few exceptions.")
            
    if findIn(["!YES"],message.content):
        pass
    
    if findIn(["!NO"],message.content):
        pass
        

#   listBuilder
    if len(message.content) >= 7:
        if findIn(["!VASSAL"],message.content):
            try:
                await bot.send_message(message.channel,"Generating a VASSAL list, hang on...")
                logging.info("1")
                
                liststr = message.content.strip()[7::].strip()
                h = hashlib.new('md5')
                h.update(str(time.time()).encode())
                guid = h.hexdigest()[0:16]
                logging.info("2")
                
                listbuilderpath = os.path.abspath("/home/ardaedhel/bin/shrimpbot/")
                workingpath = os.path.join(listbuilderpath,"working/")
                outpath = os.path.join(listbuilderpath,"out/")
                vlbdirpath = os.path.join(listbuilderpath,"vlb/")
                vlbfilepath = os.path.join(vlbdirpath,guid+".vlb")
                vlogfilepath = os.path.join(outpath,guid+".vlog")
                databasepath = os.path.join(listbuilderpath,"vlb_pieces.vlo")
                logging.info("3")
                
                conn = sqlite3.connect(databasepath)
                if "pieces" not in conn.execute("select name from sqlite_master where type='table'").fetchall()[0]:
                    logging.critical("Database at {}, {}, is corrupted or nonexistent.".format(databasepath,conn))
                else:
                    logging.info("Database at {}, {}, found...".format(databasepath,conn))
                logging.info("4")
                
                success, last_item = listbuilder.import_from_list(liststr,vlbfilepath,workingpath,conn)
                logging.info("5")
                
                if not success:
                    logging.info(last_item)
                    await bot.send_message(BOT_OWNER, "[!] LISTBUILDER ERROR | {}".format(last_item))
                    await bot.send_message(message.channel, "Sorry, there was an error. I have reported it to Ardaedhel to fix it.")
                    await bot.send_message(message.channel, "Details - The error was in parsing this line: ")
                    await bot.send_message(message.channel, last_item)
                
                else:
                    listbuilder.export_to_vlog(vlogfilepath,vlbfilepath,workingpath)
                    logging.info("6")
                    await bot.send_file(destination=message.channel,fp=vlogfilepath)
                    logging.info("7")
                del h
                
            except Exception as inst:
                logging.info(inst)
                await bot.send_message(BOT_OWNER, "[!] LISTBUILDER ERROR | {}".format(inst))
                await bot.send_message(message.channel, "Sorry, there was an error. I have reported it to Ardaedhel to fix it.")
                await bot.send_message(message.channel, "Details - Runtime Error:")
                await bot.send_message(message.channel, inst)


bot.run(BOT_TOKEN)
