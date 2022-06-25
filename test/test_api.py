#!/usr/bin/env python3

import pathlib
import requests

url_stem = "http://yoda.advancedtransponder.net:5000/"
# url_stem = "http://0.0.0.0:5000/"
path = "api/v1/listbuilder/?gimme=yes"
url = url_stem + path

args = {"gimme": "yes"}

# print(args)


def get_list(list_path, url, args):

    with open(list_path, "rb") as list_file_obj:
        files = {"upload_file": list_file_obj}
        print("Sending request to {}...".format(url))
        r = requests.post(url, files=files, data=args)
        print("Response:")

    # print(r)
    # [print(x) for x in r]

    test_out_dir = list_path.parent.parent / "test_vlogs"
    test_out_filename = ".".join(list_path.name.split(".")[0:-1]) + ".vlog"
    test_out_path = test_out_dir / test_out_filename
    with open(test_out_path, "wb+") as out_path:
        out_path.write(r.content)


P = pathlib.Path("./testlists")
for x in P.iterdir():
    get_list(x, url, args)
