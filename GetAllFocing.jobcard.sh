#!/bin/sh

date=$1
cycl=$2
mesh=$3

meshname="${mesh##*/}"
meshname="${meshname: 0: -4}"

jobcard="PreProcess.RWPS.$1.$2.jobcard"
outputfile="PreProcess.RWPS.$1.$2.out"

rm $jobcard

echo "#!/bin/sh" > $jobcard
echo "#PBS -q dev" >> $jobcard
echo "#PBS -l walltime=00:59:00" >> $jobcard
echo "#PBS -A GLWU-DEV" >> $jobcard
echo "#PBS -N RWPS.PreProc" >> $jobcard
echo "#PBS -j oe" >> $jobcard
echo "#PBS -l select=1:ncpus=4:mem=64GB" >> $jobcard
echo "#PBS -o RWPS.PreProc.out" >> $jobcard
echo " " >> $jobcard
echo "cd /lfs/h2/emc/couple/noscrub/keston.smith/RWPSInterpolationUtilities" >> $jobcard
echo " " >> $jobcard

# Setup and load modules 
echo "module load PrgEnv-intel/8.1.0" >> $jobcard
echo "module load craype/2.7.8" >> $jobcard
echo "module load intel/19.1.3.304" >> $jobcard
echo "module load cfp/2.0.4" >> $jobcard
echo "module load prod_util/2.0.8" >> $jobcard
echo "module load prod_envir/2.0.5" >> $jobcard
echo " " >> $jobcard

echo "date=$1" >> $jobcard
echo "cycl=$2" >> $jobcard
echo "mesh=$3" >> $jobcard
echo " " >> $jobcard

echo "meshname=$meshname"  >> $jobcard
echo " " >> $jobcard

echo "rm FetchWinds.out ProcWinds.out FetchCurrents.out ProcCurrents.out FetchWaterLevel.out ProcWaterLevel.out" >> $jobcard
echo " " >> $jobcard

echo "(" >> $jobcard
echo "    sh GetWaterLevel.sh $date $cycl > FetchWaterLevel.out" >> $jobcard
echo "    sh ProcessWaterLevel.sh $date $cycl $mesh  > ProcWaterLevel.out" >> $jobcard
echo ")&" >> $jobcard
echo " " >> $jobcard

echo "(" >> $jobcard
echo "    sh GetWinds.sh $date $cycl  > FetchWinds.out" >> $jobcard
echo "    sh ProcessWindsP.sh $date $cycl $mesh > ProcWinds.out" >> $jobcard
echo ")&" >> $jobcard
echo " " >> $jobcard

echo "(" >> $jobcard
echo "    sh GetCurrents.sh $date $cycl > FetchCurrents.out" >> $jobcard
echo "    sh ProcessCurrents.sh $date $cycl $mesh  > ProcCurrents.out" >> $jobcard
echo ")&" >> $jobcard
echo " " >> $jobcard

echo "wait" >> $jobcard
echo " " >> $jobcard
echo "cp $meshname.$date.$cycl.cwl.stofs.nc $meshname.$date.$cycl.waterlevel.nc" >> $jobcard
echo "cp $meshname.$date.$cycl.vel.stofsxrtofs.nc $meshname.$date.$cycl.current.nc" >> $jobcard
echo "cp rwps_winds.$meshname.$date.$cycl/rwps.est.$meshname.$date.$cycl.wind10m.nc $meshname.$date.$cycl.wind.nc" >> $jobcard

qsub $jobcard > $outputfile
