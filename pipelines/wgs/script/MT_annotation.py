#!/bi/software/Anaconda3/bin/python
import argparse
import re
from collections import defaultdict
import pandas as pd

def readCfrm(inputfile):
    mitomapCfrmDict = defaultdict(lambda: defaultdict(lambda: 0))
    df = pd.read_csv(inputfile, sep='\t', header=0)
    mitomapCfrmDict = defaultdict(lambda: defaultdict(list))
    for index, row in df.iterrows():
        type = row['Locus_Type']
        position = row['Position']
        value = f"{row['Allele']}:p.{row['aaChange/RNA']}"
        if '>' in row['Allele'] and '[P]' in row['Status']:
            if row['Position'] in mitomapCfrmDict[type]:
                mitomapCfrmDict[type][position].append(value)
            else:
                mitomapCfrmDict[type][position] = [value]
    mitomapCfrmDict = {k: {kk: '|'.join(vv) for kk, vv in v.items()} for k, v in mitomapCfrmDict.items()}
    return mitomapCfrmDict

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--cfrmFile", help = "mitomap cfrm file", required = True)
    parser.add_argument("--hmtnoteCsv", help = "hmtnote tools out csv file", required = True)
    parser.add_argument("--mityCsv", help = "mity report out csv file", required = True)
    parser.add_argument("--output", default = "test", help = "Output txt file", required = True)
    args = parser.parse_args()
    cfrmFile = args.cfrmFile
    hmtDf = pd.read_csv(args.hmtnoteCsv)
    mityDf = pd.read_csv(args.mityCsv)
    fltFile = open(args.output, 'w')
    mitomapCfrmDict = readCfrm(cfrmFile)
    head = (
        'Gene', 'VarID', 'Position', 'Nucleotide', 'AaChange', 'Pathogenicity', 'EvidenceList', 'Evidence', 'Het/Hom', 'VAF', 'Depth', 'LocalSig', 'ClinvarSig', 'HmtvarSig', "ClinvarID", 'GeneType',
        'PM2/BS1/BA1', 'PS1/PM5', 'PP3/BP4', 'ClinvarStatus', 'ClinvarCondition', 'MitomapPubmed', 'MitomapDisease', 'MitomapStatus', 'HmtvarScore', 'ApogeeScore', 'ApogeePred',
        'MitotipScore', 'MitotipQuartile', 'MafLocalHet', 'MafLocalHom', 'MafGnomADHet', 'MafGnomADHom', 'MafHealthyAll', 'MafPatientsAll', 'MafHealthyAsia', 'MafPatientsAsia', 'MafMitomap', 'MutPred_Prediction', 'MutPred_Probability', 'Panther_Prediction',
        'Panther_Probability', 'PhDSNP_Prediction', 'PhDSNP_Probability', 'SNPsGO_Prediction', 'SNPsGO_Probability', 'Polyphen2HumDiv_Prediction', 'Polyphen2HumDiv_Probability',
        'Polyphen2HumVar_Prediction', 'Polyphen2HumVar_Probability', 'HGFL')
    fltFile.write('\t'.join(head) + '\n')
    mityDf['var_ID'] = mityDf['CHR'] + '-' + mityDf['POS'].map(str) + '-' + mityDf['REF'] + '-' + mityDf['ALT']
    mityDf.set_index('var_ID', drop = False, inplace = True)
    for index, row in hmtDf.iterrows():
        CHROM = row['CHROM']
        POS = int(row['POS'])
        pos = POS
        ID = row['ID']
        REF = row['REF']
        ALT = row['ALT']
        var_ID = f'{CHROM}-{str(POS)}-{REF}-{ALT}'
        gene = mityDf.at[var_ID, 'gene/locus']
        geneType = mityDf.at[var_ID, 'gene/locus description']
        varPos = f'{CHROM}:{str(POS)}'
        nucleotide = f'm.{str(POS)}{REF}>{ALT}'
        if len(REF) == 2:
            pos = POS + 1
            nucleotide = f'm.{str(pos)}del'
            varPos = f'{CHROM}:{str(pos)}'
        elif len(REF) > 2:
            posStart = POS + 1
            posEnd = POS + 1 + (len(REF) - 2)
            pos = str(posStart) + '_' + str(posEnd)
            nucleotide = 'm.' + str(pos) + 'del'
            varPos = CHROM + ":" + str(pos)
        elif len(ALT) == 2:
            pos = POS + 1
            newseq = ALT.replace(REF, '', 1)
            nucleotide = 'm.' + str(pos) + 'ins' + newseq
            varPos = CHROM + ":" + str(pos)
        elif len(ALT) > 2:
            posStart = POS + 1
            newseq = ALT.replace(REF, '', 1)
            posEnd = posStart + len(newseq) - 1
            pos = str(posStart) + '_' + str(posEnd)
            nucleotide = 'm.' + str(pos) + 'ins' + newseq
            varPos = CHROM + ":" + str(pos)
        AlleleFreqH = 0 if row['AlleleFreqH'] == '.' else row['AlleleFreqH']
        AlleleFreqP = 0 if row['AlleleFreqP'] == '.' else row['AlleleFreqP']
        AlleleFreqH_AS = 0 if row['AlleleFreqH_AS'] == '.' else row['AlleleFreqH_AS']
        gt = 'Hom'
        vaf = round((row['SAF'] + row['SAR']) / row['DP'], 4)
        if vaf < 0.95:
            gt = 'Het'

        AaChange = row['AaChange']
        if row['AaChange'] != '.':
            AaChange = 'p.' + AaChange
            AaChange = AaChange.replace('X','*')
        PM5 = 'PM5:'
        PS1 = 'PS1:'
        if geneType == 'Mt_tRNA':
            if '_' in str(pos):
                poskey = str(pos).split('_')[0]
            else:
                poskey = str(pos)
            if poskey in mitomapCfrmDict['tRNA']:
                pathognicVlist = mitomapCfrmDict['tRNA'][poskey].split('|')
                for pathognicV in pathognicVlist:
                    dbHGVSc, dbHGVSp = pathognicV.split(':')
                    dbpos = re.findall('\d+', dbHGVSc)[0]
                    dbREF = dbHGVSc.replace(('m.' + str(dbpos)), '').split('>')[0]
                    dbALT = dbHGVSc.replace(('m.' + str(dbpos)), '').split('>')[1]
                    if REF == dbREF and ALT != dbALT:
                        PM5 = PM5 + '|' + pathognicV
        elif geneType == 'protein_coding':
            if '_' in str(pos):
                poskey = str(pos).split('_')[0]
            else:
                poskey = str(pos)
            if poskey in mitomapCfrmDict['Coding']:
                pathognicVlist = mitomapCfrmDict['Coding'][poskey].split('|')
                for pathognicV in pathognicVlist:
                    dbHGVSc, dbHGVSp = pathognicV.split(':')
                    dbpos = re.findall('\d+', dbHGVSc)[0]
                    dbREF = dbHGVSc.replace(('m.' + str(dbpos)), '').split('>')[0]
                    dbALT = dbHGVSc.replace(('m.' + str(dbpos)), '').split('>')[1]
                    if REF == dbREF and ALT != dbALT:
                        PM5 = PM5 + '|' + pathognicV
                    if REF == dbREF and ALT != dbALT and dbHGVSp == AaChange:
                        PS1 = PS1 + '|' + pathognicV
        prediction = ''
        APOGEE = row['APOGEE']
        Pathogenicity = row['Pathogenicity']
        if geneType == 'Mt_tRNA' and row['MitotipScore'] !='.' and row['DiseaseScore'] !='.':
            if float(row['MitotipScore']) >= 12.66 and float(row['DiseaseScore']) >= 0.35:
                prediction = f"PP3:MitotipScore={str(row['MitotipScore'])};HmtvarScore={str(row['DiseaseScore'])}"
            elif float(row['MitotipScore']) < 12.66 and float(row['DiseaseScore']) < 0.35:
                prediction = f"BP4:MitotipScore={str(row['MitotipScore'])};HmtvarScore={str(row['DiseaseScore'])}"
        elif geneType == 'protein_coding':
            if APOGEE == 'Pathogenic':
                prediction = 'PP3:APOGEE=' + str(APOGEE)
            elif APOGEE == 'Neutral':
                prediction = 'BP4:APOGEE=' + str(APOGEE)
        maf = ''
        HGFL = row['HGFL']
        HGFL = HGFL.replace('%3A', ':')
        if re.findall('\d+', HGFL):
            maf = 'BA1'
        elif 0.005 <= float(AlleleFreqH) < 0.01 or 0.005 <= float(AlleleFreqH_AS) < 0.01:
            maf = 'BS1'
        elif float(AlleleFreqH) < 0.00002 and float(AlleleFreqH_AS) < 0.00002:
            maf = 'PM2'
        row['Evidence'] = row['Evidence'].replace('%3A%3A', ';')
        row['Evidence'] = row['Evidence'].replace('%3A', ':')
        row['Evidence'] = row['Evidence'].replace('&&', ' | ')
        row['Evidence'] = row['Evidence'].replace('$$', '=')
        row['Evidence'] = row['Evidence'].replace('##', '|')
        row['Evidence'] = row['Evidence'].replace('&', ',')
        evidence = f"ClinVar={row['CLNSIG']}|{maf}:MAF_Healthy_All={str(row['AlleleFreqH']) };MAF_Patients_All={str(row['AlleleFreqP'])};MAF_Healthy_Asia={str(row['AlleleFreqH_AS'])};MAF_Patients_Asia={str(row['AlleleFreqP_AS'])}|{prediction}|{PS1}|{PM5}"
        if row['Evidence'] != '.':
            evidence = row['Evidence']
        row['AC_het'] = str(row['AC_het']).replace('-1','.')
        row['AC_hom'] = str(row['AC_hom']).replace('-1','.')
        row['AN'] = str(row['AN']).replace('-1','.')
        gnomADhet = str(row['AC_het']) + '/' + str(row['AN'])
        gnomADhom = str(row['AC_hom']) + '/' + str(row['AN'])
        gnomADhet = gnomADhet.replace('./.','')
        gnomADhom = gnomADhom.replace('./.','')

        outline = '\t'.join([gene, var_ID, varPos, nucleotide, str(AaChange), row['LocalSig'], row['EvidenceList'], evidence, gt, str(vaf), str(row['DP']), row['LocalSig'], row['CLNSIG'], Pathogenicity, row['ClinvarID'], geneType, maf, PM5+';'+PS1, prediction, str(row['CLNREVSTAT']), str(row['CLNDN']), str(row['PubmedIDs']), str(row['Disease']), str(row['DiseaseStatus']), str(row['DiseaseScore']), str(row['APOGEE_score']), str(row['APOGEE']), str(row['MitotipScore']), str(row['MitotipQuartile']), str(row['FreqHet']),str(row['FreqHom']),gnomADhet,gnomADhom,str(row['AlleleFreqH']), str(row['AlleleFreqP']), str(row['AlleleFreqH_AS']), str(row['AlleleFreqP_AS']), str(row['AF']), str(row['MutPred_Prediction']), str(row['MutPred_Probability']), str(row['Panther_Prediction']), str(row['Panther_Probability']), str(row['PhDSNP_Prediction']), str(row['PhDSNP_Probability']), str(row['SNPsGO_Prediction']), str(row['SNPsGO_Probability']), str(row['Polyphen2HumDiv_Prediction']), str(row['Polyphen2HumDiv_Probability']), str(row['Polyphen2HumVar_Prediction']), str(row['Polyphen2HumVar_Probability']), str(HGFL)])
        fltFile.write(outline + '\n')
    fltFile.close()
