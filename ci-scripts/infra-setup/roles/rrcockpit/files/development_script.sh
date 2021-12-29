#!/bin/bash
set -x

usage()
{
    echo "usage: simple script to setup the cockpit"
    echo " -s, --start, fire it up "
    echo " -c, --clean, to stop and clean up containers"
    echo " -h, --help, usage"
}

start()
{
    FILE=nginx.conf
    if [ ! -f "$FILE" ]; then
        cp -v nginx.conf.local nginx.conf
    fi
    # start up
    docker volume create telegraf-volume
    docker volume create grafana-volume
    docker volume create influxdb-volume
    docker volume create mariadb-volume
    docker-compose up
}

clean()
{
  # clean
    docker system prune -f
    running_containers=`docker ps -a --format="{{.ID}}"`
    for i in $running_containers; do
        echo $i;
        docker rm -f $i
    done
    sudo docker rmi -f $(sudo docker images -q)
}

if [ -z "$1" ]; then
    usage
fi

# do not run on production servers
if [[ $HOSTNAME == "incockpit" || $HOSTNAME == "rrcockpit.novalocal" ]]; then
    echo "do not run this script here"
    exit
fi

while [ "$1" != "" ]; do
    case $1 in
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
