import logging
import os
import pprint
from staged_environment import StagedEnvironment


config = {
    "candidate_name": "tripleo-ci-testing",
    "release": "master",
    "distros": [
        "centos7",
        "redhat8"
    ],
    "overcloud_images": {
        "base_dir": "/tmp/overcloud_images/"
        ""
    },
    "containers":{
        "registry_url": "",
        "template_dir": ""
    },
    "dlrn": {
        "repo_root": "data/repos"
    }
}



def main():

    log = logging.getLogger("promoter-staging")

    base_path = os.path.dirname(os.path.abspath(__file__))

    staging_config = config
    IMAGES_HOME = "/tmp/"
    #IMAGES_HOME=os.environ.get('HOME', "/tmp")
    staging_config['db_fixtures'] = base_path + "/fixtures/scenario-1.yaml"
    staged_env = StagedEnvironment(staging_config)
    staged_env.teardown()


if __name__ == "__main__":
    main()
