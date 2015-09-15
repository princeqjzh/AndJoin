#! /bin/bash
#echo $#
if [ $# -lt 1 ]; then
    echo "Usage: $0 [backup dir]"
    exit 1
fi

dir=$1
echo "-------------------------------------------"
echo "backing up mobie data to $dir ..."
mkdir $dir

echo "backing up snapshots..."
mv *.png $dir
cp -r snapshot $dir
rm -f snapshot/*.png

echo "backing up app log..."
#mkdir $dir/app_logs
adb pull /data/data/com.innopath.mobilemd/app_logs/log.txt $dir

#echo "backing up logcat log..."
#adb pull /data/data/com.innopath.mobilemd/files/logcat.txt $dir

echo "backing up bam file..."
adb pull /data/data/com.innopath.mobilemd/databases/bam1.0 $dir

echo "Done."
echo "check $dir"
echo "-------------------------------------------"
