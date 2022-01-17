-- Get the server informations prior to 9.0
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
               COALESCE(CASE WHEN sum(sd.blks_read) + sum(sd.blks_hit) = 0
                   THEN 0
                   ELSE trunc(100 * sum(sd.blks_hit) / (sum(sd.blks_read) + sum(sd.blks_hit)), 2)
               END, 0) AS cache_hit_ratio,
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
         WHERE CASE WHEN %(dbname_filter)s IS NULL THEN true
                    ELSE datname ~* %(dbname_filter)s
               END
), walreceivers AS (
        SELECT NULL AS wal_receivers
), walsenders AS (
        SELECT NULL AS wal_senders
), slots AS (
	SELECT NULL AS replication_slots
), tempfiles AS (
	SELECT count(agg.tmpfile) AS temp_files,
	       COALESCE(SUM(COALESCE((pg_stat_file(agg.dir||'/'||agg.tmpfile)).size, 0)),0) AS temp_bytes
	  FROM (
		SELECT ls.oid, ls.spcname AS spcname,
		       ls.dir||'/'||ls.sub AS dir,
		       pg_ls_dir(ls.dir||'/'||ls.sub) AS tmpfile
		  FROM (SELECT sr.oid, sr.spcname,
			       'pg_tblspc/'||sr.oid||'/'||sr.spc_root AS dir,
			       pg_ls_dir('pg_tblspc/'||sr.oid||'/'||sr.spc_root) AS sub
			  FROM
			       (SELECT spc.oid, spc.spcname,
				       pg_ls_dir('pg_tblspc/'||spc.oid) AS spc_root,
				       trim(TRAILING e'\n ' FROM pg_read_file('PG_VERSION', 0, 100)) AS v
				 FROM (SELECT oid, spcname
					 FROM pg_tablespace
					WHERE spcname NOT IN ('pg_default', 'pg_global')
				      ) AS spc
				) AS sr
			 WHERE sr.spc_root ~ ('^PG_'||sr.v)
			UNION ALL
			SELECT 0, 'pg_default', 'base' AS dir, 'pgsql_tmp' AS sub
			  FROM pg_ls_dir('base') AS l
			 WHERE l='pgsql_tmp'
			) AS ls
		 WHERE ls.sub = 'pgsql_tmp'
		) AS agg
	 WHERE current_setting('is_superuser')::bool  -- should filter out rds also
)
SELECT * FROM dbinfo, activity, walreceivers, walsenders, slots, tempfiles;
