-- get the replication slots information for pg > 14
-- NEW pg_replication_slots
SELECT count(*) AS replication_slots FROM pg_replication_slots
