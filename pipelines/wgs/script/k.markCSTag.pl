#!/usr/bin/env perl -w
use strict;
use Encode;
use FindBin qw($Bin);
use Getopt::Long;
use File::Spec;
use File::Path;
use File::Basename;
use List::Util; 
use List::Util qw/max min sum maxstr minstr shuffle first/;
use YAML::XS;
# perl /sg2/19.yuli/git/wgs/script/k.markCSTag.pl -i 01_SNV/JX22G00198543_WGS24060045-CS.flt.tsv -o 01_SNV/JX22G00198543_WGS24060045-CS.markCS.flt.tsv

my ($splitfile, $fltfile, $configFile, $help);
GetOptions (
		"input|i=s"     => \$splitfile,
		"output|o=s"    => \$fltfile,
		"cfg=s"	        => \$configFile,
		"h|help"        => \$help
);
if (!defined $splitfile or !defined $fltfile or !defined $configFile or defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Usage1:     perl $0 -i inputfile -o outputfile
Options:
       -i        <file>               input file(result of VEP->slivar->split->split_vep->annotion), with .flt.tsv suffix
       -o        <file>               output file, with cs.tsv suffix
	   -cfg      <string>             配置文件
       -h|help   <help information>   this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}

open CFG, $configFile or die $!;
my $yamlContent = do { local $/; <CFG> };
close CFG;
my $yaml = YAML::XS::Load($yamlContent);
my $morbidmap = $yaml->{'database'}->{'morbidmapFile'};

open MORBID, $morbidmap or die $!;
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

