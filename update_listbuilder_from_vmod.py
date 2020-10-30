#!/usr/bin/env python3

import argparse
import os
import re
import zipfile

import xml.etree.ElementTree as ET


def parse_vmod(vmod_path):
    '''Unzip the vmod and return an object with things like Vassal
    version, module version, and buildFile contents.
    '''

    metadata_out = {}
    build_file_out = ""

    zip_in_memory = zipfile.ZipFile(vmod_path)
    
    with zip_in_memory.open("moduledata") as module_metadata_raw:
        module_metadata_root = ET.fromstring(module_metadata_raw.read())
        
    metadata_out['module_version'] = module_metadata_root.find('version').text
    metadata_out['vassal_version'] = module_metadata_root.find('VassalVersion').text
    metadata_out['description'] = module_metadata_root.find('description').text

    with zip_in_memory.open("buildFile") as build_file_raw:
        build_file_out = build_file_raw.read()

    return(metadata_out,build_file_out)


def preprocess_build_file(build_file):
    '''Wrote this specifically to unfuck the fucked up Leading Shots entry under
       <VASSAL.build.module.PrototypeDefinition name="Upgrade Ion Cannon"> in the
       buildfile (zipped inside the Armada module .vmod).  
       Feeling mad.  Might delete later idk.'''

    try:
        before_everything_and_after = build_file.split("+\\/null\\/prototype\\;Upgrade card prototype\\\\\\\\\\")[0], build_file.split("null\\;99\\;87\\;9511")[1]
        in_between = "VASSAL.build.module.PieceWindow:Game pieces\\/VASSAL.build.widget.TabWidget\\/VASSAL.build.widget.TabWidget:Upgrades\\/VASSAL.build.widget.ListWidget:Ion Cannon\\/VASSAL.build.widget.PieceSlot:Leading Shots"
        return "".join([before_everything_and_after[0],in_between,before_everything_and_after[1]])
    except:
        return build_file


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-db", 
        help="VLO DB to reference for pieces", 
        type=str, 
        default="vlb_pieces.vlo"
        )
    parser.add_argument(
        "-m",
        help="path to module (.VMOD) to source new piece definitions from",
        type=str,
        default="working"
        )
    args = parser.parse_args()

    vmod_path = os.path.abspath(args.m)
    database_path = os.path.abspath(args.db)
    
    module_metadata, build_file = parse_vmod(vmod_path)
    build_file = preprocess_build_file(build_file)