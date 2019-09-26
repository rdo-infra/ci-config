
FILE_STORAGE = "/tmp/logscache/"
LOG_FILE = "comparator.log"
DATA = {
    'oooq': 'ara.json',
    'undercloud': 'ara.oooq.root.json',
    'overcloud': 'ara.oooq.oc.json'
}

SQLITE_FILES = {
    'oooq': 'non-exist',
    'undercloud': 'ara_oooq_root/ara-report/ansible.sqlite',
    'overcloud': 'ara_oooq_overcloud/ara-report/ansible.sqlite'
}
RPM_LOC = 'undercloud/var/log/extra/rpm-list.txt.gz'
PIP_LOC = 'undercloud/var/log/extra/pip.txt.gz'
