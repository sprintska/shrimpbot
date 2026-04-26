import logging

logger = logging.getLogger("updater")

import hashlib
from html import unescape
import json
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
    vassal_url="https://vassalengine.org/library/projects/Star_Wars_Armada",
):
    if not latest_local_vmod_path.exists():
        raise FileNotFoundError(
            "Module file does not exist: " + str(latest_local_vmod_path)
        )

    local_vmod_dir = latest_local_vmod_path.parent

    r = requests.get(vassal_url)
    r.raise_for_status()

    meta_match = re.search(r'id="project-data" content="(.*?)"', r.text)
    if not meta_match:
        raise RuntimeError("Could not find project-data on VASSAL library page")

    data = json.loads(unescape(meta_match.group(1)))

    # First release in the Module package is always the latest
    releases = data["packages"][0]["releases"]
    latest_files = releases[0]["files"]
    latest_file = next(f for f in latest_files if f["filename"].endswith(".vmod"))

    latest_vmod_filename = latest_file["filename"]
    latest_vmod_url = latest_file["url"]
    expected_sha256 = latest_file.get("sha256")

    if latest_vmod_filename == latest_local_vmod_path.name:
        logger.info(f"[*] Already up to date: {latest_vmod_filename}")
        return False

    logger.info(f"[+] New VMOD version found: {latest_vmod_filename}")
    logger.info(f"[+] Downloading from {latest_vmod_url}...")

    new_vmod_path = pathlib.Path(local_vmod_dir / latest_vmod_filename)
    sha256 = hashlib.sha256()
    with requests.get(latest_vmod_url, stream=True) as r:
        r.raise_for_status()
        with open(new_vmod_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                sha256.update(chunk)

    if expected_sha256 and sha256.hexdigest() != expected_sha256:
        new_vmod_path.unlink()
        raise RuntimeError(
            f"SHA256 mismatch for {latest_vmod_filename}: "
            f"expected {expected_sha256}, got {sha256.hexdigest()}"
        )

    logger.info(f"[+] Written and verified: {new_vmod_path}")
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
        logger.debug(f"[*] CREATING - {piecetype:<14} - {piecename:<40}")
        conn.execute(
            """INSERT INTO pieces VALUES (?,?,?,?)""",
            (piecetype, piecename, content, catchall),
        )
        logger.info(f" [+] CREATED  - {piecetype:<14} - {piecename:<40}")

    else:
        logger.debug(f"[*] UPDATING - {piecetype:<14} - {piecename:<40}")
        conn.execute(
            """UPDATE pieces
                        SET content=? ,
                            catchall=?
                        WHERE piecename=?
                        AND piecetype=?""",
            (content, catchall, piecename, piecetype),
        )
        logger.info(f" [^] UPDATED  - {piecetype:<14} - {piecename:<40}")

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
