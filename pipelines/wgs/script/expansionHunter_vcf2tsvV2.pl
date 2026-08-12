#!/usr/bin/env perl -w
use strict;
use FindBin qw($Bin);
use File::Path;
use Getopt::Long;
my ($inTxt, $database, $inVcf, $output, $liftover, $liftoverChain, $help);
GetOptions (
		"input|i=s"	    => \$inTxt,
		"vcf|v=s"	    => \$inVcf,
		"database|d=s"  => \$database,
		"output|o=s"	=> \$output,
		"liftover=s"	=> \$liftover,
		"chain=s"		=> \$liftoverChain,
		"help|h"        => \$help
);
if (!defined $inTxt || !defined $database || !defined $inVcf || !defined $output || !defined $liftover || !defined $liftoverChain || defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Usage:     perl $0 -i sample.expansionHunter.txt -v sample.vcf -d Repeat_expansion_info_hg38V20230808.txt -o sample.expansionHunter.tsv -liftover /bi/software/liftover/liftOver -chain hg38ToHg19.over.chain.gz
	Options:
       -input|i       <file>           input txt file, eg. sample.expansionHunter.txt
       -vcf|v         <file>           input vcf file, eg. sample.vcf
       -database|d    <file>           eg. Repeat_expansion_info_hg38V20230808.txt
       -output|o      <file>           output tsv file, eg. sample.expansionHunter.tsv
       -liftover      <file>           eg. /bi/software/liftover/liftOver
       -chain         <file>           eg. hg38ToHg19.over.chain.gz
       -help|h        <help>           this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}
my $projectDir = $Bin =~ s/\/src//r;
my $liftoverInput = $inTxt =~ s/txt/bed/r;
my $liftoverBed = $inTxt =~ s/txt/liftover.bed/r;
my $liftoverUnmap = $inTxt =~ s/txt/liftover.unmap/r;
my @outHeader = ("VariantId","ReferenceRegion_hg19","ReferenceRegion_hg38","ChromosomeBands","CatalogId:ReferenceCN:ReferenceLen","RepeatUnit","Motif_In-frame_of_Gene","相关疾病","正常重复数","中间型重复数","前突变型重复数/外显率降低","致病重复数","Genotype","FILTER","GenotypeConfidenceInterval","CountsOfSpanningReads","CountsOfFlankingReads","CountsOfInrepeatReads","LocusId","AlleleCount","Coverage","FragmentLength");

