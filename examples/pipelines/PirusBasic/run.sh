#!/bin/bash
# coding: utf-8

# Hardcoded parameters
DB="/pipeline/db/"
OUT="/pipeline/outputs/"
IN="/pipeline/inputs/"
LOG="/pipeline/logs/"
JOB="/pipeline/job/"

# Dynamic parameters loaded from config.json
FILE1=`cat ${IN}config.json | jq ".job.file1"`
DURATION=`cat ${IN}config.json | jq ".job.duration"`
CRASH=`cat ${IN}config.json | jq ".job.crash"`
OUTPUT=`cat ${IN}config.json | jq ".job.outfilename"`
NOTIFY_URL=`cat ${IN}config.json | jq ".pirus.notify_url"`

FILE1=`sed -e 's/^"//' -e 's/"$//' <<<"$FILE1"`
OUTPUT=`sed -e 's/^"//' -e 's/"$//' <<<"$OUTPUT"`
NOTIFY_URL=`sed -e 's/^"//' -e 's/"$//' <<<"$NOTIFY_URL"`

echo "START Plugin de test"
echo "===================="
cd ${JOB}
pwd
ls -l

echo "Environment"
echo "==========="
env
echo "DURATION=${DURATION}"
echo "NOTIFY_URL=${NOTIFY_URL}"


echo "Config.json :"
cat ${IN}config.json


echo "Inputs files"
echo "============"
ls -l ${IN}
echo "tail ${IN}${FILE1}"
tail ${IN}${FILE1}


echo "Loop"
echo "===="
for i in `seq 0 ${DURATION}`
do
    echo "$i %"
    curl -X POST -d '{"progress" : {"min":"0", "max":"'${DURATION}'", "value":"'${i}'", "label" : "'${i}' / '${DURATION}'"}}' ${NOTIFY_URL}
    if [ ${CRASH} = true ] && [ $i = 24]; then
        return 500
    fi
    sleep 1
done

echo "Create output file"
echo "=================="
echo "Gene in refGene that have more than 50 exons:" >  ${OUT}${OUTPUT}
zcat ${DB}/hg19/refGene.txt.zip | awk '$9 > 50{print $13}' >>  ${OUT}${OUTPUT}

echo "Done"
echo "===="
