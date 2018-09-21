#!/bin/env python3

# Copyright 2018, Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# TODO: implements heat stack wipe


import shade
import time
import json
import kazoo.client
import os.path
import argparse

parser = argparse.ArgumentParser()

parser = argparse.ArgumentParser(description='Cloud provider wiper')
parser.add_argument(
    '--skip-zookeeper', action='store_true', default=False,
    help="Do not attempt to clean the nodepool's zookeeeper")
parser.add_argument(
    '--skip-volumes', action='store_true', default=False,
    help="Do not attempt to clean tenant volume")
parser.add_argument(
    '--os-cloud', type=str,
    help="Cloud name as in clouds.yaml")
parser.add_argument(
    '--servers-to-exclude', type=str, default="",
    help="Comma separated list of servers to exclude." +
         "Attached ports and volumes will be excluded too.")

args = parser.parse_args()

servers_to_exclude = args.servers_to_exclude.split(',')
servers_to_exclude_objs = []

input("Press enter to continue - We are going to discover resources to wipe")

# Get tenant resources
cloud = shade.openstack_cloud(cloud=args.os_cloud)
servers = cloud.list_servers()
ports = cloud.list_ports()
if args.skip_volumes:
    volumes = cloud.list_volumes()
router = cloud.list_routers()[0]
router_interface = cloud.list_router_interfaces(router)[0]

# remove excluded servers from the servers list
for server_excluded in servers_to_exclude:
    servers_to_exclude_objs.append(
        list(filter(lambda x: x['name'] == server_excluded, servers))[0])
servers = list(filter(lambda x: x["name"] not in servers_to_exclude, servers))

if args.volumes:
    # Remove excluded server volume from volumes list
    for server_excluded in servers_to_exclude:
        volumes = list(
                    filter(
                        lambda x: x['id'] != server_excluded[
                            'volumes'][0]['id'],
                        volumes))

# Remove excluded server port from ports list
for server_excluded in servers_to_exclude:
    ports = list(
        filter(
            lambda x: x['fixed_ips'][0]['ip_address'] != server_excluded[
                'addresses']['private'][0]['addr'],
            ports))

# Remove router from ports list
ports = list(
    filter(
        lambda x: x['fixed_ips'][0]['ip_address'] != router_interface[
            'fixed_ips'][0]['ip_address'],
        ports))

# Remove ACTIVE port - Only keep DOWN port
ports = list(filter(lambda x: x['status'] != 'ACTIVE', ports))

if not args.skip_zookeeper:
    # Kazoo - get zookeeper nodes
    client = kazoo.client.KazooClient(hosts="zookeeper")
    client.start()

    kz_to_delete = []
    for node in client.get_children("/nodepool/nodes"):
        node_path = os.path.join("/nodepool/nodes", node)
        node_data = client.get(node_path)[0].decode('utf-8')
        try:
            node = json.loads(node_data)
        except:
            print("%s: decode failed" % node_path)
            if not node_data:
                print("Deleting empty %s" % node_path)
                client.delete(node_path, recursive=True)
            else:
                print(node_data)
            continue
        if node["provider"] != args.os_cloud:
            continue
        kz_to_delete.append(node_path)

    print("%d zookeeper node" % len(kz_to_delete))

if not args.skip_volumes:
    print("%d volumes" % len(volumes))

print("%d servers, %d ports" % (len(servers), len(ports)))

input("Press enter to continue - Resources are going to be deleted")

if not args.skip_zookeeper:
    for kz_node in kz_to_delete:
        print("%s: deleting" % kz_node)
        client.delete(kz_node, recursive=True)

for server in servers:
    print("%s: deleting instance %s" % (server['id'], server['name']))
    try:
        if not cloud.delete_server(server['id']):
            print("delete failed")
    except Exception as e:
        print('couldnt delete...', e)
    time.sleep(0.5)

for port in ports:
    print("%s: deleting port" % port['id'])
    try:
        if not cloud.delete_port(port['id']):
            print("delete failed")
    except Exception as e:
        print('couldnt delete...', e)
    time.sleep(0.5)

if not args.skip_volumes:
    for volume in volumes:
        print("%s: deleting volume" % volume['id'])
        try:
            if not cloud.delete_volume(volume['id']):
                print("delete failed")
        except Exception as e:
            print('couldnt delete...', e)
        time.sleep(0.5)

print("%d servers remaining" % len(cloud.list_servers()))
print("%d ports remaining" % len(cloud.list_ports()))
if not args.skip_volumes:
    print("%d volumes remaining" % len(cloud.list_volumes()))
