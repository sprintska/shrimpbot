import logging
import logging.handlers
import os
import re
import sqlite3

from .definitions import (
    nomenclature_translation,
    ambiguous_names,
)
from .fleet import Fleet
from .utils import scrub_piecename, unzipall


_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


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

                    # We check ambiguous name both before and after the nomenclature
                    # translation because the ambiguity may be in either the
                    # fleetbuilder or the canon name.

                    logging.info(
                        "Checking {} ({}) for ambiguity.".format(upgrade, cost)
                    )
                    if (upgrade, cost) in ambiguous_names:
                        translated = ambiguous_names[(upgrade, cost)][0]
                        logging.info(
                            "Ambiguous name {} ({}) translated to {}.".format(
                                upgrade, cost, translated
                            )
                        )
                        upgrade = translated

                    logging.info(
                        "Checking {} ({}) for nomenclature.".format(upgrade, cost)
                    )
                    if upgrade in nomenclature_translation:
                        translated = nomenclature_translation[upgrade]
                        logging.info(
                            "[-] Translated {} to {} - AFD.".format(upgrade, translated)
                        )
                        upgrade = translated

                    logging.info(
                        "Checking {} ({}) for ambiguity.".format(upgrade, cost)
                    )
                    if (upgrade, cost) in ambiguous_names:
                        translated = ambiguous_names[(upgrade, cost)][0]
                        logging.info(
                            "Ambiguous name {} ({}) translated to {}.".format(
                                upgrade, cost, translated
                            )
                        )
                        upgrade = translated

                    _ = ship.add_upgrade(upgrade)

                elif "(" not in card_name:
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
                        # We check ambiguous name both before and after the nomenclature
                        # translation because the ambiguity may be in either the
                        # fleetbuilder or the canon name.

                        logging.info(
                            "Checking {} ({}) for ambiguity.".format(card_name, cost)
                        )
                        if (card_name, cost) in ambiguous_names:
                            card_name_new = ambiguous_names[(card_name, cost)][0]
                            logging.info(
                                "Ambiguous name {} ({}) translated to {}.".format(
                                    card_name, cost, card_name_new
                                )
                            )
                            card_name = card_name_new
                        logging.info(
                            "Checking {} ({}) for nomenclature.".format(card_name, cost)
                        )
                        if card_name in nomenclature_translation:
                            t = nomenclature_translation[card_name]
                            logging.info(
                                "[-] Translated {} to {} - AFD.".format(card_name, t)
                            )
                            card_name = t
                        logging.info(
                            "Checking {} ({}) for ambiguity.".format(card_name, cost)
                        )
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
                    "Version",
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
                        # Can't disambiguate either Venator-II OR VicI on cost, because both variants are identical *sigh*
                        if faction == "Imperial":
                            if card_name == "Venator II (100)":
                                logging.info(
                                    "[Debug] Found Imperial Venator.  Setting card name."
                                )
                                card_name = "Venator II Imp"
                            elif card_name == "Victory I (73)":
                                logging.info(
                                    "[Debug] Found Imperial Victory.  Setting card name."
                                )
                                card_name = "Victory I Imp"
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
