#!/bin/bash

pod2man -r "pg_activity 0.3.1" -d "2013-02-11" -c "PostgreSQL server activity monitoring tool" pg_activity.pod > pg_activity.1; gzip -f pg_activity.1;
