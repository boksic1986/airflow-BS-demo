# container: config["containers"]["SMA"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("SMA", {})
python3=CONTAINER_TOOLS["python3"]
SMNCopyNumberCaller=CONTAINER_TOOLS["smn_caller"]
SMNCharts=CONTAINER_TOOLS["smn_charts"]
Cyrius=CONTAINER_TOOLS["star_caller"]
SamtoolsPath=CONTAINER_TOOLS["samtools"]

batch=config["batch"]
SAMPLES=config["sample"]
wkdir=config["workDir"]

ruleHelper=config['src']['ruleHelper']
SLC25A13Py=config['src']['SLC25A13Py']

reference=config["genome"]["fasta"]

SLC25A13_region=config["database"]["SLC25A13_region"]


rule SMAall:
    input:
        "03_CNV/"+batch+".SMA.tsv",
        "03_CNV/"+batch+".SMA.json",
        expand("03_CNV/{sample}.SLC25A13.tsv", sample=config["sample"]),
        #"01_SNV/"+batch+".CYP2D6.tsv",

rule SMA:
    container:
        runtime_container("SMA_SMA")
    input:
        Bam = expand("00_PreCalling/{sample}.deduped.cram", sample=config["sample"]),
    output:
        bamlist= "03_CNV/{batch}.bamlist",
        tsvFile= "03_CNV/{batch}.SMA.tsv",
        jsonFile= "03_CNV/{batch}.SMA.json",
    params:
        genome = reference,
        SMNCaller=SMNCopyNumberCaller,
        SMNCharts=SMNCharts,
        predix="{batch}.SMA",
        pythonPath=python3,
        helper=ruleHelper
    shell:
        """
        {params.pythonPath} {params.helper} bam-list --output {output.bamlist} {input.Bam}
        {params.SMNCaller} --manifest {output.bamlist} --genome 38 --prefix {params.predix} --outDir 03_CNV --threads {threads} --reference {params.genome}
        sed -i 's/.deduped//g' {output.jsonFile} {output.tsvFile}
        mkdir -p 03_CNV/SMA
        {params.SMNCharts} -s {output.jsonFile} -o 03_CNV/SMA
        {params.pythonPath} {params.helper} sma-split --input {output.tsvFile} --output-dir 03_CNV/SMA
        """

rule CYP2D6:
    container:
        runtime_container("SMA_CYP2D6")
    input:
         bamlist= "03_CNV/{batch}.bamlist",
    output:
         tsvFile= "01_SNV/CYP2D6/{batch}.CYP2D6.tsv",
         jsonFile= "01_SNV/CYP2D6/{batch}.CYP2D6.json",
    params:
        bampath=wkdir,
        predix="{batch}.CYP2D6",
        python3 = python3,
        Cyrius = Cyrius,
        reference = reference,
        helper = ruleHelper
    shell:
        """
        mkdir -p 01_SNV/CYP2D6
        {params.Cyrius} --manifest {input.bamlist} --genome 38 --prefix {params.predix} --outDir 01_SNV/CYP2D6 --threads {threads} --reference {params.reference}
        {params.python3} {params.helper} cyp2d6-split --input {output.tsvFile} --output-dir 01_SNV/CYP2D6
        """

rule SLC25A13:
    container:
        runtime_container("SMA_SLC25A13")
    input:
        cram=lambda wc: f"00_PreCalling/{wc.sample}.deduped.cram",
        crai=lambda wc: f"00_PreCalling/{wc.sample}.deduped.cram.crai"
    output:
        result = "03_CNV/{sample}.SLC25A13.tsv"
    params:
        python3=python3,
        SLC25A13Py=SLC25A13Py,
        SamtoolsPath=SamtoolsPath,
        reference=reference,
        SLC25A13_region=SLC25A13_region,
    shell:
        """
        {params.python3} {params.SLC25A13Py} --samtools {params.SamtoolsPath} --reference {params.reference} -bam {input.cram} -r {params.SLC25A13_region} -o {output.result}
        """
