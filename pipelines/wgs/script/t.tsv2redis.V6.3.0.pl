#!/usr/bin/perl -w
use strict;
use Getopt::Long;
use Data::Dumper;
use FindBin qw($Bin $Script);
use FileHandle;
use List::Util qw(first max maxstr min minstr reduce shuffle sum);
use List::MoreUtils qw(first_index);
use Cwd qw(abs_path getcwd realpath);
use Unicode::UTF8simple;
use Encode;
use RedisDB;
#update: 20220614, 切换新系统，将redis从172.17.61.200:6479改为172.17.61.200:6378
#update: 20221020, WGS新建新系统，将redis从172.17.61.200:6378改为172.17.61.200:6481
#update: 20230317, WGS新建新系统，将redis从172.17.61.200:6481改为172.17.100.93:6481
#update: 20230904, 上传hg38结果，SNV新增sampleid-ReferenceV字段，CNV新增ReferenceV字段
#update: 20260331, WGS SNV 携筛，将redis从172.17.100.93:6483改为172.17.100.107:6483
my ($sampleID,$snvFile,$csFile,$cnvFile,$svFile,$mtFile,$help);
GetOptions(
			"h|?" => \$help,
			"ID=s" => \$sampleID,
			"snv:s" => \$snvFile,
			"cs:s" => \$csFile,
			"cnv:s" => \$cnvFile,
			"sv:s" => \$svFile,
			"mt:s"  => \$mtFile
);
if (!defined $sampleID || (!defined $snvFile && !defined $csFile && !defined $cnvFile && !defined $svFile && !defined $mtFile) || defined $help){
	my $usage = << "Usage";
---------------------------------------------------------------------------------------------------
	Usage1:	 perl $0 -ID probandID -snv sample-panel.flt.tsv
	Usage2:	 perl $0 -ID probandID -cs pedID-probandID-CS.markCS.flt.tsv
	Usage3:	 perl $0 -ID probandID -cnv sample-panel.CNV.tsv
	Usage4:	 perl $0 -ID probandID -mt sample-panel.MT.tsv
	Usage5:	 perl $0 -ID probandID -sv sample-panel.SV.sort.tsv
	-ID			<sampleID>			required, eg. WES2408001
	-snv		<snvFile>			optional, eg. WES2408001-WGS.flt.tsv, JX24G00035093_WES2408001.flt.tsv
	-cs			<csFile>			eg. JX24G00035093_WES2408001-CS.markCS.flt.tsv
	-cnv		<cnvFile>			optional, eg. WES2408001-WGS.CNV.tsv
	-sv			<svFile>			optional, eg. WES2408001-WGS.SV.sort.tsv
	-mt			<mtFile>			optional, eg. WES2408001-WGS.MT.tsv
	-h			<help information>	this help information
---------------------------------------------------------------------------------------------------
Usage
	print STDERR $usage;
	exit;
}

if (defined $snvFile){load_SNV($snvFile, $sampleID);}
if (defined $csFile){load_CS_SNV($csFile, $sampleID);}
if (defined $cnvFile){load_CNV($cnvFile, $sampleID);}
if (defined $mtFile){load_MT($mtFile, $sampleID);}
if (defined $svFile){load_SV($svFile, $sampleID);}

