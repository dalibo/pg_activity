"""
pg_activity
author: Julien Tachoires <julmon@gmail.com>
license: PostgreSQL License

Copyright (c) 2012 - 2019, Julien Tachoires

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose, without fee, and without a written
agreement is hereby granted, provided that the above copyright notice
and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL JULIEN TACHOIRES BE LIABLE TO ANY PARTY FOR DIRECT,
INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST
PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION,
EVEN IF JULIEN TACHOIRES HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

JULIEN TACHOIRES SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT
NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS"
BASIS, AND JULIEN TACHOIRES HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""


class PGProcess(object):
    """
    Simple class for Postgres process management.
    """
    def __init__(self, pid=None, database=None, user=None, client=None,
                 cpu=0, mem=0, read=0, write=0, state=None, query=None,
                 duration=0, wait=None, extras={}, appname=None):
        self.pid = pid
        self.database = database
        self.user = user
        self.client = client
        self.cpu = cpu
        self.mem = mem
        self.read = read
        self.write = write
        self.state = state
        self.query = query
        self.duration = duration
        self.wait = wait
        self.extras = extras
        self.appname = appname
        self.psproc = None
        self.meminfo = None
        self.read_bytes = 0
        self.write_bytes = 0
        self.io_time = 0
        self.cpu_times = None
        self.io_wait = None

    def set_extra(self, key, value):
        """
        Set a pair of key/value in extras dict
        """
        self.extras[key] = value

    def get_extra(self, key):
        """
        Get a value from extras dict
        """
        return self.extras.get(key)


class PGProcessList(object):
    """
    List of PGProcess
    """

    def __init__(self):
        self.procs = dict()
        self.rw_counter = dict()

    def __iter__(self):
        for pid, proc in self.procs.items():
            yield proc

    def __len__(self):
        return len(self.procs.items())

    def add(self, pgproc):
        self.procs[pgproc.pid] = pgproc

    def update(self, pgproc):
        self.add(pgproc)

    def sort(self, key, reverse=True):
        for pid, proc in sorted(self.procs.items(),
                                key=lambda (pid, proc): getattr(proc, key),  # noqa
                                reverse=reverse):
            yield proc

    def has(self, pid):
        return (pid in self.procs)

    def get(self, pid):
        return self.procs.get(pid)

    def delete(self, pid):
        del(self.procs[pid])

    def pid_list(self):
        return [pid for pid, _ in self.procs.items()]

    def rw_store(self, process):
        self.rw_counter[process.pid] = PGProcessDeltaCounter(
            process.pid,
            io_time=process.io_time,
            read_bytes=process.read_bytes,
            write_bytes=process.write_bytes
        )

    def rw_delta(self, process):
        read_delta = 0
        write_delta = 0

        if process.pid not in self.rw_counter:
            return (read_delta, write_delta)

        d_io_time = process.io_time - self.rw_counter[process.pid].io_time

        if d_io_time == 0:
            return (read_delta, write_delta)

        read_delta = ((process.read_bytes
                      - self.rw_counter[process.pid].read_bytes) / d_io_time)
        write_delta = ((process.write_bytes
                       - self.rw_counter[process.pid].write_bytes) / d_io_time)
        return (read_delta, write_delta)


class PGProcessDeltaCounter(object):

    def __init__(self, pid, io_time=0, read_bytes=0, write_bytes=0):
        self.pid = pid
        self.io_time = io_time
        self.read_bytes = read_bytes
        self.write_bytes = write_bytes
