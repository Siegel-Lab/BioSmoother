from distutils.core import setup
import subprocess
from conf_version_file import conf_version

VERSION = "0.3.1"

# update version file...
conf_version("smoother/VERSION.in", VERSION, "smoother/VERSION")

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
    packages=["smoother"],
    include_package_data=True,
    extras_require={"test": "pytest"},
    zip_safe=False,
    python_requires=">=3.9",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
    ],
    install_requires=[
        'libsmoother @ git+https://github.com/Siegel-Lab/libSmoother@stable-latest',
        'bokeh==2.3.2', # specific version is necessary for now -> with newer versions the layout starts glitching
        'psutil',
    ],
    entry_points={
        'console_scripts': [
            'smoother = cli:main',
        ],
    },
)