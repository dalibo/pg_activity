pg_activity
===========

	PostgreSQL top like application for database activity monitoring.

Dependencies
------------

	Python >= 2.6
	psycopg2
	psutil

Usage
-----

	Options:
		-U USERNAME, --username=USERNAME
                        	  Database user name (default: "postgres").
		-p PORT, --port=PORT  Database server port (default: "5432").
		-h HOSTNAME, --host=HOSTNAME
							  Database server host or socket directory (default:
                        	  "local socket").
		-C, --no-color        Disable color usage.
		--help                Show this help message and exit.

	Display Options, you can exclude some columns by using them :
		--no-database         Disable DATABASE.
    	--no-client           Disable CLIENT.
    	--no-cpu              Disable CPU%.
    	--no-mem              Disable MEM%.
    	--no-read             Disable READ/s.
    	--no-write            Disable WRITE/s.
    	--no-time             Disable TIME+.
    	--no-wait             Disable W.

Screenshot
----------

	![pg_activity screenshot](screenshot.png)
