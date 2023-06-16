#!/usr/bin/env python

import subprocess
import sys
import os

def conf_version(in_file_name, cmake_version, out_file_name):
    def run_command(cmd):
        return subprocess.check_output(cmd)

    git_commit_hash="-".join(run_command(["git", "log", "-1", "--format=%h-%ci"]).decode().split()[:2])
    status_out = run_command(["git", "status", "-s"])
    if len(status_out) > 0:
        print("WARNING: building on dirty git repo", status_out)
        git_status="D-"
    else:
        git_status=""

    os.makedirs(os.path.dirname(out_file_name), exist_ok=True)

    # configure the new version file
    out_lines = []
    with open(in_file_name, "r") as in_file:
        for line in in_file.readlines():
            line = line.replace("@CMAKE_VERSION@", cmake_version)
            line = line.replace("@GIT_COMMIT_HASH@", git_commit_hash)
            line = line.replace("@GIT_STATUS@", git_status)
            out_lines.append(line)

    file_changed = False
    if not os.path.isfile(out_file_name):
        file_changed=True
    else:
        with open(out_file_name, "r") as in_file:
            lines = in_file.readlines()
            file_changed = lines == out_lines

    if file_changed:
        print("writing new version file")
        with open(out_file_name, "w") as out_file:
            for line in out_lines:
                out_file.write(line)

if __name__ == "__main__":
    conf_version(sys.argv[1], sys.argv[2], sys.argv[3])