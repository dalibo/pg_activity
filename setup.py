import sys

data_files = None
for opt in sys.argv:
    if opt == '--with-man':
        data_files = [ ('/usr/share/man/man1', ['docs/man/pg_activity.1']) ]
        sys.argv.remove(opt)

from setuptools import setup

if sys.version_info < (2, 6):
    raise SystemExit('ERROR: pg_activity need at least python 2.6 to work.')

setup(
    name = 'pg_activity',
    version = '1.3.1',
    author = 'Julien Tachoires',
    author_email = 'julmon@gmail.com',
    scripts = ['pg_activity'],
    packages = ['pgactivity'],
    url = 'https://github.com/julmon/pg_activity',
    license = 'LICENSE.txt',
    description = 'Command line tool for PostgreSQL server activity monitoring.',
    install_requires = [
        "psutil >= 0.4.1",
        "psycopg2 >= 2.2.1",
    ],
    data_files = data_files,
)
