from setuptools import setup, find_packages
from peakorc import run

setup (
    name = 'peakorc',
    version='0.1.0',
    description='Peak Orchestration API',
    url='https://github.com/peak-oss/peakorc',
    author='Peak Development Team',
    author_email='dev@peak-oss.tech',
    keywords='peak api testing containers docker',
    entry_points = {
        'console_scripts': [
            'peakorc = peakorc.run:main',
        ],
    },
    packages=find_packages(),
    install_requires=['falcon','peewee','psycopg2-binary','requests','numpy',
                      'subprocess32', 'gunicorn','rq']
)
