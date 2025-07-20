#!/usr/bin/python3

import json
import logging
import logging.handlers
import os
import pathlib
import requests
import shutil


_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


def autoPopulateImage(subject):

    pageTitle = findPage(subject)
    if pageTitle:
        img_title = getBestMatchImageTitle(pageTitle)
        if img_title:
            img_url = getImageUrl(img_title)
            if img_url:
                return img_url

    return False


def findPage(page_name):
    """Search by page name.  Return page title of the top result."""

    payload = {
        "action": "query",
        "list": "search",
        "srsearch": page_name,
        "format": "json",
    }
    urlString = "https://starwars-armada.fandom.com/api.php"

    try:
        with requests.get(urlString, params=payload) as r:
            data = r.json()
        logging.info("Top wiki hit: {}".format(data["query"]["search"][0]["title"]))
        return data["query"]["search"][0]["title"]
    except IndexError:
        return False


def getBestMatchImageTitle(pageTitle):
    """Return the main image from the page of the given title."""

    logging.info("Searching for a good match in {}...".format(pageTitle))

    payload = {
        "action": "query",
        "titles": pageTitle,
        "format": "json",
        "prop": "images",
    }
    urlString = "https://starwars-armada.fandom.com/api.php"

    try:
        with requests.get(urlString, params=payload) as r:
            data = r.json()

        for _, val in data["query"]["pages"].items():
            [logging.info(v) for v in val]
            for img in val["images"]:
                imgfile = img["title"]
                if imgfile.endswith(".png"):
                    print("Testing | {}".format(imgfile))
                    bar = len(pageTitle.split()) * 0.5
                    matches = 0
                    for word in pageTitle.split():
                        if word.lower() in imgfile.lower():
                            matches += 1
                    if matches >= bar:
                        print("[+]")
                        return imgfile
                    print("[-]")
    except Exception as err:
        logging.error("{} - {} - {}".format(type(err), err.args, err))

    return False


def getImageUrl(img_title):

    payload = {
        "action": "query",
        "titles": img_title,
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
    }
    urlString = "https://starwars-armada.fandom.com/api.php"

    try:
        with requests.get(urlString, params=payload) as r:
            data = r.json()

    except:
        raise

    for _, val in data["query"]["pages"].items():
        for entry in val["imageinfo"]:
            return entry["url"].split("/revision/")[0]


def addCardToReference(img_src_path, img_dest_path, card_name, reference_table_path):

    src = pathlib.Path(img_src_path).resolve()
    dst = pathlib.Path(img_dest_path).resolve()
    table = pathlib.Path(reference_table_path).resolve()

    img_filename = "_" + src.name
    dst = dst / img_filename

    shutil.copy(src, dst)
    os.remove(src)

    table_entry = "\n{};{}".format(img_filename, card_name)

    with open(table, "a") as t:
        t.write(table_entry)


if __name__ == "__main__":

    autoPopulateImage("hondo ohnaka officer")
