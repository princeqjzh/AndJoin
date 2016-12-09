#! /usr/bin/python
"""
android automated tester

Copyright (C) 2012-2015  Xinquan Wang
Created on Dec 1, 2012

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Xinquan Wang
"""
from __future__ import with_statement
import os
import re

import time
import logging
from os import path, remove, getcwd, mkdir, listdir
from subprocess import Popen

from fw.iDevice import TestDevicePool
from fw.TestUtil import printLog, createLogger, TestStatus, Shell, \
    TC_DIR, SNAPSHOT_DIR, TS_DIR, LOGS_DIR, \
    MONKEYTEST_LOG_FILE, TESTER_DEBUG_LOG_FILE, ADBLOG_FILE
from fw.TestRunner import TestCasePool
from fw.AppTestRunner import AppTestRunner, APP_VERSION, APP_PKG_NAME, APPLOG_FILE_PATH, APPLOG_FILE, \
    DEFAULT_TEST_SUITE, MAIL_SERVER_ADDRESS, MAIL_SENDER_ADDRESS, MAIL_SENDER_PASSWORD, MAIL_ADMIN_ADDRESS

from fw.MailUtil import send_mail


class Tester:
    """ The Tester class plays a tester role -- It manages test build, testcase,
    test devices, and test results. It uses AppTestRunner to execute testcases.
    """

    EXCEPTION_AGGREGATION_MODE = 0
    """ 0: use thread/class as key, 1: use exception as key"""
    GET_BUILD = True
    """ used to control if tester gets the build file before test starts, or use the installed build in test"""
    DEBUG = logging.NOTSET
    """ control log verbosity"""

    def __init__(self, suite=DEFAULT_TEST_SUITE, buildnum=0):
        """
        constructor.
        """

        self.test_buildnum = buildnum
        """ the build number to verify """
        self.test_suite = suite
        """ the suite to test"""

        self.Pass = 0
        """ Passed testcase number"""
        self.Fail = 0
        """ failed testcase number """
        self.Total = 0
        """ total testcase number """
        self.ALTList = []
        """ activity launch time list """
        self.exception_map_list = [{}, {}]
        """ app exception map list: one keeps formulated exceptions and the other keeps raw exceptions """
        self.start_time = None
        """ test start time"""
        self.end_time = None
        """ test finish time"""
        self.shell = Shell()
        """ Shell object """
        # do environment validation
        if not path.isdir(TC_DIR):
            print('Required directory %s does not exist. please check and run again.' % TC_DIR)
            return
        if not path.isdir(TS_DIR):
            print('Required directory %s does not exist. please check and run again.' % TS_DIR)
            return
        if not path.isdir(SNAPSHOT_DIR):
            mkdir(SNAPSHOT_DIR)
        # remove old log file
        if path.isfile(TESTER_DEBUG_LOG_FILE):
            if Tester.DEBUG == logging.DEBUG:
                print('Removing old log file...')
            remove(TESTER_DEBUG_LOG_FILE)
        # truncate_file(TESTER_DEBUG_LOG_FILE)

        # create new log file
        # Oct 21: need to assign a different logger id each time, otherwise it will use the existing one
        # which will be closed at the end of run()
        self.logHandler = createLogger(Tester.DEBUG)
        """ log file handler """
        # get device, by default get the connected Genymotion device
        self.device = None
        self.device = TestDevicePool().getDevice()  # make='Genymotion')
        """ test device """
        if self.device is None:
            raise EnvironmentError('[Tester] NO DEVICE OR MORE THAN ONE DEVICE FOUND. QUIT.')

        if Tester.DEBUG == logging.DEBUG:
            printLog('[Tester] FOUND DEVICE.', logging.DEBUG)

        if Tester.GET_BUILD:
            if not self.getBuild():
                raise EnvironmentError('[Tester] Get build failed.')
        # build testcase pool
        self.testPool = TestCasePool.fromSuite(self.test_suite)
        """ testcase pool for current test run """
        if len(self.testPool) == 0:
            raise EnvironmentError('[Tester] NO TESTCASE IN THE TEST SUITE. QUIT.')

    def __del__(self):
        if self.device:
            del self.device
        del self.ALTList
        self.logHandler.close()
        logging.shutdown()

    def __reset(self):
        """
        reset counters and remove result file and temp files
        Note: execution log file is not removed at the beginning of each run, but during the init.
        """
        self.Pass = 0
        self.Fail = 0
        self.Total = 0
        self.ALTList = []
        self.start_time = None
        self.end_time = None

        # remove old result file
        if path.isfile(self.test_suite + '.txt'):
            print 'Removing old result file %s ...' % (self.test_suite + '.txt')
            remove(self.test_suite + '.txt')
        if path.isfile(APPLOG_FILE):
            print 'Removing old app log file %s ...' % APPLOG_FILE
            remove(APPLOG_FILE)
        if path.isfile(ADBLOG_FILE):
            print 'Removing old ADB log file %s ...' % ADBLOG_FILE
            remove(ADBLOG_FILE)
        # remove temp png files
        self.shell.runShellCmd(r'rm *.png')
        self.shell.runShellCmd(r'rm %s/*.png' % SNAPSHOT_DIR)
        # reset test pool status
        for tc in self.testPool:
            tc.result = TestStatus.NotRun
            tc.crash = False

    def getBuild(self):
        """
        get the specified build file to current directory
        this is an abstract method. subclasses should implement it.
        """
        raise NotImplementedError("Please implement getBuild()!")

    def generateTestReport(self):
        """
        generate test report content
        this is an abstract method. subclasses should implement it.
        """
        raise NotImplementedError("Please implement generateTestReport()!")

    def scanExceptionInAppLog(self, file_path):
        """
        scan the app log for exceptions, and parse them into lists of exception, class and line numbers
        this is an abstract method. subclasses should implement it.
        @param file_path: file path (string)
        @return: two maps: one keeps formulated exceptions and the other keeps raw exceptions
        @rtype list
        """
        raise NotImplementedError("Please implement scanExceptionInAppLog()!")

    @staticmethod
    def __convertTime(rawtime):
        """
        split the minute part from second part, and convert to launch time in seconds.
        the input raw time may contain seconds and milliseconds, e.g. 1s12ms (2014-07-22)
        @param rawtime: raw time string
        @return: the processed time string
        """
        # printLog('[getTime] raw time: %s'% rawtime)
        # remove the trailing '\n' and 'ms'
        rawtime = rawtime.split('m')[0]
        # rawtime=rawtime[0:(len(rawtime)-2)]
        # printLog('[getTime] stripped raw time: %s'% rawtime)
        if not rawtime.isdigit():
            sec, ms = rawtime.split('s')
            rawtime = str(int(sec) * 1000 + int(ms))
            # printLog('[getTime] converted time: %s(ms)' % rawtime)
        return rawtime

    @staticmethod
    def getLaunchTime(fname):
        """
        scan logcat file and retrieve activity launch time data
        2015-09-01: refactored to remove the dependency to external shell script
        @param fname: the logcat filename
        @return: a list of activities and their launch time
        """
        if not os.path.isfile(fname):
            return ''

        ALTList = []
        LT_RE = re.compile("^I/ActivityManager\(\s*\d+\): Displayed {}/(\S+): \+(\S+)\s*$".format(APP_PKG_NAME))

        try:
            with open(ADBLOG_FILE, 'r') as fd:
                lines = filter(lambda x: not x.startswith('\n') and APP_PKG_NAME in x, fd.readlines())
                for line in lines:
                    # printLog('[getLaunchTime] current line: %s'% line)
                    if LT_RE.match(line):
                        activity, ltime = LT_RE.search(line).groups()
                        ltime = Tester.__convertTime(ltime.rstrip('\n'))
                        # Oct 23: changed method to get activity name and time
                        # use ':' to split columns in get_ALT.sh and '+' to split
                        # activity name and launch time
                        ALTList.append((activity, ltime))
        except Exception, e:
            printLog('[getLaunchTime] Caught exception while writing launch time data to file: %s' % e.message,
                     logging.ERROR)
        finally:
            for alt in ALTList:
                print "activity {}:{}".format(alt[0], alt[1])
            return ALTList

    def run(self):
        """
        run tester to capture logcat, start App TestRunner instance, get launch time, filter exceptions in app log
        and generate test report

        @return: number of failed testcases
        @rtype: integer
        """
        self.__reset()
        self.start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

        # 2014-07-22, capture logcat in ASYNC mode
        printLog('Start capture adb logcat ...')
        # redirect to local drive would generate error: /system/bin/sh: can't create logcat.log: Read-only file system
        # using the android file system path would solve the problem
        # child = Popen(['adb', 'logcat', '>', '/data/data/%s' % ADBLOG_FILE])
        child = Popen('adb logcat 2>&1 > %s' % ADBLOG_FILE, shell=True)
        # truncate file after 3 seconds to get rid of old logs
        time.sleep(3)
        self.shell.truncate_file(ADBLOG_FILE)
        try:
            tr = AppTestRunner(self.test_buildnum, self.testPool, self.device)
            tr.run()
        except (AssertionError, EnvironmentError), e:
            printLog('Failed to initialize test runner {}: \n{}'.format(self.device.deviceId, e.message), logging.ERROR)
            return -1

        printLog('============================================================')
        printLog('<Main Thread> all test finished!')
        printLog('============================================================')
        self.end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        self.testPool.printTestResult()
        # stop logcat capture and get activity launch time
        child.terminate()
        # if tr.pullFile('/data/data/{}'.format(ADBLOG_FILE)) == 0:
        if path.isfile(ADBLOG_FILE):
            self.ALTList = Tester.getLaunchTime(ADBLOG_FILE)
        # scan app log and get any exception
        if len(APPLOG_FILE) > 0:
            applog = path.join(LOGS_DIR, "{}_{}.log".format(APPLOG_FILE[:-4], self.device.deviceId.replace(':', '-')))
            if tr.pullFile(APPLOG_FILE_PATH, applog) == 0:
                self.exception_map_list = self.scanExceptionInAppLog(applog)
        # generate result report
        self.generateTestReport()

        return self.Fail

    def sendmail(self, subject, to):
        """
        send mail
        @param subject: mail subject
        @param to: receivers
        @return: none
        """
        mailserver = {'name': MAIL_SERVER_ADDRESS, 'user': MAIL_SENDER_ADDRESS, 'password': MAIL_SENDER_PASSWORD}
        fro = MAIL_SENDER_ADDRESS
        if len(to) == 0:
            to = [MAIL_ADMIN_ADDRESS]
        attachList = []
        if self.Fail > 0 or len(self.exception_map_list[0]) > 0 or len(self.exception_map_list[1]) > 0:
            for log_file in [APPLOG_FILE, ADBLOG_FILE, MONKEYTEST_LOG_FILE]:  # TESTER_DEBUG_LOG_FILE
                if path.isfile(log_file):
                    attachList.append(log_file)
            # get the snapshot file list
            for i in listdir(path.join(getcwd(), 'snapshot')):
                attachList.append(path.join(getcwd(), 'snapshot', i))
        # open result file and read the result
        try:
            print('reading %s...' % (self.test_suite + '.html'))
            with open(self.test_suite + '.html') as fd:
                text = fd.read()
            # content=''.join(text)
            # print content
            send_mail(mailserver, fro, to, subject, text, attachList)
            print '[sendmail] Mail sent out to %s with attachment %s' % (to, attachList)
        except Exception, e:
            print '[sendmail] Exception during mail send.\n%s' % e.message
            send_mail(mailserver, fro, [MAIL_ADMIN_ADDRESS], 'Build %s_%d: Failed to send automation email' %
                      (APP_VERSION, self.test_buildnum), e.message, attachList)
