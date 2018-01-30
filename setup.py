from setuptools import setup, find_packages

setup (
    name = 'peakorc',
    version='0.1.0',
    description='Peak Orchestration API',
    url='https://github.com/peak-oss/peakorc',
    author='Peak Development Team',
    author_email='dev@peak-oss.tech',
    keywords='peak api testing containers docker',
    packages=find_packages(),
    install_requires=['falcon','peewee','psycopg2','requests','numpy']
)