my %VarInfo=();
my %PLPvar=();
my %LOFvar=();
my %VUSvar=();
my %PLPID=();
my %LOFID=();
my %VUSID=();
open IN, $splitfile or die $!;
chomp(my $title = <IN>);
my @term = split /\t/, $title;
while(my $line = <IN>){
	chomp $line;
	my @cols = split/\t/,$line;
	my %h = map{$term[$_]=>$cols[$_]}(0..$#term);
	my $varid = ".";
	if(exists $h{'VarID_hg19'}){
		$varid = $h{'VarID_hg19'};
	}elsif(exists $h{'VarID'}){
		$varid = $h{'VarID'};
	}
	if($h{'Dad_Format'} =~ /\.\/1|1\/\./){
		$h{'Dad_Zygosity'} = "Het";
	}
	if($h{'Mom_Format'} =~ /\.\/1|1\/\./){
		$h{'Mom_Zygosity'} = "Het";
	}
	if($h{'TagPathogenicity'} !~ /P-|LP-/){
		if($h{'Pathogenicity'} =~ /致病变异/){
			$h{'TagPathogenicity'} = "P-S";
		}elsif($h{'Pathogenicity'} =~ /临床意义未明变异/){
			$h{'TagPathogenicity'} = "VUS-V";
		}elsif($h{'ClinVar_Significances'} =~ /P/ && $h{'ClinVar_Significances'} !~ /B/){
			$h{'TagPathogenicity'} = "P-P";
		}elsif($h{'HGMD_Class:HGMD_Score'} =~ /DM/ && $h{'TagPathogenicity'} =~ /B-/){
			$h{'TagPathogenicity'} = "VUS-P";
		}elsif($h{'HGMD_Class:HGMD_Score'} =~ /DM/){
			$h{'TagPathogenicity'} = "LP-P";
		}elsif($h{'ClinVar_Significances'} !~ /P|VUS/ && $h{'ClinVar_Significances'} =~ /B/ && $h{'TagPathogenicity'} !~ /VUS-/){
			$h{'TagPathogenicity'} = "B-P";
		}
	}
	if($varid =~ /chr\d/ && $h{'Inheritance'} =~ /AR|\./ && $h{'TagPathogenicity'} !~ /B-/ && $h{'TagGenetic'} ne "."){
		if($h{'TagPathogenicity'} =~ /P-|LP-/){
			if(exists $PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}}){
				$PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}} += 1;
			}else{
				$PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}} = 1;
			}
			$PLPID{$varid} = $h{'TagGenetic'};
		}elsif($h{'IMPACT'} eq 'HIGH'){
			if(exists $PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}}){
				$LOFvar{$h{'Gene'}}->{$h{'TagGenetic'}} += 1;
			}else{
				$LOFvar{$h{'Gene'}}->{$h{'TagGenetic'}} = 1;
			}
			$LOFID{$varid} = $h{'TagGenetic'};
		}else{
			if(exists $PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}}){
				$VUSvar{$h{'Gene'}}->{$h{'TagGenetic'}} += 1;
			}else{
				$VUSvar{$h{'Gene'}}->{$h{'TagGenetic'}} = 1;
			}
			$VUSID{$varid} = $h{'TagGenetic'};
		}
	}elsif($varid =~ /chrX/ && $h{'Mom_Zygosity'} ne "." && $h{'Inheritance'} =~ /XL|\./ && $h{'TagPathogenicity'} !~ /B-/ && $h{'TagGenetic'} ne "."){
		if($h{'TagPathogenicity'} =~ /P-|LP-/){
			if(exists $PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}}){
				$PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}} += 1;
			}else{
				$PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}} = 1;
			}
			$PLPID{$varid} = $h{'TagGenetic'};
		}elsif($h{'IMPACT'} eq 'HIGH'){
			if(exists $PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}}){
				$LOFvar{$h{'Gene'}}->{$h{'TagGenetic'}} += 1;
			}else{
				$LOFvar{$h{'Gene'}}->{$h{'TagGenetic'}} = 1;
			}
			$LOFID{$varid} = $h{'TagGenetic'};
		}else{
			if(exists $PLPvar{$h{'Gene'}}->{$h{'TagGenetic'}}){
				$VUSvar{$h{'Gene'}}->{$h{'TagGenetic'}} += 1;
			}else{
				$VUSvar{$h{'Gene'}}->{$h{'TagGenetic'}} = 1;
			}
			$VUSID{$varid} = $h{'TagGenetic'};
		}
	}elsif($varid =~ /chrX/ && $h{'Dad_Zygosity'} ne "." && $h{'Inheritance'} =~ /XL|\./ && $h{'TagPathogenicity'} !~ /B-/){
		if($h{'TagPathogenicity'} =~ /P-|LP-/){
			if(exists $PLPvar{$h{'Gene'}}->{'Het/Hemi:XL'}){
				$PLPvar{$h{'Gene'}}->{'Het/Hemi:XL'} += 1;
			}else{
				$PLPvar{$h{'Gene'}}->{'Het/Hemi:XL'} = 1;
			}
			$PLPID{$varid} = "Het/Hemi:XL";
		}elsif($h{'IMPACT'} eq 'HIGH'){
			if(exists $PLPvar{$h{'Gene'}}->{'Het/Hemi:XL'}){
				$LOFvar{$h{'Gene'}}->{'Het/Hemi:XL'} += 1;
			}else{
				$LOFvar{$h{'Gene'}}->{'Het/Hemi:XL'} = 1;
			}
			$LOFID{$varid} = "Het/Hemi:XL";
		}else{
			if(exists $PLPvar{$h{'Gene'}}->{'Het/Hemi:XL'}){
				$VUSvar{$h{'Gene'}}->{'Het/Hemi:XL'} += 1;
			}else{
				$VUSvar{$h{'Gene'}}->{'Het/Hemi:XL'} = 1;
			}
			$VUSID{$varid} = "Het/Hemi:XL";
		}
	}
	$VarInfo{$varid}->{$h{'Gene'}} = $line;
}
close(IN);
open OUT1, ">$fltfile";
print OUT1 "IsMorbid\tCS_Class\t$title\n";
close OUT1;
my $unsortfltfile = "$fltfile.tmp";
open("OUT",">","$unsortfltfile");
print OUT "IsMorbid\tCS_Class\t$title\n";

