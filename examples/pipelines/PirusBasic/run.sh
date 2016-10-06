#!/bin/sh
# coding: utf-8


DB="/pipeline/db/"
OUT="/pipeline/outputs/"
IN="/pipeline/inputs/"
LOG="/pipeline/logs/"
RUN="/pipeline/run/"


echo "START Plugin de test"
echo "===================="
cd ${RUN}
pwd
ls -l

echo "Environment"
echo "==========="
env

echo "Inputs files"
echo "============"
ls -l ${IN}


echo "Loop"
echo "===="
for i in `seq 0 100`
do
   echo "$i %"
   curl "$NOTIFY$i"
   sleep 1
done

echo "Create output file"
echo "=================="
echo "Gene in refGene that have more than 50 exons:" >  ${OUT}refGenAnalysis.txt
zcat ${DB}refGene.txt.gz | awk '$9 > 50{print $13}' >>  ${OUT}refGenAnalysis.txt

echo "Done"
echo "===="