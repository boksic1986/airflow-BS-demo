#!/usr/bin/env perl -w
#---------------------------------------------------------------------------------------------------
#用于处理vcf-VEP-filter-Slivar-split的输出结果,主要是将格式调整成接近WES分析系统的输入文件格式
#运行模式1：家系样本/单先证者样本，从rank文件中获取性别、表型关键词、样本输出顺序
#运行模式2：单先证者样本，不依赖rank文件，将性别和表型关键词作为参数输入
# 20230906,zhangran,更新GenomAD genome 的字段名
use strict;
use File::Basename;
use Encode;
use FindBin qw($Bin);
use Getopt::Long;
use File::Spec;
use File::Path;
use List::Util; 
use List::Util qw/max min sum maxstr minstr shuffle first/;
use YAML::XS;
my ($sampleRankFile, $gender, $phenotype, $splitFile, $fltFile, $vepLocationTsv,  $CS, $configFile, $liftoverArg, $help);
GetOptions (
		"rank|r:s"      => \$sampleRankFile,
		"gender|g:s"    => \$gender,
		"phenotype|p:s" => \$phenotype,
		"input|i=s"	    => \$splitFile,
		"output|o=s"	=> \$fltFile,
		"veplocationtsv|v=s" => \$vepLocationTsv,
		"type:s"	    => \$CS,
		"cfg=s"	        => \$configFile,
		"liftover=s"    => \$liftoverArg,
        "h|help"        => \$help
);
if ((!defined $sampleRankFile and (!defined $gender or !defined $phenotype)) or !defined $splitFile or !defined $vepLocationTsv or !defined $fltFile or !defined $configFile or defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Usage1:     perl $0 -r sampleRankFile -i inputFileOfFamily -o outputFile
	Usage2:     perl $0 -g gender -p phenotypeKeyWords -i inputFileOfSolo -o outputFile
Options:
       -r        <file>               optional, sample rank file
	   -g        <string>             optional, F, M or ND
	   -p        <string>             optional, separated by commas, eg. intellectual_disability.hpo,nystagmus.hpo,global_developmental_delay.hpo
       -i        <file>               input file(result of VEP->slivar->split->split_vep), with split.tsv or split.lenient.tsv suffix
       -o        <file>               output file, with verbose.tsv suffix
       -v        <file>               veplocationtsv, VEP location TSV file
       -type     <string>             optional, 分析类型，如果是carrier，则输入CS
	   -cfg      <string>             配置文件
	   -liftover <file>               liftOver可执行文件，容器运行时应显式传入
	   -h|help   <help information>   this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}
my $fltFileUnsorted = ($fltFile =~ /(.*)tsv/)[0]."tmp.tsv";
open OUT, ">$fltFileUnsorted";
print $fltFileUnsorted;
open OUT1, ">$fltFile";

open CFG, $configFile or die $!;
my $yamlContent = do { local $/; <CFG> };
close CFG;
my $yaml = YAML::XS::Load($yamlContent);
my $keyWords2GeneFile = $yaml->{'database'}->{'keyWords2GeneFile'};
my $transcriptFile = $yaml->{'database'}->{'maneFile'};                          #raw
my $hgncFile = $yaml->{'database'}->{'hgncFile'};                                   #raw, 有EntrezID, 基因个数以HGNC为准
my $omimFile = $yaml->{'database'}->{'omimFile'};                                       #脚本输出
my $hpoFile = $yaml->{'database'}->{'hpoFile'};                                    #raw
my $chpoJson = $yaml->{'database'}->{'chpoJson'};                                           #raw, 不需要EntrezID,需要MIMnum
my $chpoDiseaseJson = $yaml->{'database'}->{'chpoDiseaseJson'};                            #raw，不需要EntrezID,需要MIMnum
my $dualGeneFile = $yaml->{'database'}->{'dualGeneFile'};                                          #人工：http://dida.ibsquare.be/, 网站不再更新，没有EntrezID
my $geneimprintFile = $yaml->{'database'}->{'geneimprintFile'};                           #人工：添加了EntrezID, 其中32个基因名是经过人工校正的，并删除了个别在NCBI无法检测的基因
my $penetranceFile = $yaml->{'database'}->{'penetranceFile'};                    #人工
my $gnomadPLIfile = $yaml->{'database'}->{'gnomadPLIfile'};                              #人工整理，来源于D:\数据库配置文件\基因信息数据库\gene_PLI_Zscore_by_transcript.hg19.xlsx
my $clingenHIfile = $yaml->{'database'}->{'clingenHIfile'};         #raw
my $clingenGeneValidityFile = $yaml->{'database'}->{'clingenGeneValidityFile'};    #raw
my $gene2varTypeFile = $yaml->{'database'}->{'gene2varTypeFile'};           #脚本输出
my $ps1pm5File = $yaml->{'database'}->{'clinvarPS1PM5'};
my $psiFile = $yaml->{'database'}->{'TTNPSI'};
my $highFre_PLPFile = $yaml->{'database'}->{'highFre_PLPFile'};
my $morbidFile = $yaml->{'database'}->{'morbidmapFile'};
my $liftoverChain = $yaml->{'genome'}->{'hg38ToHg19Chain'};
my $liftover = $liftoverArg;
die "liftOver executable is unavailable: $liftover\n" unless defined $liftover && -x $liftover;
die "liftOver chain is unreadable: $liftoverChain\n" unless defined $liftoverChain && -r $liftoverChain;
# my $batch = $yaml->{'batch'};
# my $vepLocationTsv = "01_SNV/".$batch.".vepLocation.lenient.flt.tsv";
# if ($splitFile =~ /flt/){
# 	$vepLocationTsv = "01_SNV/".$batch.".vepLocation.flt.tsv";
# }
my @outPutHeader = ("GeneRankScore","VarRankScore","Variant_Priority_Group","TagKeyWords","TagGenetic","TagPathogenicity","TagQual","TagMAF","Gene","Inheritance","dosageScore","PLI","Disease_CN","Disease_EN","Synopsis_CN","CHPO","VarID_hg19","Var_Pos_hg19","VarID_hg38","Var_Pos_hg38","Consequence","Transcript","All_Trancripts","Overlap_Genes","Exon/Intron","ExonCount","HGVSc","HGVSp","ProteinPos","Pathogenicity","Evidence_List","Evidence","InterVar","Proband_Zygosity","Proband_Format","Proband_VAF","Dad_Zygosity","Dad_Format","Dad_VAF","Mom_Zygosity","Mom_Format","Mom_VAF","Other_Zygosity","Other_Format","Other_VAF","Max_AC/AN","Max_MAF","GnomAD_Hom/Hemi_Count","GnomAD_Total_AC/AN","GnomAD_Total_AF","GnomAD_Total_EAS_AC/AN","GnomAD_Total_EAS_AF","GnomAD_WES_All_AC/AN","GnomAD_WES_All_AF","GnomAD_WES_EAS_AC/AN","GnomAD_WES_EAS_AF","1000G_EAS","Local_AC/AN","Local_AF","LocalPatients","ClinVar_Significances","HGMD_Class:HGMD_Score","Pubmed","PP3/BP4","Prediction","PP2","SpliceAI","dbscSNV","Clingen_Classification","Var_Type_In_Clinvar","Imprint","Digenic","Gene_Alias","OMIM_PhenotypeID","Synopsis_EN","Disease_CHPO","Penetrance_GeneReviews","Penetrance_Hpo","Penetrance_OMIM","rsID","OMIM_GeneID","ClinVar_Methods","ClinVar_Submitters","ClinVar_Conditions","ClinVar_Status","PS1/PM5","Mapability_Score","Simple_Repeat","ClinVarID","HGNC_ID","EntrezID","IMPACT","ClinSig","GnomAD_WGS_All_AC/AN","GnomAD_WGS_All_AF","GnomAD_WGS_EAS_AC/AN","GnomAD_WGS_EAS_AF","inheritanceScore","pathogenicityScore","mafScore","keyWordScore","qualScore");
my @plusClinical = ("649","667","673","775","776","783","1029","1523","2074","2273","2651","2774","2778","2892","3098","3265","3655","3909","4000","4204","4286","4338","4629","4703","5250","5339","5648","5727","6326","6331","6334","6597","6812","6929","7273","8291","8626","8671","8974","9364","9381","10020","10059","10083","10801","11155","23096","23114","23345","23516","54715","57539","65125","65217","79659","81570","92840","157680");
my %sampleSort = ();
my %family2phenotype = ();
my %couple = ();
my %hashGender = ();
my %sampleRole = ();
if (defined $sampleRankFile){
	print "# 0.Get sample rank information.--------------------------------------------------------------\n";
	open RANK, $sampleRankFile or die $!;
	chomp(my $header = <RANK>);
	my @item = split(/\t/, $header);
	my $index5 = 0;
	my %hashInfo = map{$_=>$index5++} @item;
	while (my $line = <RANK>) {
		chomp $line;
		my $rawLine = $line;
		$line =~ s/\[keep\]//;
		my @array = split(/\t/, $line);
		my @rawArray = split(/\t/, $rawLine);
		my @sampleList = ($rawArray[$hashInfo{"ProbandID"}],$rawArray[$hashInfo{"DadID/SpouseID"}],$rawArray[$hashInfo{"MomID/KidID"}],$rawArray[$hashInfo{"OtherID"}]);
		$hashGender{$array[$hashInfo{"ProbandID"}]} = $array[$hashInfo{"ProbandGender"}];
		$hashGender{$array[$hashInfo{"DadID/SpouseID"}]} = $array[$hashInfo{"Dad/SpouseGender"}];
		$hashGender{$array[$hashInfo{"MomID/KidID"}]} = $array[$hashInfo{"Mom/KidGender"}];
		$hashGender{$array[$hashInfo{"OtherID"}]} = $array[$hashInfo{"OtherGender"}];
		foreach my $sample(@sampleList){
			if (defined $sample && $sample =~ /\d/) {
				if ($sample =~ /\[keep\](.*)/) {
					$sample = $1;
					$couple{$sample} = "";
				}
				$family2phenotype{$sample} = $array[$hashInfo{"PhenotypeKeyWords"}];
			}
		}
		$family2phenotype{$array[$hashInfo{"FamilyID"}]} = $array[$hashInfo{"PhenotypeKeyWords"}];
		@{$sampleSort{$array[0]}} = @array[1..4];
		@{$sampleRole{$array[0]}} = @array[5..8];
	}
	close RANK;
	print "# 0.Get sample rank information. Done---------------------------------------------------------\n";
}
print "# 1.Mapping phenotype key words to genelist.--------------------------------------------------\n";
open KEYWORD, $keyWords2GeneFile or die $!;
my $keyWordHeader = <KEYWORD>;
my %phen2CN = ();
my %gene2Phen = ();
while (my $line = <KEYWORD>) {
	chomp $line;                       #format:<中文>\t<同义词>\<配置关键词>\t<基因列表>\t<HPO_id>\t<其他ID>\t<备注>
	my @arr = split(/\t/,$line);
	my @geneList = split(/\|/, $arr[3]);
	$phen2CN{$arr[2]} = $arr[0];
	foreach my $gene (@geneList) {
		push(@{$gene2Phen{$gene}}, $arr[2]);
	}
}
close KEYWORD;
print "# 1.Mapping phenotype key words to genelist. Done---------------------------------------------\n";

