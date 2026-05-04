"""Tests for scripts.models routing tables and resolve()."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import models  # noqa: E402


EXPECTED_AESTHETICS = {
    "fashion",
    "portrait",
    "lifestyle",
    "product",
    "cinematic",
    "architectural",
    "atmospheric",
    "typography",
    "poster",
    "illustration",
    "stylized",
    "brand_palette",
}


class TestLaneToModel(unittest.TestCase):
    def test_i2i_product_middle_slug(self):
        self.assertEqual(
            models.LANE_TO_MODEL["i2i_product_middle"],
            "black-forest-labs/flux/kontext",
        )

    def test_i2v_middle_slug(self):
        self.assertEqual(
            models.LANE_TO_MODEL["i2v_middle"],
            "kling-video/v2.1/pro/image-to-video",
        )


class TestAestheticToModel(unittest.TestCase):
    def test_product_slug(self):
        self.assertEqual(
            models.AESTHETIC_TO_MODEL["product"],
            "google/nano-banana-pro",
        )

    def test_all_twelve_enum_values_present(self):
        self.assertEqual(set(models.AESTHETIC_TO_MODEL.keys()), EXPECTED_AESTHETICS)
        self.assertEqual(len(models.AESTHETIC_TO_MODEL), 12)


class TestResolve(unittest.TestCase):
    def test_resolve_primary(self):
        self.assertEqual(
            models.resolve("i2i_product_middle", fallback=0),
            "black-forest-labs/flux/kontext",
        )

    def test_resolve_second_fallback(self):
        self.assertEqual(
            models.resolve("i2i_product_middle", fallback=2),
            "higgsfield-ai/soul/inpaint",
        )

    def test_resolve_out_of_range_raises(self):
        with self.assertRaises(KeyError):
            models.resolve("i2i_product_middle", fallback=99)


if __name__ == "__main__":
    unittest.main()
