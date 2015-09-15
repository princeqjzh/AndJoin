#! /usr/bin/python
# -*- encoding: utf-8 -*-
"""
automated Android application test runner

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

AppTestRunner - a subclass of C{TestRunner}, is able to execute testcases on devices using the abilities
from iDevice, as well as the custom methods you added to this module.

C{Tester} uses this custome TestRunner to run tests.
"""
from __future__ import with_statement
from os import path, remove
import logging
import re

from fw.TestUtil import printLog, CORE_DIR, CONFIG_FILE, validateDigit
from fw.TestRunner import TestRunner

import ConfigParser

# read configurables
config = ConfigParser.ConfigParser(allow_no_value=True)
config.readfp(open(CONFIG_FILE))
try:
    MAIL_SERVER_ADDRESS = config.get('Mail', 'MAIL_SERVER_ADDRESS')
    MAIL_SENDER_ADDRESS = config.get('Mail', 'MAIL_SENDER_ADDRESS')
    MAIL_SENDER_PASSWORD = config.get('Mail', 'MAIL_SENDER_PASSWORD')
    MAIL_ADMIN_ADDRESS = config.get('Mail', 'MAIL_ADMIN_ADDRESS')

    # todo: consider implement dynamic loading
    PRODUCT_NAME = config.get('APP', 'PRODUCT_NAME')
    """ the product's full name used in test report """
    PRODUCT_SHORT_NAME = config.get('APP', 'PRODUCT_SHORT_NAME')
    """ the short name of the product that may be used in build filename """
    APP_PKG_NAME = config.get('APP', 'APP_PKG_NAME')
    """ the android package name, e.g. com.google.map """
    APPLOG_FILE = config.get('APP', 'APPLOG_FILE')
    """ the filename of the app log on device (OPTIONAL) """
    APP_VERSION_PREFIX = config.get('APP', 'APP_VERSION_PREFIX')
    """ the app's version prefix used to verify the installed apk file version. e.g. '3.0.19215' (OPTIONAL)"""
    APP_VERSION = config.get('APP', 'APP_VERSION')
    """ the app's version used to locate the build apk file. e.g. '1.0.0_rel' """
    DEFAULT_TEST_SUITE = config.get('TEST', 'DEFAULT_TEST_SUITE')
    """ the default test suite to test """
    CRITICAL_TESTCASES = config.get('TEST', 'CRITICAL_TESTCASES').split(',')
    """ the critical testcases to determine the quality of the build """
    for para in ['PRODUCT_NAME', 'PRODUCT_SHORT_NAME', 'APP_PKG_NAME', 'APP_VERSION', 'DEFAULT_TEST_SUITE']:
        exec "if %s is None or len(%s.strip()) == 0: " \
             "    raise ValueError('Oops...You have not configured %s properly in %s.')" % \
             (para, para, para, CONFIG_FILE)
except ConfigParser.NoSectionError:
    raise RuntimeError("The configuration file may be corrupted or missing one or more mandatory sections.")

except ConfigParser.NoOptionError:
    raise RuntimeError("The configuration file may be corrupted or missing one or more mandatory options.")


APPLOG_FILE_PATH = '/data/data/%s/app_logs/%s' % (APP_PKG_NAME, APPLOG_FILE) if len(APPLOG_FILE.strip()) > 0 else ''
UPGRADE_APP_ON_TEST_START = False

# below are product specific constants, please feel free to customize them, or add new one.

BUILD_FILENAME = PRODUCT_NAME + '.apk'
""" the filename of the apk file"""
BUILD_ROOT_PATH = "/home/innopath/jenkins/%s" % PRODUCT_NAME
""" the path of remote build root directory"""
BUILDNUM_FILE_PATH = path.join(BUILD_ROOT_PATH, APP_VERSION, 'buildnum.txt')
""" the path of the file containing build number """
BUILD_FILE_PATH = path.join(BUILD_ROOT_PATH, APP_VERSION, BUILD_FILENAME)
""" the path of the build file """
LOCAL_BUILD_ROOT_PATH = "/home/innopath/workspace/build/%s" % PRODUCT_NAME
""" the path of local build root directory """
APP_LAUNCH_ACTIVITY = APP_PKG_NAME + '/.ApiDemos'
""" the activity name to launch the App """


