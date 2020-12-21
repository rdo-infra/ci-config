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

* Find stack which are older than 5 hours.
* Delete stacks which are older than 5 hours.
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
import sys
import time
import openstack

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
    print("Identifier is %s", identifier)

    return identifier


def env_accessibility_check():
    """ This function checks if cloud is accessible """
    conn = openstack.connect(cloud='overcloud')
    try:
        conn.identity.get_token()
    except:
        print("Failed to talk with cloud, credentials should be"
              " sourced or configured in cloud.yaml file.")
        return False
    print("Successfull able to talk with cloud")
    return True


def old_heat_stacks(time_expired=300):
    """ This function fetches list of heat stacks
        which running longer than time_expired minutes.
    """
    conn = openstack.connect(cloud='overcloud')
    old_stack_list=[]
    utc_current_time = datetime.datetime.now(datetime.timezone.utc)
    utc_time_expired = (utc_current_time
                        - datetime.timedelta(minutes=time_expired))
    utc_time_expired = utc_time_expired.strftime("%Y-%m-%dT%H:%M:%SZ")
    for stack in conn.orchestration.stacks():
        if stack['created_at']  < utc_time_expired:
            old_stack_list.append(stack['id'])
    print(f"Stacks which was older than {time_expired} minutes : {old_stack_list}")
    return old_stack_list


def stack_delete(stack_list, dry_run=False):
    """ This function takes a list of heat stacks and delete them if dry_run
        is False. After each stack deletion this function waits for 5 seconds
        deleted. This would avoid overwhelming the tenant with mass delete.
    """
    conn = openstack.connect(cloud='overcloud')
    if stack_list:
        if dry_run:
            print("DRY RUN - Stack list to "
                  "delete: %s", stack_list)
        else:
            print("These stacks will be "
                  "deleted: %s", stack_list)
            for stack in stack_list:
                print("Deleting stack id %s", stack)
                conn.orchestration.delete_stack(stack)
                time.sleep(20)
    else:
        print("There are no stack to delete")


def failed_heat_stacks():
    """ This function fetches list of all heat stacks that are in i.e
        CREATE_FAILED or DELETE_FAILED state
    """
    conn = openstack.connect(cloud='overcloud')
    print("Collecting a list of stacks left in CREATE_FAILED "
          "or DELETE_FAILED state")
    failed_stack_list = []
    for stack in conn.orchestration.stacks():
        if "FAILED" in stack['status']:
            failed_stack_list.append(stack["name"])
    print(f"Stacks which are i.e `CREATE_FAILED` or `DELETE_FAILED` state: {failed_stack_list}")
    return failed_stack_list


def servers_with_identifier(identifier):
    """ This function fetches list of servers that have a particular
        text(identifier) in their name. If there are no servers with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud='overcloud')
    server_list = []
    for server in conn.compute.servers():
        if identifier in server['name']:
            server_list.append(server['id'])
        else:
            for network in server['addresses']:
                if identifier in network:
                    server_list.append(server['id'])
    return server_list


def server_delete(server_names, dry_run=False):
    """ This function takes a list of servers and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud='overcloud')
    if server_names:
        if dry_run:
            print("DRY RUN - Servers to delete: %s", server_names)
        else:
            for server in server_names:
                print("Deleting server ID %s", server)
                conn.compute.delete_server(server)
    else:
        print("There are no servers to delete")


def subnets_with_identifier(identifier):
    """ For every heat stack multiple subnets are created, This
        function fetches list of all the subnets which have
        text(identifier) in name.
    """
    conn = openstack.connect(cloud='overcloud')
    subnet_with_identifier_list = []
    for subnet in conn.network.subnets():
        if subnet['name'].endswith(identifier):
            subnet_with_identifier_list.append(subnet['id'])
    print("Subnets with identifier: %s", subnet_with_identifier_list)
    return subnet_with_identifier_list


def ports_of_subnets(subnet_ids_list):
    """ This functions takes list of subnet ids as input and fetches
        list of all the ports belongs to those subnets.
    """
    conn = openstack.connect(cloud='overcloud')
    port_list = []
    if subnet_ids_list:
        for subnet in subnet_ids_list:
            for port in conn.network.get_subnet_ports(subnet):
                port_list.append(port['id'])
    return port_list


def port_delete(port_ids, dry_run=False):
    """ This function takes a list of ports and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud='overcloud')
    if port_ids:
        if dry_run:
            print("DRY RUN - Ports to delete: %s", port_ids)
        else:
            for port in port_ids:
                print("Deleting port ID %s", port)
                conn.network.delete_port(port)
    else:
        print("There are no ports to delete")


def networks_with_identifier(identifier):
    """ This function fetches list of networks that have a particular
        text(identifier) in their name. If there are no networks with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud='overcloud')
    network_list = []
    for network in conn.network.networks():
        if network['name'].endswith(identifier):
            network_list.append(network['id'])
    return network_list


def network_delete(network_ids, dry_run=False):
    """ This function takes a list of networks and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud='overcloud')
    if network_ids:
        if dry_run:
            print("DRY RUN - Networks to delete: %s", network_ids)
        else:
            for network_id in network_ids:
                print("Deleting network ID %s", network_id)
                conn.network.delete_network(network_id)
    else:
        print("There are no networks to delete")


def routers_with_identifier(identifier):
    """ This function fetches list of routers that have a particular
        text(identifier) in their name. If there are no router with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud='overcloud')
    router_list = []
    for router in conn.network.routers():
        if identifier in router['name']:
            router_list.append(router['id'])
    return router_list


