#!/bin/bash

V="0.2"

GIT_STATUS=$(git status -s)
if [ "${GIT_STATUS}" != "" ]
then
    echo -ne "Version: D-$V-" > VERSION
else
    echo -ne "Version: $V-" > VERSION
fi

git log -1 --format=%h-%ci | cut -d' ' -f1,2 --output-delimiter - >> VERSION
