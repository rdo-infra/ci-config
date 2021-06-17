"""
This script emulates the state of the environment around promoter as it would be
just before starting a promotion process.

The promotion interacts with:
    - dlrn_api (staged locally as standalone service)
    - docker registries (staged locally with registries on different ports)
    - images server (staged locally as normal sftp via ssh)

It can setup different components independently, the list of components it
handles it's currently defined by the "scenes" variable

This provisioner should produce

- A database usable by dlrnapi that contains hashes, users, votes from jobs
- A hierarchy for overcloud images, so image promotion script can
  sftp to localhost and change the links accordingly
- A containers definition file, oused by container-push
  playbook as a list of containers to promote.
- a yaml file containing reusable information on what this script produced for
  the components called
- A set of images pushed to source registry, so the promoter has the container
  to pull and  push during the promotion run
- A file with all information on what was produced by an executions
"""
import argparse
import logging
import os

from promoter.common import get_log_file
from promoter.config import PromoterConfigFactory
from stage.stage_config import StageConfig
from stage.stage_orchestrator import StageOrchestrator


def command_setup(staged_env):
    staged_env.setup()


def command_teardown(staged_env):
    staged_env.teardown()


def parse_args(defaults, cmd_line=None):
    """
    parses command line arguments
    :param cmd_line: an optional str paramter to simlate a command line.
    Useful for testing this function
    :return: The argparse args namespace object with cli arguments
    """
    parser = argparse.ArgumentParser(description='Staging promoter')
    default_scenes = ','.join(defaults['scenes'])
    parser.add_argument('--scenes',
                        default=default_scenes,
                        help=("Select scenes to create in the environment "
                              "scenes available {}"
                              "".format(default_scenes))
                        ),
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help="Don't do anything, still create stage-info")
    parser.add_argument('--promoter-user',
                        default=os.environ.get("USER", None),
                        help="The promoter user")
    parser.add_argument('--stage-info-file',
                        default=defaults['stage_info_file'],
                        help="Config file for stage results")
    parser.add_argument('--extra-settings',
                        help="Config file with additional settings")
    parser.add_argument('--db-data-file',
                        default=defaults['db_data_file'],
                        help=("Data file to inject to dlrn server"
                              " (relative to config dir)"))

    command_parser = parser.add_subparsers(dest='subcommand')
    command_parser.required = True
    setup_parser = command_parser.add_parser('setup',
                                             help="Set up the stage")
    setup_parser.set_defaults(handler=command_setup)
    setup_parser.add_argument('--release-config',
                              required=True,
                              help=("Config file for promoter"
                                    " on which to base the stage"
                                    " (relative to config dir)"))

    teardown_parser = command_parser.add_parser('teardown',
                                                help="Tear down the stage")
    teardown_parser.set_defaults(handler=command_teardown)

    # Parse from the function parameter if present
    if cmd_line is not None:
        args = parser.parse_args(cmd_line.split())
    else:
        args = parser.parse_args()

    return args


def main(cmd_line=None):
    """
    The main sets up logging and instantiates the Config object and the staging
    environment object.
    The calls the proper action based on the mandatory action command line
    argument.
    :param cmd_line: an optional parameter to pass to the argument parser
    function
    :return: the configuration produced if a cmd_line has been passed. None
    otherwise. Useful for testing of the main function
    """
    release_config = 'CentOS-8/master.yaml'
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('dlrnapi_promoter')
    log.setLevel(logging.DEBUG)

    log.info("Checking for log directory")
    log_file = os.path.expanduser(get_log_file('staging',
                                               release_config))
    log_dir = "/".join(log_file.split("/")[:-1])
    if not os.path.exists(log_dir):
        log.info("Creating log directory : {}".format(log_dir))
        os.makedirs(log_dir)
    config_builder = PromoterConfigFactory(config_class=StageConfig)

    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger("promoter-staging")
    log.setLevel(logging.DEBUG)

    args = parse_args(config_builder.global_defaults, cmd_line=cmd_line)

    if hasattr(args, "release_config"):
        release_config = args.release_config
    config_builder = PromoterConfigFactory(config_class=StageConfig,
                                           **{'log_file': log_file})

    config = config_builder("staging", release_config,
                            validate=None)
    # Export dlrn password
    os.environ['DLRNAPI_PASSWORD'] = config.dlrn['server']['password']
    staged_env = StageOrchestrator(config)
    args.handler(staged_env)

    if cmd_line is not None:
        return config


if __name__ == "__main__":
    main()
