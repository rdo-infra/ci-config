#! /usr/bin/python3
"""
This is a cleanup script for vexxhost/psi cloud.
To test openstack deployment on ovb jobs, on vexxhost/si cloud a heat
stack is created.
Normally, Heat stack is created and destroyed by job itself.
But, sometimes due to infra related issues heat stack failed to
create/delete by job itself.
In a scenario where heat stack is not deleted by job itself, We need manual
cleanup on Infrastrusture to avoid resource crunch.


Expectations from this script:-

* Check if vexx/PSI infrastructure is reachable.

* Find stack which are older than 6 hours.
* Delete stacks which are older than 6 hours.
* Find stacks which are i.e in `CREATE_FAILED` or `DELETE_FAILED` state
* Delete stacks which are i.e in `CREATE_FAILED` or `DELETE_FAILED` state

* Sleep(wait for stack to delete)

* If some stacks cannot be deleted - Find list of those stacks
* Extract identifier from those stack names
* Delete the individual resources which are associated to those stacks.
- Server
- port
- Subnet
- Network
- router
- Security group
* Attempt to delete the stacks again

* Sleep(wait for stack to delete)

* If all stacks are deleted - Success, if not - failure (logs with details to
  reach out to infra team)
"""

import argparse
import datetime
import logging
import sys
import time

import openstack

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
    return identifier


def env_accessibility_check(cloud_name):
    """ This function checks if cloud is accessible """
    conn = openstack.connect(cloud=cloud_name)
    try:
        conn.identity.get_token()
    except Exception:
        return False
    return True


def old_heat_stacks(cloud_name, time_expired=360):
    """ This function fetches list of heat stacks
        which running longer than time_expired minutes.
    """
    conn = openstack.connect(cloud=cloud_name)
    old_stack_list = []
    utc_current_time = datetime.datetime.now(datetime.timezone.utc)
    utc_time_expired = (utc_current_time
                        - datetime.timedelta(minutes=time_expired))
    utc_time_expired = utc_time_expired.strftime("%Y-%m-%dT%H:%M:%SZ")
    for stack in conn.orchestration.stacks():
        if stack['created_at'] < utc_time_expired:
            old_stack_list.append(stack['id'])
    return old_stack_list


def stack_delete(cloud_name, stack_list, dry_run=False):
    """ This function takes a list of heat stacks and delete them if dry_run
        is False. After each stack deletion this function waits for 20 seconds
        deleted. This would avoid overwhelming the tenant with mass delete.
    """
    conn = openstack.connect(cloud=cloud_name)
    if stack_list:
        if dry_run:
            logger.info("DRY RUN - Stack list to "
                        "delete: %s", stack_list)
        else:
            logger.info("These stacks will be "
                        "deleted: %s", stack_list)
            for stack in stack_list:
                logger.info("Deleting stack id %s", stack)
                conn.orchestration.delete_stack(stack)
                time.sleep(20)
    else:
        logger.info("There are no stack to delete")


def failed_heat_stacks(cloud_name):
    """ This function fetches list of all heat stacks that are in i.e
        CREATE_FAILED or DELETE_FAILED state
    """
    conn = openstack.connect(cloud=cloud_name)
    failed_stack_list = []
    for stack in conn.orchestration.stacks():
        if "FAILED" in stack['status']:
            failed_stack_list.append(stack["name"])
    return failed_stack_list


def servers_with_identifier(cloud_name, identifier):
    """ This function fetches list of servers that have a particular
        text(identifier) in their name. If there are no servers with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud=cloud_name)
    server_list = []
    for server in conn.compute.servers():
        if identifier in server['name']:
            server_list.append(server['id'])
        else:
            for network in server['addresses']:
                if identifier in network:
                    server_list.append(server['id'])
    return server_list


def server_delete(cloud_name, server_names, dry_run=False):
    """ This function takes a list of servers and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud=cloud_name)
    if server_names:
        if dry_run:
            logger.info("DRY RUN - Servers to delete: %s", server_names)
        else:
            for server in server_names:
                logger.info("Deleting server ID %s", server)
                conn.compute.delete_server(server)
    else:
        logger.info("There are no servers to delete")


def subnets_with_identifier(cloud_name, identifier):
    """ For every heat stack multiple subnets are created, This
        function fetches list of all the subnets which have
        text(identifier) in name.
    """
    conn = openstack.connect(cloud=cloud_name)
    subnet_with_identifier_list = []
    for subnet in conn.network.subnets():
        if subnet['name'].endswith(identifier):
            subnet_with_identifier_list.append(subnet['id'])
    return subnet_with_identifier_list


