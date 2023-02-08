from distutils.core import setup
import os
from pathlib import Path
from distutils.dir_util import copy_tree

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
import site
import subprocess

with open("VERSION", "r") as in_file:
    VERSION = in_file.readline()

### taken from: https://github.com/pybind/cmake_example/blob/master/setup.py
# A BokehServer needs a sourcedir instead of a file list.
# The name must be the _single_ output extension from the CMake build.
# If you need multiple extensions, see scikit-build.
class BokehServer(Extension):
    def __init__(self, name: str, install_dir: str = "", sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.fspath(Path(sourcedir).resolve())
        self.install_dir = install_dir


class CopyFiles(build_ext):
    def build_extension(self, ext: BokehServer) -> None:
        subprocess.run([os.path.join(ext.sourcedir, 'bin/conf_version_file.sh'),
                        os.path.join(ext.sourcedir, "VERSION"), VERSION], timeout=10) 
        #print("XXXXXXX", ext.sourcedir, os.path.join(site.getsitepackages()[0], ext.install_dir))
        copy_tree(ext.sourcedir, os.path.join(site.getsitepackages()[0], ext.install_dir))

setup(
    name="smoother",
    version=VERSION,
    author='Markus Schmidt',
    author_email='markus.rainer.schmidt@gmail.com',
    license='MIT',
    url='https://github.com/Siegel-Lab/smoother',
    description="On-the-fly processing and visualization of contact mapping data",
    long_description="",
    py_modules=["cli"],
    ext_modules=[BokehServer("smoother", "smoother", "smoother")],
    cmdclass={"build_ext": CopyFiles},
    extras_require={"test": "pytest"},
    zip_safe=False,
    python_requires=">=3.5",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    install_requires=[
        'libsmoother @ git+https://github.com/Siegel-Lab/libSmoother',
        'bokeh==2.3.2', # specific version is necessary for now -> with newer versions the layout starts glitching
    ],
    entry_points={
        'console_scripts': [
            'smoother = cli:main',
        ],
    },
)