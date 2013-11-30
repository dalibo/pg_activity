"""
pg_activity
version: 1.1.0
author: Julien Tachoires <julmon@gmail.com>
license: PostgreSQL License

Copyright (c) 2012 - 2013, Julien Tachoires

Permission to use, copy, modify, and distribute this software and its documentation for any purpose, without fee, and without a written agreement is hereby granted, provided that the above copyright notice and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL JULIEN TACHOIRES BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF JULIEN TACHOIRES HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

JULIEN TACHOIRES SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS, AND JULIEN TACHOIRES HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

import curses
import re
import time
import os, sys
from datetime import timedelta
from Data import *

# Define some color pairs
C_BLACK_GREEN = 1
C_CYAN =        2
C_RED =         3
C_GREEN =       4
C_YELLOW =      5
C_MAGENTA =     6
C_WHITE =       7
C_BLACK_CYAN =  8
C_RED_BLACK =   9
C_GRAY =        10

# Columns
PGTOP_FLAG_DATABASE =   1
PGTOP_FLAG_CLIENT =     2
PGTOP_FLAG_USER =       4
PGTOP_FLAG_CPU =        8
PGTOP_FLAG_MEM =        16
PGTOP_FLAG_READ =       32
PGTOP_FLAG_WRITE =      64
PGTOP_FLAG_TIME =       128
PGTOP_FLAG_WAIT =       256
PGTOP_FLAG_RELATION =   512
PGTOP_FLAG_TYPE =       1024
PGTOP_FLAG_MODE =       2048
PGTOP_FLAG_IOWAIT =     4096
PGTOP_FLAG_NONE =       None

# Display query mode
PGTOP_TRUNCATE =        1
PGTOP_WRAP_NOINDENT =   2
PGTOP_WRAP =            3

# Maximum number of column
PGTOP_MAX_NCOL = 13

PGTOP_COLS = {
    'activities': {
        'pid'       : {'n':  1, 'name': 'PID', 'template_h': '%-6s ', 'flag': PGTOP_FLAG_NONE, 'mandatory': True},
        'database'  : {'n':  2, 'name': 'DATABASE', 'template_h': '%-16s ', 'flag': PGTOP_FLAG_DATABASE, 'mandatory': False},
        'user'      : {'n':  3, 'name': 'USER', 'template_h': '%16s ', 'flag': PGTOP_FLAG_USER, 'mandatory': False},
        'client'    : {'n':  4, 'name': 'CLIENT', 'template_h': '%16s ', 'flag': PGTOP_FLAG_CLIENT, 'mandatory': False},
        'cpu'       : {'n':  5, 'name': 'CPU%', 'template_h': '%6s ', 'flag': PGTOP_FLAG_CPU, 'mandatory': False},
        'mem'       : {'n':  6, 'name': 'MEM%', 'template_h': '%4s ', 'flag': PGTOP_FLAG_MEM, 'mandatory': False},
        'read'      : {'n':  7, 'name': 'READ/s', 'template_h': '%8s ', 'flag': PGTOP_FLAG_READ, 'mandatory': False},
        'write'     : {'n':  8, 'name': 'WRITE/s', 'template_h': '%8s ', 'flag': PGTOP_FLAG_WRITE, 'mandatory': False},
        'time'      : {'n':  9, 'name': 'TIME+', 'template_h': '%9s ', 'flag': PGTOP_FLAG_TIME, 'mandatory': False},
        'wait'      : {'n': 10, 'name': 'W', 'template_h': '%2s ', 'flag': PGTOP_FLAG_WAIT, 'mandatory': False},
        'iowait'    : {'n': 11, 'name': 'IOW', 'template_h': '%4s ', 'flag': PGTOP_FLAG_IOWAIT, 'mandatory': False},
        'query'     : {'n': 12, 'name': 'Query', 'template_h': ' %2s', 'flag': PGTOP_FLAG_NONE, 'mandatory': True},
    },
    'waiting': {
        'pid'       : {'n': 1, 'name': 'PID', 'template_h': '%-6s ', 'flag': PGTOP_FLAG_NONE, 'mandatory': True},
        'database'  : {'n': 2, 'name': 'DATABASE', 'template_h': '%-16s ', 'flag': PGTOP_FLAG_DATABASE, 'mandatory': False},
        'relation'  : {'n': 3, 'name': 'RELATION', 'template_h': '%9s ', 'flag': PGTOP_FLAG_RELATION, 'mandatory': False},
        'type'      : {'n': 4, 'name': 'TYPE', 'template_h': '%16s ', 'flag': PGTOP_FLAG_TYPE, 'mandatory': False},
        'mode'      : {'n': 5, 'name': 'MODE', 'template_h': '%16s ', 'flag': PGTOP_FLAG_MODE, 'mandatory': False},
        'time'      : {'n': 6, 'name': 'TIME+', 'template_h': '%9s ', 'flag': PGTOP_FLAG_TIME, 'mandatory': False},
        'query'     : {'n': 7, 'name': 'Query', 'template_h': ' %2s', 'flag': PGTOP_FLAG_NONE, 'mandatory': True},
    },
    'blocking': {
        'pid'       : {'n': 1, 'name': 'PID', 'template_h': '%-6s ', 'flag': PGTOP_FLAG_NONE, 'mandatory': True},
        'database'  : {'n': 2, 'name': 'DATABASE', 'template_h': '%-16s ', 'flag': PGTOP_FLAG_DATABASE, 'mandatory': False},
        'relation'  : {'n': 3, 'name': 'RELATION', 'template_h': '%9s ', 'flag': PGTOP_FLAG_RELATION, 'mandatory': False},
        'type'      : {'n': 4, 'name': 'TYPE', 'template_h': '%16s ', 'flag': PGTOP_FLAG_TYPE, 'mandatory': False},
        'mode'      : {'n': 5, 'name': 'MODE', 'template_h': '%16s ', 'flag': PGTOP_FLAG_MODE, 'mandatory': False},
        'time'      : {'n': 6, 'name': 'TIME+', 'template_h': '%9s ', 'flag': PGTOP_FLAG_TIME, 'mandatory': False},
        'query'     : {'n': 7, 'name': 'Query', 'template_h': ' %2s', 'flag': PGTOP_FLAG_NONE, 'mandatory': True},
    }
}

class UI:

    def __init__(self, version):
        """
        Constructor.
        """
        self.version = version
        self.win = 0
        self.sys_color = True
        self.lineno = 0
        self.lines = []
        # Maximum number of columns
        self.max_ncol = 13
        # Default
        self.verbose_mode = PGTOP_WRAP_NOINDENT
        # Max IOPS
        self.max_iops = 0
        # Sort
        self.sort = 't'
        # Color
        self.color = True
        # Default mode : activites, waiting, blocking
        self.mode = 'activities'
        # Does pg_activity is connected to a local PG server ?
        self.is_local = True
        # Start line
        self.start_line = 5
        # Window's size
        self.maxy = 0
        self.maxx = 0
        # Init buffer
        self.buffer = None
        # Refresh time
        self.refresh_time = 2
        # Maximum DATABASE columns header length
        self.max_db_length = 16
        # Array containing pid of processes to yank
        self.pid_yank = []
        self.pid = []
        # Data collector
        self.dc = Data()
        # Maximum number of column
        self.max_ncol = PGTOP_MAX_NCOL
        # Default filesystem blocksize
        self.fs_blocksize = 4096
        # Init curses
        self.init_curses()
        # Columns colors definition
        self.line_colors = {
            'pid': {
                'default': self.get_curses_color(C_CYAN),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
             },
            'database': {
                'default': curses.A_BOLD|self.get_curses_color(C_GRAY),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'user': {
                'default': curses.A_BOLD|self.get_curses_color(C_GRAY),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'client': {
                'default': self.get_curses_color(C_CYAN),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'cpu': {
                'default': self.get_curses_color(0),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'mem': {
                'default': self.get_curses_color(0),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'read': {
                'default': self.get_curses_color(0),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'write': {
                'default': self.get_curses_color(0),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'time_red': {
                'default': self.get_curses_color(C_RED),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'time_yellow': {
                'default': self.get_curses_color(C_YELLOW),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'time_green': {
                'default': self.get_curses_color(C_GREEN),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'wait_green': {
                'default': self.get_curses_color(C_GREEN)|curses.A_BOLD,
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'wait_red': {
                'default': self.get_curses_color(C_RED)|curses.A_BOLD,
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'query': {
                'default': self.get_curses_color(0),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'relation': {
                'default': self.get_curses_color(C_CYAN),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'type': {
                'default': self.get_curses_color(0),
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'mode_yellow': {
                'default': self.get_curses_color(C_YELLOW)|curses.A_BOLD,
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            },
            'mode_red': {
                'default': self.get_curses_color(C_RED)|curses.A_BOLD,
                'cursor':  self.get_curses_color(C_CYAN)|curses.A_REVERSE,
                'yellow':  self.get_curses_color(C_YELLOW)|curses.A_BOLD
            }
        }

    def set_is_local(self, is_local):
        """
        Set self.is_local
        """
        self.is_local = is_local

    def get_is_local(self,):
        """
        Get self.is_local
        """
        return self.is_local

    def get_mode(self,):
        """
        Get self.mode
        """
        return self.mode

    def set_start_line(self, start_line):
        """
        Set self.start_line
        """
        self.start_line = start_line

    def set_buffer(self, buffer):
        """
        Set self.buffer
        """
        self.buffer = buffer

    def set_blocksize(self, blocksize):
        """
        Set blocksize
        """
        if not isinstance(blocksize, int):
            raise Exception('Unvalid blocksize value.')
        if blocksize != 0 and not ((blocksize & (blocksize - 1)) == 0):
            raise Exception('Unvalid blocksize value.')
        if not blocksize > 0:
            raise Exception('Unvalid blocksize value.')
        self.fs_blocksize = int(blocksize)

    def init_curses(self,):
        """
        Initialize curses environment.
        """
        curses.setupterm()
        self.win = curses.initscr()
        self.win.keypad(1)
        curses.noecho()
        try:
            # deactivate cursor
            curses.curs_set(0)
            # use colors
            curses.start_color()
            curses.use_default_colors()
        except Exception:
            # Terminal doesn't support curs_set() and colors
            self.sys_color = False
        curses.cbreak()
        curses.endwin()
        self.win.scrollok(0)
        (self.maxy, self.maxx) = self.win.getmaxyx()

    def get_flag_from_options(self, options):
        """
        Returns the flag depending on the options.
        """
        flag = PGTOP_FLAG_DATABASE | PGTOP_FLAG_USER | PGTOP_FLAG_CLIENT | PGTOP_FLAG_CPU | PGTOP_FLAG_MEM | PGTOP_FLAG_READ | PGTOP_FLAG_WRITE | PGTOP_FLAG_TIME | PGTOP_FLAG_WAIT | PGTOP_FLAG_RELATION | PGTOP_FLAG_TYPE | PGTOP_FLAG_MODE | PGTOP_FLAG_IOWAIT
        if options.nodb is True:
            flag -= PGTOP_FLAG_DATABASE
        if options.nouser is True:
            flag -= PGTOP_FLAG_USER
        if options.nocpu is True:
            flag -= PGTOP_FLAG_CPU
        if options.noclient is True:
            flag -= PGTOP_FLAG_CLIENT
        if options.nomem is True:
            flag -= PGTOP_FLAG_MEM
        if options.noread is True:
            flag -= PGTOP_FLAG_READ
        if options.nowrite is True:
            flag -= PGTOP_FLAG_WRITE
        if options.notime is True:
            flag -= PGTOP_FLAG_TIME
        if options.nowait is True:
            flag -= PGTOP_FLAG_WAIT

        # Remove some if no running against local pg server.
        if not self.get_is_local() and (flag & PGTOP_FLAG_CPU):
            flag -= PGTOP_FLAG_CPU
        if not self.get_is_local() and (flag & PGTOP_FLAG_MEM):
            flag -= PGTOP_FLAG_MEM
        if not self.get_is_local() and (flag & PGTOP_FLAG_READ):
            flag -= PGTOP_FLAG_READ
        if not self.get_is_local() and (flag & PGTOP_FLAG_WRITE):
            flag -= PGTOP_FLAG_WRITE
        if not self.get_is_local() and (flag & PGTOP_FLAG_IOWAIT):
            flag -= PGTOP_FLAG_IOWAIT
        return flag

    def get_curses_color(self, color):
        """
        Wrapper around curses.color_pair()
        """
        if self.sys_color:
            return curses.color_pair(color)
        else:
            return 0

    def set_max_db_length(self, new_length):
        """
        Set new DATABASE column length
        """
        global PGTOP_COLS
        if new_length > 16:
            new_length = 16
        if new_length < 8:
            new_length = 8

        self.max_db_length = new_length
        PGTOP_COLS['activities']['database']['template_h'] = '%-'+str(new_length)+'s '
        PGTOP_COLS['waiting']['database']['template_h'] = '%-'+str(new_length)+'s '
        PGTOP_COLS['blocking']['database']['template_h'] = '%-'+str(new_length)+'s '

    def at_exit_curses(self,):
        """
        Called at exit time.
        Rollback to default values.
        """
        try:
            self.win.keypad(0)
            self.win.move(0, 0)
            self.win.erase()
        except KeyboardInterrupt:
            pass
        curses.nocbreak()
        curses.echo()
        try:
            curses.curs_set(1)
        except Exception:
            pass
        curses.endwin()

    def signal_handler(self, signal, frame):
        """
        Function called on a process kill.
        """
        self.at_exit_curses()
        print "FATAL: Killed with signal %s ." % (str(signal),)
        print "%s" % (str(frame),)
        sys.exit(1)

    def set_nocolor(self,):
        """
        Replace colors by white.
        """
        if not self.sys_color:
            return
        self.color = False
        curses.init_pair(C_BLACK_GREEN, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(C_CYAN, curses.COLOR_WHITE, -1)
        curses.init_pair(C_RED, curses.COLOR_WHITE, -1)
        curses.init_pair(C_RED_BLACK, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(C_GREEN, curses.COLOR_WHITE, -1)
        curses.init_pair(C_YELLOW, curses.COLOR_WHITE, -1)
        curses.init_pair(C_MAGENTA, curses.COLOR_WHITE, -1)
        curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(C_BLACK_CYAN, curses.COLOR_WHITE, -1)
        curses.init_pair(C_GRAY, curses.COLOR_WHITE, -1)

    def set_color(self,):
        """
        Set colors.
        """
        if not self.sys_color:
            return
        self.color = True
        curses.init_pair(C_BLACK_GREEN, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(C_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(C_RED, curses.COLOR_RED, -1)
        curses.init_pair(C_RED_BLACK, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(C_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(C_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_MAGENTA, curses.COLOR_MAGENTA, -1)
        curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(C_BLACK_CYAN, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(C_GRAY, 0, -1)

    def clean_str(self, string):
        """
        Strip and replace some special characters.
        """
        msg = str(string)
        msg = msg.replace("\n", " ")
        msg = re.sub(r"\s+", r" ", msg)
        msg = msg.replace("FATAL:", "")
        msg = re.sub(r"^\s", r"", msg)
        msg = re.sub(r"\s$", r"", msg)
        return msg

    def check_window_size(self,):
        """
        Update window's size
        """
        (self.maxy, self.maxx) = self.win.getmaxyx()
        return

    def get_pause_msg(self,):
        """
        Returns PAUSE message, depending of the line size
        """
        msg = "PAUSE"
        line = ""
        line += " " * (int(self.maxx/2) - len(msg))
        line += msg
        line += " " * (self.maxx - len(line) - 0)
        return line

    def pause(self,):
        """
        PAUSE mode
        """
        self.print_string(self.start_line, 0, self.get_pause_msg(), self.get_curses_color(C_RED_BLACK)|curses.A_REVERSE|curses.A_BOLD)
        while 1:
            try:
                k = self.win.getch()
            except KeyboardInterrupt as e:
                raise e
            if k == ord('q'):
                curses.endwin()
                exit()
            if k == ord(' '):
                curses.flushinp()
                return 0

            if k == curses.KEY_RESIZE and self.buffer is not None and self.buffer.has_key('procs'):
                self.check_window_size()
                self.refresh_window(self.buffer['procs'], self.buffer['extras'], self.buffer['flag'], self.buffer['indent'], self.buffer['io'], self.buffer['tps'], self.buffer['size_ev'], self.buffer['total_size'])
                self.print_string(self.start_line, 0, self.get_pause_msg(), self.get_curses_color(C_RED_BLACK)|curses.A_REVERSE|curses.A_BOLD)
            curses.flushinp()

    def current_position(self,):
        """
        Display current mode
        """
        if self.mode == 'activities':
            msg = "RUNNING QUERIES"
        if self.mode == 'waiting':
            msg = "WAITING QUERIES"
        if self.mode == 'blocking':
            msg = "BLOCKING QUERIES"
        color = self.get_curses_color(C_GREEN)
        line = ""
        line += " " * (int(self.maxx/2) - len(msg))
        line += msg
        line += " " * (self.maxx - len(line) - 0)
        self.print_string(self.start_line, 0, line, color|curses.A_BOLD)

    def help_key_interactive(self,):
        """
        Display interactive mode menu bar
        """
        colno = self.print_string((self.maxy - 1), 0, "k", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Terminate the backend    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "Space", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Tag/untag the process    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "Other", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Back to activity    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "q", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Quit    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, self.add_blank(" "), self.get_curses_color(C_CYAN)|curses.A_REVERSE)

    def change_mode_interactive(self,):
        """
        Display change mode menu bar
        """
        colno = self.print_string((self.maxy - 1), 0, "F1/1", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Running queries    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "F2/2", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Waiting queries    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "F3/3", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Blocking queries ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "Space", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Pause    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "q", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Quit    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, "h", self.get_curses_color(0))
        colno += self.print_string((self.maxy - 1), colno, "Help    ", self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        colno += self.print_string((self.maxy - 1), colno, self.add_blank(" "), self.get_curses_color(C_CYAN)|curses.A_REVERSE)

    def ask_terminate_backends(self, pids,):
        """
        Ask for terminating some backends
        """
        if len(pids) == 1: 
            colno = self.print_string((self.maxy - 1), 0, "Terminate backend with PID %s ? <Y/N>" % (str(pids[0]),), self.get_curses_color(0))
        else:
            n = 0
            disp = ""
            for pid in pids:
                if n > 5:
                    disp += "..."
                    break
                if n > 0:
                    disp += ", "
                disp += "%s" % (pid,)
                n += 1
            colno = self.print_string((self.maxy - 1), 0, "Terminate backends with PID %s ? <Y/N>" % (str(disp),), self.get_curses_color(0))

        colno += self.print_string((self.maxy - 1), colno, self.add_blank(" "), self.get_curses_color(C_CYAN)|curses.A_REVERSE)
        while 1:
            try:
                k = self.win.getch()
            except KeyboardInterrupt as e:
                raise e
            # quit
            if k == ord('q'):
                curses.endwin()
                exit()
            # yes
            if k == ord('y') or k == ord('Y'):
                for pid in pids:
                    self.dc.pg_terminate_backend(str(pid),)
                self.empty_pid_yank()
                return 1
            # no
            if k == ord('n') or k == ord('N') or k == ord(' '):
                return 0
            # resize => exit
            if k == curses.KEY_RESIZE:
                return 0

    def empty_pid_yank(self,):
        """
        Empty pid list to be yanked
        """
        self.pid_yank = []

    def check_pid_yank(self,):
        """
        Check if PIDs in PGTOP_PID_YANK list are still attached
        to live processes
        """
        if len(self.pid_yank) > 0:
            for pid in self.pid_yank:
                if self.pid.count(pid) == 0:
                    self.pid_yank.remove(pid)

    def interactive(self, process, flag, indent,):
        """
        Interactive mode trigged on KEY_UP or KEY_DOWN key press
        If no key hit during 3 seconds, exit this mode
        """
        # Force truncated display
        old_verbose_mode = self.verbose_mode
        self.verbose_mode = PGTOP_TRUNCATE

        # Refresh lines with this verbose mode    
        self.scroll_window(process, flag, indent, 0)

        self.help_key_interactive()

        current_pos = 0
        offset = 0
        self.refresh_line(process[current_pos], flag, indent, 'cursor', self.lines[current_pos] - offset)
        self.win.timeout(int(1000))
        nb_nk = 0

        while 1:
            known = False
            try:
                k = self.win.getch()
            except KeyboardInterrupt as e:
                raise e
            if k == -1:
                nb_nk += 1
            # quit
            if k == ord('q'):
                curses.endwin()
                exit()
            # terminate the backend attached to this PID
            if k == ord('k'):
                if len(self.pid_yank) == 0:
                    self.ask_terminate_backends([process[current_pos]['pid']],)
                else:
                    self.ask_terminate_backends(self.pid_yank,)
                self.verbose_mode = old_verbose_mode
                curses.flushinp()
                return 0
            # Move cursor
            if k == curses.KEY_DOWN or k == curses.KEY_UP:
                nb_nk = 0
                known = True
                if k == curses.KEY_UP and current_pos > 0:
                    if (self.lines[current_pos] - offset) < (self.start_line + 3):
                        offset -= 1
                        self.scroll_window(process, flag, indent, offset)
                        self.help_key_interactive()

                    if current_pos < len(process):
                        self.refresh_line(process[current_pos], flag, indent, 'default', self.lines[current_pos] - offset)
                    current_pos -= 1
                if k == curses.KEY_DOWN and current_pos < (len(process) - 1):
                    if (self.lines[current_pos] - offset) >= (self.maxy - 2):
                        offset += 1
                        self.scroll_window(process, flag, indent, offset)
                        self.help_key_interactive()

                    if current_pos >= 0:
                        self.refresh_line(process[current_pos], flag, indent, 'default', self.lines[current_pos] - offset)
                    current_pos += 1
                self.refresh_line(process[current_pos], flag, indent, 'cursor', self.lines[current_pos] - offset)
                curses.flushinp()
                continue
            # Add/remove a PID from the yank list
            if k == ord(' '):
                known = True
                if not self.pid_yank.count(process[current_pos]['pid']) > 0:
                    self.pid_yank.append(process[current_pos]['pid'])
                else:
                    self.pid_yank.remove(process[current_pos]['pid'])

                self.refresh_line(process[current_pos], flag, indent, 'default', self.lines[current_pos] - offset)

                if current_pos < (len(process) - 1):
                    current_pos += 1
                    if (self.lines[current_pos] - offset) >= (self.maxy - 1):
                        offset += 1
                        self.scroll_window(process, flag, indent, offset)
                        self.help_key_interactive()
                self.refresh_line(process[current_pos], flag, indent, 'cursor', self.lines[current_pos] - offset)
            # Quit interactive mode
            if (k != -1 and not known) or k == curses.KEY_RESIZE:
                self.verbose_mode = old_verbose_mode
                curses.flushinp()
                return 0
            curses.flushinp()
            if nb_nk > 3:
                self.verbose_mode = old_verbose_mode
                return 0

    def poll(self, interval, flag, indent, process = None, disp_proc = None):
        """
        Wrapper around polling
        """
        if self.mode == 'activities':
            return self.poll_activities(interval, flag, indent, process, disp_proc)
        elif self.mode == 'waiting' or self.mode == 'blocking':
            return self.poll_waiting_blocking(interval, flag, indent, process, disp_proc)

    def poll_activities(self, interval, flag, indent, process = None, disp_proc = None):
        """
        Poll activities.
        """
        # Keyboard interactions
        self.win.timeout(int(1000 * self.refresh_time * interval))
        t_start = time.time()
        known = False
        do_refresh = False
        try:
            k = self.win.getch()
        except KeyboardInterrupt as e:
            raise e
        if k == ord('q'):
            curses.endwin()
            exit()
        # PAUSE mode
        if k == ord(' '):
            self.pause()
            do_refresh = True
        # interactive mode
        if (k == curses.KEY_DOWN or k == curses.KEY_UP) and len(disp_proc) > 0:
            self.interactive(disp_proc, flag, indent)
            known = False
            do_refresh = True
        # show waiting queries
        if (k == curses.KEY_F2 or k == ord('2')):
            self.mode = 'waiting'
            curses.flushinp()
            return self.poll_waiting_blocking(0, flag, indent)
        # show blocking queries
        if (k == curses.KEY_F3 or k == ord('3')):
            self.mode = 'blocking'
            curses.flushinp()
            return self.poll_waiting_blocking(0, flag, indent)
        # change verbosity
        if k == ord('v'):
            self.verbose_mode += 1
            if self.verbose_mode > 3:
                self.verbose_mode = 1
            do_refresh = True
        # turn off/on colors
        if k == ord('C'):
            if self.color is True:
                self.set_nocolor()
            else:
                self.set_color()
            do_refresh = True
        # sorts
        if k == ord('c') and (flag & PGTOP_FLAG_CPU) and self.sort != 'c':
            self.sort = 'c'
            known = True
        if k == ord('m') and (flag & PGTOP_FLAG_MEM) and self.sort != 'm':
            self.sort = 'm'
            known = True
        if k == ord('r') and (flag & PGTOP_FLAG_READ) and self.sort != 'r':
            self.sort = 'r'
            known = True
        if k == ord('w') and (flag & PGTOP_FLAG_WRITE) and self.sort != 'w':
            self.sort = 'w'
            known = True
        if k == ord('t') and self.sort != 't':
            self.sort = 't'
            known = True
        if k == ord('+') and self.refresh_time < 3:
            self.refresh_time += 1
            do_refresh = True
        if k == ord('-') and self.refresh_time > 1:
            self.refresh_time -= 1
            do_refresh = True
        # Refresh
        if k == ord('R'):
            known = True
        
        if k == ord('u'):
            self.empty_yank_pid()
            known = True

        if k == ord('h'):
            self.help_window()
            do_refresh = True

        if k == curses.KEY_RESIZE and self.buffer is not None and self.buffer.has_key('procs'):
            do_refresh = True

        if do_refresh is True and self.buffer is not None and self.buffer.has_key('procs'):
            self.check_window_size()
            self.refresh_window(self.buffer['procs'], self.buffer['extras'], self.buffer['flag'], self.buffer['indent'], self.buffer['io'], self.buffer['tps'], self.buffer['size_ev'], self.buffer['total_size'])

        curses.flushinp()
        t_end = time.time()
        if k > -1 and not known and (t_end - t_start) < (self.refresh_time * interval):
            return self.poll_activities(((self.refresh_time * interval) - (t_end - t_start))/self.refresh_time, flag, indent, process, disp_proc)

        # poll postgresql activity
        queries =  self.dc.pg_get_activities()
        self.pid = []
        if self.is_local:
            # get resource usage for each process
            new_procs = self.dc.sys_get_proc(queries, self.is_local)

            procs = []
            read_bytes_delta = 0
            write_bytes_delta = 0
            read_count_delta = 0
            write_count_delta = 0
            for pid, new_proc in new_procs.items():
                try:
                    if process.has_key(pid):
                        n_io_time = time.time()
                        # Getting informations from the previous loop
                        proc = process[pid]
                        # Update old process with new informations
                        proc.duration = new_proc.duration
                        proc.query = new_proc.query
                        proc.client = new_proc.client
                        proc.wait = new_proc.wait
                        proc.setExtra('io_wait', new_proc.getExtra('io_wait'))
                        proc.setExtra('read_delta', (new_proc.getExtra('io_counters').read_bytes - proc.getExtra('io_counters').read_bytes)/(n_io_time - proc.getExtra('io_time')))
                        proc.setExtra('write_delta', (new_proc.getExtra('io_counters').write_bytes - proc.getExtra('io_counters').write_bytes)/(n_io_time - proc.getExtra('io_time')))
                        proc.setExtra('io_counters', new_proc.getExtra('io_counters'))
                        proc.setExtra('io_time', n_io_time)
 
                        # Global io counters
                        read_bytes_delta  += proc.getExtra('read_delta')
                        write_bytes_delta += proc.getExtra('write_delta')
                    else:
                        # No previous information about this process
                        proc = new_proc

                    if not self.pid.count(pid):
                        self.pid.append(pid)

                    proc.setExtra('mem_percent', proc.getExtra('psutil_proc').get_memory_percent())
                    proc.setExtra('cpu_percent', proc.getExtra('psutil_proc').get_cpu_percent(interval=0))
                    new_procs[pid] = proc
                    procs.append({'pid': pid, 'database': proc.database, 'user':proc.user, 'client': proc.client, 'cpu': proc.getExtra('cpu_percent'), 'mem': proc.getExtra('mem_percent'), 'read': proc.getExtra('read_delta'), 'write': proc.getExtra('write_delta'), 'query': proc.query, 'duration': self.dc.get_duration(proc.duration), 'wait': proc.wait, 'io_wait': proc.getExtra('io_wait')})

                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    pass
                except Exception as e:
                    raise e
            # store io counters
            if read_bytes_delta > 0:
                read_count_delta  += int(read_bytes_delta/self.fs_blocksize)
            if write_bytes_delta > 0:
                write_count_delta += int(write_bytes_delta/self.fs_blocksize)
            self.dc.set_global_io_counters(read_bytes_delta, write_bytes_delta, read_count_delta, write_count_delta)
        else:
            procs = []
            new_procs = None
            for q in queries:
                if not this.pid.count(q['pid']):
                    this.pid.append(q['pid'])
                procs.append({'pid': q['pid'], 'database': q['database'], 'user': q['user'], 'client': q['client'], 'query': q['query'], 'duration': self.dc.get_duration(q['duration']), 'wait': q['wait']})

        # return processes sorted by query duration
        if self.sort == 't':
            # TIME
            disp_procs = sorted(procs, key=lambda p: p['duration'], reverse=True)
        elif self.sort == 'c':
            # CPU
            disp_procs = sorted(procs, key=lambda p: p['cpu'], reverse=True)
        elif self.sort == 'm':
            # MEM
            disp_procs = sorted(procs, key=lambda p: p['mem'], reverse=True)
        elif self.sort == 'r':
            # READ
            disp_procs = sorted(procs, key=lambda p: p['read'], reverse=True)
        elif self.sort == 'w':
            # WRITE
            disp_procs = sorted(procs, key=lambda p: p['write'], reverse=True)
        else:
            disp_procs = sorted(procs, key=lambda p: p['duration'], reverse=True)

        self.check_pid_yank()

        return (disp_procs, new_procs)

    def poll_waiting_blocking(self, interval, flag, indent, process = None, disp_proc = None):
        """
        Poll waiting or blocking queries
        """
        t_start = time.time()
        do_refresh = False
        known = False
        # Keyboard interactions
        self.win.timeout(int(1000 * self.refresh_time * interval))

        try:
            k = self.win.getch()
        except KeyboardInterrupt as e:
            raise e
        if k == ord('q'):
            curses.endwin()
            exit()
        # PAUSE mode
        if k == ord(' '):
            self.pause()
            do_refresh = True
        # interactive mode
        if (k == curses.KEY_DOWN or k == curses.KEY_UP) and len(disp_proc) > 0:
            self.interactive(disp_proc, flag, indent)
            known = True
        # activities mode
        if (k == curses.KEY_F1 or k == ord('1')):
            self.mode = 'activities'
            curses.flushinp()
            queries = self.dc.pg_get_activities()
            procs = self.dc.sys_get_proc(queries, self.is_local)
            return self.poll_activities(0, flag, indent, procs)
        # Waiting queries
        if ((k == curses.KEY_F2 or k == ord('2')) and self.mode != 'waiting'):
            self.mode = 'waiting'
            curses.flushinp()
            return self.poll_waiting_blocking(0,flag, indent)
        # blocking queries
        if ((k == curses.KEY_F3 or k == ord('3')) and self.mode != 'blocking'):
            self.mode = 'blocking'
            curses.flushinp()
            return self.poll_waiting_blocking(0, flag, indent)
        # change verbosity
        if k == ord('v'):
            self.verbose_mode += 1
            if self.verbose_mode > 3:
                self.verbose_mode = 1
            do_refresh = True
        # turnoff/on colors
        if k == ord('C'):
            if self.color is True:
                self.set_nocolor()
            else:
                self.set_color()
            do_refresh = True
        # sorts
        if k == ord('t') and self.sort != 't':
            self.sort = 't'
            known = True
        if k == ord('+') and self.refresh_time < 3:
            self.refresh_time += 1
        if k == ord('-') and self.refresh_time > 1:
            self.refresh_time -= 1

        if k == ord('h'):
            self.help_window()
            do_refresh = True

        # Refresh
        if k == ord('R'):
            known = True

        if k == curses.KEY_RESIZE and self.buffer is not None and self.buffer.has_key('procs'):
            do_refresh = True

        if do_refresh is True and self.buffer is not None and self.buffer.has_key('procs'):
            self.check_window_size()
            self.refresh_window(self.buffer['procs'], self.buffer['extras'], self.buffer['flag'], self.buffer['indent'], self.buffer['io'], self.buffer['tps'], self.buffer['size_ev'], self.buffer['total_size'])

        curses.flushinp()
        t_end = time.time()
        if k > -1 and not known and (t_end - t_start) < (self.refresh_time * interval):
            return self.poll_waiting_blocking(((self.refresh_time * interval) - (t_end - t_start))/self.refresh_time, flag, indent, process, disp_proc)

        # poll postgresql activity
        if self.mode == 'waiting':
            queries =  self.dc.pg_get_waiting()
        else:
            queries =  self.dc.pg_get_blocking()

        new_procs = {}
        for q in queries:
            new_procs[q['pid']] = q
            new_procs[q['pid']]['duration'] = self.dc.get_duration(q['duration'])

        # return processes sorted by query duration
        if self.sort == 't':
            # TIME
            disp_procs = sorted(queries, key=lambda q: q['duration'], reverse=True)
        else:
            disp_procs = sorted(queries, key=lambda q: q['duration'], reverse=True)

        return (disp_procs, new_procs)

    def print_string(self, lineno, colno, word, color = 0):
        """
        Print a string at position (lineno, colno) and returns its length.
        """
        try:
            self.win.addstr(lineno, colno, word, color)
        except curses.error:
            pass
        return len(word)

    def add_blank(self, line, offset = 0):
        """
        Complete string with white spaces from the end of string to the end of line.
        """
        line += " " * (self.maxx - (len(line) + offset))
        return line

    def bytes2human(self, n):
        """
        Convert a size into a human readable format.
        """
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        ne = ''
        if n < 0:
            n = n * -1
            ne = '-'
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i+1)*10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = "%.2f" % float(float(n) / float(prefix[s]))
                return "%s%s%s" % (ne, value, s)
        return "%s%.2fB" % (ne, n)

    def get_indent(self, flag):
        """
        Returns identation for Query column.
        """
        indent = ''
        r = [0] * self.max_ncol
        for _, val in PGTOP_COLS[self.mode].items():
            if val['mandatory'] or (not val['mandatory'] and val['flag'] & flag):
                r[int(val['n'])] = val
        for val in r:
            if val is not 0:
                if val['name'] is not 'Query':
                    indent += val['template_h'] % ' '
        return indent

    def print_cols_header(self, flag):
        """
        Print columns headers
        """
        line = ''
        disp = ''
        x = 0
        r = [0] * self.max_ncol
        color = self.get_curses_color(C_GREEN)
        for _, val in PGTOP_COLS[self.mode].items():
            if val['mandatory'] or (not val['mandatory'] and val['flag'] & flag):
                r[int(val['n'])] = val
        for val in r:
            if val is not 0:
                disp = val['template_h'] % val['name']
                if ((val['name'] == "CPU%" and self.sort == 'c') or
                    (val['name'] == "MEM%" and self.sort == 'm') or
                    (val['name'] == "READ/s" and self.sort == 'r') or
                    (val['name'] == "WRITE/s" and self.sort == 'w') or
                    (val['name'] == "TIME+" and self.sort == 't')):
                    color_highlight = self.get_curses_color(C_CYAN)
                else:
                    color_highlight = color
                if val['name'] == "Query":
                    disp += " " * (self.maxx - (len(line) + len(disp)))
                line += disp
                self.print_string(self.lineno, x, disp, color_highlight|curses.A_REVERSE)
                x += len(disp)
        self.lineno += 1

    def print_header(self, pg_version, hostname, user, host, port, io, tps, size_ev, total_size):
        """
        Print window header
        """
        self.lineno = 0
        colno = 0
        version = " %s" % (pg_version)
        colno = self.print_string(self.lineno, colno, version)
        colno += self.print_string(self.lineno, colno, " - ")
        colno += self.print_string(self.lineno, colno, hostname, curses.A_BOLD)
        colno += self.print_string(self.lineno, colno, " - ")
        colno += self.print_string(self.lineno, colno, user, self.get_curses_color(C_CYAN))
        colno += self.print_string(self.lineno, colno, "@")
        colno += self.print_string(self.lineno, colno, host, self.get_curses_color(C_CYAN))
        colno += self.print_string(self.lineno, colno, ":")
        colno += self.print_string(self.lineno, colno, port, self.get_curses_color(C_CYAN))
        colno += self.print_string(self.lineno, colno, " - Ref.: %ss" % (self.refresh_time,))
        colno = 0
        self.lineno += 1
        colno += self.print_string(self.lineno, colno, "  Size: ")
        colno += self.print_string(self.lineno, colno, "%7s" % (self.bytes2human(total_size),),)
        colno += self.print_string(self.lineno, colno, " - %9s/s" % (self.bytes2human(size_ev),),)
        colno += self.print_string(self.lineno, colno, "     | TPS: ")
        colno += self.print_string(self.lineno, colno, "%11s" % (tps,), self.get_curses_color(C_GREEN)|curses.A_BOLD)

        # If not local connection, don't get and display system informations
        if not self.is_local:
            return

        # Get memory & swap usage
        (mem_used_per, mem_used, mem_total, swap_used_per, swap_used, swap_total) = self.dc.get_mem_swap()
        # Get load average
        (av1, av2, av3) = self.dc.get_load_average()

        self.lineno += 1
        line = "  Mem.: %5s0%% - %9s/%s" % (mem_used_per, self.bytes2human(mem_used), self.bytes2human(mem_total))
        colno_io = self.print_string(self.lineno, 0, line)

        if (int(io['read_count'])+int(io['write_count'])) > self.max_iops:
            self.max_iops = (int(io['read_count'])+int(io['write_count']))

        line_io = " | IO Max: %8s/s" % (self.max_iops,)
        colno = self.print_string(self.lineno, colno_io, line_io)

        # swap usage
        line = "  Swap: %5s0%% - %9s/%s" % (swap_used_per, self.bytes2human(swap_used), self.bytes2human(swap_total))
        self.lineno += 1
        colno = self.print_string(self.lineno, 0, line)
        line_io = " | Read : %10s/s - %6s/s" % (self.bytes2human(io['read_bytes']), int(io['read_count']),)
        colno = self.print_string(self.lineno, colno_io, line_io)

        # load average, uptime
        line = "  Load:   %.2f %.2f %.2f" % (av1, av2, av3)
        self.lineno += 1
        colno = self.print_string(self.lineno, 0, line)
        line_io = " | Write: %10s/s - %6s/s" % (self.bytes2human(io['write_bytes']), int(io['write_count']),)
        colno = self.print_string(self.lineno, colno_io, line_io)

    def help_window(self,):
        """
        Display help window
        """
        self.win.erase()
        self.lineno = 0
        text = "pg_activity %s - (c) 2012-2013 Julien Tachoires" % (self.version)
        self.print_string(self.lineno, 0, text, self.get_curses_color(C_GREEN)|curses.A_BOLD)
        self.lineno += 1
        text = "Released under PostgreSQL License."
        self.print_string(self.lineno, 0, text)
        self.lineno += 2
        self.display_help_key(self.lineno, 00, "Up/Down", "scroll process list")
        self.display_help_key(self.lineno, 45, "      C", "activate/deactivate colors")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "  Space", "pause")
        self.display_help_key(self.lineno, 45, "      r", "sort by READ/s desc. (activities)")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "      v", "change display mode")
        self.display_help_key(self.lineno, 45, "      w", "sort by WRITE/s desc. (activities)")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "      q", "quit")
        self.display_help_key(self.lineno, 45, "      c", "sort by CPU% desc. (activities)")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "      +", "increase refresh time (max:3)")
        self.display_help_key(self.lineno, 45, "      m", "sort by MEM% desc. (activities)")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "      -", "decrease refresh time (min:1)")
        self.display_help_key(self.lineno, 45, "      t", "sort by TIME+ desc. (activities)")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "      R", "force refresh")
        self.lineno += 1
        self.print_string(self.lineno, 0, "Mode")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "   F1/1", "running queries")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "   F2/2", "waiting queries")
        self.lineno += 1
        self.display_help_key(self.lineno, 00, "   F3/3", "blocking queries")

        self.lineno += 2
        self.print_string(self.lineno, 0, "Press any key to exit.")
        self.win.timeout(-1)
        try:
            self.win.getch()
        except KeyboardInterrupt as e:
            raise e

    def display_help_key(self, lineno, colno, key, help):
        """
        Display help key
        """
        l = self.print_string(lineno, colno, key, self.get_curses_color(C_CYAN)|curses.A_BOLD)
        l2 = self.print_string(lineno, colno + l, ": %s" % (help,))
        return (colno + l + l2)

    def refresh_window(self, procs, extras, flag, indent, io, tps, size_ev, total_size):
        """
        Refresh the window
        """

        self.lines = []
        (pg_version, hostname, user, host, port) = extras
        self.win.erase()
        self.print_header(pg_version, hostname, user, host, port, io, tps, size_ev, total_size)
        self.lineno += 2
        line_trunc = self.lineno
        self.current_position()
        self.print_cols_header(flag)
        for p in procs:
            try:
                self.refresh_line(p, flag, indent, 'default')
                line_trunc += 1
                self.lines.append(line_trunc)
            except curses.error:
                break
        for l in range(self.lineno, (self.maxy-1)):
            self.print_string(l, 0, self.add_blank(" "))
        self.change_mode_interactive()

    def scroll_window(self, procs, flag, indent, offset = 0):
        """
        Scroll the window
        """
        self.lineno = (self.start_line + 2)
        pos = 0
        for p in procs:
            if pos >= offset and self.lineno < (self.maxy - 1):
                self.refresh_line(p, flag, indent, 'default')
            pos += 1
        for l in range(self.lineno, (self.maxy-1)):
            self.print_string(l, 0, self.add_blank(" "))

    def refresh_line(self, p, flag, indent, typecolor = 'default', line = None):
        """
        Refresh a line for activities mode
        """
        if line is not None:
            l_lineno = line
        else:
            l_lineno = self.lineno

        if typecolor == 'default' and self.pid_yank.count(p['pid']) > 0:
            typecolor = 'yellow'

        colno = 0
        colno += self.print_string(l_lineno, colno, "%-6s " % (p['pid'],), self.line_colors['pid'][typecolor])
        if flag & PGTOP_FLAG_DATABASE:
            colno += self.print_string(l_lineno, colno, PGTOP_COLS[self.mode]['database']['template_h'] % (p['database'][:16],), self.line_colors['database'][typecolor])
        if self.mode == 'activities':
            if flag & PGTOP_FLAG_USER:
                colno += self.print_string(l_lineno, colno, "%16s " % (str(p['user'])[:16],), self.line_colors['user'][typecolor])
            if flag & PGTOP_FLAG_CLIENT:
                colno += self.print_string(l_lineno, colno, "%16s " % (str(p['client'])[:16],), self.line_colors['client'][typecolor])
            if flag & PGTOP_FLAG_CPU:
                colno += self.print_string(l_lineno, colno, "%6s " % (p['cpu'],), self.line_colors['cpu'][typecolor])
            if flag & PGTOP_FLAG_MEM:
                colno += self.print_string(l_lineno, colno, "%4s " % (round(p['mem'], 1),), self.line_colors['mem'][typecolor])
            if flag & PGTOP_FLAG_READ:
                colno += self.print_string(l_lineno, colno, "%8s " % (self.bytes2human(p['read']),), self.line_colors['read'][typecolor])
            if flag & PGTOP_FLAG_WRITE:
                colno += self.print_string(l_lineno, colno, "%8s " % (self.bytes2human(p['write']),), self.line_colors['write'][typecolor])
        elif self.mode == 'waiting' or self.mode == 'blocking':
            if flag & PGTOP_FLAG_RELATION:
                colno += self.print_string(l_lineno, colno, "%9s " % (str(p['relation'])[:9],), self.line_colors['relation'][typecolor])
            if flag & PGTOP_FLAG_TYPE:
                colno += self.print_string(l_lineno, colno, "%16s " % (str(p['type'])[:16],), self.line_colors['type'][typecolor])
            if flag & PGTOP_FLAG_MODE:
                if p['mode'] == 'ExclusiveLock' or p['mode'] == 'RowExclusiveLock' or p['mode'] == 'AccessExclusiveLock':
                    colno += self.print_string(l_lineno, colno, "%16s " % (str(p['mode'])[:16],), self.line_colors['mode_red'][typecolor])
                else:
                    colno += self.print_string(l_lineno, colno, "%16s " % (str(p['mode'])[:16],), self.line_colors['mode_yellow'][typecolor])

        if flag & PGTOP_FLAG_TIME:
            if p['duration'] >= 1:
                ctime = timedelta(seconds=float(p['duration']))
                mic = '%.6d' % (ctime.microseconds)
                ctime = "%s:%s.%s" % (str((ctime.seconds // 60)).zfill(2), str((ctime.seconds % 60)).zfill(2), str(mic)[:2])
            if p['duration'] < 1:
                colno += self.print_string(l_lineno, colno, " %.6f " % (p['duration'],), self.line_colors['time_green'][typecolor])
            elif p['duration'] >= 1 and p['duration'] < 3:
                colno += self.print_string(l_lineno, colno, "%9s " % (ctime,), self.line_colors['time_yellow'][typecolor])
            else:
                colno += self.print_string(l_lineno, colno, "%9s " % (ctime,), self.line_colors['time_red'][typecolor])
        if self.mode == 'activities' and flag & PGTOP_FLAG_WAIT:
            if p['wait']:
                colno += self.print_string(l_lineno, colno, "%2s " % ('Y',), self.line_colors['wait_red'][typecolor])
            else:
                colno += self.print_string(l_lineno, colno, "%2s " % ('N',), self.line_colors['wait_green'][typecolor])

        if self.mode == 'activities' and flag & PGTOP_FLAG_IOWAIT:
            if p['io_wait'] == 'Y':
                colno += self.print_string(l_lineno, colno, "%4s " % ('Y',), self.line_colors['wait_red'][typecolor])
            else:
                colno += self.print_string(l_lineno, colno, "%4s " % ('N',), self.line_colors['wait_green'][typecolor])

        dif = self.maxx - len(indent) - 1
        if self.verbose_mode == PGTOP_TRUNCATE:
            query = p['query'][:dif]
            colno += self.print_string(l_lineno, colno, " %s" % (self.add_blank(query, len(indent)+1),), self.line_colors['query'][typecolor])
        elif self.verbose_mode == PGTOP_WRAP or  self.verbose_mode == PGTOP_WRAP_NOINDENT:
            query = p['query']
            query_wrote = ''
            offset = 0
            if len(query) > dif and dif > 1:
                query_part = query[offset:dif]
                self.print_string(l_lineno, colno, " %s" % (self.add_blank(query_part, len(indent)+1),), self.line_colors['query'][typecolor])
                query_wrote += query_part
                offset = len(query_wrote)
                if self.verbose_mode == PGTOP_WRAP_NOINDENT:
                    dif = self.maxx
                    p_indent = ""
                else:
                    p_indent = indent
                while (len(query) - offset > 0):
                    query_part = query[offset:(dif+offset)]
                    l_lineno += 1
                    self.lineno += 1
                    self.print_string(l_lineno, 0, "%s" % (self.add_blank(p_indent + " " + query_part, len(indent)+1)), self.line_colors['query'][typecolor])
                    query_wrote += query_part
                    offset = len(query_wrote)
            else:
                colno += self.print_string(l_lineno, colno, " %s" % (self.add_blank(query, len(indent)),), self.line_colors['query'][typecolor])
        self.lineno += 1