#以下标签的前提是：遗传模式为AR/XL/未知
#A11: P/LP + Hemi/Hom + Het/Hemi:XL
#A12: P/LP + P/LP + CH
#A2: P/LP + HIGH + CH
#A3: HIGH + Hemi/Hom + Het/Hemi:XL
#A3: HIGH + HIGH + CH
#B1: P/LP + VUS + CH
#B2: HIGH + VUS + CH
#C: VUS + Hemi/Hom + Het/Hemi:XL
#C: VUS + VUS + CH
#B3: P/LP/HIGH + B/LB + CH
#.: 其他
foreach my $keyID(keys %VarInfo){
	foreach my $keygene(keys %{ $VarInfo{$keyID} }){
		if(exists $PLPID{$keyID} && ($PLPID{$keyID} eq "Hemi:M" || $PLPID{$keyID} eq "Hom:P/M" || $PLPID{$keyID} eq "Het/Hemi:XL")){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tA11\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tA11\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif(exists $PLPID{$keyID} && ((exists $PLPvar{$keygene}->{'CH:M'} && ($PLPID{$keyID} eq 'CH:P')) || (exists $PLPvar{$keygene}->{'CH:P'} && ($PLPID{$keyID} eq 'CH:M')) || ($PLPID{$keyID} eq 'hom/CH:Hom') || ((($PLPID{$keyID} eq 'hom/CH:Het:M') || ($PLPID{$keyID} eq 'hom/CH:Het:P')) && exists $PLPvar{$keygene}->{'hom/CH:Hom'}))){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tA12\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tA12\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif((exists $PLPID{$keyID} || exists $LOFID{$keyID}) && ((exists $PLPvar{$keygene}->{'CH:M'} && exists $LOFID{$keyID} && ($LOFID{$keyID} eq 'CH:P')) || (exists $PLPvar{$keygene}->{'CH:P'} && exists $LOFID{$keyID} && ($LOFID{$keyID} eq 'CH:M')) || (exists $LOFvar{$keygene}->{'CH:M'} && exists $PLPID{$keyID} && ($PLPID{$keyID} eq 'CH:P')) || (exists $LOFvar{$keygene}->{'CH:P'} && exists $PLPID{$keyID} && ($PLPID{$keyID} eq 'CH:M')) || (exists $LOFID{$keyID} && ($LOFID{$keyID} eq 'hom/CH:Hom') && (exists $PLPvar{$keygene}->{'hom/CH:Het:M'} || exists $PLPvar{$keygene}->{'hom/CH:Het:P'} || exists $PLPvar{$keygene}->{'CH:P'} || exists $PLPvar{$keygene}->{'CH:M'})) || (exists $LOFID{$keyID} && (($LOFID{$keyID} eq 'hom/CH:Het:M') || ($LOFID{$keyID} eq 'hom/CH:Het:P') || ($LOFID{$keyID} eq 'CH:P') || ($LOFID{$keyID} eq 'CH:M')) && exists $PLPvar{$keygene}->{'hom/CH:Hom'}) || (exists $PLPID{$keyID} && (($PLPID{$keyID} eq 'hom/CH:Het:M') || ($PLPID{$keyID} eq 'hom/CH:Het:P') || ($PLPID{$keyID} eq 'CH:P') || ($PLPID{$keyID} eq 'CH:M')) && exists $LOFvar{$keygene}->{'hom/CH:Hom'}))){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tA2\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tA2\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif( exists $LOFID{$keyID} && ($LOFID{$keyID} eq "Hemi:M" || $LOFID{$keyID} eq "Hom:P/M" || $LOFID{$keyID} eq "Het/Hemi:XL")){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tA3\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tA3\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif( exists $LOFID{$keyID} && ((exists $LOFvar{$keygene}->{'CH:M'} && ($LOFID{$keyID} eq 'CH:P')) || (exists $LOFvar{$keygene}->{'CH:P'} && ($LOFID{$keyID} eq 'CH:M')) || ($LOFID{$keyID} eq 'hom/CH:Hom') || ((($LOFID{$keyID} eq 'hom/CH:Het:M') || ($LOFID{$keyID} eq 'hom/CH:Het:P')) && exists $LOFvar{$keygene}->{'hom/CH:Hom'}))){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tA3\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tA3\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif((exists $PLPID{$keyID} || exists $VUSID{$keyID}) && ((exists $PLPvar{$keygene}->{'CH:M'} && exists $VUSID{$keyID} && ($VUSID{$keyID} eq 'CH:P')) || (exists $PLPvar{$keygene}->{'CH:P'} && exists $VUSID{$keyID} && ($VUSID{$keyID} eq 'CH:M')) || (exists $VUSvar{$keygene}->{'CH:M'} && exists $PLPID{$keyID} && ($PLPID{$keyID} eq 'CH:P')) || (exists $VUSvar{$keygene}->{'CH:P'} && exists $PLPID{$keyID} && ($PLPID{$keyID} eq 'CH:M')) || (exists $VUSID{$keyID} && ($VUSID{$keyID} eq 'hom/CH:Hom') && (exists $PLPvar{$keygene}->{'hom/CH:Het:M'} || exists $PLPvar{$keygene}->{'hom/CH:Het:P'} || exists $PLPvar{$keygene}->{'CH:P'} || exists $PLPvar{$keygene}->{'CH:M'})) || (exists $VUSID{$keyID} && (($VUSID{$keyID} eq 'hom/CH:Het:M') || ($VUSID{$keyID} eq 'hom/CH:Het:P') || ($VUSID{$keyID} eq 'CH:P') || ($VUSID{$keyID} eq 'CH:M')) && exists $PLPvar{$keygene}->{'hom/CH:Hom'}) || (exists $PLPID{$keyID} && (($PLPID{$keyID} eq 'hom/CH:Het:M') || ($PLPID{$keyID} eq 'hom/CH:Het:P') || ($PLPID{$keyID} eq 'CH:P') || ($PLPID{$keyID} eq 'CH:M')) && exists $VUSvar{$keygene}->{'hom/CH:Hom'}))){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tB1\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tB1\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif((exists $LOFID{$keyID} || exists $VUSID{$keyID}) && ((exists $LOFvar{$keygene}->{'CH:M'} && exists $VUSID{$keyID} && ($VUSID{$keyID} eq 'CH:P')) || (exists $LOFvar{$keygene}->{'CH:P'} && exists $VUSID{$keyID} && ($VUSID{$keyID} eq 'CH:M')) || (exists $VUSvar{$keygene}->{'CH:M'} && exists $LOFID{$keyID} && ($LOFID{$keyID} eq 'CH:P')) || (exists $VUSvar{$keygene}->{'CH:P'} && exists $LOFID{$keyID} && ($LOFID{$keyID} eq 'CH:M')) || (exists $VUSID{$keyID} && ($VUSID{$keyID} eq 'hom/CH:Hom') && (exists $LOFvar{$keygene}->{'hom/CH:Het:M'} || exists $LOFvar{$keygene}->{'hom/CH:Het:P'} || exists $LOFvar{$keygene}->{'CH:P'} || exists $LOFvar{$keygene}->{'CH:M'})) || (exists $VUSID{$keyID} && (($VUSID{$keyID} eq 'hom/CH:Het:M') || ($VUSID{$keyID} eq 'hom/CH:Het:P') || ($VUSID{$keyID} eq 'CH:P') || ($VUSID{$keyID} eq 'CH:M')) && exists $LOFvar{$keygene}->{'hom/CH:Hom'}) || (exists $LOFID{$keyID} && (($LOFID{$keyID} eq 'hom/CH:Het:M') || ($LOFID{$keyID} eq 'hom/CH:Het:P') || ($LOFID{$keyID} eq 'CH:P') || ($LOFID{$keyID} eq 'CH:M')) && exists $VUSvar{$keygene}->{'hom/CH:Hom'}))){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tB2\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tB2\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif( exists $VUSID{$keyID} && ($VUSID{$keyID} eq "Hemi:M" || $VUSID{$keyID} eq "Hom:P/M" || $VUSID{$keyID} eq "Het/Hemi:XL")){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tC\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tC\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif(exists $VUSID{$keyID} && ((exists $VUSvar{$keygene}->{'CH:M'} && ($VUSID{$keyID} eq 'CH:P')) || (exists $VUSvar{$keygene}->{'CH:P'} && ($VUSID{$keyID} eq 'CH:M')) || ($VUSID{$keyID} eq 'hom/CH:Hom') || (exists $VUSvar{$keygene}->{'hom/CH:Hom'} && (($VUSID{$keyID} eq 'hom/CH:Het:M') || ($VUSID{$keyID} eq 'hom/CH:Het:P'))))){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tC\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tC\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}elsif(exists $PLPID{$keyID} || exists $LOFID{$keyID}){
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\tB3\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\tB3\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}else{
			if(exists $gene2morbid{$keygene}){
				print OUT "morbid\t.\t$VarInfo{$keyID}->{$keygene}\n";
			}else{
				print OUT ".\t.\t$VarInfo{$keyID}->{$keygene}\n";
			}
		}
	}
}
close(OUT);
`tail -n +2 $unsortfltfile | sort -t '\t' -k3,3nr -k10,10V -k4,4nr>> $fltfile && rm $unsortfltfile`;

