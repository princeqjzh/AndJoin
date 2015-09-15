#! /usr/bin/python
import sys
import os
import re

sys.path.append(os.path.abspath('.'))
print sys.path
from fw.iDevice import iDevice
from fw.TestUtil import Shell
# import argparse

__author__ = 'Xinquan Wang'


def main(argv):
    # simple command line parameter support. only [-f ini_file] [-h] support
    # usage = "usage: %prog [options]"
    #
    # parser = argparse.ArgumentParser()
    # parser.add_argument("echo")
    # args = parser.parse_args()
    # print args.echo
    # parser = OptionParser(usage)
    #    parser.add_option("-f", "--file", dest="scptfilename",  \
    #              help="specify script file to run", metavar="FILE")
    #    parser.add_option("-r", "--reference", \
    #              help="list fw usage keywords and examples")
    #    (options, args) = parser.parse_args()
    #    if len(args)==0:
    #        parser.print_help()
    #        return
    #    print options
    #    scptfilename=options.scptfilename
    #    print scptfilename

    deviceIds = Shell().getShellCmdOutput(r"adb devices")
    # deviceIdList = filter(lambda x: len(x) > 0, devices.split('\n'))  # .split('\t',1)[0]
    deviceId = None
    connected_RE = re.compile("^\S+\t*device$")
    for line in deviceIds.split('\n'):
        # if deviceIdList[i].strip() == 'List of devices attached':
        #     print 'list start'
        #     deviceIdList = deviceIdList[i+1:]
        #     break
        if connected_RE.match(line):
            deviceId = line.split('\t', 1)[0]
    if deviceId is None:
        print "device/emulator not found. Please check the USB connection or start the emulator and try again."
        return
    # print("Got device %s." % deviceId)

    idev = iDevice(deviceId)
    try_count = 0
    tv = None

    while tv is None:
        if try_count == 0:
            vtext = raw_input("please enter the view text you are looking for:")
        else:
            vtext = raw_input('Sorry, The view was not found. Please check the text in the screen'
                              ' and try again [Q|q to exit]:')
        if vtext.lower() == 'q':
            return
        idev.vc.dump()
        tv = idev.vc.findViewWithText(vtext)
        try_count += 1

    print "The view's id is:", tv.getId()
    # print "target view's tag is:", tv.getTag()

    idev.vc.findViewsWithSameId(tv, [tv])
    # traverse the tree to detect views with the same id
    # if __findViewsWithSameId(tv):
    #     print 'please use the provided string in your testcase.'
    # else:
    #     print 'You can use the id directly in your testcase.'

    # with open(scptfilename) as sf:
    #     steps = map(lambda x: x.strip().strip('\t'), sf.readlines())
    #
    # device.test(scptfilename, TestCase(scptfilename, "", steps, scptfilename))

if __name__ == "__main__":
    main(sys.argv)
