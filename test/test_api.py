#!/usr/bin/env python3

import requests

url_stem = 'http://127.0.0.1:5000/'
path = 'api/v1/test/?gimme=yes'
url = url_stem + path

args = {'gimme': 'fule'}

# print(args)

list_path = './testlists/kingston_test_imp.txt'

with open(list_path, 'rb') as list_file_obj:
    files = {'upload_file': list_file_obj}
    r = requests.post(url, files=files, data=args)

print(r.content)
exit()


x = requests.post(url, data = myobj)