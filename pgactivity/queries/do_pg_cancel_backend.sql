-- Cancel the current query of the session whose backend process has the
-- specified process ID
SELECT pg_cancel_backend(%(pid)s) AS is_stopped;
