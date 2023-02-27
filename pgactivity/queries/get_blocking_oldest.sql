-- Get blocking queries
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
      CASE
          WHEN sq.query = '<IDLE> in transaction (aborted)' THEN 'idle in transaction (aborted)'
          WHEN sq.query = '<IDLE> in transaction' THEN 'idle in transaction'
          WHEN sq.query = '<IDLE>' THEN 'idle'
          ELSE 'active'
      END AS state,
      CASE WHEN sq.query LIKE '<IDLE>%%'
          THEN NULL
          ELSE sq.query
      END AS query,
      pg_catalog.pg_encoding_to_char(b.encoding) AS encoding,
      waiting AS wait
  FROM
      (
      -- Transaction id lock
      SELECT
            blocking.pid,
            '<unknown>' AS application_name,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.datid,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
            END AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            NULL AS state,
            blocking.relation::regclass AS relation,
            pg_stat_activity.waiting
        FROM
            pg_locks AS blocking
            JOIN pg_locks AS blocked ON (blocking.transactionid = blocked.transactionid AND blocking.locktype = blocked.locktype)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.procpid)
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
            '<unknown>' AS application_name,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.datid,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
            END AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            NULL AS state,
            blocking.relation::regclass AS relation,
            pg_stat_activity.waiting
        FROM
            pg_locks AS blocking
            JOIN pg_locks AS blocked ON (blocking.virtualxid = blocked.virtualxid AND blocking.locktype = blocked.locktype)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.procpid)
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
            '<unknown>' AS application_name,
            pg_stat_activity.current_query AS query,
            blocking.mode,
            pg_stat_activity.datname,
            pg_stat_activity.datid,
            pg_stat_activity.usename,
            CASE WHEN pg_stat_activity.client_addr IS NULL
                THEN 'local'
                ELSE pg_stat_activity.client_addr::TEXT
            END AS client,
            blocking.locktype,
            EXTRACT(epoch FROM (NOW() - pg_stat_activity.{duration_column})) AS duration,
            NULL AS state,
            blocking.relation::regclass AS relation,
            pg_stat_activity.waiting
        FROM
            pg_locks AS blocking
            JOIN pg_locks AS blocked ON (blocking.database = blocked.database AND blocking.relation = blocked.relation AND blocking.locktype = blocked.locktype)
            JOIN pg_stat_activity ON (blocking.pid = pg_stat_activity.procpid)
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
      waiting
ORDER BY
      duration DESC;
