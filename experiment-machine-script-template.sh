#!/bin/bash
export BATCH_NAME=
export TARBALL=
export CONFIGURATION=
export REPAIR_ARGS=
export SEEDS=
export DEBUG_FILE=
export GENPROG_MANY_BUGS=

export TARBALL_HOST=
export TARBALL_HOST_PATH=
export REPAIR_HOST_PATH=
export HOST_KEYFILE=
export HOST_USER=

export RESULTS_HOST=
export RESULTS_KEYFILE=
export RESULTS_USER=

export SHUTDOWN=
export SHUTDOWN_TIMEOUT=

export RESULTS_HOST_PATH="results-$BATCH_NAME" 
export TARBASE=`basename $TARBALL .tar.gz`
export SCP="scp -o StrictHostKeyChecking=false"
export SSH="ssh -o StrictHostKeyChecking=false" 

cd /root

shutdownreport() {
  echo $TARBALL 
  echo $TARBALL >> $DEBUG_FILE
  date 
  date >> $DEBUG_FILE
  echo "shutting down" 
  echo "shutting down" >> $DEBUG_FILE
  export DEBUG_ARCHIVE=$TARBASE-debug-$CONFIGURATION-`hostname`-`date +%F-%0k-%0M`
  mkdir $DEBUG_ARCHIVE
  cp repair.debug.* $DEBUG_ARCHIVE
  cp repair.cache $DEBUG_ARCHIVE
  cp $DEBUG_FILE $DEBUG_ARCHIVE
  cp experiment-machine-script.sh $DEBUG_ARCHIVE
  tar czf $DEBUG_ARCHIVE.tgz $DEBUG_ARCHIVE
  if [ ! -f $DEBUG_ARCHIVE.tgz ] ; then
    echo "warning: debug archive $DEBUG_ARCHIVE not created" 
    echo "warning: debug archive $DEBUG_ARCHIVE not created" >> $DEBUG_FILE
  fi 
  $SSH -i ~/$RESULTS_KEYFILE $RESULTS_USER@$RESULTS_HOST "mkdir -p $RESULTS_HOST_PATH" 
  $SCP -i ~/$RESULTS_KEYFILE $DEBUG_ARCHIVE.tgz $RESULTS_USER@$RESULTS_HOST:$RESULTS_HOST_PATH/
  if [ x"$SHUTDOWN" = "xyes" ] ; then 
    shutdown -P now & 
  fi 
  exit 1 
} 

echo "----------------------------------------------------------------------" 
echo "----------------------------------------------------------------------" > $DEBUG_FILE
echo "experiment-machine-script.sh begins" 
echo "experiment-machine-script.sh begins" >> $DEBUG_FILE
chmod 0700 $HOST_KEYFILE
chmod 0700 $RESULTS_KEYFILE
date 
date >> $DEBUG_FILE
hostname -a
hostname -a >> $DEBUG_FILE
# These next lines allow us to use all of memory, since there is typically
# no swap on a cloud computing instance. 
echo 200 > /proc/sys/vm/overcommit_ratio
echo 2 > /proc/sys/vm/overcommit_memory
(sleep $SHUTDOWN_TIMEOUT && (echo "*** $SHUTDOWN_TIMEOUT timeout" >> $DEBUG_FILE ; shutdownreport)) & 

if [ ! -f $HOST_KEYFILE ] ; then
  echo "KEYFILE $HOST_KEYFILE not found" 
  echo "KEYFILE $HOST_KEYFILE not found" >> $DEBUG_FILE
  shutdownreport
fi 
if [ ! -f $RESULTS_KEYFILE ] ; then
  echo "KEYFILE $RESULTS_KEYFILE not found" 
  echo "KEYFILE $RESULTS_KEYFILE not found" >> $DEBUG_FILE
  shutdownreport
fi 
if [ ! -d $GENPROG_MANY_BUGS ] ; then 
  echo "GENPROG_MANY_BUGS $GENPROG_MANY_BUGS not found" 
  echo "GENPROG_MANY_BUGS $GENPROG_MANY_BUGS not found" >> $DEBUG_FILE
  shutdownreport
fi 
$SCP -i $HOST_KEYFILE $HOST_USER@$TARBALL_HOST:$TARBALL_HOST_PATH/$TARBALL . 
if [ ! -f $TARBALL ] ; then 
  echo "TARBALL $TARBALL not transferred"
  echo "TARBALL $TARBALL not transferred" >> $DEBUG_FILE
  shutdownreport
fi 
if [ x`ps --no-headers -C repair` != x ] ; then 
  echo "repair processes already running" 
  echo "repair processes already running" >> $DEBUG_FILE
  ps -C repair >& $DEBUG_FILE
  shutdownreport
fi 
$SCP -i $HOST_KEYFILE $HOST_USER@$TARBALL_HOST:$REPAIR_HOST_PATH/repair . 
if [ ! -f repair ] ; then 
  echo "repair executable 'repair' not transferred" 
  echo "repair executable 'repair' not transferred" >> $DEBUG_FILE
  shutdownreport
fi 
mkdir -p $GENPROG_MANY_BUGS
cd $GENPROG_MANY_BUGS
rm -rf $TARBASE
rm -rf *bug*/
tar xf ~/$TARBALL
cd $TARBASE
if [[ -f /root/templates.c ]] 
then
    cp /root/templates.c .
    cp /root/templates.h .
    gcc -E templates.c > templates.i
fi
if [[ -f test.c ]]
then
    gcc -o test test.c
fi
cp /root/experiment-machine-script.sh .
for SEED in $SEEDS ; do 
  echo "----------------------------------------------------------------------" 
  echo "----------------------------------------------------------------------" >> $DEBUG_FILE
  date 
  date >> $DEBUG_FILE 
  echo "seed $SEED" 
  echo "seed $SEED" >> $DEBUG_FILE
  rm -f repair.debug.* repair/* $TARBASE*.tgz
  ~/repair $CONFIGURATION $REPAIR_ARGS --seed $SEED >& $DEBUG_FILE
  export REPORT_ARCHIVE=$TARBASE-s$SEED-$CONFIGURATION-`hostname`-`date +%F-%0k-%0M`
  mkdir $REPORT_ARCHIVE
  cp repair.debug.*  $REPORT_ARCHIVE
  cp repair.cache $REPORT_ARCHIVE
  cp -ra repair/ $REPORT_ARCHIVE
  cp experiment-machine-script.sh $REPORT_ARCHIVE
  tar czf $REPORT_ARCHIVE.tgz $REPORT_ARCHIVE
  if [ ! -f $REPORT_ARCHIVE.tgz ] ; then
    echo "warning: report archive $REPORT_ARCHIVE not created" 
    echo "warning: report archive $REPORT_ARCHIVE not created" >> $DEBUG_FILE
  fi 
  $SSH -i ~/$RESULTS_KEYFILE $RESULTS_USER@$RESULTS_HOST "mkdir -p $RESULTS_HOST_PATH" 
  $SCP -i ~/$RESULTS_KEYFILE $REPORT_ARCHIVE.tgz $RESULTS_USER@$RESULTS_HOST:$RESULTS_HOST_PATH/
done 
shutdownreport
