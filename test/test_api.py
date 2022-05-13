#!/usr/bin/env python3

import requests

url_stem = 'http://yoda.advancedtransponder.net:5000/'
path = 'api/v1/listbuilder/?gimme=yes'
url = url_stem + path

args = {'gimme': 'yes'}

# print(args)

list_path = './testlists/kingston_test_imp.txt'

with open(list_path, 'rb') as list_file_obj:
    files = {'upload_file': list_file_obj}
    print("Sending request to {}...".format(url))
    r = requests.post(url, files=files, data=args)
    print("Response:")

print(r)
[print(x) for x in r]

test_out_path = "./test.vlog"
with open(test_out_path, 'wb') as out_path:
    out_path.write(r.content)
