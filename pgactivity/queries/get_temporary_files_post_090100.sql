-- Get temporary file information for pg >= 9.1
-- NEW pg_read_file no longer need 3 parameters
SELECT count(agg.tmpfile) AS temp_files,
       COALESCE(SUM(COALESCE((pg_stat_file(agg.dir||'/'||agg.tmpfile)).size, 0)),0) AS temp_bytes
  FROM (
       SELECT ls.oid, ls.spcname AS spcname,
              ls.dir||'/'||ls.sub AS dir,
              pg_ls_dir(ls.dir||'/'||ls.sub) AS tmpfile
         FROM (SELECT sr.oid, sr.spcname,
                      'pg_tblspc/'||sr.oid||'/'||sr.spc_root AS dir,
                      pg_ls_dir('pg_tblspc/'||sr.oid||'/'||sr.spc_root) AS sub
                 FROM
                      (SELECT spc.oid, spc.spcname,
                              pg_ls_dir('pg_tblspc/'||spc.oid) AS spc_root,
                              trim(TRAILING e'\n ' FROM pg_read_file('PG_VERSION')) AS v
                         FROM (SELECT oid, spcname
                                 FROM pg_tablespace
                                WHERE spcname NOT IN ('pg_default', 'pg_global')
                              ) AS spc
                      ) AS sr
                WHERE sr.spc_root ~ ('^PG_'||sr.v)
               UNION ALL
               SELECT 0, 'pg_default', 'base' AS dir, 'pgsql_tmp' AS sub
                 FROM pg_ls_dir('base') AS l
                WHERE l='pgsql_tmp'
               ) AS ls
        WHERE ls.sub = 'pgsql_tmp'
       ) AS agg
