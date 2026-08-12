#!/usr/bin/env perl -w
use strict;
use FindBin qw($Bin);
use File::Path;
use Getopt::Long;

my ($fltVcf, $slivarVcf, $slivarTsv, $pedFile, $bcftoolsPath, $slivarPath);
my ($slivarJs, $slivarGnomad, $CS, $help);
GetOptions (
		"input|i=s"	    => \$fltVcf,
		"outputVcf|v=s"	=> \$slivarVcf,
		"outputTsv|t=s"	=> \$slivarTsv,
		"ped|p=s"	    => \$pedFile,
	    "bcftools:s"    => \$bcftoolsPath,
		"slivar:s"      =>\$slivarPath,
		"type:s"	    => \$CS,
		"slivar-js=s"   => \$slivarJs,
		"slivar-gnomad=s" => \$slivarGnomad,
        "help|h"        => \$help
);
if (!defined $fltVcf or !defined $slivarVcf or !defined $slivarTsv or !defined $pedFile or !defined $bcftoolsPath or !defined $slivarPath or defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Usage:     perl $0 -i {familyID}.split.fam.vcf -v {familyID}.slivar.vcf -t {familyID}.slivar.tsv -p {familyID}.ped -bcftools /bi/software/bcftools-1.17/bcftools -slivar /bi/software/slivar-0.2.4
	Options:
       -input|i       <vcf_file>           result of lenient filter, with .split.fam.lenient.vcf suffix, or result of strict filter, with .split.fam.vcf suffix,
       -outputVcf|v   <vcf_file>           result of slivar annotation, with .slivar.vcf or .slivar.lenient.vcf suffix
       -outputTsv|t   <tsv_file>           result of slivar annotation and split-vep, with .slivar.tsv or .slivar.lenient.tsv suffix
       -ped|p         <file>               ped file of one pedigree
       -bcftools      <string>             eg. /bi/software/bcftools-1.17/bcftools
       -slivar      <string>               the absolute path of slivar software,eg. /bi/software/slivar-0.2.4
       -type          <string>             optional, 分析类型，如果是carrier，则输入CS
       -slivar-js     <file>               slivar JavaScript resource when -slivar is a command
       -slivar-gnomad <file>               slivar gnomAD resource when -slivar is a command
       -help|h        <help information>   this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}

my $projectDir = $Bin;
my $bcftools = $bcftoolsPath;
my $slivar;
if (-d $slivarPath) {
	$slivar = "$slivarPath/slivar";
	$slivarJs //= "$slivarPath/js/slivar-functions.V6.3.0.js";
	$slivarGnomad //= "$slivarPath/gnomad.hg38.v2.zip";
}
else {
	$slivar = $slivarPath;
}
if (!defined $slivarJs or !defined $slivarGnomad) {
	die "--slivar-js and --slivar-gnomad are required when -slivar is a command\n";
}

#以下文件按顺序生成
my $vcfFilePrefix = $slivarVcf =~ s/vcf//r;
my $slivarTmpVcf = $vcfFilePrefix."tmp.vcf";
my $slivarTmpVcfGz = $slivarTmpVcf.".gz";
my $comhetTmpVcf = $vcfFilePrefix."compoundhet.tmp.vcf";
my $comhetTmpVcfGz = $comhetTmpVcf.".gz";
open FAM, ">$slivarTsv";
my $slivarCmd = "$slivar expr --js $slivarJs -g $slivarGnomad --vcf $fltVcf --ped $pedFile -o $slivarTmpVcf ".
	"--trio \"trio_specific:mom.alts>0 || dad.alts>0 || kid.alts>0\" ".
	"--trio \"LenientDenovo:hasSample(INFO,'trio_specific', kid.id) && ((kid.alts>0 && mom.alts==0 && dad.alts==0) || (variant.CHROM=='chrX' && kid.sex=='male' && mom.alts==0 && dad.alts==2 && kid.alts==2))\" ".
	"--trio \"Denovo:hasSample(INFO, 'LenientDenovo', kid.id) && hq(kid, mom, dad)\" ".
	"--trio \"Hom_P_M:hasSample(INFO,'trio_specific', kid.id) && variant.CHROM!='chrX' && kid.alts==2 && mom.alts==1 && dad.alts==1 && hq(kid, mom, dad)\" ".
	"--trio \"Hom_P:hasSample(INFO,'trio_specific', kid.id) && variant.CHROM!='chrX' && kid.alts==2 && mom.alts==0 && dad.alts>0 && hq(kid, mom, dad)\" ".
	"--trio \"Hom_M:hasSample(INFO,'trio_specific', kid.id) && variant.CHROM!='chrX' && kid.alts==2 && mom.alts>0 && dad.alts==0 && hq(kid, mom, dad)\" ".
	"--trio \"Hemi:hasSample(INFO,'trio_specific', kid.id) && kid.sex=='male' && variant.CHROM=='chrX' && kid.alts==2 && mom.alts==1 && dad.alts==0 && hq(kid, mom, dad)\" ".
	"--trio \"het_P:hasSample(INFO,'trio_specific', kid.id) && kid.alts==1 && mom.alts==0 && dad.alts==1\" ".
	"--trio \"het_M:hasSample(INFO,'trio_specific', kid.id) && kid.alts==1 && mom.alts==1 && dad.alts==0\" ".
	"--trio \"comphet_side:comphet_side(kid,mom,dad) && hasSample(INFO,'trio_specific', kid.id)\" ".
	"--family-expr \"SegregatingDominant:fam.every(segregating_dominant)\" ".
	"--family-expr \"SegregatingRecessive:fam.every(segregating_recessive)\"";

