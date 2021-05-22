#!/usr/bin/env python3

import argparse
import flask
from flask import request, jsonify
import hashlib
import listbuilder
import os
import sqlite3
import time


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


@app.route("/api/v1/test/", methods=["POST"])
def home():

    out = "bananas\r\n"
    [print(arg) for arg in request.args] 
    if "list" in request.args:
        out = "{}{}\r\n".format(out, str(request.args["list"]))
    if "help" in request.args:
        out = str(request.__dir__())
    if "gimme" in request.args:
        print("gimme was in there")
        fleet_list_filestorage = request.files['upload_file']
        liststr = fleet_list_filestorage.read().decode()
            # liststr = list_file.readlines()
            # liststr = "boooooop"

        print("===========================================================================")
        print(liststr)
        print("---------------------------------------------------------------------------")

        success, last_item = listbuilder.import_from_list(
            liststr, vlbfilepath, workingpath, conn
        )

        if success:
            listbuilder.export_to_vlog(vlogfilepath, vlbfilepath, workingpath)
            out = vlogfilepath
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
