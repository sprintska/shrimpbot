#!/usr/bin/env python3

import shutil
import os
import zipfile
import argparse
import sqlite3
import re
import random
import logging
import logging.handlers



PWD = os.getcwd()

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)

g_import_vlb = os.path.abspath("vlb-out.vlog")
g_vlb_path = os.path.abspath("list.vlb")
g_working_path = os.path.abspath(os.path.join(PWD, "working"))
g_export_to = os.path.abspath("vlb-out.vlog")
g_import_aff = os.path.abspath("test.aff")
g_import_flt = os.path.abspath("list.flt")
g_conn = os.path.abspath("vlb_pieces.vlo")
g_import_vlog = False


""" These dicts translate between canonical names and non-canonical
    (some misspelled, mostly just shorthand).  Because they all have
    to match the Vassal name (as that's what the db is generated
    from), the Vassal errors dict translates correct keys to the
    corresponding incorrect Vassal values, while the listbuilder errors
    dict translates incorrect keys to Vassal values regardless of the
    correctness of the Vassal value.

    "exectuorclass": "executorclass" is a special case because the
    reference in the card itself to the ship token is wrong.  I have no
    idea why it is able to successfully spawn in-game, but this fixes
    it on my side soooo...
"""

# "canon": "non-canon",
vassal_nomenclature_errors = {
    "arc170starfightersquadron": "arc170squadron",
    "arquitensclasscommandcruiser": "arquitenscommandcruiser",
    "arquitensclasslightcruiser": "arquitenslightcruiser",
    "bailorgana": "bailorganacom",
    "belbullab22starfightersquadron": "belbullab22squadron",
    "coloneljendonlambdaclassshuttle": "coloneljendon",
    "consularclasschargerc70": "consularclasschargerc70retrofit",
    "dist81": "distb1",
    "exectuorclass": "executorclass",
    "executoriclassstardreadnought": "executoristardn",
    "executoriiclassstardreadnought": "executoriistardn",
    "gladiatoriclassstardestroyer": "gladiatori",
    "gladiatoriiclassstardestroyer": "gladiatorii",
    "gozanticlassassaultcarriers": "gozantiassaultcarriers",
    "gozanticlasscruisers": "gozanticruisers",
    "greensquadronawing": "greensquadron",
    "greensquadronawingsquadron": "greensquadron",
    "hwk290": "hwk290lightfreighter",
    "hyenaclassdroidbombersquadron": "hyenabombersquadron",
    "imperialiclassstardestroyer": "imperiali",
    "imperialiiclassstardestroyer": "imperialii",
    "imperialstardestroyercymoon1refit": "cymoon1refit",
    "imperialstardestroyerkuatrefit": "kuatrefit",
    "independence": "independance",
    "isdcymoon1refit": "cymoon1refit",
    "isdkuatrefit": "kuatrefit",
    "kyrstaagatecom": "kyrstaagate",
    "landocalrissianoff": "landocalrissian",
    "lieutenantblountz95headhuntersquadron": "lieutenantblount",
    "mandaloriangauntletfighter": "mandogauntletfighter",
    "modifiedpeltaclassassaultship": "peltaclassassaultship",
    "modifiedpeltaclasscommandship": "peltaclasscommandship",
    "obiwankenobi": "obiwankenobicom",
    "providenceclasscarrier": "providencecarrier",
    "providenceclassdreadnought": "providencedreadnought",
    "quasarfireiclasscruisercarrier": "quasarfirei",
    "quasarfireiiclasscruisercarrier": "quasarfireii",
    "raidericlasscorvette": "raideri",
    "raideriiclasscorvette": "raiderii",
    "recusantclasslightdestroyer": "recusantlightdestroyer",
    "recusantclasssupportdestroyer": "recusantsupportdestroyer",
    "stardreadnoughtassaultprototype": "stardnassaultprototype",
    "stardreadnoughtcommandprototype": "stardncommandprototype",
    "vcx100freighter": "vcx100lightfreighter",
    "venatoriclassstardestroyer": "venatori",
    "venatoriiclassstardestroyer": "venatorii",
    "victoryiclassstardestroyer": "victoryi",
    "victoryiiclassstardestroyer": "victoryii",
    "vultureclassdroidfightersquadron": "vulturedroidsquadron",
    "yt1300": "yt1300lightfreighter",
    "yt2400": "yt2400lightfreighter",
    "yv666": "yv666lightfreighter",
}

