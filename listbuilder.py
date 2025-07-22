#!/usr/bin/env python3

"""
listbuilder.py

This module provides classes and functions for importing, exporting, and converting Star Wars: Armada fleet lists between various formats and VASSAL-compatible files.

Configuration:
---------------
All public functions and classes require a `ShrimpConfig` object, which encapsulates all file paths and runtime options. This eliminates the need for global variables and makes dependencies explicit.

- To use with default settings, create a config with `config = ShrimpConfig()`.
- To override defaults, pass arguments to `ShrimpConfig(...)`.
- When calling as a script, command-line arguments are parsed and used to populate a `ShrimpConfig` instance.
- When importing as a module, always pass a config object to functions/classes.

Example usage (as a module):
    import listbuilder
    config = listbuilder.ShrimpConfig(vlb="myfleet.vlb", db="custom_db.vlo")
    result = listbuilder.import_from_list(config)

"""

import argparse
import logging
import logging.handlers
import os
import re
import shutil
import sqlite3

from listbuilder.definitions import (
    nomenclature_translation,
    ambiguous_names,
)
from listbuilder.fleet import Fleet
from listbuilder.utils import unzipall, zipall, scrub_piecename

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


class ShrimpConfig:
    def __init__(
        self,
        vlog="vlb-out.vlog",
        vlb="list.vlb",
        working_dir=None,
        aff="test.aff",
        flt="list.flt",
        db="vlb_pieces.vlo",
        import_vlog=False,
    ):
        self.pwd = os.path.dirname(__file__)
        self.vlog_path = os.path.abspath(vlog)
        self.vlb_path = os.path.abspath(vlb)
        self.working_dir = os.path.abspath(
            working_dir or os.path.join(self.pwd, "working")
        )
        self.aff_path = os.path.abspath(aff)
        self.fleet = os.path.abspath(flt)  # path or text
        self.db_path = os.path.abspath(db)
        self.import_vlog = import_vlog


def ident_format(fleet_text):
    """Use a series of heuristics to identify the format of a fleet list."""

    formats = {
        "fab": 0.0,
        "warlord": 0.0,
        "afd": 0.0,
        "kingston": 0.0,
        "aff": 0.0,
        "vlog": 0.0,
        "vlb": 0.0,
    }

    # format_names = {'fab': "Fab's Armada Fleet Builder",
    #                 'warlord': "Armada Warlords",
    #                 'afd': "Armada Fleets Designer for Android",
    #                 'kingston': "Ryan Kingston's Armada Fleet Builder",
    #                 'aff': "Armada Fleet Format",
    #                 'vlog': "VASSAL Log File",
    #                 'vlb': "VASSAL Armada Listbuilder"}

    # Fab's
    if " • " in fleet_text:
        formats["fab"] += 1.0
    if "FLEET" in fleet_text.split("\n")[0]:
        formats["fab"] += 1.0
    if "armada.fabpsb.net" in fleet_text.lower():
        formats["fab"] += 5.0

    i = 0
    for line in fleet_text.split("\n"):
        try:
            if " • " in line and line[0].isdigit():
                if int(line[0]) == i + 1:
                    formats["fab"] += 1
                i += int(line[0])
        except IndexError:
            pass

    # Warlords
    ft = fleet_text.replace("â€¢", "\u2022")
    if "[flagship]" in ft.replace(" ", ""):
        formats["warlord"] += 5.0
    if "Armada Warlords" in ft:
        formats["warlord"] += 5.0
    if "Commander: " in ft:
        formats["warlord"] += 2.0
    for line in ft.split("\n"):
        if "\t points)" in line:
            formats["warlord"] += 1
        if line.strip().startswith("-  "):
            formats["warlord"] += 0.5

    # Armada Fleets Designer
    if "+" in fleet_text:
        formats["afd"] += 1.0
    if "/400)" in fleet_text.split("\n")[0]:
        formats["afd"] += 2.0

    for lineloc, line in enumerate(fleet_text.split("\n")):
        if lineloc > 0:
            if (len(fleet_text.split("\n")[lineloc - 1]) == line.count("=") + 1) and (
                line.count("=") > 3
            ):
                formats["afd"] += 5.0
            if line.strip().startswith("· "):
                formats["afd"] += 1

    # Kingston
    if "Faction:" in ft:
        formats["kingston"] += 1.0
    if "Commander: " in ft:
        formats["kingston"] += 2.0
    for line in ft.split("\n"):
        if line.strip().startswith("• ") or line.strip().startswith("\u2022"):
            formats["kingston"] += 1

    # AFF
    if fleet_text[0] == "{":
        formats["aff"] += 30.0
    if fleet_text.startswith("ship:"):
        formats["aff"] += 30.0
    if fleet_text.startswith("squadron:"):
        formats["aff"] += 30

    logging.info("Format detection: {}".format(str(formats)))
    return max(formats.keys(), key=(lambda x: formats[x]))


