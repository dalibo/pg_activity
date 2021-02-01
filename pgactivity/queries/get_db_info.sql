-- Get the database info
SELECT
      EXTRACT(EPOCH FROM NOW()) AS timestamp,
      SUM(pg_stat_get_db_xact_commit(oid)+pg_stat_get_db_xact_rollback(oid))::BIGINT AS no_xact,
      CASE
          WHEN %(skip_db_size)s THEN %(prev_total_size)s
          ELSE SUM(pg_database_size(datname))
      END AS total_size,
      MAX(LENGTH(datname)) AS max_length
  FROM pg_database
 WHERE NOT (datname = 'rdsadmin' AND %(using_rds)s);