# "non-canon": "vassal-canon",
listbuilder_nomenclature_errors = {
    "7thfleetstardestroyer": "seventhfleetstardestroyer",
    "acclamatori": "acclamatoriclassassaultship",
    "acclamatorii": "acclamatoriiclassassaultship",
    "acclamatoriclass": "acclamatoriclassassaultship",
    "acclamatoriiclass": "acclamatoriiclassassaultship",
    "admiralozzelcom": "admiralozzel",
    "ahsokatanooff": "ahsokatano",
    "anakinskywalkeryrep": "anakinskywalker",
    "armedcruiser": "consularclassarmedcruiser",
    "assaultfrigatemk2a": "assaultfrigatemarkiia",
    "assaultfrigatemk2b": "assaultfrigatemarkiib",
    "assaultfrigatemkiia": "assaultfrigatemarkiia",
    "assaultfrigatemkiib": "assaultfrigatemarkiib",
    "battlerefit": "hardcellclassbattlerefit",
    "bltbywingsquadron": "btlbywingsquadron",
    "chargerc70": "consularclasschargerc70retrofit",
    "clonecmdrwolffe": "clonecommanderwolffe",
    "commsfrigate": "munificentclasscommsfrigate",
    "consulararmedcruiser": "consularclassarmedcruiser",
    "consularchargerc70": "consularclasschargerc70retrofit",
    "cr90acorvette": "cr90corvettea",
    "cr90bcorvette": "cr90corvetteb",
    "cr90corelliancorvettea": "cr90corvettea",
    "cr90corelliancorvetteb": "cr90corvetteb",
    "dby827heavyturbolaser": "dby827heavyturbolasers",
    "genericritrcommander": "admiralkonstantine",
    "hardcellbattlerefit": "hardcellclassbattlerefit",
    "hardcelltransport": "hardcellclasstransport",
    "hardendbulkheads": "hardenedbulkheads",
    "hyenadroidbombersquadron": "hyenabombersquadron",
    "ig88ig2000": "ig88",
    "interdictorclasssuppressionrefit": "interdictorsuppressionrefit",
    "interdictorclasscombatrefit": "interdictorcombatrefit",
    "lambdashuttle": "lambdaclassshuttle",
    "lancerpursuitcraft": "lancerclasspursuitcraft",
    "landocarissian": "landocalrissian",
    "lietenantblount": "lieutenantblount",
    "linkedturbolaserturrets": "linkedturbolasertowers",
    "locationfirecontrol": "localfirecontrol",
    "maareksteele": "maarekstele",
    "moncalamariexodusfleet": "moncalexodusfleet",
    "munificentcommsfrigate": "munificentclasscommsfrigate",
    "munificentstarfrigate": "munificentclassstarfrigate",
    "munitionsresuppy": "munitionsresupply",
    "onagerstardestroyer": "onagerclassstardestroyer",
    "onagertestbed": "onagerclasstestbed",
    "partsresuppy": "partsresupply",
    "peltaassaultship": "peltaclassassaultship",
    "peltacommandship": "peltaclasscommandship",
    "peltamedicalfrigate": "peltaclassmedicalfrigate",
    "peltatransportfrigate": "peltaclasstransportfrigate",
    "rayantilles": "raymusantilles",
    "solorcorona": "solarcorona",
    "ssdexecutori": "executoristardn",
    "ssdexecutorii": "executoriistardn",
    "ssdcommandprototype": "stardncommandprototype",
    "ssdassaultprototype": "stardnassaultprototype",
    "starfrigate": "munificentclassstarfrigate",
    "starhawkclassmki": "starhawkmarki",
    "starhawkclassmkii": "starhawkmarkii",
    "starhawkbattleshipmarki": "starhawkmarki",
    "starhawkbattleshipmarkii": "starhawkmarkii",
    "starhawkclassbattleshipmarki": "starhawkmarki",
    "starhawkclassbattleshipmarkii": "starhawkmarkii",
    "supriseattack": "surpriseattack",
    "transport": "hardcellclasstransport",
    "vulturedroidfightersquadron": "vulturedroidsquadron",
    "xcustomcommander": "admiralkonstantine",
    "x17turbolasers": "xi7turbolasers",
}

nomenclature_translation = {
    **vassal_nomenclature_errors,
    **listbuilder_nomenclature_errors,
}

""" This dict pairs names of identically-named cards (Darth Vader, Leia Organa,
    etc) with their costs in a tuple (the key) to reference their Vassal name and 
    card type.
"""