def import_from_list(config, isvlog=False):
    """Imports a fleet list from a file or string into a VASSAL Listbuilder (VLB) format."""

    conn = config.db_path
    working_path = config.working_dir
    output_to = config.vlb_path

    ingest_format = {
        "fab": import_from_fabs,
        "warlord": import_from_warlords,
        "afd": import_from_afd,
        "kingston": import_from_kingston,
        "aff": import_from_aff,
        "vlog": import_from_vlog,
    }

    if isvlog:
        import_from_vlog(config.fleet, output_to, working_path, conn)
    else:
        if os.path.exists(config.fleet):
            logging.info(config.fleet)
            with open(config.fleet) as fleet_list:
                fleet_text = fleet_list.read()
        else:
            fleet_text = config.fleet

        fmt = ident_format(fleet_text)
        success, f = ingest_format[fmt](fleet_text, config)

        if not success:
            return (success, f)

        os.makedirs(os.path.dirname(output_to), exist_ok=True)
        with open(output_to, "w") as vlb:
            vlb.write("a1\r\nbegin_save{}\r\nend_save{}\r\n".format(chr(27), chr(27)))
            vlb.write(
                "LOG\tCHAT<Listbuilder> - "
                + "Fleet imported by Shrimpbot on the Armada Discord.{}\r\n".format(
                    chr(27)
                )
                + "LOG\tCHAT<Listbuilder> - "
                + "https://discord.gg/jY4K4d6{}\r\n\r\n".format(chr(27))
            )
            for s in f.ships:
                vlb.write(s.shipcard.content + chr(27))
                vlb.write(s.shiptoken.content + chr(27))
                vlb.write(s.shipcmdstack.content + chr(27))
                [vlb.write(u.content + chr(27)) for u in s.upgrades]
            for sq in f.squadrons:
                vlb.write(sq.squadroncard.content + chr(27))
                vlb.write(sq.squadrontoken.content + chr(27))
            for o in f.objectives:
                vlb.write(f.objectives[o].content + chr(27))

        return (True, None)


def import_from_fabs(import_list, config):
    """Imports a Fab's Fleet Builder list into a Fleet object"""

    vlb_path = config.vlb_path
    working_path = config.working_dir
    fleet = Fleet("Food", config=config)
    last_line = ""

    for line in import_list.split("\n"):
        logging.info(line)
        last_line = line

        try:
            if line.strip():
                if line.strip()[0].isdigit():
                    this_line = line.replace("â€¢", "\u2022").strip()
                    this_line = "".join(
                        "".join(this_line.split(" {} ".format("\u2022"))[1::]).split(
                            " ("
                        )[:-1]
                    )

                    # only ships & objs are broken up with " - ", and objs are labelled
                    # otherwise, it's either sqd or upgradeless ship--indistinguishable

                    if " - " in this_line:
                        if this_line.startswith("Objective"):
                            pass
                        else:
                            working_line = this_line.split(" - ")
                            ship = fleet.add_ship(working_line[0].strip())
                            for upgrade in working_line[1::]:
                                ship.add_upgrade(upgrade.strip())

                    else:
                        issquadron = False
                        isship = False
                        issquadronfancy = False
                        this_line = scrub_piecename(this_line)
                        if this_line in nomenclature_translation:
                            corrected_piecename = nomenclature_translation[this_line]
                            logging.info(
                                "[-] Translated {} to {} - Fab's.".format(
                                    this_line, corrected_piecename
                                )
                            )
                            this_line = corrected_piecename
                        logging.info(
                            "Searching for Fab's piece {} in {}".format(
                                scrub_piecename(this_line), str(config.db_path)
                            )
                        )
                        try:
                            with sqlite3.connect(config.db_path) as connection:
                                issquadron = connection.execute(
                                    """SELECT * FROM pieces
                                        WHERE piecetype='squadroncard'
                                        AND piecename LIKE ?;""",
                                    ("%" + scrub_piecename(this_line) + "%",),
                                ).fetchall()
                        except ValueError as err:
                            logging.exception(err)

                        try:
                            with sqlite3.connect(config.db_path) as connection:
                                isship = connection.execute(
                                    """SELECT * FROM pieces
                                        WHERE piecetype='shipcard'
                                        AND piecename LIKE ?;""",
                                    ("%" + scrub_piecename(this_line),),
                                ).fetchall()
                        except ValueError as err:
                            logging.exception(err)

                        try:
                            if this_line.lower()[-8::] == "squadron":
                                ltmp = this_line[0:-8]
                                with sqlite3.connect(config.db_path) as connection:
                                    issquadronfancy = connection.execute(
                                        """SELECT * FROM pieces
                                            WHERE piecetype='squadroncard'
                                            AND piecename LIKE ?;""",
                                        ("%" + scrub_piecename(ltmp) + "%",),
                                    ).fetchall()
                        except ValueError as err:
                            logging.exception(err)

                        if bool(issquadron):
                            # sq = f.add_squadron(l.strip())
                            fleet.add_squadron(this_line.strip())
                        elif bool(issquadronfancy):
                            _ = fleet.add_squadron(ltmp.strip())
                        elif bool(isship):
                            ship = fleet.add_ship(this_line.strip())
                        else:
                            logging.info(
                                "{}{} IS FUCKED UP, YO{}".format(
                                    "=" * 40, this_line, "=" * 40
                                )
                            )
        except Exception as err:
            logging.exception(err)
            return (False, last_line)

    return (True, fleet)


