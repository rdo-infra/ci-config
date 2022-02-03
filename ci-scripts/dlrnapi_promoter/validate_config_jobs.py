from __future__ import print_function

import logging
import os

import click
import requests
import yaml


class ZuulAPI:
    def __init__(self, name, verbose=False,
                 tenant='openstack'):
        self.name = name
        self.tenant = tenant
        self.verbose = verbose

    def get_job_names(self):
        """
        Get job names from zuul
        """
        if self.tenant:
            url = os.path.join(self.name, 'api', 'tenant', self.tenant, 'jobs')
        else:
            url = os.path.join(self.name, 'api', 'jobs')
        logging.debug("Requesting: {}".format(url))
        jobs = requests.get(url)
        all_jobs = jobs.json()
        return_jobs = [i['name'] for i in all_jobs]
        logging.debug("Zuul returned {} jobs.".format(len(return_jobs)))
        return return_jobs


class ConfigFiles:
    def __init__(self, config_dir, verbose=False, component=True):
        self.component = component
        self.config_dir = config_dir
        self.verbose = verbose

    def get_files(self):
        """
        This method will return file list for the component and criteria
        """
        all_files = []
        jobs_home = self.config_dir
        for dirs, subdir, files in os.walk(os.path.join(os.curdir, jobs_home)):
            for f in files:
                if f in ['defaults.yaml', 'global_defaults.yaml']:
                    logging.debug("Skipping: {}".format(f))
                    continue
                if f.endswith('.yaml') or f.endswith('.yml'):
                    all_files.append(os.path.join(os.path.abspath(dirs), f))
        return all_files

    def get_jobs_from_file(self, files):
        """
        This method will return jobs from component file.
        """
        jobs = []
        files = [files] if isinstance(files, str) else files
        for f in files:
            logging.debug("Reading jobs from file: {}".format(f))
            if isinstance(f, str):
                file_data = open(f).read()
                yaml_data = yaml.safe_load(file_data)
                if 'promoted-components' in yaml_data.keys():
                    components = yaml_data['promoted-components']
                    for key, value in components.items():
                        logging.debug("Getting {} component jobs".format(key))
                        if value:
                            jobs.extend(value)
                elif 'criteria' in yaml_data[
                        'promotions']['current-tripleo'].keys():
                    logging.debug("Getting jobs from promotion: "
                                  "'current-tripleo'")
                    criteria = yaml_data['promotions'][
                        'current-tripleo']['criteria']
                    if criteria:
                        jobs.extend(criteria)
        return jobs


@click.command()
@click.option('-c', '--config-dir', help='Config dir', required=True)
@click.option('-z', '--zuul-url', help="Zuul url",
              default="https://review.rdoproject.org/zuul")
@click.option('-v', '--verbose', help="Verbose", is_flag=True)
def jobs_validation(config_dir, zuul_url, verbose):
    loglevel = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(encoding='utf-8', level=loglevel)

    config = ConfigFiles(config_dir, verbose=verbose)
    tenant = '' if 'rdoproject' in zuul_url else 'openstack'
    logging.debug("Using tenant: {}".format(tenant))
    zuul_client = ZuulAPI(zuul_url, verbose=verbose, tenant=tenant)

    file_jobs = []
    c_files = config.get_files()
    file_jobs.extend(config.get_jobs_from_file(c_files))
    all_jobs = zuul_client.get_job_names()
    file_jobs_without_exception = set(file_jobs) - set(all_jobs)
    if file_jobs_without_exception:
        print("Invalid jobs:")
        print("\n - " + "\n - ".join(file_jobs_without_exception))
    else:
        print("SUCCESS: All jobs are okay.")


if __name__ == '__main__':
    jobs_validation()  # pylint: disable = E1120
