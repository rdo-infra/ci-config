import unittest

from containers_lists import ImageName


class ImageNameGet(unittest.TestCase):

    def test_get_full(self):
        image_name = ImageName(('host:port', 'namespace', 'base_name',
                                     'tag'))

        self.assertEqual(image_name.full, "host:port/namespace/base_name:tag")

    def test_get_full_no_tag(self):
        image_name = ImageName(('host:port', 'namespace', 'base_name',
                                'tag'))

        self.assertEqual(image_name.full_no_tag,
                         "host:port/namespace/base_name")


class ImageNameGetParts(unittest.TestCase):

    def test_get_parts_full(self):
        assert False