class AppTestRunner(TestRunner):
    """
    this class extends TestRunner

    Note:
        1. requires each exposed function starts with "do_"
        2. It is recommended that functions in this class have no argument. If it does,
        you need to append the arguments to the function name in testcase file (*.tc).

    Add new "do_" functions to enhance TestRunner's capability for automation
    purpose as you wish.
    """

    @staticmethod
    def factory(buildnum, testcasePool, device):
        mt = AppTestRunner(buildnum, testcasePool, device)
        return mt

    def __init__(self, buildnum, testcasePool, device):
        TestRunner.__init__(self, testcasePool, device)
        self.test_buildnum = buildnum
        self.currentBuildnum = self.getCurrentBuildNumber()

        if self.currentBuildnum <= 0 and buildnum < 0:
            msg = "Failed to get installed app's version number. Either you don't have the app installed, or the way " \
                  "you retrieve the version number is outdated."
            # printLog("{} [{}] {}".format(self.threadName, self.__class__.__name__, msg), logging.ERROR)
            raise RuntimeError(msg)
        printLog("{} [{}] the current installed app's version is {}".format(self.threadName, self.__class__.__name__,
                                                                            self.currentBuildnum), logging.DEBUG)
        if buildnum < 0:
            self.test_buildnum = self.currentBuildnum
        if self.currentBuildnum < self.test_buildnum:
            # upgrade app to target build
            if UPGRADE_APP_ON_TEST_START:
                printLog(self.threadName + "[%s] Upgrading device to build %s..." %
                         (self.__class__.__name__, self.test_buildnum))
                assert self.updateApp()
            else:
                printLog(self.threadName + "[%s] Upgrade to build %s skipped..." %
                         (self.__class__.__name__, self.test_buildnum))

    def __del__(self):
        TestRunner.__del__(self)

    def updateApp(self):
        return self.do_upgradeApp()

    def getCurrentBuildNumber(self):
        """ sample implement: get it from com.xxx.xxx_preferences.xml
        <int name="pref_current_app_version_code" value="604" />
        """
        # target_filename = self.deviceId + '_preference.xml'
        # if self.pullFile('/data/data/%s/shared_prefs/%s_preferences.xml' % (APP_PKG_NAME, APP_PKG_NAME), target_filename) == 0:
        #     app_version_code_RE = re.compile("^\s*<int name=\"pref_current_app_version_code\" value=\"(\d+)\" />\s*$")
        #     with open(target_filename) as fd:
        #         for line in fd.readlines():
        #             if "pref_current_app_version_code" in line:
        #                 remove(target_filename)
        #                 return int(app_version_code_RE.search(line.strip('\n')).groups()[0])
        #     remove(target_filename)
        return 0

    @staticmethod
    def getLatestBuildNumber():
        """
        sample implementation:
        @return: build number (integer)
        """
        # buildnum = 0
        # try:
        #     # read the buildnum.txt and get the currect build number
        #     printLog("Getting the latest build number from {} on {} branch...".format(BUILD_ROOT_PATH, APP_VERSION))
        #     with open(BUILDNUM_FILE_PATH) as fd:
        #         content = filter(lambda x: not x.startswith('\n'), fd.readlines())
        #         buildnum = int(content[0].split('-')[1][1:])
        #         printLog("the latest build number is {} on {} branch".format(buildnum, APP_VERSION))
        # except IOError:
        #     printLog("File %s open error." % BUILDNUM_FILE_PATH, logging.ERROR)
        # except Exception, e:
        #     printLog("Caught Exception when getting latest build number: %s" % e.message, logging.ERROR)
        # return buildnum
        return 10

    def do_changeDeviceTime(self, str_arg=''):
        """
        change device time
        usage: changeDeviceTime <min>
        e.g. changeDeviceTime 60  # adjust to 60 minutes later
        @param str_arg: time in minutes (string)
        """
        # self.resultFlag=change_phone_time(int(self.validateDigit(str_arg)), self.deviceId)
        cmd = 'python {}/changePhoneTime.py {}'.format(CORE_DIR, validateDigit(str_arg))
        print self.sh.getShellCmdOutput(cmd)
        # printLog(self.threadName + "[status=%s]" % self.resultFlag)

    def do_removeApp(self, str_arg=''):
        """
        sample implementation: remove app from device
        """
        self.removeApp(APP_PKG_NAME)

    def do_installApp(self, str_arg=''):
        """
        sample implementation: install app with the specified build number(optional) on device
        @param str_arg: the build number (optional)
        @return: result (boolean)
        """
        if len(str_arg) > 0:
            buildnum = validateDigit(str_arg)
        else:
            buildnum = self.test_buildnum
        target = path.join(LOCAL_BUILD_ROOT_PATH, APP_VERSION,
                           "{}-{}.apk".format(PRODUCT_SHORT_NAME, buildnum))
        if path.isfile(target):
            self.installApp(target)
            return True
        else:
            printLog(self.threadName + "CANNOT ACCESS/FIND BUILD FILE at %s" % target, logging.ERROR)
            return False

    def do_upgradeApp(self, str_arg=''):
        """
        sample implementation: replace app with new version
        @return: result (boolean)
        """
        target = path.join(LOCAL_BUILD_ROOT_PATH, APP_VERSION,
                           "{}-{}.apk".format(PRODUCT_SHORT_NAME, self.test_buildnum))
        if path.isfile(target):
            self.resultFlag = self.upgradeApp(target)
        else:
            printLog(self.threadName + "CANNOT ACCESS/FIND BUILD FILE at %s" % target, logging.ERROR)
            self.resultFlag = False
        return self.resultFlag

    def do_freshInstallApp(self, str_arg=''):
        """
        sample implementation: remove and install app with the specified build number(optional).
        @param str_arg: the build number (optional)
        """
        if len(str_arg) > 0:
            buildnum = validateDigit(str_arg)
        else:
            buildnum = self.test_buildnum
        self.do_removeApp()
        self.do_sleep('1')
        self.do_installApp(buildnum)

    def do_dragDownStatusBar(self, str_arg=''):
        """
        sample implementation: drag to show the Android status bar
        @param str_arg:
        @return: result (boolean)
        """
        return self.do_drag("(%d,1), (%d,%d)" % (self.scn_width / 2, self.scn_width / 2, self.scn_height - 50))

    def do_testAppLog(self, str_arg=''):
        """
        sample implementation: search app log for specified key words
        """
        tmpFn = "tmp.log"
        self.pullFile('/data/data/%s/app_logs/log.txt' % APP_PKG_NAME, tmpFn)
        cmd = "tail -n 100 %s | grep '%s'" % (tmpFn, str_arg)
        output = self.sh.getShellCmdOutput(cmd)
        if str_arg in output:
            self.resultFlag = True
        else:
            self.resultFlag = False
        remove(tmpFn)

    def do_startApp(self, str_arg=''):
        """ sample implementation """
        printLog(self.threadName + "[running command 'startApp %s']" % str_arg)
        self.startApp(APP_LAUNCH_ACTIVITY)
        self.do_sleep('5')

    def do_stopApp(self, str_arg=''):
        """ sample implementation """
        printLog(self.threadName + "[running command 'stopApp %s']" % str_arg)
        self.stopApp(APP_PKG_NAME)

    def do_removeAppLog(self, str_arg=''):
        """ sample implementation """
        self.do_stopApp(str_arg)
        self.removeFile(r'/data/data/%s/app_logs/log.txt' % APP_PKG_NAME)

    def do_makeNetworkBroken(self, str_arg=''):
        """ sample implementation """
        self.disableWiFi()
    #        self.disableMobileData()

    def do_makeNetworkBothConnected(self, str_arg=''):
        """ sample implementation """
        self.enableWiFi()
    #        self.enableMobileData()

    def do_makeNetworkWiFiConnected(self, str_arg=''):
        """ sample implementation """
        self.enableWiFi()

    def do_makeNetworkDataConnected(self, str_arg=''):
        """ sample implementation """
        self.disableWiFi()
        self.enableMobileData()

    def do_showNotificationCount(self, str_args):
        """
        sample implementation: for debug or assistance only
        @param str_args:
        @return: count (integer)
        """
        count = self.__getChildrenCount("id/card_holder_id")
        printLog(self.threadName + 'There are %d notifications.' % count)
        return count

    def do_removeNotification(self, str_arg=''):
        """ sample implementation """
        arg = '(%d,%d) (%d,%d)' % (
            int(self.scn_width * 0.1), 200, int(self.scn_width * 0.9), 200)
        self.do_drag(arg)

    def do_testMonkeyTest(self, str_arg):
        """
        run Monkey test for the given count times (default is 500)
        e.g. testMonkeyTest 5000
        @param str_arg: count times
        """
        if len(str_arg) == 0:
            count = 500
        else:
            count = validateDigit(str_arg)
        printLog(self.threadName + 'run monkey test.')
        self.resultFlag = self.runMonkeyTest(APP_PKG_NAME, count)
        return self.resultFlag
