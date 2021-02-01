-- Get the path of the pidfile
SELECT setting||'/postmaster.pid' AS pid_file
  FROM pg_settings
 WHERE name = 'data_directory';
