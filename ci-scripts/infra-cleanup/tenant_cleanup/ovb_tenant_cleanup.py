#!/usr/bin/env python
"""
This is a cleanup script for rdo/vexxhost cloud.
To test openstack deployment on ovb jobs, on rdo/vexxhost cloud a heat
stack is created.
Normally, Heat stack is created and destroyed by job itself.
But, sometimes due to infra related issues heat stack failed to
create/delete by job itself.
In a scenario where heat stack is not deleted by job itself, We need manual
cleanup on Infrastrusture to avoid resource crunch.
"""

import datetime
import json
import logging
import subprocess
import sys
import time

import click

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

formatter = logging.Formatter('%(asctime)s:%(message)s')
formatter.converter = time.gmtime

file_handler = logging.FileHandler('clean_stacks.log')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def env_accessibility_check():
    """ This function checks if cloud is accessible """
    try:
        subprocess.run(['openstack', 'token', 'issue'],
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        logger.error("Failed to talk with cloud, credentials should be"
                     " sourced or configured in cloud.yaml file.")
        sys.exit()
    logger.info("Successfull able to talk with cloud")


def remove_prefix(text, prefix):
    """ If a particular prefix exists in text string, This function
        removes that prefix from string and then returns the remaining string
    """
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def remove_suffix(text, suffix):
    """ If a particular suffix exists in text string, This function
        removes that suffix from string and then returns the remaining string
    """
    if suffix and text.endswith(suffix):
        return text[:-len(suffix)]
    return text


def fetch_identifier(text, prefix, suffix):
    """ Every heat stack have a unique text(identifier) in their name,
        This identifier can be used to identify associated resources of
        the heat stack.
        If a particular prefix and suffix exists in text string,
        This function removes prefix and suffix from string and
        then returns the remaining string(identifier).
    """
    text = remove_prefix(text, prefix)
    identifier = remove_suffix(text, suffix)
    logger.info("Identifier is %s", identifier)

    return identifier


def fetch_resources(resource):
    """ This function take a resource name(stack/server/network/subnet/port)
        as input and make a call to openstack cloud to list that resource.
        This function fetches the corresponding result in json format.
   """
    valid_choices = ['stack', 'server', 'network', 'subnet', 'port']
    if resource in valid_choices:
        command = "openstack {} list -f json".format(resource)
    else:
        raise ValueError("resource attribute value is not appropriate, Valid"
                         " values are {}".format(valid_choices))
    return subprocess.run("{}".format(command),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          check=True,
                          shell=True).stdout.decode('utf-8')


def heat_stacks(time_expired, prefix, nuclear):
    """ This function fetches list of heat stacks.
        If nuclear is True, this function returns list of all heat stacks.
        If nuclear is False, it returns list  of all stacks which are starting
        with prefix and running longer than time_expired minutes.
    """
    stack_list = []
    json_input = fetch_resources('stack')
    data = json.loads(json_input)
    if nuclear:
        logger.info("Collecting a list of all available Heat stacks ...")
        for item in data:
            stack_list.append(item['ID'])
        return stack_list

    logger.info("Collecting a list of Heat stacks which are older than "
                "%s minutes", time_expired)
    utc_current_time = datetime.datetime.now(datetime.timezone.utc)
    utc_time_expired = (utc_current_time
                        - datetime.timedelta(minutes=time_expired))
    utc_time_expired = utc_time_expired.strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in data:
        if item["Stack Name"].startswith(prefix):
            if item['Creation Time'] < utc_time_expired:
                stack_list.append(item['ID'])
    return stack_list


def failed_heat_stacks():
    """ This function fetches list of all heat stacks that are in i.e
        CREATE_FAILED or DELETE_FAILED state
    """
    logger.info("Collecting a list of stacks left in CREATE_FAILED "
                "or DELETE_FAILED state")
    stack_list = []
    json_input = fetch_resources('stack')
    data = json.loads(json_input)
    for item in data:
        if "FAILED" in item["Stack Status"]:
            stack_list.append(item["Stack Name"])
    return stack_list


def stack_delete(stack_list, dry_run):
    """ This function takes a list of heat stacks and delete them if dry_run
        is False. For each stack deletion this function waits till stack is
        deleted. This would avoid overwhelming the tenant with mass delete.
    """
    if stack_list:
        if dry_run:
            logger.info("DRY RUN - Stack list to "
                        "delete: %s", stack_list)
        else:
            logger.info("These stacks will be "
                        "deleted: %s", stack_list)
            for stack in stack_list:
                logger.info("Deleting stack id %s", stack)
                subprocess.run(['openstack', 'stack', 'delete', '-y',
                               '--wait', stack],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True)
    else:
        logger.info("There are no stack to delete")


def servers_with_identifier(identifier):
    """ This function fetches list of servers that have a particular
        text(identifier) in their name. If there are no servers with
        text(identifier) in their name it returns an empty list.
    """
    json_input = fetch_resources('server')
    data = json.loads(json_input)
    server_list = []
    for item in data:
        if identifier in item['Name']:
            server_list.append(item['ID'])

    return server_list


def reset_server_state(server_uuid):
    """ This function check for instance current status and reset instance
        state to active if its in error state.
    """
    status = subprocess.run("openstack server show {} -f json"
                            " | jq '.status'".format(server_uuid),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True,
                            shell=True).stdout.decode('utf-8').rstrip()
    if status == '"ERROR"':
        logger.info("Resetting state of server: %s", server_uuid)
        subprocess.run(f"openstack server set --state active {server_uuid}",
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       check=True,
                       shell=True)


def server_delete(server_names, dry_run):
    """ This function takes a list of servers and delete them if dry_run
        is False.
    """
    if server_names:
        if dry_run:
            logger.info("DRY RUN - Servers to delete: %s", server_names)
        else:
            for server in server_names:
                reset_server_state(server)
                logger.info("Deleting server ID %s", server)
                subprocess.run(['openstack', 'server', 'delete', server],
                               check=True)
    else:
        logger.info("There are no servers to delete")


def subnets_with_identifier(identifier):
    """ For every heat stack multiple subnets are created, This
        function fetches list of all the subnets which have
        text(identifier) in name.
    """
    json_input = fetch_resources('subnet')
    data = json.loads(json_input)
    subnet_list = []
    for item in data:
        if item['Name'].endswith(identifier):
            subnet_list.append(item['ID'])
    logger.info("Subnets with identifier: %s", subnet_list)
    return subnet_list


def ports_of_subnets(subnet_ids_list):
    """ This functions takes list of subnet ids as input and fetches
        list of all the ports belongs to those subnets.
    """
    port_list = []
    json_input = fetch_resources('port')
    data = json.loads(json_input)
    if subnet_ids_list:
        for item in data:
            if item['Fixed IP Addresses'][0]['subnet_id'] in subnet_ids_list:
                port_list.append(item['ID'])
    return port_list


def port_delete(port_ids, dry_run):
    """ This function takes a list of ports and delete them if dry_run
        is False.
    """
    if port_ids:
        if dry_run:
            logger.info("DRY RUN - Ports to delete: %s", port_ids)
        else:
            for port in port_ids:
                logger.info("Deleting port ID %s", port)
                subprocess.run(['openstack', 'port', 'delete', port],
                               check=True)
    else:
        logger.info("There are no ports to delete")


def networks_with_identifier(identifier):
    """ This function fetches list of networks that have a particular
        text(identifier) in their name. If there are no networks with
        text(identifier) in their name it returns an empty list.
    """
    json_input = fetch_resources('network')
    data = json.loads(json_input)
    network_list = []
    for item in data:
        if item['Name'].endswith(identifier):
            network_list.append(item['ID'])
    return network_list


def network_delete(network_ids, dry_run):
    """ This function takes a list of networks and delete them if dry_run
        is False.
    """
    if network_ids:
        if dry_run:
            logger.info("DRY RUN - Networks to delete: %s", network_ids)
        else:
            for network_id in network_ids:
                logger.info("Deleting network ID %s", network_id)
                subprocess.run(['openstack', 'network', 'delete', network_id],
                               check=True)
    else:
        logger.info("There are no networks to delete")


def delete_individual_resources(stack_list_status, prefix, suffix, dry_run):
    """ This function takes a list of heat stack which failed to create
        or delete successfully. It then deletes the individual resources
        (including instances, ports, and networks) of that heat stack.
    """
    if stack_list_status == []:
        logger.info("There are no stacks to delete, exiting script.")
        sys.exit()
    else:
        logger.info("There are stacks in CREATE_FAILED "
                    "or DELETE_FAILED state - %s", stack_list_status)

        for stack in stack_list_status:
            # Extract identfier for associated resources
            logger.info("Removing individual resources which are associated "
                        "with stack %s", stack)
            identifier = fetch_identifier(stack, prefix, suffix)
            fetched_servers = servers_with_identifier(identifier)
            server_delete(fetched_servers, dry_run)
            # delete empty ports associated with subnets and then networkso
            fetched_subnets_list = subnets_with_identifier(identifier)
            fetched_subnet_ports = ports_of_subnets(fetched_subnets_list)
            port_delete(fetched_subnet_ports, dry_run)
            fetched_networks = networks_with_identifier(identifier)
            network_delete(fetched_networks, dry_run)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--time-expired',
              '-t',
              help='Time, in minutes, a stack has been running when it will '
                   'be deleted. It is used with the long-running option. '
                   'Defaults to 300 minutes (5 hours)',
              default=300,
              type=int)
