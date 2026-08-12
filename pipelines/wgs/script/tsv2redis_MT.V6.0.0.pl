#!/usr/bin/env perl
# 
# Copyright (c)   BioSan
# Writer:         xuxiong <xuxiong19880610@163.com>
# Program Date:   2020.07.22
# Modifier:       xuxiong <xuxiong19880610@163.com>
# Last Modified:  2020.07.22
#update: 20221020, WGS新建新系统，将redis从172.17.61.200:6378改为172.17.61.200:6481
my $ver="0.0.1";

use Getopt::Long;
use Data::Dumper;
use FindBin qw($Bin $Script);
use FileHandle;
use File::Basename qw(basename dirname);
use List::Util qw(first max maxstr min minstr reduce shuffle sum);
use List::MoreUtils qw(first_index);
use Cwd qw(abs_path getcwd realpath);
use Unicode::UTF8simple;
use Encode;
use utf8;
use RedisDB;

my ($infile);
GetOptions(
            "help|?" =>\&USAGE,
            "i:s"=>\$infile,
            ) or &USAGE;
&USAGE unless ($infile) ;
###############Time_start#############################
my $Time_Start;
$Time_Start = sub_format_datetime(localtime(time()));
print STDERR "\nStart Time :[$Time_Start]\n\n";
######################################################
$infile||="-";
print STDERR abs_path($infile),"\n";
load_vcf($infile);

sub load_vcf{
	my ($infile)=@_;
	my $redis = RedisDB->new(host => '172.17.61.99', port => 6481,password => 'BioSan');
	my @title=();
	my $SampleName="";
	my $baseInfile=basename($infile);
	if($baseInfile=~/(.*)-WGS\.mity\.flt\.txt/){
		$SampleName=$1;
		print STDERR $SampleName,"\n";
		$redis->zadd("SampleList",sub_format_date(localtime(time())),$SampleName);
	}
	open IN, $infile || die "Can't open $infile\n";
	chomp(my $header = <IN>);
	my @title = split /\t/, $header;
	my @subTitle = ("Het/Hom","VAF","Depth");
    foreach my $subEle (@subTitle) {
		my $index = first_index {$_ eq $subEle && $_!~/$SampleName/} @title;
		if($index >= 0){
			splice(@title, $index, 1, $SampleName."-".$title[$index]);
		}
	}

	my @unit=();
	while (my $line = <IN>) {
		chomp $line;
		@unit=split /\t/, $line;
		@unit= map {decode("utf-8",$_)} @unit;
		my %hash=map {$title[$_]=>$unit[$_]} (0..$#unit);
		$hash{"VarID"}=~s/^chr//;
		my @varID=split(/-/,$hash{"VarID"});
		my $ID=sprintf("%s-%05d-%s-%s",$varID[0],$varID[1],$varID[2],$varID[3]);
		$redis->hmset($ID, %hash);
		$redis->zrem($SampleName."-MT",$ID);
		$redis->zrem($SampleName."-MT",$hash{"VarID"}.'-00000--');
		$redis->zadd($SampleName."-MT",0,$ID);
	}
	close IN;
	print STDERR "Done load $infile\n";
}

###############Time_end###########
my $Time_End;
$Time_End = sub_format_datetime(localtime(time()));
print STDERR "\nEnd Time :[$Time_End]\n\n";

###############Sub_format_datetime
sub sub_format_date {
	my($sec, $min, $hour, $day, $mon, $year, $wday, $yday, $isdst) = @_;
	return sprintf("%4d%02d%02d%02d", $year+1900, $mon+1, $day,$hour);
}
sub sub_format_datetime {#Time calculation subroutine
    my($sec, $min, $hour, $day, $mon, $year, $wday, $yday, $isdst) = @_;
    $wday = $yday = $isdst = 0;
    sprintf("%4d-%02d-%02d %02d:%02d:%02d", $year+1900, $mon+1, $day, $hour, $min, $sec);
}

sub USAGE {#
    my $usage=<<"USAGE";
Program: $0
Version: $ver
Contact: XiongXu <xuxiong\@yearth.cn> <xuxiong19880610\@163.com>

Example:
  perl $0 
Description:
  This program is used for load vcf file into redis database
Usage:
  -i                    infile                                 required
  -g                    flag(add genotyping info or not)       option

USAGE
    print STDERR $usage;
    exit;
}
