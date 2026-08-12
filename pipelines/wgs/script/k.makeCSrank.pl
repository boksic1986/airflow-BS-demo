#!/usr/bin/env perl -w
use strict;
use Cwd;
use FindBin qw($Bin);
use File::Path;
use Getopt::Long;

my ($inRankFile, $outRankFile, $outPedFile, $help);
GetOptions (
		"in_rank|i=s"	    => \$inRankFile,
		"out_rank|o=s"	    => \$outRankFile,
		"ped|p=s"	        => \$outPedFile,
		"help|h"            => \$help
);
if (!defined $inRankFile || !defined $outRankFile ||!defined $outPedFile || defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Copyright: Biosan Dx
	Author: houmin\@biosan.cn	
	Version:   V6.0.5
	Created:   2021-11-12	
	Usage:     perl $0 -i inRankFile -o outRankFile -p outPedFile
	Options:
       -in_rank|i        <file>               input rank file of this batch
       -out_rank|o       <file>               output rank file of couple, with virtual proband
       -ped|p            <file>               output ped file, with virtual proband
       -help|h           <help information>   this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
    exit(1);
}
check_path("08_ped");
my $dir = getcwd;
open PED, ">$outPedFile";
open RANK, ">$outRankFile";
open IN, $inRankFile;
my $header = <IN>;
chomp $header;
print RANK $header."\n";
my @item = split /\t/, $header;
my $index = 0;
my %hashInfo = map{$_=>$index++} @item;
my %relation2sample = ();
my %sample2gender = ();
while (my $line = <IN>) {
	$line =~ s/\[keep\]//g;
	my @arr = split /\t/, $line;
	my $outr = "$dir/08_ped/$arr[$hashInfo{'FamilyID'}]-CS.rank.txt";
	my $outrc = "$dir/08_ped/$arr[$hashInfo{'FamilyID'}]-CS.rankcs.txt";
	my $outp = "$dir/08_ped/$arr[$hashInfo{'FamilyID'}]-CS.ped";
	
	my $outr_1 = "$dir/08_ped/$arr[$hashInfo{'FamilyID'}]_1-CS.rank.txt";
	my $outrc_1 = "$dir/08_ped/$arr[$hashInfo{'FamilyID'}]_1-CS.rankcs.txt";
	my $outp_1 = "$dir/08_ped/$arr[$hashInfo{'FamilyID'}]_1-CS.ped";
	
	open OUTR, ">$outr";
	open OUTRC, ">$outrc";
	open OUTP, ">$outp";
	print OUTR $header."\n";
	print OUTRC $header."\n";
	my (@pedList,@rankList,@rankListcs);
	my (@pedList_1,@rankList_1,@rankListcs_1);
	if ($arr[$hashInfo{"Dad/Spouse"}] eq "1dad" && $arr[$hashInfo{"Mom/Kid"}] eq "2mom" && ($arr[$hashInfo{'Other'}] eq '3wife' || $arr[$hashInfo{'Other'}] eq '4husband')) {
		if ($arr[$hashInfo{'Other'}] eq '3wife'){
			@pedList =(
			[$arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'FamilyID'}].'.kid',$arr[$hashInfo{'ProbandID'}].'.dad',$arr[$hashInfo{'OtherID'}].'.mom',1,2],
			[$arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'ProbandID'}].'.dad',0,0,1,1],
			[$arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'OtherID'}].'.mom',0,0,2,1]);
			@rankList = ($arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'FamilyID'}].'.kid',$arr[$hashInfo{'ProbandID'}].'.dad',$arr[$hashInfo{'OtherID'}].'.mom','.','0proband','1dad','2mom','.','1','1','2','.','2','1','1','.',$arr[$hashInfo{'PhenotypeKeyWords'}],'.','.');
			@rankListcs = ($arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'ProbandID'}],$arr[$hashInfo{'OtherID'}],'.','.','0proband','3wife','.','.','1','2','.','.','1','1','.','.',$arr[$hashInfo{'PhenotypeKeyWords'}],'.','.');
		}elsif ($arr[$hashInfo{'Other'}] eq '4husband'){
			@pedList =(
			[$arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'FamilyID'}].'.kid',$arr[$hashInfo{'OtherID'}].'.dad',$arr[$hashInfo{'ProbandID'}].'.mom',1,2],
			[$arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'OtherID'}].'.dad',0,0,1,1],
			[$arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'ProbandID'}].'.mom',0,0,2,1]);
			@rankList = ($arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'FamilyID'}].'.kid',$arr[$hashInfo{'OtherID'}].'.dad',$arr[$hashInfo{'ProbandID'}].'.mom','.','0proband','1dad','2mom','.','1','1','2','.','2','1','1','.',$arr[$hashInfo{'PhenotypeKeyWords'}],'.','.');
			@rankListcs = ($arr[$hashInfo{'FamilyID'}].'-CS',$arr[$hashInfo{'OtherID'}],$arr[$hashInfo{'ProbandID'}],'.','.','0proband','3wife','.','.','1','2','.','.','1','1','.','.',$arr[$hashInfo{'PhenotypeKeyWords'}],'.','.');
		}
		open OUTR_1, ">$outr_1";
		open OUTRC_1, ">$outrc_1";
		open OUTP_1, ">$outp_1";
		print OUTR_1 $header."\n";
		print OUTRC_1 $header."\n";

		@pedList_1 =(
		[$arr[$hashInfo{"FamilyID"}]."_1-CS",$arr[$hashInfo{"FamilyID"}]."_1.kid",$arr[$hashInfo{"DadID/SpouseID"}].".dad",$arr[$hashInfo{"MomID/KidID"}].".mom",1,2],
		[$arr[$hashInfo{"FamilyID"}]."_1-CS",$arr[$hashInfo{"DadID/SpouseID"}].".dad",0,0,1,1],
		[$arr[$hashInfo{"FamilyID"}]."_1-CS",$arr[$hashInfo{"MomID/KidID"}].".mom",0,0,2,1]);
		@rankList_1 = ($arr[$hashInfo{"FamilyID"}]."_1-CS",$arr[$hashInfo{"FamilyID"}]."_1.kid",$arr[$hashInfo{"DadID/SpouseID"}].".dad",$arr[$hashInfo{"MomID/KidID"}].".mom",".","0proband","1dad","2mom",".","1","1","2",".","2","1","1",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
		@rankListcs_1 = ($arr[$hashInfo{"FamilyID"}]."_1-CS",$arr[$hashInfo{"DadID/SpouseID"}],$arr[$hashInfo{"MomID/KidID"}],".",".","0proband","3wife",".",".","1","2",".",".","1","1",".",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
		map{print OUTP_1 join("\t", @$_)."\n"} @pedList_1;
		print OUTR_1 join("\t",@rankList_1)."\n";
		print OUTRC_1 join("\t",@rankListcs_1)."\n";
		close OUTP_1;
		close OUTR_1;
		close OUTRC_1;
	}elsif ($arr[$hashInfo{"Dad/Spouse"}] eq "3wife") {
		@pedList =(
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"FamilyID"}].".kid",$arr[$hashInfo{"ProbandID"}].".dad",$arr[$hashInfo{"DadID/SpouseID"}].".mom",1,2],
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"ProbandID"}].".dad",0,0,1,1],
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"DadID/SpouseID"}].".mom",0,0,2,1]);
		@rankList = ($arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"FamilyID"}].".kid",$arr[$hashInfo{"ProbandID"}].".dad",$arr[$hashInfo{"DadID/SpouseID"}].".mom",".","0proband","1dad","2mom",".","1","1","2",".","2","1","1",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
		@rankListcs = ($arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"ProbandID"}],$arr[$hashInfo{"DadID/SpouseID"}],".",".","0proband","3wife",".",".","1","2",".",".","1","1",".",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
	}
	elsif ($arr[$hashInfo{"Dad/Spouse"}] eq "4husband") {
		@pedList =(
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"FamilyID"}].".kid",$arr[$hashInfo{"DadID/SpouseID"}].".dad",$arr[$hashInfo{"ProbandID"}].".mom",1,2],
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"DadID/SpouseID"}].".dad",0,0,1,1],
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"ProbandID"}].".mom",0,0,2,1]);
		@rankList = ($arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"FamilyID"}].".kid",$arr[$hashInfo{"DadID/SpouseID"}].".dad",$arr[$hashInfo{"ProbandID"}].".mom",".","0proband","1dad","2mom",".","1","1","2",".","2","1","1",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
		@rankListcs = ($arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"DadID/SpouseID"}],$arr[$hashInfo{"ProbandID"}],".",".","0proband","3wife",".",".","1","2",".",".","1","1",".",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
	}elsif ($arr[$hashInfo{"Dad/Spouse"}] eq "1dad" && $arr[$hashInfo{"Mom/Kid"}] eq "2mom") {
		@pedList =(
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"FamilyID"}].".kid",$arr[$hashInfo{"DadID/SpouseID"}].".dad",$arr[$hashInfo{"MomID/KidID"}].".mom",1,2],
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"DadID/SpouseID"}].".dad",0,0,1,1],
		[$arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"MomID/KidID"}].".mom",0,0,2,1]);
		@rankList = ($arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"FamilyID"}].".kid",$arr[$hashInfo{"DadID/SpouseID"}].".dad",$arr[$hashInfo{"MomID/KidID"}].".mom",".","0proband","1dad","2mom",".","1","1","2",".","2","1","1",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
		@rankListcs = ($arr[$hashInfo{"FamilyID"}]."-CS",$arr[$hashInfo{"DadID/SpouseID"}],$arr[$hashInfo{"MomID/KidID"}],".",".","0proband","3wife",".",".","1","2",".",".","1","1",".",".",$arr[$hashInfo{"PhenotypeKeyWords"}],".",".");
	}
	if (@pedList){
		map{print PED join("\t", @$_)."\n"} @pedList;
		print RANK join("\t",@rankList)."\n";
		map{print OUTP join("\t", @$_)."\n"} @pedList;
		print OUTR join("\t",@rankList)."\n";
		print OUTRC join("\t",@rankListcs)."\n";
		close OUTP;
		close OUTR;
		close OUTRC;
	}
	if (@pedList_1){
		map{print PED join("\t", @$_)."\n"} @pedList_1;
		print RANK join("\t",@rankList_1)."\n";
	}
}
close IN;
close RANK;
close PED;


sub check_path{
	my ($path) = @_;
	if (!-d $path) {
		mkpath($path);
	}
}