def import_from_warlords(import_list, config):
    """Imports an Armada Warlords list into a Fleet object"""

    conn = config.db_path

    fleet = Fleet("Food", config=config)

    shipnext = False
    is_flagship = False

    logging.info("Warlords")

    # Set the flag if it looks like Flagship format to enable the custom error
    flagship_regex = re.compile(r"\)\n= [\d]{1,3} points\n")
    if flagship_regex.search(import_list):
        logging.info("[!] FLAGSHIP LIST -- UNSUPPORTED!")
        is_flagship = True

    # Make sure the cretinous user isn't just schwacking off all the garbage at
    # the top of a Warlords export.
    ship_regex = re.compile(r".*\([\d]{1,3} points\)")
    squadron_regex = re.compile(r"^[\d]{1,2}.*\(.*[\d]{1,3} points\)")

    ship_check = import_list.split("\n")[0].strip()
    if ship_regex.search(ship_check):
        logging.info("Ship check regex hit on: " + str(ship_regex.search(ship_check)))
        ship_check = ship_check.split()[0]
        logging.info(
            "SELECT piecetype FROM pieces where piecename LIKE %"
            + scrub_piecename(ship_check)
            + "%"
        )
        with sqlite3.connect(config.db_path) as connection:
            ship_query = connection.execute(
                '''SELECT piecetype FROM pieces where piecename LIKE ?" "''',
                ("%" + scrub_piecename(ship_check) + "%",),
            ).fetchall()
        if len(ship_query) > 0:
            if ("ship",) in ship_query or ("shipcard",) in ship_query:
                shipnext = True

    for line in import_list.split("\n"):
        card_name = line.strip()
        last_line = card_name

        logging.info(card_name)

        try:
            logging.info(card_name.split())

            if len(card_name.split()) <= 1:
                shipnext = True

            elif card_name.split()[0].strip() in [
                "Faction:",
                "Points:",
                "Commander:",
                "Author:",
            ]:
                pass

            elif card_name.split()[1] == "Objective:":
                objective = [card_name.split()[0], card_name.split(":")[1]]
                fleet.add_objective(objective[0], objective[1])
                shipnext = False

            elif squadron_regex.search(card_name):
                squadron = "".join(card_name.split("(")[0:-1])
                cost = card_name.split("(")[-1]
                squadron = scrub_piecename(
                    "".join(card_name.split("(")[0].split()[1::])
                )
                cost = scrub_piecename(cost.split()[0])
                if card_name.split()[0].isdigit:
                    if int(card_name.split()[0]) > 1:
                        squadron = squadron[:-1]
                if (squadron, cost) in ambiguous_names:
                    squadron_new = ambiguous_names[(squadron, cost)][0]
                    logging.info(
                        "Ambiguous name {} ({}) translated to {}.".format(
                            squadron, cost, squadron_new
                        )
                    )
                    squadron = squadron_new
                # sq = f.add_squadron(squadron)
                fleet.add_squadron(squadron)
                shipnext = False

            elif card_name[0] == "=":
                shipnext = True

            elif shipnext:
                ship = "(".join(card_name.split("]")[-1].split("(")[0:-1])
                cost = card_name.split("]")[-1].split("(")[-1]
                ship = scrub_piecename(ship.strip(" -\t"))
                cost = scrub_piecename(cost.split()[0])
                if (ship, cost) in ambiguous_names:
                    ship_new = ambiguous_names[(ship, cost)][0]
                    logging.info(
                        "Ambiguous name {} ({}) translated to {}.".format(
                            ship, cost, ship_new
                        )
                    )
                    ship = ship_new
                s = fleet.add_ship(ship)
                shipnext = False

            elif card_name[0] == "-":
                upgrade, cost = card_name.rsplit("(", 1)
                upgrade = scrub_piecename(upgrade)
                cost = scrub_piecename(cost.split()[0])
                if (upgrade, cost) in ambiguous_names:
                    upgrade_new = ambiguous_names[(upgrade, cost)][0]
                    logging.info(
                        "Ambiguous name {} ({}) translated to {}.".format(
                            upgrade, cost, upgrade_new
                        )
                    )
                    upgrade = upgrade_new
                _ = s.add_upgrade(upgrade)
                shipnext = False
        except Exception as err:
            logging.exception(err)
            if is_flagship:
                last_line = (
                    last_line
                    + "\n"
                    + "=" * 40
                    + "\nThis appears to be a Flagship list.  Shrimpbot currently "
                    + "supports Flagship only only insofar as it conforms to Warlords' "
                    + "format. *Usually* you can make it work by removing and manually "
                    + "spawning squadrons. \nSee "
                    + "https://github.com/sprintska/shrimpbot/issues/59"
                )
            return (False, last_line)

    return (True, fleet)


