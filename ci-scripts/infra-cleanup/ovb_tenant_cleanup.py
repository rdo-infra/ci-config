#!/usr/bin/env python
"""
This is a cleanup script for rdo/vexxhost cloud.
To test openstack deployment on ovb jobs, on rdo/vexxhost cloud a heat
stack is created.
Normally, Heat stack is created and destroyed by job itself.
But, sometimes due to infra related issues heat stack failed to
create/delete by job itself.
In a scenario where heat stack is not deleted by job itself, We need manual
cleanup on Infrastrusture to avoid resource constraint.
"""

import ast
import datetime
import subprocess
import sys
import click


class PythonLiteralOption(click.Option):
    """ To pass several list of arguments to @click.option.
        This class will use Python's Abstract Syntax Tree module
        to parse the parameter as a python literal.
        We inherit from click.Option in our own class and override
        the methods click.Option.type_cast_value() and then call
        ast.literal_eval() to parse the list.
    """
    def type_cast_value(self, ctx, value):
        try:
            return ast.literal_eval(value)
        except Exception:
            raise click.BadParameter(value) from None


def env_accessibility_check():
    """ This function checks if cloud is accessible """
    completed = subprocess.run(['openstack', 'token', 'issue'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True)

    if completed.returncode != 0:
        print(completed.stderr.decode('utf-8'))
        print("ERROR: Failed to talk with cloud, credentials should be"
              " sourced or configured in cloud.yaml file.")
        sys.exit()
    print("Successfull able to talk with cloud")


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
    return remove_suffix(text, suffix)


def heat_stacks(time_expired, prefix, nuclear):
    """ This function fetches list of heat stacks.
        If nuclear is True, this function returns list of all heat stacks.
        If nuclear is False, it returns list  of all stacks which are starting
        with prefix and running longer than time_expired minutes.
    """
    if nuclear:
        print("INFO: Collecting a list of all available Heat stacks ...")
        return subprocess.run(
                """openstack stack list -f json | jq -r '.[]| .["ID"]'""",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                shell=True).stdout.decode('utf-8').split()

    print("INFO: Collecting a list of Heat stacks which are older than "
          "{} minutes".format(time_expired))
    utc_current_time = datetime.datetime.now(datetime.timezone.utc)
    utc_time_expired = (utc_current_time
                        - datetime.timedelta(minutes=time_expired))
    utc_time_expired = utc_time_expired.strftime("%Y-%m-%dT%H:%M:%SZ")

    command = f"""openstack stack list -f json | jq --arg date_time_expired {
                  utc_time_expired} --arg IDENTIFIER "{
                  prefix}" -r '.[]| select(.[
                  "Creation Time"] <= $date_time_expired) | select(.[
                  "Stack Name"] | contains($IDENTIFIER)) | .["ID"]'"""
    return subprocess.run("{}".format(command),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          check=True,
                          shell=True).stdout.decode('utf-8').split()


def failed_heat_stacks():
    """ This function fetches list of all heat stacks that are in i.e
        CREATE_FAILED or DELETE_FAILED state
    """
    print("INFO: Collecting a list of stacks left in CREATE_FAILED "
          "or DELETE_FAILED state")
    command = ("""openstack stack list -f json | jq -r '.[] | """
               """select(.["Stack Status"] |test("(CREATE|DELETE)_FAILED"))"""
               """ | .["Stack Name"]'""")
    return subprocess.run("{}".format(command),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          check=True,
                          shell=True).stdout.decode('utf-8').split()


def stack_delete(stack_list, dry_run):
    """ This function takes a list of heat stacks and delete them if dry_run
        is False. For each stack deletion this function waits till stack is
        deleted. This would avoid overwhelming the tenant with mass delete.
    """
    if stack_list:
        if dry_run:
            print("INFO: DRY RUN - Stack list to "
                  "delete: {}".format(stack_list))
        else:
            for stack in stack_list:
                print("INFO: Deleting stack id {}".format(stack))
                subprocess.run(['openstack', 'stack', 'delete', '-y',
                               '--wait', stack],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True)
    else:
        print("INFO: There are no stack to delete")


def servers_with_identifier(identifier):
    """ This function fetches list of servers that have a particular
        text(identifier) in their name. If there are no servers with
        text(identifier) in their name it returns an empty list.
    """
    command = ("""openstack server list -f json |  jq -r --arg IDENTIFIER"""
               """ "-{}" '.[] | select(.["Name"] | contains($IDENTIFIER))"""
               """ | .["ID"]'""".format(identifier))
    completed = subprocess.run("{}".format(command),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True,
                               shell=True)
    return completed.stdout.decode('utf-8').split()


def reset_server_state(server_uuid):
    """ This function check for instance current status and reset instance
        state to active if its in error state.
    """
    print("INFO: Resetting state of server: {}".format(server_uuid))
    status = subprocess.run("openstack server show {} -f json"
                            " | jq '.status'".format(server_uuid),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True,
                            shell=True).stdout.decode('utf-8').rstrip()
    if status == '"ERROR"':
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
            print("DRY RUN - Servers to delete: {}".format(server_names))
        else:
            for server in server_names:
                reset_server_state(server)
                print("INFO: Deleting server ID {}".format(server))
                subprocess.run(['openstack', 'server', 'delete', server],
                               check=True)
    else:
        print("INFO: There are no servers to delete")


def subnet_port_with_identifier(identifier):
    """ For every heat stack multiple subnets are created, This
        function fetches list of all the ports associated with all the
        subnets which have text(identifier) in name.
    """
    port_subnet_ids = []
    command_to_get_subnet_ids = ("""openstack subnet list -f json |  jq -r """
                                 """--arg IDENTIFIER "-{}" '.[] | """
                                 """select(.["Name"] | endswith($IDENTIFIER"""
                                 """)) | .["ID"]'""".format(identifier))
    subnet_ids = subprocess.run("{}".format(command_to_get_subnet_ids),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                check=True,
                                shell=True).stdout.decode('utf-8').split()
    for subnet_id in subnet_ids:
        command = ("""openstack port list -f json | jq -r --arg SUBNET_ID"""
                   """ "{}" '.[] | select(."Fixed IP Addresses" | .[] | """
                   """."subnet_id" == $SUBNET_ID)"""
                   """ | .["ID"]'""".format(subnet_id))
        port_id = subprocess.run("{}".format(command),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 check=True,
                                 shell=True).stdout.decode('utf-8').split()
        port_subnet_ids.extend(port_id)
    return port_subnet_ids


def port_delete(port_ids, dry_run):
    """ This function takes a list of ports and delete them if dry_run
        is False.
    """
    if port_ids:
        if dry_run:
            print("INFO: DRY RUN - Ports to delete: {}".format(port_ids))
        else:
            for port in port_ids:
                print("INFO: Deleting port ID {}".format(port))
                subprocess.run(['openstack', 'port', 'delete', port],
                               check=True)
    else:
        print("INFO: There are no ports to delete")


def networks_with_identifier(identifier):
    """ This function fetches list of networks that have a particular
        text(identifier) in their name. If there are no networks with
        text(identifier) in their name it returns an empty list.
    """
    command = ("""openstack network list -f json |  jq -r --arg IDENTIFIER"""
               """ "-{}" '.[] | select(.["Name"] | endswith($IDENTIFIER))"""
               """ | .["ID"]'""".format(identifier))
    completed = subprocess.run("{}".format(command),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               check=True,
                               shell=True)
    return completed.stdout.decode('utf-8').split()


def network_delete(network_ids, dry_run):
    """ This function takes a list of networks and delete them if dry_run
        is False.
    """
    if network_ids:
        if dry_run:
            print("INFO: DRY RUN - Networks to delete: {}".format(network_ids))
        else:
            for network_id in network_ids:
                print("INFO: Deleting network ID {}".format(network_id))
                subprocess.run(['openstack', 'network', 'delete', network_id],
                               check=True)
    else:
        print("INFO: There are no networks to delete")


def delete_individual_resources(stack_list_status, prefix, suffix, dry_run):
    """ This function takes a list of heat stack which failed to create
        or delete successfully. It then deletes the individual resources
        (including instances, ports, and networks) of that heat stack.
    """
    if stack_list_status == []:
        print("INFO: There are no stacks to delete, exiting script.")
        sys.exit()
    else:
        print("INFO: There are stacks in CREATE_FAILED",
              "or DELETE_FAILED state - {}".format(stack_list_status))
        print("INFO: Remove associated resources and then delete the stacks"
              " again.")

        for stack in stack_list_status:
            # Extract identfier for associated resources
            identifier = fetch_identifier(stack, prefix, suffix)
            print("INFO: Removing individual resources which are associated "
                  "with stack {}".format(stack))
            fetched_servers = servers_with_identifier(identifier)
            server_delete(fetched_servers, dry_run)
            # delete empty ports associated with subnets and then networks
            fetched_subnet_ports = subnet_port_with_identifier(identifier)
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
              cls=PythonLiteralOption,
              help='A list of stacks, and associated resources to delete. '
                   'Alternative to the long-running option. '
                   '**The stack list must be passed in quotes**',
              default='[]')
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
def main(time_expired, stack_list, nuclear, dry_run, prefix, suffix):
    """ This is the main function called when script is executed.
    """
    env_accessibility_check()
    stack_list = heat_stacks(time_expired, prefix, nuclear)
    stack_delete(stack_list, dry_run)
    #  Check if there are stacks left in CREATE_FAILED or DELETE_FAILED state
    stack_list_status = failed_heat_stacks()
    delete_individual_resources(stack_list_status, prefix, suffix, dry_run)
    stack_delete(stack_list_status, dry_run)


if __name__ == "__main__":
    main()
