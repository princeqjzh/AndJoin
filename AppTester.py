#! /usr/bin/env python
# coding=utf-8
import argparse
from os import path
import logging
from subprocess import check_output
import time
import re
import sys

from fw.Tester import Tester
try:
    from fw.AppTestRunner import BUILD_ROOT_PATH, BUILD_FILENAME, APP_VERSION, APPLOG_FILE, \
        APP_VERSION_PREFIX, LOCAL_BUILD_ROOT_PATH, AppTestRunner, PRODUCT_NAME, PRODUCT_SHORT_NAME, \
        DEFAULT_TEST_SUITE, MAIL_ADMIN_ADDRESS, CRITICAL_TESTCASES
except ValueError, e:
    print e.message
    sys.exit(1)

from fw.TestUtil import printLog, H_LINE, TestStatus, Shell

from fw.pyh import PyH, h3, h4, div, p, table, td, tr

SEND_MAIL = False
''' control if send test result by mail. '''


class AppTester(Tester):
    def __init__(self, suite=DEFAULT_TEST_SUITE, buildnum='latest'):
        Tester.__init__(self, suite, buildnum)

    def __del__(self):
        Tester.__del__(self)

    def getBuild(self):
        """
        sample implementation:
        get build file from build server and place it in the directory specified in AppTestRunner.installApp(), which is
        path.join(LOCAL_BUILD_ROOT_PATH, APP_VERSION, "{}-{}.apk".format(PRODUCT_SHORT_NAME, buildnum))
        @return: result (boolean)
        """
        result = False
        if self.test_buildnum < 0:
            return True
        if self.test_buildnum == 0:
            self.test_buildnum = AppTestRunner.getLatestBuildNumber()
            if self.test_buildnum == 0:
                printLog('[getBuild] invalid build number specified or build location not accessible.', logging.ERROR)
                return result
        local_target = path.join(LOCAL_BUILD_ROOT_PATH, APP_VERSION,
                                 "{}-{}.apk".format(PRODUCT_SHORT_NAME, self.test_buildnum))
        if not path.isfile(local_target):
            # the build file is not found locally, download it from remote build server
            remote_target = path.join(BUILD_ROOT_PATH, APP_VERSION, PRODUCT_NAME + '-' + str(self.test_buildnum), BUILD_FILENAME)
            printLog('[getBuild] Downloading build %s from %s...' % (str(self.test_buildnum), remote_target), logging.INFO)
            try:
                Shell().runShellCmd('cp {} {}'.format(remote_target, local_target))
                if path.isfile(local_target):
                    printLog('[getBuild] Build %s is downloaded.' % str(self.test_buildnum), logging.INFO)
                    result = True
            except IOError, e:
                printLog('[getBuild] Build %s download failed: %s' % e.message, logging.ERROR)
        else:
            # use the build file found locally
            printLog('[getBuild] build %d is available.' % self.test_buildnum, logging.INFO)
            return True

        return result

    def generateTestReport(self):
        """
        an implementation: generate test report in <suitename>.html
        """
        content_format = "%-*s%-*s%*s%*s%*s"
        content_format2 = "%-*s%*s"
        # '-' means left just (right just by default) http://www.cnblogs.com/zero86/archive/2012/11/22/2783679.html
        content_format3 = "%-*s%*d"
        self.Total = len(self.testPool)
        self.Pass = self.testPool.getPassCount()
        self.Fail = self.testPool.getFailCount()
        # create HTML content
        page = PyH('Test Result')
        page << h3('Overall Result:')
        # table0 = page << table(border='0',id='table_overall')
        # tmpRow = table0 << tr(id='line1')
        # tmpRow << td("Total:") <<td(str(self.Total))
        # tmpRow = table0 << tr(id='line2')
        # tmpRow << td("Pass:") <<td(str(self.Pass))
        # tmpRow = table0 << tr(id='line3')
        # tmpRow << td("Fail:") <<td(str(self.Fail))
        # tmpRow = table0 << tr(id='line4')
        # tmpRow << td("Not Run:") <<td(str(self.Total-self.Pass-self.Fail))
        page << p(content_format3 % (10, 'Total:', 5, self.Total))
        page << p(content_format3 % (10, 'Pass:', 5, self.Pass))
        page << p(content_format3 % (10, 'Fail:', 5, self.Fail))
        page << p(content_format3 % (10, 'Not Run/Blocked:', 5, self.Total - self.Pass - self.Fail))
        page << h3('Test Details:')
        table_TestResult = page << table(border='1', cellPadding='5', id='table_TestResult')
        headtr = table_TestResult << tr(id='headline1')
        headtr << td('Test ID') << td('Test Name') << td('Test Description')  \
            << td('Start Time') << td('End Time') << td('Test Result', style='font:bold;') << td('Failure Description')
        for i in range(len(self.testPool)):
            tc = self.testPool[i]
            tmpRow = table_TestResult << tr(id='line1')
            tmpRow << td(str(i + 1)) << td(tc.name) << td(tc.desc) \
                << td(tc.start_time) << td(tc.end_time)
            if tc.result == TestStatus.Pass:
                tmpRow << td(tc.result, style='color:green;') << td('')
            elif tc.result == TestStatus.Fail:
                tmpRow << td(tc.result, style='color:red;') << td(tc.errormsg)
            elif tc.result == TestStatus.Blocked:
                tmpRow << td(tc.result, style='color:blue;') << td(tc.errormsg)
            else:
                tmpRow << td(tc.result) << td(tc.errormsg)
        # if self.Fail > 0:
        #     page << h3('Failed Testcase:', style='color:red;')
        #     table1 = page << table(border='1', cellPadding='5', id='table_failedTest')
        #     headtr = table1 << tr(id='headline1')
        #     headtr << td('Test Name') << td('Failure Description') << td('Start Time') << td('End Time')
        #     for tc in self.testPool:
        #         if tc.result == TestStatus.Fail:
        #             tmpRow = table1 << tr(id='line1')
        #             tmpRow << td(tc.name) << td(tc.errormsg) << td(tc.start_time) << td(tc.end_time)
        # if self.Pass > 0:
        #     page << h3('Passed Testcase:', style='color:green;')
        #     table2 = page << table(border='1', cellPadding='5', id='table_passedTest')
        #     headtr = table2 << tr(id='headline2')
        #     headtr << td('Test Name') << td('Test Description') << td('Start Time') << td('End Time')
        #     for tc in self.testPool:
        #         if tc.result == TestStatus.Pass:
        #             tmpRow = table2 << tr(id='line2')
        #             tmpRow << td(tc.name) << td(tc.desc) << td(tc.start_time) << td(tc.end_time)

        # 2015 Jul 15, include exceptions
        if len(self.exception_map_list[0]) > 0:
            page << h3("Mobie thrown below exceptions during the test")
            if len(self.exception_map_list[0]) > 0:
                table_exceptions1 = page << table(border='1', cellPadding='5', id='table_exceptions1')
                headtr = table_exceptions1 << tr(id='headline_exp1')
                if Tester.EXCEPTION_AGGREGATION_MODE == 1:
                    headtr << td('Exception') << td('Class') << td('Date Time') << td('Line No.')  # << td('Severity')
                else:
                    headtr << td('Class') << td('Exception') << td('Date Time') << td('Line No.')  # << td('Severity')
                for key in self.exception_map_list[0]:
                    tmpRow = table_exceptions1 << tr(id='exp1')
                    tmpDict = self.exception_map_list[0][key]
                    if Tester.EXCEPTION_AGGREGATION_MODE == 1:
                        # format the multi-line colume
                        cell_with_br = '<br>'.join(tmpDict['class_name'].split(','))
                        # tmpRow << td(key) << td(cell_with_br) << td(tmpDict['datetime']) << td(tmpDict['line_no'])
                    else:
                        cell_with_br = '<br>'.join(tmpDict['message'].split(','))
                    tmpRow << td(key) << td(cell_with_br) << td(tmpDict['datetime']) << td(tmpDict['line_no'])
            if len(self.exception_map_list[1]) > 0:
                table_exceptions2 = page << table(border='1', cellPadding='5', id='table_exceptions2')
                headtr = table_exceptions2 << tr(id='headline_exp2')
                headtr << td('Line No.') << td('Exception')
                for key in self.exception_map_list[1]:
                    tmpRow = table_exceptions2 << tr(id='exp1')
                    tmpRow << td(key) << td(self.exception_map_list[1][key])
        # 2015 Jul 22, write ALT data
        if len(self.ALTList) > 0:
            page << h3("Activity Launch Time")
            table_alt = page << table(border='1', cellPadding='5', id='table_alt')
            headtr = table_alt << tr(id='headline3')
            headtr << td('Activity Name') << td('Time(millisecond)')
            for vp in self.ALTList:
                tmpRow = table_alt << tr(id='alt')
                tmpRow << td(vp[0]) << td(vp[1])
        # Test time
        mydiv2 = page << div(id='myDiv2')
        mydiv2 << h4('Test build:') + p(APP_VERSION_PREFIX + str(self.test_buildnum))
        mydiv2 << h4('Test start:') + p(self.start_time)
        mydiv2 << h4('Test stop: ') + p(self.end_time)

        # host info
        mydiv2 << h4('Test Server:  ') + p(self.shell.getHostname())
        # page << h4(content_format2 % (11, 'Test start:', 30, self.start_time), cl='left')
        # page << h4(content_format2 % (11, 'Test stop: ', 30, self.end_time), cl='left')
        # page << h4(content_format2 % (11, 'Build:', 30, CLIENT_VERSION_PREFIX+str(self.buildnum)), cl='left')
        # Test device
        mydiv2 << h4('Test Devices:')
        # count = 0
        table_device = mydiv2 << table(cellSpacing='1', cellPadding='5', border='1', borderColor='#666666',
                                       id='table_device')
        table_device.attributes['cellSpacing'] = 1

        headtr = table_device << tr(id='headline5')
        headtr << td('Make') << td('Model') << td('Android Version') << td('ID')
        # for device in self.devicePool.queue:
        #     count += 1
        tmpRow = table_device << tr(id='line1')
        tmpRow << td(self.device.make) << td(self.device.model) << td(self.device.androidVersion) << td(
            self.device.deviceId)
        # page << h5(content_format2 % (11, 'Device'+str(count)+":\t", 50, \
        #       device.make+' '+device.model+' '+device.androidVersion+' ' + device.deviceId))

        # write file
        page.printOut(file=self.test_suite + '.html')

    @staticmethod
    def to_date(millis):
        try:
            date = int(millis)
            tm = time.localtime(date / 1000)
            msec = date % 1000
            str_time = time.strftime("%m-%d %H:%M:%S", tm)
            return "%s.%03d" % (str_time, msec)
        except:
            return millis

    def scanExceptionInAppLog(self, file_path):
        """
        sample implementation: scan the app log for exceptions, parse the grep output to 2 dicts
        @param file_path: file path
        @return: two maps: one keeps formulated exceptions and the other keeps raw exceptions
        @rtype list
        """
        # file_path = path.basename(APPLOG_FILE)
        printLog('[scanExceptionInAppLog] Scanning file %s for exceptions...' % file_path, logging.INFO)
        # todo: remove dependency on grep for possible support on windows later on
        exception_string = check_output(r'grep -n "Exception" %s' % file_path, shell=True)

        # format the output

        RE1 = re.compile("^\d*:\d+ *")
        RE2 = re.compile("^\d*:*")
        exps1 = {}
        exps2 = {}
        raw_lines = exception_string.split('\n')
        exp_lines = filter(lambda x: '[ERROR]' in x, raw_lines)

        for line in exp_lines:
            if line.startswith("\n") or len(line) == 0:
                continue
            try:
                # sample:
                # 6174:1439958792236 {main} [ERROR] [AppUtil] PackageManager.NameNotFoundException for com.android.vending
                if RE1.match(line):
                    line_no, raw_exp = line.split(':', 1)
                    raw_time, thread_name, severity, class_name, message = raw_exp.split(' ', 4)
                    datetime = AppTester.to_date(raw_time)
                    if Tester.EXCEPTION_AGGREGATION_MODE == 1:
                        if message not in exps1.keys():
                            exps1[message] = {'datetime': datetime, 'class_name': class_name, 'line_no': line_no}
                            # 'severity': severity
                        else:
                            exps1[message]['line_no'] = exps1[message]['line_no'] + ', ' + line_no
                            # if thread_name not in exps1[message]['thread_name']:
                            #     exps1[message]['thread_name'] = exps1[message]['thread_name'] + ', ' + thread_name
                            if class_name not in exps1[message]['class_name']:
                                exps1[message]['class_name'] = exps1[message]['class_name'] + ', ' + class_name
                    else:
                        if class_name not in exps1.keys():
                            exps1[class_name] = {'datetime': datetime, 'message': message, 'line_no': line_no}
                        else:
                            exps1[class_name]['line_no'] = exps1[class_name]['line_no'] + ', ' + line_no
                            if message not in exps1[class_name]['message']:
                                exps1[class_name]['message'] = exps1[class_name]['message'] + ', \n' + message
                elif RE2.match(line):
                    # sample:
                    # notice/carrier_notification.txt: open failed: ENOENT (No such file or directory)
                    # 3769:Caused by: libcore.io.ErrnoException: open failed: ENOENT (No such file or directory)
                    line_no, raw_exp = line.split(':', 1)
                    printLog('[scanExceptionInAppLog] found exception at line %s: %s' % (line_no, raw_exp))
                    exps2[line_no] = raw_exp
                else:
                    raise ValueError('exceptional format in App log: %s' % line)
            except Exception, e:
                printLog('[scanExceptionInAppLog] Caught exception when handling below string. %s' % e.message,
                         logging.ERROR)
                print line

        return exps1, exps2


