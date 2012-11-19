.. pg_activity documentation master file, created by
   sphinx-quickstart on Mon Nov 19 16:56:09 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

INTRO
=====

SYNOPSIS
--------

htop like application for PostgreSQL server activity monitoring.


DESCRIPTION
-----------

Description ...

COMMAND-LINE OPTIONS
--------------------

-U USERNAME, --username=USERNAME
                   	  	Database user name (default: "postgres").
-p PORT, --port=PORT  	Database server port (default: "5432").
-h HOSTNAME, --host=HOSTNAME
						Database server host or socket directory (default: "local socket").
-C, --no-color      	Disable color usage.
--help	              	Show this help message and exit.

DISPLAY OPTIONS
---------------

--no-database         	Disable DATABASE.
--no-client           	Disable CLIENT.
--no-cpu              	Disable CPU%.
--no-mem              	Disable MEM%.
--no-read             	Disable READ/s.
--no-write            	Disable WRITE/s.
--no-time             	Disable TIME+.
--no-wait             	Disable W.

INTERACTIVE COMMANDS
--------------------

**C**	
	Activate/deactivate colors.

**r**
	Sort by READ/s, descending.

**w**
	Sort by WRITE/s, descending.

**c**
	Sort by CPU%, descending.

**m**
	Sort by MEM%, descending.

**t**
	Sort by TIME+, descending.

**Space**
	Pause on/off.

EXAMPLES
--------

PGPASSWORD='mypassword' pg_activity -U pgadmin -h 127.0.0.1 --no-client -C
	
pg_activity -h /tmp

