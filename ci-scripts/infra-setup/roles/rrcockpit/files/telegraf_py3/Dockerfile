FROM centos:8

#ENV TG_GERRIT_SERVICE_USER ${GERRIT_SERVICE_USER}
#ENV TG_GERRIT_SERVICE_PASSWORD ${GERRIT_SERVICE_PASSWORD}

RUN dnf clean all && dnf update -y  && dnf install -y \
                        python3 \
                        python3-pip \
                        python3-setuptools \
                        python3-wheel


COPY requirements.txt /

COPY .netrc /root/
COPY .gertty.yaml /root/

RUN chmod 0600 $HOME/.netrc

COPY influxdb.repo /etc/yum.repos.d/influxdb.repo

RUN dnf -y install telegraf

RUN pip3 install -r requirements.txt

COPY telegraf.conf /etc/telegraf/telegraf.conf
COPY telegraf.d/* /etc/telegraf/telegraf.d/
COPY *.py /usr/local/bin/
COPY gri /usr/local/bin/
COPY setup_netrc.sh /tmp

COPY entrypoint.sh /
ENTRYPOINT ["./entrypoint.sh"]
