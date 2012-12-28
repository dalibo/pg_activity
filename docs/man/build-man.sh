#!/bin/bash

pod2man -r "pg_activity 0.2.2" -d "2012-12-28" -c "PostgreSQL server activity monitoring tool" pg_activity.pod > pg_activity.1; gzip -f pg_activity.1;
