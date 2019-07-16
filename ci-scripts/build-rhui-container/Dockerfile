FROM registry.access.redhat.com/ubi8/python-36

USER root

# TODO(ssbanrea): convince apevec to provide a permalink as we cannot afford
# updating this url manually:
RUN rm -Rf /etc/yum.repos.d/*
RUN dnf clean all
RUN yum install -y http://38.145.34.141/rcm-guest/rhui/rdo-rhui-2.1.1.noarch.rpm

# Workaround for producing an image where dnf still works as any modification
# made to /etc/hosts for adding rhui-cds is not persistent.

# Alternatives:
# a) run containers with --add-host rhui-cds:38.145.32.241
# b) add rhui-cds entry to the DNS server used by the docker host
# Both are not practical for use in various jobs, like molecule.

RUN sed -i 's/https:\/\/rhui-cds\//https:\/\/38.145.32.241\//g' /etc/yum.repos.d/*.repo
RUN sed -i 's/sslverify=1/sslverify=0/g' /etc/yum.repos.d/*.repo

RUN dnf makecache
RUN dnf --assumeyes install python3 sudo python3-devel python3-libselinux python3-dnf bash iputils bind-utils
RUN dnf -y update
RUN dnf clean all

CMD /bin/bash
# CMD ["sh", "-c", "while true; do sleep 10000; done"]
