-- Get waiting queries for versions >= 9.2
SELECT
      pg_locks.pid AS pid,
      pg_stat_activity.application_name AS application_name,
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
      pg_stat_activity.state as state,
      pg_stat_activity.query AS query
  FROM
      pg_catalog.pg_locks
      JOIN pg_catalog.pg_stat_activity ON(pg_catalog.pg_locks.pid = pg_catalog.pg_stat_activity.pid)
 WHERE
      NOT pg_catalog.pg_locks.granted
  AND pg_catalog.pg_stat_activity.pid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC;
