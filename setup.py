from distutils.core import setup

setup(
    name="smoother",
    version="0.1.0",
    author='Markus Schmidt',
    author_email='markus.rainer.schmidt@gmail.com',
    license='MIT',
    url='https://github.com/Siegel-Lab/smoother',
    description="On-the-fly processing and visualization of contact mapping data",
    long_description="",
    packages=["smoother"],
    extras_require={"test": "pytest"},
    data_files=[("data", ["data/default.json"])], # @todo
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
            'smoother = smoother.bin.cli:main',
        ],
    },
)