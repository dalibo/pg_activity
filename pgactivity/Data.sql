-- name : is_superuser?
-- Check if we are connected with the user with the SUPERUSER attribute
SELECT current_setting('is_superuser') AS is_superuser;

-- name : get_pid_file?
-- Get the path of the pidfile
SELECT setting||'/postmaster.pid' AS pid_file
  FROM pg_settings
 WHERE name = 'data_directory';

-- name : get_version?
-- Get the server's version
SELECT version() AS pg_version;

-- name : do_pg_terminate_backend?
-- Get the server's version
SELECT pg_terminate_backend(:pid) AS is_terminated;

-- name : do_pg_cancel_backend?
-- Get the server's version
SELECT pg_cancel_backend(:pid) AS is_cancelled;

-- name : get_db_info?
-- Get the database info
SELECT
      EXTRACT(EPOCH FROM NOW()) AS timestamp,
      SUM(pg_stat_get_db_xact_commit(oid)+pg_stat_get_db_xact_rollback(oid))::BIGINT AS no_xact,
      CASE
          WHEN :skip_db_size THEN :prev_total_size
          ELSE SUM(pg_database_size(datname))
      END AS total_size,
      MAX(LENGTH(datname)) AS max_length
  FROM pg_database
 WHERE datname <> 'rdsadmin' OR NOT :using_rds;

-- name : get_active_connections_90200?
-- Get active connections from pg_stat_activity for pg >= 9.2
SELECT COUNT(*) as active_connections
  FROM pg_stat_activity
 WHERE state = 'active';


-- name : get_active_connections?
-- Get active connections from pg_stat_activity prior to 9.2
SELECT COUNT(*) as active_connections
  FROM pg_stat_activity
 WHERE current_query NOT LIKE '<IDLE>%%';

-- name : get_pg_activity_110000
-- Get data from pg_activity since pg 11
SELECT
      pg_stat_activity.pid AS pid,
      pg_stat_activity.application_name AS application_name,
      CASE WHEN LENGTH(pg_stat_activity.datname) > 16
          THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
          ELSE pg_stat_activity.datname
      END AS database,
      CASE WHEN pg_stat_activity.client_addr IS NULL
          THEN 'local'
          ELSE pg_stat_activity.client_addr::TEXT
      END AS client,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      CASE WHEN pg_stat_activity.wait_event_type IN ('LWLock', 'Lock', 'BufferPin')
          THEN true
	  ELSE false
      END AS wait,
      pg_stat_activity.usename AS user,
      pg_stat_activity.state AS state,
      pg_stat_activity.query AS query,
      pg_stat_activity.backend_type = 'parallel worker' AS is_parallel_worker
 FROM
      pg_stat_activity
 WHERE
      state <> 'idle'
  AND pid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;

-- name : get_pg_activity_100000
-- Get data from pg_activity for pg 10
SELECT
      pg_stat_activity.pid AS pid,
      pg_stat_activity.application_name AS application_name,
      CASE WHEN LENGTH(pg_stat_activity.datname) > 16
          THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
          ELSE pg_stat_activity.datname
      END AS database,
      CASE WHEN pg_stat_activity.client_addr IS NULL
          THEN 'local'
          ELSE pg_stat_activity.client_addr::TEXT
      END AS client,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      CASE WHEN pg_stat_activity.wait_event_type IN ('LWLock', 'Lock', 'BufferPin')
          THEN true
	  ELSE false
      END AS wait,
      pg_stat_activity.usename AS user,
      pg_stat_activity.state AS state,
      pg_stat_activity.query AS query,
      (   pg_stat_activity.backend_type = 'background worker'
          AND pg_stat_activity.query IS NOT NULL
      ) AS is_parallel_worker
  FROM
      pg_stat_activity
 WHERE
      state <> 'idle'
  AND pid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;

-- name : get_pg_activity_90600
-- Get data from pg_activity for pg 9.6
SELECT
      pg_stat_activity.pid AS pid,
      pg_stat_activity.application_name AS application_name,
      CASE WHEN LENGTH(pg_stat_activity.datname) > 16
          THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
          ELSE pg_stat_activity.datname
      END AS database,
      CASE WHEN pg_stat_activity.client_addr IS NULL
          THEN 'local'
          ELSE pg_stat_activity.client_addr::TEXT
      END AS client,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      pg_stat_activity.wait_event IS NOT NULL AS wait,
      pg_stat_activity.usename AS user,
      pg_stat_activity.state AS state,
      pg_stat_activity.query AS query,
      false AS is_parallel_worker
  FROM
      pg_stat_activity
 WHERE
      state <> 'idle'
  AND pid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;