@click.option('--stack-list',
              '-s',
              help='Stack, with associated resources to delete. '
                   'Alternative to the long-running option. '
                   '**To pass more than one stack, syntax is '
                   '-s <stack1 uuid> -s <stack2 uuid> -s <stack3 uuid>**',
              multiple=True)
@click.option('--nuclear',
              '-n',
              help='Delete all stacks, associated resources,and unmarked '
                   'ports. Default is delete only specified stacks and '
                   'resources. Use with caution - unmarked ports associated '
                   'with other instances will also be deleted"',
              is_flag=True,
              default=False)
@click.option('--dry-run',
              '-d',
              help='Do not delete any stacks or resources. '
                   'Print out the resources that would be deleted. '
                   'This option is off by default"',
              is_flag=True,
              default=False)
@click.option('--prefix',
              '-p',
              help='Stack name prefix added before the stack unique identifer.'
                   ' Default is baremetal_ ',
              default='baremetal_')
@click.option('--suffix',
              '-f',
              help='Stack name suffix added after the stack unique identifer. '
                   'Default is an empty string ',
              default='')
def main(time_expired=300, stack_list=(), nuclear=False,
         dry_run=False, prefix="baremetal_", suffix=""):
    """ This is the main function called when script is executed.
        It first checks if cloud is accessible, then it fetches
        list of heat stack to be deleted depending on inputs.
        This function first tries to delete the heat stack, if it
        cannot delete the heat stack, it removes the associated resources of
        heat stack and tries to delete it again.
    """
    # Check that we can talk with the cloud
    env_accessibility_check()
    # Get list of stacks if they are not passed using --stack-list
    if not stack_list:
        stack_list = heat_stacks(time_expired, prefix, nuclear)
    # Make first attempt to delete each stack
    stack_delete(stack_list, dry_run)
    #  Check if there are stacks left in CREATE_FAILED or DELETE_FAILED state
    stack_list_status = failed_heat_stacks()
    # Remove associated resources and then delete the stacks again.
    delete_individual_resources(stack_list_status, prefix, suffix, dry_run)
    stack_delete(stack_list_status, dry_run)
    # Recheck if there are stacks left in CREATE_FAILED or DELETE_FAILED state
    stack_list_status = failed_heat_stacks()
    if len(stack_list_status) == 0:
        logger.info("Script ran successfully")
    else:
        logger.info("Script didn't executed Successfully, Manual intervention "
                    "needed for following stacks %s", stack_list_status)


if __name__ == "__main__":
    main()
