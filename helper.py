#! /usr/bin/python
__author__ = 'innopath'


def printMethodAndDoc(cls, methods):
    for i in range(len(methods)):
        print "%d:\t%s" % (i+1, methods[i][3:])
        doc = getattr(cls, methods[i]).__doc__
        if doc:
            print doc
        else:
            print "\tLacking docstring!"

if __name__ == "__main__":
    from fw.MobieTestRunner import MobieTestRunner

    MobieTestRunnerMethods = []
    for key in MobieTestRunner.__dict__.keys():
        if key.startswith('do_'):
            MobieTestRunnerMethods.append(key)

    from fw.iDevice import iDevice

    iDeviceMethods = []
    for key in iDevice.__dict__.keys():
        if key.startswith('do_'):
            iDeviceMethods.append(key)

    if len(MobieTestRunnerMethods) > 0:
        MobieTestRunnerMethods.sort()

        # print getattr(iDevice, iDeviceMethods[10]).__doc__
        # exec "print iDevice." + iDeviceMethods[10] + ".__doc__"
        print "\nAvailable test functions:"
        printMethodAndDoc(MobieTestRunner, MobieTestRunnerMethods)
    # for i in range(len(MobieTestRunnerMethods)):
    #     print "%d:\t%s" % (i+1, MobieTestRunnerMethods[i][3:])
    #     print getattr(MobieTestRunner, MobieTestRunnerMethods[i]).__doc__

    if len(iDeviceMethods) > 0:
        iDeviceMethods.sort()
        print "\nAvailable device operate functions:"
        printMethodAndDoc(iDevice, iDeviceMethods)
    # for i in range(len(iDeviceMethods)):
    #     print "%d:\t%s" % (i+1, iDeviceMethods[i][3:])
    #     print getattr(iDevice, iDeviceMethods[i]).__doc__