ambiguous_names = {
    ("admiralozzel", "20"): ("admiralozzel", "upgrade"),
    ("admiralozzel", "2"): ("admiralozzeloff", "upgrade"),
    ("ahsokatano", "23"): ("ahsokatano", "squadron"),
    ("ahsokatano", "2"): ("ahsokatano", "upgrade"),
    ("ahsokatano", "6"): ("ahsokatanorepoff", "upgrade"),
    ("darthvader", "36"): ("darthvadercom", "upgrade"),
    ("darthvader", "3"): ("darthvaderwpn", "upgrade"),
    ("darthvader", "1"): ("darthvaderoff", "upgrade"),
    ("darthvader", "21"): ("darthvader", "squadron"),
    ("emperorpalpatine", "35"): ("emperorpalpatinecom", "upgrade"),
    ("emperorpalpatine", "3"): ("emperorpalpatineoff", "upgrade"),
    ("generalgrievous", "20"): ("generalgrievouscom", "upgrade"),
    ("generalgrievous", "22"): ("generalgrievous", "squadron"),
    ("hondoohnaka", "24"): ("hondoohnaka", "squadron"),
    ("hondoohnaka", "2"): ("hondoohnaka", "upgrade"),
    ("kyrstaagate", "20"): ("kyrstaagate", "upgrade"),
    ("kyrstaagate", "5"): ("kyrstaagateoff", "upgrade"),
    ("landocalrissian", "23"): ("landocalrissian", "squadron"),
    ("landocalrissian", "4"): ("landocalrissian", "upgrade"),
    ("leiaorgana", "28"): ("leiaorganacom", "upgrade"),
    ("leiaorgana", "3"): ("leiaorganaoff", "upgrade"),
    ("luminaraunduli", "23"): ("luminaraunduli", "squadron"),
    ("luminaraunduli", "25"): ("luminaraundulicom", "upgrade"),
    ("plokoon", "26"): ("plokooncom", "upgrade"),
    ("plokoon", "24"): ("plokoon", "squadron"),
    ("wedgeantilles", "19"): ("wedgeantilles", "squadron"),
    ("wedgeantilles", "4"): ("wedgeantillesoff", "upgrade"),
}


def unzipall(zip_file_path, tar_path):

    """Unzips all of the files in the zip file at zip_file_path and
    dumps all those files into directory tar_path.

    I'm pretty sure this duplicates a built-in function, but, I mean...
    it works."""

    zip_ref = zipfile.ZipFile(zip_file_path, "r")
    zip_ref.extractall(tar_path)
    zip_ref.close()


def zipall(tar_path, zip_file_path):

    """Creates a new zip file at zip_file_path and populates it with
    the zipped contents of tar_path.

    I'm pretty sure this duplicates a built-in function, but, I mean...
    it works."""

    shittyname = shutil.make_archive(zip_file_path, "zip", tar_path)
    shutil.move(shittyname, zip_file_path)


def ident_format(fleet_text):

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
            if " • " in line:
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
        # try:
        if line.strip().startswith("• ") or line.strip().startswith("\u2022"):
            # ~ print(line.strip())
            formats["kingston"] += 1
        # except: pass

    # AFF
    if fleet_text[0] == "{":
        formats["aff"] += 30.0
    if fleet_text.startswith("ship:"):
        formats["aff"] += 30.0
    if fleet_text.startswith("squadron:"):
        formats["aff"] += 30

    logging.info(formats)
    return max(formats.keys(), key=(lambda x: formats[x]))


def import_from_list(import_from, output_to, working_path, conn, isvlog=False):

    ingest_format = {
        "fab": import_from_fabs,
        "warlord": import_from_warlords,
        "afd": import_from_afd,
        "kingston": import_from_kingston,
        "aff": import_from_aff,
        "vlog": import_from_vlog,
    }

    if isvlog:
        import_from_vlog(import_from, output_to, working_path, conn)
    else:
        if os.path.exists(import_from):
            logging.info(import_from)
            with open(import_from) as fleet_list:
                fleet_text = fleet_list.read()
        else:
            fleet_text = import_from

        fmt = ident_format(fleet_text)
        success, f = ingest_format[fmt](fleet_text, output_to, working_path, conn)
        logging.info(success, f)

        if not success:
            return (success, f)

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
                # ~ print(f.objectives[o])
                vlb.write(f.objectives[o].content + chr(27))

        return (True, None)


def import_from_fabs(import_list, vlb_path, working_path, conn):

    """Imports a Fab's Fleet Builder list into a Fleet object"""

    f = Fleet("Food", conn=conn)
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
                            # print("=-"*25)
                            # print("Objectives: {}".format(l))
                            pass
                        else:
                            working_line = this_line.split(" - ")
                            s = f.add_ship(working_line[0].strip())
                            for u in working_line[1::]:
                                s.add_upgrade(u.strip())

                    else:
                        issquadron = False
                        isship = False
                        issquadronfancy = False
                        this_line = scrub_piecename(this_line)
                        if this_line in nomenclature_translation:
                            t = nomenclature_translation[this_line]
                            logging.info(
                                "[-] Translated {} to {} - Fab's.".format(this_line, t)
                            )
                            this_line = t
                        logging.info(
                            "Searching for Fab's piece {} in {}".format(
                                scrub_piecename(this_line), str(conn)
                            )
                        )
                        try:
                            with sqlite3.connect(conn) as connection:
                                issquadron = connection.execute(
                                    """SELECT * FROM pieces
                                        WHERE piecetype='squadroncard'
                                        AND piecename LIKE ?;""",
                                    ("%" + scrub_piecename(this_line) + "%",),
                                ).fetchall()
                        except ValueError as err:
                            logging.exception(err)

                        try:
                            with sqlite3.connect(conn) as connection:
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
                                with sqlite3.connect(conn) as connection:
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
                            f.add_squadron(this_line.strip())
                        elif bool(issquadronfancy):
                            _ = f.add_squadron(ltmp.strip())
                        elif bool(isship):
                            s = f.add_ship(this_line.strip())
                        else:
                            logging.info(
                                "{}{} IS FUCKED UP, YO{}".format(
                                    "=" * 40, this_line, "=" * 40
                                )
                            )
        except Exception as err:
            logging.exception(err)
            return (False, last_line)

    return (True, f)


