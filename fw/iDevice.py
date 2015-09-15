#! /usr/bin/python
# -*- encoding: utf-8 -*-
"""
android UI test framework based on @AndroidViewClient
version 2.0

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

# import system modules
import os
import sys
import traceback
import logging
import re
import time
import filecmp
from subprocess import call
from PIL import Image
from fw.androidviewclient.adbclient import AdbClient

try:
    sys.path.append(os.path.abspath('./%s' % CORE_DIR))
except:
    pass

from fw.TestUtil import printLog, CORE_DIR, Shell, validateDigit, validateString
from fw.androidviewclient.viewclient import ViewClient

# http://stackoverflow.com/questions/366682/how-to-limit-execution-time-of-a-function-call-in-python
from contextlib import contextmanager
import signal

LOG_LEVEL = logging.DEBUG
"""log verbosity level """
SNAPSHOT_IMAGE_FORMAT = 'png'
SNAPSHOT_WIDTH = 480
CONNECT_TIMEOUT = 10
DUMP_TIMEOUT = 300
FETCH_DEVICEINFO_TIMEOUT = 5
REPEAT_TIMES_ON_ERROR = 2
DEFAULT_INTERVAL = 0.5

DEBUG = True


class TimeoutException(Exception):
    pass


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out! signal %d, frame: %s" % (signum, frame))

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def getDeviceIdList():
    devices = Shell().getShellCmdOutput(r"adb devices")  # |awk -F'\t' '{print $1}'
    print devices
    deviceIdList = []  # filter(lambda x: len(x) > 0, devices.split('\n'))  # .split('\t',1)[0]
    connected_RE = re.compile("^\S+\t*device$")
    for line in devices.split('\n'):
        # if deviceIdList[i].strip() == 'List of devices attached':
        #     print 'list start'
        #     deviceIdList = deviceIdList[i+1:]
        #     break
        if connected_RE.match(line):
            deviceIdList.append(line.split('\t', 1)[0])
    if len(deviceIdList) > 0:
        printLog('List of devices attached: \n' + str(deviceIdList))
    return deviceIdList
    # else:
    #     return None


def __getDeviceInfo(deviceId, propName):
    cmd = "adb -s " + deviceId + " shell getprop | awk -F':' '/" + propName + "/ { print $2 }'|tr -d '[] '"
    # add alarm to detect timeout
    shell = Shell()
    counter = 0
    while counter < 2:
        try:
            with time_limit(FETCH_DEVICEINFO_TIMEOUT):
                output = shell.getShellCmdOutput(cmd).splitlines()
                if len(output) > 0:
                    return output[0].strip()
                else:
                    return 'UNKNOWN'
        except TimeoutException:
            printLog("Timed out! Failed to retrieve device info.", logging.ERROR)
            # todo: reboot device or emulator
            output = shell.getShellCmdOutput('adb reboot')
            time.sleep(20)
            counter += 1


def getDeviceAndroidVersion(deviceId):
    return __getDeviceInfo(deviceId, 'build.version.release')


def getDeviceModelId(deviceId):
    return __getDeviceInfo(deviceId, 'ril.model_id')


def getDeviceModel(deviceId):
    return __getDeviceInfo(deviceId, 'ro.product.model')


def getDeviceMake(deviceId):
    return __getDeviceInfo(deviceId, 'ro.product.manufacturer')


def getDeviceOperator(deviceId):
    return __getDeviceInfo(deviceId, 'gsm.sim.operator.alpha')


class TestDevice(object):
    """
    represent a test device
    """
    def __init__(self, device_id):
        self.deviceId = device_id
        """ device identifier (or serial number) """
        # fixme: if emulator dies, this call will hang there.
        self.androidVersion = getDeviceAndroidVersion(device_id)
        """ android version """
        if self.androidVersion == 'UNKNOWN':
            raise RuntimeError('Failed to retrieve device info.')
        self.make = getDeviceMake(device_id)
        """ device make """
        self.model = getDeviceModel(device_id)
        """ device model """
        if self.make.lower() == 'genymotion':
            if 'Nexus' in self.model:
                self.make = 'Google'
            if 'Galaxy' in self.model:
                self.make = 'Samsung'
            if 'Xperia' in self.model:
                self.make = 'Sony'
        self.operator = getDeviceOperator(device_id)
        """ the service operator (telecom carrier)"""
        # self.modelId = getDeviceModelId(id)
        self.idle = True
        """ idle status (boolean) """


class TestDevicePool(list):
    """
    hold a list of connected devices C{TestDevice}
    """
    def __init__(self):
        list.__init__([])
        """ the list of C{TestDevice} """
        for device_id in getDeviceIdList():
            device = TestDevice(device_id)
            printLog("adding device '%s %s (%s, %s, %s)' to pool..." % (device.make, device.model, device.deviceId,
                                                                        device.androidVersion, device.operator),
                     logging.DEBUG)
            self.append(device)

        printLog("Found %d device(s)." % len(self), logging.INFO)

    def getDevice(self, sn='', make=''):
        """
        get device by serial no and/or make
        @param sn: device serial no
        @param make: device make, e.g. Genymotion, Samsung etc.
        @return: the match device
        @rtype: TestDevice
        """
        if len(self) == 0:
            # printLog('NO DEVICE FOUND. QUIT.', logging.ERROR)
            return None
        if len(self) == 1:
            return self[0]
        if len(sn) == 0 and len(make) == 0:
            printLog("More than one device is connected. Please unplug and leave just one.", logging.ERROR)
            return None
        for dc in self:
            print dc.make, make
            if len(make) > 0 and len(sn) == 0:
                if dc.make == make:
                    # print 'make match'
                    return dc
            elif len(sn) > 0 and len(make) == 0:
                if dc.deviceId == sn:
                    return dc
            elif len(sn) > 0 and len(make) > 0:
                if dc.make == make and dc.deviceId == sn:
                    return dc
            else:
                return dc
        return None

    def releaseDevice(self, device_id):
        """
        set device to idel state
        @param device_id: the device serial number
        """
        printLog("Releasing device %s ..." % device_id, logging.INFO)
        for dc in self:
            if dc.deviceId == device_id:
                dc.idle = True
                break

    def listDevices(self):
        """
        list all devices in a formatted manner
        """
        count = 0
        for device in self:
            count += 1
            printLog("Device " + str(count) + ": '%s %s (%s, %s, %s)'" % (
                device.make, device.model, device.deviceId, device.androidVersion, device.operator))
            if device.idle:
                printLog("[Idle]")
            else:
                printLog("[Busy]")


class iDevice(AdbClient):
    """
    intelligent android device based on AndroidViewClient by Diego Torres Milano
    https://github.com/dtmilano/AndroidViewClient
    @author: Xinquan Wang
    """
    DUMP_LIST = ('click', 'clickchild', 'drag', 'keypress', 'longpress', 'swipe', 'start', 'touch')
    """ the list of methods that needs dumping view before being executed """
    NO_DUMP_LIST = ('check', 'checkchild', 'checkTextInclusion')
    """ the list of methods that does NOT need dumping view before being executed """
    dump_view = True
    """ dump view indicator """

    def __init__(self, deviceId):
        self.INTERVAL = DEFAULT_INTERVAL
        """ interval(seconds) between commands """
        self.deviceId = deviceId
        """ the serial number of the connected device """
        self.threadName = '<' + deviceId + '> '
        """ the string to represent the current test thread """
        self.resultFlag = True
        """ the test result flag (boolean) """
        AdbClient.__init__(self, serialno=self.deviceId)
        # Connect to the current device
        self.__connect()
        printLog(self.threadName + '[iDevice] Device %s init completed.' % self.deviceId, logging.DEBUG)

    def __connect(self):
        """
        connect to device or exit
        @raise: EnvironmentError
        """
        printLog(self.threadName + '[iDevice] Connecting to device %s...' % self.deviceId, logging.INFO)
        try:
            self.adbc, serialno = ViewClient.connectToDeviceOrExit(verbose=True, serialno=self.deviceId)
            # print 'Connected.'
            if self.adbc is None:
                printLog(self.threadName + '[iDevice] Failed to connect to Device %s...' % self.deviceId, logging.ERROR)
                return
            # get phone's screen resolution, once connected, it is fixed
            self.scn_width = int(self.adbc.display['width'])
            self.scn_height = int(self.adbc.display['height'])
            printLog(self.threadName + "[iDevice] Device %s's screen resolution is: %d * %d" % (
                self.deviceId, self.scn_width, self.scn_height), logging.DEBUG)
            self.adbc.wake()
            printLog(self.threadName + '[iDevice] Creating View Client... ', logging.DEBUG)
            self.vc = ViewClient(self.adbc, serialno, autodump=False, forceviewserveruse=True)
            printLog(self.threadName + '[iDevice] Device %s connected.' % self.deviceId, logging.INFO)
            # self.resultFlag = True
        except Exception, e:
            printLog(self.threadName + "[iDevice] CANNOT connect to device %s. Please check the USB cable and "
                                       "reconnect the device." % self.deviceId, logging.ERROR)
            # if DEBUG:
            #     traceback.print_exc()
            raise EnvironmentError(e.message)

    def __reconnect(self):
        """
        reconnect to device
        @return: none
        """
        self.restartAdbServer()
        # printLog(self.threadName + '[iDevice] Reconnecting to device...', logging.INFO)
        self.__connect()

    def __del__(self):
        AdbClient.__del__(self)
        self.adbc = None
        self.deviceId = None

    def __compareImage(self, file1, file2):
        """
        compare two image files with specified difference tolerance percentage (2% by default)
        input: two file's name
        @return: True or False
        """
        # arg=self.__validateString(str_arg)
        # file1, file2=arg.split(' ', 1)
        try:
            img1 = Image.open(file1)
            img2 = Image.open(file2)
            if img1.size != img2.size:
                return False
            by1 = img1.tobytes()
            by2 = img2.tobytes()
            # format r,g,b,255,r,g,b,255, 3 bytes = 1 point, 255=separator, total 4 bytes
            l = len(by1) / 4
            # total points and same points
            tp = 0
            sp = 0
            for j in range(l):
                i = j * 4
                tp += 1
                if by1[i] == by2[i] and by1[i + 1] == by2[i + 1] and by1[i + 2] == by2[i + 2]:
                    sp += 1
            # max to 2% diff allowed
            if tp * 0.98 > sp:
                return False
            else:
                return True
        except Exception, e:
            printLog(self.threadName + "Exception in __compareImage: %s" % e.message, logging.ERROR)
            traceback.print_exc()
            return False
        finally:
            img1 = None
            img2 = None

    def __compressImage(self, img_file):
        im = Image.open(img_file)
        printLog(self.threadName + 'compressing snapshot %s...' % img_file)
        ratio = float(SNAPSHOT_WIDTH) / im.size[0]
        height = int(im.size[1] * ratio)
        printLog(self.threadName + "new image size: %d*%d" % (SNAPSHOT_WIDTH, height))
        os.remove(img_file)
        im.resize((SNAPSHOT_WIDTH, height), Image.BILINEAR).save(img_file)

    def __getView(self, raw_view_id):
        """
        parse the raw string and find target view
        2015-08-27: initial version

        @param raw_view_id: a string holding the view id in 3 formats:
         1. id/button
         2. id/card_holder_id(2,0,0,0,0,1)
         3. text/Show me
        @return: view object (View)
        """
        if iDevice.dump_view:
            self.__dumpview()
        id_RE = re.compile("^(id/\D+)\((\S+)\)$")
        if DEBUG:
            printLog(self.threadName + "[__getView] raw view id:%s" % raw_view_id)
        if id_RE.match(raw_view_id):
            # search the child by sequence path
            viewId, seq_string = id_RE.search(raw_view_id).groups()
            if DEBUG:
                printLog(self.threadName + "[__getView] view id:%s, seq:%s" % (viewId, seq_string))
            seqs = seq_string.split(',')
            tv = self.__getChildView(viewId, seqs)
        else:
            # search with the given id directly
            if DEBUG:
                printLog(self.threadName + "finding view by id %s ..." % raw_view_id, logging.DEBUG)
            tv = self.vc.findViewById(raw_view_id)
        # if tv:
        #     printLog('Found view %s.' % raw_view_id, logging.DEBUG)
        #     self.resultFlag = True
        # else:
        #     printLog('Target view %s not found.' % raw_view_id, logging.ERROR)
        #     self.resultFlag = False

        return tv

    def __getChildView(self, parentId, childSeq):
        """
        get the child view of the given parent view
        @param parentId: the parent view id
        @param childSeq: the node path of the child view to the parent view
        @return: the child view (View)
        """
        # child_view = None
        # str_getChildView = "self.vc.findViewById('" + parentId + "')"
        # for index in childSeq:
        #     str_getChildView += ('.children[' + str(index) + ']')
        # printLog(self.threadName + "executing child_view=%s" % str_getChildView)
        # exec 'child_view=' + str_getChildView
        # return child_view
        pv = self.vc.findViewById(parentId)
        if not pv:
            # printLog(self.threadName + '[__getChildView] could not find parent view %s' % parentId, logging.DEBUG)
            return None
        for index in childSeq:
            printLog(self.threadName + '[__getChildView] searching child view: %s[%s]' % (pv.getId(), index),
                     logging.DEBUG)
            cv = pv.children[int(index)]
            if cv:
                printLog(self.threadName + '[__getChildView] found child view: %s' % cv.getId(), logging.DEBUG)
                pv = cv
            else:
                # printLog(self.threadName + '[__getChildView] could not find child of %s' % pv.getId(), logging.DEBUG)
                return None
        return pv

    def __getChildrenCount(self, rootId):
        """
        get the child count of the given root view
        2015-05-26: added to support removing all notifications
        @param rootId: root view id
        @return: the children count (int)
        """
        root = self.vc.findViewById(rootId)
        if root:
            return len(root.children())
        else:
            printLog(self.threadName + '[__getChildrenCount] parent view not found.', logging.ERROR)
            return 0

    def __getChildViewText(self, parentId, childSeq):
        """
        get child view's text
        @param parentId: the parent view id
        @param childSeq: the node path of the child view to the parent view
        @return: the text (String)
        """
        child_view = self.__getChildView(parentId, childSeq)
        if child_view:
            printLog(self.threadName + '[__getChildViewText] found child view of parent %s ' % parentId)
            # np = child_view.namedProperties
            # print np
            # return np.get('text:mText').value.encode(sys.getdefaultencoding())
            return child_view.getText()
        else:
            printLog(self.threadName + '[__getChildViewText] view not found.', logging.ERROR)
            self.resultFlag = False
            return ''

    @staticmethod
    def __getRootViewPosition(child_view):
        """
        get the (X, Y) of the root view of the given child view
        @param child_view: the child view
        @return: (x,y) coordinates of the root view
        """
        while child_view.parent:
            child_view = child_view.parent
            # print self.vc.getAbsolutePositionOfView(child_view)
            if DEBUG:
                print 'parent position: ', repr(child_view.getXY())
                # print 'margin and padding: ', child_view.marginTop, child_view.paddingTop
                print 'position and size: ', child_view.getPositionAndSize()

        return child_view.getXY()

    def __clickChildView(self, parentId, childSeq, offset=(0, 0)):
        """
        2015-05-06: included the offset parameter so that the tool can click on the right view center position
        when the target view does not occupy the full screen.
        the default offset would be {x:0, y:48} where 48 is the vertical offset caused by android status bar
        2015-05-26: adjusted the default offset to (0,0)
        """
        child_view = self.__getChildView(parentId, childSeq)
        if child_view:
            # 2014/09/25: the returned point Y coordinate does not include the status bar height
            # using getAbsolutePositionOfView cannot solve this issue
            point = child_view.getCenter()
            if DEBUG:
                printLog(self.threadName + 'AbsoluteCenterOfView: ' + str(child_view.getCenter()), logging.DEBUG)
                printLog(self.threadName + 'AbsolutePositionOfView: ' + str(child_view.getXY()), logging.DEBUG)
                # printLog(child_view.marginTop)
                # printLog(child_view.paddingTop)
                # printLog(child_view.getXY())
                printLog(self.threadName + self.__getRootViewPosition(child_view), logging.DEBUG)

            printLog(self.threadName + '[__clickChildView] clicking device at (%d, %d) ...' % (
                point[0] + offset[0], point[1] + offset[1]), logging.DEBUG)
            self.adbc.touch(point[0] + offset[0], point[1] + offset[1], "DOWN_AND_UP")
            self.resultFlag = True
        else:
            printLog(self.threadName + '[__clickChildView] view not found.', logging.ERROR)
            self.resultFlag = False

            # point=self.vc.getAbsoluteCenterOfView(child_view)
            # print point.x, ", ", point.y
            # printLog(self.threadName+'[__clickChildView] clicking device at (%d, %d) ...' % (point.x, point.y))
            #        self.md.touch(point.x, point.y, MonkeyDevice.DOWN_AND_UP)

    def __validatePoint(self, point):
        """
        check if the input point is valid
        @param point: a tuple with 2 int elements
        @return: the validated point
        """
        # print point
        if point[0] > self.scn_width:
            raise ValueError('X coordinate: %d out of range.' % point[0])
        if point[1] > self.scn_height:
            raise ValueError('Y coordinate: %d out of range.' % point[1])
        return point

    def __getPointXY(self, raw_string):
        """
        get a single point coordinates
        @param raw_string: the input raw string
        @return: a tuple contain (x, y)
        """
        try:
            # print 'input:',str
            pointRE = re.compile('^\((\d*, *\d*)\)$')
            x, y = pointRE.search(raw_string.strip()).groups()[0].split(',')
            # print 'x: %s, y: %s' % (x,y)
            return self.__validatePoint((int(x), int(y.strip())))
        except AttributeError:
            raise ValueError('Failed to get point coordinates.')

    def __getPointXYs(self, raw_string):
        """
        get 2 points coordinates
        @param raw_string: the input raw string
        @return: a tuple containing the 2 points ((x, y), (x, y))
        """
        try:
            pointsRE = re.compile('^\((\d*\D*, *\D*\d*)\)\D*\((\d*\D*, *\D*\d*)\)$')
            points = pointsRE.search(raw_string.strip()).groups()
            startPoint = (int(points[0].split(',')[0].strip()), int(points[0].split(',')[1].strip()))
            endPoint = (int(points[1].split(',')[0].strip()), int(points[1].split(',')[1].strip()))
            return self.__validatePoint(startPoint), self.__validatePoint(endPoint)
        except AttributeError:
            traceback.print_exc()
            raise ValueError('Failed to get point coordinates.')

    def __dumpview(self):
        """
        dump current screen UI layout within given time limit.
        added to catch the alarm exception so that main thread won't quit (2015-08-11)
        """
        try:
            with time_limit(DUMP_TIMEOUT):
                self.vc.dump()
        except TimeoutException:
            printLog(self.threadName + "Timed out! Dump view failed.", logging.ERROR)

    def do_assert(self, str_arg):
        """
        do assertion to the result of previous step to determine if the step passed or failed.
        e.g. if you expect the result of previous text check match, then write "assert true" following "check id/xx xxx"
        @param str_arg: true of false
        @return: none
        """
        arg = validateString(str_arg)
        if arg not in ('true', 'false'):
            self.resultFlag = False
            raise ValueError('Bad parameter.')
        if (arg == 'true' and self.resultFlag) or (arg == 'false' and not self.resultFlag):
            printLog(self.threadName + '[ASSERT PASS]', logging.DEBUG)
            self.resultFlag = True
        else:
            # printLog(self.threadName+'[status=%s]' % self.resultFlag)
            printLog(self.threadName + '[ASSERT FAIL!]', logging.DEBUG)
            self.resultFlag = False
            raise AssertionError()

    def do_checkchild(self, str_arg):
        """
        [obsoleted] This method is merged with 'check'. Kept here for backward compatibility.
        This is an extension to method 'check' to handle child elements whose id is not unique within the layout.

        @param str_arg: the unique parent ID, the path from parent to target child view, the target text
        @return: none, but resultFlag indicate the result, yes or not

        e.g.  checkChild id/parent (4,3,2,2) my text is text
        note:  the final text string is optinal. If not specified,  will check if the child exists
        """
        arg = validateString(str_arg).strip()
        try:
            # to avoid '  ' two spaces case
            # suppose string like: id/text1 (5,4,2,3,3,3) textfield
            i = arg.index(' ')
            ids = arg[0:i]
            arg = arg[i + 1:].strip()
            if iDevice.dump_view:
                self.__dumpview()
            if ' ' in arg:
                i = arg.index(' ')
                seqs = arg[1:i - 1].split(',')
                arg = arg[i + 1:].strip()
                texts = arg
                target_text = self.__getChildViewText(ids, seqs)
                printLog(self.threadName + '[text on screen: %s]' % target_text)
                self.resultFlag = True
                if texts != '':
                    if texts == target_text:
                        self.resultFlag = True
                    else:
                        self.resultFlag = False
            else:
                seqs = arg[1:-1].split(',')
                if self.__getChildView(ids, seqs):
                    self.resultFlag = True
                else:
                    self.resultFlag = False
        except Exception, e:
            # gbk problem
            self.resultFlag = False
            traceback.print_exc()
            printLog(self.threadName + 'Exception in do_checkchild: %s' % e.message, logging.ERROR)

    def do_check(self, str_arg):
        """
        check id existency(not visibility! sometimes a view does not show up, e.g. widgets in the other launcher page),
        if text is given, check if it is identical with what shows on the screen.
        2015-08-26: merged the checkchild method with this one.

        format: check <id>[(child path id sequence)] [text]
        Note: DO NOT INCLUDE SPACE IN THE CHILD PATH

        e.g. check id/title_text Personalize Homescreen
        e.g. check id/parent(4,3,2,2) my text is text

        @param str_arg: it takes two formats:
            1. The target id, and text to be compared (optional)
            2. The unique parent id, the path from parent to target child view, the target text (optional)
        @return boolean
        """
        # printLog(self.threadName + "[running command 'check %s']" % str_arg)
        str_arg = validateString(str_arg)

        # parse the args
        args = str_arg.split(' ', 1)
        viewId = args[0].strip()
        if len(args) < 2:
            target_text = ''
        else:
            target_text = args[1]
        try:
            # get the target view
            tv = self.__getView(viewId)
            if tv:
                printLog(self.threadName + 'Found view %s.' % viewId, logging.DEBUG)

                if len(target_text) > 0:
                    # get element text, and compare it with the given text value
                    # tmpView=self.vc.findViewWithText(ret[1].strip())
                    tempText = tv.getText()
                    printLog(self.threadName + '[Text on screen: %s, expected text: %s]' % (tempText, target_text),
                             logging.DEBUG)
                    if tempText == target_text:
                        # printLog('CHECK PASS! Text match.', logging.DEBUG)
                        self.resultFlag = True
                    else:
                        printLog(self.threadName + 'CHECK FAILED! Text not match!', logging.ERROR)
                        self.resultFlag = False
            else:
                printLog(self.threadName + 'Target view %s not found.' % viewId, logging.ERROR)
                self.resultFlag = False

        except Exception, e:
            self.resultFlag = False
            printLog(self.threadName + 'Exception in do_check: %s' % e.message, logging.ERROR)
            if DEBUG:
                traceback.print_exc()
        finally:
            return self.resultFlag

    def do_checkTextInclusion(self, str_arg):
        """
        check if the given text is included in the message of the specified resource id. (2015-07-22)
        e.g. checkTextInclusion id/icon_descriptive_text icon to see your Zones.
        """
        # printLog(self.threadName + "[running command 'checkTextInclusion %s']" % str_arg)
        arg = validateString(str_arg)
        ret = arg.split(' ', 1)
        if len(ret) == 1:
            self.resultFlag = False
            raise ValueError('Lacking argument of checkTextInclusion.')
        if iDevice.dump_view:
            self.__dumpview()
        try:
            viewId = ret[0].strip()
            printLog("finding view by id %s ..." % viewId, logging.DEBUG)
            tmpView = self.vc.findViewById(viewId)
            if not tmpView:
                self.resultFlag = False
                printLog(self.threadName + '%s is not visible.' % viewId, logging.ERROR)
                return
            else:
                # get element text, and compare it with the given text value
                tempText = tmpView.getText()
                printLog(self.threadName + '[text on screen: %s]' % tempText)
                if not ret[1].strip() in tempText.strip():
                    self.resultFlag = False
        except Exception, e:
            self.resultFlag = False
            printLog(self.threadName + 'Exception in do_check: %s' % e.message, logging.ERROR)
        finally:
            return self.resultFlag

    def do_clickchild(self, str_arg):
        """
        [obsoleted] click a certain child for one unique ID
        use it while there are multiple same name ID, but there is one unique root parent

        format: clickchild <root node ID> <child branch id list>
        e.g. clickchild id/root (0,1)

        2015-08-27: merged into click method, kept here for backward compatibility
        2015-08-11: using AVC will no longer require including the offset parameter
        ---------------------------------------------------------------------------------
        Below instruction is for Monkeyrunner which is DEPRECATED.
        2015-05-06: updated to include the offset parameter so that the tool can
        click on the right view center position

        format: clickchild <root node ID> <child branch id list> <root node relative position offset to screen>
        e.g. clickchild id/root (0,1) (18,338)
        """
        # printLog(self.threadName + "[running 'clickchild %s']" % str_arg)
        # arg validation
        arg = validateString(str_arg)
        if iDevice.dump_view:
            self.__dumpview()
        try:
            # to avoid '  ' two spaces case
            # suppose string like: id/button1 (5,2,3,3,3) (0,50)
            # i = arg.index(' ')
            # ids = arg[0:i]
            # arg = arg[i + 1:].strip()
            # seqs = arg[1:-1].split(',')
            arg_list = arg.split(' ')

            if len(arg_list) == 2:
                printLog(self.threadName + 'do_clickChild: using default offset.')
                node_id, seqs = arg_list
                self.__clickChildView(node_id, seqs[1:-1].split(','))
            elif len(arg_list) == 3:
                # node_id, seqs, offset = arg_list
                # self.__clickChildView(node_id, seqs[1:-1].split(','), self.__getPointXY(offset.strip()))
                raise ValueError("using AVC will NO LONGER require including the offset parameter.")
            else:
                raise ValueError('missing argument.')
        except ValueError:
            printLog(self.threadName + 'do_clickChild: click failed', logging.ERROR)
            traceback.print_exc()
            self.resultFlag = False
            time.sleep(1)
            # finally:
            #    printLog(self.threadName + "[status=%s]" % self.resultFlag)

    def do_click(self, str_arg):
        """
        click by a view id(or parent id with child path), a point in (x, y) coordinates,
        or the text in a view (text box, button etc.).

        2015-05-14: modified to include the way to click by text
        http://www.softteco.com/blog/android-decoding-click-low-level-event/
        2015-08-27: merged the clickchild method

        format: click <view_id>|<view_id>(child path id sequence)|text/<target text>|(x,y)
        e.g. click id/button
        e.g. click id/card_holder_id(2,0,0,0,0,1)
        e.g. click text/Show me
        e.g. click (100,200)

        """
        arg = validateString(str_arg)
        for tmp in range(REPEAT_TIMES_ON_ERROR):
            try:
                if arg.startswith('('):
                    point = self.__getPointXY(arg)
                    printLog(self.threadName + '[clicking point %s...]' % arg, logging.DEBUG)
                    self.adbc.touch(point[0], point[1], "DOWN_AND_UP")
                else:
                    if "/" not in arg:
                        raise ValueError('bad argument of do_click().')
                    # get the target view
                    tv = self.__getView(arg)
                    if tv:
                        printLog('Found view %s.' % arg, logging.DEBUG)
                        if DEBUG:
                            printLog(self.threadName + 'tinyStr: %s' % tv.__tinyStr__(), logging.DEBUG)
                            printLog(self.threadName + 'position and size: {}'.format(tv.getPositionAndSize()),
                                     logging.DEBUG)
                        printLog(self.threadName + '[clicking id %s...]' % arg, logging.DEBUG)
                        tv.touch()
                    else:
                        printLog('Target view %s not found.' % arg, logging.ERROR)
                        self.resultFlag = False
                return
            except Exception, e:
                printLog(self.threadName + 'do_click: the %dst try failed due to %s, will retry.' % (tmp, e.message),
                         logging.ERROR)
                # self.reconnect()
                time.sleep(1)
                continue
                # finally:
                #     printLog(self.threadName + "[status=%s]" % self.resultFlag)
        printLog(self.threadName + 'CLICK FAILED: still can\'t make the click. please check the test environment.',
                 logging.CRITICAL)
        self.resultFlag = False

    def do_compare(self, str_arg):
        """
        compare a snapshot file with an expected image file(by default in PNG format). this usually follows
        a takesnapshot step in a testcase.
        if the snapshot file is identical with the expected target file, return True.
        otherwise return False.

        (Note: UI checking depends on various external factors, for example, different screen brightness value would
        make the snapshots different, leading to unexpected compare results. therefore comparing snapshots is no longer
        recommended. If you insist on automated pixel-level UI testcases, make sure you have these factors well managed)

        format: compare <live captured snapshot> <target prepared snapshot>
        e.g. 'setup' is a predefined directory to hold prepared snapshots, you may define your own directories.
        takesnapshot app_drawer_icon_on_screen.png
        compare app_drawer_icon_on_screen.png setup/designed_app_drawer_icon.png
        """
        arg = validateString(str_arg)
        source, target = arg.split(' ', 1)
        if os.path.isfile(source):
            # Mar 27 @swang: if target file doesn't exist, copy source file to setup directory for later test
            # 2015-08-27: decided to go to fail path
            if not os.path.isfile(target):
                # copy(source, target)
                self.resultFlag = False
                raise ValueError('COMPARE FAILED: target file not found.')
            # if not self.__compareImage(source, target):
            if not filecmp.cmp(source, target):
                printLog(self.threadName + 'COMPARE FAILED: source file and target file DIFFER!', logging.WARNING)
                self.resultFlag = False
        else:
            self.resultFlag = False
            raise ValueError('COMPARE FAILED: source file not found.')

    def do_comparex(self, str_arg):
        """
        compare a snapshot file with a set of expected files
        if the snapshot file is identical with one of the files, return True.
        otherwise return False.

        """
        arg = validateString(str_arg)
        file1, fileset = arg.split(' ', 1)
        if len(fileset) == 0:
            self.resultFlag = False
            raise ValueError('Bad parameter. Please check your script.')
        if not os.path.isfile(file1):
            self.resultFlag = False
            raise ValueError(file1 + ' not exist, Please check your script.')
        # f_list=[pp1 for pp1 in fileset.split(' ') if pp1!='']
        for fn in fileset.split(' '):
            # print file1, f2
            if not os.path.isfile(fn):
                self.resultFlag = False
                raise ValueError(fn + ' not exist, Please check your script.')
            if self.__compareImage(file1, fn):
                self.resultFlag = True
                print('[Found match. %s and %s are identical.]' % (file1, fn))
                return
        print('[No match found.]')
        self.resultFlag = False

    def do_drag(self, str_arg):
        """
        tap and hold the screen from the start point to the end point, or from the center of the start view to
        the center of the end view

        format:
        drag (x0,y0) (x1,y1)
        drag id/start_view id/end_view

        e.g. drag (0,1) (100,100)
        @param str_arg: the coordinates
        @return: result (boolean)
        """
        # todo: make drag duration (in ms) configurable
        if str_arg.startswith('id'):
            drag_view_RE = re.compile('^id/(?P<start>/S+) *id/(?P<end>/S+)$')
            try:
                m = drag_view_RE.search(str_arg)
                if m:
                    start_view_id = m.group('start')
                    end_view_id = m.group('end')
                    startPoint = self.vc.findViewByIdOrRaise(start_view_id).getCenter()
                    endPoint = self.vc.findViewByIdOrRaise(end_view_id).getCenter()
                else:
                    raise ValueError("Bad view id is found in the given argument {}".format(str_arg))
            except:
                printLog(self.threadName + '[do_drag] FAILED to get view info! Please check the view id provided.',
                         logging.ERROR)
                self.resultFlag = False
                return self.resultFlag
        else:
            startPoint, endPoint = self.__getPointXYs(str_arg)

        try:
            printLog(self.threadName + '[do_drag] dragging from (%d,%d) to (%d,%d)...' %
                     (startPoint[0], startPoint[1], endPoint[0], endPoint[1]))
            self.adbc.drag(startPoint, endPoint, 1, 10)
        except RuntimeError:
            self.resultFlag = False
        finally:
            return self.resultFlag

    def do_interval(self, str_arg):
        """
        set sleep interval between each action
        """
        self.INTERVAL = float(validateDigit(str_arg))

    def do_keypress(self, str_arg):
        """
        press a key
        e.g. keypress KEYCODE_HOME

        check http://developer.android.com/reference/android/view/KeyEvent.html for the full list
        KEYCODE_DPAD_LEFT 21
        KEYCODE_DPAD_RIGHT 22
        KEYCODE_DPAD_UP 19
        KEYCODE_DPAD_DOWN 20
        KEYCODE_TAB 61
        KEYCODE_ENTER 66
        ...
        @param str_arg: the keycode

        """
        arg = validateString(str_arg)
        self.adbc.press(arg, "DOWN_AND_UP")

    def do_longpress(self, str_arg):
        """
        long press a UI element by view id, a point or text
        format: 1. longpress <view id> [seconds]
                2. longpress <parent view id>(child path) [seconds]
                3. longpress text/<target text> [seconds]
                4. longpress (100,200) [seconds]

        2015-08-27: add format2 support
        2014-02-17: initial version
        @param str_arg: auguments
        """
        arg = validateString(str_arg)
        # if arg.startswith(r'('):
        # raise ValueError('Bad argument, You may want to use longpress2 with coordinates as auguments.')
        x = 0
        y = 0
        seconds = 2000
        try:
            if arg.startswith(r'('):
                point, sec = arg.split(')')
                if len(sec) > 0:
                    seconds = int(validateDigit(sec))
                x, y = self.__getPointXY(point + ')')
                if not isinstance(x, int):
                    raise ValueError('bad x type: not int.')
            elif arg.startswith('id') or arg.startswith('text'):
                if ' ' in arg:
                    view_id, sec = arg.split(' ')
                    if len(sec) > 0:
                        seconds = int(validateDigit(sec.strip()))
                else:
                    view_id = arg
                # get the target view
                tv = self.__getView(view_id)
                if tv:
                    printLog('Found view %s.' % arg, logging.DEBUG)
                    if DEBUG:
                        print tv.__tinyStr__()
                        print tv.getPositionAndSize()
                    x, y = tv.getCenter()
                    if not isinstance(x, int):
                        raise ValueError('Bad center coordinate: not int.')
                else:
                    printLog('Target view %s not found.' % arg, logging.ERROR)
                    self.resultFlag = False
                    return
            else:
                raise ValueError('bad argument in longpress().')
            # perform long press
            if self.adbc.getSdkVersion() >= 19:
                printLog(self.threadName + "[running longTouch %s, %s...]" % (x, y))
                self.adbc.longTouch(x, y, seconds)

            # solution for API level > 17:
            # http://stackoverflow.com/questions/11142843/how-can-i-use-adb-to-send-a-longpress-key-event
            elif self.adbc.getSdkVersion() > 17:
                cmd = 'adb shell input touchscreen swipe %s %s %s %s %d' % (x, y, x, y, seconds)
                printLog(self.threadName + "[running cmd %s...]" % cmd)
                if call(cmd, shell=True) != 0:
                    printLog("LONGPRESS FAILED: Failed to execute command '%s'." % cmd, logging.ERROR)
                    self.resultFlag = False
            else:
                printLog("LONGPRESS FAILED: API < 18 is not supported yet.", logging.ERROR)
                self.resultFlag = False

        except Exception, e:
            printLog(self.threadName + 'LONGPRESS FAILED:%s' % e.message, logging.WARNING)
            traceback.print_exc()
            self.resultFlag = False

    def do_sleep(self, str_arg):
        """
        sleep for given seconds, can be float
        e.g. sleep 2.5
        @param str_arg: the time argument (string)
        """
        # printLog(self.threadName + "[running command 'sleep %s']" % str_arg)
        self.vc.sleep(float(validateDigit(str_arg)))

    def do_swipe(self, str_arg=''):
        """
        swipe the screen in the given direction (left, right, up or down)
        e.g. swipe left
        @param str_arg: the direction argument (string)
        @return: result (boolean)
        """
        direction = validateString(str_arg)
        if direction == 'left':
            arg = '(%d,%d) (%d,%d)' % (
                int(self.scn_width * 0.9), int(self.scn_height * 0.5), int(self.scn_width * 0.1),
                int(self.scn_height * 0.5))
        elif direction == 'right':
            arg = '(%d,%d) (%d,%d)' % (
                int(self.scn_width * 0.1), int(self.scn_height * 0.5), int(self.scn_width * 0.9),
                int(self.scn_height * 0.5))
        elif direction == 'up':
            arg = '(%d,%d) (%d,%d)' % (int(self.scn_width * 0.5), self.scn_height - 200, int(self.scn_width * 0.5), 0)
        elif direction == 'down':
            arg = '(%d,%d) (%d,%d)' % (int(self.scn_width * 0.5), 100, int(self.scn_width * 0.5), self.scn_height)
        else:
            self.resultFlag = False
            raise ValueError("do_swipe: bad argument.")

        return self.do_drag(arg)

    def do_start(self, str_arg):
        """
        start an activity (openActivity() in C{Android} can do the same thing)
        e.g. start com.android.dial
        @param str_arg: activity (string)
        """
        try:
            # self.adbc.startActivity(validateString(str_arg))
            # the above approach failed in unittest complaining device is offline, weird...
            return self.runAdbCmd('shell am start -n', validateString(str_arg))
        except RuntimeError:
            self.resultFlag = False
            if DEBUG:
                traceback.print_exc()

    def do_takesnapshot(self, str_arg):
        """
        take snapshot of the full screen and save it to the file with the given filename
        format: takesnapshot [filename]
        e.g. takesnapshot a1.png
        @param str_arg: filename (string)
        """
        img = None
        fname = validateString(str_arg)
        try:
            # self.adbc.wake()
            printLog(self.threadName + 'taking snapshot (0,50,%d,%d) ...' %
                     (self.scn_width, self.scn_height))
            img = self.adbc.takeSnapshot(reconnect=True)
            # PIL code
            img = img.crop((0, 50, self.scn_width, self.scn_height))
            img.save(fname, SNAPSHOT_IMAGE_FORMAT)
            # if self.scn_width>SNAPSHOT_WIDTH:
            #    self.compressImage(fname)
            #    os.remove(fname)
            #    im.save(fname)
            printLog(self.threadName + 'snapshot saved as %s' % fname)
        except EnvironmentError:
            self.resultFlag = False
            if DEBUG:
                traceback.print_exc()
        finally:
            img = None

    def do_takesnapshotx(self, str_arg):
        """
        take a snapshot of the given area and save it to the file with the given filename

        format: takesnapshotx (x1,y1) (x2,y2) [filename]
        e.g. takesnapshotx (0,0) (400,400) a2.png
        @param str_arg: arguments and filename (string)
        """
        # img = None
        fname = ""
        args = validateString(str_arg)
        # print args
        try:
            pa = re.compile('^(\(\d*,\d*\))\D*(\(\d*,\d*\))(.+)$')
            matches = pa.search(args.strip()).groups()
            # print matches
            point1 = self.__getPointXY(matches[0])
            point2 = self.__getPointXY(matches[1])
            fname = matches[2].strip()
        except AttributeError, e:
            printLog(self.threadName + "AttributeError: %s" % e.message, logging.ERROR)
            raise ValueError('do_takesnapshotx: Bad parameter.')
        try:
            # self.adbc.wake()
            img = self.adbc.takeSnapshot(reconnect=True)
            printLog(self.threadName + "getting sub image: x0=%d, y0=%d, x1=%d, y1=%d" %
                     (int(point1[0]), int(point1[1]), int(point2[0]), int(point2[1])))
            # PIL code
            img = img.crop((int(point1[0]), int(point1[1]),
                            int(point2[0]), int(point2[1])))
            img.save(fname, SNAPSHOT_IMAGE_FORMAT)
            del img
        except Exception, e:
            self.resultFlag = False
            printLog(self.threadName + "do_takesnapshotx: Exception: %s" % e.message, logging.ERROR)

    def do_type(self, str_arg):
        """
        type the given string in the screen
        e.g. type I'm OK
        @param str_arg: the text to type (string)
        @return: result (boolean)
        """
        try:
            self.adbc.type(validateString(str_arg))
        except Exception, e:
            printLog(self.threadName + 'TYPE FAILED: %s' % e.message)
            self.resultFlag = False
        finally:
            return self.resultFlag
