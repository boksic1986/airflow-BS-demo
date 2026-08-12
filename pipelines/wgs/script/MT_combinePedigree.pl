#!/usr/bin/env perl -w
use strict;
use Getopt::Long;

my ($rankFile, $help);
GetOptions (
		"rank=s"   => \$rankFile,
		"h|help"  => \$help,
);

if (!defined $rankFile || defined $help) {
	my $usage =<< "Usage";
---------------------------------------------------------------------------------------------------
	Usage:     perl $0 -rank batch.rank.txt
	Options:
		-rank		[file]	batch.rank.txt
		-h|help				this help information
---------------------------------------------------------------------------------------------------
Usage
	print $usage;
	exit(1);
}

open RANK, $rankFile or die $!;
chomp(my $header = <RANK>);
my @title = split /\t/, $header;
my @soloTitle = ('Gene', 'VarID', 'Position', 'Nucleotide', 'AaChange', 'Pathogenicity', 'EvidenceList', 'Evidence', 'Het/Hom', 'VAF', 'Depth', 'LocalSig', 'ClinvarSig', 'HmtvarSig', 'ClinvarID', 'GeneType', 'PM2/BS1/BA1', 'PS1/PM5', 'PP3/BP4', 'ClinvarStatus', 'ClinvarCondition', 'MitomapPubmed', 'MitomapDisease', 'MitomapStatus', 'HmtvarScore', 'ApogeeScore', 'ApogeePred', 'MitotipScore', 'MitotipQuartile', 'MafLocalHet', 'MafLocalHom', 'MafGnomADHet', 'MafGnomADHom', 'MafHealthyAll', 'MafPatientsAll', 'MafHealthyAsia', 'MafPatientsAsia', 'MafMitomap', 'MutPred_Prediction', 'MutPred_Probability', 'Panther_Prediction', 'Panther_Probability', 'PhDSNP_Prediction', 'PhDSNP_Probability', 'SNPsGO_Prediction', 'SNPsGO_Probability', 'Polyphen2HumDiv_Prediction', 'Polyphen2HumDiv_Probability', 'Polyphen2HumVar_Prediction', 'Polyphen2HumVar_Probability', 'HGFL');
my @outTitle = ('Gene', 'VarID', 'Position', 'Nucleotide', 'AaChange', 'Pathogenicity', 'EvidenceList', 'Evidence', 'Het/Hom', 'VAF', 'Depth', 'Mom-Het/Hom', 'Mom-VAF', 'Mom-Depth', 'Other-Het/Hom', 'Other-VAF', 'Other-Depth', 'LocalSig', 'ClinvarSig', 'HmtvarSig', 'ClinvarID', 'GeneType', 'PM2/BS1/BA1', 'PS1/PM5', 'PP3/BP4', 'ClinvarStatus', 'ClinvarCondition', 'MitomapPubmed', 'MitomapDisease', 'MitomapStatus', 'HmtvarScore', 'ApogeeScore', 'ApogeePred', 'MitotipScore', 'MitotipQuartile', 'MafLocalHet', 'MafLocalHom', 'MafGnomADHet', 'MafGnomADHom', 'MafHealthyAll', 'MafPatientsAll', 'MafHealthyAsia', 'MafPatientsAsia', 'MafMitomap', 'MutPred_Prediction', 'MutPred_Probability', 'Panther_Prediction', 'Panther_Probability', 'PhDSNP_Prediction', 'PhDSNP_Probability', 'SNPsGO_Prediction', 'SNPsGO_Probability', 'Polyphen2HumDiv_Prediction', 'Polyphen2HumDiv_Probability', 'Polyphen2HumVar_Prediction', 'Polyphen2HumVar_Probability', 'HGFL');
while (my $s=<RANK>) {
	chomp $s;
	$s =~ s/\[keep\]//;
	my @item=split /\t/,$s;
	my %h = map{$title[$_]=>$item[$_]}(0..$#title);
	if ($h{'Mom/Kid'} =~ /2mom/ || $h{'Dad/Spouse'} =~ /3wife/ || $h{'Dad/Spouse'} =~ /4husband/){
		my $probandMT = '11_MT/'.$h{'ProbandID'}.'.mity.flt.txt';
		my $outMT = '11_MT/'.$h{'FamilyID'}.'.mity.flt.txt';
		open OUT, ">$outMT";
		print OUT join("\t", @outTitle)."\n";
		open PRO, $probandMT or die $!;
		<PRO>;
		my %var2info;
		my %var2gt;
		while (my $line = <PRO>) {
			chomp $line;
			my @arr = split /\t/, $line;
			my %h = map{$soloTitle[$_]=>$arr[$_]}(0..$#soloTitle);
			@{$var2info{$h{'VarID'}}{'proband'}} = (@arr[0..7],@arr[11..$#arr]);
			$var2gt{$h{'VarID'}}{'proband'} = join("\t",($h{'Het/Hom'}, $h{'VAF'}, $h{'Depth'}));
		}
		close PRO;
		my ($momMT, $otherMT);
		if ($h{'Mom/Kid'} =~ /2mom/){
			$momMT = '11_MT/'.$h{'MomID/KidID'}.'.mity.flt.txt';
			open MOM, $momMT or die $!;
			<MOM>;
			while (my $line = <MOM>) {
				chomp $line;
				my @arr = split /\t/, $line;
				my %h = map{$soloTitle[$_]=>$arr[$_]}(0..$#soloTitle);
				@{$var2info{$h{'VarID'}}{'mom'}} = (@arr[0..7],@arr[11..$#arr]);
				$var2gt{$h{'VarID'}}{'mom'} = join("\t",($h{'Het/Hom'}, $h{'VAF'}, $h{'Depth'}));
			}
			close MOM;
		}

		if ($h{'Dad/Spouse'} =~ /3wife/ || $h{'Dad/Spouse'} =~ /4husband/){
			my $otherMT = '11_MT/'.$h{'DadID/SpouseID'}.'.mity.flt.txt';
			open OTHER, $otherMT or die $!;
			<OTHER>;
			while (my $line = <OTHER>) {
				chomp $line;
				my @arr = split /\t/, $line;
				my %h = map{$soloTitle[$_]=>$arr[$_]}(0..$#soloTitle);
				@{$var2info{$h{'VarID'}}{'other'}} = (@arr[0..7],@arr[11..$#arr]);
				$var2gt{$h{'VarID'}}{'other'} = join("\t",($h{'Het/Hom'}, $h{'VAF'}, $h{'Depth'}));
			}
			close OTHER;
		}

		foreach my $var (sort keys(%var2info)) {
			my $probandGT = join("\t", ('.', '.', '.'));
			my $momGT = join("\t", ('.', '.', '.'));
			my $otherGT = join("\t", ('.', '.', '.'));
			my @output;
			if (exists($var2info{$var}{"proband"})) {
				$probandGT = $var2gt{$var}{"proband"};
				@output = @{$var2info{$var}{"proband"}}
			}
			if (exists($var2info{$var}{"mom"})) {
				$momGT = $var2gt{$var}{"mom"};
				@output = @{$var2info{$var}{"mom"}};
			}
			if (exists($var2info{$var}{"other"})) {
				$otherGT = $var2gt{$var}{"other"};
				@output = @{$var2info{$var}{"other"}};
			}
			print OUT join("\t", (@output[0..7], $probandGT, $momGT, $otherGT, @output[8..$#output]))."\n";
		}
		close OUT;
	}
}
close RANK;