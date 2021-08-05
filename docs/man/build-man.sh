#!/bin/bash

version=$(python3 ../../setup.py --version)

pod2man -r "pg_activity ${version}" -d `date +%Y-%m-%d` -c "Command line tool for PostgreSQL server activity monitoring." pg_activity.pod > pg_activity.1;