open BED, ">$liftoverInput";
my (%score, %var2info);
open IN, $inTxt or die $!;
chomp(my $txtHeader = <IN>);
my @txtItem = split /\t/, $txtHeader;
my %var2txt;
while(my $line = <IN>){
	chomp $line;
	my @arr = split /\t/, $line;
	my %h = map{$txtItem[$_]=>$arr[$_]}(0..$#arr);
	$h{'LocusId'} =~ s/_\S+$//;
	$arr[8] = $h{'LocusId'};
	$var2txt{$h{'VariantId'}} = join("\t",@arr);
	my ($chr, $start, $end) = $h{'ReferenceRegion'} =~ /(chr.*):(\d+)-(\d+)/;
	print BED join("\t",($chr, $start, $end, $h{'ReferenceRegion'}))."\n";
}
close IN;
close BED;
`$liftover $liftoverInput $liftoverChain $liftoverBed $liftoverUnmap`;
my %var2liftover;
open LIFTOVER, $liftoverBed or die $!;
while (my $line = <LIFTOVER>){
	chomp $line;
	my @arr = split(/\t/, $line);
	$var2liftover{$arr[3]} = $arr[0].':'.$arr[1].'-'.$arr[2];
}
close LIFTOVER;

open DB, $database or die $!;
chomp(my $header = <DB>);
my @dbItem = split /\t/, $header;
my (%phe,%phe1);
while(my $line = <DB>){
	chomp $line;
	my @arr = split /\t/, $line;
	my %h = map{$dbItem[$_]=>$arr[$_]}(0..$#arr);
	$phe{$h{'VariantId'}} = $line;
	if($h{'疾病名称'} ne "."){ 
		$phe1{$h{'VariantId'}} = 1; 
	}
}
close DB;

open OUT,">$output" or die $!;
print OUT join("\t",@outHeader)."\n";
open VCF, $inVcf or die;
my @item = ('#CHROM','POS','ID','REF','ALT','QUAL','FILTER','INFO','FORMAT','sample');
while(my $line = <VCF>){
	chomp $line;
	if($line =~/^#/){
		next;
	}
	my @arr = split /\t/, $line;
	my %h = map{$item[$_]=>$arr[$_]}(0..$#arr);
	my @t = split /;/, $h{'INFO'};
	my %info;
	foreach my $info(@t){
		my @p = split /=/,$info;
		$info{$p[0]} = $p[1];
	}
	my $varid = $info{'VARID'};
	if($h{'FILTER'} eq "PASS"){
		$score{$varid} += 1;
	}else{
		$score{$varid} += 0;
	}
	my @txt = split /\t/, $var2txt{$varid};
	my %h1 = map{$txtItem[$_]=>$txt[$_]}(0..$#txt);

	my @arr2;
	my %h2;
	if(exists $phe{$varid}){
		if(exists($phe1{$varid})){ 
			$score{$varid} += 0.2; 
		}
		my ($g_num,$s1_num,$s2_num,$s3_num) = (0,0,0,0);
		@arr2 = split /\t/, $phe{$varid};
		%h2 = map{$dbItem[$_] => $arr2[$_]}(0..$#arr2);
		if($varid =~ /CNBP_CA|FXN_A|HTT_CCG|NOP56_CGCCTG/){
		}elsif($h1{'Genotype'} ne "."){
			$s1_num = $1 if($h2{'致病重复数'} =~ /(\d+)/);
			$s2_num = $1 if($h2{'前突变型重复数/外显率降低'} =~ /(\d+)/);
			$s3_num = $1 if($h2{'正常重复数'} =~ /(\d+)$/);
			$g_num = $1 if($h1{'Genotype'} =~ /(\d+)/);
			if($h1{'Genotype'} =~ /(\d+)\S(\d+)/ && $2 > $1){
				$g_num = $2;
			}
			if($s1_num > 0 && $g_num/$s1_num>0.95){
				$score{$varid} += 0.6;
			}elsif($s2_num > 0 && $g_num/$s2_num>0.95){
				$score{$varid} += 0.5;
			}elsif($s3_num > 0 && $g_num/$s3_num>1){
				$score{$varid} += 0.4;
			}
		}		
	}
	else{
		@arr2 = ('.') x 8;
		%h2 = map{$dbItem[$_] => $arr2[$_]}(0..$#arr2);
	}
	my $varPosLiftover = '.';
	if (exists($var2liftover{$h1{'ReferenceRegion'}})){
		$varPosLiftover = $var2liftover{$h1{'ReferenceRegion'}};
	}
	$var2info{$varid} = join("\t",($h1{'VariantId'},$varPosLiftover,$h1{'ReferenceRegion'},$h2{'Region'},$info{'REPID'}.':'.$info{'REF'}.':'.$info{'RL'},$h1{'RepeatUnit'},$h2{'Motif_In-frame_of_Gene'},$h2{'疾病名称'},$h2{'正常重复数'},$h2{'中间型重复数'},$h2{'前突变型重复数/外显率降低'},$h2{'致病重复数'},$h1{'Genotype'},$h{'FILTER'},$h1{'GenotypeConfidenceInterval'},$h1{'CountsOfSpanningReads'},$h1{'CountsOfFlankingReads'},$h1{'CountsOfInrepeatReads'},$h1{'LocusId'},$h1{'AlleleCount'},$h1{'Coverage'},$h1{'FragmentLength'}));
}
close VCF;

my @ATXN8OS = split /\t/, $var2info{'ATXN8OS'};
my @ATXN8OS_CTA = split /\t/, $var2info{'ATXN8OS_CTA'};
my @ATXN8OS_new;
for(my $i=0; $i<=$#ATXN8OS; $i++){
	if($i==3 || $i==7 || $i==8 || $i==9 || $i==10 || $i==11 || $i==18){
		push(@ATXN8OS_new, $ATXN8OS[$i]);
	}else{
		push(@ATXN8OS_new, $ATXN8OS[$i]."&".$ATXN8OS_CTA[$i]);
	}
}
$score{'ATXN8OS'} = 0.2;
if($ATXN8OS_new[13] eq "PASS&PASS"){
	$score{'ATXN8OS'} += 1 ; 
}
my ($g_num,$s1_num,$s2_num,$s3_num) = (0,0,0,0);
if($ATXN8OS_new[12] =~ /(\d+)\/(\d+)\S+(\d+)\/(\d+)/){
	$g_num = $2 + $4 ; 
}
$s1_num = $1 if($ATXN8OS_new[11] =~ /(\d+)/);
$s2_num = $1 if($ATXN8OS_new[10] =~ /(\d+)/);
$s3_num = $1 if($ATXN8OS_new[8] =~ /(\d+)$/);
if($s1_num > 0 && $g_num/$s1_num>0.95){
	$score{'ATXN8OS'} += 0.6;
}elsif($s2_num > 0 && $g_num/$s2_num>0.95){
	$score{'ATXN8OS'} += 0.5;
}elsif($s3_num > 0 && $g_num/$s3_num>1){
	$score{'ATXN8OS'} += 0.4;
}
delete$score{'ATXN8OS_CTA'};
$var2info{'ATXN8OS'} = join("\t",@ATXN8OS_new);
foreach my $id(sort{$score{$b}<=>$score{$a}}keys(%score)){
	print OUT $var2info{$id}."\n";
} 
close OUT;

`rm $liftoverInput $liftoverBed $liftoverUnmap`;
