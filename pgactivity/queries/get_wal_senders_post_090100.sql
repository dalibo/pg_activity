-- Get the wal sender info for pg >= 9.1
-- NEW pg_stat_replication
SELECT count(*) AS wal_senders
FROM pg_stat_replication
