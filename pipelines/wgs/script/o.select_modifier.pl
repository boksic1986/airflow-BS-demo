#!/usr/bin/perl -w
use strict;
use Getopt::Long;
my ($pedFile, $sampleID, $inVcf, $outTsv, $bcftools, $help);

GetOptions (
                "ped:s"         => \$pedFile,
                "sample:s"      => \$sampleID,
                "inVcf|i=s"     => \$inVcf,
                "outTsv|tsv=s"  => \$outTsv,
                "bcftools=s"    => \$bcftools,
                "help|h"        => \$help
);
if ((!defined $pedFile && !defined $sampleID) || !defined $inVcf || !defined $outTsv || !defined $bcftools || defined $help) {
        my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
        usage1:  perl $0 -i input.vcf -ped input.ped -tsv output.tsv -bcftools bcftools
        usage2:  perl $0 -i input.vcf -s sampleID -tsv output.tsv -bcftools bcftools
        Options:
                -ped            <file>                          optional, ped file of one pedigree
                -sample         <string>                        optional, sampleID
                -inVcf|i        <file>                          input vcf
                -outTsv|tsv     <file>                          output tsv
                -bcftools       <file>                          bcftools
                -help|h         <help information>              this help information
---------------------------------------------------------------------------------------------------
Usage
        print $usage;
        exit(1);
}

#形成Vep split 文件固定表头部分
my $headerOfSplitFile = `grep "^#CHROM" $inVcf | sed -e 's/#//' -e 's/INFO.*//'`;
$headerOfSplitFile .= `grep "##INFO=<ID=CSQ" $inVcf | sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations from Ensembl VEP. Format: //' -e 's/|/\t/g' -e 's/\">//'`;
$headerOfSplitFile =~ s/\n//g;

#通过家系ped文件，确定家系样本编号及可判断Denovo变异样本 
my @sampleList = ();
my @trio = ();
my %sample2relation = ();

if (defined $pedFile){
	open PED, $pedFile or die $!;
	my @item = ("familyID","SampleID","Father","Mother","Gender","Status"); #根据实际使用调整
	my $index1 = 0;
	my %hashInfo = map{$_=>$index1++} @item;
	while(my $line = <PED>){
		chomp $line;
		my @part = split /\t/, $line;
		push @sampleList, $part[$hashInfo{"SampleID"}];
		if($part[$hashInfo{"Father"}] ne 0 && $part[$hashInfo{"Mother"}] ne 0){
			push @trio, $part[$hashInfo{"SampleID"}];
			$sample2relation{$part[$hashInfo{"SampleID"}]}{"Father"} = $part[$hashInfo{"Father"}];
			$sample2relation{$part[$hashInfo{"SampleID"}]}{"Mother"} = $part[$hashInfo{"Mother"}];
		}
	}
	close PED;
}elsif (defined $sampleID){
	push @sampleList, $sampleID;
}

#vep split 文件增加表头FORMAT和家系所有样本编号
my $AllsampleID = join("\t",@sampleList);
$headerOfSplitFile .= "\t"."FORMAT"."\t".$AllsampleID;

$AllsampleID = join(",",@sampleList);
my $splitVepCmd = "$bcftools view -s $AllsampleID $inVcf -Ov -o -| $bcftools view -i \"MAX(FMT/DP)>=10\" -Ov -o -| $bcftools +split-vep - -f '%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\t%FORMAT\\n' -A tab -d > $outTsv.temp.split.tsv";
print "# Split VEP:\n$splitVepCmd\n";
system($splitVepCmd);

#定义函数：判断数据库样本量和频率组合是否达标
sub is_valid {
	my ($dist, $freq) = @_;
	return 1 if ($dist eq ".");  # 缺失值视为通过
	return 1 if ($dist < 2000);  # 样本量 <2000 视为通过
	return 1 if ($dist >= 2000 && $dist < 10000 && $freq < 0.005);  
	return 1 if ($dist >= 10000 && $freq < 0.0005);
	return 0;  # 其他情况不通过
}

#读入vep split 文件，逐行处理,写入output tsv 文件
open SPLIT, "$outTsv.temp.split.tsv" or die $!;
open TSV,">$outTsv" or die $!;
my @header = split /\t/,$headerOfSplitFile;
my $index2 = 0;
my %head = map{$_=>$index2++} @header;
while (my $line = <SPLIT>){
	chomp $line;
	next if $line =~ /^#/;
	my @F = split /\t/, $line;
	my $impact = $F[$head{"IMPACT"}];
	my $Consequence = $F[$head{"Consequence"}];
	my $SpliceAI = $F[$head{"SpliceAI_cutoff"}];
	
	my @pairs = (
		[$F[$head{"GnomADExomes_controls_AN"}],$F[$head{"GnomADExomes_controls_AF"}]],
		[$F[$head{"GnomADExomes_controls_AN_eas"}],$F[$head{"GnomADExomes_controls_AF_eas"}]],
		[$F[$head{"GnomADGenomes_controls_AN"}],$F[$head{"GnomADGenomes_controls_AF"}]],
		[$F[$head{"GnomADGenomes_controls_AN_eas"}],$F[$head{"GnomADGenomes_controls_AF_eas"}]],
		[$F[$head{"LocalMAF_AN"}],$F[$head{"LocalMAF_AF"}]]
	);
	# ----判断影响等级----
	my $pass_impact = 0;
	if ($impact eq "HIGH" || $impact eq "MODERATE" || $impact eq "LOW") {
		$pass_impact = 1;
		print "WARNING: Impact is not set to \"MODIFIER\". Please verify the VCF file. The script will keep running.\n";
	} elsif ($impact eq "MODIFIER") {
		$pass_impact = 1;
		foreach my $pair (@pairs) {
			my ($dist, $freq) = @$pair;
			if ($dist =~ /(\d+)\&(\d+)/ ){
				print  "WARNING:  Please check AN $dist , ",join("-",@F[0,1,3,4]), ", use AN $1\n";
				$dist = $1;
			}
			if ($freq =~ /(\S+)\&(\d+)/ ){
				print  "WARNING:  Please check AF $freq , ",join("-",@F[0,1,3,4]), ", use AF $1\n";
				$freq = $1;
			}
			unless (is_valid($dist, $freq)) {
				$pass_impact = 0;
				last;  # 只要有一对不达标，整体就不通过
			}
		}
	}
	
	# ----判断MODIFIER保留条件----
	my $pass_filter = 0;
	if ($SpliceAI eq "PASS") {
		$pass_filter = 1;
	} elsif ($Consequence =~ /non_coding_transcript_exon_variant/) {
		$pass_filter = 1;
	} elsif ($Consequence ne "intergenic_variant") {
		if (@trio){
			foreach my $trio(@trio){
				if($F[$head{$trio}] !~ /^0\/0:/ && $F[$head{$trio}] =~ /\S\/\S:\d+,\d+:(\d+):(\d+):/ && $1>=10 && $2>=20 && $F[$head{$sample2relation{$trio}{"Father"}}] =~ /^0\/0/ && $F[$head{$sample2relation{$trio}{"Mother"}}] =~ /^0\/0/){
					$pass_filter = 1;
				}
			}
		}
		foreach my $sample(@sampleList){
			if($F[$head{$sample}] =~ /^1\/1:\d+,\d+:(\d+):(\d+):/ && $1>=10 && $2>=20){
				$pass_filter = 1;
			}
		}
	}
	
	#输出符合条件的行
	if ($pass_impact && $pass_filter) {
        	print TSV $line,"\n"; 
    	}
}
close SPLIT;
close TSV;
