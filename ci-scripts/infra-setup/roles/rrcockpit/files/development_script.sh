#!/bin/bash
set -euxo pipefail

# If not defined compose will use 'files' directory name
export COMPOSE_PROJECT_NAME=rrcockpit

usage()
{
    echo "usage: simple script to setup the cockpit"
    echo " -u, --url, return public URL"
    echo " -s, --start, fire it up "
    echo " -c, --clean, to stop and clean up containers"
    echo " -h, --help, usage"
}

start()
{

    # start up
    docker volume create telegraf-volume
    docker volume create grafana-volume
    docker volume create influxdb-volume
    docker volume create mariadb-volume

    # build is needed in order to avoid getting changes
    docker-compose up --build
}

url()
{
    IP=$(docker network inspect rrcockpit-public -f '{{ range .Containers }}{{ .IPv4Address }}{{ end }}' | sed 's/\/.*//')
    echo http://$IP
}

clean()
{
    # clean-up that should not affect other running containers
    docker-compose down
    docker system prune -a
}

if [ -z "${1:-}" ]; then
    usage
fi

while [ "${1:-}" != "" ]; do
    case $1 in
        -u | --url )            shift
                                url
                                ;;
        -s | --start )          shift
                                start
                                ;;
        -c | --clean )          clean
                                ;;
        -h | --help )           usage
                                exit
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done