def import_from_afd(import_list, config):
    """Imports an Armada Fleets Designer list into a Fleet object"""

    fleet = Fleet("Food", config=config)

    start = False
    obj_category = "assault"

    for line in import_list.strip().split("\n"):
        try:
            last_line = line.strip()
            card_name = line.strip().split(" x ", 1)[-1]
            logging.info(card_name)

            if card_name.startswith("==="):
                start = True

            elif start and len(card_name) > 0:
                if card_name[0] == "·":
                    upgrade, cost = card_name.split("(")
                    upgrade = scrub_piecename(upgrade)
                    cost = cost.split(")")[0]

                    if upgrade in nomenclature_translation:
                        translated = nomenclature_translation[upgrade]
                        logging.info(
                            "[-] Translated {} to {} - AFD.".format(upgrade, translated)
                        )
                        upgrade = translated

                    if (upgrade, cost) in ambiguous_names:
                        upgrade_new = ambiguous_names[(upgrade, cost)][0]
                        logging.info(
                            "Ambiguous name {} ({}) translated to {}.".format(
                                upgrade, cost, upgrade_new
                            )
                        )
                        upgrade = upgrade_new

                    _ = ship.add_upgrade(upgrade)

                elif "(" not in card_name:
                    logging.info("Hit the conditional for {}.".format(card_name))
                    card_name = scrub_piecename(str(card_name))
                    fleet.add_objective(obj_category, card_name)

                    # TODO: retool the objs to not care about categories... :/
                    if obj_category == "assault":
                        obj_category = "defense"
                    else:
                        obj_category = "navigation"

                else:
                    card_name, cost = card_name.split(" (", 1)
                    cost = cost.split(" x ")[-1].split(")")[0]

                    issquadron = False
                    isship = False

                    card_name = scrub_piecename(card_name)

                    try:
                        if card_name in nomenclature_translation:
                            t = nomenclature_translation[card_name]
                            logging.info(
                                "[-] Translated {} to {} - AFD.".format(card_name, t)
                            )
                            card_name = t
                        if (card_name, cost) in ambiguous_names:
                            card_name_new = ambiguous_names[(card_name, cost)][0]
                            logging.info(
                                "Ambiguous name {} ({}) translated to {}.".format(
                                    card_name, cost, card_name_new
                                )
                            )
                            card_name = card_name_new
                        logging.info(
                            "Searching for AFD piece {} in {}".format(
                                scrub_piecename(card_name), str(config.db_path)
                            )
                        )
                        with sqlite3.connect(config.db_path) as connection:
                            issquadron = connection.execute(
                                """SELECT * FROM pieces
                                    WHERE piecetype='squadroncard'
                                    AND piecename LIKE ?;""",
                                ("%" + scrub_piecename(card_name) + "%",),
                            ).fetchall()
                    except ValueError as err:
                        logging.exception(err)

                    try:
                        logging.info(
                            "Searching for AFD piece {} in {}".format(
                                card_name, str(config.db_path)
                            )
                        )
                        with sqlite3.connect(config.db_path) as connection:
                            isship = connection.execute(
                                """SELECT * FROM pieces
                                    WHERE piecetype='shipcard'
                                    AND piecename LIKE ?;""",
                                ("%" + card_name,),
                            ).fetchall()
                    except ValueError as err:
                        logging.exception(err)

                    if bool(issquadron):
                        _ = fleet.add_squadron(card_name)
                    elif bool(isship):
                        ship = fleet.add_ship(card_name)
                    else:
                        logging.info(
                            "{}{} IS FUCKED UP, YO{}".format(
                                "=" * 40, card_name, "=" * 40
                            )
                        )
        except Exception as err:
            logging.exception(err)
            return (False, last_line)

    return (True, fleet)


