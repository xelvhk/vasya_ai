from __future__ import annotations

import unittest

from scripts.ui.avatar_skins import (
    avatar_skin_ids,
    avatar_skin_spec,
    exportable_skin_spec,
    pack_skin_combo_value,
    pack_skin_from_combo_value,
)


class AvatarSkinsTests(unittest.TestCase):
    def test_avatar_skin_ids_include_classic_default(self) -> None:
        self.assertIn("classic", avatar_skin_ids())

    def test_avatar_skin_spec_falls_back_to_default(self) -> None:
        self.assertEqual(
            avatar_skin_spec("missing")["label"],
            avatar_skin_spec("classic")["label"],
        )

    def test_pack_skin_combo_value_round_trip(self) -> None:
        combo_value = pack_skin_combo_value("8-bit-cat")

        self.assertEqual(pack_skin_from_combo_value(combo_value), "8-bit-cat")

    def test_pack_skin_from_combo_value_rejects_regular_skin_ids(self) -> None:
        self.assertIsNone(pack_skin_from_combo_value("classic"))
        self.assertIsNone(pack_skin_from_combo_value(""))

    def test_exportable_skin_spec_has_label(self) -> None:
        exported = exportable_skin_spec("classic")

        self.assertIn("label", exported)


if __name__ == "__main__":
    unittest.main()
