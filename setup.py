from distutils.core import setup
import os
from setuptools import find_packages
import subprocess
# from libbiosmoother import open_descriptions_json
import json

VERSION = "1.6.0"

# conf version file
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

# update version file...
conf_version("VERSION.in", VERSION, "biosmoother/VERSION")

# configure tooltips_generated.css
def conf_tooltips(out_file_name):
    with open(out_file_name, "w") as out_file:
        def recursion(prefix, d):
            for k, v in d.items():
                if isinstance(v, dict):
                    recursion(prefix + "__" + k, v)
                else:
                    out_file.write(f".tooltip{prefix}__{k}::after {{ content: \"{v}\"; }}\n")

        with open("biosmoother/static/conf/descriptions.json", "r") as in_file:
            recursion("", json.load(in_file))

conf_tooltips("biosmoother/static/css/tooltips_generated.css")

def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths
extra_files = package_files('biosmoother')

setup(
    name="biosmoother",
    version=VERSION,
    author='Markus Schmidt',
    license='MIT',
    url='https://github.com/Siegel-Lab/biosmoother',
    description="On-the-fly processing and visualization of interactome data",
    long_description="""
BioSmoother performs on-the-fly analysis and visualization (filtering, normalization, downstream processing, and displaying) of interactome data (https://en.wikipedia.org/wiki/Chromosome_conformation_capture). See the GitHub repository for more information: https://github.com/Siegel-Lab/BioSmoother.

BioSmoother's documentation is available at https://biosmoother.rtfd.io/.
    """,
    py_modules=["biosmoother.cli"],
    packages=find_packages(where='.'),
    package_data={'biosmoother': extra_files},
    include_package_data=True,
    data_files=[("biosmoother", ["biosmoother/VERSION"])],
    extras_require={"test": "pytest"},
    zip_safe=False,
    python_requires=">=3.9",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
    install_requires=[
        'libbiosmoother>=1.6.2',
        'bokeh==2.3.2', # specific version is necessary for now -> with newer versions the layout starts glitching
        'psutil',
        'pybase64',
    ],
    entry_points={
        'console_scripts': [
            'biosmoother = biosmoother.cli:main',
        ],
    },
)