-- name : get_pg_activity_90200_90500
-- Get data from pg_activity from pg 9.2 to pg 9.5
SELECT
      pg_stat_activity.pid AS pid,
      pg_stat_activity.application_name AS application_name,
      CASE WHEN LENGTH(pg_stat_activity.datname) > 16
          THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
          ELSE pg_stat_activity.datname
      END AS database,
      CASE WHEN pg_stat_activity.client_addr IS NULL
          THEN 'local'
          ELSE pg_stat_activity.client_addr::TEXT
      END AS client,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      pg_stat_activity.waiting AS wait,
      pg_stat_activity.usename AS user,
      pg_stat_activity.state AS state,
      pg_stat_activity.query AS query,
      false AS is_parallel_worker
  FROM
      pg_stat_activity
 WHERE
      state <> 'idle'
  AND pid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;

-- name : get_pg_activity_90200
-- Get data from pg_activity before pg 9.2
SELECT
      pg_stat_activity.procpid AS pid,
      '<unknown>' AS application_name,
      CASE
          WHEN LENGTH(pg_stat_activity.datname) > 16
          THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
          ELSE pg_stat_activity.datname
      END AS database,
      CASE WHEN pg_stat_activity.client_addr IS NULL
          THEN 'local'
          ELSE pg_stat_activity.client_addr::TEXT
      END AS client,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      pg_stat_activity.waiting AS wait,
      pg_stat_activity.usename AS user,
      CASE
          WHEN pg_stat_activity.current_query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
          WHEN pg_stat_activity.current_query = '<IDLE> in transaction' THEN 'idle in transaction'
          WHEN pg_stat_activity.current_query = '<IDLE>' THEN 'idle'
          ELSE 'active'
      END AS state,
      CASE
         WHEN pg_stat_activity.current_query LIKE '<IDLE>%%' THEN 'None'
         ELSE pg_stat_activity.current_query
      END AS query,
      false AS is_parallel_worker
  FROM
        pg_stat_activity
 WHERE
      current_query <> '<IDLE>'
  AND procpid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0 THEN true
           ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC

-- name : get_waiting_90200
-- Get waiting queries for versions before 9.2
SELECT
      pg_locks.pid AS pid,
      pg_stat_activity.application_name AS appname,
      CASE WHEN LENGTH(pg_stat_activity.datname) > 16
               THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
           ELSE pg_stat_activity.datname
      END AS database,
      pg_stat_activity.usename AS user,
      pg_locks.mode AS mode,
      pg_locks.locktype AS type,
      pg_locks.relation::regclass AS relation,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      pg_stat_activity.state as state,
      pg_stat_activity.query AS query
  FROM
      pg_catalog.pg_locks
      JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.pid)
 WHERE
      NOT pg_catalog.pg_locks.granted
      AND pg_catalog.pg_stat_activity.pid <> pg_backend_pid()
      AND CASE WHEN %(min_duration)s = 0 THEN true
               ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
          END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;


-- name : get_waiting_before_90200
-- Get waiting queries for versions before 9.2
SELECT
      pg_locks.pid AS pid,
      '<unknown>' AS appname,
      CASE WHEN LENGTH(pg_stat_activity.datname) > 16
           THEN SUBSTRING(pg_stat_activity.datname FROM 0 FOR 6)||'...'||SUBSTRING(pg_stat_activity.datname FROM '........$')
           ELSE pg_stat_activity.datname
      END AS database,
      pg_stat_activity.usename AS user,
      pg_locks.mode AS mode,
      pg_locks.locktype AS type,
      pg_locks.relation::regclass AS relation,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      CASE WHEN pg_stat_activity.current_query = '<IDLE> in transaction (aborted)'
               THEN 'idle in transaction (aborted)'
           WHEN pg_stat_activity.current_query = '<IDLE> in transaction'
	       THEN 'idle in transaction'
           WHEN pg_stat_activity.current_query = '<IDLE>'
	       THEN 'idle'
           ELSE 'active'
      END AS state,
      CASE WHEN pg_stat_activity.current_query LIKE '<IDLE>%%' THEN 'None'
           ELSE pg_stat_activity.current_query
      END AS query
  FROM
      pg_catalog.pg_locks
      JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.procpid)
 WHERE
      NOT pg_catalog.pg_locks.granted
      AND pg_catalog.pg_stat_activity.procpid <> pg_backend_pid()
      AND CASE WHEN %(min_duration)s = 0 THEN true
               ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
          END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;


-- name : get_pga_inet_addresses?
-- Get the inet address
SELECT inet_server_addr() AS inet_server_addr, inet_client_addr() AS inet_client_addr;