def import_from_warlords(import_list, vlb_path, working_path, conn):

    """Imports an Armada Warlords list into a Fleet object"""

    f = Fleet("Food", conn=conn)

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
        logging.info("SELECT piecetype FROM pieces where piecename LIKE %{}%").format(
            scrub_piecename(ship_check)
        )
        with sqlite3.connect(conn) as connection:
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
                f.add_objective(objective[0], objective[1])
                shipnext = False

            elif squadron_regex.search(card_name):
                squadron, cost = card_name.split("(", 1)
                squadron = scrub_piecename(
                    "".join(card_name.split("(")[0].split()[1::])
                )
                cost = scrub_piecename(cost.split()[0])
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
                f.add_squadron(squadron)
                shipnext = False

            elif card_name[0] == "=":
                shipnext = True

            elif shipnext:
                ship, cost = card_name.split("]")[-1].split("(")
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
                s = f.add_ship(ship)
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

    return (True, f)


def import_from_afd(import_list, vlb_path, working_path, conn):

    """Imports an Armada Fleets Designer list into a Fleet object"""

    f = Fleet("Food", conn=conn)

    start = False
    obj_category = "assault"
    # shipnext = False

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

                    _ = s.add_upgrade(upgrade)

                elif "(" not in card_name:
                    logging.info("Hit the conditional for {}.".format(card_name))
                    card_name = scrub_piecename(str(card_name))
                    f.add_objective(obj_category, card_name)

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
                                scrub_piecename(card_name), str(conn)
                            )
                        )
                        with sqlite3.connect(conn) as connection:
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
                                card_name, str(conn)
                            )
                        )
                        with sqlite3.connect(conn) as connection:
                            isship = connection.execute(
                                """SELECT * FROM pieces
                                    WHERE piecetype='shipcard'
                                    AND piecename LIKE ?;""",
                                ("%" + card_name,),
                            ).fetchall()
                    except ValueError as err:
                        logging.exception(err)

                    if bool(issquadron):
                        _ = f.add_squadron(card_name)
                    elif bool(isship):
                        s = f.add_ship(card_name)
                    else:
                        logging.info(
                            "{}{} IS FUCKED UP, YO{}".format(
                                "=" * 40, card_name, "=" * 40
                            )
                        )
        except Exception as err:
            logging.exception(err)
            return (False, last_line)

    return (True, f)


def import_from_kingston(import_list, vlb_path, working_path, conn):

    """Imports an Ryan Kingston list into a Fleet object"""

    f = Fleet("Food", conn=conn)

    logging.info("Fleet created with database {}.".format(str(conn)))

    shipnext = True

    for line in import_list.split("\n"):

        try:
            card_name = line.replace("â€¢", "\u2022").strip()
            logging.info(card_name)
            last_line = card_name

            if card_name:

                if card_name.split(":")[0].strip() in [
                    "Name",
                    "Faction",
                    "Commander",
                    "Author",
                ]:
                    pass

                elif card_name.split(":")[0] in ["Assault", "Defense", "Navigation"]:
                    if card_name.strip()[-1] != ":":
                        logging.info("{}".format(card_name))
                        _ = f.add_objective(
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

                        _ = s.add_upgrade(card_name)

                    elif card_name[0] == "=":
                        pass

                    else:
                        s = f.add_ship(card_name.split(" (", 1)[0].strip())

                elif "\u2022" in card_name and card_name[0] != "=":
                    card_name, cost = card_name.split(" x ")[-1].split(" (", 1)
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

                    _ = f.add_squadron(card_name)
        except Exception as err:
            logging.exception(err)
            return (False, last_line)

    return (True, f)


def import_from_aff(import_list, vlb_path, working_path, conn):

    """Imports a .aff (Armada Fleet Format) file into a Fleet object"""

    f = Fleet("Food", conn=conn)

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


def import_from_vlog(import_from, vlb_path, working_path, conn):

    """Strips out all the compression and obfuscation from a VASSAL
    log/continution .vlog file at path import_from and creates an
    unobfuscated .vlb text file at path vlb_path."""

    unzipall(import_from, working_path)

    with open(os.path.join(working_path, "savedGame"), "r") as vlog:
        b_vlog = vlog.read()

    xor_key_str = b_vlog[5:7]
    # print(xor_key_str)
    xor_key = int(xor_key_str, 16)
    # print(xor_key)
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

    with open(vlb_path, "w") as vlb:
        vlb.write(xor_key_str + "\r\n")
        vlb.write(clear)


def export_to_vlog(export_to, vlb_path, working_path=g_working_path):

    """Adds all the obfuscation and compression to turn a .vlb
    VASSAL listbuilder file (at vlb_path), along with boilerplate
    savedata and moduledata XML files in working_path, into a VASSAL-
    compatible .vlog replay file."""

    out_path = os.path.join(working_path, "..", "out")

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
        os.path.join(working_path, "moduledata"), os.path.join(out_path, "moduledata")
    )
    shutil.copyfile(
        os.path.join(working_path, "savedata"), os.path.join(out_path, "savedata")
    )

    with open(vlb_path, "r") as vlb:
        in_vlb = vlb.read()

    in_vlb = in_vlb.replace("\r", "").replace("\n", "")
    # print(in_vlb[0:2])
    xor_key = int(in_vlb[0:2], 16)
    clear = in_vlb[2::]
    # print(in_vlb[0:2])
    # print(in_vlb[2:10])
    obf_out = "!VCSK" + (in_vlb[0:2])
    # print(obf_out)
    for char in clear:
        obfint = ord(char) ^ xor_key
        obf_out += hex(obfint)[2::]

    with open(os.path.join(working_path, "savedGame"), "w") as savedgame_out:
        savedgame_out.write(obf_out)

    zipall(working_path, os.path.abspath(export_to))


