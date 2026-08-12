#!/usr/bin/env perl -w
use strict;
use Cwd;
use FindBin qw($Bin);
use File::Path;
use File::Basename;
use Getopt::Long;

my ($invcfFile, $outvcfFile, $help);
GetOptions (
		"in_vcf|i=s"	    => \$invcfFile,
		"out_vcf|o=s"	    => \$outvcfFile,
		"help|h"            => \$help
);
if (!defined $invcfFile || !defined $outvcfFile || defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Copyright: Biosan Dx
	Author: houmin\@biosan.cn	
	Version:   V6.0.5
	Created:   2021-11-12	
	Usage:     perl $0 -i inRankFile -o outRankFile -p outPedFile
	Options:
       -in_vcf|i        <file>               input vcf file of couple
       -out_vcf|o       <file>               output vcf file of couple, with virtual proband
       -help|h           <help information>   this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}
my $kidname;
if($invcfFile =~ /-CS.split.fam.vcf/){
	my @suffixlist = qw(-CS.split.fam.vcf);
	my ($name,$paths,$suffix) = fileparse($invcfFile,@suffixlist);
	$kidname = $name;
}elsif($invcfFile =~ /-CS.split.flt.fam.vcf/){
	my @suffixlist = qw(-CS.split.flt.fam.vcf);
	my ($name,$paths,$suffix) = fileparse($invcfFile,@suffixlist);
	$kidname = $name;
}
open IN1, $invcfFile or die $!;
open OUT1, ">$outvcfFile";
while (my $line = <IN1>) {
	chomp $line;
	if ($line =~ /^##/) {
		print OUT1 $line."\n";
	}
	elsif ($line =~ /^#CHROM/) {
		my @item = split /\t/, $line;
		print OUT1 join("\t", @item[0..8])."\t".$kidname.".kid"."\t".$item[9].".dad"."\t".$item[10].".mom"."\n";
	}
	else{
		my @arr = split /\t/, $line;
		my %GTs = ();
		my ($kidGT,$kidZygosity);
		if ($line =~ /^chr\d/) {
			$GTs{(split /:/,$arr[9])[0]}++;
			$GTs{(split /:/,$arr[10])[0]}++;
			if ((exists($GTs{"1/1"}) && $GTs{"1/1"}==2) || (exists($GTs{"0/1"}) && $GTs{"0/1"}==2) || (exists($GTs{"1/1"}) && exists($GTs{"0/1"})) || (exists($GTs{"1/."}) && exists($GTs{"0/1"})) || (exists($GTs{"1/1"}) && exists($GTs{"1/."})) || (exists($GTs{"1/."}) && $GTs{"1/."}==2) || (exists($GTs{"1/1"}) && exists($GTs{"./1"})) || (exists($GTs{"0/1"}) && exists($GTs{"./1"})) || (exists($GTs{"./1"}) && $GTs{"./1"}==2)){
				$kidZygosity = "1/1:0,100:100:99";
			}
			elsif ((exists($GTs{"1/1"}) || exists($GTs{"0/1"}) || exists($GTs{"./1"}) || exists($GTs{"1/."})) && (exists($GTs{"0/0"}) || exists($GTs{"0/."}) || exists($GTs{"./0"}) || exists($GTs{"./."}))) {
				$kidZygosity = "0/1:50,50:100:99";
			}
		}
		elsif ($line =~ /^chrX/) {
			my ($momFormat, $dadFormat) = ($arr[10],$arr[9]);
			if ($momFormat !~ /^0\/0/ && $momFormat !~ /^0\/\./ && $momFormat !~ /^\.\/0/ && $momFormat !~ /^\.\/\./) {
				$kidZygosity = "1/1:0,100:100:99";
			}elsif ($dadFormat !~ /^0\/0/ && $dadFormat !~ /^0\/\./ && $dadFormat !~ /^\.\/0/ && $dadFormat !~ /^\.\/\./) {
				$kidZygosity = "0/1:50,50:100:99";
			}
		}
		if (defined $kidZygosity) {
			if ($arr[8] eq "GT:AD:DP:GQ") {
				$kidGT = $kidZygosity;
			}
			elsif ($arr[8] eq "GT:AD:DP:GQ:PL") {
				$kidGT = $kidZygosity.":800,0,1000";
			}
			elsif ($arr[8] eq "GT:AD:DP:GQ:PGT:PID") {
				$kidGT = $kidZygosity.":.:.";
			}
			elsif ($arr[8] eq "GT:AD:DP:GQ:PGT:PID:PL") {
				$kidGT = $kidZygosity.":.:.:800,0,1000";
			}
			print OUT1 join("\t", @arr[0..8])."\t".$kidGT."\t".$arr[9]."\t".$arr[10]."\n";
		}
	}
}
close IN1;
close OUT1;