def main():
    """
    the main method, user may specify arguments including but not limited to:
    1. the test suite name. e.g. unittest, smoke, etc.
    2. the build number to test
    """
    print H_LINE
    from fw.TestUtil import levelNames
    log_help_msg = ''
    for key in sorted(levelNames.keys()):
        log_help_msg += '{}:{},'.format(key/10, levelNames[key])
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", help="specify the test suite to be run")  # , default='smoke')
    parser.add_argument("-b", "--build", type=int, help="specify the build number to get and install", default=0)
    parser.add_argument("-v", "--verbose", type=int, choices=[0, 1, 2, 3, 4, 5],
                        help="increase output verbosity: \n%s" % log_help_msg[:-1], default=3)
    args = parser.parse_args()
    if args.verbose is not None:
        Tester.DEBUG = (5 - args.verbose) * 10
        print "[Main] Log verbosity set to {}".format(levelNames[Tester.DEBUG])
    if not args.suite:
        suite = DEFAULT_TEST_SUITE
        print '[Main] Test suite not specified, use default test suite:', suite
    else:
        suite = args.suite
        print '[Main] Test suite specified:', suite
    if args.build == 0:
        print '[Main] Build number not specified, use latest build.'
        buildnum = 0
    elif args.build > 0:
        buildnum = args.build
        print '[Main] Build number specified:', buildnum
    else:
        print '[Main] Use current installed build.'
        buildnum = -1

    print H_LINE
    try:
        tester = AppTester(suite, buildnum)
        ret = tester.run()
    except EnvironmentError:
        return
    to = [MAIL_ADMIN_ADDRESS]
    prefix = 'Automation Test - %s %s (build %s%d)' % (PRODUCT_NAME, suite, APP_VERSION_PREFIX, tester.test_buildnum)

    do_deploy = True
    if ret < 0:
        print('[Main] Test aborted!')
        # status = 'RED'
        subject = prefix + r': RED (Test aborted! PLEASE CHECK THE TEST SERVER AND ENVIRONMENT!)'
    elif ret == 0:
        print '[Main] All Test PASS!'
        # status = 'GREEN'
        if len(tester.exception_map_list[0]) == 0 and len(tester.exception_map_list[1]) == 0:
            subject = '%s: GREEN' % prefix
        else:
            subject = '%s: GREEN with errors in log' % prefix

    elif tester.testPool.isFatalErrorHappened(CRITICAL_TESTCASES):
        print '[Main] Test has fatal error!'
        # status = 'RED'
        subject = '%s: RED (Found fatal error)' % prefix
        do_deploy = False
    elif float(ret) / float(tester.Total) >= 0.5:
        # status = 'RED'
        print '[Main] Test has failures (Fail: %d of %d)' % (ret, tester.Total)
        subject = '%s: RED (Fail: %d of %d)' % (prefix, ret, tester.Total)
    else:
        # status = 'YELLOW'
        print '[Main] Test has failures (Fail: %d of %d)' % (ret, tester.Total)
        subject = '%s: YELLOW (Fail: %d of %d)' % (prefix, ret, tester.Total)

    if do_deploy:
        # FIXME: implement the deploy logic
        pass
    if SEND_MAIL:
        try:
            tester.sendmail(subject, to)
        except Exception, e:
            print '[Main] Exception during mail send:%s' % e.message


if __name__ == "__main__":
    main()
