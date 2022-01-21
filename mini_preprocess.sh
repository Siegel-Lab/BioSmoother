#!/bin/bash
#SBATCH -p slim16 -c 18 -J preprocess_heatmap --mail-user=markus.rainer.schmidt@gmail.com --mail-type END --time=240:00:00 -o slurm_preprocess_heatmap-%j.out

BED_FOLDER="/work/project/ladsie_012/ABS.2.2/2021-10-26_NS502-NS521_ABS_CR_RADICL_inputMicroC/bed_files"
BED_SUFFIX="RNA.sorted.bed_K1K2.bed_K4.bed_R_D.bed_R_D_K1K2.bed_R_D_PRE1.bed"

BAM_FOLDER="/work/project/ladsie_012/ABS.2.2/20210608_Inputs"
BAM_SUFFIX="R1.sorted.bam"

head -n 1000 "${BED_FOLDER}/NS504_P10_Total_3.${BED_SUFFIX}" > "out/data/Mini_NS504_P10_Total_3.${BED_SUFFIX}"
head -n 1000 "${BED_FOLDER}/NS505_N50_Total_1.${BED_SUFFIX}" > "out/data/Mini_NS505_N50_Total_1.${BED_SUFFIX}"
head -n 1000 "${BED_FOLDER}/NS508_P10_NPM_1.${BED_SUFFIX}" > "out/data/Mini_NS508_P10_NPM_1.${BED_SUFFIX}"
head -n 1000 "${BED_FOLDER}/NS511_N50_NPM_1.${BED_SUFFIX}" > "out/data/Mini_NS511_N50_NPM_1.${BED_SUFFIX}"
samtools view -h "${BAM_FOLDER}/WT1_gDNA_inputATAC.${BAM_SUFFIX}" | head -n 1000 | samtools view -b - > "out/data/Mini_WT1_gDNA_inputATAC.${BAM_SUFFIX}"
samtools view -h "${BAM_FOLDER}/WT1_RNAseq_NS320.${BAM_SUFFIX}" | head -n 1000 | samtools view -b - > "out/data/Mini_WT1_RNAseq_NS320.${BAM_SUFFIX}"

head -n 1000 "/work/project/ladsie_012/ABS.2.2/20210608_Inputs/smallRNA/GSM1385605_Tb_WT_DMOG_smallRNA_For.wig" | \
    sed --expression='s/TP13J3/Chr1_3A_Tb427v10/g' > "out/data/Mini_wig.wig"

export SPATIALINDEX_C_LIBRARY="./libspatialindex_c.so"
python3 preprocess.py \
    -l Lister427.sizes \
    -o out/mini \
    -a ../heatmap_static/HGAP3_Tb427v10_merged_2021_06_21.gff3 \
    -i "out/data/Mini_NS504_P10_Total_3.${BED_SUFFIX}" P10_Total_Rep3 a \
    -i "out/data/Mini_NS505_N50_Total_1.${BED_SUFFIX}" P10_Total_Rep1 a \
    -i "out/data/Mini_NS508_P10_NPM_1.${BED_SUFFIX}" P10_NPM_Rep1 b \
    -i "out/data/Mini_NS511_N50_NPM_1.${BED_SUFFIX}" N50_NPM_Rep1 b \
    -n "out/data/Mini_WT1_gDNA_inputATAC.${BAM_SUFFIX}" gDNA_inputATAC col \
    -n "out/data/Mini_WT1_RNAseq_NS320.${BAM_SUFFIX}" RNAseq_NS320 row \
    -n "out/data/Mini_wig.wig" RNAseq_NS320 neither