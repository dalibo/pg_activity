-- Get blocking queries >= 9.2
SELECT
      pid,
      application_name,
      datname AS database,
      usename AS user,
      client,
      relation,
      mode,
      locktype AS type,
      duration,
      state,
      query
  FROM
      (
      SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
	    CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
            END AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation
        FROM
            pg_locks AS blocking
            JOIN (
                SELECT
                      transactionid
                  FROM
                      pg_locks
                 WHERE
                      NOT granted
	    ) AS blocked ON (blocking.transactionid = blocked.transactionid)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
       WHERE
            blocking.granted
        AND CASE WHEN %(min_duration)s = 0
                THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
      UNION ALL
      SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
            END AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation
        FROM
            pg_locks AS blocking
            JOIN (
                SELECT
                      database,
                      relation,
                      mode
                  FROM
                      pg_locks
                 WHERE
                      NOT granted
                  AND relation IS NOT NULL
            ) AS blocked ON (blocking.database = blocked.database AND blocking.relation = blocked.relation)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
       WHERE
            blocking.granted
        AND CASE WHEN %(min_duration)s = 0
                THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
      ) AS sq
GROUP BY
      pid,
      application_name,
      query,
      mode,
      locktype,
      duration,
      datname,
      usename,
      client,
      state,
      relation
ORDER BY
      duration DESC;
