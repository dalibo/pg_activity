-- Terminate the session whose backend process has the specified process ID
SELECT pg_terminate_backend(%(pid)s) AS is_stopped;
