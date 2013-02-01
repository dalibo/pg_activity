#!/bin/bash

pod2man -r "pg_activity 0.3.0" -d "2013-01-31" -c "PostgreSQL server activity monitoring tool" pg_activity.pod > pg_activity.1; gzip -f pg_activity.1;