print "# 2.Get our selected transcript.--------------------------------------------------------------\n";
my %transcript = ();
my %transcriptPlus = ();
open SELECTED, $transcriptFile or die $!;
chomp(my $transcriptHeader = <SELECTED>);
my @transcriptItem = split(/\t/, $transcriptHeader);
while (my $line = <SELECTED>) {
	chomp $line;
	my @arr = split(/\t/,$line);
	my %h = map{$transcriptItem[$_]=>$arr[$_]}(0..$#transcriptItem);
	$h{'#NCBI_GeneID'} =~ s/GeneID://;
	$h{'RefSeq_nuc'} =~ s/\.\d+//;
	if ($h{'MANE_status'} =~ /MANE Select/){
		$transcript{$h{'#NCBI_GeneID'}}=$h{'RefSeq_nuc'};
	}elsif ($h{'MANE_status'} =~ /MANE Plus Clinical/){
		$transcriptPlus{$h{'#NCBI_GeneID'}}=$h{'RefSeq_nuc'}
	}
}
close SELECTED;
print "# 2.Get our selected transcript. Done---------------------------------------------------------\n";

print "# 3.Annotating gene with OMIM database.-------------------------------------------------------\n";
my %geneInfo = ();
my %hgncID2entrezID = ();
my %symbol2entrezID = ();
open HGNC, $hgncFile or die $!;
chomp(my $hgncHeader = <HGNC>);
my @hgncItem = split(/\t/, $hgncHeader);
while (my $line = <HGNC>) {
	chomp $line;
	my @arr = split(/\t/,$line);
	my %h = map{$arr[$_]="" if !defined $arr[$_]; $hgncItem[$_]=>$arr[$_]}(0..$#hgncItem);
	#print $h{'symbol'}."\t".$#arr."\n";
	if ($h{'entrez_id'} =~ /\d/){
		$geneInfo{$h{'entrez_id'}}{'Gene'} = $h{'symbol'};
		$geneInfo{$h{'entrez_id'}}{'GeneAlias'} = $h{'prev_symbol'}."|".$h{'alias_symbol'};
		$geneInfo{$h{'entrez_id'}}{'GeneAlias'} =~ s/^\|$/\./;
		$geneInfo{$h{'entrez_id'}}{'GeneAlias'} =~ s/^\|//;
		$geneInfo{$h{'entrez_id'}}{'GeneAlias'} =~ s/\|$//;
		$h{'hgnc_id'} =~ s/HGNC://;
		$geneInfo{$h{'entrez_id'}}{'HGNC_ID'} = $h{'hgnc_id'};
		$hgncID2entrezID{$h{'hgnc_id'}} = $h{'entrez_id'};
		$symbol2entrezID{$h{'symbol'}} = $h{'entrez_id'};
	}
}
close HGNC;
#不需要用到EntrezID信息
my %mimnum2hpoID = ();
my %mimnum2hpoTerm = ();
open HPO, $hpoFile or die $!;
<HPO>;
my @hpoTerm = ('entrez-gene-id','entrez-gene-symbol','HPO-Term-ID','HPO-Term-Name','Frequency-Raw','Frequency-HPO','Additional Info from G-D source','G-D source','disease-ID for link');
while (my $line = <HPO>) {
	chomp $line;
	if ($line !~ /OMIM:/){
		next;
	}
	my @arr = split(/\t/, $line);
	my %h = map{$hpoTerm[$_]=>$arr[$_]}(0..$#hpoTerm);
	$h{'disease-ID for link'} =~ s/OMIM://;
	$mimnum2hpoID{$h{'disease-ID for link'}} .= $h{'HPO-Term-ID'}.';';
	$mimnum2hpoTerm{$h{'disease-ID for link'}} .= $h{'HPO-Term-Name'}.';';
}
close HPO;

my %hpoID2chpo = ();
open CHPO, $chpoJson or die $!;
$/="},\n";
while (my $line = <CHPO>) {
	my $hpoID;
	if ($line =~ /"hpoId": "(.*?)",/) {
		$hpoID = $1;
	}
	if ($line =~ /"name_cn": "(.*?)",/) {
		$hpoID2chpo{$hpoID} = $1;
	}
}
close CHPO;

my %mimnum2chpo = ();
my %mimnum2chpoDisease = ();
open DISEASECHPO, $chpoDiseaseJson or die $!;
while (my $line = <DISEASECHPO>){
	my $mimNumber;
	if ($line =~ /"mimNumber": (.*?),/) {
		$mimNumber = $1;
	}
	if ($line =~ /"cnTitle": "(.*?)"\s?,/) {
		$mimnum2chpoDisease{$mimNumber} = $1;
		$mimnum2chpoDisease{$mimNumber} =~ s/【.*//;
		$mimnum2chpoDisease{$mimNumber} =~ s/\w$//;
	}
}
close DISEASECHPO;
$/="\n";
for my $mimNum(keys(%mimnum2hpoID)){
	$mimnum2hpoID{$mimNum} =~ s/;$//;
	my @hpoidList = split(/;/, $mimnum2hpoID{$mimNum});
	foreach my $hpoID(@hpoidList){
		if(exists($hpoID2chpo{$hpoID})){
			$mimnum2chpo{$mimNum} .= $hpoID2chpo{$hpoID}.";";
		}else{
			$mimnum2chpo{$mimNum} .= ".;";
		}
	}
	$mimnum2chpo{$mimNum} =~ s/;$//;
}

open OMIM, $omimFile or die $!;
chomp(my $omimHeader = <OMIM>);
my @omimItem = split(/\t/, $omimHeader);
while (my $line = <OMIM>) {
	chomp $line;
	my @arr = split(/\t/,$line);
	my %h = map{$omimItem[$_]=>$arr[$_]}(0..$#omimItem);
	my @mimnumList = split(/\|/, $h{'OMIM_PhenotypeID'});
	my @CHPOdiseaseList = map{my $chpoDisease= ''; $chpoDisease = $mimnum2chpoDisease{$_} if (exists($mimnum2chpoDisease{$_})); $chpoDisease} @mimnumList;
	my @CHPOtermList = map{my $chpoTerm= ''; $chpoTerm = $mimnum2chpo{$_} if (exists($mimnum2chpo{$_})); $chpoTerm} @mimnumList;
	if (exists($geneInfo{$h{'EntrezID'}})){
		foreach my $term (@omimItem) {
			$geneInfo{$h{'EntrezID'}}{$term}=$h{$term};
		}
		$geneInfo{$h{'EntrezID'}}{'CHPO'} = join("|",@CHPOtermList);
		$geneInfo{$h{'EntrezID'}}{'DiseaseCHPO'} = join("|",@CHPOdiseaseList);
	}
}
close OMIM;

open MORBID, $morbidFile or die $!;
my %gene2morbid = ();
while (my $line = <MORBID>) {
	chomp $line;                       #format:<中文>\t<同义词>\<配置关键词>\t<基因列表>\t<HPO_id>\t<其他ID>\t<备注>
	next if ($line =~ /^#/);
	my @arr = split(/\t/,$line);
	my @geneList = split(/, /, $arr[1]);
	foreach my $gene (@geneList) {
		push(@{$gene2morbid{$gene}}, "morbid");
	}
}
close MORBID;

#注意：双基因的情况可能存在多个基因间两两组合致病的情况
#没有EntrezID信息
open DUAL, $dualGeneFile or die $!;
chomp (my $dualHeader = <DUAL>);
my @dualTerm = split /\t/, $dualHeader;
while (my $line = <DUAL>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my %h = map{$dualTerm[$_]=>$arr[$_]}(0..$#dualTerm);
	if (exists($symbol2entrezID{$h{'#Gene A'}})){
		$geneInfo{$symbol2entrezID{$h{'#Gene A'}}}{'Digenic'} .= $h{'Gene B'}.'('.$h{'Disease name (ORPHANET/OMIM)'}.');';
	}
	if (exists($symbol2entrezID{$h{'Gene B'}})){
		$geneInfo{$symbol2entrezID{$h{'Gene B'}}}{'Digenic'} .= $h{'#Gene A'}.'('.$h{'Disease name (ORPHANET/OMIM)'}.');';
	}
}
close DUAL;

#有EntrezID信息
open IMPRINT, $geneimprintFile or die $!;
chomp (my $imprintHeader = <IMPRINT>);
my @imprintTerm = split /\t/, $imprintHeader;
while (my $line = <IMPRINT>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my %h = map{$arr[$_]="" if !defined $arr[$_];$imprintTerm[$_]=>$arr[$_]}(0..$#imprintTerm);
	$geneInfo{$h{'EntrezID'}}{'Imprint'} = $h{'Status'}.':'.$h{'Expressed Allele'};
}
close IMPRINT;

#有EntrezID信息
open PENETRANCE, $penetranceFile or die $!;
chomp (my $penetranceHeader = <PENETRANCE>);
my @penetranceTerm = split /\t/, $penetranceHeader;
while (my $line = <PENETRANCE>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my %h = map{$penetranceTerm[$_]=>$arr[$_]}(0..$#penetranceTerm);
	$geneInfo{$h{'NCBI_ID'}}{'PenetranceGeneReviews'} = $h{'GeneReview_penetrance'};
	$geneInfo{$h{'NCBI_ID'}}{'PenetranceHpo'} = $h{'HPO_penetrance:遗传模式:疾病名称'};
	$geneInfo{$h{'NCBI_ID'}}{'PenetranceOMIM'} = $h{'OMIM_penetrance'};
}
close PENETRANCE;

#有EntrezID信息
open PLI, $gnomadPLIfile or die $!;
chomp (my $pliHeader = <PLI>);
my @pliTerm = split /\t/, $pliHeader;
while (my $line = <PLI>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my %h = map{$pliTerm[$_]=>$arr[$_]}(0..$#pliTerm);
	if (exists($geneInfo{$h{'EntrezID'}})){
		$geneInfo{$h{'EntrezID'}}{'PLI'} = $h{'PLI'};
		$geneInfo{$h{'EntrezID'}}{'ZScore'} = $h{'Zscore'};
	}
}
close PLI;

#有EntrezID信息
open HI, $clingenHIfile or die $!;
<HI>;<HI>;<HI>;<HI>;<HI>;
chomp (my $hiHeader = <HI>);
my @hiTerm = split /\t/, $hiHeader;
while (my $line = <HI>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my %h = map{$hiTerm[$_]=>$arr[$_]}(0..$#hiTerm);
	if (exists($geneInfo{$h{'Gene ID'}})){
		$geneInfo{$h{'Gene ID'}}{'HI'} = $h{'Haploinsufficiency Score'};
		if ($h{'Haploinsufficiency Score'} =~ /\d/){
			$geneInfo{$h{'Gene ID'}}{'dosageScore'} = 'HI:'.$h{'Haploinsufficiency Score'};
			if ($h{'Triplosensitivity Score'} =~ /\d/){
				$geneInfo{$h{'Gene ID'}}{'dosageScore'} .= '|'.'TS:'.$h{'Triplosensitivity Score'};
			}
		}elsif ($h{'Triplosensitivity Score'} =~ /\d/){
			$geneInfo{$h{'Gene ID'}}{'dosageScore'} = 'TS:'.$h{'Triplosensitivity Score'};
		}else{
			$geneInfo{$h{'Gene ID'}}{'dosageScore'} = '.';
		}
	}
}
close HI;

#没有EntrezID信息
open VALIDITY, $clingenGeneValidityFile or die $!;
<VALIDITY>;<VALIDITY>;<VALIDITY>;<VALIDITY>;
chomp (my $validityHeader = <VALIDITY>);
$validityHeader =~ s/^"//;
$validityHeader =~ s/"$//;
my @validityTerm = split /","/, $validityHeader;
while (my $line = <VALIDITY>) {
	chomp $line;
	$line =~ s/^"//;
	$line =~ s/"$//;
	my @arr = split(/","/, $line);
	my %h = map{$validityTerm[$_]=>$arr[$_]}(0..$#validityTerm);
	$h{'GENE ID (HGNC)'} =~ s/HGNC://;
	if (exists($hgncID2entrezID{$h{'GENE ID (HGNC)'}})){
		$geneInfo{$hgncID2entrezID{$h{'GENE ID (HGNC)'}}}{'ClingenClassification'} = $h{'CLASSIFICATION'}.':'.$h{'MOI'}.':'.$h{'DISEASE LABEL'};  #eg. Definitive:AR:dilated_cardiomyopathy
	}
}
close VALIDITY;

#有EntrezID
open VARTYPE, $gene2varTypeFile or die $!;
chomp (my $typeHeader = <VARTYPE>);
my @typeTerm = split /\t/, $typeHeader;
while (my $line = <VARTYPE>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my %h = map{$typeTerm[$_]=>$arr[$_]}(0..$#typeTerm);
	if (exists($geneInfo{$h{'EntrezID'}})){
		$geneInfo{$h{'EntrezID'}}{'ClinVarVarType'} = $h{'VarType'};
	}
}
close VARTYPE;

my @termList = ('OMIM_GeneID','OMIM_PhenotypeID','Inheritance','DiseaseCN','SynopsisCN','CHPO','HI','dosageScore','PLI','ZScore','ClingenClassification','Imprint','Digenic','PenetranceGeneReviews','PenetranceOMIM','PenetranceHpo','DiseaseCHPO','DiseaseEN','SynopsisEN','ClinVarVarType');
foreach my $entrezID(keys(%geneInfo)){
	foreach my $term(@termList){
		if (!exists($geneInfo{$entrezID}{$term})){
			$geneInfo{$entrezID}{$term} = '.';
		}elsif($geneInfo{$entrezID}{$term} eq ''){
			$geneInfo{$entrezID}{$term} = '.';
		}
	}

}

print "# 3.Annotating gene with OMIM database. Done--------------------------------------------------\n";


###zr add 20230407
print "# 4.White sites with high Fre.--------------------------------------------------------------\n";
open WHITE,$highFre_PLPFile or die $!;
my @whiteInfo = ();
while (my $line = <WHITE>) {
	chomp $line;
	my @arr = split /\t/,$line;
	my $variantid=$arr[1];
	if(defined $variantid and $variantid ne '') {
		push(@whiteInfo, $variantid);
	}
	else {push(@whiteInfo, $arr[2]);}
}
close WHITE;

print "# 4.White sites with high Fre. Done-------------------------------------------------------\n";


print "# 5.PS1/PM5:ClinVar & HGMD database.----------------------------------------------------------\n";
my %hashPM5;
open PM5, $ps1pm5File or die $!;
my $pm5Header = <PM5>;
while (my $line = <PM5>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	$hashPM5{$arr[0]}{$arr[1]} = $arr[2];
}
close PM5;
print "# 5.PS1/PM5:HGMD database. Done---------------------------------------------------------------\n";

print "# 6.TTN PSI data.----------------------------------------------------------\n";
my %TTN2PSI;
open PSI, $psiFile or die $!;
my $psiHeader = <PSI>;
while (my $line = <PSI>) {
	chomp $line;
	my @arr = split(/\t/, $line);
	my $key = "TTN_".$arr[0];
	$TTN2PSI{$key} = $arr[2];
}
close PSI;
print "# 6.TTN PSI data. Done----------------------------------------------------------\n";

open LOC, $vepLocationTsv or die $!;
my $locHeader = "CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tLocation\tAllele\tSYMBOL\tConsequence\tFeature\tGene";
my @locItem = split(/\t/, $locHeader);
my $indexLoc = 0;
my %locInfo = ();
my %locIndex = map{$_=>$indexLoc++} @locItem;
while (my $line = <LOC>) {
	chomp $line;
	my @arr = split(/\t/,$line);
	my $varID = $arr[$locIndex{"CHROM"}]."-".$arr[$locIndex{"POS"}]."-".$arr[$locIndex{"REF"}]."-".$arr[$locIndex{"ALT"}];
	my $transcript = $arr[$locIndex{"Feature"}];
	my $EntrezID = $arr[$locIndex{"Gene"}];
	$locInfo{$varID}{$EntrezID}{$transcript} = $arr[$locIndex{"Location"}];
}
close LOC;

my ($familyId, $sampleID,$keyWordsCount);
my @keyWordList;
if ($splitFile =~ /(JX.*?)(\.flt)?\.slivar\.tsv/) {
	$familyId = $1;
	#print($familyId);
	@keyWordList = split(/\|/, $family2phenotype{$familyId});
}elsif ($splitFile =~ /.*\/(.*)\.split(\.flt)?\.tsv/) {
	$sampleID = $1;
	if (exists($family2phenotype{$sampleID})){
		@keyWordList = split(/\|/, $family2phenotype{$sampleID});
	}
	elsif(defined $phenotype){
		@keyWordList = split(/,/, $phenotype);
	}
}
$keyWordsCount = @keyWordList;
if (defined($familyId) && ${$sampleRole{$familyId}}[1] =~ /3wife|4husband/){
    splice(@outPutHeader,35,1,"Other_Zygosity");
    splice(@outPutHeader,36,1,"Other_Format");
    splice(@outPutHeader,37,1,"Other_VAF");
    splice(@outPutHeader,38,1,"Dad_Zygosity");
    splice(@outPutHeader,39,1,"Dad_Format");
    splice(@outPutHeader,40,1,"Dad_VAF");
    splice(@outPutHeader,41,1,"Mom_Zygosity");
    splice(@outPutHeader,42,1,"Mom_Format");
    splice(@outPutHeader,43,1,"Mom_VAF");
}elsif (defined($familyId) && ${$sampleRole{$familyId}}[2] =~ /6kid/){
    splice(@outPutHeader,38,1,"Other_Zygosity");
    splice(@outPutHeader,39,1,"Other_Format");
    splice(@outPutHeader,40,1,"Other_VAF");
    splice(@outPutHeader,35,1,"Dad_Zygosity");
    splice(@outPutHeader,36,1,"Dad_Format");
    splice(@outPutHeader,37,1,"Dad_VAF");
    splice(@outPutHeader,41,1,"Mom_Zygosity");
    splice(@outPutHeader,42,1,"Mom_Format");
    splice(@outPutHeader,43,1,"Mom_VAF");
}
print "# 7.Main.-------------------------------------------------------------------------------------\n";
print OUT join("\t", @outPutHeader)."\n";
print OUT1 join("\t", @outPutHeader)."\n";
close OUT1;
open IN, $splitFile or die $!;
chomp(my $varHeader = <IN>);
my @varItem = split(/\t/, $varHeader);
my $index6 = 0;
my %varInfo = ();
my %varIndex = map{$_=>$index6++} @varItem;
my @sampleList = @varItem[$varIndex{"FORMAT"}+1..$#varItem];
my $sampleCount = @sampleList;
my @singleItem = ("ID","QUAL","HGVSg","Interpro_domain","ada_score","rf_score","clinvar","clinvar_CLNREVSTAT","clinvar_CLNSIG","clinvar_ClinicalSignificance","clinvar_Submitter","clinvar_CollectionMethod","clinvar_CLNDN","HGMD","HGMD_Rank_Score","HGMD_Class","HGMD_Pubmed","intervar_SIG","local_path","local_path_Pathogenicity","local_path_EvidenceList","local_path_Evidence","GnomADExomes","GnomADExomes_controls_AC","GnomADExomes_controls_AN","GnomADExomes_controls_AF","GnomADExomes_controls_AC_eas","GnomADExomes_controls_AN_eas","GnomADExomes_controls_AF_eas","GnomADExomes_controls_nhomalt","GnomADExomes_controls_nhomalt_male","GnomADExomes_controls_nhomalt_female","GnomADGenomes","GnomADGenomes_controls_AC","GnomADGenomes_controls_AN","GnomADGenomes_controls_AF","GnomADGenomes_controls_AC_eas","GnomADGenomes_controls_AN_eas","GnomADGenomes_controls_AF_eas","GnomADGenomes_controls_nhomalt","GnomADGenomes_controls_nhomalt_male","GnomADGenomes_controls_nhomalt_female","Domain","Repeat","Mapability","LocalMAF","LocalMAF_AC","LocalMAF_AN","LocalMAF_AF",
"IsLocalPLP","IsClinvarPLP","IsException","IsGnomADcommon","IsLocalCommon","IsLowQual","Denovo","LenientDenovo","Hom_P_M","Hemi","SegregatingDominant","SegregatingRecessive","CompoundHet","Hom_P","Hom_M","het_P","het_M",@sampleList); ##Domain字段无
my @insilicoItem = ("REVEL_score","FATHMM_pred","LRT_pred","MetaLR_pred","MetaSVM_pred","MutationAssessor_pred","AlphaMissense_pred","PROVEAN_pred","Polyphen2_HDIV_pred","Polyphen2_HVAR_pred","SIFT_pred");
# my %gene2strand = ();
while (my $line = <IN>) {
	chomp $line;
	my @arr = split(/\t/,$line);
	my $varID = $arr[$varIndex{"CHROM"}]."-".$arr[$varIndex{"POS"}]."-".$arr[$varIndex{"REF"}]."-".$arr[$varIndex{"ALT"}];
	foreach my $key (keys(%varIndex)) {
		if (grep(/^$key$/, @singleItem)) {
			$varInfo{$varID}{$key}=$arr[$varIndex{$key}];
		}elsif (grep(/^$key$/,@insilicoItem)) {
			$varInfo{$varID}{$key}.=$arr[$varIndex{$key}].";";
		}else {
			$varInfo{$varID}{$key}.=$arr[$varIndex{$key}].";";
		}
	}
	# $gene2strand{$arr[$varIndex{"Gene"}]} = $arr[$varIndex{"STRAND"}];
	#caculate Total_All_AC/AN，Total_EAS_AC/AN
	my ($GnomADAcAn,$GnomADAc, $GnomADAn, $GnomADAf,$GnomADEasAcAn,$GnomADEasAc, $GnomADEasAn, $GnomADEasAf) = ('.', '.', '.', '.','.', '.', '.', '.');
	if ($varInfo{$varID}{"GnomADExomes_controls_AN"} =~ /\d/ && $varInfo{$varID}{"GnomADGenomes_controls_AN"} =~ /\d/ && ($varInfo{$varID}{"GnomADExomes_controls_AN"} >0 or $varInfo{$varID}{"GnomADGenomes_controls_AN"} >0)){
		$GnomADAc = $varInfo{$varID}{"GnomADExomes_controls_AC"} + $varInfo{$varID}{"GnomADGenomes_controls_AC"};
		$GnomADAn = $varInfo{$varID}{"GnomADExomes_controls_AN"} + $varInfo{$varID}{"GnomADGenomes_controls_AN"};
		$GnomADAcAn = $GnomADAc.'/'.$GnomADAn;
		$GnomADAf = $GnomADAc/$GnomADAn;
	}
	elsif ($varInfo{$varID}{"GnomADExomes_controls_AN"} =~ /\d/ && $varInfo{$varID}{"GnomADExomes_controls_AN"}>0){
		$GnomADAc = $varInfo{$varID}{"GnomADExomes_controls_AC"};
		$GnomADAn = $varInfo{$varID}{"GnomADExomes_controls_AN"};
		$GnomADAcAn = $GnomADAc.'/'.$GnomADAn;
		$GnomADAf = $GnomADAc/$GnomADAn;
	}
	elsif ($varInfo{$varID}{"GnomADGenomes_controls_AN"} =~ /\d/ && $varInfo{$varID}{"GnomADGenomes_controls_AN"}>0){
		$GnomADAc = $varInfo{$varID}{"GnomADGenomes_controls_AC"};
		$GnomADAn = $varInfo{$varID}{"GnomADGenomes_controls_AN"};
		$GnomADAcAn = $GnomADAc.'/'.$GnomADAn;
		$GnomADAf = $GnomADAc/$GnomADAn;
	}
	if ($varInfo{$varID}{"GnomADExomes_controls_AN_eas"} =~ /\d/ && $varInfo{$varID}{"GnomADGenomes_controls_AN_eas"} =~ /\d/ && ($varInfo{$varID}{"GnomADExomes_controls_AN_eas"}>0 or $varInfo{$varID}{"GnomADExomes_controls_AN_eas"}>0)){
		$GnomADEasAc = $varInfo{$varID}{"GnomADExomes_controls_AC_eas"} + $varInfo{$varID}{"GnomADGenomes_controls_AC_eas"};
		$GnomADEasAn = $varInfo{$varID}{"GnomADExomes_controls_AN_eas"} + $varInfo{$varID}{"GnomADGenomes_controls_AN_eas"};
		$GnomADEasAcAn = $GnomADEasAc.'/'.$GnomADEasAn;
		$GnomADEasAf = $GnomADEasAc/$GnomADEasAn;
	}
	elsif ($varInfo{$varID}{"GnomADExomes_controls_AN_eas"} =~ /\d/ && $varInfo{$varID}{"GnomADExomes_controls_AN_eas"}>0){
		$GnomADEasAc = $varInfo{$varID}{"GnomADExomes_controls_AC_eas"};
		$GnomADEasAn = $varInfo{$varID}{"GnomADExomes_controls_AN_eas"};
		$GnomADEasAcAn = $GnomADEasAc.'/'.$GnomADEasAn;
		$GnomADEasAf = $GnomADEasAc/$GnomADEasAn;
	}
	elsif ($varInfo{$varID}{"GnomADGenomes_controls_AN_eas"} =~ /\d/ && $varInfo{$varID}{"GnomADGenomes_controls_AN_eas"}>0){
		$GnomADEasAc = $varInfo{$varID}{"GnomADGenomes_controls_AC_eas"};
		$GnomADEasAn = $varInfo{$varID}{"GnomADGenomes_controls_AN_eas"};
		$GnomADEasAcAn = $GnomADEasAc.'/'.$GnomADEasAn;
		$GnomADEasAf = $GnomADEasAc/$GnomADEasAn;
	}
	$varInfo{$varID}{'GnomADAcAn'}=$GnomADAcAn;
	$varInfo{$varID}{'GnomADAc'}=$GnomADAc;
	$varInfo{$varID}{'GnomADAn'}=$GnomADAn;
	$varInfo{$varID}{'GnomADAf'}=$GnomADAf;
	$varInfo{$varID}{'GnomADEasAcAn'}=$GnomADEasAcAn;
	$varInfo{$varID}{'GnomADEasAn'}=$GnomADEasAn;
	$varInfo{$varID}{'GnomADEasAc'}=$GnomADEasAc;
	$varInfo{$varID}{'GnomADEasAf'}=$GnomADEasAf;
}
close IN;

# ----- liftover: hg38 -> hg19 -----
my %var2liftover;
my %var2diff;
my $bed = $fltFile =~ s/tsv/bed/r;
my $liftoverBed = $fltFile =~ s/tsv/liftover.bed/r;
my $liftoverUnmap = $fltFile =~ s/tsv/liftover.unmap/r;

open BED, ">$bed" or die "Cannot write $bed: $!";
foreach my $varID (sort keys(%varInfo)) {
    my ($chr, $pos, $ref, $alt) = split /-/, $varID;
    my ($start, $end) = ($pos, $pos+1);
    print BED join("\t", ($chr, $start, $end, $varID)) . "\n";
}
close BED;

`$liftover $bed $liftoverChain $liftoverBed $liftoverUnmap`;

open LIFTOVER, $liftoverBed or die "Cannot read $liftoverBed: $!";
while (my $line = <LIFTOVER>) {
    chomp $line;
    my @arr = split(/\t/, $line);
    my ($chr, $pos, $ref, $alt) = split /-/, $arr[3];
    $var2liftover{$arr[3]} = join("-", ($arr[0], $arr[1], $ref, $alt));
    $var2diff{$arr[3]} = $pos - $arr[1];
}
close LIFTOVER;

unlink $bed, $liftoverBed, $liftoverUnmap;
# ----- liftover done -----

my %varOutPut = ();
my %geneRankScore = ();
my %geneCH = (); # Carrier新加的
foreach my $varID (sort keys(%varInfo)) {
	my $rankScore = 0;
	my @keyList = keys(%{$varInfo{$varID}});
	map {$varInfo{$varID}{$_} =~ s/\;$//} @keyList;
	map {$varInfo{$varID}{$_} =~ s/\&$//} @keyList;
	my ($tagGenetic,$tagPathogenicity,$tagMaf,$tagQual,$tagWhite);
	my ($probandZygosityOut,$dadZygosityOut,$momZygosityOut,$otherZygosityOut,$probandFormatOut,$dadFormatOut,$momFormatOut,$otherFormatOut,$probandVafOut,$dadVafOut,$momVafOut,$otherVafOut,$coupleVAF);
	my ($pm5Out);
	my ($denovoOut,$lenientDenovoOut,$homOut,$homPatOut,$homMatOut,$hetPatOut,$hetMatOut,$hemiOut,$segregatingDominantOut,$segregatingRecessiveOut,$slivarComphetOut);
	my ($maxAcAnOut,$maxMafOut,$homAltCountOut,$predictionOut,$pp3Bp4Out,$pp2Out,$spliceAIout,$spliceAIscoreOut,$maxSpliceAIscore,$dbscSNVOut,$dbscSNVscoreOut);
	# $varPosOut = ($varInfo{$varID}{"HGVSg"} =~ /(chr.*:g\..*\d+)[a-zA-Z]+/)[0];
	# $varPosOut =~ s/g\.//;
	$varInfo{$varID}{"HGVSp"} = &aminoacidAbbr($varInfo{$varID}{"HGVSp"});

	# 基因转录本相关
	my @entrezIdList = split(/;/, $varInfo{$varID}{"Gene"});
	my @geneList = split(/;/, $varInfo{$varID}{"SYMBOL"});
	my @transcriptList = split(/;/, $varInfo{$varID}{"Feature"});
	my @consequenceList = split(/;/, $varInfo{$varID}{"Consequence"});
	my @impactList = split(/;/, $varInfo{$varID}{"IMPACT"});
	my @hgvscList = split(/;/, $varInfo{$varID}{"HGVSc"});
	@hgvscList = map {my $hgvsc = $_; $hgvsc =~ s/^\.$/\.:\./;$hgvsc} @hgvscList;
	my @hgvspList = split(/;/, $varInfo{$varID}{"HGVSp"});
	@hgvspList = map {my $hgvsp = $_; $hgvsp =~ s/^\.$/\.:\./;$hgvsp} @hgvspList;
	my @proteinPosList = split(/;/, $varInfo{$varID}{"Protein_position"});
	my @exonList =  split(/;/, $varInfo{$varID}{"EXON"});
	my @intronList =  split(/;/, $varInfo{$varID}{"INTRON"});
	my @canonicalList =  split(/;/, $varInfo{$varID}{"CANONICAL"});
	my @biotypeList = split(/;/,$varInfo{$varID}{"BIOTYPE"});
	my @spliceAI = split(/;/,$varInfo{$varID}{"SpliceAI_cutoff"});
	my @spliceAIag = split(/;/,$varInfo{$varID}{"SpliceAI_pred_DS_AG"});
	my @spliceAIal = split(/;/,$varInfo{$varID}{"SpliceAI_pred_DS_AL"});
	my @spliceAIdg = split(/;/,$varInfo{$varID}{"SpliceAI_pred_DS_DG"});
	my @spliceAIdl = split(/;/,$varInfo{$varID}{"SpliceAI_pred_DS_DL"});
	my @FATHMM_pred = split(/;/,$varInfo{$varID}{"FATHMM_pred"});
	my @MutationAssessor_pred = split(/;/,$varInfo{$varID}{"MutationAssessor_pred"});
	my @PROVEAN_pred = split(/;/,$varInfo{$varID}{"PROVEAN_pred"});
	my @Polyphen2_HDIV_pred = split(/;/,$varInfo{$varID}{"Polyphen2_HDIV_pred"});
	my @Polyphen2_HVAR_pred = split(/;/,$varInfo{$varID}{"Polyphen2_HVAR_pred"});
	my @SIFT_pred = split(/;/,$varInfo{$varID}{"SIFT_pred"});
	my @LRT_pred = split(/;/,$varInfo{$varID}{"LRT_pred"});
	my @MetaLR_pred = split(/;/,$varInfo{$varID}{"MetaLR_pred"});
	my @MetaSVM_pred = split(/;/,$varInfo{$varID}{"MetaSVM_pred"});
	my @REVEL_score = split(/;/,$varInfo{$varID}{"REVEL_score"});
	my @AlphaMissense_pred = split(/;/,$varInfo{$varID}{"AlphaMissense_pred"});
	my %geneMember = map{$_=>""} @entrezIdList;

	my (%gene2Symbol,%gene2Transcript,%gene2Consequence,%gene2Impact,%gene2Biotype,%gene2Hgvsc,%gene2Hgvsp,%gene2ProteinPos,%gene2Exon,%gene2Intron,%gene2Canonical,%gene2spliceAI, %gene2spliceAIag,%gene2spliceAIal,%gene2spliceAIdg,%gene2spliceAIdl,%gene2FATHMM_pred, %gene2MutationAssessor_pred, %gene2PROVEAN_pred, %gene2Polyphen2_HDIV_pred, %gene2Polyphen2_HVAR_pred, %gene2SIFT_pred, %gene2LRT_pred, %gene2MetaLR_pred, %gene2MetaSVM_pred, %gene2AlphaMissense_pred, %gene2REVEL_score);
	my (@indexList1, @indexList2, @indexList3,@indexList4,@indexList5,@indexList6,@indexList7,@indexList8,@indexList9,@indexList10,@indexList11,@indexList12,@indexList13,@indexList14,@indexList15,@indexList16);
	foreach my $entrezId (keys(%geneMember)) {
		my @matchEntrezIndexList = grep{$entrezIdList[$_]~~$entrezId} 0..$#entrezIdList;
		@{$gene2Symbol{$entrezId}} = @geneList[@matchEntrezIndexList];
		@{$gene2Transcript{$entrezId}} = @transcriptList[@matchEntrezIndexList];
		@{$gene2Consequence{$entrezId}} = @consequenceList[@matchEntrezIndexList];
		@{$gene2Impact{$entrezId}} = @impactList[@matchEntrezIndexList];
		@{$gene2Biotype{$entrezId}} = @biotypeList[@matchEntrezIndexList];
		@{$gene2Hgvsc{$entrezId}} = @hgvscList[@matchEntrezIndexList];
		@{$gene2Hgvsp{$entrezId}} = @hgvspList[@matchEntrezIndexList];
		@{$gene2ProteinPos{$entrezId}} = @proteinPosList[@matchEntrezIndexList];
		@{$gene2Exon{$entrezId}} = @exonList[@matchEntrezIndexList];
		@{$gene2Intron{$entrezId}} = @intronList[@matchEntrezIndexList];
		@{$gene2Canonical{$entrezId}} = @canonicalList[@matchEntrezIndexList];
		@{$gene2spliceAI{$entrezId}} = @spliceAI[@matchEntrezIndexList];
		@{$gene2spliceAIag{$entrezId}} = @spliceAIag[@matchEntrezIndexList];
		@{$gene2spliceAIal{$entrezId}} = @spliceAIal[@matchEntrezIndexList];
		@{$gene2spliceAIdg{$entrezId}} = @spliceAIdg[@matchEntrezIndexList];
		@{$gene2spliceAIdl{$entrezId}} = @spliceAIdl[@matchEntrezIndexList];
		@{$gene2FATHMM_pred{$entrezId}} = @FATHMM_pred[@matchEntrezIndexList];
		@{$gene2MutationAssessor_pred{$entrezId}} = @MutationAssessor_pred[@matchEntrezIndexList];
		@{$gene2PROVEAN_pred{$entrezId}} = @PROVEAN_pred[@matchEntrezIndexList];
		@{$gene2Polyphen2_HDIV_pred{$entrezId}} = @Polyphen2_HDIV_pred[@matchEntrezIndexList];
		@{$gene2Polyphen2_HVAR_pred{$entrezId}} = @Polyphen2_HVAR_pred[@matchEntrezIndexList];
		@{$gene2SIFT_pred{$entrezId}} = @SIFT_pred[@matchEntrezIndexList];
		@{$gene2LRT_pred{$entrezId}} = @LRT_pred[@matchEntrezIndexList];
		@{$gene2MetaLR_pred{$entrezId}} = @MetaLR_pred[@matchEntrezIndexList];
		@{$gene2MetaSVM_pred{$entrezId}} = @MetaSVM_pred[@matchEntrezIndexList];
		@{$gene2AlphaMissense_pred{$entrezId}} = @AlphaMissense_pred[@matchEntrezIndexList];
		@{$gene2REVEL_score{$entrezId}} = @REVEL_score[@matchEntrezIndexList];

		my @outbody = ("upstream_gene_variant","downstream_gene_variant","intergenic_variant");
		my $isOutbody = all_outbody(\@{$gene2Consequence{$entrezId}}, \@outbody);
		if(! $isOutbody){
		#1. genebody内 且 Morbid基因 且 impact为HIGH
			if (exists($gene2morbid{$gene2Symbol{$entrezId}[0]}) && (grep(/HIGH/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList1,@matchEntrezIndexList);
			#2. genebody内 且 Morbid基因 且 impact为MODERATE
			}elsif (exists($gene2morbid{$gene2Symbol{$entrezId}[0]}) && (grep(/MODERATE/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList2,@matchEntrezIndexList);
			#3. genebody内 且 Morbid基因 且 impact为LOW
			}elsif (exists($gene2morbid{$gene2Symbol{$entrezId}[0]}) && (grep(/LOW/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList3,@matchEntrezIndexList);
			#4. genebody内 且 Morbid基因
			}elsif (exists($gene2morbid{$gene2Symbol{$entrezId}[0]})) {
				push(@indexList4,@matchEntrezIndexList);
			#5. genebody内 且 非Morbid基因 且 impact为HIGH
			}elsif ((grep(/HIGH/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList5,@matchEntrezIndexList);
			#6. genebody内 且 非Morbid基因 且 impact为MODERATE
			}elsif ((grep(/MODERATE/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList6,@matchEntrezIndexList);
			#7. genebody内 且 非Morbid基因 且 impact为LOW
			}elsif ((grep(/LOW/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList7,@matchEntrezIndexList);
			#8. genebody内 且 非Morbid基因
			}else{
				push(@indexList8,@matchEntrezIndexList);
			}
		}else{
			#9. genebody外 且 Morbid基因 且 impact为HIGH
			if (exists($gene2morbid{$gene2Symbol{$entrezId}[0]}) && (grep(/HIGH/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList9,@matchEntrezIndexList);
			#10. genebody外 且 Morbid基因 且 impact为MODERATE
			}elsif (exists($gene2morbid{$gene2Symbol{$entrezId}[0]}) && (grep(/MODERATE/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList10,@matchEntrezIndexList);
			#11. genebody外 且 Morbid基因 且 impact为LOW
			}elsif (exists($gene2morbid{$gene2Symbol{$entrezId}[0]}) && (grep(/LOW/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList11,@matchEntrezIndexList);
			#12. genebody外 且 Morbid基因
			}elsif (exists($gene2morbid{$gene2Symbol{$entrezId}[0]})) {
				push(@indexList12,@matchEntrezIndexList);
			#13. genebody外 且 非Morbid基因 且 impact为HIGH
			}elsif ((grep(/HIGH/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList13,@matchEntrezIndexList);
			#14. genebody外 且 非Morbid基因 且 impact为MODERATE
			}elsif ((grep(/MODERATE/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList14,@matchEntrezIndexList);
			#15. genebody外 且 非Morbid基因 且 impact为LOW
			}elsif ((grep(/LOW/,@{$gene2Impact{$entrezId}}))) {
				push(@indexList15,@matchEntrezIndexList);
			#16. genebody外 且 非Morbid基因
			}else{
				push(@indexList16,@matchEntrezIndexList);
			}
		}
	}
	my @outEntrezIndexList;
	my ($geneIndex, $transcriptOut,$allTrancriptsOut);
	if (@indexList1) {
		$geneIndex = $indexList1[0];
		@outEntrezIndexList = @indexList1;
	}elsif (@indexList2) {
		$geneIndex = $indexList2[0];
		@outEntrezIndexList = @indexList2;
	}elsif (@indexList3) {
		$geneIndex = $indexList3[0];
		@outEntrezIndexList = @indexList3;
	}elsif (@indexList4) {
		$geneIndex = $indexList4[0];
		@outEntrezIndexList = @indexList4;
	}elsif (@indexList5) {
		$geneIndex = $indexList5[0];
		@outEntrezIndexList = @indexList5;
	}elsif (@indexList6) {
		$geneIndex = $indexList6[0];
		@outEntrezIndexList = @indexList6;
	}elsif (@indexList7) {
		$geneIndex = $indexList7[0];
		@outEntrezIndexList = @indexList7;
	}elsif (@indexList8) {
		$geneIndex = $indexList8[0];
		@outEntrezIndexList = @indexList8;
	}elsif (@indexList9) {
		$geneIndex = $indexList9[0];
		@outEntrezIndexList = @indexList9;
	}elsif (@indexList10) {
		$geneIndex = $indexList10[0];
		@outEntrezIndexList = @indexList10;
	}elsif (@indexList11) {
		$geneIndex = $indexList11[0];
		@outEntrezIndexList = @indexList11;
	}elsif (@indexList12) {
		$geneIndex = $indexList12[0];
		@outEntrezIndexList = @indexList12;
	}elsif (@indexList13) {
		$geneIndex = $indexList13[0];
		@outEntrezIndexList = @indexList13;
	}elsif (@indexList14) {
		$geneIndex = $indexList14[0];
		@outEntrezIndexList = @indexList14;
	}elsif (@indexList15) {
		$geneIndex = $indexList15[0];
		@outEntrezIndexList = @indexList15;
	}elsif (@indexList16) {
		$geneIndex = $indexList16[0];
		@outEntrezIndexList = @indexList16;
	}
	#基因相关
	my ($entrezIdOut, $geneOut) = ($entrezIdList[$geneIndex], $geneList[$geneIndex]);
	my ($omimGeneIdOut, $omimPhenotypeIdOut, $inheritanceOut, $diseaseCnOut, $synopsisCnOut, $chpoOut) = 
		($geneInfo{$entrezIdOut}{"OMIM_GeneID"},$geneInfo{$entrezIdOut}{"OMIM_PhenotypeID"}, $geneInfo{$entrezIdOut}{"Inheritance"}, $geneInfo{$entrezIdOut}{"DiseaseCN"}, $geneInfo{$entrezIdOut}{"SynopsisCN"}, $geneInfo{$entrezIdOut}{"CHPO"});
	my ($varTypeInClinvarOut, $hgncIdOut, $hiOut, $dosageScoreOut, $pliOut, $clingenClassificationOut, $zScoreOut, $imprintOut, $digenicOut, $penetranceGeneReviewsOut,$penetranceHpoOut, $penetranceOmimOut, $geneAliasOut, $diseaseEnOut, $synopsisEnOut, $diseaseChpoOut) =
		($geneInfo{$entrezIdOut}{"ClinVarVarType"}, $geneInfo{$entrezIdOut}{"HGNC_ID"}, $geneInfo{$entrezIdOut}{"HI"}, $geneInfo{$entrezIdOut}{"dosageScore"}, $geneInfo{$entrezIdOut}{"PLI"}, $geneInfo{$entrezIdOut}{"ClingenClassification"}, $geneInfo{$entrezIdOut}{"ZScore"}, $geneInfo{$entrezIdOut}{"Imprint"}, $geneInfo{$entrezIdOut}{"Digenic"}, $geneInfo{$entrezIdOut}{"PenetranceGeneReviews"}, $geneInfo{$entrezIdOut}{"PenetranceHpo"}, $geneInfo{$entrezIdOut}{"PenetranceOMIM"}, $geneInfo{$entrezIdOut}{"GeneAlias"}, $geneInfo{$entrezIdOut}{"DiseaseEN"}, $geneInfo{$entrezIdOut}{"SynopsisEN"}, $geneInfo{$entrezIdOut}{"DiseaseCHPO"});
	#位点相关
	my ($tsIndex,$MANEindex,$PLUSindex,$CANONICALindex);
	if (exists $transcript{$entrezIdOut}) {
		$MANEindex = first {$gene2Transcript{$entrezIdOut}[$_]~~/$transcript{$entrezIdOut}\.\d+/} 0..$#{$gene2Transcript{$entrezIdOut}};
	}elsif (exists $transcriptPlus{$entrezIdOut}) {
		$PLUSindex = first {$gene2Transcript{$entrezIdOut}[$_]~~/$transcriptPlus{$entrezIdOut}\.\d+/} 0..$#{$gene2Transcript{$entrezIdOut}};
	}
	$CANONICALindex = first {$gene2Canonical{$entrezIdOut}[$_]~~/YES/} 0..$#{$gene2Canonical{$entrezIdOut}};
	if (defined $MANEindex){
		$tsIndex = $MANEindex;
		$transcriptOut = $gene2Transcript{$entrezIdOut}[$tsIndex];
	}elsif (defined $PLUSindex){
		$tsIndex = $PLUSindex;
		$transcriptOut = "(plus)".$gene2Transcript{$entrezIdOut}[$tsIndex];
	}elsif (defined $CANONICALindex){
		$tsIndex = $CANONICALindex;
		$transcriptOut = "(canonical)".$gene2Transcript{$entrezIdOut}[$tsIndex];
	}else{
		$tsIndex = 0;
		$transcriptOut = "(vep)".$gene2Transcript{$entrezIdOut}[$tsIndex];
	}
	my ($hgvscOut,$hgvspOut) = ((split(/:/,$gene2Hgvsc{$entrezIdOut}[$tsIndex]))[1],(split(/:/,$gene2Hgvsp{$entrezIdOut}[$tsIndex]))[1]);
	my $varPosOut = $locInfo{$varID}{$entrezIdOut}{$gene2Transcript{$entrezIdOut}[$tsIndex]};
	my ($exonIntronOut, $exonCountOut) = (".", "."); 
	if ($gene2Exon{$entrezIdOut}[$tsIndex] =~ /(\d+)\/(\d+)/) {
		($exonIntronOut, $exonCountOut) = ("exon".$1, $2);
	}elsif ($gene2Intron{$entrezIdOut}[$tsIndex] =~ /(\d+)\/(\d+)/) {
		($exonIntronOut, $exonCountOut) = ("intron".$1, $2+1);
	}
	my ($consequenceOut,$impactOut,$proteinPositionOut) = ($gene2Consequence{$entrezIdOut}[$tsIndex],$gene2Impact{$entrezIdOut}[$tsIndex],$gene2ProteinPos{$entrezIdOut}[$tsIndex]);
	my ($FATHMM_predOut, $MutationAssessor_predOut, $PROVEAN_predOut, $Polyphen2_HDIV_predOut, $Polyphen2_HVAR_predOut, $SIFT_predOut, $LRT_predOut, $MetaLR_predOut, $MetaSVM_predOut, $AlphaMissense_predOut, $REVEL_scoreOut) = ($gene2FATHMM_pred{$entrezIdOut}[$tsIndex], $gene2MutationAssessor_pred{$entrezIdOut}[$tsIndex], $gene2PROVEAN_pred{$entrezIdOut}[$tsIndex], $gene2Polyphen2_HDIV_pred{$entrezIdOut}[$tsIndex], $gene2Polyphen2_HVAR_pred{$entrezIdOut}[$tsIndex], $gene2SIFT_pred{$entrezIdOut}[$tsIndex], $gene2LRT_pred{$entrezIdOut}[$tsIndex], $gene2MetaLR_pred{$entrezIdOut}[$tsIndex], $gene2MetaSVM_pred{$entrezIdOut}[$tsIndex], $gene2AlphaMissense_pred{$entrezIdOut}[$tsIndex], $gene2REVEL_score{$entrezIdOut}[$tsIndex]);
	$FATHMM_predOut = ($FATHMM_predOut =~ /\w/)? $FATHMM_predOut =~ s/.*(\w).*/$1/r : ".";
	$MutationAssessor_predOut = ($MutationAssessor_predOut =~ /\w/)? $MutationAssessor_predOut =~ s/.*(\w).*/$1/r : ".";
	$AlphaMissense_predOut = ($AlphaMissense_predOut =~ /\w/)? $AlphaMissense_predOut =~ s/.*(\w).*/$1/r : ".";
	$PROVEAN_predOut = ($PROVEAN_predOut =~ /\w/)? $PROVEAN_predOut =~ s/.*(\w).*/$1/r : ".";
	$Polyphen2_HDIV_predOut = ($Polyphen2_HDIV_predOut =~ /\w/)? $Polyphen2_HDIV_predOut =~ s/.*(\w).*/$1/r : ".";
	$Polyphen2_HVAR_predOut = ($Polyphen2_HVAR_predOut =~ /\w/)? $Polyphen2_HVAR_predOut =~ s/.*(\w).*/$1/r : ".";
	$SIFT_predOut = ($SIFT_predOut =~ /\w/)? $SIFT_predOut =~ s/.*(\w).*/$1/r : ".";
	$LRT_predOut = ($LRT_predOut =~ /\w/)? $LRT_predOut =~ s/.*(\w).*/$1/r : ".";
	$MetaLR_predOut = ($MetaLR_predOut =~ /\w/)? $MetaLR_predOut =~ s/.*(\w).*/$1/r : ".";
	$MetaSVM_predOut = ($MetaSVM_predOut =~ /\w/)? $MetaSVM_predOut =~ s/.*(\w).*/$1/r : ".";
	$REVEL_scoreOut = ($REVEL_scoreOut =~ /\d/)? $REVEL_scoreOut =~ s/.*(0\.\d+).*/$1/r : ".";
	for (my $i=0; $i<=$#outEntrezIndexList; $i++) {
		$hgvscList[$outEntrezIndexList[$i]] =~ s/^\.$/\.:\./;
		$hgvspList[$outEntrezIndexList[$i]] =~ s/^\.$/\.:\./;
		my $hgvsc = (split(/:/,$hgvscList[$outEntrezIndexList[$i]]))[1];
		my $hgvsp = (split(/:/,$hgvspList[$outEntrezIndexList[$i]]))[1];
		my $impact = $impactList[$outEntrezIndexList[$i]];
		my $consequence = $consequenceList[$outEntrezIndexList[$i]];
		$allTrancriptsOut .= join(":",($transcriptList[$outEntrezIndexList[$i]],$hgvsc, $hgvsp, $impact, $consequence)).";";
	}
	if (defined $allTrancriptsOut) {
		$allTrancriptsOut =~ s/;$//;
	}else {
		$allTrancriptsOut = ".";
	}
	my @notmatchEntrezIndexList = grep{$entrezIdList[$_]!~$entrezIdOut} 0..$#entrezIdList;
	my $overlapGeneOut;
	if (@notmatchEntrezIndexList) {
		for (my $j=0; $j<=$#notmatchEntrezIndexList; $j++) {
			my $notMatchEntrezID = $entrezIdList[$notmatchEntrezIndexList[$j]];
			if (not exists($geneInfo{$notMatchEntrezID}{"DiseaseCN"})){
				$overlapGeneOut .= join(":", ($notMatchEntrezID, $geneList[$notmatchEntrezIndexList[$j]], ".", $transcriptList[$notmatchEntrezIndexList[$j]], $hgvscList[$notmatchEntrezIndexList[$j]], $hgvspList[$notmatchEntrezIndexList[$j]], $impactList[$notmatchEntrezIndexList[$j]], $consequenceList[$notmatchEntrezIndexList[$j]])).";";
			}else{
				$overlapGeneOut .= join(":", ($notMatchEntrezID, $geneList[$notmatchEntrezIndexList[$j]], $geneInfo{$notMatchEntrezID}{"DiseaseCN"}, $transcriptList[$notmatchEntrezIndexList[$j]], $hgvscList[$notmatchEntrezIndexList[$j]], $hgvspList[$notmatchEntrezIndexList[$j]], $impactList[$notmatchEntrezIndexList[$j]], $consequenceList[$notmatchEntrezIndexList[$j]])).";";
			}
		}
	}
	if (not defined($overlapGeneOut)){
		$overlapGeneOut = ".";
	}
	if (exists $geneInfo{$entrezIdOut}{"Gene"}) {
		$geneOut = $geneInfo{$entrezIdOut}{"Gene"};
	}

	## 判断位点是否在白名单中，zr add 20230407
	$tagWhite='F';
	if ($varID ~~ @whiteInfo ) {
		$tagWhite = 'T';
	}
	else {
		my @alltranscriptlist=split(/;/, $allTrancriptsOut);
		foreach my $onetranscript (@alltranscriptlist) {
			my @tranlist=split(/:/, $onetranscript);
			my $NM=$tranlist[0];# @变成$
			$NM =~ s/\.\d+//;
			my $hgvc1=$tranlist[1];# @变成$
			my $hgvsp1=$tranlist[2];# @变成$
			foreach my $whitesite  (@whiteInfo) {
				my @whitearray = split(/:/, $whitesite);
				my $nm = $whitearray[0];
				$nm =~ s/\.\d+//;
				my $hgvscW = $whitearray[1];
				if ($nm eq $NM && $hgvscW eq $hgvc1) {
					$tagWhite = 'T';
					last;
				}
			}
		}

	}
	#-----------------------家系所有成员的Zygosity,Format,VAF列--------------------------------------------------
	my ($probandGT,$probandRefReads,$probandAltReads,$probandDP,$probandGQ,$coupleMemberFormatOut,$coupleGT,$coupleRefReads,$coupleAltReads,$coupleDP,$coupleGQ);
	if (defined $familyId) {
		if (grep(/$sampleSort{$familyId}[0]/, @sampleList)) {
			$probandFormatOut = $varInfo{$varID}{${$sampleSort{$familyId}}[0]};
			($probandGT,$probandRefReads,$probandAltReads,$probandDP,$probandGQ) = $probandFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
			if ($probandDP>0 && $probandAltReads/$probandDP>=0.005){
				$probandVafOut = sprintf("%.2f",$probandAltReads/$probandDP);
			}else{
				$probandVafOut = 0;
			}
			my $probandFormatTmp = ($hashGender{${$sampleSort{$familyId}}[0]} =~ /2|0/)? "Hom" : (($varID =~ /X|Y/)? "Hemi" : "Hom");
			$probandZygosityOut = ($probandFormatOut =~ /^0\/1/ or $probandFormatOut =~ /^1\/0/)? "Het" : (($probandFormatOut=~/^1\/1/)? $probandFormatTmp : ".");
		} 
		#当送检模式为：先证者+配偶(有或无)+子女+其他(有或无)时，$dadFormatOut对应的其实是配偶的信息
		if ((grep(/${$sampleSort{$familyId}}[1]/, @sampleList)) && ${$sampleSort{$familyId}}[1] =~ /\d/) {
			$dadFormatOut = $varInfo{$varID}{${$sampleSort{$familyId}}[1]};
			my ($GT, $refReads, $altReads, $DP, $GQ) = $dadFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
			if ($DP>0 && $altReads/$DP>=0.005){
				$dadVafOut = sprintf("%.2f",$altReads/$DP);
			}else{
				$dadVafOut = 0;
			}
			my $dadZygosityTmp = ($hashGender{${$sampleSort{$familyId}}[1]} =~ /2|0/)? "Hom" : (($varID =~ /X|Y/)? "Hemi" : "Hom");
			$dadZygosityOut = ($dadFormatOut =~ /^0\/1/ or $dadFormatOut =~ /^1\/0/)? "Het" : (($dadFormatOut=~/^1\/1/)? "$dadZygosityTmp" : ".");
			if (exists($couple{${$sampleSort{$familyId}}[1]})) {
				($coupleMemberFormatOut,$coupleVAF) = ($dadFormatOut,$dadVafOut);
				($coupleGT,$coupleRefReads,$coupleAltReads,$coupleDP,$coupleGQ) = $coupleMemberFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
			}
		}else {
			($dadZygosityOut,$dadFormatOut,$dadVafOut) = (".",".",".");
		}
		#当送检模式为：先证者+配偶(有或无)+子女+其他(有或无)时，$momFormatOut对应的其实是子女的信息
		if ((grep(/${$sampleSort{$familyId}}[2]/, @sampleList)) && ${$sampleSort{$familyId}}[2] =~ /\d/) {
			$momFormatOut = $varInfo{$varID}{${$sampleSort{$familyId}}[2]};
			my ($GT, $refReads, $altReads, $DP, $GQ) = $momFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
			if ($DP>0 && $altReads/$DP>=0.005){
				$momVafOut = sprintf("%.2f",$altReads/$DP);
			}else{
				$momVafOut = 0;
			}
			my $momZygosityTmp = ($hashGender{${$sampleSort{$familyId}}[2]} =~ /2|0/)? "Hom" : (($varID =~ /X|Y/)? "Hemi" : "Hom");
			$momZygosityOut = ($momFormatOut =~ /^0\/1/ or $momFormatOut =~ /^1\/0/)? "Het" : (($momFormatOut=~/^1\/1/)? "Hom" : ".");
		}else {
			($momZygosityOut,$momFormatOut,$momVafOut) = (".",".",".");
		}
		if ((grep(/${$sampleSort{$familyId}}[3]/, @sampleList)) && ${$sampleSort{$familyId}}[3] =~ /\d/) {
			$otherFormatOut = $varInfo{$varID}{${$sampleSort{$familyId}}[3]};
			my ($GT, $refReads, $altReads, $DP, $GQ) = $otherFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
			if ($DP>0 && $altReads/$DP>=0.005){
				$otherVafOut = sprintf("%.2f",$altReads/$DP);
			}else{
				$otherVafOut = 0;
			}			
			my $otherFormatTmp = ($hashGender{${$sampleSort{$familyId}}[3]} =~ /2|0/)? "Hom" : (($varID =~ /X|Y/)? "Hemi" : "Hom");
			$otherZygosityOut = ($otherFormatOut =~ /^0\/1/ or $otherFormatOut =~ /^1\/0/)? "Het" : (($otherFormatOut=~/^1\/1/)? $otherFormatTmp : ".");
		}else {
			($otherZygosityOut,$otherFormatOut,$otherVafOut) = (".",".",".");
		}
		if (defined $CS and $CS eq 'CS' && $varID =~ /X/ && $probandZygosityOut eq "Hemi" && $momZygosityOut ne "." && $dadZygosityOut ne ".") {
			$probandZygosityOut = "Hom";
		} # Carrier新加的
	}elsif (defined $sampleID) {
		($probandFormatOut, $momFormatOut, $dadFormatOut, $otherFormatOut) = ($varInfo{$varID}{$sampleID},".",".",".");
		($probandGT,$probandRefReads,$probandAltReads,$probandDP,$probandGQ) = $probandFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
		if ($probandDP>0 && $probandAltReads/$probandDP>=0.005){
			$probandVafOut = sprintf("%.2f",$probandAltReads/$probandDP);
		}else{
			$probandVafOut = 0;
		}
		my $inputGender = (defined $gender)? $gender : $hashGender{$sampleID};
		my $probandFormatTmp = ($inputGender =~ /F|ND|2|0/)? "Hom" : (($varID =~ /X|Y/)? "Hemi" : "Hom");
		$probandZygosityOut = ($probandFormatOut =~ /^0\/1/ or $probandFormatOut =~ /^1\/0/)? "Het" : (($probandFormatOut=~/^1\/1/)? $probandFormatTmp : ".");
	}
	#-----------------------Done 家系所有成员的杂合性和FORMAT列--------------------------------------------------

	#-------------------------遗传来源标记----------------------------------------------------------------------
	unless (exists($varInfo{$varID}{"Denovo"})){
		($varInfo{$varID}{"Denovo"},$varInfo{$varID}{"LenientDenovo"},$varInfo{$varID}{"Hom_P_M"},$varInfo{$varID}{"Hom_P"}, $varInfo{$varID}{"Hom_M"},$varInfo{$varID}{"Hemi"},$varInfo{$varID}{"SegregatingDominant"},$varInfo{$varID}{"SegregatingRecessive"},$varInfo{$varID}{"CompoundHet"},$varInfo{$varID}{"het_P"},$varInfo{$varID}{"het_M"})= ('.','.','.','.','.','.','.','.','.','.','.');
	}
	my @denovoSampleList = split(/,/, $varInfo{$varID}{"Denovo"});
	my @lenientDenovoSampleList = split(/,/, $varInfo{$varID}{"LenientDenovo"});
	my @homSampleList = split(/,/, $varInfo{$varID}{"Hom_P_M"});
	my @homPatSampleList = split(/,/, $varInfo{$varID}{"Hom_P"});
	my @homMatSampleList = split(/,/, $varInfo{$varID}{"Hom_M"});
	my @hemiSampleList = split(/,/, $varInfo{$varID}{"Hemi"});
	my @segregatingDominantSampleList = split(/,/, $varInfo{$varID}{"SegregatingDominant"});
	my @segregatingRecessiveSampleList = split(/,/, $varInfo{$varID}{"SegregatingRecessive"});
	my @slivarComphetList = split(/,/, $varInfo{$varID}{"CompoundHet"});
	my @hetPatSampleList = split(/,/, $varInfo{$varID}{"het_P"});
	my @hetMatSampleList = split(/,/, $varInfo{$varID}{"het_M"});
	foreach my $sample (@denovoSampleList) {
		if (grep(/$sample/, @sampleList)) {$denovoOut .= $sample.",";}
	}
	foreach my $sample (@lenientDenovoSampleList) {
		if (grep(/$sample/, @sampleList)) {$lenientDenovoOut .= $sample.",";}
	}
	foreach my $sample (@homSampleList) {
		if (grep(/$sample/, @sampleList)) {$homOut .= $sample.",";}
	}
	foreach my $sample (@homPatSampleList) {
		if (grep(/$sample/, @sampleList)) {$homPatOut .= $sample.",";}
	}
	foreach my $sample (@homMatSampleList) {
		if (grep(/$sample/, @sampleList)) {$homMatOut .= $sample.",";}
	}
	foreach my $sample (@hemiSampleList) {
		if (grep(/$sample/, @sampleList)) {$hemiOut .= $sample.",";}
	}
	foreach my $sample (@segregatingDominantSampleList) {
		if (grep(/$sample/, @sampleList)) {$segregatingDominantOut .= $sample.",";}
	}
	foreach my $sample (@segregatingRecessiveSampleList) {
		if (grep(/$sample/, @sampleList)) {$segregatingRecessiveOut .= $sample.",";}
	}
	foreach my $slivarComphetItem (@slivarComphetList) {
		my $comphetSample = (split(/\//, $slivarComphetItem))[0];
		if (grep(/$comphetSample/, @sampleList)) {$slivarComphetOut .= $slivarComphetItem.",";}
	}
	foreach my $sample (@hetPatSampleList) {
		if (grep(/$sample/, @sampleList)) {$hetPatOut .= $sample.",";}
	}
	foreach my $sample (@hetMatSampleList) {
		if (grep(/$sample/, @sampleList)) {$hetMatOut .= $sample.",";}
	}
	
	$denovoOut = (defined $denovoOut) ? $denovoOut=~s/,$//r : ".";     #错误的写法：$denovoOut = (defined $denovoOut) ? chop $denovoOut : ".";，返回的$denovoOut是被chop掉的","，而不是样本编号
	$lenientDenovoOut = (defined $lenientDenovoOut) ? $lenientDenovoOut=~s/,$//r : ".";
	$homOut = (defined $homOut) ? $homOut=~s/,$//r : ".";
	$homPatOut = (defined $homPatOut) ? $homPatOut=~s/,$//r : ".";
	$homMatOut = (defined $homMatOut) ? $homMatOut=~s/,$//r : ".";
	$hemiOut = (defined $hemiOut) ? $hemiOut=~s/,$//r : ".";
	$slivarComphetOut = (defined $slivarComphetOut) ? $slivarComphetOut=~s/,$//r : ".";
	$hetPatOut = (defined $hetPatOut) ? $hetPatOut=~s/,$//r : ".";
	$hetMatOut = (defined $hetMatOut) ? $hetMatOut=~s/,$//r : ".";
	$segregatingDominantOut = (defined $segregatingDominantOut && $segregatingDominantOut =~ /,\w/) ? $segregatingDominantOut=~s/,$//r : ".";    #家系共分离需要至少2个患者
	$segregatingRecessiveOut = (defined $segregatingRecessiveOut && $segregatingRecessiveOut =~ /,\w/) ? $segregatingRecessiveOut=~s/,$//r : "."; #家系共分离需要至少2个患者
	
	if ($segregatingDominantOut =~ /\d/) {$tagGenetic = "SD;";}
	elsif ($segregatingRecessiveOut =~ /\d/ && $sampleCount >3) {$tagGenetic = "SR;";}
	if ($denovoOut =~ /\d/) {$tagGenetic .= "Denovo;";}
	elsif ($lenientDenovoOut =~ /\d/) {$tagGenetic .= "Lenient_Denovo;";}
	if ($homOut =~ /\d/) {$tagGenetic .= "Hom:P/M;";}
	elsif ($homPatOut =~ /\d/) {$tagGenetic .= "Hom:P/-;";}
	elsif ($homMatOut =~ /\d/) {$tagGenetic .= "Hom:-/M;";}
	elsif ($hemiOut =~ /\d/) {$tagGenetic .= "Hemi:M;";}
	elsif (defined $CS and $CS eq 'CS' && $varID =~ /X/ && $probandZygosityOut eq "Hemi" && $momZygosityOut eq "Het" && $momFormatOut =~ /^1\/0/ && $dadZygosityOut eq ".") {
		my ($GTmon, $refReadsmon, $altReadsmon, $DPmon, $GQmon) = $momFormatOut =~ /(.*?):(\d+),(\d+):(\d+):(\d+|\.)/;
		if($DPmon >= 10 && $GQmon >= 20 && ($altReadsmon/$DPmon) >= 0.2 && ($altReadsmon/$DPmon) <= 0.8){
			$tagGenetic .= "Hemi:M;";
		}
	} # Carrier新加的

	if ($slivarComphetOut =~ /\d/ && $hetPatOut =~ /\d/) {$tagGenetic .= "CH:P;";}
	elsif (defined $CS and $CS eq 'CS' && $hetPatOut =~ /\d/) {$tagGenetic .= "Het:P;";} # Carrier新加的
	if ($slivarComphetOut =~ /\d/ && $hetMatOut =~ /\d/) {$tagGenetic .= "CH:M;";}
	elsif (defined $CS and $CS eq 'CS' && $hetMatOut =~ /\d/) {$tagGenetic .= "Het:M;";} # Carrier新加的
	if(defined $CS and $CS eq 'CS'){
		if($hetPatOut =~ /\d/){ # Carrier新加的
			push(@{$geneCH{$geneOut}},"Het:P");
		}elsif($hetMatOut =~ /\d/){ # Carrier新加的
			push(@{$geneCH{$geneOut}},"Het:M");
		}elsif($homOut =~ /\d/){ # Carrier新加的
			push(@{$geneCH{$geneOut}},"Hom:P/M");
		}
	}

	if (defined $tagGenetic){
		$tagGenetic =~ s/;$//;
	}else {
		$tagGenetic = ".";
	}
    #---------------------Done 遗传来源标记---------------------------------------------------------

	#-------------------------Qual标记-------------------------------------------
	if (defined $probandGT and ($probandGT eq "0/1" or $probandGT eq "1/0")){
		if ($probandDP>=5) {
			if ($probandVafOut >=0.3) {$tagQual = "High";}
			elsif ($probandVafOut >=0.2 && $probandVafOut <0.3) {$tagQual = "Moderate";}
			elsif ($probandVafOut >=0.1 && $probandVafOut <0.2) {$tagQual = "Low";}
			else {$tagQual = "False";}
		}else {$tagQual = "LowDepth";}
	}elsif (defined $probandGT and $probandGT eq "1/1"){
		if ($probandDP>20) {
			if ($probandRefReads <=3) {$tagQual = "High";}
			elsif ($probandRefReads <=7) {$tagQual = "Moderate";}
			else{$tagQual = "Low";}
		}elsif ($probandDP>=5) {
			if ($probandRefReads <=1) {$tagQual = "High";}
			elsif ($probandRefReads <=3) {$tagQual = "Moderate";}
			else {$tagQual = "Low";}
		}else {$tagQual = "LowDepth";}
	}elsif (defined $coupleGT && ($coupleGT eq "0/1" or $coupleGT eq "1/0")) {
		if ($coupleDP >=5) {
			if ($coupleVAF >=0.3) {$tagQual = "High";}
			elsif ($coupleVAF >=0.2 && $coupleVAF <0.3) {$tagQual = "Moderate";}
			elsif ($coupleVAF >=0.1 && $coupleVAF <0.2) {$tagQual = "Low";}
			else {$tagQual = "False";}
		}else {$tagQual = "LowDepth";}
	}elsif (defined $coupleGT && $coupleGT eq "1/1") {
		if ($coupleDP >20) {
			if ($coupleRefReads <=3) {$tagQual = "High";}
			elsif ($coupleRefReads <=7) {$tagQual = "Moderate";}
			else {$tagQual = "Low";}
		}elsif ($coupleDP >=5) {
			if ($coupleRefReads <=1)  {$tagQual = "High";}
			elsif ($coupleRefReads <=3) {$tagQual = "Moderate";}
			else {$tagQual = "Low";}
		}else {$tagQual = "LowDepth";}
	}
	#-------------------------Done Qual标记-------------------------------------------

	#-------------------------致病性标记----------------------------------------------
	#clinvar-3/4星,本地变异分类
	if ($varInfo{$varID}{"clinvar_CLNREVSTAT"} =~ /practice_guideline|reviewed_by_expert_panel/) {
		if ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Pathogenic/){
			if ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /致病变异/){$tagPathogenicity = "P-V";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /临床意义未明变异/){$tagPathogenicity = "P-P";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /良性变异/){$tagPathogenicity = "Conflict";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} eq "."){$tagPathogenicity = "P-S";}
		}elsif ( $varInfo{$varID}{"clinvar_CLNSIG"} =~/Likely_pathogenic/){
			if ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /^致病变异/){$tagPathogenicity = "P-V";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /疑似致病变异/){$tagPathogenicity = "LP-V";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /临床意义未明变异/){$tagPathogenicity = "LP-P";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /良性变异/){$tagPathogenicity = "Conflict";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} eq "."){$tagPathogenicity = "LP-S";}
		}elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~ /Uncertain_significance/){
			if ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /^致病变异/){$tagPathogenicity = "P-M";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /疑似致病变异/){$tagPathogenicity = "LP-M";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /临床意义未明变异/){$tagPathogenicity = "VUS-V";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /良性变异/){$tagPathogenicity = "Conflict";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} eq "."){$tagPathogenicity = "VUS-S";}
		}elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~ /benign/i){
			if ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /致病变异/){$tagPathogenicity = "Conflict";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /临床意义未明变异|\./){$tagPathogenicity = "B-S";}
			elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /良性变异/){$tagPathogenicity = "B-V";}
		}else {$tagPathogenicity = ".";}
	}elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /^致病变异/) {$tagPathogenicity = "P-S";}
	elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /疑似致病变异/) {$tagPathogenicity = "LP-S";}
	elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /临床意义未明变异/) {$tagPathogenicity = "VUS-V";}
	elsif ($varInfo{$varID}{"local_path_Pathogenicity"} =~ /良性变异/) {$tagPathogenicity = "B-S";}
	elsif ($varInfo{$varID}{"clinvar_CLNREVSTAT"} eq "criteria_provided&_multiple_submitters&_no_conflicts") {
		if ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Pathogenic/) {$tagPathogenicity = "P-M";}
		elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Likely_pathogenic/) {$tagPathogenicity = "LP-M";}
		elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Uncertain_significance/) {$tagPathogenicity = "VUS-M";}
		elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~ /benign/i && $varInfo{$varID}{"clinvar_CLNSIG"} !~ /pathogenic/i) {$tagPathogenicity = "B-M";}
		else {$tagPathogenicity = ".";}
	}elsif ($varInfo{$varID}{"HGMD_Class"}=~/^DM$/ && $varInfo{$varID}{"HGMD_Rank_Score"} =~ /\d/ && $varInfo{$varID}{"HGMD_Rank_Score"}>=0.9){$tagPathogenicity = "P-P";}
	elsif ($varInfo{$varID}{"clinvar_CLNREVSTAT"} =~ /criteria_provided&_single_submitter|no_assertion_criteria_provided/){
		if ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Pathogenic/) {$tagPathogenicity = "P-P";}
		elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Likely_pathogenic/) {$tagPathogenicity = "LP-P";}
		elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~/Uncertain_significance/) {$tagPathogenicity = "VUS-P";}
		elsif ($varInfo{$varID}{"clinvar_CLNSIG"} =~ /benign/i) {$tagPathogenicity = "B-P";}
		else {$tagPathogenicity = ".";}
	}
	elsif ($varInfo{$varID}{"clinvar_CLNREVSTAT"} =~/conflicting/) {$tagPathogenicity = "Conflict";}
	elsif ($varInfo{$varID}{"HGMD_Class"}=~/^DM$/ && $varInfo{$varID}{"HGMD_Rank_Score"} =~ /\d/ && $varInfo{$varID}{"HGMD_Rank_Score"}<0.9){$tagPathogenicity = "LP-P";}
	else {$tagPathogenicity = ".";}
	#-------------------------Done 致病性标记-------------------------------------------------------

	#-------------------------MAF 标记--------------------------------------------------------------
	if ($varInfo{$varID}{"LocalMAF_AF"} =~ /&/){
		$varInfo{$varID}{"LocalMAF_AF"} = (split(/&/,$varInfo{$varID}{"LocalMAF_AF"}))[0] + (split(/&/,$varInfo{$varID}{"LocalMAF_AF"}))[1];
		$varInfo{$varID}{"LocalMAF_AN"} = max(split(/&/,$varInfo{$varID}{"LocalMAF_AN"}));
		$varInfo{$varID}{"LocalMAF_AC"} = (split(/&/,$varInfo{$varID}{"LocalMAF_AC"}))[0] + (split(/&/,$varInfo{$varID}{"LocalMAF_AC"}))[1];
	}
	my @arrAcList = ($varInfo{$varID}{"GnomADAc"},$varInfo{$varID}{"GnomADEasAc"});
	my @arrAnList = ($varInfo{$varID}{"GnomADAn"},$varInfo{$varID}{"GnomADEasAn"});
	my @arrAfList = ($varInfo{$varID}{"GnomADAf"},$varInfo{$varID}{"GnomADEasAf"});
	my @arrAfIndexNum = grep{$arrAnList[$_] =~ /\d/} 0..$#arrAnList; #判断AN中是否包含数字
	my @arrAfIndexList = grep{$arrAnList[$_]>=2000} @arrAfIndexNum;#判断AN是否>=2000并取出对应的AF列
	my @arrAfIndex0List = grep{$arrAnList[$_]>=0} @arrAfIndexNum;#判断AN是否>=0并取出对应的AF列
	$varInfo{$varID}{"GnomADGenomes_controls_nhomalt"} =~ s/\./0/;
	$varInfo{$varID}{"GnomADExomes_controls_nhomalt"} =~ s/\./0/;
	$homAltCountOut = $varInfo{$varID}{"GnomADGenomes_controls_nhomalt"}+$varInfo{$varID}{"GnomADExomes_controls_nhomalt"};
	#当gnomAD total AN 或 gnomAD eas total AN >=2000
	if (@arrAfIndexList) {
		$maxMafOut = max(@arrAfList[@arrAfIndexList]);
		my @maxAfIndex = grep{$arrAfList[$_] eq $maxMafOut} 0..$#arrAfList;
		$maxAcAnOut = $arrAcList[$maxAfIndex[0]]."/".$arrAnList[$maxAfIndex[0]];
		$varInfo{$varID}{"GnomADGenomes_controls_nhomalt"} =~ s/^\.$|^$/0/;
		$varInfo{$varID}{"GnomADExomes_controls_nhomalt"} =~ s/^\.$|^$/0/;
		if ($maxMafOut >0.01) {$tagMaf = "High";}
		elsif ($maxMafOut >0.001) {$tagMaf = "Moderate";}
		elsif ($maxMafOut >0) {
			if ($varInfo{$varID}{"LocalMAF_AF"} =~ /\d/ && $varInfo{$varID}{"LocalMAF_AF"}>=0.05){$tagMaf = "Moderate";}
			else{$tagMaf = "Low";}
		}
		elsif ($arrAcList[$maxAfIndex[0]] == 0) {
			if ($varInfo{$varID}{"LocalMAF_AF"} eq '.'){$tagMaf = "0";} #最大值等于0，并且本地频率.时，加0.03分
			elsif($varInfo{$varID}{"LocalMAF_AF"}==0){$tagMaf = "0";} #最大值等于0，并且本地频率等于0，加0.03分
			elsif ($varInfo{$varID}{"LocalMAF_AN"} >=2000 && $varInfo{$varID}{"LocalMAF_AF"}>=0.05 ){$tagMaf = "Moderate";} #最大值等于0，但本地AN>=2000并且AF>=0.05，减0.2分
			else{$tagMaf = "Low";} #最大值等于0，并且本地不满足以上条件，不加不减分
		}
	}
	#gnomAD total AN 和gnomAD eas total AN 都等于.
	unless (@arrAfIndexNum) {
		if ($varInfo{$varID}{"LocalMAF_AF"} eq '.'){$tagMaf = "0";}
		elsif($varInfo{$varID}{"LocalMAF_AF"}==0){$tagMaf = "0";} #gnomAD 的两个AN都等于.并且本地频率等于0或者.时，加0.03分
		elsif ($varInfo{$varID}{"LocalMAF_AN"} >=2000 && $varInfo{$varID}{"LocalMAF_AF"}>=0.05 ){$tagMaf = "Moderate";} #gnomAD 的两个AN都等于.但本地AN>=2000且AF>=0.05，减0.2分
		else{$tagMaf = "Low";} #gnomAD 的两个AN都等于.并且本地不满足以上条件，不加不减分
		}
	#当gnomAD total AN 和 gnomAD eas total AN 都是数字但都<2000
	unless (defined $tagMaf) {
		$maxMafOut = max(@arrAfList[@arrAfIndex0List]);
		my @maxAfIndex = grep{$arrAfList[$_] eq $maxMafOut} 0..$#arrAfList;
		$maxAcAnOut = $arrAcList[$maxAfIndex[0]]."/".$arrAnList[$maxAfIndex[0]];
		if ($arrAcList[$maxAfIndex[0]] == 0){
			if ($varInfo{$varID}{"LocalMAF_AF"} eq '.'){$tagMaf = "0";}
			elsif ($varInfo{$varID}{"LocalMAF_AF"}==0 ) {$tagMaf = "0";}
			elsif ($varInfo{$varID}{"LocalMAF_AN"} >=2000 && $varInfo{$varID}{"LocalMAF_AF"}>=0.05 ){$tagMaf = "Moderate";}
			else{$tagMaf = "Low";}
		}
		else{
			$tagMaf = "ND";
		}
	}
	#-------------------------Done MAF 标记--------------------------------------------------

	#-------------------------PP3/BP4 标签---------------------------------------------------
	my $adaScore = $varInfo{$varID}{"ada_score"} =~ s/^\.$/0/r;
	my $rfScore = $varInfo{$varID}{"rf_score"} =~ s/^\.$/0/r;
	$dbscSNVscoreOut = max($adaScore,$rfScore);
	$dbscSNVscoreOut = sprintf("%.2f",$dbscSNVscoreOut);
	my $spliceAiAgOut = $gene2spliceAIag{$entrezIdOut}[$tsIndex];
	my $spliceAiAlOut = $gene2spliceAIal{$entrezIdOut}[$tsIndex];
	my $spliceAiDgOut = $gene2spliceAIdg{$entrezIdOut}[$tsIndex];
	my $spliceAiDlOut = $gene2spliceAIdl{$entrezIdOut}[$tsIndex];
	$spliceAiAgOut =~ s/^\.$/0/;
	$spliceAiAlOut =~ s/^\.$/0/;
	$spliceAiDgOut =~ s/^\.$/0/;
	$spliceAiDlOut =~ s/^\.$/0/;
	$spliceAIscoreOut = join("|",($spliceAiAgOut, $spliceAiAlOut, $spliceAiDgOut, $spliceAiDlOut));
	$maxSpliceAIscore = max($spliceAiAgOut, $spliceAiAlOut, $spliceAiDgOut, $spliceAiDlOut);
	$dbscSNVOut = ($dbscSNVscoreOut>=0.6) ? "Y" : "N";
	$spliceAIout = $gene2spliceAI{$entrezIdOut}[$tsIndex];
	$spliceAIout =~ s/PASS/Y/;
	$spliceAIout =~ s/FAIL/N/;
	my @inSilicoPredList = ($SIFT_predOut,$Polyphen2_HDIV_predOut,$Polyphen2_HVAR_predOut,$LRT_predOut,$AlphaMissense_predOut,$MutationAssessor_predOut,$FATHMM_predOut,$PROVEAN_predOut,$MetaSVM_predOut,$MetaLR_predOut,$REVEL_scoreOut);
	if ($consequenceOut !~ /missense/){
		@inSilicoPredList = (('.') x 11);
	}
	$predictionOut = join("",@inSilicoPredList[0..9]).",".$inSilicoPredList[10];
	if ($inSilicoPredList[-1] =~ /\d/){                #$inSilicoPredList[-1] = $varInfo{$varID}{"dbNSFP_REVEL_score"}去掉&的内容
		if ($inSilicoPredList[-1]>=0.773){
			$pp3Bp4Out = "PP3_M:$inSilicoPredList[-1]";
		}elsif ($inSilicoPredList[-1]>=0.644){
			$pp3Bp4Out = "PP3:$inSilicoPredList[-1]";
		}elsif($inSilicoPredList[-1]>0.29){
			$pp3Bp4Out = "$inSilicoPredList[-1]";
		}elsif ($inSilicoPredList[-1]>0.183){
			$pp3Bp4Out = "BP4:$inSilicoPredList[-1]";
		}elsif($inSilicoPredList[-1]<=0.183){
			$pp3Bp4Out = "BP4_M:$inSilicoPredList[-1]";
		}
		if ($maxSpliceAIscore >= 0.2){
			$pp3Bp4Out .= "|Y";
		}
	}elsif ($consequenceOut =~ /missense/){  #WGS有20%左右的missense位点未注释REVEL得分
		if ($maxSpliceAIscore >= 0.2){
			$pp3Bp4Out = "|Y";
		}else{
			$pp3Bp4Out = ".";
		}
	}elsif ($impactOut =~ /LOW|MODIFIER/){
		if ($consequenceOut =~ /intron_variant|synonymous_variant/){
			if ($maxSpliceAIscore >= 0.2){
				$pp3Bp4Out = "PP3:Y";
			}elsif ($maxSpliceAIscore <= 0.1){
				$pp3Bp4Out = "BP4:N";
			}else {
				$pp3Bp4Out = ".";
			}
		}else{
			if ($maxSpliceAIscore >= 0.2){
				$pp3Bp4Out = "|Y";
			}elsif ($maxSpliceAIscore <= 0.1){
				$pp3Bp4Out = "|N";
			}else {
				$pp3Bp4Out = ".";
			}
		}
	}else{
		$pp3Bp4Out = ".";
	}
	#-------------------------Done PP3/BP4---------------------------------------------------

	#-----------------------------PP2 标签---------------------------------------------------
	if (defined $zScoreOut && $zScoreOut =~ /\d/) {
		$zScoreOut = sprintf("%.2f",$zScoreOut);
		if ($consequenceOut =~ /missense/ && $zScoreOut>3.09){
			$pp2Out = "PP2:$zScoreOut";
		}else{$pp2Out = ".:$zScoreOut";}
	}else {
		$pp2Out = ".";
	}
	#--------------------------Done PP2 标签-------------------------------------------------
	#-------------------------表型关键词匹配程度标记-------------------------------------------
	my ($matchKeyWordsCount,$overlapMatchKeyWordsCount,$tagKeyWords) =(0,0,"") ;
	my @matchKeyWordsList;
	my @overlapMatchKeyWordsList;
	foreach my $keyWord (@{$gene2Phen{$geneOut}}) {
		if ($keyWord~~@keyWordList) {
			push(@matchKeyWordsList, $keyWord);
		}
	}
	if (@matchKeyWordsList) {
		$matchKeyWordsCount = @matchKeyWordsList;
		$tagKeyWords .= "[".$matchKeyWordsCount."/".$keyWordsCount."]";
		foreach my $keyWord (@keyWordList) {
			if ($keyWord~~@matchKeyWordsList) {$tagKeyWords .= $phen2CN{$keyWord}."(".$keyWord.")"."|";}
			else {$tagKeyWords .= ".|";}
		}
		$tagKeyWords =~ s/\|$//;
	}elsif (@geneList) {
		my %tmpHash;
		@geneList = grep{++$tmpHash{$_}<2}@geneList;
		foreach my $overlapGene (@geneList) {
			foreach my $keyWord (@{$gene2Phen{$overlapGene}}) {
				if ($keyWord~~@keyWordList) {
					$overlapMatchKeyWordsCount++;
					push(@overlapMatchKeyWordsList, $keyWord);
				}
			}
		}
		if (@overlapMatchKeyWordsList) {
			$overlapMatchKeyWordsCount = @overlapMatchKeyWordsList;
			$tagKeyWords .= "*[".$overlapMatchKeyWordsCount."/".$keyWordsCount."]";
			foreach my $keyWord (@keyWordList) {
				if ($keyWord~~@overlapMatchKeyWordsList) {
					$tagKeyWords .= $phen2CN{$keyWord}."(".$keyWord.")"."|";
				}else {$tagKeyWords .= ".|";}
			}
			$tagKeyWords =~ s/\|$//;
		}
	}
	#-------------------------Done 表型关键词匹配程度标记-------------------------------------------
	#-------------------------优先级分类标记------------------------------------------------------
	my $tagPriority = "Other";
	if ($varInfo{$varID}{"IsLocalPLP"} eq '1' or $varInfo{$varID}{"IsException"} eq '1'){
		$tagPriority = "Biosan_PLP";
		print $varID."\n";
	}elsif ($varInfo{$varID}{"IsClinvarPLP"} eq '1'){
		$tagPriority = "ClinVar_PLP";
	}elsif (exists($gene2morbid{$geneOut}) and ($allTrancriptsOut =~ /HIGH/ or $overlapGeneOut =~ /HIGH/ or $spliceAIout =~ /Y/)){
		$tagPriority = "Candidate_LoF";
	}elsif (exists($gene2morbid{$geneOut}) and ($allTrancriptsOut =~ /missense/ or $overlapGeneOut =~ /missense/) and $REVEL_scoreOut >= 0.6){
		$tagPriority = "Candidate_Damaging";
	}elsif (exists($gene2morbid{$geneOut}) and ($allTrancriptsOut =~ /inframe/ or $overlapGeneOut =~ /inframe/ or $allTrancriptsOut =~ /protein_altering_variant/ or $overlapGeneOut =~ /protein_altering_variant/)){
		$tagPriority = "Candidate_Damaging";
	}
	#----------------------------------排序得分---------------------------------------------------------
	my ($pathogenicityScore,$inheritanceScore,$mafScore,$qualScore) = (0,0,0,0);
	if (defined $inheritanceOut && $inheritanceOut =~ /AD|XLD/) {
		 if ($tagGenetic =~ /SD|;Denovo|^Denovo/) {
			 $rankScore = 0.27;
			 $inheritanceScore = 0.27;
		 }
	}
	if (defined $inheritanceOut && $inheritanceOut =~ /AR/) {
		 if ($tagGenetic =~ /Hom|CH|SR/) {
			 $rankScore = 0.27;
			 $inheritanceScore = 0.27;
		 }
	}
	if ($varID =~ /chrX/) {
		 if ($tagGenetic =~ /SR|Hemi|;Denovo|^Denovo/) {
			 $rankScore = 0.27;
			 $inheritanceScore = 0.27;
		 }
	}
	if (defined $inheritanceOut && $varID !~ /chrX/ && $inheritanceOut !~ /AR|AD/){
		 if ($tagGenetic =~ /SD|SR|Hom|CH|;Denovo|^Denovo/) {
			 $rankScore =0.12;
			 $inheritanceScore =0.12;
		 }
	}
	my $keyWordScore = 0;
	#if ($tagKeyWords =~ /\.panel/ && $tagKeyWords !~ /report_CES\.panel/) {$keyWordScore += 1;}
	if ($tagKeyWords =~ /\d\//) {$keyWordScore += sprintf("%.2f",0.3+0.01*$matchKeyWordsCount);}
	$rankScore +=$keyWordScore;
	if ($tagPathogenicity =~ /P-V|P-S|P-M|LP-V|LP-S|LP-M/) { ## clinvar致病加分，不对软件预测、突变类型、人群频率再计分
		$rankScore +=0.5; #0.33
		$pathogenicityScore +=0.5;
	}
	elsif ($tagPathogenicity =~ /P-P|LP-P/) {## clinvar致病加分，不对软件预测、突变类型、人群频率再计分
		$rankScore +=0.2;
		$pathogenicityScore +=0.2;
	}
	elsif ($tagPathogenicity =~ /B-V|B-S/) { ## clinvar致病B-V|B-S,致病性减分，如果不在文献白名单才对高频进行减分,才对致病性进行减分
		#$rankScore -=0.5;
		#$pathogenicityScore -=0.5
		if ($tagWhite eq 'F'){
			$rankScore -=0.5;
			$pathogenicityScore -=0.5;
			if ($tagMaf eq "High") {
				$rankScore -=1;
				$mafScore -=1;
			}elsif ($tagMaf eq "Moderate") {
				$rankScore -=0.2;
				$mafScore -=0.2;
			}elsif ($tagMaf eq "ND") {
				$rankScore -=0;
				$mafScore -=0;
			}
		}
	}
	elsif ($tagPathogenicity =~ /B-M|B-P/) {## clinvar致病B-M|B-P,致病性减分，如果不在文献白名单才对高频进行减分,才对致病性进行减分
			#$rankScore -=0.4;
			#$pathogenicityScore -=0.4;
		if ($tagWhite eq 'F'){
			$rankScore -=0.4;
			$pathogenicityScore -=0.4;
			if ($tagMaf eq "High") {
				$rankScore -=1;
				$mafScore -=1;
			}elsif ($tagMaf eq "Moderate") {
				$rankScore -=0.2;
				$mafScore -=0.2;
			}elsif ($tagMaf eq "ND") {
				$rankScore -=0;
				$mafScore -=0;
			}
		}
	}
	else {
		if (defined $pp2Out && $pp2Out =~ /PP2/) {
				$rankScore +=0.05;
				$pathogenicityScore +=0.05;
		}
		if (defined $pp3Bp4Out && $pp3Bp4Out =~ /PP3/) {
			$rankScore +=0.05;
			$pathogenicityScore +=0.05;
		}elsif (defined $pp3Bp4Out &&  $pp3Bp4Out =~ /BP4/) {
			if ($tagWhite eq 'F'){
				$rankScore -=0.05;
				$pathogenicityScore -=0.05;
			}
		}else {
			if ($impactOut eq "HIGH") {
				$rankScore +=0.2; #0.1
				$pathogenicityScore +=0.2;
			}elsif ($impactOut eq "LOW") {
				if ($tagWhite eq 'F'){
					$rankScore -=0.02;
					$pathogenicityScore -=0.02;}
			}elsif ($impactOut eq "MODIFIER") {
				if ($tagWhite eq 'F'){
					$rankScore -=0.05;
					$pathogenicityScore -=0.05;}
			}
		}
		if  ($tagPathogenicity =~ /VUS-V|VUS-S|VUS-M|VUS-P|Conflict/){
			if ($tagMaf eq "0") {
					$rankScore +=0.03;
					$mafScore +=0.03;
			}
			if ($tagWhite eq 'F'){
				if ($tagMaf eq "High") {
					$rankScore -=1;
					$mafScore -=1;
				}elsif ($tagMaf eq "Moderate") {
					$rankScore -=0.2;
					$mafScore -=0.2;
				}elsif ($tagMaf eq "ND") {
					$rankScore -=0;
					$mafScore -=0;
				}
			}
		}
		if ($tagPathogenicity eq '.'){
			if ($tagMaf eq "0") {
					$rankScore +=0.03;
					$mafScore +=0.03;
			}
			if ($tagWhite eq 'F'){
				if ($tagMaf eq "High") {
					$rankScore -=1; # -0.5
					$mafScore -=1;
				}elsif ($tagMaf eq "Moderate") {
					$rankScore -=0.2;
					$mafScore -=0.2;
				}elsif ($tagMaf eq "ND") {
					$rankScore -=0;
					$mafScore -=0;
				}
			}
		}
	}
	if ((not defined $diseaseEnOut) or (defined $diseaseEnOut && $diseaseEnOut !~ /\w/)){
		$keyWordScore-=0.3; ## zr add 20230407
		$rankScore =sprintf("%.2f",$rankScore-0.3);
	}
	#print $varID."\t".$probandGT."\t".$tagQual."\n";
	if (defined $tagQual && $tagQual eq "Low") {
		$rankScore =sprintf("%.2f",$rankScore-0.1);
		$qualScore +=-0.1;
	}elsif (defined $tagQual && $tagQual eq "False") {
		$rankScore =sprintf("%.2f",$rankScore-0.3);
		$qualScore +=-0.3;
	}
	$rankScore =sprintf("%.2f",$rankScore);
	push(@{$geneRankScore{$geneOut}},$rankScore);
	#---------------------------Done 排序得分-----------------------------------------------------------

	$varInfo{$varID}{"local_path_Evidence"} =~ s/\$\$/=/g;
	$varInfo{$varID}{"local_path_Evidence"} =~ s/::/;/g;
	$varInfo{$varID}{"local_path_Evidence"} =~ s/&&/ \| /g;
	$varInfo{$varID}{"local_path_Evidence"} =~ s/\#\#/\|/g;
	$varInfo{$varID}{"local_path_Evidence"} =~ tr/&_/, /;
	$varInfo{$varID}{"clinvar_CLNREVSTAT"} =~ tr/&_/, /;
	$varInfo{$varID}{"HGMD_Pubmed"} =~ tr/&_/, /;
	$varInfo{$varID}{"HGMD_Pubmed"} =~ s/\#\#/ \| /g;
	if (defined $pliOut) {
		$pliOut = ($pliOut =~ /^\.$/)? "." : sprintf("%.2f", $pliOut);
		$pliOut =~ s/0\.00/0/;
		$pliOut =~ s/1\.00/1/;
	}
	else {$pliOut = ".";}
	my $localAcAn = ($varInfo{$varID}{"LocalMAF_AN"}=~ /\d/)?$varInfo{$varID}{"LocalMAF_AC"}."/".$varInfo{$varID}{"LocalMAF_AN"} : ".";
	my $GnomADExomesAcAn = ($varInfo{$varID}{"GnomADExomes_controls_AN"} =~ /\d/)?$varInfo{$varID}{"GnomADExomes_controls_AC"}."/".$varInfo{$varID}{"GnomADExomes_controls_AN"} : ".";
	my $GnomADExomesEasAcAn = ($varInfo{$varID}{"GnomADExomes_controls_AN_eas"} =~ /\d/)?$varInfo{$varID}{"GnomADExomes_controls_AC_eas"}."/".$varInfo{$varID}{"GnomADExomes_controls_AN_eas"} : ".";
	my $GnomADGenomesAcAn = ($varInfo{$varID}{"GnomADGenomes_controls_AN"} =~ /\d/)?$varInfo{$varID}{"GnomADGenomes_controls_AC"}."/".$varInfo{$varID}{"GnomADGenomes_controls_AN"} : ".";
	my $GnomADGenomesEasAcAn = ($varInfo{$varID}{"GnomADGenomes_controls_AN_eas"} =~ /\d/)?$varInfo{$varID}{"GnomADGenomes_controls_AC_eas"}."/".$varInfo{$varID}{"GnomADGenomes_controls_AN_eas"} : ".";
	my $clinsigOut='.';
	my $clinicalSignificanceOut='.';
	my @clinsigOutList = map{&clinSigAbbr($_)} split(/&/,$varInfo{$varID}{"clinvar_CLNSIG"});
	$clinsigOut = join(";", @clinsigOutList);
	#$varInfo{$varID}{"clinvar_ClinicalSignificance"} =~ s/&_/_/g;
	my @clinsigList = map{&clinSigAbbr($_)} split(/&/, $varInfo{$varID}{"clinvar_ClinicalSignificance"});
	$clinicalSignificanceOut = join("|", @clinsigList);

	#print $varID."\t".$varInfo{$varID}{"clinvar_CLNSIG"}."\t".$clinsigOut."\t".$clinicalSignificanceOut."\n";

	$varInfo{$varID}{"clinvar_Submitter"} =~ s/&_/, /g;
	$varInfo{$varID}{"clinvar_Submitter"} =~ s/_/ /g;
	$varInfo{$varID}{"clinvar_Submitter"} =~ s/&/\|/g;
	$varInfo{$varID}{"clinvar_CollectionMethod"} =~ tr/_&/ \|/;
	$varInfo{$varID}{"clinvar_CLNDN"} =~ s/&_/, /g;
	$varInfo{$varID}{"clinvar_CLNDN"} =~ s/_/ /g;
	$varInfo{$varID}{"clinvar_CLNDN"} =~ s/&/\|/g;
	my $lofOut;
	if ((defined $hiOut) && (defined $pliOut) && $hiOut=~/\d/ && $pliOut=~/\d/) {
		$lofOut = ($hiOut==30 or $pliOut>0.9)? "LOF:$hiOut:$pliOut" : ".:$hiOut:$pliOut";
	}
	elsif ((defined $hiOut) && $hiOut=~/\d/) {
		$lofOut = ($hiOut==30)? "LOF:$hiOut:." : ".:$hiOut:.";
	}
	elsif ((defined $pliOut) && $pliOut=~/\d/) {
		$lofOut = ($pliOut>0.9)? "LOF:.:$pliOut" : ".:.:$pliOut";
	}
	else {$lofOut = ".";}
	if ($varInfo{$varID}{"local_path_Evidence"} !~ /\d/) {
		$varInfo{$varID}{"local_path_Evidence"} = "ClinVar:$clinsigOut;HGMD:$varInfo{$varID}{'HGMD_Class'}($varInfo{$varID}{'HGMD_Rank_Score'})";
		my $exonPos = ($exonIntronOut =~ /(\d+)/)[0];
		my $exonDistance;
		if ((defined $exonPos) && $exonPos =~ /\d/ && $exonCountOut=~ /\d/) {
			$exonDistance = $exonCountOut-$exonPos;
		}
		if (($impactOut eq "HIGH") && (defined $exonDistance) && $exonDistance>2 && $lofOut =~ /LOF/) {
			$varInfo{$varID}{"local_path_Evidence"} .= " | PVS1:LOF(HI=$hiOut:PLI=$pliOut),无义、移码或剪接位点变异";
		}
		$varInfo{$varID}{"local_path_Evidence"} .= " | Local=$localAcAn;GnomAD_WES_EAS=$GnomADExomesEasAcAn;GnomAD_WES_ALL=$GnomADExomesAcAn;GnomAD_WGS_EAS=$GnomADGenomesEasAcAn;GnomAD_WGS_ALL=$GnomADGenomesAcAn;GnomAD_Hom=$homAltCountOut;GnomAD_Total=$varInfo{$varID}{'GnomADAcAn'};GnomAD_Total_EAS=$varInfo{$varID}{'GnomADEasAcAn'}";
		if ($pp2Out =~ /PP2/) {
			$varInfo{$varID}{"local_path_Evidence"} .= " | $pp2Out";
		}
		if (defined $pp3Bp4Out && $pp3Bp4Out =~ /PP3/) {
			$varInfo{$varID}{"local_path_Evidence"} .= " | $pp3Bp4Out";
		}elsif (defined $pp3Bp4Out && $pp3Bp4Out =~ /BP4/) {
			$varInfo{$varID}{"local_path_Evidence"} .= " | $pp3Bp4Out";
		}else {
			$varInfo{$varID}{"local_path_Evidence"} .= " | 无PP3:$pp3Bp4Out";
		}
		$varInfo{$varID}{"local_path_Evidence"} =~ s/ClinVar:\.;//;
		$varInfo{$varID}{"local_path_Evidence"} =~ s/HGMD:\.\(\.\)//;
		$varInfo{$varID}{"local_path_Evidence"} =~ s/^ \| //;
	}
	if ($consequenceOut =~ /missense/) {
		my $aaPos = (split(/\//, $proteinPositionOut))[0];
		my $transcriptNoVersion = (split(/\./, $transcriptOut))[0];
		if (exists($hashPM5{$transcriptNoVersion}{$aaPos})) {
			$hashPM5{$transcriptNoVersion}{$aaPos} =~ s/;$//;
			my @pm5List = split(/;/,$hashPM5{$transcriptNoVersion}{$aaPos});
			for my $pm5Info(@pm5List) {
				#print($hgvspOut."\n".$dbHGVSp."\n");
				my ($dbName,$dbTranscript,$dbHGVSc,$dbHGVSp) = split(/:/, $pm5Info);
				if ($hgvscOut !~ /$dbHGVSc/) {
					if ($hgvspOut =~ /$dbHGVSp/) {$pm5Out .= "PS1:".$pm5Info.";";}
					else {$pm5Out .= "PM5:".$pm5Info.";";}
					#print($pm5Out);
				}
			}	
		}
	}
	if (defined $pm5Out) {$pm5Out =~ s/;$//;}

	# if ($gene2strand{$entrezIdOut} =~ /-/ and $hgvscOut =~ /ins|dup/){
		# my ($chr,$pos,$ref,$alt) = split(/-/,$varID);
		# $varPosOut = $chr.":".$pos."_".($pos+1);
	# }elsif($gene2strand{$entrezIdOut} =~ /-/ and $hgvscOut =~ /del/){
		# my ($chr,$pos,$ref,$alt) = split(/-/,$varID);
		# my $lacklength = length($ref) - length($alt);
		# if ($lacklength == 1){
			# $varPosOut = $chr.":".($pos+1);
		# }
		# if ($lacklength > 1){
			# $varPosOut = $chr.":".($pos+1)."_".($pos+$lacklength);
		# }
	# }elsif ($gene2strand{$entrezIdOut} !~ /-/ and $hgvscOut =~ /dup/){ #chrX:48542822-48542823 #chrX:100624849
		# my ($chr,$pos) = (split(/:|_/,$varPosOut))[0,-1];
		# my $posend = $pos + 1;
		# $varPosOut = $chr.":".$pos."_".$posend;
	# }
	$varPosOut =~ s/-/_/;
	# ----- liftover coordinates for this variant -----
	my $varIDliftover = '.';
	my $varPosLiftover = '.';
	if (exists $var2liftover{$varID}) {
		$varIDliftover = $var2liftover{$varID};
		if ($varPosOut =~ /_/) {
			my ($chr, $start, $end) = $varPosOut =~ /(chr.*?):(.*?)_(.*)/;
			my $startLiftover = $start - $var2diff{$varID};
			my $endLiftover   = $end   - $var2diff{$varID};
			$varPosLiftover = $chr . ':' . $startLiftover . '_' . $endLiftover;
		} else {
			my ($chr, $start) = $varPosOut =~ /(chr.*?):(.*)/;
			my $startLiftover = $start - $var2diff{$varID};
			$varPosLiftover = $chr . ':' . $startLiftover;
		}
	}
	# ----- end liftover -----
	if (exists($TTN2PSI{$geneOut.'_'.$exonIntronOut})){
		$pp3Bp4Out = $pp3Bp4Out."|".$TTN2PSI{$geneOut.'_'.$exonIntronOut};
	}
	if (defined $digenicOut) {$digenicOut =~ s/;$//;}

	if ((!defined $CS || (defined $CS && $CS !~ /CS/)) && defined $tagGenetic && $tagGenetic eq '.'){
		if ($probandZygosityOut eq 'Hom' && defined $dadZygosityOut && defined $momZygosityOut){
			if ($dadZygosityOut eq 'Hom' && $momZygosityOut eq 'Hom'){
				$tagGenetic = 'Hom:P_hom/M_hom';
			}elsif ($dadZygosityOut eq 'Het' && $momZygosityOut eq 'Het'){
				$tagGenetic = 'Hom:P_het/M_het';
			}elsif ($dadZygosityOut eq 'Hom' && $momZygosityOut eq 'Het'){
				$tagGenetic = 'Hom:P_hom/M_het';
			}elsif ($dadZygosityOut eq 'Het' && $momZygosityOut eq 'Hom'){
				$tagGenetic = 'Hom:P_het/M_hom';
			}
		}
	}

	if (defined $maxMafOut and $maxMafOut ne '.'){
		# $maxMafOut = sprintf "%.6f", $maxMafOut;
		$maxMafOut = &FormatSigFigs($maxMafOut,2);
	}
	my $gnomADAfOut = '.';
	if ($varInfo{$varID}{'GnomADAf'} ne '.'){
		# $gnomADAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADAf'};
		$gnomADAfOut = $varInfo{$varID}{'GnomADAf'};
		$gnomADAfOut = &FormatSigFigs($gnomADAfOut,2);
	}
	my $gnomADEasAfOut = '.';
	if ($varInfo{$varID}{'GnomADEasAf'} ne '.'){
		# $gnomADEasAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADEasAf'};
		$gnomADEasAfOut = $varInfo{$varID}{'GnomADEasAf'};
		$gnomADEasAfOut = &FormatSigFigs($gnomADEasAfOut,2);
	}
	my $localAfOut = '.';
	if ($varInfo{$varID}{"LocalMAF_AF"} ne '.'){
		# $gnomADEasAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADEasAf'};
		$localAfOut = $varInfo{$varID}{"LocalMAF_AF"};
		$localAfOut = &FormatSigFigs($localAfOut,2);
	}
	my $gnomADExomesAfOut = '.';
	if ($varInfo{$varID}{"GnomADExomes_controls_AF"} ne '.'){
		# $gnomADEasAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADEasAf'};
		$gnomADExomesAfOut = $varInfo{$varID}{"GnomADExomes_controls_AF"};
		$gnomADExomesAfOut = &FormatSigFigs($gnomADExomesAfOut,2);
	}
	my $gnomADExomesEasAfOut = '.';
	if ($varInfo{$varID}{"GnomADExomes_controls_AF_eas"} ne '.'){
		# $gnomADEasAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADEasAf'};
		$gnomADExomesEasAfOut = $varInfo{$varID}{"GnomADExomes_controls_AF_eas"};
		$gnomADExomesEasAfOut = &FormatSigFigs($gnomADExomesEasAfOut,2);
	}
	my $gnomADGenomesAfOut = '.';
	if ($varInfo{$varID}{"GnomADGenomes_controls_AF"} ne '.'){
		# $gnomADEasAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADEasAf'};
		$gnomADGenomesAfOut = $varInfo{$varID}{"GnomADGenomes_controls_AF"};
		$gnomADGenomesAfOut = &FormatSigFigs($gnomADGenomesAfOut,2);
	}
	my $gnomADGenomesEasAfOut = '.';
	if ($varInfo{$varID}{"GnomADGenomes_controls_AF_eas"} ne '.'){
		# $gnomADEasAfOut = sprintf "%.6f", $varInfo{$varID}{'GnomADEasAf'};
		$gnomADGenomesEasAfOut = $varInfo{$varID}{"GnomADGenomes_controls_AF_eas"};
		$gnomADGenomesEasAfOut = &FormatSigFigs($gnomADGenomesEasAfOut,2);
	}
	my @output = ($rankScore,$tagPriority,$tagKeyWords,$tagGenetic,$tagPathogenicity,$tagQual,$tagMaf,
		$geneOut,$inheritanceOut,$dosageScoreOut,$pliOut,$diseaseCnOut,$diseaseEnOut,$synopsisCnOut,$chpoOut,
		$varIDliftover, $varPosLiftover, $varID, $varPosOut,$consequenceOut,$transcriptOut,$allTrancriptsOut,$overlapGeneOut,$exonIntronOut,$exonCountOut,$hgvscOut,$hgvspOut,$proteinPositionOut,
		$varInfo{$varID}{"local_path_Pathogenicity"},$varInfo{$varID}{"local_path_EvidenceList"},$varInfo{$varID}{"local_path_Evidence"},$varInfo{$varID}{"intervar_SIG"},
		$probandZygosityOut,$probandFormatOut,$probandVafOut,$dadZygosityOut,$dadFormatOut,$dadVafOut,$momZygosityOut,$momFormatOut,$momVafOut,$otherZygosityOut,$otherFormatOut,$otherVafOut,
		$maxAcAnOut,$maxMafOut,$homAltCountOut,$varInfo{$varID}{'GnomADAcAn'},$gnomADAfOut,$varInfo{$varID}{'GnomADEasAcAn'},$gnomADEasAfOut,$GnomADExomesAcAn,$gnomADExomesAfOut,$GnomADExomesEasAcAn,$gnomADExomesEasAfOut,"/",$localAcAn,$localAfOut,
		"/",$clinicalSignificanceOut,$varInfo{$varID}{"HGMD_Class"}.":".$varInfo{$varID}{"HGMD_Rank_Score"},$varInfo{$varID}{"HGMD_Pubmed"},
		$pp3Bp4Out,$predictionOut,$pp2Out,$spliceAIout.":".$spliceAIscoreOut,$dbscSNVOut.":".$dbscSNVscoreOut,
		$clingenClassificationOut,$varTypeInClinvarOut,$imprintOut,$digenicOut,$geneAliasOut,$omimPhenotypeIdOut,$synopsisEnOut,$diseaseChpoOut,$penetranceGeneReviewsOut,$penetranceHpoOut,$penetranceOmimOut,
		$varInfo{$varID}{"ID"},$omimGeneIdOut,$varInfo{$varID}{"clinvar_CollectionMethod"},$varInfo{$varID}{"clinvar_Submitter"},$varInfo{$varID}{"clinvar_CLNDN"},$varInfo{$varID}{"clinvar_CLNREVSTAT"},$pm5Out,
		$varInfo{$varID}{"Mapability"},$varInfo{$varID}{"Repeat"},$varInfo{$varID}{"clinvar"},$hgncIdOut,$entrezIdOut,$impactOut,$clinsigOut,
		$GnomADGenomesAcAn,$gnomADGenomesAfOut,$GnomADGenomesEasAcAn,$gnomADGenomesEasAfOut,
		$inheritanceScore,$pathogenicityScore,$mafScore,$keyWordScore,$qualScore);
	my @outputDefined;
	for my $item(@output) {
		unless (defined $item) {$item = ".";}
		push(@outputDefined, $item);
	}
	@{$varOutPut{$varID}} = @output
}
foreach my $varID (sort keys(%varOutPut)) {
	my $geneOut = $varOutPut{$varID}[7];
	if ($geneOut !~ /^HLA-/) {
		my $geneRankScore = max(@{$geneRankScore{$geneOut}});
		# Carrier新加的
		if (defined $CS and $CS eq 'CS'){
			my $tagGenetics = $varOutPut{$varID}[3];
			my $rankScore = $varOutPut{$varID}[0];
			my $inheritanceOut = $varOutPut{$varID}[8];
			if($tagGenetics =~ /CH:P/){
				$tagGenetics = "Het:P";
			}elsif($tagGenetics =~ /CH:M/){
				$tagGenetics = "Het:M";
			}
			if( (grep { $_ eq "Het:P" } @{$geneCH{$geneOut}}) && (grep { $_ eq "Het:M" } @{$geneCH{$geneOut}}) && (grep { $_ eq "Hom:P/M" } @{$geneCH{$geneOut}})){
				if($tagGenetics =~ /Hom:P\/M/){
					$varOutPut{$varID}[3] = "hom/CH:Hom";
				}
			}
			if( (grep { $_ eq "Het:P" } @{$geneCH{$geneOut}}) && (grep { $_ eq "Het:M" } @{$geneCH{$geneOut}})){
				if($tagGenetics =~ /Het:P/){
					$varOutPut{$varID}[3] = "CH:P";
				}elsif($tagGenetics =~ /Het:M/){
					$varOutPut{$varID}[3] = "CH:M";
				}
			}elsif( ((grep { $_ eq "Het:P" } @{$geneCH{$geneOut}}) || (grep { $_ eq "Het:M" } @{$geneCH{$geneOut}})) && (grep { $_ eq "Hom:P/M" } @{$geneCH{$geneOut}})){
				if($tagGenetics =~ /Hom:P\/M/){
					$varOutPut{$varID}[3] = "hom/CH:Hom";
				}elsif($tagGenetics =~ /Het:P/){
					$varOutPut{$varID}[3] = "hom/CH:Het:P";
				}elsif($tagGenetics =~ /Het:M/){
					$varOutPut{$varID}[3] = "hom/CH:Het:M";
				}
			}
		}
		my $outLine = $geneRankScore."\t".join("\t", @{$varOutPut{$varID}});
		print OUT $outLine."\n";
	}

}
close OUT;
print "# 7.Main. Done--------------------------------------------------------------------------------\n";
if (defined $CS and $CS eq 'CS'){
	`tail -n +2 $fltFileUnsorted | sort -t \$'\t' -k1,1nr -k9,9V -k2,2nr>> $fltFile && rm $fltFileUnsorted`;
}else{
	`tail -n +2 $fltFileUnsorted | sort -t \$'\t' -k2,2nr>> $fltFile && rm $fltFileUnsorted`;
}

sub aminoacidAbbr {
	my ($Amino_acid) = @_;
	$Amino_acid =~ s/Asn/N/g;
	$Amino_acid =~ s/Ala/A/g;
	$Amino_acid =~ s/Arg/R/g;
	$Amino_acid =~ s/Asp/D/g;
	$Amino_acid =~ s/Cys/C/g;
	$Amino_acid =~ s/Gln/Q/g;
	$Amino_acid =~ s/Glu/E/g;
	$Amino_acid =~ s/Gly/G/g;
	$Amino_acid =~ s/His/H/g;
	$Amino_acid =~ s/Ile/I/g;
	$Amino_acid =~ s/Leu/L/g;
	$Amino_acid =~ s/Lys/K/g;
	$Amino_acid =~ s/Met/M/g;
	$Amino_acid =~ s/Phe/F/g;
	$Amino_acid =~ s/Pro/P/g;
	$Amino_acid =~ s/Ser/S/g;
	$Amino_acid =~ s/Thr/T/g;
	$Amino_acid =~ s/Trp/W/g;
	$Amino_acid =~ s/Tyr/Y/g;
	$Amino_acid =~ s/Val/V/g;
	$Amino_acid =~ s/Ter/\*/g;
	return $Amino_acid;
}

sub clinSigAbbr {
	my ($clinsig) = @_;
	my %sig = ('.'=>'.','Pathogenic'=>'P','Likely_pathogenic'=>'LP','Pathogenic/Likely_pathogenic'=>'P/LP','Uncertain_significance'=>'VUS','Likely_benign'=>'LB','Benign'=>'B','Benign/Likely_benign'=>'B/LB','drug_response'=>'DR','Conflicting_interpretations_of_pathogenicity'=>'Conflict','Conflicting_classifications_of_pathogenicity'=>'Conflict','risk_factor'=>'RF','association'=>'.','protective'=>'.','Affects'=>'.','not_provided'=>'.','Likely_risk_allele'=>'.','other'=>'.','Pathogenic_low_penetrance'=>'P_low_penetrance','confers_sensitivity'=>'confers_sensitivity','_low_penetrance'=>'low_penetrance','Uncertain_risk_allele'=>'.');
	if (exists($sig{$clinsig})){
		return $sig{$clinsig};
	}else{
		return $clinsig;
	}
}

sub _Simplify {
   my($n)  = @_;
   return  if (! defined($n));
   $n      =~ s/\s+//g;
   $n      =~ s/^([+-])//;
   my $s   = $1  ||  '';
   return  if ($n eq '');
   my $exp;
   if ($n  =~ s/[eE]([+-]*\d+)$//) {
      $exp = $1;
   } else {
      $exp = 0;
   }

   my($int,$dec,$sig,$lsp);

   if ($n  =~ /^\d+$/) {                    # 00     0123     012300
      $int    = $n+0;                       # 0      123      12300
      $int    =~ /^(\d+?)(0*)$/;
      my($i,$z) = ($1,$2);                  # 0,''   123,''   123,00
      $lsp    = length($z);                 # 0      0        2
      $sig    = length($int) - $lsp;        # 1      3        3
      $dec    = '';

   } elsif ($n =~ /^0*\.(\d+)$/) {          # .000       .00123     .0012300
      $dec    = $1;                         # 000        00123      0012300
      $int    = '';
      $dec    =~ /^(0*?)([1-9]\d*?)?(0*+)$/;
      my($z0,$d,$z1) = ($1,$2,$3);          # '','',000  00,123,''  00,123,00
      $lsp    = -length($dec);              # -3         -5         -7
      $sig    = length($dec)-length($z0);   # 3          3          5

   } elsif ($n =~ /^0*(\d+)\.(\d*)$/) {     # 12.       12.3
      ($int,$dec) = ($1,$2);                # 12,''     12,3
      $lsp    = -length($dec);              # 0         -1
      $sig    = length($int) + length($dec);# 2         3

   } else {
      return;
   }

   # Handle the exponent, if any

   if ($exp > 0) {
      if ($exp >= length($dec)) {
         $int  = "$int$dec" . "0"x($exp-length($dec));
         $dec  = '';
      } else {
         $int .= substr($dec,0,$exp);
         $dec  = substr($dec,$exp);
      }
      $lsp += $exp;
      $int  =~ s/^0*//;
      $int  = '0'  if (! $int);

   } elsif ($exp < 0) {
      if (-$exp < length($int)) {
         $dec  = substr($int,$exp) . $dec;
         $int  = substr($int,0,length($int)+$exp);
      } else {
         $dec  = "0"x(-$exp-length($int)) . "$int$dec";
         $int  = "0";
      }
      $lsp += $exp;
   }

   # We have a decimal point if:
   #    There is a decimal section
   #    An integer ends with a significant 0 but is not exactly 0
   # We prepend a sign to anything except for 0

   my $num;
   if ($dec eq '') {
      $num  = $int;
      $num .= "."  if ($lsp == 0  &&  $int =~ /0$/  &&  $int ne '0');
   } else {
      $int  = "0"  if ($int eq '');
      $num  = "$int.$dec";
   }
   $s       = ''   if ($num == 0  ||  $s eq '+');
   $num     = "$s$num";

   return ($num,$sig,$lsp,$s,$int,$dec);
}

sub FormatSigFigs {
   my($N,$n) = @_;
   return ''  if ($n !~ /^\d+$/  ||  $n == 0);

   my($ret,$sig,$lsp,$s,$int,$dec);
   ($N,$sig,$lsp,$s,$int,$dec) = _Simplify($N);
   return ""  if (! defined($N));
   return '0.0'  if ($N==0  &&  $n==1);

   return $N  if ($sig eq $n);

   # Convert $N to an exponential where the numeric part with the exponent
   # ignored is 0.1 <= $num < 1.0.  i.e. 0.#####e## where the first '#' is
   # non-zero.  Then we can format it using a simple sprintf command.

   my($num,$e);
   if ($int > 0) {
      $num = "0.$int$dec";
      $e   = length($int);
   } elsif ($dec ne ''  &&  $dec > 0) {
      $dec =~ s/^(0*)//;
      $num = "0.$dec";
      $e   = -length($1);
   } else {
      $e = 0;
      $num = "$int.$dec";
   }

   # sprintf doesn't round 5 up, so convert a 5 to 6 in the n+1'th position

   if ($n < $sig  &&  substr($num,$n+2,1) eq '5') {
      substr($num,$n+2,1) = '6';
   }

   # We have to handle the one special case:
   #    0.99 (1) => 1.0
   # If sprintf rounds a number to 1.0 or higher, then we reduce the
   # number of decimal points by 1.

   my $tmp = sprintf("%.${n}f",$num);
   if ($tmp >= 1.0) {
      $n--;
      $tmp = sprintf("%.${n}f",$num);
   }
   ($N,$sig,$lsp,$s,$int,$dec) = _Simplify("$s${tmp}e$e");
   return $N;
}

# 检查数组所有元素是否都包含 关键词列表中的任意一个
sub all_outbody {
    my ($array_ref, $keywords_ref) = @_;

    # 遍历数组每一个元素
    foreach my $elem (@$array_ref) {
        my $matched = 0;

        # 检查当前元素是否匹配任意一个关键词
        foreach my $kw (@$keywords_ref) {
            if ($elem =~ /\Q$kw\E/) {  # \Q 自动转义特殊字符，安全匹配
                $matched = 1;
                last;
            }
        }

        # 只要有一个元素不匹配任何关键词，直接返回失败
        if (!$matched) {
            return 0;
        }
    }

    # 所有元素都通过检查
    return 1;
}
