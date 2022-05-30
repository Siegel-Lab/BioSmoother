#!/bin/bash

echo -ne "0." > VERSION
git log -1 --format=%h >> VERSION