FROM quay.io/centos/centos:stream9

RUN dnf clean all && dnf update -y  && dnf install -y \
                        python3 \
                        python3-pip \
                        python3-setuptools

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

CMD ["telegraf", "--debug", "--config-directory","/etc/telegraf/telegraf.d/","--input-filter", "exec"]
