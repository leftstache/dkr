import os
from distutils.core import setup

def get_packages(root_dir):
    packages = []
    for root, dirs, files in os.walk(root_dir):
        if "__init__.py" in files:
            packages.append(root.replace('/', '.'))
    return packages


setup(
    name='dkr',
    version='0.0.1',
    author='Joel Johnson',
    author_email='joelj@joelj.com',
    packages=['dkr_core', 'commands'],
    scripts=['dkr'],
    data_files=['README.md'],
    url='https://github.com/leftstache/dkr',
    license='(c) 2016 Joel Johnson',
    description='Extendable alternative client for Docker',
    long_description=open('README.md').read(),
    install_requires=[
        'docker-py>=1.8.1',
        'tabulate>=0.7.5',
        'ansicolors>=1.0.2',
        'py-pretty>=1',
        'pyyaml>=3.11'
    ]
)