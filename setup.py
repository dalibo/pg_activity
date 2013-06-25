import sys

# Dirty work around destinated to deactivate
# manual page install when option --no-man is given
data_files = [ ('/usr/share/man/man1', ['docs/man/pg_activity.1']) ]
for opt in sys.argv:
    if opt == '--no-man':
        data_files = None
        sys.argv.remove(opt)

from setuptools import setup

if sys.version_info < (2, 6):
    raise SystemExit('ERROR: pg_activity need at least python 2.6 to work.')

setup(
    name = 'pg_activity',
    version = '1.0.2',
    author = 'Julien Tachoires',
    author_email = 'julmon@gmail.com',
    scripts = ['bin/pg_activity'],
    url = 'https://github.com/julmon/pg_activity',
    license = 'LICENSE.txt',
    description = 'htop like utility for PostgreSQL activity monitoring.',
    install_requires = [
        "psutil >= 0.4.1",
        "psycopg2 >= 2.2.1",
    ],
    data_files = data_files,
)