def import_from_kingston(import_list, config):
    """Imports a Ryan Kingston list into a Fleet object"""

    fleet = Fleet("Food", config=config)

    logging.info("Fleet created with database {}.".format(str(config.db_path)))

    shipnext = True
    faction = None

    for line in import_list.split("\n"):
        try:
            card_name = line.replace("â€¢", "\u2022").strip()
            logging.info(card_name)
            last_line = card_name

            if card_name:
                if card_name.split(":")[0].strip() in [
                    "Name",
                    "Commander",
                    "Author",
                ]:
                    pass

                # Track faction to disambiguate Venator-II variants later
                elif card_name.split(":")[0].strip() == "Faction":
                    faction = card_name.split(":")[-1].strip()
                    logging.info("Faction identified: {}".format(faction))

                elif card_name.split(":")[0] in ["Assault", "Defense", "Navigation"]:
                    if card_name.strip()[-1] != ":":
                        logging.info("{}".format(card_name))
                        _ = fleet.add_objective(
                            card_name.split(":")[0].lower().strip(),
                            card_name.split(":")[1].lower().strip(),
                        )

                elif shipnext:
                    if card_name.lower().strip() == "squadrons:":
                        logging.info("Squadrons next")
                        shipnext = False

                    elif "\u2022" in card_name:
                        card_name, cost = card_name.split(" (", 1)
                        card_name = scrub_piecename(card_name)
                        cost = cost.split(")")[0]

                        if (card_name, cost) in ambiguous_names:
                            card_name_new = ambiguous_names[(card_name, cost)][0]
                            logging.info(
                                "Ambiguous name {} ({}) translated to {}.".format(
                                    card_name, cost, card_name_new
                                )
                            )
                            card_name = card_name_new

                        _ = ship.add_upgrade(card_name)

                    elif card_name[0] == "=":
                        pass

                    else:
                        # Can't disambiguate Venator-II on cost because both variants are identical *sigh*
                        if card_name == "Venator II (100)" and faction == "Imperial":
                            logging.info(
                                "[Debug] Found Imperial Venator.  Setting card name."
                            )
                            card_name = "Venator II Imp"

                        ship = fleet.add_ship(card_name.split(" (", 1)[0].strip())

                elif "\u2022" in card_name and card_name[0] != "=":
                    cost = card_name.split(" (")[-1]
                    cost = cost.split(")")[0]
                    card_name = "".join(card_name.split(" x ")[-1].split(" (")[0:-1])
                    card_name = scrub_piecename(card_name)

                    if (card_name, cost) in ambiguous_names:
                        card_name_new = ambiguous_names[(card_name, cost)][0]
                        logging.info(
                            "Ambiguous name {} ({}) translated to {}.".format(
                                card_name, cost, card_name_new
                            )
                        )
                        card_name = card_name_new

                    _ = fleet.add_squadron(card_name)
        except Exception as err:
            logging.exception(err)
            return (False, last_line)

    return (True, fleet)


def import_from_aff(import_list, config):
    """Imports a .aff (Armada Fleet Format) file into a Fleet object"""

    f = Fleet("Food", config=config)

    # with open(import_list) as aff_in:
    for line in import_list.split("\n"):
        logging.info(line)
        # for line in aff_in.readlines():

        if line.lower().startswith("ship:"):
            s = f.add_ship(line.split(":")[-1].strip())

        elif line.lower().startswith("upgrade:"):
            _ = s.add_upgrade(line.split(":")[-1].strip())

        elif line.lower().startswith("squadron:"):
            _ = f.add_squadron(line.split(":")[-1].strip())

    return f