def router_delete(router_ids, dry_run=False):
    """ This function takes a list of routers and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud='overcloud')
    if router_ids:
        if dry_run:
            print("DRY RUN - Routers to delete: %s", router_ids)
        else:
            for router_id in router_ids:
                print("Deleting router ID %s", router_id)
                conn.network.delete_router(router_id)
    else:
        print("There are no router to delete")


def sec_gp_with_identifier(identifier):
    """ This function fetches list of security group that have a particular
        text(identifier) in their name. If there are no security group with
        text(identifier) in their name it returns an empty list.
    """
    conn = openstack.connect(cloud='overcloud')
    security_group = []
    for sec_group in conn.network.security_groups():
        if identifier in sec_group['name']:
            security_group.append(sec_group['id'])
    return security_group

def sec_group_delete(sec_group_ids, dry_run=False):
    """ This function takes a list of security group and delete them if dry_run
        is False.
    """
    conn = openstack.connect(cloud='overcloud')
    if sec_group_ids:
        if dry_run:
            print("DRY RUN - Security group to delete: %s", sec_group_ids)
        else:
            for sec_group_id in sec_group_ids:
                print("Deleting Security group with ID %s", sec_group_id)
                conn.network.delete_security_group(sec_group_id)
    else:
        print("There are no Security group to delete")

def delete_individual_resources(stack_list, prefix, suffix, dry_run):
    """ This function takes a list of heat stack which failed to create
        or delete successfully. It then deletes the individual resources
        (including instances, ports, security group and networks) of that
        heat stack.
    """
    if stack_list == []:
        print("There are no stacks to delete, exiting script.")
        sys.exit()
    else:
        print("There are stacks in CREATE_FAILED "
                    "or DELETE_FAILED state - %s", stack_list)

        for stack in stack_list:
            # Extract identfier for associated resources
            print("Removing individual resources which are associated "
                        "with stack %s", stack)
            identifier = fetch_identifier(stack, prefix, suffix)
            print(f"prefix: {prefix}")
            fetched_servers = servers_with_identifier(identifier)
            server_delete(fetched_servers, dry_run)
            # delete empty ports associated with subnets and then networkso
            fetched_subnets_list = subnets_with_identifier(identifier)
            fetched_subnet_ports = ports_of_subnets(fetched_subnets_list)
            port_delete(fetched_subnet_ports, dry_run)
            fetched_networks = networks_with_identifier(identifier)
            network_delete(fetched_networks, dry_run)
            fetched_routers = routers_with_identifier(identifier)
            router_delete(fetched_routers, dry_run)
            fetched_sec_groups = sec_gp_with_identifier(identifier)
            sec_group_delete(fetched_sec_groups, dry_run)

def main(time_expired=300, dry_run=False, prefix="baremetal_", suffix=""):
    """ This is the main function called when script is executed.
        It first checks if cloud is accessible, then it fetches
        list of heat stack to be deleted depending on inputs.
        This function first tries to delete the heat stack, if it
        cannot delete the heat stack, it removes the associated resources of
        heat stack and tries to delete it again.
    """
    if not env_accessibility_check():
        sys.exit()
    old_stack_list = old_heat_stacks(time_expired)
    stack_delete(old_stack_list, dry_run)
    failed_stack_list = failed_heat_stacks()
    stack_delete(failed_stack_list, dry_run)
    if not dry_run:
        print("Waiting for 150s for stacks to delete ")
        # wait for 150s
        time.sleep(150)
    #  Check if there are stacks left in CREATE_FAILED or DELETE_FAILED state
    print("Rechecking if there are stacks left in CREATE_FAILED or DELETE_FAILED state")
    failed_stack_list = failed_heat_stacks()
    delete_individual_resources(failed_stack_list, prefix, suffix, dry_run)
    stack_delete(failed_stack_list, dry_run)
    if not dry_run:
        # wait for 150s
        time.sleep(150)
    # Recheck if there are stacks left in CREATE_FAILED or DELETE_FAILED state
    failed_stack_list = failed_heat_stacks()
    if len(failed_stack_list) == 0:
        print("Script ran successfully: No Heat stack in failed state")
    else:
        print("Script didn't executed Successfully, Manual intervention "
              "needed for following stacks %s", failed_stack_list)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OVB Stale resources cleanup"
                                     "script for vexxhost/psi cloud")
    parser.add_argument('-t',
                        '--time-expired',
                        type=int,
                        metavar='',
                        default=300,
                        help='Time, in minutes, a stack has been running when it will '
                        'be deleted. It is used with the long-running option. '
                        'Defaults to 300 minutes (5 hours)')

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
                        help='Stack name prefix added before the stack unique identifer.'
                        ' Default is baremetal_ ')

    parser.add_argument('-s',
                        '--suffix',
                        metavar='',
                        default='',
                        help='Stack name suffix added after the stack unique identifer. '
                        'Default is an empty string.')

    args = parser.parse_args()

    main(time_expired=args.time_expired,
         prefix=args.prefix,
         suffix=args.suffix,
         dry_run=args.dry_run)
