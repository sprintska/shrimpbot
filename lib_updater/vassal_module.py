import logging

logger = logging.getLogger("parser")

import datetime
import difflib
import random
import re
import xml.etree.ElementTree as ET
import zipfile


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

        logger.info("parsing prototypes")
        _ = self.__parse_prototypes()
        logger.info("parsing pieces")
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
        logger.info(f"parsing Vassal Module at {self.vmod_path}")
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
            logger.info(f"\t [!] NOT ADDING       | {element.name}")
            return False

        error_regex = re.compile(r"(?<!^)(\+.*?)(\{.*?\}.*?|[^\{\}])(?<!\\);")
        error_matches = error_regex.finditer(element.vassal_data_raw)
        made_changes = False

        for error_match in error_matches:

            logger.info(f"\t [*] Amending embedded reference in | {element.name}")
            logger.debug(f"\t [.] Mangled reference: \n\t\t{error_match.group(0)}")
            full_error_match = error_match.group(0)
            full_error_match = full_error_match.replace("\\;", ";").replace("\\/", "/")
            full_error_match = re.sub(r"\\+\t", "\t", full_error_match)
            full_error_match = full_error_match.split("\t")
            full_error_match = "\t".join(
                [(x + "\\" * xloc) for xloc, x in enumerate(full_error_match)]
            )

            fuzzy_matched_xml = difflib.get_close_matches(
                full_error_match,
                [ele.text for ele in self.build_xml.iter() if ele.text],
                cutoff=0.65,
            )

            try:
                matching_xml_elements = [
                    ele
                    for ele in self.build_xml.iter()
                    if ele.text == fuzzy_matched_xml[0]
                ]
            except IndexError as err:
                # fmt: off
                logger.info("[!] Don't ignore this error: lists won't load properly if these aren't dealt with.")
                logger.info(" .  This regex finds embedded references--these MUST be rereferenced or both the containing")
                logger.info(" .  and improperly referenced pieces will not load properly.")
                logger.info(f" .  I have fixed this before by tuning 'cutoff' down in fuzzy_matched_xml.")
                raise err
                # fmt: on

            if len(matching_xml_elements) >= 1:
                target_absolute_reference = (
                    f"{self.__get_parent_path(matching_xml_elements[0])};"
                )
                element.vassal_data_raw = element.vassal_data_raw.replace(
                    error_match.group(0), target_absolute_reference, 1
                )
            made_changes = True

        if made_changes:

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
                logger.error(*err.args)

    def __parse_pieces(self):
        """Retrieves all the pieces and populates them to the Module"""

        for element_x in self.build_xml.iter("VASSAL.build.widget.PieceSlot"):
            try:
                self.add_element(PieceDefinition(element_x))
            except RuntimeError as err:
                logger.error(*err.args)

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

        module_element = self.__resolve_embedded_references(module_element)

        if not module_element:
            return False

        if "------------" in module_element.name:
            logger.info(f"\t [!] NOT ADDING       | {module_element.name}")
            return False
        elif isinstance(module_element, PrototypeDefinition):
            logger.info(f"\t [*] Adding prototype | {module_element.name}")
            self.prototypes[module_element.name] = module_element
        elif (
            isinstance(module_element, PieceDefinition)
            and module_element.name in self.pieces
        ):
            piece_name = (
                f"{str(module_element.name)}__{str(int(random.random() * 10000))}__"
            )
            self.pieces[piece_name] = module_element
            logger.info(f"\t [!] DUPLICATE        | {str(module_element.name)}")
        elif isinstance(module_element, PieceDefinition):
            self.pieces[module_element.name] = module_element
        else:
            logger.info(
                f"\t [-] {str(type(module_element))} is not a piece or prototype--skipping."
            )

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
