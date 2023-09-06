FROM quay.io/centos/centos:stream8

RUN dnf clean all && dnf update -y  && dnf install -y \
                        python3 \
                        python3-devel \
                        python3-pip \
                        python3-setuptools \
                        krb5-devel \
                        gcc

COPY requirements.txt /
COPY influxdb.repo /etc/yum.repos.d/influxdb.repo

RUN dnf -y install telegraf

RUN pip3 install -r requirements.txt

COPY telegraf.conf /etc/telegraf/telegraf.conf
COPY telegraf.d/* /etc/telegraf/telegraf.d/
COPY *.py /usr/local/bin/
COPY *.yaml /usr/local/bin/
RUN mkdir -p /usr/local/bin/templates
COPY templates/* /usr/local/bin/templates/
RUN ln -s /usr/bin/python3 /usr/bin/python

# NOTE(dasm): Install RHEL certs inside the container
# If the command failed, ignore it by '|| true'
RUN cd /etc/pki/ca-trust/source/anchors && \
    curl -O https://password.corp.redhat.com/RH-IT-Root-CA.crt && \
    curl -O https://password.corp.redhat.com/pki-ca-chain.crt && \
    update-ca-trust extract && update-ca-trust enable || true

CMD ["telegraf", "--debug", "--config-directory", "/etc/telegraf/telegraf.d/", "--input-filter", "exec"]