sub load_SNV{
	my ($snvFile, $sampleID) = @_;
	my $redis = RedisDB -> new(host => '172.17.100.93', port => 6481, password => 'BioSan');
	$redis -> zadd("SampleList",sub_format_date(localtime(time())),$sampleID);
	open IN, $snvFile || die "Can't open $snvFile\n";
	my $header = <IN>;
	chomp $header;
	my @title = split /\t/, $header;
	# 去除列名中的 _hg38
	@title = map { s/_hg38//g; $_ } @title;

	my @subTitle = ("GeneRankScore","VarRankScore","TagGenetic","TagKeyWords","Proband_Zygosity","Proband_Format","Proband_VAF","Dad_Zygosity","Dad_Format","Dad_VAF","Mom_Zygosity","Mom_Format","Mom_VAF","Other_Zygosity","Other_Format","Other_VAF");
	foreach my $subEle (@subTitle) {
		my $index = first_index {$_ eq $subEle && $_!~/$sampleID/} @title;
		if($index >= 0){
			splice(@title, $index, 1, $sampleID."-".$title[$index]);
		}
	}
	while (my $line = <IN>) {
		chomp $line;
		my @item = split /\t/, $line;
		my %hash = map {$title[$_] => $item[$_]} (0..$#item);
		$hash{"VarID"} =~ s/chr//;
		$hash{"VarID_hg19"} =~ s/chr//;
		my $referenceV=$sampleID."-ReferenceV";
		$hash{$referenceV} ="hg38";
		my @varID = split(/-/, $hash{"VarID"});
		my $ID = sprintf("%s-%09d-%s-%s", $varID[0], $varID[1], $varID[2], $varID[3]);
		$redis->hmset($ID, %hash);
		$redis->zrem($sampleID, $ID);
		$redis->zrem($sampleID, $hash{"VarID"}.'-000000000--');
		$redis->zadd($sampleID, 0, $ID);
	}
	close IN;
	print STDERR "Done load $snvFile\n";
}

sub load_CS_SNV{
	my ($csFile,$sampleID) = @_;
	my $redis = RedisDB -> new(host => '172.17.100.107', port => 6483, password => 'BioSan');
	$redis -> zadd("SampleList",sub_format_date(localtime(time())),$sampleID);
	open IN, $csFile || die "Can't open $csFile\n";
	my $header = <IN>;
	chomp $header;
	my @title = split /\t/, $header;
	# 去除列名中的 _hg38
	@title = map { s/_hg38//g; $_ } @title;

	my @subTitle = ("CS_Class","GeneRankScore","VarRankScore","TagGenetic","TagKeyWords","Proband_Zygosity","Proband_Format","Proband_VAF","Dad_Zygosity","Dad_Format","Dad_VAF","Mom_Zygosity","Mom_Format","Mom_VAF","Other_Zygosity","Other_Format","Other_VAF");
	foreach my $subEle (@subTitle) {
		my $index = first_index {$_ eq $subEle && $_!~/$sampleID/} @title;
		if($index >= 0){
			splice(@title, $index, 1, $sampleID."-".$title[$index]);
		}
	}
	while (my $line = <IN>) {
		chomp $line;
		my @item = split /\t/, $line;
		my %hash = map {$title[$_] => $item[$_]} (0..$#item);
		$hash{"VarID"} =~ s/chr//;
		$hash{"VarID_hg19"} =~ s/chr//;
		my $referenceV=$sampleID."-ReferenceV";
		$hash{$referenceV} ="hg38";
		my @varID = split(/-/, $hash{"VarID"});
		my $ID = sprintf("%s-%09d-%s-%s", $varID[0], $varID[1], $varID[2], $varID[3]);
		$redis->hmset($ID, %hash);
		$redis->zrem($sampleID, $ID);
		$redis->zrem($sampleID, $hash{"VarID"}.'-000000000--');
		$redis->zadd($sampleID, 0, $ID);
	}
	close IN;
	print STDERR "Done load $csFile\n";
}

sub load_CNV{
	my ($cnvFile, $sampleID) = @_;
	my $redis = RedisDB->new(host => '172.17.100.93', port => 6481, password => 'BioSan');
	open IN, $cnvFile || die "Can't open $cnvFile\n";
	chomp(my $header = <IN>);
	my @title = split /\t/, $header;
	# 去除列名中的 _hg38
	@title = map { s/_hg38//g; $_ } @title;

	my @unit = ();
	my $score = 0;
	while (my $line = <IN>) {
		chomp $line;
        $score++;
		@unit=split /\t/, $line;
		my %hash=map {$title[$_]=>$unit[$_]} (3..$#unit);
		$hash{'CNV_ID'} = $unit[5]."_".$unit[7];
		$hash{'CNV_ID'} =~ s/chr//i;
		$hash{'CNV_ID'} =~ tr/:-/__/;
		$hash{'ReferenceV'} ="hg38";
		my ($chr,$start,$end) = (split/_/,$hash{'CNV_ID'})[0,1,2];
		my $ID = sprintf("%s-%s-%09d-%09d-%s", $sampleID, $chr, $start, $end, $hash{'变异类型'});
        $hash{"preservedPathogenicScoreForSort"}=$score;
		$redis->hdel($ID,keys(%hash));
		$redis->hmset($ID,%hash);
		$redis->zrem($sampleID."-CNV",$ID);
		$redis->zadd($sampleID."-CNV",0,$ID);
	}
	close IN;
	print STDERR "Done load $cnvFile\n";
}

sub load_MT{
	my ($mtFile, $sampleID)=@_;
	my $redis = RedisDB->new(host => '172.17.100.93', port => 6481, password => 'BioSan');
	$redis->zadd("SampleList",sub_format_date(localtime(time())),$sampleID);
	open IN, $mtFile || die "Can't open $mtFile\n";
	chomp(my $header = <IN>);
	my @title = split /\t/, $header;
	# 去除列名中的 _hg38
	# @title = map { s/_hg38//g; $_ } @title;

	my @subTitle = ('Het/Hom','VAF','Depth','Mom-Het/Hom', 'Mom-VAF', 'Mom-Depth', 'Other-Het/Hom', 'Other-VAF', 'Other-Depth');
	foreach my $subEle (@subTitle) {
		my $index = first_index {$_ eq $subEle} @title;
		if($index >= 0){
			splice(@title, $index, 1, $sampleID."-".$title[$index]);
		}
	}
	my @unit=();
	while (my $line = <IN>) {
		chomp $line;
		@unit=split /\t/, $line;
		my %hash=map {$title[$_]=>$unit[$_]} (0..$#unit);
		$hash{"VarID"}=~s/^chr//;
		my @varID=split(/-/,$hash{"VarID"});
		my $ID=sprintf("%s-%05d-%s-%s",$varID[0],$varID[1],$varID[2],$varID[3]);
		$redis->hmset($ID, %hash);
		$redis->zrem($sampleID."-MT",$ID);
		$redis->zrem($sampleID."-MT",$hash{"VarID"}.'-00000--');
		$redis->zadd($sampleID."-MT",0,$ID);
	}
	close IN;
	print STDERR "Done load $mtFile\n";
}

sub load_SV {
	my ($svFile, $sampleID) = @_;
	my $redis = RedisDB->new(host => '172.17.100.93', port => 6481, password => 'BioSan');
	my %hash;
	$hash{'ReferenceV'} = "hg38";
	open SV, $svFile || die "Can't open $svFile\n";
	chomp(my $header = <SV>);
	my @title = split /\t/, $header;
	# 去除列名中的 _hg38
	# @title = map { s/_hg38//g; $_ } @title;

	while (my $line = <SV>) {
		chomp $line;
		my @arr = split /\t/, $line;
		my %h = map{$title[$_]=>$arr[$_]}(0..$#title);
		my ($chr1, $start1, $end1) = split(/:|-/, $h{'染色体位置'});
		my ($chr2, $start2, $end2) = split(/:|-/, $h{'染色体位置2'});
		my $ID;
		if ($h{'SVTYPE'} eq "BND") {
			$ID = sprintf("%s-%s-%09d-%09d-%s-%09d-%09d-%s", $sampleID, $chr1, $start1, $end1, $chr2, $start2, $end2, $h{'SVTYPE'});
		} else {
			$ID = sprintf("%s-%s-%09d-%09d-.-%s", $sampleID, $chr1, $start1, $end1, $h{'SVTYPE'});
		}
		$redis->hdel($ID, 'ReferenceV');
		$redis->hmset($ID, %hash);
		$redis->zrem($sampleID."-SV", $ID);
		$redis->zadd($sampleID."-SV", 0, $ID);
	}
	close SV;
	print STDERR "Done load $svFile\n";
}

sub sub_format_date {
	my($sec, $min, $hour, $day, $mon, $year, $wday, $yday, $isdst) = @_;
	return sprintf("%4d%02d%02d%02d", $year+1900, $mon+1, $day,$hour);
}
