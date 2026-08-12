#!/usr/bin/env perl -w
use strict;
use Cwd;
use FindBin qw($Bin);
use File::Path;
use Getopt::Long;
#说明：按rank文件中的家系、trio或单人拆分
#家系送检模式分类：
#1. 超过4人，需要单独处理
#2. 3-4人：a. 一家三口，孩子是患者；b. 一家三口，夫妻一方是患者；c. 父母+2个孩子
#3. 2人：a. 夫妻双方，表型均正常；b. 夫妻双方，一方是患者；c. 夫妻双方均是患者
#4. 1人：统一按单先证者模式分析
my ($rankFile, $inVcf, $sample, $outVcf, $outTsv, $bcftools, $whitelist, $help);
GetOptions (
		"rank|r:s"		=> \$rankFile,
		"inVcf|i=s"		=> \$inVcf,
		"outVcf|o=s"	=> \$outVcf,
		"outTsv|tsv:s"	=> \$outTsv,
		"sample|s=s"	=> \$sample,
		"bcftools=s"	=> \$bcftools,
		"whitelist|w=s"	=> \$whitelist,
		"help|h"		=> \$help
);
if (!defined $inVcf || !defined $outVcf || !defined $sample || !defined $bcftools || defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Copyright: Biosan Dx
	Author: houmin\@biosan.cn	
	Created:   2021-11-22	
	Updated:   2022-05-09
	Updated:   2022-06-29,出于家系解耦合的目的, 将输入的vcf文件由slivar结果改为VEP注释并按宽松规则或严格规则过滤的结果
	Usage1:     perl $0 -r rankFile -i input_vcf -o output_vcf -s familyID -bcftools /bi/software/bcftools-1.18/bcftools -whitelist whitelistV4.vcf.gz
	Usage2:     perl $0 -i input_vcf -o output_vcf -s sampleID -bcftools /bi/software/bcftools-1.18/bcftools -whitelist whitelistV4.vcf.gz
	Options:
		-rank|r		<file>				optional, rank file of one pedigree
		-inVcf|i	<file>				input vcf
		-outVcf|o	<file>				output vcf
		-outTsv|tsv	<file>				optional, output tsv
		-sample|s	<string>			sample ID(eg. WGS22040074-WGS), or family ID(eg. JX22G10000513_WGS22050405.fam.tmp), or trio ID(eg. JX22G10000513_WGS22050405.trio.tmp)
		-bcftools	<file>				bcftools
		-whitelist|w  <file>      whitelistV4 VCF, bgzip-compressed and indexed
		-help|h		<help information>	this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}
my $dir = getcwd;

my %trio2samples = ();
my %sample2status = ();
my %sample2relation = ();
if (defined $rankFile) {
	open RANK, $rankFile or die $!;
	my $header = <RANK>;
	chomp $header;
	my @item = split(/\t/, $header);
	my $index = 0;
	my %hashInfo = map{$_=>$index++} @item;
	while (my $line = <RANK>) {
		chomp $line;
		$line =~ s/\[keep\]//g;
		my @arr = split(/\t/, $line);
		my @sampleList = ($arr[$hashInfo{"ProbandID"}],$arr[$hashInfo{"DadID/SpouseID"}],$arr[$hashInfo{"MomID/KidID"}],$arr[$hashInfo{"OtherID"}]);
		my @relationList = ($arr[$hashInfo{"Proband"}],$arr[$hashInfo{"Dad/Spouse"}],$arr[$hashInfo{"Mom/Kid"}],$arr[$hashInfo{"Other"}]);
		my @statusList = ($arr[$hashInfo{"ProbandStatus"}],$arr[$hashInfo{"Dad/SpouseStatus"}],$arr[$hashInfo{"Mom/KidStatus"}],$arr[$hashInfo{"OtherStatus"}]);
		@{$trio2samples{$arr[$hashInfo{"FamilyID"}]}} = ($arr[$hashInfo{"ProbandID"}],$arr[$hashInfo{"DadID/SpouseID"}],$arr[$hashInfo{"MomID/KidID"}]);
		for (my $i=0;$i<=$#sampleList ;$i++) {
			if ($sampleList[$i] ne ".") {
				$sample2status{$sampleList[$i]} = $statusList[$i];
				$sample2relation{$arr[$hashInfo{"FamilyID"}]}{$sampleList[$i]} = $relationList[$i];
			}
		}
	}
	close RANK;
}

if ($sample =~ /fam/){
	my $familyID = $sample =~ s/\.fam//r;
	&pedigree($familyID);
}elsif ($sample =~ /trio/){
	my $familyID = $sample =~ s/\.trio//r;
	&trio($familyID);
}else{
	&solo($sample);
}

