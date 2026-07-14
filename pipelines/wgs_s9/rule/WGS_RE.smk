"""
@author:Rzhang
@file: WGS_RE.smk
@time: 2021/09/13
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
## V2.0
#### update@zhangran,20221018,修改e2.expansionHunter_vcf2tsv.pl路径
## V2.3
配置文件更新/sg2/1.haomeirong/STR_pipeline/variant_catalog_hg19_V20230608.json
注释库更新：/sg2/1.haomeirong/STR_pipeline/Repeat_expansion_info_V20230608V2.txt
流程脚本更新：/sg2/1.haomeirong/STR_pipeline/expansionHunter_vcf2tsvV2.pl
## V3.0
#### update@zhangran,20230801,更新参考基因组版本为hg38
#### update@zhangran,20230801,更新bam文件为deduped.bam
## V3.1
#### update@zhangran,20230920,更新bam文件为deduped.cram
"""

SAMPLES=config["sample"]
ExpansionHunterPath=config["bioSoft"]["ExpansionHunterPath"]
reference=config["reference"]['hg38']["genome"]
ExpansionHunterDatabase=config["reference"]['hg38']["ExpansionHunterDatabase"]
WGScript=config["Self-built-Tools"]["SNV_MT"]["WGScript"]
REjson=config["reference"]['hg38']["REjson"]

rule REall:
    input:
        expand("06_STR/{sample}.expansionHunter.vcf", sample=SAMPLES),
        expand("06_STR/{sample}.expansionHunter.json", sample=SAMPLES),
        expand("06_STR/{sample}.expansionHunter.txt", sample=SAMPLES),
        expand("06_STR/{sample}.expansionHunter.tsv", sample=SAMPLES)
rule expansionhunter:
    input:
         Bam = "00_PreCalling/{sample}.deduped.cram",
         qcfile="07_QC/{sample}.QC.tsv"
    output:
         vcf="06_STR/{sample}.expansionHunter.vcf",
         json="06_STR/{sample}.expansionHunter.json",
         txt="06_STR/{sample}.expansionHunter.txt",
         tsv="06_STR/{sample}.expansionHunter.tsv"
    params:
          dir= directory("06_STR/"),
          prefix="{sample}.expansionHunter",
          softwarepath=ExpansionHunterPath,
          genome = reference,
          STRdata=ExpansionHunterDatabase,
          scriptPath=WGScript,
          rejson=REjson
    threads:1
    resources:
        qsub_vf=30000
    run:
        import json
        SEX = 'female'
        file = open(input.qcfile, 'r', encoding = "utf-8")
        head = file.readline().strip('\r\n')
        ar = head.split('\t')
        #dataindex = ar.index('数据编号')
        sexindex = ar.index('预测性别')
        file.close()
        with open(input.qcfile, 'r', encoding = "utf-8") as Hfp:
            next(Hfp)
            for line in Hfp:
                line = line.strip('\r\n')
                linelist = line.split('\t')
                sex = linelist[sexindex]
                if sex=='M':
                   SEX='male'
                elif sex=='F':
                    SEX='female'
                else:
                    print("ERROR : sex must be M or F")
        print( params.softwarepath+"/bin/ExpansionHunter --reads"+ input.Bam +" --reference "+params.genome+" --variant-catalog "+params.rejson+ " --output-prefix "+params.dir+"/"+params.prefix +" --sex "+ SEX+" --log-level info")
        shell("{params.softwarepath}/bin/ExpansionHunter --reads {input.Bam} --reference {params.genome} --variant-catalog {params.rejson} --output-prefix {params.dir}/{params.prefix} --sex {SEX} --log-level info")
        #shell("python {params.scriptPath}/expansionHunter_json2txt.py {output.json} {params.dir}/{output.txt}")
        with open(output.json, 'r') as f:
            bb = json.load(f)
        out = open(output.txt, 'w')
        out.write('\t'.join('VariantId ReferenceRegion RepeatUnit Genotype GenotypeConfidenceInterval CountsOfSpanningReads CountsOfFlankingReads CountsOfInrepeatReads LocusId AlleleCount Coverage FragmentLength'.strip().split()) + '\n')
        for i in bb['LocusResults']:
            data = []
            data.append(i)
            data.append(bb['LocusResults'][i]['AlleleCount'])
            data.append(bb['LocusResults'][i]['Coverage'])
            data.append(bb['LocusResults'][i]['FragmentLength'])
            for j in bb['LocusResults'][i]['Variants']:
                variant = []
                variant.append(bb['LocusResults'][i]['Variants'][j]['VariantId'])
                variant.append(bb['LocusResults'][i]['Variants'][j]['ReferenceRegion'])
                variant.append(bb['LocusResults'][i]['Variants'][j]['RepeatUnit'])
                if 'Genotype' in bb['LocusResults'][i]['Variants'][j]:
                    Genotypes = '{' + bb['LocusResults'][i]['Variants'][j]['Genotype'] + '}'
                    #Genotypes = Genotypes.replace('/','/STR')
                    variant.append(Genotypes)
                else:
                    variant.append('.')
                if 'GenotypeConfidenceInterval' in bb['LocusResults'][i]['Variants'][j]:
                    Interval = '{' + bb['LocusResults'][i]['Variants'][j]['GenotypeConfidenceInterval'] + '}'
                    variant.append(Interval)
                else:
                    variant.append('.')
                variant.append(bb['LocusResults'][i]['Variants'][j]['CountsOfSpanningReads'])
                variant.append(bb['LocusResults'][i]['Variants'][j]['CountsOfFlankingReads'])
                variant.append(bb['LocusResults'][i]['Variants'][j]['CountsOfInrepeatReads'])
                out.write('\t'.join([str(s) for s in variant]) + '\t' + '\t'.join([str(t) for t in data]) + '\n')
        out.close()

        shell("perl {params.scriptPath}/expansionHunter_vcf2tsvV2.pl {output.txt} {params.STRdata} {output.vcf} {output.tsv}")
