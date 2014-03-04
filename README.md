pg_activity
===========

`htop` like application for **PostgreSQL** server activity monitoring.

Dependencies
------------

`python`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;>= **2.6**  
`psycopg2`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;>= **2.2.1**  
`psutil`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;>= **0.5.1**  
`setuptools` >= **0.6.14**  

Installation
------------

    sudo python setup.py install

### Installation without man pages

    sudo python setup.py install --no-man


Usage
-----

`pg_activity` can works **localy** or **remotely**. In a local execution context, to obtain sufficient rights to display system informations, the system user running `pg_activity` must be the same user running postgresql server (`postgres` by default), or have more rights like `root`. Otherwise, `pg_activity` can fallback to a degraded mode without displaying system informations. On the same way, the postgres' user used to connect to the database must have administration rights.  
ex:  
    
    sudo -u postgres pg_activity -U postgres

Options
-------

    pg_activity [options]

	Options:
		--version            Show program's version number and exit 
		-U USERNAME, --username=USERNAME
                        	  Database user name (default: "postgres").
		-p PORT, --port=PORT  Database server port (default: "5432").
		-h HOSTNAME, --host=HOSTNAME
							  Database server host or socket directory (default:
                        	  "localhost").
        -d DBNAME, --dbname=DBNAME
                              Database name to connect to (default: "postgres").
		-C, --no-color        Disable color usage.
		--help                Show this help message and exit.
		--debug               Enable debug mode for traceback tracking.
        --blocksize=BLOCKSIZE Filesystem blocksize (default: 4096).

	Display options, you can exclude some columns by using them :
		--no-database         Disable DATABASE.
    	--no-user             Disable USER.
    	--no-client           Disable CLIENT.
    	--no-cpu              Disable CPU%.
    	--no-mem              Disable MEM%.
    	--no-read             Disable READ/s.
    	--no-write            Disable WRITE/s.
    	--no-time             Disable TIME+.
    	--no-wait             Disable W.

Interactives commands
---------------------

`C`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Activate/deactivate colors  
`r`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sort by READ/s, descending  
`w`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sort by WRITE/s, descending  
`c`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sort by CPU%, descending  
`m`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sort by MEM%, descending  
`t`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sort by TIME+, descending  
`Space`		Pause on/off  
`v`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Change queries display mode: full, truncated, indented  
`UP/DOWN`	Scroll processes list  
`q`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Quit  
`+`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Increase refresh time. Maximum value : 3s  
`-`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Decrease refesh time. Minimum Value : 1s  
`F1/1`&nbsp;&nbsp;Running queries list  
`F2/2`&nbsp;&nbsp;Waiting queries list  
`F3/3`&nbsp;&nbsp;Blocking queries list  
`h`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Help page  
`R`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Refresh  

Navigation mode
---------------

`UP`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Move up the cursor  
`DOWN`&nbsp;&nbsp;&nbsp;Move down the cursor  
`k`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Terminate the current backend/tagged backends  
`Space`&nbsp;Tag or untag the process  
`q`&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Quit  
`Other`&nbsp;&nbsp;Back to activity  
			
Screenshot
----------

![pg_activity screenshot](https://raw.github.com/julmon/pg_activity/master/docs/imgs/screenshot.png)
