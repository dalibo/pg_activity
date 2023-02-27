-- Get waiting queries for versions before 9.2
SELECT
      pg_locks.pid AS pid,
      '<unknown>' AS application_name,
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
      CASE
          WHEN a.current_query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
          WHEN a.current_query = '<IDLE> in transaction' THEN 'idle in transaction'
          WHEN a.current_query = '<IDLE>' THEN 'idle'
          ELSE 'active'
      END AS state,
      CASE WHEN a.current_query LIKE '<IDLE>%%'
          THEN NULL
          ELSE a.current_query
      END AS query,
      pg_catalog.pg_encoding_to_char(b.encoding) AS encoding
  FROM
      pg_catalog.pg_locks
      JOIN pg_catalog.pg_stat_activity a ON (pg_catalog.pg_locks.pid = a.procpid)
      LEFT OUTER JOIN pg_database b ON a.datid = b.oid
 WHERE
      NOT pg_catalog.pg_locks.granted
  AND a.procpid <> pg_backend_pid()
  AND CASE WHEN {min_duration} = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
  AND CASE WHEN {dbname_filter} IS NULL THEN true
      ELSE a.datname ~* %(dbname_filter)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - a.{duration_column})) DESC;
