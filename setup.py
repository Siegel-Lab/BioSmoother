from distutils.core import setup
import os
from setuptools import find_packages
import subprocess

VERSION = "0.5.0"

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

def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths
extra_files = package_files('biosmoother')
print(extra_files)

setup(
    name="biosmoother",
    version=VERSION,
    author='Markus Schmidt',
    author_email='markus.rainer.schmidt@gmail.com',
    license='MIT',
    url='https://github.com/Siegel-Lab/biosmoother',
    description="On-the-fly processing and visualization of contact mapping data",
    long_description="""
        On-the-fly processing and visualization of contact mapping data
    """,
    py_modules=["cli"],
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
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
    install_requires=[
        'libbiosmoother',
        'bokeh==2.3.2', # specific version is necessary for now -> with newer versions the layout starts glitching
        'psutil',
    ],
    entry_points={
        'console_scripts': [
            'biosmoother = cli:main',
        ],
    },
)