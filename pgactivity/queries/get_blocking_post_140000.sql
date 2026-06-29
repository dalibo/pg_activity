-- Get blocking queries >= 14
SELECT
      pid,
      application_name,
      sq.datname AS database,
      usename AS user,
      client,
      relation,
      mode,
      locktype AS type,
      duration,
      state,
      sq.query AS query,
      pg_catalog.pg_encoding_to_char(b.encoding) AS encoding,
      wait_event as wait,
      query_id
  FROM
      (
      -- Transaction id lock
      SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.datid,
            pg_stat_activity.usename,
            pg_stat_activity.client_addr AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation,
            pg_stat_activity.wait_event,
            pg_stat_activity.query_id
        FROM
            pg_locks AS blocking
            JOIN pg_locks AS blocked ON (blocking.transactionid = blocked.transactionid AND blocking.locktype = blocked.locktype)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
       WHERE
            blocking.granted
        AND NOT blocked.granted
        AND CASE WHEN {min_duration} = 0
                THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
        AND CASE WHEN {dbname_filter} IS NULL THEN true
            ELSE datname ~* %(dbname_filter)s
            END
      UNION ALL
      -- VirtualXid Lock
      SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.datid,
            pg_stat_activity.usename,
            pg_stat_activity.client_addr AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation,
            pg_stat_activity.wait_event,
            pg_stat_activity.query_id
        FROM
            pg_locks AS blocking
            JOIN pg_locks AS blocked ON (blocking.virtualxid = blocked.virtualxid AND blocking.locktype = blocked.locktype)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
       WHERE
            blocking.granted
        AND NOT blocked.granted
        AND CASE WHEN {min_duration} = 0
                THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
        AND CASE WHEN {dbname_filter} IS NULL THEN true
            ELSE datname ~* %(dbname_filter)s
            END
      UNION ALL
      -- Relation or tuple Lock
      SELECT
            blocking.pid,
            pg_stat_activity.application_name,
            pg_stat_activity.query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.datid,
            pg_stat_activity.usename,
            pg_stat_activity.client_addr AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            pg_stat_activity.state as state,
            blocking.relation::regclass AS relation,
            pg_stat_activity.wait_event,
            pg_stat_activity.query_id
        FROM
            pg_locks AS blocking
            JOIN pg_locks AS blocked ON (blocking.database = blocked.database AND blocking.relation = blocked.relation AND blocking.locktype = blocked.locktype)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.pid)
       WHERE
            blocking.granted
        AND NOT blocked.granted
        AND blocked.relation IS NOT NULL
        AND CASE WHEN {min_duration} = 0
                THEN true
                ELSE extract(epoch from now() - {duration_column}) > %(min_duration)s
            END
        AND CASE WHEN {dbname_filter} IS NULL THEN true
            ELSE datname ~* %(dbname_filter)s
            END
      ) AS sq
      LEFT OUTER JOIN pg_database b ON sq.datid = b.oid
GROUP BY
      pid,
      application_name,
      database,
      usename,
      client,
      relation,
      mode,
      locktype,
      duration,
      state,
      query,
      encoding,
      wait_event,
      query_id
ORDER BY
      duration DESC;
