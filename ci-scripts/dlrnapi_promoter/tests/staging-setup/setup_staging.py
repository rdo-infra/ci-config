import logging
import os
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

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    logging.basicConfig(level=logging.DEBUG)

    log.setLevel(logging.DEBUG)
    base_path = os.path.dirname(os.path.abspath(__file__))

    staging_config = config
    IMAGES_HOME = "/tmp/"
    #IMAGES_HOME=os.environ.get('HOME', "/tmp")
    staging_config['db_fixtures'] = base_path + "/fixtures/scenario-1.yaml"
    staging_config['db_filepath'] = os.path.join(os.environ['HOME'], "sqlite.commits")
    staged_env = StagedEnvironment(staging_config)
    staged_env.setup()


if __name__ == "__main__":
    main()
