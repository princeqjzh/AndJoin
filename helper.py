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
    from fw.AppTestRunner import AppTestRunner

    AppTestRunnerMethods = []
    for key in AppTestRunner.__dict__.keys():
        if key.startswith('do_'):
            AppTestRunnerMethods.append(key)

    from fw.iDevice import iDevice

    iDeviceMethods = []
    for key in iDevice.__dict__.keys():
        if key.startswith('do_'):
            iDeviceMethods.append(key)

    if len(AppTestRunnerMethods) > 0:
        AppTestRunnerMethods.sort()

        # print getattr(iDevice, iDeviceMethods[10]).__doc__
        # exec "print iDevice." + iDeviceMethods[10] + ".__doc__"
        print "\nAvailable test functions:"
        printMethodAndDoc(AppTestRunner, AppTestRunnerMethods)
    # for i in range(len(AppTestRunnerMethods)):
    #     print "%d:\t%s" % (i+1, AppTestRunnerMethods[i][3:])
    #     print getattr(AppTestRunner, AppTestRunnerMethods[i]).__doc__

    if len(iDeviceMethods) > 0:
        iDeviceMethods.sort()
        print "\nAvailable device operate functions:"
        printMethodAndDoc(iDevice, iDeviceMethods)
    # for i in range(len(iDeviceMethods)):
    #     print "%d:\t%s" % (i+1, iDeviceMethods[i][3:])
    #     print getattr(iDevice, iDeviceMethods[i]).__doc__
