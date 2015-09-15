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
####2. install Java 7

```bash
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install oracle-java7-installer
...
export JAVA_HOME=/usr/lib/jvm/java-7-oracle
```
Reference: http://blog.csdn.net/longshengguoji/article/details/38466915

####3. configure JDK7
http://www.linuxidc.com/Linux/2014-05/101038.htm

####4. install ia32 libs
```bash
sudo apt-get install -y libc6-i386 lib32stdc++6 lib32gcc1 lib32ncurses5 lib32z1
```
Reference: http://www.cnblogs.com/sink_cup/archive/2011/10/31/ubuntu_x64_android_sdk_java.html

####5. install Android SDK
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
cd /home/your_username/workspace/AndJoin
./AppTester.py smoke
```
make sure you get something like below from the output.
```bash
your_username@your_hostname:~/workspace/AndJoin$ ./AppTester.py apidemos
---------------------------------------------------------------------------------------------------------------
[Main] Log verbosity set to INFO
[Main] Test suite specified: apidemos
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
#### configure config.ini
 * provide the values for each mandatory parameters
 * provide the values for the optional parameters

#### build environment setup
 * Setup local build file directories, build number file and build file.
 * mount remote jenkins build delivery path to local directory and configure that directory in BUILD_ROOT_PATH

#### implement basic functions
 * Implement getCurrentBuildNumber() and getLatestBuildNumber() AppTestRunner.py
 * Implement getBuild(), scanExceptionInApplog() and generateTestReport() in AppTester.py, and Configure APPLOG_FILE_PATH in AppTestRunner.py
 * Configure APP_LAUNCH_ACTIVITY in AppTestRunner.py

#### organize your testcases and test suites
 * I already provided a sample testcase named "test_apidemos.tc" under "tc" directory. You may copy that and rename it to "test_whatever.tc" as you wish.
 * change the section values. e.g. the line before @TITLE specifies the test title and @DESC specifies the description. (NOTE: DO NOT append your title next to @TITLE, just make sure you start on a new line.)
 * provide the test steps under @SETUP, @VALIDATION and @TEARDOWN respectively.
  * Don't know what test steps are available? Try this under your work directory:
  ```bash
  $./helper.py
  ```
  it will list all the available test commands with format and examples.
 * create test suite file
  * again, I already provided a sample test suite file named "apidemos.ts" under "ts" directory. You may copy that and rename it to whatever.ts you wish.
    just make sure you add the testcase filename and a descriptive message with colon in the middle to that file. One line for one testcase - that's the rule ;)

#### configure the DEFAULT_TEST_SUITE in AppTestRunner.py
Now you should be able to run your first test! try:
```bash
$./AppTester.py your_suite_name
```
Good Luck!

#### add your own functions in AppTestRunner.py (optional)
Please read on to find the way in developer part below.

## Developer's guide
coming soon.
