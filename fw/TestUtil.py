# coding=utf-8
from __future__ import with_statement
import logging


# # !!DO NOT CHANGE BELOW PARAMETERS !! ##
import os
from subprocess import Popen, PIPE, call

H_LINE = "----------------------------------------------------------------------\
-----------------------------------------"
TC_DIR = 'tc'
""" the directory to keep testcase files"""
TS_DIR = 'ts'
""" the directory to keep test suite files"""
SNAPSHOT_DIR = 'snapshot'
""" the directory to keep snapshot files"""
LOGS_DIR = 'logs'
""" the directory used by test_robot.py to save log files to"""
TESTDATA_SUBDIR = 'testdata'
""" the directory to keep test data files"""
CORE_DIR = 'fw'
""" the directory to keep core framework files"""

EXT_TEST_SUITE = '.ts'
""" the file extension of test suite files"""
EXT_TEST_CASE = '.tc'
""" the file extension of testcase files"""

MONKEYTEST_LOG_FILE = 'monkey.txt'
""" the log file to keep monkey text output"""
TESTER_DEBUG_LOG_FILE = 'debug_log.txt'
""" the log file to keep the runtime output"""
ADBLOG_FILE = 'logcat.log'
""" the log file to keep adb logcat output"""
CONFIG_FILE = 'config.ini'
""" the configuration file to keep the App settings"""


LOG_LEVEL = logging.DEBUG  # control the current log level
tester_debug_log_file_handle = None
logger_name = 1


def createLogger(log_level=logging.INFO):
    """
    create log file logger
    2015-08-28: refactored to accept input as log level to control overall log output verbosity.
    @param log_level: log level (integer)
    @return: log file handler
    """
    global LOG_LEVEL
    LOG_LEVEL = log_level
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S',
        filename=TESTER_DEBUG_LOG_FILE,
        filemode='w')
    # need to assign a different logger name each time,
    # otherwise it will use the existing one which will be closed at the end of run()
    global logger_name
    logger = logging.getLogger(str(logger_name))
    logger_name += 1

    handler = logging.FileHandler(TESTER_DEBUG_LOG_FILE)
    logger.addHandler(handler)
    global tester_debug_log_file_handle
    tester_debug_log_file_handle = handler
    return handler


levelNames = {logging.NOTSET: 'ALL',
              logging.DEBUG: 'DEBUG',
              logging.INFO: 'INFO',
              logging.WARNING: 'WARNING',
              logging.ERROR: 'ERROR',
              logging.CRITICAL: 'CRITICAL'
              }


def printLog(content, loglevel=logging.DEBUG):
    """
    print log to stdout and log to log file
    @param content:
    @param loglevel: log level (integer)
    """
    if loglevel >= LOG_LEVEL:
        level = levelNames[loglevel]
        getattr(logging, level.lower())(content)
        #        print("{0: ^5} {1}".format(level,content))
        print("%-8s %s" % (level, content))


# http://stackoverflow.com/questions/36932/how-can-i-represent-an-enum-in-python?rq=1
# from enum import Enum
# TestStatus = Enum('TestStatus', 'NotRun Running Pass Fail')
class TestStatus:
    NotRun = 'Not Run'
    Running = 'Running'
    Pass = 'Pass'
    Fail = 'Fail'
    Blocked = 'Blocked'


class Shell:
    """ provide OS type specific access to enable command execution and file operations, etc.
    """
    def __init__(self):
        import platform
        sysstr = platform.system()
        if sysstr == "Windows":
            self.platform = "win"
            """ the OS type """
        elif sysstr == "Linux":
            self.platform = "linux"
        else:
            self.platform = "others"

    def getShellCmdOutput(self, cmd):
        """
        run the given shell command and return the output, and print any errors if generated
        @param cmd: the shell command
        @return: the standard output (String)
        """
        printLog("[getShellCmdOutput] Running cmd:" + cmd, logging.DEBUG)
        try:
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            # printLog("out:\n%s\n" % out, logging.DEBUG)
            if len(err) > 0:
                printLog("[getShellCmdOutput]\n%s" % err, logging.DEBUG)
        except (TypeError, ValueError):
            printLog("[getShellCmdOutput] Exception when run cmd '%s'." % cmd, logging.ERROR)
            return None
        return out

    def runShellCmd(self, cmd):
        """
        run the given shell command and return 0 (succeeded) or 1 (failed)
        @param cmd: the shell command
        @return: 0 (succeeded) or 1 (failed)
        """
        rcode = call(cmd, shell=True)
        if rcode == 0:
            return 0
        else:
            printLog("Failed to execute command '{}', returned {}.".format(cmd, rcode), logging.ERROR)
            return 1

    def truncate_file(self, fname, size=0):
        """
        truncate the given file to specified size in bytes.
        @param fname: the filename
        @param size: target size in byte (int, default=0)
        """
        if not os.path.isfile(fname):
            return
        # with open(fname, "ab") as f:
        # 	f.truncate(size)
        # 	f.close()
        initSize = os.path.getsize(fname)
        printLog('initial size of %s: %d' % (fname, initSize), logging.DEBUG)
        with open(fname, mode='w') as f:
            f.truncate(size)
            # f.write('[log start]\n')
        finalSize = os.path.getsize(fname)
        printLog('final size of %s: %d' % (fname, finalSize), logging.DEBUG)
        printLog('truncated size of %s: %d' % (fname, initSize - finalSize), logging.DEBUG)

    def getHostname(self):
        sys = os.name
        if sys == 'nt':
            hostname = os.getenv('computername')
        elif sys == 'posix':
            hostname = self.getShellCmdOutput(r"hostname")
        else:
            hostname = 'Unknown'
        return hostname


def validateDigit(input_str):
    """
    check if the string parameter is digital, including integer and float.
    return stripped input string if not empty and is digital
    @param input_str: the input string
    @return: a stripped string
    """
    tmpstr = input_str.strip()
    if '.' in tmpstr:
        if not tmpstr.split('.')[0].isdigit() or not tmpstr.split('.')[1].isdigit():
            raise ValueError('Bad float parameter.')
    elif not tmpstr.isdigit():
        raise ValueError('Bad integer parameter.')
    return input_str.strip()


def validateString(input_str):
    """
    check if the input string is empty, return input string if not empty
    @param input_str: the input string
    @return: a stripped string
    """
    if len(input_str.strip()) == 0:
        raise ValueError('Bad string parameter.')
    return input_str.strip()
