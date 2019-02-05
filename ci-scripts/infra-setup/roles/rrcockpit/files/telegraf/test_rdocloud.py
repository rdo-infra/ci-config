import rdocloud

def test_with_server_and_stack_and_quota():
    servers = {
        "ACTIVE":293,
        "BUILD":2,
        "ERROR":11,
        "DELETED":0,
        "undercloud":17,
        "multinode":1,
        "bmc":50,
        "ovb-node":197,
        "other":55,
        "total":320
    }
    stacks = {
        "stacks_total": 99,
        "create_complete": 50,
        "create_failed": 6,
        "create_in_progress": 0,
        "delete_in_progress": 0,
        "delete_failed": 43,
        "delete_complete": 0,
        "old_stacks": 0
    }
    quotes = {
        "instances": 318,
        "cores": 1443,
        "ram": 2390016,
        "gbs": 158,
        "fips": 63,
        "ports_down":1249
    }
    expected='''rdocloud-servers ACTIVE=293,BUILD=2,ERROR=11,DELETED=0,undercloud=17,multinode=1,bmc=50,ovb-node=197,other=55,total=320,stacks_total=99,create_complete=50,create_failed=6,create_in_progress=0,delete_in_progress=0,delete_failed=43,delete_complete=0,old_stacks=0 1549374336000000000
rdocloud-perf instances=318,cores=1443,ram=2390016,gigabytes=158,fips=63,ports_down=1249 1549374336000000000
'''

    obtained = rdocloud.compose_influxdb_data(servers=servers, quotes=quotes, stacks=stacks, fips=63, ports_down=1249, ts=1549374336)

    assert(expected == obtained)

def test_with_server_and_quote():
    servers = {
        "ACTIVE":293,
        "BUILD":2,
        "ERROR":11,
        "DELETED":0,
        "undercloud":17,
        "multinode":1,
        "bmc":50,
        "ovb-node":197,
        "other":55,
        "total":320
    }
    stacks = None
    quotes = {
        "instances": 318,
        "cores": 1443,
        "ram": 2390016,
        "gbs": 158,
        "fips": 63,
        "ports_down":1249
    }
    expected='''rdocloud-servers ACTIVE=293,BUILD=2,ERROR=11,DELETED=0,undercloud=17,multinode=1,bmc=50,ovb-node=197,other=55,total=320 1549374336000000000
rdocloud-perf instances=318,cores=1443,ram=2390016,gigabytes=158,fips=63,ports_down=1249 1549374336000000000
'''

    obtained = rdocloud.compose_influxdb_data(servers=servers, quotes=quotes, stacks=stacks, fips=63, ports_down=1249, ts=1549374336)

    assert(expected == obtained)


def test_with_stack_and_quota():
    servers = None
    stacks = {
        "stacks_total": 99,
        "create_complete": 50,
        "create_failed": 6,
        "create_in_progress": 0,
        "delete_in_progress": 0,
        "delete_failed": 43,
        "delete_complete": 0,
        "old_stacks": 0
    }
    quotes = {
        "instances": 318,
        "cores": 1443,
        "ram": 2390016,
        "gbs": 158,
        "fips": 63,
        "ports_down":1249
    }
    expected='''rdocloud-servers stacks_total=99,create_complete=50,create_failed=6,create_in_progress=0,delete_in_progress=0,delete_failed=43,delete_complete=0,old_stacks=0 1549374336000000000
rdocloud-perf instances=318,cores=1443,ram=2390016,gigabytes=158,fips=63,ports_down=1249 1549374336000000000
'''

    obtained = rdocloud.compose_influxdb_data(servers=servers, quotes=quotes, stacks=stacks, fips=63, ports_down=1249, ts=1549374336)

    assert(expected == obtained)



def test_with_only_quote():
    servers = None
    stacks = None
    quotes = {
        "instances": 318,
        "cores": 1443,
        "ram": 2390016,
        "gbs": 158,
        "fips": 63,
        "ports_down":1249
    }
    expected='''rdocloud-perf instances=318,cores=1443,ram=2390016,gigabytes=158,fips=63,ports_down=1249 1549374336000000000
'''

    obtained = rdocloud.compose_influxdb_data(servers=servers, quotes=quotes, stacks=stacks, fips=63, ports_down=1249, ts=1549374336)

    assert(expected == obtained)

def test_without_quote():
    servers = {
        "ACTIVE":293,
        "BUILD":2,
        "ERROR":11,
        "DELETED":0,
        "undercloud":17,
        "multinode":1,
        "bmc":50,
        "ovb-node":197,
        "other":55,
        "total":320
    }
    stacks = {
        "stacks_total": 99,
        "create_complete": 50,
        "create_failed": 6,
        "create_in_progress": 0,
        "delete_in_progress": 0,
        "delete_failed": 43,
        "delete_complete": 0,
        "old_stacks": 0
    }
    quotes = None
    expected='''rdocloud-servers ACTIVE=293,BUILD=2,ERROR=11,DELETED=0,undercloud=17,multinode=1,bmc=50,ovb-node=197,other=55,total=320,stacks_total=99,create_complete=50,create_failed=6,create_in_progress=0,delete_in_progress=0,delete_failed=43,delete_complete=0,old_stacks=0 1549374336000000000
'''

    obtained = rdocloud.compose_influxdb_data(servers=servers, quotes=quotes, stacks=stacks, fips=63, ports_down=1249, ts=1549374336)

    assert(expected == obtained)


