#!/bin/bash

V=$2

GIT_STATUS=$(git status -s)
if [ "${GIT_STATUS}" != "" ]
then
    echo -ne "Version: D-$V-" > $1
else
    echo -ne "Version: $V-" > $1
fi


git log -1 --format=%h-%ci | cut -d' ' -f1,2 --output-delimiter - >> $1
