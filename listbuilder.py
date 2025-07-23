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
import shutil

from lib_listbuilder.importers import (
    import_from_fabs,
    import_from_warlords,
    import_from_afd,
    import_from_kingston,
    import_from_aff,
    import_from_vlog,
)
from lib_listbuilder.utils import zipall

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


class ShrimpConfig:
    """Configuration class for the listbuilder module."""

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


def identify_format(fleet_text):
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

        fmt = identify_format(fleet_text)
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
    """Returns a default configuration for the listbuilder module."""
    return ShrimpConfig()


def main():
    """Main function to handle command line arguments and execute the appropriate import/export functions."""

    config = ShrimpConfig()

    # fmt: off
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-db", help="path to reference database", type=str, default="vlb_pieces.vlo")
    parser.add_argument("-wd",help="working directory",type=str,default=os.path.join(config.pwd, "working"),)
    parser.add_argument("-vlog", help=".vlog filename", type=str, default="vlb-out.vlog")
    parser.add_argument("-vlb", help=".vlb filename", type=str, default="list.vlb")
    parser.add_argument("-aff", help=".aff filename", type=str, default="test.aff")
    parser.add_argument("-flt", help="fleet list location", type=str, default="list.flt")
    parser.add_argument("--imp", help="import a .vlog to a .vlb", action="store_true")
    parser.add_argument("--exp", help="export a .vlb to a .vlog", action="store_true")
    parser.add_argument("--impvlog", help="import a .vlog to .vlb", action="store_true")
    args = parser.parse_args()

    config = ShrimpConfig(
        vlog=args.vlog,
        vlb=args.vlb,
        working_dir=args.wd,
        aff=args.aff,
        flt=args.flt,
        db=args.db,
        import_vlog=args.impvlog,
    )
    # fmt: on

    if args.imp:
        print(import_from_list(config))

    if args.exp:
        print(export_to_vlog(config))


if __name__ == "__main__":

    main()
