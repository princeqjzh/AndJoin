#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
test each operation in iDevice using apidemos.
"""
import re
import sys
import os

import unittest

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))
# print sys.path
from fw.iDevice import iDevice
from fw.TestUtil import Shell
# from fw.androidviewclient.viewclient import ViewClient

APIS_PKGNAME = "com.example.android.apis"
APK_FILENAME = "apidemos.apk"


class iDeviceTestCase(unittest.TestCase):

    def setUp(self):
        devices = Shell().getShellCmdOutput(r"adb devices")
        deviceIdList = []
        connected_RE = re.compile("^\S+\t*device$")
        for line in devices.split('\n'):
            if connected_RE.match(line):
                deviceIdList.append(line.split('\t', 1)[0])

        self.assertEqual(len(deviceIdList), 1)
        self.serial_no = deviceIdList[0]
        self.idev = iDevice(self.serial_no)
        # devices = self.idev.adbc.getDevices()
        # self.assertEqual(devices[0].serialno, self.serial_no)

    # def test_01_connect_device(self):
    #     # connect device
    #     # global idev
    #     # adbc, serial_no = ViewClient.connectToDeviceOrExit()
    #
    #     print 'device %s connected.' % self.serial_no

    def test_01_install_app(self):
        self.idev.removeApp(APIS_PKGNAME)
        # self.assertTrue(os.path.isfile('testdata/%s' % APK_FILENAME))
        self.assertEqual(self.idev.installApp('testdata/%s' % APK_FILENAME), 0)

    def test_02_start_activity(self):
        self.idev.do_sleep('2')
        self.idev.do_start("%s/.ApiDemos" % APIS_PKGNAME)
        self.assertTrue(self.idev.do_check('id/action_bar_title API Demos'))

    def test_03_click(self):
        # self.idev.
        self.idev.do_click("id/list(2)")
        self.assertTrue(self.idev.do_check('id/list(1) Activity'))

    # def test_04_drag(self):
    #     # bring up the Views/Drag and Drop page
    #     self.idev.do_start("%s/.view.DragAndDropDemo" % APIS_PKGNAME)
    #     self.assertTrue(self.idev.do_check('id/action_bar_title Views/Drag and Drop'))
    #
    #     self.idev.do_drag("id/drag_dot_1 id/drag_dot_2")
    #     self.idev.do_sleep('5')
    #     self.assertTrue(self.idev.do_check('id/drag_result_text Dropped!'))
    #
    #     self.idev.do_keypress('KEYCODE_BACK')


# def suite():
#     suite = unittest.TestSuite()
#     suite.addTest(test_01_connect_device)
#     suite.addTest(test_02_install_app)
#     return suite

if __name__ == "__main__":
    unittest.main()
