import Tempest_file_downloader
import Tempest_html_json


def get_files():
    files = Tempest_file_downloader.get_last_build()
    for File in files:
        Tempest_html_json.parse_html(File)
        pass_tests_name = Tempest_html_json.get_pass_tests_name()
        fail_tests_name = Tempest_html_json.get_fail_tests_name()
        status_pass_test = Tempest_html_json.get_status_pass()
        status_fail_test = Tempest_html_json.get_status_fail()