if (defined $CS and $CS eq "CS"){
	$slivarJs = "$projectDir/slivar-functions.WGS-CS.js";
	$slivarCmd = "$slivar expr --js $slivarJs -g $slivarGnomad --vcf $fltVcf --ped $pedFile -o $slivarTmpVcf ".
	"--trio \"trio_specific:mom.alts>0 || dad.alts>0 || kid.alts>0\" ".
	"--trio \"LenientDenovo:hasSample(INFO,'trio_specific', kid.id) && ((kid.alts>0 && mom.alts==0 && dad.alts==0) || (variant.CHROM=='chrX' && kid.sex=='male' && mom.alts==0 && dad.alts==2 && kid.alts==2))\" ".
	"--trio \"Denovo:hasSample(INFO, 'LenientDenovo', kid.id) && hq(kid, mom, dad)\" ".
	"--trio \"Hom_P_M:hasSample(INFO,'trio_specific', kid.id) && kid.alts==2 && mom.alts>0 && dad.alts>0\" ".
	"--trio \"Hom_P:hasSample(INFO,'trio_specific', kid.id) && variant.CHROM!='chrX' && kid.alts==2 && mom.alts==0 && dad.alts>0 && hq1(dad)\" ".
	"--trio \"Hom_M:hasSample(INFO,'trio_specific', kid.id) && variant.CHROM!='chrX' && kid.alts==2 && mom.alts>0 && dad.alts==0 && hq1(mom)\" ".
	"--trio \"Hemi:hasSample(INFO,'trio_specific', kid.id) && kid.sex=='male' && variant.CHROM=='chrX' && kid.alts==2 && mom.alts>0 && dad.alts==0 && hq1(mom)\" ".
	"--trio \"het_P:hasSample(INFO,'trio_specific', kid.id) && (kid.alts==1 && mom.alts==0 && dad.alts>0) || (kid.alts==1 && mom.alts==1 && dad.alts==2)\" ".
	"--trio \"het_M:hasSample(INFO,'trio_specific', kid.id) && (kid.alts==1 && mom.alts>0 && dad.alts==0) || (kid.alts==1 && mom.alts==2 && dad.alts==1)\" ".
	"--trio \"het_M_P:hasSample(INFO,'trio_specific', kid.id) && (kid.alts==1 && mom.alts==1 && dad.alts==1)\" ".
	"--trio \"comphet_side:comphet_side(kid,mom,dad) && hasSample(INFO,'trio_specific', kid.id)\" ".
	"--family-expr \"SegregatingDominant:fam.every(segregating_dominant)\" ".
	"--family-expr \"SegregatingRecessive:fam.every(segregating_recessive)\"";
}

