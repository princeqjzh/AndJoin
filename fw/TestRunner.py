#! /usr/bin/env python
# coding=utf-8
"""
android automated test runner

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
from os import sep
import logging
import time
from fw.TestUtil import printLog, TestStatus, H_LINE, SNAPSHOT_DIR
from fw.iDevice import iDevice


def parseTestStep(s):
    """
    split the input string by space and return the method name and the optional arguments
    @type s: str
    @param s: raw string
    @return: a list [command, argument] (list)
    @raise ValueError
    """
    try:
        cmd = s.split(' ', 1)
        if len(cmd) == 1:
            cmd.append('')
        return cmd
    except Exception, e:
        raise ValueError('Failed to parse test step: %s' % e.message)
        # import traceback
        # traceback.print_exc()


def getFailedAction(cmds, failedLine):
    if failedLine <= 2:
        return 0, cmds[0]
    ignoreMethodList = ['sleep', 'assert']
    tmpLine = failedLine - 1
    tmpCmd = cmds[tmpLine - 1]
    while tmpCmd.startswith('#') or tmpCmd.strip() == '' or parseTestStep(tmpCmd)[0] in ignoreMethodList:
        tmpLine -= 1
        if tmpLine == 0:
            break
        tmpCmd = cmds[tmpLine - 1]
    # print 'Found command: %d, %s' % (tmpLine, tmpCmd)
    return tmpLine, tmpCmd


class TestRunner(iDevice):
    """
    this version of TestRunner abandons thread support in order to use signal alarm which is only supported in
    main thread.
    """
    def __init__(self, tcPool, device):
        self.testcasePool = tcPool
        """testcase pool """
        self.crash = False
        """app crash indicator"""
        self.block = False
        """test block indicator"""
        # self.device = device
        # """TestDevice object """
        iDevice.__init__(self, device.deviceId)

    def __del__(self):
        iDevice.__del__(self)

    def getCurrentBuildNumber(self):
        """abstract method to get current build number."""
        raise NotImplementedError("Please implement getCurrentBuildNumber()!")

    def __executer(self, testcase):
        """
        test case executor: read and execute command written in the test case file
        failure detail message is included in the C{testcase} object if test fails (2014-06-25)

        @param testcase: the testcase to be executed
        @return: pass or fail (boolean)
        """
        # take a snapshot before executing the case
        self.do_takesnapshot(''.join((SNAPSHOT_DIR, sep, testcase.name, '_start.png')))

        """ a testcase has 5 main sections: @TITLE, @DESC, @SETUP, @VALIDATION and @TEARDOWN.
        executor will execute each step in @SETUP, @VALIDATION first, and determine the result. if passed, continue
        execute the steps in @TEARDOWN; if it failed, save the failure details in the testcase and skip the rest steps;
        if a step in @TEARDOWN failed, mark the testcase as passed, and the rest testcases as blocked.
        """
        section = '@SETUP'
        section_sep = '----------------------------'
        for i in range(testcase.steps.index('@SETUP'), len(testcase.steps)):
            step = testcase.steps[i]
            line_number = i + 1
            # printLog('line len:%d' % len(step))
            if len(step) < 2:
                # skip blank lines
                continue
            if step.startswith("#"):
                # lines start with "#" are test step comments. print them out.
                printLog("%s%s%-30s%s" % (self.threadName, '####', step.strip()[1:], '#####'), logging.INFO)
                continue
            if step.startswith("@"):
                # lines start with "@" are section indicator.
                printLog(self.threadName + '{} Enter {} {}'.format(section_sep, step.strip()[1:], section_sep),
                         logging.INFO)
                section = step.strip()
                continue
            printLog(self.threadName + "[cmd at line %d: %s]" % (line_number, step.strip()), logging.INFO)
            # save current command and previous command
            # testcase.precmds[0] = testcase.precmds[1]
            testcase.precmd = testcase.cmd
            testcase.cmd = (line_number, step.strip())
            time.sleep(self.INTERVAL)

            # execute test step.
            try:
                method, args = parseTestStep(step)
                if not method == 'assert':
                    # prepare test environment
                    self.resultFlag = True
                    self.crash = False
                # printLog(self.threadName + "[running command '%s %s']" % (method, args), logging.INFO)
                getattr(self, 'do_' + method)(
                    args.strip())  # include the arg string for backward compatibility, Feb 18, 2014
                printLog(self.threadName + '[result = %s]' % self.resultFlag, logging.INFO)

                if method in iDevice.NO_DUMP_LIST:
                    # 2015-08-11: add dump_view to save time costed by ViewClient.dump()
                    printLog(self.threadName + 'turn off dump after %s.' % method, logging.DEBUG)
                    iDevice.dump_view = False
                elif method in iDevice.DUMP_LIST:
                    printLog(self.threadName + 'turn on dump after %s.' % method, logging.DEBUG)
                    iDevice.dump_view = True

                if self.crash:
                    # fixme: determine if it happens in teardown
                    printLog('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!', logging.CRITICAL)
                    printLog(self.threadName + 'APP CRASHED DURING TEST %s!' % testcase.name, logging.CRITICAL)
                    printLog('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!', logging.CRITICAL)
                    # testcase.cmd=getFailedAction(lines, testcase.precmd[0])
                    testcase.crash = True
                    testcase.errormsg = 'APP CRASHED! Line %d: "%s"' % (testcase.cmd[0], testcase.cmd[1])
                    # 2015-05-06: break if detect crash
                    self.resultFlag = False
                    break
            except AssertionError:
                # if method == 'assert' and not self.resultFlag:
                # print testcase.cmd
                printLog(H_LINE)
                printLog(self.threadName + 'TEST FAILED IN %s!' % section, logging.ERROR)
                testcase.cmd = getFailedAction(testcase.steps, line_number)
                testcase.errormsg = 'Error at Line %d: "%s"' % (testcase.cmd[0], testcase.cmd[1])
                break
            except (AttributeError, ValueError, IndexError, EnvironmentError), e:
                testcase.errormsg = "Script AttributeError: %s" % e.message
                printLog(self.threadName + testcase.errormsg, logging.ERROR)
                self.resultFlag = False
                break
        # for loop end

        printLog(H_LINE, logging.INFO)
        if self.resultFlag:
            printLog(self.threadName + '[%s PASS]\n' % testcase.name, logging.INFO)
        elif section != '@TEARDOWN':
            printLog(self.threadName + '[%s FAIL at Line %d: %s]' % (
                testcase.name, testcase.cmd[0], testcase.cmd[1]), logging.INFO)
            # take snapshot before running teardown
            self.do_takesnapshot(''.join((SNAPSHOT_DIR, sep, testcase.name, '_fail.png')))
            # Jul 4, 2014: run the steps in TEARDOWN section to ensure a complete tear down
            # todo: merge below code block with the above normal test loop to save code lines
            for step in testcase.teardownSteps:
                line_number = testcase.steps.index('@TEARDOWN') + 1
                if step.startswith("#"):
                    # lines starts with "#" or "@" are test step remarks or section indicator. print them out.
                    printLog(self.threadName + '####' + step.strip() + '#####', logging.INFO)
                    continue
                if step.startswith("@"):
                    # lines starts with "@" are section indicators. print them out.
                    printLog(self.threadName + '{} Enter {} {}'.format(section_sep, step.strip()[1:], section_sep),
                             logging.INFO)
                    continue

                printLog(self.threadName + "[cmd at line %d: %s]" % (line_number, step.strip()), logging.INFO)
                try:
                    method, args = parseTestStep(step)
                    if len(method) == 0:
                        continue
                    getattr(self, 'do_' + method)(
                        args.strip())  # include the arg string for backward compatibility, Feb 18, 2014
                except Exception, e:
                    printLog(self.threadName + "TEARDOWN Failed: %s" % e.message, logging.ERROR)
                    self.resultFlag = False
                    self.block = True
                    # todo: consider appending teardown error to testcase.errormsg
                    break
        else:
            printLog(self.threadName + '[%s PASS] but TEARDOWN Failed.\n' % testcase.name, logging.INFO)
            self.block = True
            self.resultFlag = True  # set testcase as Pass
        return self.resultFlag

    def run(self):
        """
        testcase runner: use test executor to execute all testcases in the pool
        """
        printLog(H_LINE, logging.INFO)
        printLog(self.threadName + "test starts now...", logging.INFO)
        testcase = self.testcasePool.getTestCase()
        # execute each testcase in the testcase Pool
        while testcase:
            # testcase.device_info = self.device.make + ' ' + self.device.model + ' ' + self.device.deviceId
            printLog(H_LINE, logging.INFO)
            if self.block:
                testcase.result = TestStatus.Blocked
                printLog(self.threadName + 'Testcase %s is blocked.' % testcase.name, logging.INFO)
            else:
                printLog(self.threadName + "Testcase %s is started..." % testcase.name, logging.INFO)
                # get test start time
                testcase.start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                # execute testcase
                ret = self.__executer(testcase)
                # get test end time
                testcase.end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                if ret:
                    # printLog(self.threadName + 'Testcase %s Passed.' % testcase.name)
                    testcase.result = TestStatus.Pass
                else:
                    # printLog(self.threadName + 'Testcase %s Failed.' % testcase.name, logging.ERROR)
                    testcase.result = TestStatus.Fail
                    # printLog(self.threadName+'Test device is: %s' % testcase.device)
            printLog(H_LINE, logging.INFO)
            # take snapshot for later debug
            # self.do_takesnapshot(''.join((SNAPSHOT_SUBDIR,sep,testcase.name,'_end.png')))
            testcase = self.testcasePool.getTestCase()

        printLog(self.threadName + "test is finished.", logging.INFO)
