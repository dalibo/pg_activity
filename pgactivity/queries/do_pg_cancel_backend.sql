-- Get the server's version
SELECT pg_cancel_backend(%(pid)s) AS cancelled;
