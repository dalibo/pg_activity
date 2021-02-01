-- Get the server's version
SELECT pg_terminate_backend(%(pid)s) AS terminated;
