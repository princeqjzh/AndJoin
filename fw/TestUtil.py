# coding=utf-8
from __future__ import with_statement
from os import path, sep
import logging


# # !!DO NOT CHANGE BELOW PARAMETERS !! ##
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


class TestCase:
    def __init__(self, tcname, steps, desc='', jid=''):

        try:
            steps.index('@SETUP') & steps.index('@VALIDATION') & steps.index('@TEARDOWN')
        except ValueError:
            raise ValueError('Section label @SETUP or @VALIDATION or @TEARDOWN '
                             'not included in testcase file {}.'.format(tcname))

        self.name = tcname
        """ testcase name """
        # self.path = suite + sep + tcname + EXT_TEST_CASE
        self.desc = desc
        """ testcase description """
        if len(desc) == 0:
            self.desc = tcname
        assert isinstance(steps, list)
        self.steps = steps
        """ list of test steps """
        # extract the steps for teardown, which are used to ensure tear down is completed even if the testcase fails
        self.teardownSteps = self.steps[self.steps.index("@TEARDOWN"):]
        """ steps used in test tear down """
        self.result = TestStatus.NotRun
        """ test result """
        self.jiraId = jid
        """ jira ID """
        self.start_time = 0
        """ test start time """
        self.end_time = 0
        """ test finish time """
        # self.device_info = ''  # used to tell on which device the testcase was executed
        # self.requiredDevicePara = ''

        self.line = 0
        """ test step's line number """
        self.preline = 0
        """ the previous line number """
        self.cmd = ''
        """ the current test step """
        self.precmd = ''
        """ the previous test step """
        self.errormsg = ''
        """ the error message """
        self.crash = False
        """ the crash indicator """

    @staticmethod
    def fromString(tc_string, tc_name='', desc='', jid=''):
        """
        build TestCase from a string
        @param tc_string: a string holding the testcase content
        @param tc_name: testcase name (optional)
        @param desc: testcase description (optional)
        @param jid: Jira ID (optional)
        @return: a TestCase instance
        """
        lines = map(lambda x: x.strip().strip('\t'), tc_string.splitlines())
        try:
            lines.index('@TITLE') & lines.index('@DESC')
        except ValueError:
            raise ValueError('Section label @TITLE or @DESC not included in testcase file {}.'.format(tc_name))
        if len(tc_name) == 0:
            tc_name = lines[lines.index('@TITLE') + 1]
        if len(desc) == 0:
            desc = lines[lines.index('@DESC') + 1] if lines.index('@DESC') else tc_name

        return TestCase(tc_name, lines, desc=desc, jid=jid)

    @staticmethod
    def fromFile(tc_file_path, tc_name='', desc='', jid=''):
        """
        build TestCase from a file
        @param tc_file_path: testcase file path
        @param tc_name: testcase name (optional)
        @param desc: testcase description (optional)
        @param jid: Jira ID (optional)
        @return: a TestCase instance
        """
        with open(tc_file_path, 'r') as tcf:
            return TestCase.fromString(tcf.read(), tc_name, desc, jid)


class TestCasePool(list):
    """
    a list of TestCase instances
    """
    def __init__(self, suite):
        """
        the constructor read the testcases included in the test suite file, and build a list of C{TestCase}s
        @param suite: test suite name
        @raise: ValueError
        """
        list.__init__([])
        testSuiteFile = suite + EXT_TEST_SUITE
        try:
            propfile_path = path.abspath('') + sep + 'ts' + sep + testSuiteFile
            printLog('Reading testcase from file %s...' % propfile_path, logging.DEBUG)
            with open(propfile_path) as fd:
                content = filter(lambda x: not x.startswith('#') and not x.startswith('\n'), fd.readlines())
                # print content
                testlist = map(lambda x: [x.split(':', 1)[0].strip(), x.split(':', 1)[1].strip()], content)
                # print testlist
                for test in testlist:
                    printLog('adding testcase %s to pool...' % test[0], logging.DEBUG)
                    scptfilename = TC_DIR + '/' + test[0] + EXT_TEST_CASE
                    # dirName, tcName=scptfilename.split('/')
                    try:
                        # with open(scptfilename) as sf:
                        #     lines = map(lambda x: x.strip().strip('\t'), sf.readlines())
                        self.append(TestCase.fromFile(scptfilename, tc_name=test[0], desc=test[1]))
                    except IOError, e:
                        printLog("Error open/read file %s: %s" % (scptfilename, e.message), logging.ERROR)
                        raise IOError(e.message)
                    except AssertionError:
                        raise ValueError("Missing or bad step value in %s." % scptfilename)
        except IOError:
            printLog('File %s open error.' % testSuiteFile, logging.ERROR)
            raise ValueError('Failed to open/read suite file.')
        except IndexError, e:
            printLog('File %s format error: %s' % (testSuiteFile, e.message), logging.ERROR)
            raise ValueError('Failed to read testcase.')
        printLog('%d testcase read...' % len(self))

    def getTestCase(self):
        """
        get the first NotRun testcase
        @return: a testcase
        """
        for tc in self:
            if tc.result == TestStatus.NotRun:
                tc.result = TestStatus.Running
                return tc
        return None

    def printTestResult(self):
        """
        print the test results in a formated manner
        @return:
        """
        splitter = "================================================================================================="
        print("\n" + splitter)
        print("%-3s%-60s%11s" % ('ID', 'Testcase Name', 'Test Result'))
        for i in range(len(self)):
            print("%-3d%-60s%11s" % (i + 1, self[i].name, self[i].result))
        print(splitter + "\n")

    def getPassCount(self):
        """
        get the number of passed testcases
        @return: the number (integer)
        """
        num = 0
        for tc in self:
            if tc.result == TestStatus.Pass:
                num += 1
        return num

    def getFailCount(self):
        """
        get the number of failed testcases
        @return: the number (integer)
        """
        num = 0
        for tc in self:
            if tc.result == TestStatus.Fail:
                num += 1
        return num

    def isFatalErrorHappened(self, tcNameTuple):
        """
        filter the given testcase tuple and check if crash or failure happened.
        used to inject a status code in test report
        @param tcNameTuple: testcase name tuple
        @return: result (boolean)
        """
        if len(self) == 0:
            print 'Please invoke Tester.run() before execute this method.'
            return False
        for tc in self:
            if tc.crash:
                return True
            if tc.result == TestStatus.Fail:
                if tc.name in tcNameTuple:
                    return True
        return False
