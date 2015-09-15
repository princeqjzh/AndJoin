#! /usr/bin/python

import os, sys
from datetime import *
import re


def format_string(input_str):
    if input_str < 10:
        output = '0' + str(input_str)
    else:
        output = str(input_str)
    return output


'''
@param delta: the time value to be changed in seconds 
'''


def change_phone_time(delta):
    step_result = True
    try:
        f = os.popen('adb shell date')
        phone_date_tmp = f.readline().strip()
        f.close()
        # os.system('adb root')
        if phone_date_tmp is None:
            print 'failed to get phone date. exiting...'
            return False
        # phone_date1 = phone_date_tmp.replace('CST ', '').strip()
        print "Current phone time:", phone_date_tmp
        arg_list = re.split(' +', phone_date_tmp)
        print arg_list
        arg_list.pop(4)
        phone_date = ' '.join(arg_list)
        ''' remove the zone from the string Sun May 10 23:35:34 EDT 2015'''
        print phone_date
        # if phone_date1 == phone_date:
        #     print 'the two output strings are identical!'
        phone_time_value = datetime.strptime(phone_date, "%a %b %d %H:%M:%S %Y")
        new_time = phone_time_value + timedelta(seconds=delta)
        print '{0:<15} {1:>30}'.format("New phone time:", str(new_time))

        phone_new_time_value = str(new_time.year) + format_string(new_time.month) + \
                               format_string(new_time.day) + '.' + format_string(new_time.hour) + \
                               format_string(new_time.minute) + format_string(new_time.second)
        print phone_new_time_value
        print "change to:"
        os.system('adb shell date -s ' + phone_new_time_value)
    # print "Phone time is changed to %s"%phone_new_time_value

    except Exception, e:
        print "Fail to get the time and date on the phone.", e.message
        # print "FAILED TO CHANGE PHONE'S TEST"
        step_result = False
    # else:
    # print "The result of changing phone time value is %d"%result
    finally:
        return step_result


def main(argv):
    if len(argv) == 1:
        print("usage: changePhoneTime.py [time in minute]")
        print("by default adjust time 1 hour forward...")
        delta = 60
    else:
        delta = argv[1]
    try:
        change_phone_time(int(delta) * 60)
        print "Done."
    except Exception:
        print Exception.message


if __name__ == "__main__":
    main(sys.argv)
