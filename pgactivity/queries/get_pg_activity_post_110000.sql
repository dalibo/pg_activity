-- Get data from pg_activity since pg 11
-- NEW pg_activity.backend_type value for 'parallel worker'
SELECT
      a.pid AS pid,
      a.application_name AS application_name,
      a.datname AS database,
      CASE WHEN a.client_addr IS NULL
          THEN 'local'
          ELSE a.client_addr::TEXT
      END AS client,
      EXTRACT(epoch FROM (NOW() - a.{duration_column})) AS duration,
      a.wait_event AS wait,
      a.usename AS user,
      a.state AS state,
      a.query AS query,
      pg_catalog.pg_encoding_to_char(b.encoding) AS encoding,
      NULL AS query_leader_pid,
      a.backend_type = 'parallel worker' AS is_parallel_worker
 FROM
      pg_stat_activity a
      LEFT OUTER JOIN pg_database b ON a.datid = b.oid
 WHERE
      a.state <> 'idle'
  AND a.pid <> pg_catalog.pg_backend_pid()
  AND CASE WHEN {min_duration} = 0
          THEN true
          ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
      END
    AND CASE WHEN {dbname_filter} IS NULL THEN true
        ELSE a.datname ~* %(dbname_filter)s
        END
ORDER BY
      EXTRACT(epoch FROM (NOW() - a.{duration_column})) DESC;
