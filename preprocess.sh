#!/bin/bash
#SBATCH -p fat --mem 383G -J preprocess_heatmap --time=240:00:00 -o slurm_preprocess_heatmap-%j.out --mail-user=markus.rainer.schmidt@gmail.com --mail-type END

./bin/conf_version.sh
cat VERSION

module load ngs/samtools/1.9
source activate $(pwd)/conda_env/smoother


BEDS="/work/project/ladsie_012/ABS.2.2/2021-10-26_NS502-NS521_ABS_CR_RADICL_inputMicroC/bed_files"
BED_SUF="RNA.sorted.bed_K1K2.bed_K4.bed_R_D.bed_R_D_K1K2.bed_R_D_PRE1.bed"

BAMS="/work/project/ladsie_012/ABS.2.2/20210608_Inputs"
BAM_SUF="R1.sorted.bam"

#INDEX_PREFIX="../smoother_out/test_wo_dep_dim"
INDEX_PREFIX="../smoother_out/test"

rm -r ${INDEX_PREFIX}.smoother_index

echo "generating index ${INDEX_PREFIX}"

#DBG_C="--without_dep_dim"
#DBG_C="--uncached --test"
#DBG_C="--uncached"
DBG_C="--test --uncached --simulate_hic"

python3 preprocess.py ${DBG_C} init "${INDEX_PREFIX}" Lister427.sizes -a HGAP3_Tb427v10_merged_2021_06_21.gff3 -d 10000


python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS503_P10_Total_2.${BED_SUF}" "P10_Total_Rep2" -g a

#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS504_P10_Total_3.${BED_SUF}" "P10_Total_Rep3" -g a
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS505_N50_Total_1.${BED_SUF}" "N50_Total_Rep1" -g a
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS506_N50_Total_2.${BED_SUF}" "N50_Total_Rep2" -g a
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS507_N50_Total_3.${BED_SUF}" "N50_Total_Rep3" -g a

python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS508_P10_NPM_1.${BED_SUF}" "P10_NPM_Rep1" -g b

#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS509_P10_NPM_2.${BED_SUF}" "P10_NPM_Rep2" -g b
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS510_P10_NPM_3.${BED_SUF}" "P10_NPM_Rep3" -g b
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS511_N50_NPM_1.${BED_SUF}" "N50_NPM_Rep1" -g b
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS512_N50_NPM_2.${BED_SUF}" "N50_NPM_Rep2" -g b
#python3 preprocess.py ${DBG_C} repl "${INDEX_PREFIX}" "${BEDS}/NS513_N50_NPM_3.${BED_SUF}" "N50_NPM_Rep3" -g b

#python3 preprocess.py ${DBG_C} norm "${INDEX_PREFIX}" "${BAMS}/WT1_gDNA_inputATAC.${BAM_SUF}" "gDNA_inputATAC" -g col
#python3 preprocess.py ${DBG_C} norm "${INDEX_PREFIX}" "${BAMS}/WT1_RNAseq_NS320.${BAM_SUF}" "RNAseq_NS320" -g row


# BROKEN
#python3 preprocess.py ${DBG_C} norm "${INDEX_PREFIX}" \
#                           "${BAMS}/small_rna/ID-000723-NS1_noadapter_longer17.fq.sorted.bam" "small_RNA" -g row

# test with this:
# python3 preprocess.py ${DBG_C} grid-seq-norm -v -b 10000 -R 0.005 -D 1 ${INDEX_PREFIX} caGene

# once -R and -D are correct use this:
# python3 preprocess.py ${DBG_C} grid-seq-norm -van -b 10000 -R 0.005 -D 1 ${INDEX_PREFIX} caGene