def scrub_piecename(piecename):

    scrub_these = " :!-'(),\"+.\t\r\n·[]" + "\u2022"

    piecename = piecename.replace("\/", "").split("/")[0].split(";")[-1]

    for char in scrub_these:
        piecename = piecename.replace(char, "")

    return piecename.lower()


def calc_guid():

    return str(round(random.random() * 10 ** 13))


class Piece:

    """Meant to be a prototype for the other pieces, not really to be used on its own"""

    def __init__(self, piecename, conn=g_conn):

        self.banana = scrub_piecename(str(piecename))
        self.conn = conn
        with sqlite3.connect(self.conn) as connection:
            self.content = connection.execute(
                """select content from pieces where piecename=?;""", (self.upgradename,)
            ).fetchall()[0][0]

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")
        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords


class Fleet:
    def __init__(
        self,
        name,
        faction="",
        points=0,
        mode="",
        fleet_version="",
        description="",
        objectives={},
        ships=[],
        squadrons=[],
        author="",
        conn=g_conn,
    ):

        self.name = str(name)
        self.faction = str(faction)
        self.points = int(points)
        self.mode = str(mode)
        self.fleet_version = str(fleet_version)
        self.description = str(description)
        self.objectives = dict(objectives)
        self.ships = list(ships)
        self.squadrons = list(squadrons)
        self.author = str(author)
        self.conn = conn

        # simple piece locations calculations

        self.x = 200
        self.ship_y = 850
        self.upgd_upper_y = 775

        self.sc_to_obj_x_padding = -100
        self.sc_to_obj_y_padding = 0
        self.obj_x = self.x + self.sc_to_obj_x_padding
        self.obj_y = self.ship_y + self.sc_to_obj_y_padding

        self.cmd_to_sc_x_offset = 90
        self.cmd_to_sc_y_offset = -10

        self.sc_to_st_x_padding = 173
        self.sc_to_st_y_padding = 0
        # self.s_to_u_padding = 60
        # self.u_to_u_x_padding = 105
        # self.u_to_u_y_padding = 175
        self.s_to_u_padding = 50
        self.u_to_u_x_padding = 145
        self.u_to_u_y_padding = 225
        self.u_to_s_padding = 195
        self.u_to_sq_padding = 195
        self.upgd_lower_y = self.upgd_upper_y + self.u_to_u_y_padding
        self.sq_to_sq_x_padding = 175
        self.sq_to_sq_y_padding = 240
        self.obj_to_obj_x_offset = 25
        self.obj_to_obj_y_offset = 25

        self.sq_y_offset = -120
        self.sq_upper_y = self.ship_y + self.sq_y_offset
        self.sq_lower_y = self.sq_upper_y + self.sq_to_sq_y_padding
        self.sq_row = 1

    def set_name(self, name):

        self.name = str(name)

    def set_faction(self, faction):

        self.faction = str(faction)

    def set_points(self, points):

        self.points = int(points)

    def set_mode(self, mode):

        self.mode = str(mode)

    def set_fleet_version(self, fleet_version):

        self.fleet_version = str(fleet_version)

    def set_description(self, description):

        self.description = str(description)

    def set_objectives(self, objectives):

        self.objectives = dict(objectives)

    def add_ship(self, shipclass):

        shipclass = scrub_piecename(shipclass)
        if shipclass in nomenclature_translation:
            sc = nomenclature_translation[shipclass]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Fleet.add_ship().".format(
                    shipclass, sc
                )
            )
            shipclass = sc

        s = Ship(shipclass, self, self.conn)
        self.x += self.u_to_s_padding
        s.set_coords([str(self.x), str(self.ship_y)])
        s.shipcard.set_coords([str(self.x), str(self.ship_y)])
        s.shipcmdstack.set_coords(
            [
                str(self.x + self.cmd_to_sc_x_offset),
                str(self.ship_y + self.cmd_to_sc_y_offset),
            ]
        )
        self.x += self.sc_to_st_x_padding
        s.shiptoken.set_coords(
            [str(self.x), str(self.ship_y + self.sc_to_st_y_padding)]
        )
        self.x += self.s_to_u_padding
        self.u_row = 1

        self.ships.append(s)
        return s

    def remove_ship(self, ship):

        self.ships.remove(ship)

    def add_squadron(self, squadronclass):

        squadronclass = scrub_piecename(squadronclass)
        if squadronclass in nomenclature_translation:
            sc = nomenclature_translation[squadronclass]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Fleet.add_squadron().".format(
                    squadronclass, sc
                )
            )
            squadronclass = sc

        sq = Squadron(squadronclass, self, self.conn)
        if self.sq_row % 2:
            self.x += self.sq_to_sq_x_padding
            sq.set_coords([str(self.x), str(self.sq_upper_y)])
            sq.squadroncard.set_coords([str(self.x), str(self.sq_upper_y)])
            sq.squadrontoken.set_coords([str(self.x), str(self.sq_upper_y)])
        else:
            sq.set_coords([str(self.x), str(self.sq_lower_y)])
            sq.squadroncard.set_coords([str(self.x), str(self.sq_lower_y)])
            sq.squadrontoken.set_coords([str(self.x), str(self.sq_lower_y)])
        self.sq_row += 1

        self.squadrons.append(sq)
        return sq

    def remove_squadron(self, squadron):

        self.squadrons.remove(squadron)

    def add_objective(self, category, objectivename):

        category = scrub_piecename(category)
        objectivename = scrub_piecename(objectivename)

        if objectivename in nomenclature_translation:
            ob = nomenclature_translation[objectivename]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Fleet.add_objective()".format(
                    objectivename, ob
                )
            )
            objectivename = ob

        if "custom" in objectivename.lower():
            return False

        obj_categories = ["assault", "defense", "navigation", "campaign", "other"]
        if category.lower() in obj_categories:
            self.objectives[category] = Objective(objectivename, self.conn)
        else:
            # except:
            # raise ValueError
            logging.info("{} is not a valid objective type.".format(str(category)))
            logging.info("Valid types are: {}".format(obj_categories))

        self.objectives[category].set_coords([str(self.obj_x), str(self.obj_y)])
        self.obj_x = self.obj_x + self.obj_to_obj_x_offset
        self.obj_y = self.obj_y + self.obj_to_obj_y_offset

    def remove_objective(self, category, objective):

        if category in self.objectives.keys():
            if self.objectives[category] == objective:
                del self.objectives[category]

    def __add__(self, ship):

        self.add_ship(ship)

    def __sub__(self, ship):

        self.remove_ship(ship)


