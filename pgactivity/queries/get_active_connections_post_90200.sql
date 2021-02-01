-- Get active connections from pg_stat_activity for pg >= 9.2
SELECT COUNT(*) as active_connections
  FROM pg_stat_activity
 WHERE state = 'active';
