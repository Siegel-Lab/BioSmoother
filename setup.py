from distutils.core import setup
import os
from conf_version_file import conf_version
from setuptools import find_packages

VERSION = "0.3.1"

# update version file...
conf_version("VERSION.in", VERSION, "biosmoother/VERSION")


setup(
    name="biosmoother",
    version=VERSION,
    author='Markus Schmidt',
    author_email='markus.rainer.schmidt@gmail.com',
    license='MIT',
    url='https://github.com/Siegel-Lab/biosmoother',
    description="On-the-fly processing and visualization of contact mapping data",
    long_description="""
        # On-the-fly processing and visualization of contact mapping data
    """,
    py_modules=["cli"],
    packages=find_packages(where='.'),
    include_package_data=True,
    data_files=[("biosmoother", ["biosmoother/VERSION"])],
    extras_require={"test": "pytest"},
    zip_safe=False,
    python_requires=">=3.8",
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