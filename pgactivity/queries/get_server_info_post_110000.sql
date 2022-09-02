-- Get the server information for pg >= 11
-- NEW: pg_activity.backend_type for background workers (logical replication worker, parallel worker)
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
               AND CASE WHEN %(dbname_filter)s IS NULL THEN true
                        ELSE d.datname ~* %(dbname_filter)s
                   END
), activity AS (
        SELECT count(*) FILTER( WHERE backend_type = 'client backend' and state = 'active') AS active_connections,
               count(*) FILTER( WHERE backend_type = 'client backend' and state = 'idle') AS idle,
               count(*) FILTER( WHERE backend_type = 'client backend' and state = 'idle in transaction') AS idle_in_transaction,
               count(*) FILTER( WHERE backend_type = 'client backend' and state = 'idle in transaction aborted') AS idle_in_transaction_aborted,
               count(*) FILTER( WHERE backend_type = 'client backend') AS total,
               count(*) FILTER( WHERE wait_event_type = 'Lock') as waiting,
               current_setting('max_connections')::int AS max_connections,
               count(*) FILTER( WHERE backend_type = 'autovacuum worker') AS autovacuum_workers,
               current_setting('autovacuum_max_workers')::int AS autovacuum_max_workers,
               count(*) FILTER( WHERE backend_type = 'logical replication worker') AS logical_replication_workers,
               count(*) FILTER( WHERE backend_type = 'parallel worker') AS parallel_workers,
               current_setting('max_logical_replication_workers')::int AS max_logical_replication_workers,
               current_setting('max_parallel_workers')::int AS max_parallel_workers,
               current_setting('max_worker_processes')::int AS max_worker_processes,
               current_setting('max_wal_senders')::int AS max_wal_senders,
               current_setting('max_replication_slots')::int AS max_replication_slots
          FROM pg_stat_activity
         WHERE CASE WHEN %(dbname_filter)s IS NULL THEN true
                    ELSE datname ~* %(dbname_filter)s
               END
)
SELECT * FROM dbinfo, activity
