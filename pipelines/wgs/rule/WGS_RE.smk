# container: config["containers"]["RE"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("RE", {})
ExpansionHunterPath=CONTAINER_TOOLS["ExpansionHunter"]
python3Path=CONTAINER_TOOLS["python3"]
perl=CONTAINER_TOOLS["perl"]
liftover=CONTAINER_TOOLS["liftOver"]

SAMPLES=config["sample"]

ruleHelper=config['src']['ruleHelper']
annotationScript=config['src']['annotationScript']

reference=config["genome"]["fasta"]
liftoverChain=config["genome"]["hg38ToHg19Chain"]

ExpansionHunterDatabase=config["database"]["expansion"]
REjson=config["database"]["expansionCatalog"]


rule REall:
    input:
        expand("06_STR/{sample}.expansionHunter.vcf", sample=SAMPLES),
        expand("06_STR/{sample}.expansionHunter.json", sample=SAMPLES),
        expand("06_STR/{sample}.expansionHunter.txt", sample=SAMPLES),
        expand("06_STR/{sample}.expansionHunter.tsv", sample=SAMPLES)

rule expansionhunter:
    container:
        runtime_container("RE_expansionhunter")
    input:
         Bam=lambda wc: f"00_PreCalling/{wc.sample}.deduped.cram",
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
          rejson=REjson,
          liftover=liftover,
          liftoverChain=liftoverChain,
          helper=ruleHelper,
          annotationScript=annotationScript,
          python3Path=python3Path,
          perl=perl
    shell:
        """
        SEX=$({params.python3Path} {params.helper} expansionhunter-sex --qc {input.qcfile})
        {params.softwarepath} --reads {input.Bam} --reference {params.genome} --variant-catalog {params.rejson} --output-prefix {params.dir}/{params.prefix} --sex "${{SEX}}" --log-level info
        {params.python3Path} {params.helper} expansionhunter-json --input {output.json} --output {output.txt}
        {params.perl} {params.annotationScript} -i {output.txt} -d {params.STRdata} -v {output.vcf} -o {output.tsv} -liftover {params.liftover} -chain {params.liftoverChain}
        """