def ports_of_subnets(cloud_name, subnet_ids_list):
    """ This functions takes list of subnet ids as input and fetches
        list of all the ports belongs to those subnets.
    """
    conn = openstack.connect(cloud=cloud_name)
    port_list = []
    if subnet_ids_list:
        for subnet in subnet_ids_list:
            for port in conn.network.get_subnet_ports(subnet):
                port_list.append(port['id'])
    return port_list


def port_delete(cloud_name, port_ids, dry_run=False):
    """ This function takes a list of ports and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud=cloud_name)
    if port_ids:
        if dry_run:
            logger.info("DRY RUN - Ports to delete: %s", port_ids)
        else:
            for port in port_ids:
                logger.info("Deleting port ID %s", port)
                conn.network.delete_port(port)
    else:
        logger.info("There are no ports to delete")


def networks_with_identifier(cloud_name, identifier):
    """ This function fetches list of networks that have a particular
        text(identifier) in their name. If there are no networks with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud=cloud_name)
    network_list = []
    for network in conn.network.networks():
        if network['name'].endswith(identifier):
            network_list.append(network['id'])
    return network_list


def network_delete(cloud_name, network_ids, dry_run=False):
    """ This function takes a list of networks and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud=cloud_name)
    if network_ids:
        if dry_run:
            logger.info("DRY RUN - Networks to delete: %s", network_ids)
        else:
            for network_id in network_ids:
                logger.info("Deleting network ID %s", network_id)
                conn.network.delete_network(network_id)
    else:
        logger.info("There are no networks to delete")


def routers_with_identifier(cloud_name, identifier):
    """ This function fetches list of routers that have a particular
        text(identifier) in their name. If there are no router with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud=cloud_name)
    router_list = []
    for router in conn.network.routers():
        if identifier in router['name']:
            router_list.append(router['id'])
    return router_list


def router_interface_delete(cloud_name, router_id, dry_run=False):
    """ This function takes a router id and deattaches its
        interfaces"""
    conn = openstack.connect(cloud=cloud_name)
    for port in conn.network.ports(device_id=router_id):
        if port['device_owner'] == 'network:router_interface':
            logger.info("Deattaching %s from  %s", port['id'], router_id)
            if not dry_run:
                conn.network.remove_interface_from_router(
                        router_id, port_id=port['id'])


def router_delete(cloud_name, router_ids, dry_run=False):
    """ This function takes a list of routers and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud=cloud_name)
    if router_ids:
        if dry_run:
            logger.info("DRY RUN - Routers to delete: %s", router_ids)
        else:
            for router_id in router_ids:
                logger.info("Deleting router ID %s", router_id)
                router_interface_delete(cloud_name, router_id, dry_run)
                conn.network.delete_router(router_id)
    else:
        logger.info("There are no router to delete")


def sec_gp_with_identifier(cloud_name, identifier):
    """ This function fetches list of security group that have a particular
        text(identifier) in their name. If there are no security group with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud=cloud_name)
    security_group = []
    for sec_group in conn.network.security_groups():
        if identifier in sec_group['name']:
            security_group.append(sec_group['id'])
    return security_group


