-- Get active connections from pg_stat_activity for pg >= 9.2
SELECT COUNT(*) as active_connections
  FROM pg_stat_activity
 WHERE state = 'active'
 AND CASE WHEN %(dbname_filter)s IS NULL THEN true
     ELSE datname ~* %(dbname_filter)s
     END;
