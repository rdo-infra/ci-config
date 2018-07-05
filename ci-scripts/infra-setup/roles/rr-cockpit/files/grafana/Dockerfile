FROM grafana/grafana:5.2.1

COPY dashboards-provider.yaml /etc/grafana/provisioning/dashboards/
COPY *dashboard*.json /etc/grafana/provisioning/dashboards/
COPY datasources.yml  /etc/grafana/provisioning/datasources/

WORKDIR /
ENTRYPOINT [ "/run.sh" ]