def sec_group_delete(cloud_name, sec_group_ids, dry_run=False):
    """ This function takes a list of security group and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud=cloud_name)
    if sec_group_ids:
        if dry_run:
            logger.info("DRY RUN: Security group to delete: %s", sec_group_ids)
        else:
            for sec_group_id in sec_group_ids:
                logger.info("Deleting Security group with ID %s", sec_group_id)
                conn.network.delete_security_group(sec_group_id)
    else:
        logger.info("There are no Security group to delete")


def delete_individual_resources(cloud_name, stack_list, prefix='baremetal_',
                                suffix="", dry_run=False):
    """ This function takes a list of heat stack which failed to create
        or delete successfully. It then deletes the individual resources
        (including instances, ports, security group and networks) of that
        heat stack.
    """
    if stack_list == []:
        logger.info("There are no stacks to delete")
    else:
        logger.info("There are stacks in CREATE_FAILED "
                    "or DELETE_FAILED state - %s", stack_list)

        for stack in stack_list:
            # Extract identfier for associated resources
            logger.info("Removing individual resources which are associated "
                        "with stack %s", stack)
            identifier = fetch_identifier(stack, prefix, suffix)
            logger.info("Identifier is %s", identifier)
            fetched_servers = servers_with_identifier(cloud_name, identifier)
            server_delete(cloud_name, fetched_servers, dry_run)
            fetched_routers = routers_with_identifier(cloud_name, identifier)
            router_delete(cloud_name, fetched_routers, dry_run)
            # delete empty ports associated with subnets and then networkso
            fetched_subnets_list = subnets_with_identifier(cloud_name,
                                                           identifier)
            logger.info("Subnets to delete %s", fetched_subnets_list)
            fetched_subnet_ports = ports_of_subnets(cloud_name,
                                                    fetched_subnets_list)
            port_delete(cloud_name, fetched_subnet_ports, dry_run)
            fetched_networks = networks_with_identifier(cloud_name, identifier)
            network_delete(cloud_name, fetched_networks, dry_run)
            fetched_sec_groups = sec_gp_with_identifier(cloud_name, identifier)
            sec_group_delete(cloud_name, fetched_sec_groups, dry_run)


def main(cloud_name, time_expired=360, dry_run=False,
         prefix="baremetal_", suffix=""):
    """ This is the main function called when script is executed.
        It first checks if cloud is accessible, then it fetches
        list of heat stack to be deleted depending on inputs.
        This function first tries to delete the heat stack, if it
        cannot delete the heat stack, it removes the associated resources of
        heat stack and tries to delete it again.
    """
    logger.info("==========================================================")
    logger.info("Starting script for cleanup on %s", cloud_name)

    # Check if vexx/PSI infrastructure is reachable.
    if env_accessibility_check(cloud_name):
        logger.info("Successfull able to talk with cloud")
    else:
        logger.info("Failed to talk with cloud, credentials should be"
                    " sourced or configured in cloud.yaml file.")
        sys.exit()

    # Find stacks which are older than time_expired and delete them.
    old_stack_list = old_heat_stacks(cloud_name, time_expired)
    logger.info("Stacks which was older than %s mins: %s",
                time_expired, old_stack_list)
    stack_delete(cloud_name, old_stack_list, dry_run)

    # Find stacks which are in `FAILED` state and delete them.
    failed_stack_list = failed_heat_stacks(cloud_name)
    logger.info("Stacks which are in  CREATE_FAILED or DELETE_FAILED state"
                ": %s", failed_stack_list)
    stack_delete(cloud_name, failed_stack_list, dry_run)

    # wait for stack to delete
    if not dry_run:
        logger.info("Waiting for 150s for stacks to delete ")
        # wait for 150s
        time.sleep(150)

    #  ReCheck if there are stacks left in CREATE_FAILED/ DELETE_FAILED state
    logger.info("Rechecking if there are stacks left in CREATE_FAILED"
                " or DELETE_FAILED state")
    failed_stack_list = failed_heat_stacks(cloud_name)
    logger.info("Stacks which are in FAILED state %s", failed_stack_list)

    # Delete the individual resources which are associated to stacks which
    # cannot be deleted normally.
    if failed_stack_list:
        delete_individual_resources(cloud_name, failed_stack_list, prefix,
                                    suffix, dry_run)
        stack_delete(cloud_name, failed_stack_list, dry_run)
        if not dry_run:
            # wait for 150s
            time.sleep(150)

    # Success/ Failure based on left over stacks
    failed_stack_list = failed_heat_stacks(cloud_name)
    if len(failed_stack_list) == 0:
        logger.info("Script ran successfully: No Heat stack in failed state")
    else:
        logger.info("Script didn't executed Successfully, Manual intervention "
                    "needed for following stacks %s", failed_stack_list)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OVB Stale resources cleanup"
                                     " script for vexxhost/psi cloud")
    parser.add_argument('-t',
                        '--time-expired',
                        type=int,
                        metavar='',
                        default=360,
                        help='Time, in minutes, a stack has been running when '
                        'it will be deleted. Defaults to 360 minutes(6 hours)')

    parser.add_argument('-d',
                        '--dry-run',
                        action='store_true',
                        help='Do not delete any stacks or resources. '
                        'Print out the resources that would be deleted. '
                        'This option is off by default"')

    parser.add_argument('-p',
                        '--prefix',
                        metavar='',
                        default='baremetal_',
                        help='Stack name prefix added before the stack unique '
                        'identifer. Default is "baremetal_" ')

    parser.add_argument('-s',
                        '--suffix',
                        metavar='',
                        default='',
                        help='Stack name suffix added after the stack unique '
                        'identifer. Default is an empty string.')

    parser.add_argument('-c',
                        '--cloud-name',
                        metavar='',
                        help='OpenStack Cloud name to connect to, It is '
                        'expected that you have a clouds.yaml file which '
                        'contains auth info about the cloud name you passes '
                        'here. File clouds.yaml will be looked i.e in the '
                        'current directory, $HOME/.config/openstack or '
                        '/etc/openstack')

    args = parser.parse_args()

    main(time_expired=args.time_expired,
         prefix=args.prefix,
         suffix=args.suffix,
         dry_run=args.dry_run,
         cloud_name=args.cloud_name)
