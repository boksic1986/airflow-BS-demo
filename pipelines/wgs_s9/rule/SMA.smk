"""
@author:Rzhang
@license: Apache Licence
@file: SMA.smk
@time: 2023/04/24
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
## V1.1
## #### updatee@zhangran,20230424,新增SMA.smk,使用SMNCopyNumberCaller进行SMA calling
## V1.2
#### update@zhangran,20230801,更新参考基因组版本为hg38
#### update@zhangran,20230801,更新bam文件为deduped.bam
#### update@zhangran,20230801,更新SMNCopyNumberCaller参数genome值为38
## V1.3
#### update@zhangran,20230920,更新bam文件为deduped.cram
"""
batch=config["batch"]
SMNCopyNumberCaller=config['bioSoft']['SMNCopyNumberCaller']
SAMPLES=config["sample"]
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
reference=config["reference"]['hg38']["genome"]
wkdir=config["fastqDir"]
python3=config["bioSoft"]["python3"]
Cyrius=config["bioSoft"]["Cyrius"]

rule SMAall:
    input:
       "03_CNV/"+batch+".SMA.tsv",
       "03_CNV/"+batch+".SMA.json",
       #"01_SNV/"+batch+".CYP2D6.tsv",

rule SMA:
    input:
         Bam = expand("00_PreCalling/{sample}.deduped.cram",sample=SAMPLES),
    output:
          bamlist= "03_CNV/{batch}.bamlist",
          tsvFile= "03_CNV/{batch}.SMA.tsv",
          jsonFile= "03_CNV/{batch}.SMA.json",
          #pdfFile= expand("03_CNV/SMA/smn_{sample}.pdf",sample=SAMPLES),
    params:
        genome = reference,
        SMNCaller=SMNCopyNumberCaller,
        bampath=wkdir,
        predix="{batch}.SMA",
        pythonPath=python3
    threads:16
    resources:
        qsub_vf=30000
    run:
        f2 = open(output.bamlist, 'w')
        for i in input.Bam:
            f2.write(params.bampath+'/'+i+'\n')
        f2.close()
        shell("{params.pythonPath}/python3 {params.SMNCaller}/smn_caller.py --manifest {output.bamlist} --genome 38  --prefix {params.predix} --outDir 03_CNV --threads {threads}  --reference {params.genome}")
        shell("sed -i 's/.deduped//g' {output.jsonFile}")
        shell("sed -i 's/.deduped//g' {output.tsvFile}")
        shell("mkdir -p 03_CNV/SMA && {params.pythonPath}/python3 {params.SMNCaller}/smn_charts.py -s {output.jsonFile} -o 03_CNV/SMA")
        data = {}
        with open(output.tsvFile, 'r', encoding = "utf-8") as f:
            next(f)
            for line in f:
                line = line.strip('\r\n')
                linelist = line.split('\t')
                sample=linelist[0].split('.')[0]
                smaValue='\t'.join(linelist[1:len(linelist)])
                data[sample]=smaValue
        for i in data:
            full_path='03_CNV/SMA/'+i+'.SMA.tsv'
            file = open(full_path, 'w')
            file.write('Sample\tisSMA\tisCarrier\tSMN1_CN\tSMN2_CN\tSMN2delta7-8_CN\tTotal_CN_raw\tFull_length_CN_raw\tg.27134T>G_CN\tSMN1_CN_raw'+'\n')
            file.write(i+'\t'+data[i]+'\n')
            file.close()
rule CYP2D6:
    input:
         bamlist= "03_CNV/{batch}.bamlist",
    output:
         tsvFile= "01_SNV/CYP2D6/{batch}.CYP2D6.tsv",
         jsonFile= "01_SNV/CYP2D6/{batch}.CYP2D6.json",
    params:
        bampath=wkdir,
        predix="{batch}.CYP2D6",
    threads:16
    resources:
        qsub_vf=30000
    run:
        shell("mkdir -p 01_SNV/CYP2D6 && {python3}/python3 {Cyrius}/star_caller.py --manifest {input.bamlist} --genome 38  --prefix {params.predix} --outDir 01_SNV/CYP2D6 --threads {threads} --reference {reference}" )
        data = {}
        with open(output.tsvFile, 'r', encoding = "utf-8") as f:
            for line in f:
                line = line.strip('\r\n')
                linelist = line.split('\t')
                sample=linelist[0].split('.')[0]
                genotype=linelist[1]
                filter =  linelist[2]
                data[sample]=genotype
        for i in data:
            full_path='01_SNV/CYP2D6/'+i+'.CYP2D6.tsv'
            file = open(full_path, 'w')
            file.write("CYP2D6\t"+data[i]+'\n')
            file.close()
