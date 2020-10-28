#!/usr/bin/env python3

import re


def preprocess_build_file(build_file):
    '''Wrote this specifically to unfuck the fucked up Leading Shots entry under
       <VASSAL.build.module.PrototypeDefinition name="Upgrade Ion Cannon"> in the
       buildfile (zipped inside the Armada module .vmod).  
       Feeling mad.  Might delete later idk.'''

    before_everything_and_after = build_file.split("+\\/null\\/prototype\\;Upgrade card prototype\\\\\\\\\\")[0], build_file.split("null\\;99\\;87\\;9511")[1]
    in_between = "VASSAL.build.module.PieceWindow:Game pieces\\/VASSAL.build.widget.TabWidget\\/VASSAL.build.widget.TabWidget:Upgrades\\/VASSAL.build.widget.ListWidget:Ion Cannon\\/VASSAL.build.widget.PieceSlot:Leading Shots"
    return "".join([before_everything_and_after[0],in_between,before_everything_and_after[1]])


def populate_prototypes(unresolved_piece_data,build_file,depth=0):
    
    piece_null_pattern = re.compile(r"piece;;;;[\S\s]{0,}null;[0-9]{1,3};[0-9]{1,3};[0-9]{0,8}")
    piece_null_match = piece_null_pattern.search(unresolved_piece_data)

    if piece_null_match:
        unresolved_piece_data = "".join([
            unresolved_piece_data[:piece_null_match.start(0)],
            unresolved_piece_data[piece_null_match.end(0):]
        ])

    resolved_piece_data = unresolved_piece_data
    
    if "prototype;" in unresolved_piece_data:

        prototype_references_array = unresolved_piece_data.split("prototype;")

        for passdown_reference in prototype_references_array[1:]:
            unresolved_prototype_reference = passdown_reference.split("\t")[0].replace("\\/","/").rstrip("\\")
            resolved_prototype_reference = prototype_lookup(unresolved_prototype_reference,build_file)
            resolved_prototype_reference = populate_prototypes(resolved_prototype_reference,build_file,depth=depth+1)
            resolved_piece_data = resolved_piece_data.replace("prototype;{}".format(passdown_reference.split("\t")[0]),resolved_prototype_reference)

    return resolved_piece_data


def prototype_lookup(prototype_reference,build_file):
    '''do the actual lookup.
    in: "Ship card prototype"
    out: "prototype;Spawn Upgrade	mark;Layer\	clone;Clone;67,130\\	delete;Delete;68,130\\\	piece;;;;/	Card\	\\	\\\	null;0;0;"
        I haven't exhaustively verified where "out" should end here.
        Also, this "out" contains a lookup (prototype;Spawn Upgrade) and is thus not fully resolved.
        This will be handled by populate_prototypes.
    '''
    resolved_reference = build_file.split('name="{}">+/null/'.format(prototype_reference))[1]
    resolved_reference = resolved_reference.split('</VASSAL.')[0]
    return resolved_reference


def add_wacky_slashes_why_even(vlb_unprocessed):
        
    vlb_endslash_processing = []
    num_slashes = -1
    for piecemark in vlb_unprocessed.split("\t"):
        piece_entry = piecemark.rstrip("\\")
        if len(piece_entry) > 0:
            piece_entry = piece_entry + "\\"*num_slashes
            # print(piece_entry)
            vlb_endslash_processing.append(piece_entry)
            num_slashes += 1

    vlb_processed = "\t".join(vlb_endslash_processing) + "\t"
    
    return vlb_processed


def extract_suffix(piece_name,piece_data):

    piece_null_pattern = re.compile(r"piece;;;;"+piece_name+r"[\S\s]{0,}null;[0-9]{1,};[0-9]{1,};[0-9]{1,}")
    piece_null_match = piece_null_pattern.search(piece_data)

    return piece_null_match.group(0)


def add_wackier_slashes(vlb_unprocessed):
    '''
    Add the loooong string of garbage at the end of the
    entry.  Could there possibly be a worse way to do
    this?
    '''

    terminating_whack_pattern = re.compile(r"[\\]{1,}\t")
    terminating_whack_matches = terminating_whack_pattern.findall(vlb_unprocessed)

    terminating_whacks = []

    for terminating_whack_match in terminating_whack_matches:
        if len(terminating_whacks) == 0:
            terminating_whacks.append(terminating_whack_match)
        elif len(terminating_whacks[-1]) < len(terminating_whack_match):
            terminating_whacks.append(terminating_whack_match)
    [(vlb_unprocessed = vlb_unprocessed + twm)  for twm in terminating_whacks]

    return vlb_unprocessed


with open("buildFile") as build_file_obj:
    build_file = build_file_obj.read()

build_file = preprocess_build_file(build_file)

for line in build_file.split("\n"):
    if line.strip().startswith("<VASSAL.build.widget.PieceSlot"):
        piece_name = line.split('entryName="')[1].split('"')[0]
        piece_data = line.split('+/null/',1)[1].split("</VASSAL.build.widget.PieceSlot>")[0]
        if "Onager-class Testbed" in piece_name:
            suffix = extract_suffix(piece_name,piece_data)
            out = "LOG\t+//"
            out += populate_prototypes(piece_data,build_file)
            out = add_wacky_slashes_why_even(out)
            out += suffix
            out = add_wackier_slashes(out)

    # if line.strip().startswith("<VASSAL.build.module.PrototypeDefinition"):
    #     piece_name = line.split('ame="')[1].split('"')[0]
    #     piece_data = line.split('+/null/',1)[1].split("</VASSAL.build.module.PrototypeDefinition>")[0]
    #     if "Ship card prototype" in piece_name:
    #         print(piece_name)
    #         print(piece_data)
    #         out = "LOG\t+//"
    #         out += populate_prototypes(piece_data,build_file)




print(out.replace("\t","\t\n"))
