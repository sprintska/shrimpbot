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

    def __preprocess_build_xml(self):
        """Wrote this specifically to unfuck the fucked up Leading Shots entry under
        <VASSAL.build.module.PrototypeDefinition name="Upgrade Ion Cannon"> in the
        buildfile (zipped inside the Armada module .vmod).
        Feeling mad.  Might delete later idk."""

        try:
            before_everything_and_after = (
                self.build_xml.split(
                    "+\\/null\\/prototype\\;Upgrade card prototype\\\\\\\\\\"
                )[0],
                self.build_xml.split("null\\;99\\;87\\;9511")[1],
            )
            in_between = "VASSAL.build.module.PieceWindow:Game pieces\\/VASSAL.build.widget.TabWidget\\/VASSAL.build.widget.TabWidget:Upgrades\\/VASSAL.build.widget.ListWidget:Ion Cannon\\/VASSAL.build.widget.PieceSlot:Leading Shots"
            self.build_xml = "".join(
                [
                    before_everything_and_after[0],
                    in_between,
                    before_everything_and_after[1],
                ]
            )

            return True

        except Exception as err:

            return err

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

        with zipped_vmod.open("buildFile") as build_xml_raw:

            self.build_xml = build_xml_raw.read()

        _ = self.__preprocess_build_xml()
        self.build_xml = ET.fromstring(self.build_xml)


class ModuleElement:

    """Prototype for the different element types."""

    def __init__(self, element_obj):

        self.object_type = element_obj.tag
        self.vassal_data_raw = element_obj.text
        self.attributes = element_obj.attrib


class PrototypeDefinition(ModuleElement):

    """VASSAL.build.module.PrototypeDefinition."""

    def __init__(self, element_obj):

        super(PrototypeDefinition, self).__init__(element_obj)
        self.name = self.attributes["name"]

        self.segments = re.split(r"(?<!\\)\/", self.vassal_data_raw)


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

    prototype_definitions = {}

    for element_x in armada_module.build_xml.iter(
        "VASSAL.build.module.PrototypeDefinition"
    ):
        o = PrototypeDefinition(element_x)
        prototype_definitions[o.name] = o

    print(prototype_definitions["Imperial Ships"].vassal_data)

    # prototypes = {}
    # for prototype_definition in armada_module.build_xml.iter(
    #     "VASSAL.build.module.PrototypeDefinition"
    # ):
    #     prototypes[prototype_definition.attrib["name"]] = prototype_definition.text

    # print(prototypes["Ship card prototype"])
