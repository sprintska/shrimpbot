#!/usr/bin/env python3

import argparse
import os
import re
import datetime
import zipfile
import xml.etree.ElementTree as ET


class VassalModule:

    """Contains all the elements of the module as defined in the VMOD."""

    def __init__(self, vmod_path):

        self.vmod_path = vmod_path

        _ = self.__get_vmod_metadata()
        _ = self.__get_build_xml()

        self.prototypes = {}
        self.pieces = {}

        _ = self.__parse_prototypes()
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

        # error_regex = re.compile(r"(?<!>)\+.*?emb2")
        error_regex = re.compile(r"(?<!>)\+.*?emb2.*?(?<!\\);")
        good_regex = re.compile(r"VASSAL.build.module.[\s\S]{1,}?(?=\\;)")

        error_count = len(error_regex.findall(self.build_xml_raw))

        if error_count:
            for error_item in range(error_count):

                try:

                    error_match = error_regex.search(self.build_xml_raw)
                    error_string = error_match[0]

                    good_match = good_regex.search(error_string)
                    good_string = good_match[0].replace("\\\\", "\\")

                    self.build_xml_raw = (
                        self.build_xml_raw[: error_match.start(0)]
                        + good_string
                        + self.build_xml_raw[error_match.end(0) - 1 :]
                    )

                    # print(self.build_xml_raw[error_match.start(0)-10:error_match.start(0)+len(good_string)+10])

                except TypeError as type_err:

                    if "object is not subscriptable" not in str(type_err.args[0]):
                        raise type_err

                    print("[+] No weird ass errors found in processing the buildFile.")

    def __get_vmod_metadata(self):
        """Unzip the vmod and parse out the module's metadata."""

        self.metadata = {}

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

        with zipped_vmod.open("buildFile") as build_xml_file:

            self.build_xml_raw = str(build_xml_file.read(), "utf-8")

        _ = self.__preprocess_build_xml()
        self.build_xml = ET.fromstring(self.build_xml_raw)

    def __parse_prototypes(self):
        """Retrieves all the prototypes and populates them to the Module."""
        prototype_definitions = {}

        for element_x in self.build_xml.iter("VASSAL.build.module.PrototypeDefinition"):
            try:
                self.add_element(PrototypeDefinition(element_x))
            except RuntimeError as err:
                [print(arg) for arg in err.args]

    def __parse_pieces(self):
        """Retrieves all the pieces and populates them to the Module"""
        piece_definitions = {}

        for element_x in self.build_xml.iter("VASSAL.build.widget.PieceSlot"):
            try:
                self.add_element(PieceDefinition(element_x))
            except RuntimeError as err:
                [print(arg) for arg in err.args]

        # [self.dereference(self.pieces[piece]) for piece in self.pieces]

        for piece in self.pieces:
            print("[+] Piece     | {}".format(piece))
            self.dereference(self.pieces[piece])
            # [print("    Trait     | {}\n    State     | {}".format(trait[0].trait_text,trait[0].state.state_text)) for trait in o.traits]
            # for trait in self.pieces[piece].traits:
            #     # if trait[0].trait_text.startswith("piece;;;;") and o.name not in trait[0].trait_text.replace("\\",""):
            #     print("       {}".format(trait[0].trait_text))

    def add_element(self, module_element):
        """Add element to the right list."""

        if isinstance(module_element, PrototypeDefinition):
            self.prototypes[module_element.name] = module_element
        elif isinstance(module_element, PieceDefinition):
            self.pieces[module_element.name] = module_element
        else:
            print(str(type(module_element)))

    def dereference(self, referring_element):
        """Lookup the references to prototypes and replaces the
        reference with the text of the prototype."""

        for trait in referring_element.traits:
            if trait[0].trait_text.startswith("prototype;"):
                prototype_name = trait[0].trait_text.split(";")[1].replace("\\","")
                print("    [-] {}\n    [|] {}".format(prototype_name,self.prototypes[prototype_name]))


class ModuleElement:

    """Prototype for the different element types."""

    def __init__(self, element_obj):

        self.object_type = element_obj.tag
        self.vassal_data_raw = element_obj.text
        self.attributes = element_obj.attrib

        # print("="*50+"\n"+self.vassal_data_raw)


class PrototypeDefinition(ModuleElement):

    """VASSAL.build.module.PrototypeDefinition."""

    def __init__(self, element_obj):

        super(PrototypeDefinition, self).__init__(element_obj)
        self.name = self.attributes["name"]
        self.segments = re.split(r"(?<!\\)\/", self.vassal_data_raw)
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

        # if "ship movement template" not in self.name:
        #     self.__parse_traits()
        self.__parse_traits()

    def __parse_traits(self):

        self.traits = []

        traits = self.traits_raw.split("\t")
        states = self.states_raw.split("\t")

        # print(self.name)

        if len(traits) == len(states):
            for tloc, trait in enumerate(traits):
                self.traits.append((Trait(trait), State(states[tloc])))
                self.traits[tloc][0].associate_state(self.traits[tloc][1])
        else:
            [print("|T|{}".format(trait)) for trait in traits]
            [print("|S|{}".format(state)) for state in states]
            exit()
            raise RuntimeError(
                "[!] Failed to import Prototype {} - {} traits vs {} states".format(
                    self.name, len(traits), len(states)
                )
            )


class PieceDefinition(ModuleElement):

    """VASSAL.build.widget.PieceSlot"""

    def __init__(self, element_obj):

        super(PieceDefinition, self).__init__(element_obj)
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

        self.__parse_traits()

    def __parse_traits(self):

        self.traits = []

        traits = self.traits_raw.split("\t")
        states = self.states_raw.split("\t")

        # print(self.name)

        if len(traits) == len(states):
            for tloc, trait in enumerate(traits):
                self.traits.append((Trait(trait), State(states[tloc])))
                self.traits[tloc][0].associate_state(self.traits[tloc][1])
        else:
            raise RuntimeError(
                "[!] Failed to import Piece {} - {} traits vs {} states".format(
                    self.name, len(traits), len(states)
                )
            )


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


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-db", help="VLO DB to reference for pieces", type=str, default="vlb_pieces.vlo"
    )
    parser.add_argument(
        "-m",
        help="path to module (.VMOD) to source new piece definitions from",
        type=str,
        default="working",
    )
    args = parser.parse_args()

    vmod_path = os.path.abspath(args.m)
    database_path = os.path.abspath(args.db)

    armada_module = VassalModule(vmod_path)
