import unittest
import tempfile
import os
import yaml

from convert_config_format import main as convert_main

test_ini = '''
[main]
release: master

[promote_from]
current_tripleo: tripleo-ci-testing

[current-tripleo]
job1
job2
'''


class TestConvert(unittest.TestCase):

    def setUp(self):
        __, self.path = tempfile.mkstemp()
        with open(self.path, "w") as config_file_ini:
            config_file_ini.write(test_ini)

    def tearDown(self):
        os.unlink(self.path)

    def test_convert(self):
        config_path_yaml = convert_main(self.path)
        with open(config_path_yaml, "r") as config_file:
            config = yaml.safe_load(config_file)

        self.assertEqual(config['main']['release'], "master")
        self.assertIn("job1", config['current-tripleo'])
        self.assertEqual(config['current-tripleo']['job1'], None)
