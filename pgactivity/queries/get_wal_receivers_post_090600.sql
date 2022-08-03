-- Get the wal receiver info for pg >= 9.6
-- NEW pg_stat_wal_receiver
SELECT count(*) AS wal_receivers FROM pg_stat_wal_receiver