my $slivarComphetCmd = "$slivar compound-hets -v $slivarTmpVcf --sample-field comphet_side --skip intergenic_variant,upstream_gene_variant,downstream_gene_variant -p $pedFile>$comhetTmpVcf";
my $bgzSlivarTmpVcfCmd = "$bcftools view $slivarTmpVcf -Oz -o $slivarTmpVcfGz && $bcftools index $slivarTmpVcfGz";
my $bgzComhetTmpVcfCmd = "$bcftools view $comhetTmpVcf -Oz -o $comhetTmpVcfGz && $bcftools index $comhetTmpVcfGz";
my $comphetCmd = "$bcftools annotate -c 'INFO/slivar_comphet' -a $comhetTmpVcfGz $slivarTmpVcfGz -Ov -o $slivarVcf";
my $addSlivarComphetTagCmd = "$slivar expr --js $slivarJs -g $slivarGnomad --vcf $slivarTmpVcf --ped $pedFile -o $slivarVcf --trio \"slivar_comphet:comphet_side(kid,mom,dad)\"";
print "# 1 Slivar:\n# $slivarCmd\n";
system($slivarCmd);
print "# 2 Comphet:\n# $slivarComphetCmd\n";
system($slivarComphetCmd);
print "# 3 bcftools bgzip and tabix:\n# $bgzSlivarTmpVcfCmd\n";
system($bgzSlivarTmpVcfCmd);

#兼容整批次都没有trio送检模式的情况,防止$comhetTmpVcf文件为空导致后续流程中断
unless (-z $comhetTmpVcf) {
	print "# 4 bcftools bgzip and tabix:\n# $bgzComhetTmpVcfCmd\n";
	system($bgzComhetTmpVcfCmd);
	print "# 5 Slivar Comphet:\n# $comphetCmd\n";
	system($comphetCmd);
}
else{
	print "# 6 add slivar_comphet tag:\n# $addSlivarComphetTagCmd\n";
	system($addSlivarComphetTagCmd);
}

my $headerOfSplitFile = `grep "^#CHROM" $fltVcf | sed -e 's/#//' -e 's/INFO.*//'`;
$headerOfSplitFile .= `grep "##INFO=<ID=CSQ" $fltVcf | sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations from Ensembl VEP. Format: //' -e 's/|/\t/g' -e 's/\">//'`;
if (defined $CS and $CS eq "CS"){
	$headerOfSplitFile .= "\t".join("\t", ("IsLocalPLP", "IsClinvarPLP", "IsException", "IsLOF", "IsDM", "Denovo", "LenientDenovo", "Hom_P_M", "Hemi", "SegregatingDominant", "SegregatingRecessive", "CompoundHet", "Hom_P", "Hom_M", "het_P", "het_M", "het_M_P"));
}else{
	$headerOfSplitFile .= "\t".join("\t", ("IsLocalPLP", "IsClinvarPLP", "IsException", "IsLOF", "IsDM", "Denovo", "LenientDenovo", "Hom_P_M", "Hemi", "SegregatingDominant", "SegregatingRecessive", "CompoundHet", "Hom_P", "Hom_M", "het_P", "het_M"));
}
$headerOfSplitFile =~ s/\n//g;
my $splitMemberList = `grep "^#CHROM" $fltVcf | sed -e 's/.*FORMAT\t//'`;
chomp($splitMemberList);
my $headerOfSplitPedigree = $headerOfSplitFile."\t"."FORMAT"."\t".$splitMemberList;
print FAM $headerOfSplitPedigree."\n";
my $splitVepCmd = "$bcftools +split-vep $slivarVcf -f '%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\t%IsLocalPLP\\t%IsClinvarPLP\\t%IsException\\t%IsLOF\\t%IsDM\\t%Denovo\\t%LenientDenovo\\t%Hom_P_M\\t%Hemi\\t%SegregatingDominant\\t%SegregatingRecessive\\t%slivar_comphet\\t%Hom_P\\t%Hom_M\\t%het_P\\t%het_M\\t%FORMAT\\n' -A tab -d >> $slivarTsv";
if (defined $CS and $CS eq "CS"){
	$splitVepCmd = "$bcftools +split-vep $slivarVcf -f '%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\t%IsLocalPLP\\t%IsClinvarPLP\\t%IsException\\t%IsLOF\\t%IsDM\\t%Denovo\\t%LenientDenovo\\t%Hom_P_M\\t%Hemi\\t%SegregatingDominant\\t%SegregatingRecessive\\t%slivar_comphet\\t%Hom_P\\t%Hom_M\\t%het_P\\t%het_M\\t%het_M_P\\t%FORMAT\\n' -A tab -d >> $slivarTsv";
}
print "# Split VEP:\n$splitVepCmd\n";
system($splitVepCmd);
close FAM;

# my $cmd = "rm $slivarTmpVcf $slivarTmpVcfGz $slivarTmpVcfGz.csi $comhetTmpVcf $comhetTmpVcfGz $comhetTmpVcfGz.csi";
# #!system ($cmd) or die "command return error num: ",$?>>8;
# system ($cmd);