def import_from_vlog(config):
    """Strips out all the compression and obfuscation from a VASSAL
    log/continution .vlog file at path import_from and creates an
    unobfuscated .vlb text file at path vlb_path."""

    unzipall(config.vlog_path, config.working_dir)

    with open(os.path.join(config.working_dir, "savedGame"), "r") as vlog:
        b_vlog = vlog.read()

    xor_key_str = b_vlog[5:7]
    if xor_key.isdigit():
        xor_key = int(xor_key_str, 16)
    else:
        logging.info(
            "VLOG {} is malformed: encountered an invalid XOR key.  Key {} is not a number.".format(
                str(config.vlog_path), str(xor_key)
            )
        )
        xor_key = int("0", 16)
    obfuscated = b_vlog[6::]
    obf_pair = ""
    clear = ""
    for charloc, char in enumerate(obfuscated):
        obf_pair += char
        if not charloc % 2:
            clearint = int(obf_pair, 16) ^ xor_key
            clear += chr(clearint)
            obf_pair = ""

    clear = clear[1::].replace("\t", "\t\r\n").replace(chr(27), chr(27) + "\r\n\r\n")

    os.makedirs(os.path.dirname(config.vlb_path), exist_ok=True)
    with open(config.vlb_path, "w") as vlb:
        vlb.write(xor_key_str + "\r\n")
        vlb.write(clear)


def export_to_vlog(config):
    """Adds all the obfuscation and compression to turn a .vlb
    VASSAL listbuilder file (at config.vlb_path), along with boilerplate
    savedata and moduledata XML files in config.working_dir, into a VASSAL-
    compatible .vlog replay file."""

    out_path = os.path.join(config.pwd, "out")

    for afile in os.listdir(out_path):
        file_path = os.path.join(out_path, afile)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logging.exception(e)

    shutil.copyfile(
        os.path.join(config.working_dir, "moduledata"),
        os.path.join(out_path, "moduledata"),
    )
    shutil.copyfile(
        os.path.join(config.working_dir, "savedata"), os.path.join(out_path, "savedata")
    )

    os.makedirs(os.path.dirname(config.vlb_path), exist_ok=True)
    with open(config.vlb_path, "r") as vlb:
        in_vlb = vlb.read()

    in_vlb = in_vlb.replace("\r", "").replace("\n", "")
    xor_key = int(in_vlb[0:2], 16)
    clear = in_vlb[2::]
    obf_out = "!VCSK" + (in_vlb[0:2])
    for char in clear:
        obfint = ord(char) ^ xor_key
        obf_out += hex(obfint)[2::]

    os.makedirs(os.path.dirname(config.working_dir), exist_ok=True)
    with open(os.path.join(config.working_dir, "savedGame"), "w") as savedgame_out:
        savedgame_out.write(obf_out)

    zipall(config.working_dir, os.path.abspath(config.vlog_path))


def get_default_config():
    return ShrimpConfig()


if __name__ == "__main__":

    config = ShrimpConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-db", help="path to reference database", type=str, default="vlb_pieces.vlo"
    )
    parser.add_argument(
        "-wd",
        help="working directory",
        type=str,
        default=os.path.join(config.pwd, "working"),
    )
    parser.add_argument(
        "-vlog", help=".vlog filename", type=str, default="vlb-out.vlog"
    )
    parser.add_argument("-vlb", help=".vlb filename", type=str, default="list.vlb")
    parser.add_argument("-aff", help=".aff filename", type=str, default="test.aff")
    parser.add_argument(
        "-flt", help="fleet list location", type=str, default="list.flt"
    )
    parser.add_argument("--imp", help="import a .vlog to a .vlb", action="store_true")
    parser.add_argument("--exp", help="export a .vlb to a .vlog", action="store_true")
    parser.add_argument("--impvlog", help="import a .vlog to .vlb", action="store_true")
    args = parser.parse_args()

    config = ShrimpConfig()

    config.vlog_path = os.path.abspath(args.vlog)
    config.vlb_path = os.path.abspath(args.vlb)
    config.working_dir = os.path.abspath(args.wd)
    config.aff_path = os.path.abspath(args.aff)
    config.fleet = os.path.abspath(args.flt)
    config.db_path = os.path.abspath(args.db)
    config.import_vlog = args.impvlog

    if args.imp:
        print(import_from_list(config))

    if args.exp:
        print(export_to_vlog(config))
