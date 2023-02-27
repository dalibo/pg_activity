-- Get waiting queries for versions >= 9.2
-- NEW pg_stat_activity.state
-- NEW pg_stat_activity.current_query => pg_stat_activity.query
-- NEW pg_stat_activity.procpid => pg_stat_activity.pid
SELECT
      pg_locks.pid AS pid,
      a.application_name AS application_name,
      a.datname AS database,
      a.usename AS user,
      CASE WHEN a.client_addr IS NULL
          THEN 'local'
          ELSE a.client_addr::TEXT
      END AS client,
      pg_locks.mode AS mode,
      pg_locks.locktype AS type,
      pg_locks.relation::regclass AS relation,
      EXTRACT(epoch FROM (NOW() - a.{duration_column})) AS duration,
      a.state as state,
      a.query AS query,
      pg_catalog.pg_encoding_to_char(b.encoding) AS encoding
  FROM
      pg_catalog.pg_locks
      JOIN pg_catalog.pg_stat_activity a ON(pg_catalog.pg_locks.pid = a.pid)
      LEFT OUTER JOIN pg_database b ON a.datid = b.oid
 WHERE
      NOT pg_catalog.pg_locks.granted
  AND a.pid <> pg_backend_pid()
  AND CASE WHEN {min_duration} = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
  AND CASE WHEN {dbname_filter} IS NULL THEN true
      ELSE a.datname ~* %(dbname_filter)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - a.{duration_column})) DESC;
