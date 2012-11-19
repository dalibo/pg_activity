#from distutils.core import setup

from setuptools import setup
setup(
	name='pg_activity',
	version='0.1.0',
	author='Julien Tachoires',
	author_email='julmon@gmail.com',
	scripts=['bin/pg_activity'],
    url='https://github.com/julmon/pg_activity',
    license='LICENSE.txt',
    description='htop like utility for PostgreSQL activity monitoring.',
    long_description=open('README.txt').read(),
    install_requires=[
        "psutil >= 0.4.1",
        "psycopg2 >= 2.2.1",
    ],
)