sub pedigree {
	my ($familyID) = @_;
	my @sampleList = keys(%{$sample2relation{$familyID}});
	my $sampleCount = keys(%{$sample2relation{$familyID}});
	my %pedigree = ();
	if ($sampleCount > 4) {
		print "#!!!Error, the sample count of $familyID is greater than 4!\n";
		last;
	}else {
		my @splitMemberList = ();
		my @splitIfKeepVar = ();
		my $splitIndex = -1;
		foreach my $sampleID (@sampleList) {
			if ($sample2relation{$familyID}{$sampleID} eq "0proband") {
				$pedigree{"0proband"} = $sampleID;
			}elsif ($sample2relation{$familyID}{$sampleID} eq "1dad") {
				$pedigree{"1dad"} = $sampleID;
			}elsif ($sample2relation{$familyID}{$sampleID} eq "2mom") {
				$pedigree{"2mom"} = $sampleID;
			}elsif ($sample2relation{$familyID}{$sampleID} eq "3wife") {
				$pedigree{"3wife"} = $sampleID;
			}elsif ($sample2relation{$familyID}{$sampleID} eq "4husband") {
				$pedigree{"4husband"} = $sampleID;
			}elsif ($sample2relation{$familyID}{$sampleID} eq "5sib") {
				$pedigree{"5sib"} = $sampleID;
			}elsif ($sample2relation{$familyID}{$sampleID} eq "6kid") {
				$pedigree{"6kid"} = $sampleID;
			}else{
				$pedigree{"7other"} = $sampleID;
			}
		}
		my @relationList = sort keys(%pedigree);
		foreach my $relation (@relationList) {
			$splitIndex++;
			push(@splitMemberList, $pedigree{$relation});
			my ($dad, $mom) = (0, 0);
			my $ifAffected = 1;
			if ($sample2status{$pedigree{$relation}} == 2) {
				$ifAffected = 2;
				push(@splitIfKeepVar, $splitIndex);
			}elsif ($relation =~ /3wife|4husband/ && (not exists($pedigree{"6kid"}))) {
				push(@splitIfKeepVar, (0,1));
			}
		}
		my $include = "";
		for (@splitIfKeepVar) {
				$include .= "GT[$_]~\"1\" || ";
		}
		$include =~ s/ \|\| $//;
		my $splitMembers = join(",",@splitMemberList);
		my $pedigreeTmpVcf = $outVcf.".tmp.vcf.gz";
		my $splitSampleCmd = "$bcftools view -Ou -s $splitMembers $inVcf | $bcftools view -i '$include' -Oz -o $pedigreeTmpVcf && $bcftools index -f -t $pedigreeTmpVcf && $bcftools annotate -Ou -a $whitelist --pair-logic exact -m +WHITELIST $pedigreeTmpVcf | $bcftools view -Ou -i '(FMT/DP[0]>=5 && FMT/GQ[0]>=20) || WHITELIST=1' | $bcftools annotate -Ov -x INFO/WHITELIST > $outVcf";
		print "# Split Pedigree:\n$splitSampleCmd\n";
		system($splitSampleCmd);
		unlink $pedigreeTmpVcf;
		unlink $pedigreeTmpVcf.".tbi";
	}
}

sub trio {
	my ($familyID) = @_;
	my $splitCmd = "$bcftools view -s ${$trio2samples{$familyID}}[0],${$trio2samples{$familyID}}[1],${$trio2samples{$familyID}}[2] $inVcf | $bcftools annotate -x FMT/ADS | $bcftools view -e 'GT[0]!~\"1\" && GT[1]!~\"1\" && GT[2]!~\"1\"' > $outVcf";
	print "# Split trio:\n$splitCmd\n";
	system($splitCmd);
}

sub solo {
	my ($sampleID) = @_;
	open SOLO, ">$outTsv";
	my $headerOfSplitFile = `zgrep "^#CHROM" $inVcf | sed -e 's/#//' -e 's/INFO.*//'`;
	$headerOfSplitFile .= `zgrep "##INFO=<ID=CSQ" $inVcf | sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations from Ensembl VEP. Format: //' -e 's/|/\t/g' -e 's/\">//'`;
	$headerOfSplitFile =~ s/\n//g;
	my $headerOfSplitSolo = join("\t",($headerOfSplitFile, "IsLocalPLP", "IsClinvarPLP", "IsException", "IsLOF", "IsDM", "FORMAT", $sampleID));
	my $soloTmpVcf = $outVcf.".tmp.vcf.gz";
	my $include = "FMT/GT[0]~\"1\"";
	my $splitSampleCmd = "$bcftools view -Ou -s $sampleID $inVcf | $bcftools annotate -Ou -x FMT/ADS | $bcftools view -i '$include' -Oz -o $soloTmpVcf && $bcftools index -f -t $soloTmpVcf && $bcftools annotate -Ou -a $whitelist --pair-logic exact -m +WHITELIST $soloTmpVcf | $bcftools view -Ou -i '(FMT/DP[0]>=5 && FMT/GQ[0]>=20) || WHITELIST=1' | $bcftools annotate -Ov -x INFO/WHITELIST > $outVcf";
	print "# Split sample:\n$splitSampleCmd\n";
	system($splitSampleCmd);
	unlink $soloTmpVcf;
	unlink $soloTmpVcf.".tbi";

	print SOLO $headerOfSplitSolo."\n";
	my $splitVepCmd = "$bcftools +split-vep $outVcf -f '%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\t%IsLocalPLP\\t%IsClinvarPLP\\t%IsException\\t%IsLOF\\t%IsDM\\t%FORMAT\\n' -A tab -d >> $outTsv";
	print "# Split VEP:\n$splitVepCmd\n";
	system($splitVepCmd);
	close SOLO;
}