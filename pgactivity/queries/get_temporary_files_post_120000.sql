-- Get temporary file information for pg >= 12
-- NEW: pg_ls_tmp_dir()
SELECT count(*) as temp_files,
       COALESCE(SUM(size), 0) AS temp_bytes
  FROM pg_tablespace ts, LATERAL pg_catalog.pg_ls_tmpdir(ts.oid) tmp
 WHERE spcname <> 'pg_global'
