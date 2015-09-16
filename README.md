# AndJoin - make each team member able to develop Android tests
======
AndJoin is an automate test framework designed for android App testing in middle-sized agile teams. 
It eases test creation and maintenance and able to Join everyone into Android test development -- that's where the name comes from.

##What you can get from AndJoin?
1. quick runnable testcases to cover your smoke test
2. test logic in natural language
3. flexible testcases to maintain
4. extensible modules to add new test functions
5. scalable architecture to accommadate compatibility test on devices across multiple make/models

##Environment Setup

AndJoin is verified on Ubuntu LTS 12.04 and 14.04. I don't have an exact plan to support Windows yet but already took some actions for the adaptive purpose.

###Setup Your Ubuntu Test Server

####1. install open-ssh server

```bash
sudo apt-get install openssh-server
```
####2. install and configure Java 7

```bash
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install oracle-java7-installer
...
export JAVA_HOME=/usr/lib/jvm/java-7-oracle
```
Reference: 
http://blog.csdn.net/longshengguoji/article/details/38466915
http://www.linuxidc.com/Linux/2014-05/101038.htm

####3. install ia32 libs
```bash
sudo apt-get install -y libc6-i386 lib32stdc++6 lib32gcc1 lib32ncurses5 lib32z1
```
Reference: http://www.cnblogs.com/sink_cup/archive/2011/10/31/ubuntu_x64_android_sdk_java.html

####4. install Android SDK
```bash
cd ~/Downloads/
wget http://dl.google.com/android/android-sdk_r22.6.2-linux.tgz
tar -zxvf android-sdk_r22.6.2-linux.tgz
echo 'export ANDROID_HOME="'$HOME'/Downloads/android-sdk-linux"' >> ~/.bashrc
echo 'export PATH="$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools"' >> ~/.bashrc
```

### Setup AndJoin
unzip the package you downloaded to a directory, e.g. /home/your_username/workspace/AndJoin
start an Android emulator, or connect a Android device to the host machine via USB cable.
#### test your environment
```bash
$cd /home/your_username/workspace/AndJoin
your_username@your_hostname:~/workspace/AndJoin$ ./AppTester.py example
```
make sure you get something like below from the output.
```bash
---------------------------------------------------------------------------------------------------------------
[Main] Log verbosity set to INFO
[Main] Test suite specified: example
[Main] Build number not specified, use latest build.
---------------------------------------------------------------------------------------------------------------
output:List of devices attached 
014697590A01F00F

INFO     Found 1 device(s).
```
(If you encounter other error, check your server setup first and contact me whenever necessary. Make sure you send me the full log output so I can help.)

## AndJoin's guide
With AndJoin, a tester is not required to be familiar with how to control the device before s/he can start writing your own testcases. 
The only prerequisit is basic python programming abilities.
### start customizing AndJoin for your App and run your first automated test
#### Configure config.ini
 * provide the values for each mandatory parameters following the guidance inline
   ```ini
   [APP]
# the product's full name used in test report
PRODUCT_NAME=apidemos

# the short name of the product that may be used in build filename
PRODUCT_SHORT_NAME=apis

# the android package name, e.g. com.google.map
APP_PKG_NAME=com.example.android.apis

# the filename of the app log on device
APPLOG_FILE=

# the app's version prefix used to verify the installed apk file version. e.g. '3.0.' (OPTIONAL)
APP_VERSION_PREFIX = 1.0.

#""" the app's version used to locate the build apk file. e.g. '1.0.0_rel' """
APP_VERSION = 1.0
   ```
 * provide the values for the optional parameters

