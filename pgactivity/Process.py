"""
pg_activity
author: Julien Tachoires <julmon@gmail.com>
license: PostgreSQL License

Copyright (c) 2012 - 2016, Julien Tachoires

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

class Process():
    """
    Simple class for process management.
    """
    def __init__(self, pid = None, database = None, user = None, \
        client = None, cpu = None, mem = None, read = None, write = None, \
        query = None, duration = None, wait = None, extras = None):
        self.pid = pid
        self.database = database
        self.user = user
        self.client = client
        self.cpu = cpu
        self.mem = mem
        self.read = read
        self.write = write
        self.query = query
        self.duration = duration
        self.wait = wait
        self.extras = extras

    def set_extra(self, key, value):
        """
        Set a pair of key/value in extras dict
        """
        self.extras[key] = value

    def get_extra(self, key):
        """
        Get a value from extras dict
        """
        if self.extras is not None and key in self.extras:
            return self.extras[key]
