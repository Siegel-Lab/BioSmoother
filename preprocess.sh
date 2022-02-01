#!/bin/bash
#SBATCH srun --pty -p fat --mem 383G -J preprocess_heatmap --time=240:00:00 -o slurm_preprocess_heatmap-%j.out

BED_FOLDER="/work/project/ladsie_012/ABS.2.2/2021-10-26_NS502-NS521_ABS_CR_RADICL_inputMicroC/bed_files"
BED_SUFFIX="RNA.sorted.bed_K1K2.bed_K4.bed_R_D.bed_R_D_K1K2.bed_R_D_PRE1.bed"

BAM_FOLDER="/work/project/ladsie_012/ABS.2.2/20210608_Inputs"
BAM_SUFFIX="R1.sorted.bam"

export SPATIALINDEX_C_LIBRARY="$(pwd)/libspatialindex_c.so"
python3 preprocess.py \
    -l Lister427.sizes \
    -o out/test \
    -a ../heatmap_static/HGAP3_Tb427v10_merged_2021_06_21.gff3 \
    -i "${BED_FOLDER}/NS504_P10_Total_3.${BED_SUFFIX}" P10_Total_Rep3 a \
    -i "${BED_FOLDER}/NS505_N50_Total_1.${BED_SUFFIX}" P10_Total_Rep1 a \
    -i "${BED_FOLDER}/NS508_P10_NPM_1.${BED_SUFFIX}" P10_NPM_Rep1 b \
    -i "${BED_FOLDER}/NS511_N50_NPM_1.${BED_SUFFIX}" N50_NPM_Rep1 b \
    -n "${BAM_FOLDER}/WT1_gDNA_inputATAC.${BAM_SUFFIX}" gDNA_inputATAC col \
    -n "${BAM_FOLDER}/WT1_RNAseq_NS320.${BAM_SUFFIX}" RNAseq_NS320 row