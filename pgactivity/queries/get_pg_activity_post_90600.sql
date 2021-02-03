-- Get data from pg_activity from pg 9.6 to 10
-- In this versiosn there is no way to distinguish parallel workers from the rest
SELECT
      pg_stat_activity.pid AS pid,
      pg_stat_activity.application_name AS application_name,
      pg_stat_activity.datname AS database,
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
