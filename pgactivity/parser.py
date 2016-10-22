import os
import getpass
from optparse import OptionParser, OptionGroup

from pgactivity import __version__


# Customized OptionParser
class ModifiedOptionParser(OptionParser):
    """
    ModifiedOptionParser
    """
    def error(self, msg):
        raise OptionParsingError(msg)

class OptionParsingError(RuntimeError):
    """
    OptionParsingError
    """
    def __init__(self, msg):
        self.msg = msg

parser = ModifiedOptionParser(
    add_help_option = False,
    version = "%prog "+__version__,
    description = "htop like application for PostgreSQL \
server activity monitoring.")

# -U / --username
parser.add_option(
    '-U',
    '--username',
    dest = 'username',
    default = os.environ.get('PGUSER') or getpass.getuser(),
    help = "Database user name (default: \"%s\")."
        % (getpass.getuser(),),
    metavar = 'USERNAME')
# -p / --port
parser.add_option(
    '-p',
    '--port',
    dest = 'port',
    default = os.environ.get('PGPORT') or '5432',
    help = "Database server port (default: \"5432\").",
    metavar = 'PORT')
# -h / --host
parser.add_option(
    '-h',
    '--host',
    dest = 'host',
    help = "Database server host or socket directory \
                (default: \"localhost\").",
    metavar = 'HOSTNAME',
    default = os.environ.get('PGHOST') or 'localhost')
# -d / --dbname
parser.add_option(
    '-d',
    '--dbname',
    dest = 'dbname',
    help = "Database name to connect to (default: \"postgres\").",
    metavar = 'DBNAME',
    default = 'postgres')
# -C / --no-color
parser.add_option(
    '-C',
    '--no-color',
    dest = 'nocolor',
    action = 'store_true',
    help = "Disable color usage.",
    default = 'false')
# --blocksize
parser.add_option(
    '--blocksize',
    dest = 'blocksize',
    help = "Filesystem blocksize (default: 4096)",
    metavar = 'BLOCKSIZE',
    default = 4096)
# --rds
parser.add_option(
    '--rds',
    dest = 'rds',
    action = 'store_true',
    help = "Enable support for AWS RDS",
    default = 'false')
group = OptionGroup(
    parser,
    "Display Options, you can exclude some columns by using them ")
# --no-database
group.add_option(
    '--no-database',
    dest = 'nodb',
    action = 'store_true',
    help = "Disable DATABASE.",
    default = 'false')
# --no-user
group.add_option(
    '--no-user',
    dest = 'nouser',
    action = 'store_true',
    help = "Disable USER.",
    default = 'false')
# --no-client
group.add_option(
    '--no-client',
    dest = 'noclient',
    action = 'store_true',
    help = "Disable CLIENT.",
    default = 'false')
# --no-cpu
group.add_option(
    '--no-cpu',
    dest = 'nocpu',
    action = 'store_true',
    help = "Disable CPU%.",
    default = 'false')
# --no-mem
group.add_option(
    '--no-mem',
    dest = 'nomem',
    action = 'store_true',
    help = "Disable MEM%.",
    default = 'false')
# --no-read
group.add_option(
    '--no-read',
    dest = 'noread',
    action = 'store_true',
    help = "Disable READ/s.",
    default = 'false')
# --no-write
group.add_option(
    '--no-write',
    dest = 'nowrite',
    action = 'store_true',
    help = "Disable WRITE/s.",
    default = 'false')
# --no-time
group.add_option(
    '--no-time',
    dest = 'notime',
    action = 'store_true',
    help = "Disable TIME+.",
    default = 'false')
# --no-wait
group.add_option(
    '--no-wait',
    dest = 'nowait',
    action = 'store_true',
    help = "Disable W.",
    default = 'false')
parser.add_option_group(group)
# --help
parser.add_option(
    '--help',
    dest = 'help',
    action = 'store_true',
    help = "Show this help message and exit.",
    default = 'false')
# --debug
parser.add_option(
    '--debug',
    dest = 'debug',
    action = 'store_true',
    help = "Enable debug mode for traceback tracking.",
    default = 'false')