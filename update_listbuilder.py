#!/usr/bin/env python3

import argparse
import datetime
import difflib
import logging
import logging.handlers
import os
import pathlib
import random
import re
import requests
import sqlite3
import zipfile
import xml.etree.ElementTree as ET


""" To check daily for updates:

"""


_handler = logging.handlers.WatchedFileHandler("/var/log/shrimpbot/shrimp.log")
logging.basicConfig(handlers=[_handler], level=logging.INFO)


class VassalModule:
    """Contains all the elements of the module as defined in the VMOD."""

    def __init__(self, vmod_path):

        self.vmod_path = vmod_path

        _ = self.__get_vmod_metadata()
        _ = self.__get_build_xml()

        self.prototypes = {}
        self.pieces = {}
        self.xml_parent_map = {
            child: parent for parent in self.build_xml.iter() for child in parent
        }
        self.piece_type_signatures = {
            "prototype;Objective card prototype": "objective",
            "Actual Obstacle": "obstacle",
            "prototype;Basic Ship": "ship",
            "prototype;Huge Ship": "ship",
            "prototype;Ship card prototype": "shipcard",
            "prototype;Fighter Prototype": "squadron",
            "prototype;Squadron Card prototype": "squadroncard",
            "prototype;Upgrade card prototype": "upgradecard",
            "prototype;Nonrecurring upgrade card prototype": "upgradecard",
        }

        print("parsing prototypes")
        _ = self.__parse_prototypes()
        print("parsing pieces")
        _ = self.__parse_pieces()

    def __preprocess_build_xml(self):
        """Wrote this specifically to unfuck the fucked up Leading Shots entry under
        <VASSAL.build.module.PrototypeDefinition name="Upgrade Ion Cannon"> in the
        buildfile (zipped inside the Armada module .vmod). Later found that the
        second section was needed for Ketsu Onyo and Morna Kee; would be needed for
        a few others too if they were things I needed. Update: yup, I need em. Fk."""

        try:
            before_everything_and_after = (
                self.build_xml_raw.split(
                    "+\\/null\\/prototype\\;Upgrade card prototype\\\\\\\\\\"
                )[0],
                self.build_xml_raw.split("null\\;99\\;87\\;9511")[1],
            )
            in_between = "VASSAL.build.module.PieceWindow:Game pieces\\/VASSAL.build.widget.TabWidget\\/VASSAL.build.widget.TabWidget:Upgrades\\/VASSAL.build.widget.ListWidget:Ion Cannon\\/VASSAL.build.widget.PieceSlot:Leading Shots"
            self.build_xml_raw = "".join(
                [
                    before_everything_and_after[0],
                    in_between,
                    before_everything_and_after[1],
                ]
            )

        except Exception as err:

            return err

    def __get_vmod_metadata(self):
        """Unzip the vmod and parse out the module's metadata."""

        self.metadata = {}
        print(self.vmod_path)
        zipped_vmod = zipfile.ZipFile(self.vmod_path)

        with zipped_vmod.open("moduledata") as module_metadata_raw:
            module_metadata_root = ET.fromstring(module_metadata_raw.read())

        self.metadata["vmod_schema_version"] = module_metadata_root.attrib["version"]
        if self.metadata["vmod_schema_version"] != "1":
            raise Exception(
                "Unsupported Vassal Module version {} found at {} in moduleData.".format(
                    self.metadata["vmod_schema_version"], self.vmod_path
                )
            )

        self.metadata["module_version"] = module_metadata_root.find("version").text
        self.metadata["vassal_version"] = module_metadata_root.find(
            "VassalVersion"
        ).text
        self.metadata["description"] = module_metadata_root.find("description").text
        self.metadata["name"] = module_metadata_root.find("name").text

        unix_timestamp = int(int(module_metadata_root.find("dateSaved").text) / 1000)
        self.metadata["date_saved"] = datetime.datetime.fromtimestamp(unix_timestamp)

    def __get_build_xml(self):
        """Unzip the vmod and parse out the buildFile contents."""

        zipped_vmod = zipfile.ZipFile(self.vmod_path)

        with zipped_vmod.open("buildFile.xml") as build_xml_file:
            self.build_xml_raw = str(build_xml_file.read(), "utf-8")

        self.build_xml = ET.fromstring(self.build_xml_raw)

    def __resolve_embedded_references(self, element):
        """Regexes out all the weird mangled pieces sorta-embedded into the traits
        of other pieces, fuzzy-matches them to another piece, and 're-references'
        the piece."""

        if "dice" in element.name.lower():
            print(f"\n\t [!] Not adding | {element.name}")
            return False

        error_regex = re.compile(r"(?<!^)(\+.*?)(\{.*?\}.*?|[^\{\}])(?<!\\);")
        error_matches = error_regex.finditer(element.vassal_data_raw)
        ex = False

        for error_match in error_matches:
            print(f"\n\t [*] Amending embedded reference in | {element.name}")
            full_error_match = error_match.group(0)
            full_error_match = full_error_match.replace("\\;", ";").replace("\\/", "/")
            full_error_match = re.sub(r"\\+\t", "\t", full_error_match)
            full_error_match = full_error_match.split("\t")
            full_error_match = "\t".join(
                [(x + "\\" * xloc) for xloc, x in enumerate(full_error_match)]
            )

            try:
                fuzzy_matched_xml = [
                    x
                    for x in difflib.get_close_matches(
                        full_error_match,
                        [ele.text for ele in self.build_xml.iter() if ele.text],
                        cutoff=0.7,
                    )
                ]

                print("full_error_match:", repr(full_error_match))
                all_texts = [ele.text for ele in self.build_xml.iter() if ele.text]
                print("Sample of all_texts:", all_texts[:10])
                print("Total texts:", len(all_texts))

                matching_xml_element = [
                    ele
                    for ele in self.build_xml.iter()
                    if ele.text == fuzzy_matched_xml[0]
                ][0]
            except Exception as err:
                raise err

            target_absolute_reference = (
                f"{self.__get_parent_path(matching_xml_element)};"
            )
            element.vassal_data_raw = element.vassal_data_raw.replace(
                error_match.group(0), target_absolute_reference, 1
            )
            ex = True

        if ex:

            element.clear_traits()
            element.parse()
            element._parse_traits()

        return element

    def __get_parent_path(self, xml_element):
        """Returns the absolute XML path of xml_element, in the format VASSAL likes."""

        try:
            out = xml_element.tag
            for x in ["name", "entryName"]:
                if x in xml_element.attrib.keys():
                    name = xml_element.attrib[x]
                    name = name.replace("/", "\\\\/")
                    out = f"{out}:{name}"
                    break
            parent = self.__get_parent_path(self.xml_parent_map[xml_element])
            if parent:
                out = f"{parent}\\/{out}"
            return out
        except KeyError as err:
            return ""
        except Exception as err:
            raise err

    def __parse_prototypes(self):
        """Retrieves all the prototypes and populates them to the Module."""

        for element_x in self.build_xml.iter("VASSAL.build.module.PrototypeDefinition"):
            try:
                self.add_element(PrototypeDefinition(element_x))
            except RuntimeError as err:
                [print(arg) for arg in err.args]

    def __parse_pieces(self):
        """Retrieves all the pieces and populates them to the Module"""

        for element_x in self.build_xml.iter("VASSAL.build.widget.PieceSlot"):
            try:
                self.add_element(PieceDefinition(element_x))
            except RuntimeError as err:
                [print(arg) for arg in err.args]

        for piece in self.pieces:

            for signature in self.piece_type_signatures:
                if signature in self.pieces[piece].traits_raw:
                    self.pieces[piece].piece_type = self.piece_type_signatures[
                        signature
                    ]

            dereferenced_traits = [
                trait for trait in self.dereference(self.pieces[piece], top_level=True)
            ]
            self.pieces[piece].traits = dereferenced_traits

    def add_element(self, module_element):
        """Add element to the right list."""

        print(f"\n\t [*] Adding element | {module_element.name}")

        module_element = self.__resolve_embedded_references(module_element)

        if not module_element:
            return False

        if "/" in module_element.name:
            print(module_element.name)
        if isinstance(module_element, PrototypeDefinition):
            self.prototypes[module_element.name] = module_element
        elif (
            isinstance(module_element, PieceDefinition)
            and module_element.name in self.pieces
            and "------------" not in module_element.name
        ):
            piece_name = (
                str(module_element.name)
                + "__"
                + str(int(random.random() * 10000))
                + "__"
            )
            self.pieces[piece_name] = module_element
            print("[!] Duplicate: {}".format(str(module_element.name)))
        elif isinstance(module_element, PieceDefinition):
            self.pieces[module_element.name] = module_element
        else:
            print(str(type(module_element)))

    def dereference(self, referring_element, top_level=False):
        """Lookup the references to prototypes and replaces the
        reference with the text of the prototype."""

        for trait in referring_element.traits:
            if trait[0].trait_type == "prototype":
                prototype_name = trait[0].trait_text.split(";")[1].replace("\\", "")
                for dereferenced_trait in self.dereference(
                    self.prototypes[prototype_name]
                ):
                    yield dereferenced_trait
            elif trait[0].trait_type != "piece":
                yield trait
            elif trait[0].trait_type == "piece" and top_level:
                yield trait


