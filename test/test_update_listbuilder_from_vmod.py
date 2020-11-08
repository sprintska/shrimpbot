#!/usr/bin/env python3

import datetime
import unittest
import update_listbuilder_from_vmod as updater


class UpdaterTestCase(unittest.TestCase):
    def setUp(self):
        self.test_instance = updater.VassalModule(
            "./test/test_vmod/ArmadaModule_-_3.11.1.vmod"
        )

    def test_vmod_metadata_parsing(self):
        self.assertEqual(
            self.test_instance.metadata,
            {"date_saved": datetime.datetime.fromtimestamp(1578157636),
             "description": "Wave 8 (VWC 2020 ed.)",
             "module_version": "3.11.1",
             "name": "Star Wars Armada",
             "vassal_version": "3.2.17",
             "vmod_schema_version": "1"},
            "Failed to correctly parse vmod.",
        )

    def test_preprocessing_removal(self):
        self.assertNotIn(
            "\\/null\\/prototype\\;Upgrade",
            self.test_instance.build_xml_raw,
            "Failed to remove fucked up Leading Shots reference",
        )

    def test_preprocessing_replacement(self):
        self.assertIn(
            "VASSAL.build.widget.PieceSlot:Leading Shots",
            self.test_instance.build_xml_raw,
            "Failed to insert the corrected Leading Shots reference",
        )


if __name__ == "__main__":
    unittest.main()
