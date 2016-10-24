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

from __future__ import print_function

import curses
import re
import time
import sys
from datetime import timedelta
import pgactivity
from pgactivity.Data import Data
import psutil
from getpass import getpass
import operator
from functools import reduce, partial
if sys.version_info[0] == 2:
    from itertools import imap as map, ifilter as filter

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
        'pid'       : {
            'n':  1,
            'name': 'PID',
            'template_h': '%-6s ',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
        'database': {
            'n':  2,
            'name': 'DATABASE',
            'template_h': '%-16s ',
            'flag': PGTOP_FLAG_DATABASE,
            'mandatory': False
        },
        'user': {
            'n':  3,
            'name': 'USER',
            'template_h': '%16s ',
            'flag': PGTOP_FLAG_USER,
            'mandatory': False
        },
        'client': {
            'n':  4,
            'name': 'CLIENT',
            'template_h': '%16s ',
            'flag': PGTOP_FLAG_CLIENT,
            'mandatory': False
        },
        'cpu': {
            'n':  5,
            'name': 'CPU%',
            'template_h': '%6s ',
            'flag': PGTOP_FLAG_CPU,
            'mandatory': False
        },
        'mem': {
            'n':  6,
            'name': 'MEM%',
            'template_h': '%4s ',
            'flag': PGTOP_FLAG_MEM,
            'mandatory': False
        },
        'read': {
            'n':  7,
            'name': 'READ/s',
            'template_h': '%8s ',
            'flag': PGTOP_FLAG_READ,
            'mandatory': False
        },
        'write': {
            'n':  8,
            'name': 'WRITE/s',
            'template_h': '%8s ',
            'flag': PGTOP_FLAG_WRITE,
            'mandatory': False
        },
        'time': {
            'n':  9,
            'name': 'TIME+',
            'template_h': '%9s ',
            'flag': PGTOP_FLAG_TIME,
            'mandatory': False
        },
        'wait': {
            'n': 10,
            'name': 'W',
            'template_h': '%2s ',
            'flag': PGTOP_FLAG_WAIT,
            'mandatory': False
        },
        'iowait': {
            'n': 11,
            'name': 'IOW',
            'template_h': '%4s ',
            'flag': PGTOP_FLAG_IOWAIT,
            'mandatory': False
        },
        'query': {
            'n': 12,
            'name': 'Query',
            'template_h': ' %2s',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
    },
    'waiting': {
        'pid': {
            'n': 1,
            'name': 'PID',
            'template_h': '%-6s ',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
        'database': {
            'n': 2,
            'name': 'DATABASE',
            'template_h': '%-16s ',
            'flag': PGTOP_FLAG_DATABASE,
            'mandatory': False
        },
        'relation': {
            'n': 3,
            'name': 'RELATION',
            'template_h': '%9s ',
            'flag': PGTOP_FLAG_RELATION,
            'mandatory': False
        },
        'type': {
            'n': 4,
            'name': 'TYPE',
            'template_h': '%16s ',
            'flag': PGTOP_FLAG_TYPE,
            'mandatory': False
        },
        'mode': {
            'n': 5,
            'name': 'MODE',
            'template_h': '%16s ',
            'flag': PGTOP_FLAG_MODE,
            'mandatory': False
        },
        'time': {
            'n': 6,
            'name': 'TIME+',
            'template_h': '%9s ',
            'flag': PGTOP_FLAG_TIME,
            'mandatory': False
        },
        'query': {
            'n': 7,
            'name': 'Query',
            'template_h': ' %2s',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
    },
    'blocking': {
        'pid': {
            'n': 1,
            'name': 'PID',
            'template_h': '%-6s ',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
        'database': {
            'n': 2,
            'name': 'DATABASE',
            'template_h': '%-16s ',
            'flag': PGTOP_FLAG_DATABASE,
            'mandatory': False
        },
        'relation': {
            'n': 3,
            'name': 'RELATION',
            'template_h': '%9s ',
            'flag': PGTOP_FLAG_RELATION,
            'mandatory': False
        },
        'type': {
            'n': 4,
            'name': 'TYPE',
            'template_h': '%16s ',
            'flag': PGTOP_FLAG_TYPE,
            'mandatory': False
        },
        'mode': {
            'n': 5,
            'name': 'MODE',
            'template_h': '%16s ',
            'flag': PGTOP_FLAG_MODE,
            'mandatory': False
        },
        'time': {
            'n': 6,
            'name': 'TIME+',
            'template_h': '%9s ',
            'flag': PGTOP_FLAG_TIME,
            'mandatory': False
        },
        'query': {
            'n': 7,
            'name': 'Query',
            'template_h': ' %2s',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
    }
}

def bytes2human(num):
    """
    Convert a size into a human readable format.
    """
    symbols = tuple(enumerate('BKMGTPEZY'))
    nume, num = ('-' if num<0 else ''), abs(num)

    dt = ((1<<(pos*10), sym) for pos, sym in reversed(symbols))
    filtered = filter(lambda elem: num>=elem[0], dt)
    val, unit_symbol = next(filtered)  # 1st elem for which num>=elem[0]
    value = "%.2f" % (float(num)/val)
    return "%s%s%s" % (nume, value, unit_symbol)

class UI:
    """
    UI class
    """
    def __init__(self, version):
        """
        Constructor.
        """
        self.version = pgactivity.__version__
        self.win = None
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
        # Init uibuffer
        self.uibuffer = None
        # Refresh time
        self.refresh_time = 2
        # Maximum DATABASE columns header length
        self.max_db_length = 16
        # Array containing pid of processes to yank
        self.pid_yank = []
        self.pid = []
        # Data collector
        self.data = Data()
        # Maximum number of column
        self.max_ncol = PGTOP_MAX_NCOL
        # Default filesystem blocksize
        self.fs_blocksize = 4096
        # Init curses
        # self.__init_curses()

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

    def set_buffer(self, uibuffer):
        """
        Set self.uibuffer
        """
        self.uibuffer = uibuffer

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
        Initialize curses environment and colors.
        """
        self.__init_curses()
        # Columns colors definition
        colors = [0, C_CYAN, C_RED, C_YELLOW, C_GREEN]
        zero, cyan, red, yellow, green = map(self.__get_color, colors)
        bold = curses.A_BOLD

        bold_gray = self.__get_color(C_GRAY)|bold
        bold_green = self.__get_color(C_GREEN)|bold
        bold_red = self.__get_color(C_RED)|bold
        bold_yellow = self.__get_color(C_YELLOW)|bold
        reverse_cyan = self.__get_color(C_CYAN)|curses.A_REVERSE

        line_colors = {
            'pid':          {'default': cyan},
            'database':     {'default': bold_gray},
            'user':         {'default': bold_gray},
            'client':       {'default': cyan},
            'cpu':          {'default': zero},
            'mem':          {'default': zero},
            'read':         {'default': zero},
            'write':        {'default': zero},
            'time_red':     {'default': red},
            'time_yellow':  {'default': yellow},
            'time_green':   {'default': green},
            'wait_green':   {'default': bold_green},
            'wait_red':     {'default': bold_red},
            'query':        {'default': zero},
            'relation':     {'default': cyan},
            'type':         {'default': zero},
            'mode_yellow':  {'default': bold_yellow},
            'mode_red':     {'default': bold_red},
        }

        for col in line_colors:
            line_colors[col].setdefault('cursor', reverse_cyan)
            line_colors[col].setdefault('yellow', bold_yellow)

        self.line_colors = line_colors

    def __init_curses(self,):
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
        flag_values = (
            PGTOP_FLAG_DATABASE, PGTOP_FLAG_USER, PGTOP_FLAG_CLIENT,
            PGTOP_FLAG_CPU, PGTOP_FLAG_MEM, PGTOP_FLAG_READ, PGTOP_FLAG_WRITE,
            PGTOP_FLAG_TIME, PGTOP_FLAG_WAIT, PGTOP_FLAG_RELATION,
            PGTOP_FLAG_TYPE, PGTOP_FLAG_MODE, PGTOP_FLAG_IOWAIT,)
        flag = reduce(operator.or_, flag_values)

        noflag_opts = ((PGTOP_FLAG_DATABASE, options.nodb),
                       (PGTOP_FLAG_USER,     options.nouser),
                       (PGTOP_FLAG_CPU,      options.nocpu),
                       (PGTOP_FLAG_CLIENT,   options.noclient),
                       (PGTOP_FLAG_MEM,      options.nomem),
                       (PGTOP_FLAG_READ,     options.noread),
                       (PGTOP_FLAG_WRITE,    options.nowrite),
                       (PGTOP_FLAG_TIME,     options.notime),
                       (PGTOP_FLAG_WAIT,     options.nowait),)
        flag -= sum(fl for fl, opt in noflag_opts if opt is True)

        # Remove some if no running against local pg server.
        unavailable = (PGTOP_FLAG_CPU,
                       PGTOP_FLAG_MEM,
                       PGTOP_FLAG_READ,
                       PGTOP_FLAG_WRITE,
                       PGTOP_FLAG_IOWAIT) if not self.get_is_local() else ()

        return flag - sum(i for i in unavailable if flag&i)

    def __get_color(self, color):
        """
        Wrapper around curses.color_pair()
        """
        return curses.color_pair(color) if self.sys_color else 0

    def set_max_db_length(self, new_length):
        """
        Set new DATABASE column length
        """
        global PGTOP_COLS
        nl = 16 if new_length>16 else max(new_length, 8)
        self.max_db_length = nl

        str_nl = '%-'+str(nl)+'s '
        for screen in ('activities', 'database', 'template_h'):
            PGTOP_COLS[screen]['database']['template_h'] = str_nl

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
        except AttributeError:
            # Curses not initialized yet
            return
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
        print("FATAL: Killed with signal %s ." % (str(signal),))
        print("%s" % (str(frame),))
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
        return msg.strip()

    def ask_password(self, ):
        """
        Ask for PostgreSQL user password
        """
        password = getpass()
        return password

    def check_window_size(self,):
        """
        Update window's size
        """
        (self.maxy, self.maxx) = self.win.getmaxyx()

    def __get_msg(self, text):
        """
        Returns PAUSE message, depending of the line size
        """
        start = " " * (self.maxx//2 - len(msg))
        end = " " * (self.maxx - len(start) -len(msg))
        return start + text + end

    def __print_pause_msg(self):
        self.__putstrLn(
            self.start_line,
            0,
            self.__get_msg("PAUSE"),
            self.__get_color(C_RED_BLACK)|curses.A_REVERSE|curses.A_BOLD)

    def __pause(self,):
        """
        PAUSE mode
        """
        self.__print_pause_msg()
        while 1:
            try:
                k = self.win.getch()
            except KeyboardInterrupt as err:
                raise err
            if k == ord('q'):
                curses.endwin()
                exit()
            if k == ord(' '):
                curses.flushinp()
                return 0

            if k == curses.KEY_RESIZE:
                if self.uibuffer is not None and 'procs' in self.uibuffer:
                    self.check_window_size()
                    param_keys = (
                        'procs', 'extras', 'flag', 'indent', 'io', 'tps',
                        'size_ev', 'total_size')
                    params = [self.uibuffer[p] for p in param_keys]
                    self.refresh_window(*params)
                    self.__print_pause_msg()
            curses.flushinp()

    def __current_position(self,):
        """
        Display current mode
        """
        msg_map = dict(
                    activities="RUNNING QUERIES",
                    waiting="WAITING QUERIES",
                    blocking="BLOCKING QUERIES")
        msg = msg_map[self.mode]
        color = self.__get_color(C_GREEN)
        line = self.__get_msg(msg)

        self.__putstrLn(self.start_line, 0, line, color|curses.A_BOLD)

    def __help_key_interactive(self,):
        """
        Display interactive mode menu bar
        """

        cyan = self.__get_color(C_CYAN)
        params = (
            ("k", self.__get_color(0)),
            ("Terminate the backend    ", cyan|curses.A_REVERSE),
            ("Space", self.__get_color(0)),
            ("Tag/untag the process    ", cyan|curses.A_REVERSE),
            ("Other", self.__get_color(0)),
            ("Back to activity    ", cyan|curses.A_REVERSE),
            ("q", self.__get_color(0)),
            ("Quit    ", cyan|curses.A_REVERSE),
            (self.__add_blank(" "), cyan|curses.A_REVERSE),
        )

        self.__print_line(self.maxy-1, 0, params)

    def __change_mode_interactive(self,):
        """
        Display change mode menu bar
        """

        
        cyan_reverse = self.__get_color(C_CYAN)|curses.A_REVERSE
        zero = self.__get_color(0)
        params = (
            ("F1/1", zero),
            ("Running queries    ", cyan_reverse),
            ("F2/2", zero),
            ("Waiting queries    ", cyan_reverse),
            ("F3/3", zero),
            ("Blocking queries ", cyan_reverse),
            ("Space", zero),
            ("Pause    ", cyan_reverse),
            ("q", zero),
            ("Quit    ", cyan_reverse),
            ("h", zero),
            ("Help    ", cyan_reverse),
            (self.__add_blank(" "), cyan_reverse),
            )

        self.__print_line(self.maxy-1, 0, params)

    def __ask_terminate_backends(self, pids,):
        """
        Ask for terminating some backends
        """
        xs = ('%s' % pid for pid in pids)
        (xs, endln) = (xs[-1], '...') if len(xs)>5 else (xs, '')
        disp = ', '.join(xs) + endln
        word = "Terminate backend with PID %s ? <Y/N>" % disp
        blank = self.__add_blank(" ")

        params = ((word, self.__get_color(0)),
                  (blank, self.__get_color(C_CYAN)|curses.A_REVERSE),)
        self.__print_line(self.maxy-1, 0, params)

        while 1:
            try:
                key = self.win.getch()
            except KeyboardInterrupt as err:
                raise err
            # quit
            if key == ord('q'):
                curses.endwin()
                exit()
            # yes
            if key == ord('y') or key == ord('Y'):
                for pid in pids:
                    self.data.pg_terminate_backend(str(pid),)
                self.__empty_pid_yank()
                return 1
            # no
            if key in map(ord, 'nN '):
                return 0
            # resize => exit
            if key == curses.KEY_RESIZE:
                return 0

    def __empty_pid_yank(self,):
        """
        Empty pid list to be yanked
        """
        self.pid_yank = []

    def __check_pid_yank(self,):
        """
        Check if PIDs in PGTOP_PID_YANK list are still attached
        to live processes
        """
        filtered = [pid for pid in self.pid_yank if self.pid.count(pid)!=0]
        self.pid_yank = filtered


    def __interactive(self, process, flag, indent,):
        """
        Interactive mode trigged on KEY_UP or KEY_DOWN key press
        If no key hit during 3 seconds, exit this mode
        """
        # Force truncated display
        old_verbose_mode = self.verbose_mode
        self.verbose_mode = PGTOP_TRUNCATE

        # Refresh lines with this verbose mode
        self.__scroll_window(process, flag, indent, 0)

        self.__help_key_interactive()

        current_pos = 0
        offset = 0
        self.__refresh_line(
            process[current_pos],
            flag,
            indent,
            'cursor',
            self.lines[current_pos] - offset)
        self.win.timeout(int(1000))
        nb_nk = 0

        while 1:
            known = False
            try:
                k = self.win.getch()
            except KeyboardInterrupt as err:
                raise err
            if k == -1:
                nb_nk += 1
            # quit
            if k == ord('q'):
                curses.endwin()
                exit()
            # terminate the backend attached to this PID
            if k == ord('k'):
                if len(self.pid_yank) == 0:
                    self.__ask_terminate_backends( \
                        [process[current_pos]['pid']],)
                else:
                    self.__ask_terminate_backends(self.pid_yank,)
                self.verbose_mode = old_verbose_mode
                curses.flushinp()
                return 0
            # Move cursor
            if k == curses.KEY_DOWN or k == curses.KEY_UP:
                nb_nk = 0
                known = True
                if k == curses.KEY_UP and current_pos > 0:
                    if (self.lines[current_pos] - offset)\
                        < (self.start_line + 3):
                        offset -= 1
                        self.__scroll_window(process, flag, indent, offset)
                        self.__help_key_interactive()

                    if current_pos < len(process):
                        self.__refresh_line(
                            process[current_pos],
                            flag,
                            indent,
                            'default',
                            self.lines[current_pos] - offset)
                    current_pos -= 1
                if k == curses.KEY_DOWN and current_pos < (len(process) - 1):
                    if (self.lines[current_pos] - offset) >= (self.maxy - 2):
                        offset += 1
                        self.__scroll_window(process, flag, indent, offset)
                        self.__help_key_interactive()

                    if current_pos >= 0:
                        self.__refresh_line(
                            process[current_pos],
                            flag,
                            indent,
                            'default',
                            self.lines[current_pos] - offset)
                    current_pos += 1
                self.__refresh_line(
                    process[current_pos],
                    flag,
                    indent,
                    'cursor',
                    self.lines[current_pos] - offset)
                curses.flushinp()
                continue
            # Add/remove a PID from the yank list
            if k == ord(' '):
                known = True
                if not self.pid_yank.count(process[current_pos]['pid']) > 0:
                    self.pid_yank.append(process[current_pos]['pid'])
                else:
                    self.pid_yank.remove(process[current_pos]['pid'])

                self.__refresh_line(
                    process[current_pos],
                    flag,
                    indent,
                    'default',
                    self.lines[current_pos] - offset)

                if current_pos < (len(process) - 1):
                    current_pos += 1
                    if (self.lines[current_pos] - offset) >= (self.maxy - 1):
                        offset += 1
                        self.__scroll_window(process, flag, indent, offset)
                        self.__help_key_interactive()
                self.__refresh_line(
                    process[current_pos],
                    flag,
                    indent,
                    'cursor',
                    self.lines[current_pos] - offset)
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
            return self.__poll_activities(
                    interval,
                    flag,
                    indent,
                    process,
                    disp_proc)
        elif self.mode == 'waiting' or self.mode == 'blocking':
            return self.__poll_waiting_blocking(
                    interval,
                    flag,
                    indent,
                    process,
                    disp_proc)

    def __poll_activities(self, interval, flag, indent, process = None, \
        disp_proc = None):
        """
        Poll activities.
        """
        # Keyboard interactions
        self.win.timeout(int(1000 * self.refresh_time * interval))
        t_start = time.time()
        known = False
        do_refresh = False
        try:
            key = self.win.getch()
        except KeyboardInterrupt as err:
            raise err
        if key == ord('q'):
            curses.endwin()
            exit()
        # PAUSE mode
        if key == ord(' '):
            self.__pause()
            do_refresh = True
        # interactive mode
        if (key == curses.KEY_DOWN or key == curses.KEY_UP) and \
            len(disp_proc) > 0:
            self.__interactive(disp_proc, flag, indent)
            known = False
            do_refresh = True
        # show waiting queries
        if (key == curses.KEY_F2 or key == ord('2')):
            self.mode = 'waiting'
            self.sort = 't'
            curses.flushinp()
            return self.__poll_waiting_blocking(0, flag, indent)
        # show blocking queries
        if (key == curses.KEY_F3 or key == ord('3')):
            self.mode = 'blocking'
            self.sort = 't'
            curses.flushinp()
            return self.__poll_waiting_blocking(0, flag, indent)
        # change verbosity
        if key == ord('v'):
            self.verbose_mode += 1
            if self.verbose_mode > 3:
                self.verbose_mode = 1
            do_refresh = True
        # turn off/on colors
        if key == ord('C'):
            if self.color is True:
                self.set_nocolor()
            else:
                self.set_color()
            do_refresh = True
        # sorts
        if key == ord('c') and (flag & PGTOP_FLAG_CPU) and self.sort != 'c':
            self.sort = 'c'
            known = True
        if key == ord('m') and (flag & PGTOP_FLAG_MEM) and self.sort != 'm':
            self.sort = 'm'
            known = True
        if key == ord('r') and (flag & PGTOP_FLAG_READ) and self.sort != 'r':
            self.sort = 'r'
            known = True
        if key == ord('w') and (flag & PGTOP_FLAG_WRITE) and self.sort != 'w':
            self.sort = 'w'
            known = True
        if key == ord('t') and self.sort != 't':
            self.sort = 't'
            known = True
        if key == ord('+') and self.refresh_time < 3:
            self.refresh_time += 1
            do_refresh = True
        if key == ord('-') and self.refresh_time > 1:
            self.refresh_time -= 1
            do_refresh = True
        # Refresh
        if key == ord('R'):
            known = True

        if key == ord('u'):
            self.__empty_pid_yank()
            known = True

        if key == ord('h'):
            self.__help_window()
            do_refresh = True

        if key == curses.KEY_RESIZE and \
            self.uibuffer is not None and \
            'procs' in self.uibuffer:
            do_refresh = True

        if do_refresh is True and \
            self.uibuffer is not None and \
            type(self.uibuffer) is dict and \
            'procs' in self.uibuffer:
                self.check_window_size()
                self.refresh_window(
                    self.uibuffer['procs'],
                    self.uibuffer['extras'],
                    self.uibuffer['flag'],
                    self.uibuffer['indent'],
                    self.uibuffer['io'],
                    self.uibuffer['tps'],
                    self.uibuffer['size_ev'],
                    self.uibuffer['total_size'])

        curses.flushinp()
        t_end = time.time()
        if key > -1 and not known and \
            (t_end - t_start) < (self.refresh_time * interval):
            return self.__poll_activities(
                        ((self.refresh_time * interval) - \
                            (t_end - t_start))/self.refresh_time,
                        flag,
                        indent,
                        process,
                        disp_proc)

        # poll postgresql activity
        queries =  self.data.pg_get_activities()
        self.pid = []
        if self.is_local:
            # get resource usage for each process
            new_procs = self.data.sys_get_proc(queries, self.is_local)

            procs = []
            read_bytes_delta = 0
            write_bytes_delta = 0
            read_count_delta = 0
            write_count_delta = 0
            for pid, new_proc in new_procs.items():
                try:
                    if pid in process:
                        n_io_time = time.time()
                        # Getting informations from the previous loop
                        proc = process[pid]
                        # Update old process with new informations
                        proc.duration = new_proc.duration
                        proc.query = new_proc.query
                        proc.client = new_proc.client
                        proc.wait = new_proc.wait
                        proc.set_extra(
                            'io_wait',
                            new_proc.get_extra('io_wait'))
                        proc.set_extra(
                            'read_delta',
                            (new_proc.get_extra('io_counters').read_bytes
                            - proc.get_extra('io_counters').read_bytes)
                            / (n_io_time - proc.get_extra('io_time')))
                        proc.set_extra(
                            'write_delta',
                            (new_proc.get_extra('io_counters').write_bytes
                            - proc.get_extra('io_counters').write_bytes)
                            / (n_io_time - proc.get_extra('io_time')))
                        proc.set_extra(
                            'io_counters',
                            new_proc.get_extra('io_counters'))
                        proc.set_extra(
                            'io_time',
                            n_io_time)

                        # Global io counters
                        read_bytes_delta  += proc.get_extra('read_delta')
                        write_bytes_delta += proc.get_extra('write_delta')
                    else:
                        # No previous information about this process
                        proc = new_proc

                    if not self.pid.count(pid):
                        self.pid.append(pid)

                    proc.set_extra(
                        'mem_percent',
                        proc.get_extra('psutil_proc').memory_percent())
                    proc.set_extra(
                        'cpu_percent',
                        proc.get_extra('psutil_proc').\
                            cpu_percent(interval=0))
                    new_procs[pid] = proc
                    procs.append({
                        'pid': pid,
                        'database': proc.database,
                        'user':proc.user,
                        'client': proc.client,
                        'cpu': proc.get_extra('cpu_percent'),
                        'mem': proc.get_extra('mem_percent'),
                        'read': proc.get_extra('read_delta'),
                        'write': proc.get_extra('write_delta'),
                        'query': proc.query,
                        'duration': self.data.get_duration(proc.duration),
                        'wait': proc.wait,
                        'io_wait': proc.get_extra('io_wait')
                    })

                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    pass
                except Exception as err:
                    raise err
            # store io counters
            if read_bytes_delta > 0:
                read_count_delta  += int(read_bytes_delta/self.fs_blocksize)
            if write_bytes_delta > 0:
                write_count_delta += int(write_bytes_delta/self.fs_blocksize)
            self.data.set_global_io_counters(
                read_bytes_delta,
                write_bytes_delta,
                read_count_delta,
                write_count_delta)
        else:
            procs = []
            new_procs = None
            for query in queries:
                if not self.pid.count(query['pid']):
                    self.pid.append(query['pid'])
                procs.append({
                    'pid': query['pid'],
                    'database': query['database'],
                    'user': query['user'],
                    'client': query['client'],
                    'query': query['query'],
                    'duration': self.data.get_duration(query['duration']),
                    'wait': query['wait']
                })

        # return processes sorted by query duration
        if self.sort == 't':
            # TIME
            disp_procs = sorted(
                            procs,
                            key=lambda p: p['duration'],
                            reverse=True)
        elif self.sort == 'c':
            # CPU
            disp_procs = sorted(
                            procs,
                            key=lambda p: p['cpu'],
                            reverse=True)
        elif self.sort == 'm':
            # MEM
            disp_procs = sorted(
                            procs,
                            key=lambda p: p['mem'],
                            reverse=True)
        elif self.sort == 'r':
            # READ
            disp_procs = sorted(
                            procs,
                            key=lambda p: p['read'],
                            reverse=True)
        elif self.sort == 'w':
            # WRITE
            disp_procs = sorted(
                            procs,
                            key=lambda p: p['write'],
                            reverse=True)
        else:
            disp_procs = sorted(
                            procs,
                            key=lambda p: p['duration'],
                            reverse=True)

        self.__check_pid_yank()

        return (disp_procs, new_procs)

    def __poll_waiting_blocking(self, interval, flag, indent, \
        process = None, disp_proc = None):
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
        except KeyboardInterrupt as err:
            raise err
        if k == ord('q'):
            curses.endwin()
            exit()
        # PAUSE mode
        if k == ord(' '):
            self.__pause()
            do_refresh = True
        # interactive mode
        if (k == curses.KEY_DOWN or k == curses.KEY_UP) and \
            len(disp_proc) > 0:
            self.__interactive(disp_proc, flag, indent)
            known = True
        # activities mode
        if (k == curses.KEY_F1 or k == ord('1')):
            self.mode = 'activities'
            curses.flushinp()
            queries = self.data.pg_get_activities()
            procs = self.data.sys_get_proc(queries, self.is_local)
            return self.__poll_activities(0, flag, indent, procs)
        # Waiting queries
        if (k == curses.KEY_F2 or k == ord('2')) and \
            self.mode != 'waiting':
            self.mode = 'waiting'
            curses.flushinp()
            return self.__poll_waiting_blocking(0, flag, indent)
        # blocking queries
        if (k == curses.KEY_F3 or k == ord('3')) and \
            self.mode != 'blocking':
            self.mode = 'blocking'
            curses.flushinp()
            return self.__poll_waiting_blocking(0, flag, indent)
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
            self.__help_window()
            do_refresh = True

        # Refresh
        if k == ord('R'):
            known = True

        if k == curses.KEY_RESIZE and self.uibuffer is not None and \
            'procs' in self.uibuffer:
            do_refresh = True

        if do_refresh is True and self.uibuffer is not None and \
            'procs' in self.uibuffer:
            self.check_window_size()
            self.refresh_window(
                self.uibuffer['procs'],
                self.uibuffer['extras'],
                self.uibuffer['flag'],
                self.uibuffer['indent'],
                self.uibuffer['io'],
                self.uibuffer['tps'],
                self.uibuffer['size_ev'],
                self.uibuffer['total_size'])

        curses.flushinp()
        t_end = time.time()
        if k > -1 and \
            not known and \
            (t_end - t_start) < (self.refresh_time * interval):
            return self.__poll_waiting_blocking(
                    ((self.refresh_time * interval) -\
                        (t_end - t_start))/self.refresh_time,
                    flag,
                    indent,
                    process,
                    disp_proc)

        # poll postgresql activity
        if self.mode == 'waiting':
            queries =  self.data.pg_get_waiting()
        else:
            queries =  self.data.pg_get_blocking()

        new_procs = {}
        for query in queries:
            new_procs[query['pid']] = query
            new_procs[query['pid']][6] = \
                self.data.get_duration(query['duration'])

        # return processes sorted by query duration
        disp_procs = sorted(
                        queries,
                        key=lambda q: q['duration'],
                        reverse=True)

        return (disp_procs, new_procs)

    def __print_string(self, lineno, colno, word, color=0):
        """
        Print a string at position (lineno, colno) and returns its length.
        """
        try:
            self.win.addstr(lineno, colno, word, color)
        except curses.error:
            pass
        return len(word)

    def __putstrLn(self, lineno, colno, word, color=0):
        try:
            self.win.addstr(lineno, colno, word, color)
        except curses.error:
            pass

    def __print_line(self, lineno, start_colno, params):
        print_fn = partial(self.__putstrLn, lineno)

        colno = start_colno
        for p in params:
            print_fn(colno, *p)
            word = p[0]
            colno += len(word)

    def __add_blank(self, line, offset = 0):
        """
        Complete string with white spaces from the end of string to the end of line.
        """
        line += " " * (self.maxx - (len(line) + offset))
        return line

    def get_indent(self, flag):
        """
        Returns identation for Query column.
        """
        indent = ''
        res = [0] * self.max_ncol
        for _, val in PGTOP_COLS[self.mode].items():
            if val['mandatory'] or \
                (not val['mandatory'] and val['flag'] & flag):
                res[int(val['n'])] = val
        for val in res:
            if val is not 0:
                if val['name'] is not 'Query':
                    indent += val['template_h'] % ' '
        return indent

    def __print_cols_header(self, flag):
        """
        Print columns headers
        """
        line = ''
        disp = ''
        xpos = 0
        res = [0] * self.max_ncol
        color = self.__get_color(C_GREEN)
        for _, val in PGTOP_COLS[self.mode].items():
            if val['mandatory'] or \
                (not val['mandatory'] and val['flag'] & flag):
                res[int(val['n'])] = val
        for val in res:
            if val is not 0:
                disp = val['template_h'] % val['name']
                if ((val['name'] == "CPU%" and self.sort == 'c') or
                    (val['name'] == "MEM%" and self.sort == 'm') or
                    (val['name'] == "READ/s" and self.sort == 'r') or
                    (val['name'] == "WRITE/s" and self.sort == 'w') or
                    (val['name'] == "TIME+" and self.sort == 't')):
                    color_highlight = self.__get_color(C_CYAN)
                else:
                    color_highlight = color
                if val['name'] == "Query":
                    disp += " " * (self.maxx - (len(line) + len(disp)))
                line += disp
                self.__putstrLn(
                    self.lineno,
                    xpos,
                    disp,
                    color_highlight|curses.A_REVERSE)
                xpos += len(disp)
        self.lineno += 1

    def __print_header(self, pg_version, hostname, user, host, \
        port, database, ios, tps, size_ev, total_size):
        """
        Print window header
        """
        version = " %s" % (pg_version)

        self.lineno = 0
        cyan = self.__get_color(C_CYAN)
        params = (
            (" - ",),
            (hostname,curses.A_BOLD,),
            (" - ",),
            (user, cyan),
            ("@",),
            (host, cyan),
            (":",),
            (port, cyan),
            ("/",),
            (database, cyan),
            (" - Ref.: {}s".format(self.refresh_time),),
        )
        self.__print_line(self.lineno, 0, params)

        self.lineno += 1
        s_total_size = "%8s" % bytes2human(total_size)
        s_size_ev = " - %9s/s" % bytes2human(size_ev)
        s_tps = "%11s" % (tps,)
        green_bold = self.__get_color(C_GREEN)|curses.A_BOLD
        params = (
            ("  Size: ",),
            (s_total_size,),
            (s_size_ev,),
            ("        | TPS: ",),
            (s_tps, green_bold),
            )
        self.__print_line(self.lineno, 0, params)

        # If not local connection, don't get and display system informations
        if not self.is_local:
            return

        # Get memory & swap usage
        (mem_used_per, mem_used, mem_total, swap_used_per, \
            swap_used, swap_total) = self.data.get_mem_swap()
        # Get load average
        (av1, av2, av3) = self.data.get_load_average()

        self.lineno += 1
        line = "  Mem.: %6s0%% - %9s/%-8s" % \
            (mem_used_per, bytes2human(mem_used), \
                bytes2human(mem_total))
        colno_io = self.__print_string(self.lineno, 0, line)

        if (int(ios['read_count'])+int(ios['write_count'])) > self.max_iops:
            self.max_iops = (int(ios['read_count'])+int(ios['write_count']))

        line_io = " | IO Max: %8s/s" % (self.max_iops,)
        colno = self.__print_string(self.lineno, colno_io, line_io)

        # swap usage
        line = "  Swap: %6s0%% - %9s/%-8s" % \
            (swap_used_per, bytes2human(swap_used), \
                bytes2human(swap_total))
        self.lineno += 1
        colno = self.__print_string(self.lineno, 0, line)
        line_io = " | Read : %10s/s - %6s/s" % \
            (bytes2human(ios['read_bytes']), int(ios['read_count']),)
        colno = self.__print_string(self.lineno, colno_io, line_io)

        # load average, uptime
        line = "  Load:    %.2f %.2f %.2f" % (av1, av2, av3)
        self.lineno += 1
        colno = self.__print_string(self.lineno, 0, line)
        line_io = " | Write: %10s/s - %6s/s" % \
            (bytes2human(ios['write_bytes']), int(ios['write_count']),)
        colno = self.__print_string(self.lineno, colno_io, line_io)

    def __help_window(self,):
        """
        Display help window
        """
        self.win.erase()
        self.lineno = 0
        version = self.version
        text = "pg_activity %s - (c) 2012-2015 Julien Tachoires" % version
        self.__putstrLn(
                self.lineno,
                0,
                text,
                self.__get_color(C_GREEN)|curses.A_BOLD)
        self.lineno += 1
        text = "Released under PostgreSQL License."
        self.__putstrLn(
                self.lineno,
                0,
                text)
        self.lineno += 2
        self.__display_help_key(
                self.lineno,
                00,
                "Up/Down",
                "scroll process list")
        self.__display_help_key(
                self.lineno,
                45,
                "      C",
                "activate/deactivate colors")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "  Space",
                "pause")
        self.__display_help_key(
                self.lineno,
                45,
                "      r",
                "sort by READ/s desc. (activities)")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "      v",
                "change display mode")
        self.__display_help_key(
                self.lineno,
                45,
                "      w",
                "sort by WRITE/s desc. (activities)")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "      q",
                "quit")
        self.__display_help_key(
                self.lineno,
                45,
                "      c",
                "sort by CPU% desc. (activities)")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "      +",
                "increase refresh time (max:3)")
        self.__display_help_key(
                self.lineno,
                45,
                "      m",
                "sort by MEM% desc. (activities)")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "      -",
                "decrease refresh time (min:1)")
        self.__display_help_key(
                self.lineno,
                45,
                "      t",
                "sort by TIME+ desc. (activities)")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "      R",
                "force refresh")
        self.lineno += 1
        self.__putstrLn(
                self.lineno,
                0,
                "Mode")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "   F1/1",
                "running queries")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "   F2/2",
                "waiting queries")
        self.lineno += 1
        self.__display_help_key(
                self.lineno,
                00,
                "   F3/3",
                "blocking queries")

        self.lineno += 2
        self.__putstrLn(
                self.lineno,
                0,
                "Press any key to exit.")
        self.win.timeout(-1)
        try:
            self.win.getch()
        except KeyboardInterrupt as err:
            raise err

    def __display_help_key(self, lineno, colno, key, help_msg):
        """
        Display help key
        """
        cyan_b = self.__get_color(C_CYAN)|curses.A_BOLD
        word = ": %s" % (help_msg,)
        self.__putstrLn(lineno, colno, key, cyan_b)
        self.__putstrLn(lineno, colno + len(key), word)
        return (colno + len(key) + len(word))

    def refresh_window(self, procs, extras, flag, indent, ios, \
        tps, size_ev, total_size):
        """
        Refresh the window
        """
        self.lines = []
        self.win.erase()
        (pg_version, hostname, user, host, port, dbname) = extras
        self.__print_header(
            pg_version,
            hostname,
            user,
            host,
            port,
            dbname,
            ios,
            tps,
            size_ev,
            total_size)
        self.lineno += 2
        line_trunc = self.lineno
        self.__current_position()
        self.__print_cols_header(flag)
        for proc in procs:
            try:
                self.__refresh_line(proc, flag, indent, 'default')
                line_trunc += 1
                self.lines.append(line_trunc)
            except curses.error:
                break
        for line in range(self.lineno, (self.maxy-1)):
            self.__putstrLn(line, 0, self.__add_blank(" "))
        self.__change_mode_interactive()

    def __scroll_window(self, procs, flag, indent, offset = 0):
        """
        Scroll the window
        """
        self.lineno = (self.start_line + 2)
        pos = 0
        for proc in procs:
            if pos >= offset and self.lineno < (self.maxy - 1):
                self.__refresh_line(proc, flag, indent, 'default')
            pos += 1
        for line in range(self.lineno, (self.maxy-1)):
            self.__putstrLn(line, 0, self.__add_blank(" "))

    def __refresh_line(self, process, flag, indent, \
        typecolor = 'default', line = None):
        """
        Refresh a line for activities mode
        """
        l_lineno = line if (line is not None) else self.lineno

        if typecolor == 'default' and self.pid_yank.count(process['pid']) > 0:
            typecolor = 'yellow'

        colno = 0
        colno += self.__print_string(
                    l_lineno,
                    colno,
                    "%-6s " % (process['pid'],),
                    self.line_colors['pid'][typecolor])
        if flag & PGTOP_FLAG_DATABASE:
            colno += self.__print_string(
                        l_lineno,
                        colno,
                        PGTOP_COLS[self.mode]['database']['template_h'] % \
                            (process['database'][:16],),
                        self.line_colors['database'][typecolor])
        if self.mode == 'activities':
            if flag & PGTOP_FLAG_USER:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%16s " % (str(process['user'])[:16],),
                            self.line_colors['user'][typecolor])
            if flag & PGTOP_FLAG_CLIENT:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%16s " % (str(process['client'])[:16],),
                            self.line_colors['client'][typecolor])
            if flag & PGTOP_FLAG_CPU:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%6s " % (process['cpu'],),
                            self.line_colors['cpu'][typecolor])
            if flag & PGTOP_FLAG_MEM:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%4s " % (round(process['mem'], 1),),
                            self.line_colors['mem'][typecolor])
            if flag & PGTOP_FLAG_READ:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%8s " % (bytes2human(process['read']),),
                            self.line_colors['read'][typecolor])
            if flag & PGTOP_FLAG_WRITE:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%8s " % (bytes2human(process['write']),),
                            self.line_colors['write'][typecolor])
        elif self.mode == 'waiting' or self.mode == 'blocking':
            if flag & PGTOP_FLAG_RELATION:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%9s " % (str(process['relation'])[:9],),
                            self.line_colors['relation'][typecolor])
            if flag & PGTOP_FLAG_TYPE:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%16s " % (str(process['type'])[:16],),
                            self.line_colors['type'][typecolor])
            if flag & PGTOP_FLAG_MODE:
                pr_locks = {'ExclusiveLock',
                            'RowExclusiveLock',
                            'AccessExclusiveLock'}
                word = "%16s " % (mode[:16],)
                fn = lambda k: self.line_colors[k][typecolor]
                color = fn('mode_red') if (process['mode'] in pr_locks) else \
                                                        fn('mode_yellow')
                self.__putstrLn(l_lineno, colno, word, color)
                colno += len(word)

        if flag & PGTOP_FLAG_TIME:
            if process['duration'] >= 1 and process['duration'] < 60000:
                ctime = timedelta(seconds=float(process['duration']))
                mic = '%.6d' % (ctime.microseconds)
                ctime = "%s:%s.%s" % (str((ctime.seconds // 60)).zfill(2), \
                            str((ctime.seconds % 60)).zfill(2), str(mic)[:2])
            elif process['duration'] >= 60000:
                ctime = "%s h" % str(int(process['duration'] / 3600))

            if process['duration'] < 1:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            " %.6f " % (process['duration'],),
                            self.line_colors['time_green'][typecolor])
            elif process['duration'] >= 1 and process['duration'] < 3:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%9s " % (ctime,),
                            self.line_colors['time_yellow'][typecolor])
            else:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%9s " % (ctime,),
                            self.line_colors['time_red'][typecolor])
        if self.mode == 'activities' and flag & PGTOP_FLAG_WAIT:
            if process['wait']:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%2s " % ('Y',),
                            self.line_colors['wait_red'][typecolor])
            else:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%2s " % ('N',),
                            self.line_colors['wait_green'][typecolor])

        if self.mode == 'activities' and flag & PGTOP_FLAG_IOWAIT:
            if process['io_wait'] == 'Y':
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%4s " % ('Y',),
                            self.line_colors['wait_red'][typecolor])
            else:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            "%4s " % ('N',),
                            self.line_colors['wait_green'][typecolor])

        dif = self.maxx - len(indent) - 1
        if self.verbose_mode == PGTOP_TRUNCATE:
            query = process['query'][:dif]
            colno += self.__print_string(
                        l_lineno,
                        colno,
                        " %s" % (self.__add_blank(query, len(indent)+1),),
                        self.line_colors['query'][typecolor])
        elif self.verbose_mode == PGTOP_WRAP or \
            self.verbose_mode == PGTOP_WRAP_NOINDENT:
            query = process['query']
            query_wrote = ''
            offset = 0
            if len(query) > dif and dif > 1:
                query_part = query[offset:dif]
                self.__print_string(
                    l_lineno,
                    colno,
                    " %s" % (self.__add_blank(query_part, len(indent)+1),),
                    self.line_colors['query'][typecolor])
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
                    self.__print_string(
                        l_lineno,
                        0,
                        "%s" % (self.__add_blank(p_indent + " " + \
                                    query_part, len(indent)+1)),
                        self.line_colors['query'][typecolor])
                    query_wrote += query_part
                    offset = len(query_wrote)
            else:
                colno += self.__print_string(
                            l_lineno,
                            colno,
                            " %s" % (self.__add_blank(query, len(indent)),),
                            self.line_colors['query'][typecolor])
        self.lineno += 1
