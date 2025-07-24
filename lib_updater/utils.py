import logging
import logging.handlers

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)

import os
import pathlib
import re
import requests
import sqlite3


def associated_token(piece_name, piece_type, vlb_content):
    """Determines if the vlb_content indicates that the entry should be associated with
    a ship or squadron token; returns the name of that token, if so."""

    # associate the ship token to the ship card
    if piece_type == "shipcard":
        ship_token = ""
        if "quasar" in piece_name:
            ship_token = "quasarfirecruisercarrier"  # fuck the Quasar, I don't know why it can't be fucking normal
        else:
            for line in vlb_content.split("\t"):
                if line.startswith("placemark;Spawn") and ("Capital Ships" in line):
                    ship_token = line.split("\\/VASSAL.build.widget.PieceSlot:")[
                        -1
                    ].split(";")[0]
                    ship_token = scrub_piecename(ship_token)
        return ship_token

    # associate the squadron token to the squadron card
    elif piece_type == "squadroncard":
        sqd_token = ""
        for line in vlb_content.split("\t"):
            if line.startswith("placemark;Spawn squadron"):
                sqd_token = line.split("\\/VASSAL.build.widget.PieceSlot:")[-1].split(
                    ";"
                )[0]
                sqd_token = scrub_piecename(sqd_token)
        return sqd_token

    return ""


def check_for_new_version(
    latest_local_vmod_path,
    vassal_url="https://vassalengine.org/library/projects/Star_Wars:_Armada",
):

    if not latest_local_vmod_path.exists():
        raise FileNotFoundError(
            "Module file does not exist: " + str(latest_local_vmod_path)
        )

    local_vmod_dir = latest_local_vmod_path.parent

    r = requests.get(vassal_url)

    vmod_regex = re.compile(r'obj.vassalengine.org/images/\S+?.vmod"')
    available_vmod_urls = vmod_regex.finditer(str(r.content))
    latest_vmod_url = (
        "https://" + [hit.group(0).strip('"') for hit in available_vmod_urls][0]
    )

    latest_vmod_filename = latest_vmod_url.split("/")[-1]

    if latest_vmod_filename == latest_local_vmod_path.name:
        logging.info(
            f"[*] Checked for new module version.  Locally installed VMOD matches latest version at {latest_vmod_filename}."
        )
        return False

    logging.info(
        f"[+] New VMOD version found: {latest_vmod_filename}.\n\tDownloading from {latest_vmod_url}..."
    )
    new_vmod_path = pathlib.Path(local_vmod_dir / latest_vmod_filename)
    r = requests.get(latest_vmod_url)
    logging.info(f"[+] Writing to {new_vmod_path}...")
    with open(new_vmod_path, "wb") as f:
        f.write(r.content)

    return new_vmod_path


def create_db(db_path):
    """Create the db at the path if it doesn't exist"""

    if not os.path.exists(db_path):
        with open(db_path, "w"):
            pass

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "CREATE TABLE pieces (piecetype text, piecename text, content text, catchall text)"
            )
            conn.commit()


def exists_piece(conn, piecetype, piecename):
    """checks for existence of piece name/type."""

    return bool(
        conn.execute(
            """SELECT * FROM pieces
                                WHERE piecetype=?
                                AND piecename=?;""",
            (piecetype, piecename),
        ).fetchall()
    )


def most_recent_vmod_in_path(vmod_path):
    """Finds the .vmod in the given path with the highest version number.

    If it's a dir, it's just the first in an inverted sort of *.vmod;
    if a file, it's just that file."""

    latest_local_vmod_path = pathlib.Path(vmod_path).absolute()
    if latest_local_vmod_path.is_dir():
        P = latest_local_vmod_path.glob("*.vmod")
        all_local_vmods = [mod for mod in P]
        latest_local_vmod_path = sorted(all_local_vmods)[-1]

    if not latest_local_vmod_path.exists():
        raise FileNotFoundError(
            "Module file does not exist: " + str(latest_local_vmod_path)
        )

    return latest_local_vmod_path


def update_piece(conn, piecetype, piecename, content):
    """updates the content of an existing entry, or creates a new one."""

    catchall = associated_token(piecename, piecetype, content)

    if not exists_piece(conn, piecetype, piecename):
        print("[+] {} - {} does not exist, creating it...".format(piecetype, piecename))
        conn.execute(
            """INSERT INTO pieces VALUES (?,?,?,?)""",
            (piecetype, piecename, content, catchall),
        )

    else:
        print("[^] {} - {} exists, updating it...".format(piecetype, piecename))
        conn.execute(
            """UPDATE pieces
                        SET content=? ,
                            catchall=?
                        WHERE piecename=?
                        AND piecetype=?""",
            (content, catchall, piecename, piecetype),
        )

    conn.commit()


def scrub_piecename(piecename):
    piecename = (
        piecename.replace("\\/", "")
        .split(";")[-1]
        .replace("/", "")
        .replace(" ", "")
        .replace(":", "")
        .replace("!", "")
        .replace("-", "")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )
    return piecename
