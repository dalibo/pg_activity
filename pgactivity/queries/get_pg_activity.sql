-- Get data from pg_activity before pg 9.2
SELECT
      pg_stat_activity.procpid AS pid,
      '<unknown>' AS application_name,
      pg_stat_activity.datname AS database,
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
          WHEN pg_stat_activity.current_query LIKE '<IDLE>%%' THEN NULL
          ELSE pg_stat_activity.current_query
      END AS query,
      false AS is_parallel_worker
  FROM
        pg_stat_activity
 WHERE
      current_query <> '<IDLE>'
  AND procpid <> pg_backend_pid()
  AND CASE WHEN %(min_duration)s = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
ORDER BY
      EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) DESC