class Ship:
    def __init__(self, shipclass, ownfleet, conn=g_conn):

        self.shipclass = scrub_piecename(str(shipclass))  # "name" in .AFF
        self.conn = conn
        self.content = ""
        self.coords = [0, 0]
        self.physicalsize = [
            [0, 0],
            [0, 0],
        ]  # amt of table space for shipcard, stack, and all upgrades
        self.shipcard = ShipCard(self.shipclass, self.conn)
        self.shiptoken = self.shipcard.shiptoken
        self.shipcmdstack = self.shipcard.shipcmdstack
        self.upgrades = []
        self.guid = calc_guid()

        self.ownfleet = ownfleet

    def set_content(self, content):

        self.content = str(content)

    def set_coords(self, coords):

        self.coords = list(coords)

    def set_shipcard(self, shipcard):

        self.shipcard = shipcard

    def set_shiptoken(self, shiptoken):

        self.shiptoken = shiptoken

    def set_upgrades(self, upgrades):

        self.upgrades = list(upgrades)

    def add_upgrade(self, upgradename):

        upgradename = scrub_piecename(upgradename)
        if upgradename in nomenclature_translation:
            sc = nomenclature_translation[upgradename]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.Ship.add_upgrade().".format(
                    upgradename, sc
                )
            )
            upgradename = sc

        u = Upgrade(upgradename, self, self.conn)

        if self.ownfleet.u_row % 2:
            self.ownfleet.x += self.ownfleet.u_to_u_x_padding
            u.set_coords([str(self.ownfleet.x), str(self.ownfleet.upgd_upper_y)])
        else:
            u.set_coords([str(self.ownfleet.x), str(self.ownfleet.upgd_lower_y)])
        self.ownfleet.u_row += 1

        self.upgrades.append(u)
        return u

    def remove_upgrade(self, upgrade):

        self.upgrades.remove(upgrade)

    def __add__(self, upgrade):

        self.add_upgrade(upgrade)

    def __sub__(self, upgrade):

        self.remove_upgrade(upgrade)


