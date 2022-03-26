#!/usr/bin/env python3

import argparse
import flask
from flask import request, jsonify, send_file
import hashlib
import listbuilder
import logging
import logging.handlers
import os
import sqlite3
import time

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)

ROOT_PATH = "./"


guid_hash = hashlib.new("md5")
guid_hash.update(str(time.time()).encode())
guid = guid_hash.hexdigest()[0:16]

workingpath = os.path.join(ROOT_PATH, "working/")
outpath = os.path.join(ROOT_PATH, "out/")
vlbdirpath = os.path.join(ROOT_PATH, "vlb/")
vlbfilepath = os.path.join(vlbdirpath, guid + ".vlb")
vlogfilepath = os.path.join(outpath, guid + ".vlog")
databasepath = os.path.join(ROOT_PATH, "vlb_pieces.vlo")

conn = databasepath

app = flask.Flask(__name__)


@app.route("/api/v1/listbuilder/", methods=["POST"])
def home():

    out = "Sorry, looks like there was an error.\r\n"

    logging.info(request.args)
    logging.info(request.files)

    [(arg) for arg in request.args] 
    if "list" in request.args:
        out = "{}{}\r\n".format(out, str(request.args["list"]))
    if "help" in request.args:
        out = str(request.__dir__())
    if "gimme" in request.args:
        fleet_list_filestorage = request.files['upload_file']
        liststr = fleet_list_filestorage.read().decode()
            # liststr = list_file.readlines()
            # liststr = "boooooop"

        success, last_item = listbuilder.import_from_list(
            liststr, vlbfilepath, workingpath, conn
        )

        if success:
            listbuilder.export_to_vlog(vlogfilepath, vlbfilepath, workingpath)
            out = send_file(vlogfilepath)
        else:
            out = "BROKEN - {}".format(str(last_item))

    print(out)

    return out


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", help="debug moad", action="store_true")
    args = parser.parse_args()

    app.config["DEBUG"] = True

    app.run()
