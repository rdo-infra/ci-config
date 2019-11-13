import requests
import os

RELEASES = ['master', 'stein', 'rocky', 'queens']
JOB_NAME = 'periodic-tripleo-ci-centos-7-ovb-1ctlr_2comp-featureset021-'
ZUUL_API_BUILD = 'https://review.rdoproject.org/zuul/api/builds?job_name='
TEMPEST_LOG = 'logs/tempest.html.gz'
TEMPEST_DUMP_DIR = '/tmp/skip'


def get_last_build():
    """It will first get the log_url for each supported release of FS021
    job and then appends logs/tempest.html.gz file and check whether new
    log_url exists or not. If exists, It will download the tempest file in
    temp directory.
    Returns: job_name and log_file
    """
    tempest = []
    for release in RELEASES:
        zuul_job_url = '{}{}{}'.format(ZUUL_API_BUILD, JOB_NAME, release)
        resp = requests.get(zuul_job_url)
        if resp.status_code == 200:
            zuul_log_url = resp.json()[0]['log_url']
            tempest_log_url = '{}{}'.format(zuul_log_url, TEMPEST_LOG)
            if requests.get(tempest_log_url).status_code == 200:
                if not os.path.exists(TEMPEST_DUMP_DIR):
                    os.mkdir(TEMPEST_DUMP_DIR)
                file_name = download_tempest_file(
                    tempest_log_url, TEMPEST_DUMP_DIR)
                tempest.append((file_name, JOB_NAME+release))
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
    print(get_last_build())

