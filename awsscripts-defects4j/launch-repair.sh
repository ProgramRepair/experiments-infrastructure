:#
# This script gets copied to the vm and is used for launching experiments. 
# Input arguments: <Project> <start-defect-id> <end-defect-id + 1> <project-checkedout-folder-name> <start-seed> <end-seed> <fault-loc-flag> <path-to-genprog> <path-to-defects4> <test-type> <test-percentage>
# Example to command to run script for full experiment on 26 Chart defects: bash launch-repair.sh Chart 1 27 chart 1 20 false /home/ubuntu/genprog4java /home/ubuntu/defects4j allHuman 100
#

#!/bin/bash
export RESULTS_HOST="54.86.79.205"
export RESULTS_KEYFILE="/home/ubuntu/defect4jvm.pem"
export RESULTS_USER="ubuntu"
export RESULTS_HOST_PATH="rsrepair-results"
export SCP="scp -o StrictHostKeyChecking=false"
export SSH="ssh -o StrictHostKeyChecking=false"
export SHUTDOWN="yes"

project="$1"
startdefectid="$2"
enddefectid="$3"
folder="$4"
startseed="$5"
endseed="$6"
faultlocflag="$7"
genprogpath="$8"
defects4jpath="$9"
testtype="${10}"
testpercent="${11}"

# update genprog4j
cd $genprogpath
hg pull
hg update
cd

# update defects4j
cd $defects4jpath
git pull
./init.sh
cd

# begin experiment"
cd $genprogpath"/defects4j-scripts/"
defectid=$startdefectid
while [ $defectid -lt $enddefectid ]
do
	# launch experiment
	# echo launching run ./runGenProgForBug.sh $project $defectid $genprogpath $defects4jpath $testtype $testpercent $defects4jpath"/ExamplesCheckedOut" $startseed $endseed $faultlocflag
	./runGenProgForBug.sh $project $defectid $genprogpath $defects4jpath $testtype $testpercent $defects4jpath"/ExamplesCheckedOut" $startseed $endseed $faultlocflag &
	currentpid="$currentpid $!"
	wait $currentpid

	# copy results to results-server
	$SSH -i $RESULTS_KEYFILE $RESULTS_USER@$RESULTS_HOST "mkdir -p $RESULTS_HOST_PATH"
	$SCP -i $RESULTS_KEYFILE -r $defects4jpath"/ExamplesCheckedOut/"$folder$defectid"Buggy/" $RESULTS_USER@$RESULTS_HOST:~/$RESULTS_HOST_PATH/
	rm -rf $defects4jpath"/ExamplesCheckedOut/"$folder$defectid"Buggy"
 
	sleep 60
	defectid=`expr $defectid + 1`
done

# experiment-ends. shutdown vm.
shutdownreport() {
	if [ y"$SHUTDOWN" = "yyes" ] ; then
		sudo shutdown -P now &
	fi
	exit 1
}
shutdownreport
