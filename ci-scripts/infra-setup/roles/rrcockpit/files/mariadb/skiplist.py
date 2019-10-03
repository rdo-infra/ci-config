import argparse
import requests
import os


def main():
    parser = argparse.ArgumentParser(
        description='This will get the tempest_file for fs021.')
    parser.add_argument(
        '--release',
        default=['master'],
        nargs='+',
        help="(default: %(default)s)")
    parser.add_argument(
        '--job_name',
        default='periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-',
        help="(default: %(default)s)")
    parser.add_argument(
        '--log_file',
        default='',
        help='spacifiy the file name')
    parser.add_argument(
        '--tempest_dump_dir',
        default='/tmp/skip',
        help='tempest_dump_dir')
    args = parser.parse_args()
    get_last_build(
        args.release,
        args.job_name,
        args.log_file,
        args.tempest_dump_dir)


ZUUL_API_BUILD = 'https://review.rdoproject.org/zuul/api/builds?job_name='


def get_last_build(releases, job_name, tempest_log, tempest_dump_dir):
    tempest = []
    for release in releases:
        zuul_job_url = '{}{}{}'.format(
            ZUUL_API_BUILD, job_name, release)
        resp = requests.get(zuul_job_url)
        if resp.status_code == 200:
            zuul_log_url = resp.json()[0]['log_url']
            tempest_log_url = '{}{}'.format(zuul_log_url, tempest_log)
            if requests.get(tempest_log_url).status_code == 200:
                if not os.path.exists(tempest_dump_dir):
                    os.mkdir(tempest_dump_dir)
                file_name = download_tempest_file(
                    tempest_log_url, tempest_dump_dir)
                tempest.append((file_name, job_name + release))
    return tempest


def download_tempest_file(url, local_dir):
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(os.path.join(local_dir, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
    return local_filename


if __name__ == "__main__":
    main()