class ModuleElement:
    """Prototype for the different element types."""

    def __init__(self, element_obj):

        self.object_type = element_obj.tag
        self.vassal_data_raw = element_obj.text
        self.attributes = element_obj.attrib

    def _parse_traits(self):

        self.traits = []

        escaped_text_regex = re.compile(r"(?<!>)\+.*?(\{.*?\}.*?|[^\{\}])(?<!\\);")
        escaped_text_instances = [
            match_instance.group()
            for match_instance in escaped_text_regex.finditer(self.traits_raw)
        ]
        traits_raw_interim = escaped_text_regex.sub(
            "___SUB_ESCAPED_BACK_IN___", self.traits_raw
        )
        traits_raw_interim = traits_raw_interim.replace("\t", "___SPLIT_ON_ME___")
        for escaped_text_instance in escaped_text_instances:
            traits_raw_interim = traits_raw_interim.replace(
                "___SUB_ESCAPED_BACK_IN___", escaped_text_instance, 1
            )
        traits = traits_raw_interim.split("___SPLIT_ON_ME___")

        states = self.states_raw.split("\t")

        self.piece_type = "other"

        if len(traits) == len(states):
            for tloc, trait in enumerate(traits):
                self.traits.append((Trait(trait), State(states[tloc])))
                self.traits[tloc][0].associate_state(self.traits[tloc][1])
        else:
            raise RuntimeError(
                "[!] Failed to import {} - {} traits vs {} states".format(
                    self.name, len(traits), len(states)
                )
            )

    def clear_traits(self):

        self.traits = []
        self.states = []