#### Setup build environment
 * setup local build file directories, build number file and build file in file system. Then set BUILD_FILENAME and LOCAL_BUILD_ROOT_PATH in AppTestRunner.py
   ```python
   BUILD_FILENAME = PRODUCT_NAME + '.apk'
   """ the filename of the apk file"""
   
   LOCAL_BUILD_ROOT_PATH = "/home/your_username/workspace/build/%s" % PRODUCT_NAME
   """ the path of local build root directory """
   ```
 * mount remote jenkins(or other CI tool) build delivery path to local directory and set BUILD_ROOT_PATH to that directory in AppTestRunner.py; Then set BUILDNUM_FILE_PATH and BUILD_FILE_PATH.
   ```python
   BUILD_ROOT_PATH = "/home/your_username/jenkins/%s" % PRODUCT_NAME
   """ the path of remote build root directory"""
   
   BUILDNUM_FILE_PATH = path.join(BUILD_ROOT_PATH, APP_VERSION, 'buildnum.txt')
   """ the path of the file containing build number """
   
   BUILD_FILE_PATH = path.join(BUILD_ROOT_PATH, APP_VERSION, BUILD_FILENAME)
   """ the path of the build file """
   ```
 * implement getCurrentBuildNumber() and getLatestBuildNumber() in AppTestRunner.py
   ```python
   def getCurrentBuildNumber(self):
       """ sample implement: get it from com.xxx.xxx_preferences.xml
       <int name="pref_current_app_version_code" value="604" />
       @return: build number (integer)
       """
   
   @staticmethod
   def getLatestBuildNumber():
       """
       sample implementation:
       @return: build number (integer)
       """
   ```
 * implement getBuild() in AppTester.py
   
   ```python
   def getBuild(self):
        """
        sample implementation:
        get build file from build server and place it in the directory specified in AppTestRunner.installApp()
        @return: result (boolean)
        """
   ```
#### Setup App log
 * implement scanExceptionInApplog() in AppTester.py
   
   ```python
   def scanExceptionInAppLog(self, file_path):
        """
        sample implementation: scan the app log for exceptions, parse the grep output to 2 dicts
        @param file_path: file path
        @return: two maps: one keeps formulated exceptions and the other keeps raw exceptions
        @rtype list
        """
   ```
 * configure APPLOG_FILE_PATH in AppTestRunner.py
   
   ```python
   APPLOG_FILE_PATH = '/data/data/%s/app_logs/%s' % (APP_PKG_NAME, APPLOG_FILE) if len(APPLOG_FILE.strip()) > 0 else ''
   """ log file path (sample) """
   ```
 * configure APP_LAUNCH_ACTIVITY in AppTestRunner.py
   
   ```python
   APP_LAUNCH_ACTIVITY = APP_PKG_NAME + '/.ApiDemos'
   """ the activity name to launch the App """
   ```
#### Customize test report (OPTIONAL)
 * implement generateTestReport() in AppTester.py, or just use the sample implementation provided.

#### Organize your testcases and test suites
 * testcase files have suffix '.tc'. I already provided a sample testcase named "example.tc" under "tc" directory. You may copy that and rename it to whatever.tc as you wish.
 * change the section values. e.g. the line before @TITLE specifies the test title and @DESC specifies the description. (NOTE: DO NOT append your title next to @TITLE, just make sure you start on a new line.)
 * provide the test steps under @SETUP, @VALIDATION and @TEARDOWN respectively.
  * Don't know what test steps are available? Try this under your work directory:
  ```bash
  your_username@your_hostname:~/workspace/AndJoin$./helper.py
  ```
  it will list all the available test commands with format and examples.
 * Create test suite file
  * suite files have suffix '.ts'. Again, I already provided a sample test suite file named "example.ts" under "ts" directory. You may copy that and rename it to whatever.ts you wish.
  * To add new testcases, start a new line, add the testcase filename(without suffix) and a descriptive message with colon in the middle. One line for one testcase - that's the rule ;)

#### configure the DEFAULT_TEST_SUITE in AppTestRunner.py
Now you should be able to run your first test! try:
```bash
your_username@your_hostname:~/workspace/AndJoin$./AppTester.py your_suite_name
```
Good Luck!

#### add your own functions in AppTestRunner.py (optional)
Please read on to find the way in developer part below.

## Developer's guide
coming soon.
