#!/bin/bash
set -exo pipefail

cd "$(dirname "$(realpath "$0")")"

DIR_DATA="$2"
PORT="$3"

if [ -z "$PORT" ]; then
    PORT="5000"
fi

if [ -z "$DIR_DATA" ]; then
    DIR_DATA=""
else
    DIR_DATA="-v $DIR_DATA:/srv/app"
fi

set -u
OPERATION="$1"

if [ "$OPERATION" == "build" ]; then
    sudo docker build -f Dockerfile -t esoadamo/http-db .
elif [ "$OPERATION" == "start" ]; then
    sudo docker rm -f http-db || true
    echo Starting interactive, to leave press CTRL + P, CTRL + Q
    sudo docker run -it --restart always --name http-db $DIR_DATA -p "$PORT":5000 esoadamo/http-db
elif [ "$OPERATION" == "delete" ]; then
    sudo docker rm -f http-db || true
    sudo docker rmi -f esoadamo/http-db || true
fi