class PrototypeDefinition(ModuleElement):
    """VASSAL.build.module.PrototypeDefinition."""

    def __init__(self, element_obj):

        super(PrototypeDefinition, self).__init__(element_obj)
        self.parse()

    def parse(self):

        self.name = self.attributes["name"]
        self.segments = re.split(
            r"(?<!\\)\/", self.vassal_data_raw
        )  # unescaped forwardslash (/ not preceded by \)
        if not len(self.segments) == 4:
            exception_detail = "Malformed VASSAL.build.module.PrototypeDefinition in module: {} does not have 4 segments.".format(
                self.name
            )
            raise RuntimeError(exception_detail).with_traceback()
        (
            self.start_of_record,
            self.instance_id,
            self.traits_raw,
            self.states_raw,
        ) = self.segments

        self._parse_traits()


class PieceDefinition(ModuleElement):
    """VASSAL.build.widget.PieceSlot"""

    def __init__(self, element_obj):

        super(PieceDefinition, self).__init__(element_obj)
        self.parse()

    def parse(self):

        self.name = self.attributes["entryName"]
        self.dimensions = (self.attributes["height"], self.attributes["width"])
        self.gpid = self.attributes["gpid"]
        self.segments = re.split(
            r"(?<!\\)\/", self.vassal_data_raw
        )  # unescaped forwardslash (/ not preceded by \)
        if not len(self.segments) == 4:
            exception_detail = "Malformed VASSAL.build.widget.PieceSlot in module: {} does not have 4 segments.".format(
                self.name
            )
            raise RuntimeError(exception_detail).with_traceback()
        (
            self.start_of_record,
            self.instance_id,
            self.traits_raw,
            self.states_raw,
        ) = self.segments

        self._parse_traits()

    def compile_vlb_entry(self):

        output = "LOG\t+/vlb_GUID/"
        for tloc, trait in enumerate(self.traits):
            output += "{}{}\t".format(trait[0].trait_text.strip(), "\\" * tloc)
        output = output.rstrip("\\\t") + "/"
        for tloc, trait in enumerate(self.traits):
            output += "{}{}\t".format(trait[1].state_text.strip(), "\\" * tloc)
        output = output.rstrip("\\\t") + "\\"
        output = re.sub(
            r"\tnull;\d{1,4};\d{1,4};",
            "\tTable;vlb_x_axis;vlb_y_axis;",
            output,
        )
        return output


