import unittest

from registry_image import ImageName


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
        image_name = ImageName("nova")
        self.assertEqual(image_name.registry, None)
        self.assertEqual(image_name.namespace, None)
        self.assertEqual(image_name.base_name, "nova")
        self.assertEqual(image_name.tag, None)

    def test_get_parts_one(self):
        image_name = ImageName("http://localhost:4000/nova")
        self.assertEqual(image_name.registry, "localhost:4000")
        self.assertEqual(image_name.namespace, None)
        self.assertEqual(image_name.base_name, "nova")
        self.assertEqual(image_name.tag, None)
