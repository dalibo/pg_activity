-- Get the server information prior to 9.0
WITH dbinfo AS(
        SELECT COALESCE(SUM(sd.xact_commit + sd.xact_rollback)::BIGINT, 0) AS xact_count,
               COALESCE(SUM(tup_inserted)::BIGINT, 0) AS insert,
               COALESCE(SUM(tup_updated)::BIGINT, 0) AS update,
               COALESCE(SUM(tup_deleted)::BIGINT, 0) AS delete,
               COALESCE(SUM(tup_returned)::BIGINT, 0) AS tuples_returned,
               COALESCE(CASE
                   WHEN %(skip_db_size)s THEN %(prev_total_size)s
                   ELSE SUM(pg_database_size(d.datname))
               END, 0) AS total_size,
               COALESCE(SUM(sd.blks_read), 0) AS blks_read,
               COALESCE(SUM(sd.blks_hit), 0) AS blks_hit,
               COALESCE(MAX(LENGTH(d.datname)), 0) AS max_dbname_length,
               current_timestamp - pg_postmaster_start_time() AS uptime,
               EXTRACT(EPOCH FROM NOW()) AS epoch
          FROM pg_database d
               INNER JOIN pg_stat_database sd ON d.oid = sd.datid
         WHERE NOT (d.datname = 'rdsadmin' AND %(using_rds)s)
               AND CASE WHEN {dbname_filter} IS NULL THEN true
                        ELSE d.datname ~* %(dbname_filter)s
                   END
), activity AS (
        SELECT sum(CASE WHEN current_query NOT LIKE '<IDLE>%%' THEN 1 ELSE 0 END) AS active_connections,
               sum(CASE WHEN current_query LIKE '<IDLE>' THEN 1 ELSE 0 END) AS idle,
               sum(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END) AS idle_in_transaction,
               sum(CASE WHEN current_query LIKE '<IDLE> in transaction (aborted)' THEN 1 ELSE 0 END) AS idle_in_transaction_aborted,
               count(*) AS total,
               sum(CASE WHEN waiting THEN 1 ELSE 0 END) AS waiting,
               current_setting('max_connections')::int AS max_connections,
               NULL AS autovacuum_workers,
               current_setting('autovacuum_max_workers')::int AS autovacuum_max_workers,
               NULL AS logical_replication_workers,
               NULL AS parallel_workers,
               NULL AS max_logical_replication_workers,
               NULL AS max_parallel_workers,
               NULL AS max_worker_processes,
               NULL AS max_wal_senders,
               NULL AS max_replication_slots
          FROM pg_stat_activity
         WHERE CASE WHEN {dbname_filter} IS NULL THEN true
                    ELSE datname ~* %(dbname_filter)s
               END
)
SELECT * FROM dbinfo, activity