class Trait:
    """A trait--a member of the third segment of a Vassal piece or prototype definition.
    A trait belongs to an object of the ModuleElement class (or a subclass like
    PrototypeDefinition or Piece), and has a 1:1 relationship to a State object which
    also belongs to that ModuleElement."""

    def __init__(self, trait_text):

        self.trait_text = trait_text.rstrip("\\")
        self.trait_type = re.split(r"(?<!\\);", trait_text)[0]

    def associate_state(self, state):

        self.state = state
        self.state.trait = self

    def __str__(self):

        return self.trait_text


class State:
    """A state--a member of the fourth segment of a Vassal piece or prototype definition.
    A state belongs to an object of the ModuleElement class (or a subclass like
    PrototypeDefinition or Piece), and and has a 1:1 relationship to a Trait object which
    also belongs to that ModuleElement."""

    def __init__(self, state_text):

        self.state_text = state_text.rstrip("\\")

    def associate_trait(self, trait):

        self.trait = trait
        self.trait.state = self


def create_db(db_path):
    """Create the db at the path if it doesn't exist"""

    if not os.path.exists(db_path):
        open(db_path, "w")

        conn = sqlite3.connect(db_path)

        conn.execute(
            "CREATE TABLE pieces (piecetype text, piecename text, content text, catchall text)"
        )
        conn.commit()
        conn.close()


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


def update_piece(conn, piecetype, piecename, content):
    """updates the content of an existing entry, or creates a new one."""

    catchall = associated_token(piecename, piecetype, content)

    if not exists_piece(conn, piecetype, piecename):
        print("[+] {} - {} does not exist, creating it...".format(piecetype, piecename))
        conn.execute(
            """INSERT INTO pieces VALUES (?,?,?,?)""",
            (piecetype, piecename, content, catchall),
        )
        conn.commit()

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
    # print("\nPiecename in: {}".format(piecename))
    piecename = (
        piecename.replace("\/", "")
        # .split("/")[0]
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
    # print("Piecename out: {}".format(piecename))
    return piecename


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


def most_recent_vmod_in_path(vmod_path):
    """Finds the latest .vmod in the given path.

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
    open(new_vmod_path, "wb").write(r.content)

    return new_vmod_path


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-db", help="Path to VLO DB to update", type=str, default="vlb_pieces.vlo"
    )
    parser.add_argument(
        "-m",
        help="path to module (.VMOD) to source new piece definitions from",
        type=str,
        default="./vmods/",
    )
    parser.add_argument(
        "--auto",
        help="Check automatically for a new version.  References the top version posted on https://vassalengine.org/wiki/Module:Star_Wars:_Armada.",
        action="store_true",
    )
    args = parser.parse_args()

    vmod_path = most_recent_vmod_in_path(args.m)
    database_path = os.path.abspath(args.db)

    if args.auto:
        vmod_path = check_for_new_version(vmod_path)
        if not vmod_path:
            exit(
                "Auto-update found no new module version available.\n\n To manually update, use: \n\n\tupdate_listbuilder.py -m ./path/to/new_version.vmod"
            )

    armada_module = VassalModule(vmod_path)

    create_db(database_path)
    conn = sqlite3.connect(database_path)

    for piece in armada_module.pieces:

        vlb_entry = armada_module.pieces[piece].compile_vlb_entry()

        update_piece(
            conn,
            armada_module.pieces[piece].piece_type,
            scrub_piecename(armada_module.pieces[piece].name),
            vlb_entry,
        )
