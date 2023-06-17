# -*- coding: utf-8 -*-
import ast
import os
import re

from setuptools import find_packages, setup

# parse version from pynetem/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')
_init_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "pynetem", "__init__.py")
with open(_init_file, 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))
filepath = 'README.md'

setup(
    name='pynetem',
    version=version,
    description="PyNetem is a tool that allow the user to limit the bandwidth or simulate weak network.",
    long_description=open(filepath, encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Topic :: Software Development :: Testing",
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: POSIX",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
    ],
    keywords='',
    author='Guo Tengda',
    author_email='ttguotengda@foxmail.com',
    url='https://github.com/GuoTengda1993/pynetem',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=["netifaces>=0.10.0", "flask>=1.0.0", "paramiko>=1.7.0.0"],
    test_suite="",
    tests_require=[],
    entry_points={
        'console_scripts': [
            'pynetem = pynetem.main:main',
        ]
    },
    data_files=[filepath]
)
