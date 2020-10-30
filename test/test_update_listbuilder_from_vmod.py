#!/usr/bin/env python3

import unittest
import update_listbuilder_from_vmod


class UpdaterTestCase(unittest.TestCase):
    
    def setUp(self):
        with open("./test/test_vmod/buildFile.xml") as build_file_obj:
            self.build_file = build_file_obj.read()

    
    def test_vmod_metadata_parsing(self):
        self.assertEqual(update_listbuilder_from_vmod.parse_vmod("./test/test_vmod/ArmadaModule_-_3.11.1.vmod")[0],
                         {"module_version":"3.11.1",
                          "vassal_version":"3.2.17",
                          "description":"Wave 8 (VWC 2020 ed.)",},
                         "Failed to correctly parse vmod.")


    def test_preprocessing_removal(self):
        self.assertNotIn("\/null\/prototype\;Upgrade",
                         update_listbuilder_from_vmod.preprocess_build_file(self.build_file),
                         "Failed to remove fucked up Leading Shots reference")


    def test_preprocessing_replacement(self):
        self.assertIn("VASSAL.build.widget.PieceSlot:Leading Shots",
                      update_listbuilder_from_vmod.preprocess_build_file(self.build_file),
                      "Failed to insert the corrected Leading Shots reference")


if __name__ == '__main__':
    unittest.main()