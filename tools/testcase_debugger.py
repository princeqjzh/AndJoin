#! /usr/bin/python
# __author__ = 'innopath'
import argparse
import re
import sys
import os
import traceback

try:
    sys.path.append(os.path.abspath('.'))
    sys.path.append(os.path.abspath('..'))
except:
    pass

from fw.androidviewclient.viewclient import ViewClient
from fw.TestUtil import Shell
from fw.TestRunner import TestCase
from fw.AppTestRunner import AppTestRunner


class TestDevice:
    def __init__(self, device_id):
        self.deviceId = device_id
        # self.androidVersion = getDeviceAndroidVersion(device_id)
        # self.make = getDeviceMake(device_id)
        # self.model = getDeviceModel(device_id)
        # self.operator = getDeviceOperator(device_id)


def getDevice(self, sn='', make=''):
    """
    get device by serial no and/or make
    :param sn: device serial no
    :param make: e.g. Genymotion, Samsung etc.
    :return: Device
    @:rtype: TestDevice
    """
    if len(sn) == 0 and len(make) == 0:
        raise ValueError("getDevice: bad argument.")
    # if len(self.queue) == 1:
    #     return self.queue[0]
    for dc in self.queue:
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


class testcase_debugger:

    def __init__(self):

        # device = TestDevicePool().getDevice()
        # if device is None:
        #     print("NO IDLE DEVICE AVAILABLE. TERMINATE.")
        #     assert False
        # # self.threadName='<'+self.device.model+'_'+self.device.deviceId+'> '
        # print("Got device %s." % device.deviceId)
        devices = Shell().getShellCmdOutput(r"adb devices")
        # deviceIdList = filter(lambda x: len(x) > 0, devices.split('\n'))  # .split('\t',1)[0]
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
            print('List of devices:')
            for j in range(len(deviceIdList)):
                print('%d: %s\n' % (j, deviceIdList[j]))
        try:
            # connect device
            self.adbc, self.serial_no = ViewClient.connectToDeviceOrExit()
            print 'device %s connected.' % self.serial_no
            self.devices = self.adbc.getDevices()
            for device in self.devices:
                print device.serialno
        except:
            traceback.print_exc()
            raise RuntimeError("cannot connect to device.")

    def run(self, tc_file_path):
        tr = AppTestRunner(10, [TestCase.fromFile(tc_file_path)], TestDevice(self.serial_no))
        tr.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("testcase_file_path", help="specify the test case file to be run")  # , default='smoke')
    # parser.add_argument("-d", "--debug_view_id", type=int, help="find view id of specified text", default=0)
    # parser.add_argument("-v", "--verbose", type=int, choices=[0, 1, 2, 3, 4, 5],
    #                     help="increase output verbosity", default=logging.INFO)
    args = parser.parse_args()

    st = testcase_debugger()
    st.run(args.suite)
