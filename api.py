#!/usr/bin/env python3

import argparse
import base64
import flask
from flask import request, jsonify, send_file
import hashlib
import listbuilder
import logging
import logging.handlers
import os
import time

_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/api.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)

logging.info("API start...")

ROOT_PATH = os.path.dirname(__file__)


guid_hash = hashlib.new("md5")
guid_hash.update(str(time.time()).encode())
guid = guid_hash.hexdigest()[0:16]

listbuilder_config = listbuilder.get_default_config()
listbuilder_config.pwd = ROOT_PATH
listbuilder_config.working_dir = os.path.join(ROOT_PATH, "working/")
outpath = os.path.join(ROOT_PATH, "out/")
listbuilder_config.vlb_path = os.path.join(
    listbuilder_config.pwd, "vlb/", f"{guid}.vlb"
)
listbuilder_config.vlog_path = os.path.join(outpath, guid + ".vlog")
listbuilder_config.db_path = os.path.join(ROOT_PATH, "vlb_pieces.vlo")


app = flask.Flask(__name__)


@app.route("/api/vassal/list", methods=["POST"])
def home():

    utc_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    logging.info(
        f"[{utc_now}] API call: {request.method} {request.path} from {request.remote_addr}"
    )

    out = "Failed\n"

    logging.info(request.args)
    logging.info(request.form)

    if "help" in request.args:
        out = str("Under Construction.\n")
    else:
        # Expecting a form field called 'fleet_b64' with a base64-encoded Vassal fleet list.
        if "fleet_b64" not in request.form:
            logging.error("Missing 'fleet_b64' field in form data.")
            return out
        try:
            liststr = base64.b64decode(request.form["fleet_b64"]).decode()
        except Exception as e:
            logging.error(f"Error decoding 'fleet_b64': {str(e)}")
            return out

        listbuilder_config.fleet = liststr
        success, last_item = listbuilder.import_from_list(listbuilder_config)

        if success:
            listbuilder.export_to_vlog(listbuilder_config)
            out = send_file(listbuilder_config.vlog_path, as_attachment=True)

    print(out)
    return out


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", help="debug moad", action="store_true")
    args = parser.parse_args()

    if args.d:
        app.config["DEBUG"] = True
    else:
        app.config["DEBUG"] = False

    app.run(host="0.0.0.0")
