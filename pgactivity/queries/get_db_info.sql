-- Get the database info
SELECT
      EXTRACT(EPOCH FROM NOW()) AS timestamp,
      COALESCE(SUM(pg_stat_get_db_xact_commit(oid)+pg_stat_get_db_xact_rollback(oid))::BIGINT, 0) AS no_xact,
      COALESCE(CASE
          WHEN %(skip_db_size)s THEN %(prev_total_size)s
          ELSE SUM(pg_database_size(datname))
      END, 0) AS total_size,
      COALESCE(MAX(LENGTH(datname)), 0) AS max_length
  FROM pg_database
 WHERE NOT (datname = 'rdsadmin' AND %(using_rds)s)
 AND CASE WHEN %(dbname_filter)s IS NULL THEN true
    ELSE datname ~* %(dbname_filter)s
    END;
