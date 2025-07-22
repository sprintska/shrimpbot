import random
import shutil
import zipfile


def unzipall(zip_file_path, tar_path):
    """Unzips all of the files in the zip file at zip_file_path and
    dumps all those files into directory tar_path.

    I'm pretty sure this duplicates a built-in function, but, I mean...
    it works."""

    zip_ref = zipfile.ZipFile(zip_file_path, "r")
    zip_ref.extractall(tar_path)
    zip_ref.close()


def zipall(src_dir, dest_zip):
    """Creates a new zip file at zip_file_path and populates it with
    the zipped contents of tar_path.

    I'm pretty sure this duplicates a built-in function, but, I mean...
    it works."""

    archive_path = shutil.make_archive(dest_zip, "zip", src_dir)
    shutil.move(archive_path, dest_zip)


def scrub_piecename(piecename):
    """Scrubs a piece name of most characters that are not alphanumeric; specifically,
    those that have substantial meaning in SQL queries.  These piecenames are about
    to be inserted into a SQL query, so we're looking to avoid SQL injection
    vulnerabilities, as well as just generally wanting clean piecenames."""

    piecename = piecename.replace("\\/", "").split("/")[0].split(";")[-1]

    scrub_these = " :!-'(),\"+.\t\r\n·[]" + "\u2022"
    for char in scrub_these:
        piecename = piecename.replace(char, "")

    return piecename.lower()


def calc_guid():
    return str(round(random.random() * 10**13))
