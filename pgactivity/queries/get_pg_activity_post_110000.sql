-- Get data from pg_activity since pg 11
SELECT
      pg_stat_activity.pid AS pid,
      pg_stat_activity.application_name AS application_name,
      pg_stat_activity.datname AS database,
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