class ShipCard:

    """A shipcard of type str(shipname) as defined in sqlitedb connection conn."""

    def __init__(self, shipname, conn=g_conn):

        self.shipname = scrub_piecename(str(shipname))
        self.conn = conn

        logging.info(
            "Searching for ship {} in {}".format(self.shipname, str(self.conn))
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                logging.debug("0")
                exact_match = connection.execute(
                    """select content,catchall 
                    from pieces 
                    where piecetype='shipcard' 
                    and piecename=?;""",
                    (self.shipname,),
                ).fetchall()
                logging.debug(".5")
            logging.debug("1")
            # logging.info(str(exact_match))
            # logging.info(str(len(exact_match)))
            if len(exact_match) == 1:
                logging.debug("2")
                [(self.content, self.shiptype)] = exact_match
                logging.debug("3")
            if not (hasattr(self, 'content') and hasattr(self, 'shiptype')):
                logging.debug("4")
                raise RuntimeError(f"Did not find ship card {self.shipname}")
        except RuntimeError as err:
            logging.debug("5")
            logging.debug(err,exc_info=err)
            logging.debug("6")
        except Exception as err:
            logging.debug("7")
            logging.debug(err,exc_info=err)
            raise err

        logging.debug("8")
        self.shiptoken = ShipToken(self.shiptype, self.conn)

        self.guid = calc_guid()
        logging.debug("9")
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

        logging.debug("10")

        self.command = self.content.split("/placemark;Spawn Command ")[-1][0]
        self.command = "commandstack" + self.command
        self.shipcmdstack = ShipCmdStack(self.command, self.conn)

        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords

    def set_guid(self, guid):

        self.content = self.content.replace("vlb_GUID", self.guid)

    def set_shiptoken(self, shiptype):

        self.shiptoken = ShipToken(shiptype, self.conn)


class ShipToken:
    def __init__(self, shiptype, conn=g_conn):

        self.shiptype = scrub_piecename(str(shiptype))
        self.conn = conn

        if self.shiptype in nomenclature_translation:
            translated_shiptype = nomenclature_translation[self.shiptype]
            logging.info(
                "[-] Translated {} to {} - in listbuilder.ShipToken.".format(
                    self.shiptype, translated_shiptype
                )
            )
            self.shiptype = translated_shiptype

        logging.info(
            "Searching for ship token {} in {}".format(self.shiptype, str(self.conn))
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='ship' and piecename=?;""",
                    (self.shiptype,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find ship token {self.shiptype}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err,exc_info=err)
            raise err

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")
        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords


class ShipCmdStack:

    """A command stack as defined in sqlitedb connection conn."""

    def __init__(self, cmdstack, conn=g_conn):

        self.cmdstack = scrub_piecename(str(cmdstack))
        self.conn = conn

        logging.info(
            "Searching for command stack {} in {}".format(self.cmdstack, str(self.conn))
        )
        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='other' and piecename=?;""",
                    (self.cmdstack,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find command stack {self.cmdstack}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err,exc_info=err)
            raise err

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")
        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords

    def set_guid(self, guid):

        self.content = self.content.replace("vlb_GUID", self.guid)


class Upgrade:
    def __init__(self, upgradename, ownship, conn=g_conn):

        self.upgradename = scrub_piecename(str(upgradename))
        self.conn = conn

        logging.info(
            "Searching for upgrade {} in {}".format(self.upgradename, str(self.conn))
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='upgradecard' and piecename=?;""",
                    (self.upgradename,),
                ).fetchall()

            self.content = False
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find upgrade {self.upgradename}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.exception(err)
            raise err

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")
        self.coords = [0, 0]

        self.ownship = ownship

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords


class Squadron:
    def __init__(self, squadronclass, ownfleet, conn=g_conn):

        self.squadronclass = scrub_piecename(str(squadronclass))  # "name" in .AFF
        self.conn = conn
        self.content = ""
        self.coords = [0, 0]
        self.squadroncard = SquadronCard(self.squadronclass, self.conn)
        self.squadrontoken = self.squadroncard.squadrontoken
        self.upgrades = []
        self.guid = calc_guid()

        self.ownfleet = ownfleet

    def set_content(self, content):

        self.content = str(content)

    def set_coords(self, coords):

        self.coords = list(coords)

    def set_squadroncard(self, squadroncard):

        self.squadroncard = squadroncard

    def set_squadrontoken(self, squadrontoken):

        self.squadrontoken = squadrontoken


class SquadronCard:

    """A squadroncard of type str(squadronname) as defined in sqlite connection conn."""

    def __init__(self, squadronname, conn=g_conn):

        self.squadronname = scrub_piecename(str(squadronname))
        self.conn = conn
        # print("[*] Retrieving {}".format(self.squadronname))

        logging.info(
            "Searching for squadron card {} in {}".format(
                self.squadronname, str(self.conn)
            )
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content,catchall 
                    from pieces 
                    where piecetype='squadroncard' and piecename like ?;""",
                    (self.squadronname,),
                ).fetchall()
            if len(exact_match) == 1:
                [(self.content, self.squadrontype)] = exact_match
            else:
                with sqlite3.connect(self.conn) as connection:
                    [(self.content, self.squadrontype)] = connection.execute(
                        """select content,catchall 
                        from pieces 
                        where piecetype='squadroncard' and piecename like ?;""",
                        ("%" + self.squadronname + "%",),
                    ).fetchall()
        except ValueError as err:
            logging.exception(f"Did not find squadron {self.squadronname}")
            raise err
        except Exception as err:
            logging.debug(err,exc_info=err)
            raise err

        self.squadrontoken = SquadronToken(self.squadrontype, self.conn)

        # self.guid = str(round(time.time()*1000))
        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")
        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords

    def set_guid(self, guid):

        self.content = self.content.replace("vlb_GUID", self.guid)

    def set_squadrontoken(self, squadrontype):

        self.squadrontoken = SquadronToken(squadrontype, self.conn)


class SquadronToken:
    def __init__(self, squadrontype, conn=g_conn):

        self.squadrontype = scrub_piecename(str(squadrontype))
        self.conn = conn
        # print(squadrontype)
        logging.info(
            "Searching for squadron token {} in {}".format(
                scrub_piecename(squadrontype), str(conn)
            )
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='squadron' and piecename=?;""",
                    (self.squadrontype,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find squadron token {self.squadrontype}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err,exc_info=err)
            raise err

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")
        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords


class Objective:
    def __init__(self, objectivename, conn=g_conn):

        self.objectivename = scrub_piecename(str(objectivename))
        self.conn = conn
        logging.info(
            "Searching for objective {} in {}".format(
                self.objectivename, str(self.conn)
            )
        )

        try:
            with sqlite3.connect(self.conn) as connection:
                exact_match = connection.execute(
                    """select content 
                    from pieces 
                    where piecetype='objective' and piecename=?;""",
                    (self.objectivename,),
                ).fetchall()
            if len(exact_match) == 1:
                if len(exact_match[0]) == 1:
                    self.content = exact_match[0][0]
            if not self.content:
                raise RuntimeError(f"Did not find objective {self.objectivename}")
        except RuntimeError as err:
            logging.exception(err)
            raise err
        except Exception as err:
            logging.debug(err,exc_info=err)
            raise err

        self.guid = calc_guid()
        self.content = self.content.replace("vlb_GUID", self.guid)
        self.content = self.content.replace("vlb_x_axis", "0")
        self.content = self.content.replace("vlb_y_axis", "0")

        c = ""
        for line in self.content.split("\t"):
            if line.strip().startswith("piece;;;;"):
                # ~ print("[!] Replaced on line:")
                # ~ print(line)
                this_line = line.replace("1", "2")
            else:
                this_line = line
            c += this_line + "\t"

        # ~ print(c)
        self.content = c

        self.coords = [0, 0]

    def set_coords(self, coords):

        if type(coords) == list and len(coords) == 2:
            self.content = re.sub(
                "Table;\d{1,4};\d{1,4}",
                "Table;{};{}".format(str(coords[0]), str(coords[1])),
                self.content,
            )
            self.coords = coords


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-db", help="VLO DB to reference for pieces", type=str, default="vlb_pieces.vlo"
    )
    parser.add_argument(
        "-wd",
        help="working directory to use with VLB",
        type=str,
        default=os.path.join(PWD, "working"),
    )
    parser.add_argument("-vlog", help=".vlog filename", type=str, default="vlb-out.vlog")
    parser.add_argument("-vlb", help=".vlb filename", type=str, default="list.vlb")
    parser.add_argument("-aff", help=".aff filename", type=str, default="test.aff")
    parser.add_argument(
        "-flt",
        help="fleet list location--VAL will attempt to identify and ingest the list in "
        + "the given format",
        type=str,
        default="list.flt",
    )
    parser.add_argument(
        "--imp", help="use VL to import a .vlog to a .vlb", action="store_true"
    )
    parser.add_argument(
        "--exp", help="use VL to export a .vlb to a .vlog", action="store_true"
    )
    parser.add_argument(
        "--impvlog", help="use this if importing a .vlog to .vlb.", action="store_true"
    )
    args = parser.parse_args()

    g_import_vlb = os.path.abspath(args.vlog)
    g_vlb_path = os.path.abspath(args.vlb)
    g_working_path = os.path.abspath(args.wd)
    g_export_to = os.path.abspath(args.vlog)
    g_import_aff = os.path.abspath(args.aff)
    g_import_flt = os.path.abspath(args.flt)
    g_conn = os.path.abspath(args.db)
    g_import_vlog = args.impvlog
    

    if args.imp:
        print(
            import_from_list(
                import_from=g_import_flt,
                output_to=g_vlb_path,
                working_path=g_working_path,
                conn=g_conn,
                isvlog=g_import_vlog,
            )
        )

    if args.exp:
        print(export_to_vlog(export_to=g_export_to, vlb_path=g_vlb_path))
