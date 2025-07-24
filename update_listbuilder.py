#!/usr/bin/env python3
import logging
import logging.handlers

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/updater.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


import argparse
import os
import sqlite3

from lib_updater.utils import (
    scrub_piecename,
    update_piece,
    create_db,
    most_recent_vmod_in_path,
    check_for_new_version,
)
from lib_updater.vassal_module import VassalModule


def main():

    # fmt: off
    parser = argparse.ArgumentParser()
    parser.add_argument("-db", help="Path to VLO DB to update", type=str, default="vlb_pieces.vlo")
    parser.add_argument("-m", help="path to module (.VMOD) to source new piece definitions from", type=str, default="./vmods/")
    parser.add_argument("--auto", help="Check automatically for a new version.  References the top version posted on https://vassalengine.org/wiki/Module:Star_Wars:_Armada.", action="store_true")
    args = parser.parse_args()

    vmod_path = most_recent_vmod_in_path(args.m)
    database_path = os.path.abspath(args.db)
    # fmt:on

    if args.auto:
        vmod_path = check_for_new_version(vmod_path)
        if not vmod_path:
            exit(
                "Auto-update found no new module version available.\n"
                "To manually update, use:\n\n"
                "\tupdate_listbuilder.py -m ./path/to/new_version.vmod"
            )

    armada_module = VassalModule(vmod_path)

    create_db(database_path)
    conn = sqlite3.connect(database_path)

    for piece in armada_module.pieces:

        vlb_entry = armada_module.pieces[piece].compile_vlb_entry()

        update_piece(
            conn,
            armada_module.pieces[piece].piece_type,
            scrub_piecename(armada_module.pieces[piece].name),
            vlb_entry,
        )


if __name__ == "__main__":

    main()
