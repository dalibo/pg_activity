-- Get waiting queries for versions before 9.2
SELECT
      pg_locks.pid AS pid,
      '<unknown>' AS application_name,
      pg_stat_activity.datname AS database,
      pg_stat_activity.usename AS user,
      CASE WHEN pg_stat_activity.client_addr IS NULL
          THEN 'local'
          ELSE pg_stat_activity.client_addr::TEXT
      END AS client,
      pg_locks.mode AS mode,
      pg_locks.locktype AS type,
      pg_locks.relation::regclass AS relation,
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
      CASE
          WHEN pg_stat_activity.current_query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
          WHEN pg_stat_activity.current_query = '<IDLE> in transaction' THEN 'idle in transaction'
          WHEN pg_stat_activity.current_query = '<IDLE>' THEN 'idle'
          ELSE 'active'
      END AS state,
      CASE WHEN pg_stat_activity.current_query LIKE '<IDLE>%%'
          THEN NULL
          ELSE pg_stat_activity.current_query
      END AS query
  FROM
      pg_catalog.pg_locks
      JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.procpid)
 WHERE
      NOT pg_catalog.pg_locks.granted
  AND pg_catalog.pg_stat_activity.procpid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;
