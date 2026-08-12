#!/usr/bin/env Rscript
library(argparser, quietly=TRUE);
library(futile.logger, quietly=TRUE);
library(data.table);
library(plyr, quietly=TRUE);
suppressPackageStartupMessages(library(dplyr));
library(maptools, quietly=TRUE);
library("polyCub")
#gpclibPermit();
library(Cairo, quietly=TRUE);
library(ggplot2,quietly=TRUE)
library(reshape2,quietly=TRUE)
library(ggnewscale)
library(ggh4x,quietly=TRUE)
library(parallel,quietly=TRUE)
library(DNAcopy,quietly=TRUE)
library(cghFLasso,quietly=TRUE)
library(bams,quietly=TRUE)
library(writexl,quietly=TRUE)
library(ggplotify)
suppressPackageStartupMessages(library(ggcorrplot))
suppressPackageStartupMessages(library(gplots,quietly=TRUE))
suppressPackageStartupMessages(library(factoextra))
options(bitmapType='cairo')
options(scipen=999)

p = arg_parser('CNVetti plotting') %>%
    add_argument('--inputBed', help='input GCcorrected Bed File.',type="character") %>%
    add_argument('--cytoFile', help='CytoBand File.',type="character") %>%
    add_argument('--fastqCount', help='statistics of fastq[.gz] file[s].', type="character",default="fastq_count.tsv") %>%
    add_argument('--Disease', help='CNV disease File.', type="character", default="/bi/8.xuxiong/work/CNVseq/CNVdb/Decipher.bed") %>%
    add_argument('--Polymorphism', help='CNV Polymorphism File.', type="character", default="/bi/8.xuxiong/work/CNVseq/Stringent.Gain+Loss.hg19.2015-02-03.txt") %>%
    add_argument('--sexCutoff', help='sexCutoff, YRC/(Sum of Autosomal RC)', type="double") %>%
    add_argument('--refData', help='pre-computed reference mean median sd RData',type="character") %>%
    add_argument('--refSexData', help='pre-computed reference gender file',type="character") %>%
    add_argument('--absCtrls', help='absCtrls or include current samples as ctrls',type="logical", flag=TRUE) %>%
    add_argument('--corrThreshold', help='correlation Threshold',type="double",default=0.78) %>%
    add_argument('--minSamples', help='minimum samples as ctrls',type="integer",default=20) %>%
    add_argument('--maxSamples', help='maximum samples as ctrls',type="integer",default=40) %>%
    add_argument('--corrQC', help='corrQC.', type="character",default="corrQC.tsv") %>%
    add_argument('--HLAstart', help='Lower bound of y axis', type="integer",default=28477797) %>%
    add_argument('--HLAend', help='Lower bound of y axis', type="integer",default=33448354) %>%
    add_argument('--chromCN', help='chromCN.', type="character",default="All.chrom.CN.tsv") %>%
    add_argument('--heatmapCN', help='chromCN.', type="character",default="heatmap.chrom.CN.png") %>%
    add_argument('--PAR', help='PARInfo.', type="character",default="/bi/8.xuxiong/database/PAR.bed") %>%
    add_argument('--assembly', help='assembly version.', type="character",default="GRCh37") %>%
    add_argument('--axis-y-min', help='Lower bound of y axis', type="double",default=0) %>%
    add_argument('--axis-y-max', help='Lower bound of y axis', type="double",default=3) %>%
    add_argument('--geneAnnbed', help='Gene annotation BED file (columns: chrom, start, end, gene_name)', type="character", default=NA) %>%
    add_argument('--config', help='Configuration file with sample2pedigree section (YAML-like format)', type="character", default=NA) %>%
    add_argument('--outdir', help='Output directory for CNV results', type="character", default="03_CNV") %>%
    add_argument('--bgzip', help='bgzip path', type="character", default="/bi/software/htslib/bgzip") %>%
    add_argument('--tabix', help='tabix path', type="character", default="/bi/software/htslib/tabix") %>%
    add_argument('--bedtools', help='bedtools path', type="character", default="/bi/software/bedtools");

argv <- parse_args(p);
flog.info('Arguments are as follows');
str(argv);

bgzip <- argv$bgzip
tabix <- argv$tabix
bedtools <- argv$bedtools

# ===== CREATE OUTPUT DIRECTORY & NORMALIZE PATH =====
if (!dir.exists(argv$outdir)) dir.create(argv$outdir, recursive=TRUE)
argv$outdir <- normalizePath(argv$outdir, mustWork = FALSE)  # 规范化路径，避免重复斜杠

# ===== Function to parse config file and extract sample->pedigree mapping =====
parse_config_pedigree <- function(config_file) {
    if (!file.exists(config_file)) {
        flog.warn("Config file %s not found, pedigree integration disabled", config_file)
        return(NULL)
    }
    lines <- readLines(config_file, warn=FALSE)
    start_idx <- grep("^\\s*sample2pedigree:\\s*$", lines, ignore.case=TRUE)
    if (length(start_idx) == 0) {
        flog.warn("No 'sample2pedigree:' section found in %s", config_file)
        return(NULL)
    }
    mapping <- list()
    i <- start_idx[1] + 1
    while (i <= length(lines)) {
        line <- trimws(lines[i])
        if (line == "") { i <- i+1; next }
        if (grepl("^\\s*[a-zA-Z_]+:\\s*$", line)) break
        if (grepl("^-\\s+", line)) {
            entry <- sub("^-\\s+", "", line)
            parts <- strsplit(entry, ":", fixed=TRUE)[[1]]
            if (length(parts) >= 2) {
                sample <- trimws(parts[1])
                pedigree <- trimws(paste(parts[-1], collapse=":"))
                mapping[[sample]] <- pedigree
            } else {
                flog.warn("Malformed pedigree entry: %s", line)
            }
        }
        i <- i+1
    }
    if (length(mapping) == 0) return(NULL)
    return(mapping)
}

# ===== Load pedigree mapping if config provided =====
sample2ped <- NULL
if (!is.na(argv$config)) {
    sample2ped <- parse_config_pedigree(argv$config)
    if (!is.null(sample2ped)) {
        flog.info("Loaded pedigree mapping for %d samples", length(sample2ped))
    }
}

# 检查必要文件
if (!is.na(argv$refData)) {
    if (!file.exists(argv$refData)) {
        print(p);
        stop(sprintf('file: %s is not exists!', argv$refData));
    }
    if (is.na(argv$refSexData) || !file.exists(argv$refSexData)) {
        print(p);
        stop('Argument refSexData is empty or file does not exist when refData is provided!');
    }
}

for (name in c('cytoFile', 'fastqCount', 'Polymorphism', 'PAR')) {
    if (is.na(argv[[name]])) {
        print(p);
        stop(sprintf('Argument %s is empty!', name));
    }
    if (!file.exists(argv[[name]])) {
        print(p);
        stop(sprintf('file: %s is not exists!', argv[[name]]));
    }
}

firstLine <- read.table(file = argv$PAR,header = F,nrows = 1)
if (length(firstLine) == 3){
    bedColNames <- c("chrom","begin","end")
}else if (length(firstLine) == 4){
    bedColNames <- c("chrom","begin","end","assembly")
}
parData <- fread(argv$PAR,header=F,sep="\t",data.table=TRUE,stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8",col.names=bedColNames) %>%
    filter(assembly == argv$assembly) %>% mutate(chrom = gsub("[Cc]hr","",chrom,perl=T))
setkey(parData, chrom, begin, end)

infiles<-grep("SizeSelect",Sys.glob(paste(ifelse(is.na(argv$inputBed),".",dirname(argv$inputBed)),"*.blk",sep=.Platform$file.sep)),perl=T,invert =T,value=T)
Chrs <- c(as.character(1:22),"X","Y")
chrBool <- grepl("^[Cc]hr",strsplit(readLines(con = ifelse(is.na(argv$inputBed),infiles[1],argv$inputBed), n = 2),"\n")[[2]],perl=T)
if(chrBool) Chrs<-paste0("chr",Chrs)

loadCytoBand<-function(cytoRData,ChrBool){#
    cyto<-NA
    if (grepl('\\.RData',cytoRData,perl=TRUE)){
        load(cytoRData)
    }else{
        data<-read.delim(cytoRData,header=F,col.names=c("chrom","start","end","name","type"))
        cyto<-data[nchar(as.character(data[,1]))<=5 & as.character(data[,1])!="chrM",]
    }
    colnames(cyto)<-c("chrom","start","end","name","type")
    if(!ChrBool) cyto$chrom <- gsub("chr","",cyto$chrom)
    cyto$Color<-NA
    cyto[cyto$type=="gneg",]$Color<-rgb(255,255,255, maxColorValue=255)
    cyto[cyto$type=="gpos25",]$Color<-rgb(200,200,200, maxColorValue=255)
    cyto[cyto$type=="gpos50",]$Color<-rgb(200,200,200, maxColorValue=255)
    cyto[cyto$type=="gpos75",]$Color<-rgb(130,130,130, maxColorValue=255)
    cyto[cyto$type=="gpos100",]$Color<-rgb(200,200,200, maxColorValue=255)
    cyto[cyto$type=="acen",]$Color<-"red"        # centromere
    cyto[cyto$type=="stalk",]$Color<-rgb(100,127,164, maxColorValue=255)   # repeat regions
    cyto[cyto$type=="gvar",]$Color<-rgb(220,220,220, maxColorValue=255)       # indented region
    chrs<-split(cyto,factor(cyto$chrom))
    chrs
}

Cyto<-loadCytoBand(argv$cytoFile,chrBool)

centromere<-matrix(c(121500000,125000000,128900000,249250621,
                    90500000,93300000,96800000,243199373,
                    87900000,91000000,93900000,198022430,
                    48200000,50400000,52700000,191154276,
                    46100000,48400000,50700000,180915260,
                    58700000,61000000,63300000,171115067,
                    58000000,59900000,61700000,159138663,
                    43100000,45600000,48100000,146364022,
                    47300000,49000000,50700000,141213431,
                    38000000,40200000,42300000,135534747,
                    51600000,53700000,55700000,135006516,
                    33300000,35800000,38200000,133851895,
                    16300000,17900000,19500000,115169878,
                    16100000,17600000,19100000,107349540,
                    15800000,19000000,20700000,102531392,
                    34600000,36600000,38600000,90354753,
                    22200000,24000000,25800000,81195210,
                    15400000,17200000,19000000,78077248,
                    24400000,26500000,28600000,59128983,
                    25600000,27500000,29400000,63025520,
                    10900000,13200000,14300000,48129895,
                    12200000,14700000,17900000,51304566,
                    58100000,60600000,63000000,155270560,
                    11600000,12500000,13400000,59373566), nrow = 24, ncol = 4, byrow = TRUE)


getISCN<-function(chr,start,end,log2R,Cyto=Cyto){
    CytoRange<-as.numeric(c(Cyto[[chr]][,2],Cyto[[chr]][nrow(Cyto[[chr]]),3]))
    cytoRowIndex<-findInterval(c(start,end),CytoRange,rightmost.closed = TRUE)
    if (all(grepl("p",Cyto[[chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],perl=TRUE))) cytoRowIndex<-rev(cytoRowIndex)
    ifelse(log2R > 0.3 | log2R < -0.5,
    paste(paste(Cyto[[chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],collapse="->"),
        ifelse(argv$HLAstart ==28477797,",seq[GRCh37]",",seq[GRCh38]"),ifelse(as.numeric(log2R)>=0,"dup(","del("),trimws(chr),")(",
        paste(Cyto[[trimws(chr)]][c(cytoRowIndex[1],cytoRowIndex[2]),4],collapse="",sep=""),
        ")chr",trimws(chr),":g.",trimws(start),"_",trimws(end),
        ifelse(as.numeric(log2R)>=0,"dup","del"),sep=""),
    paste(Cyto[[chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],collapse="->") )
}

CallSegment<-function(x,y,Chr,Cyto,Sample){
    CytoRange<-as.numeric(c(Cyto[[Chr]][,2],Cyto[[Chr]][nrow(Cyto[[Chr]]),3]))
    index_end <- seq_along(y)[c(diff(y)!=0,TRUE)]
    num_mark <- diff(c(0,index_end))
    interval<-sapply(seq_along(index_end),function(Index){
        c(ifelse(Index-1<=0,1,index_end[Index-1]+1),index_end[Index])
    })
    log2R<-y[interval[1,]]
    Len<-ncol(interval)
    ISCN<-apply(interval,2,function(X){
        cytoRowIndex<-findInterval(x[X],CytoRange,rightmost.closed = TRUE)
        if (all(grepl("p",Cyto[[Chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],perl=TRUE))) cytoRowIndex<-rev(cytoRowIndex)
        paste(paste(Cyto[[Chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],collapse="->"),
            ifelse(argv$HLAstart ==28477797,",seq[GRCh37]",",seq[GRCh38]"),ifelse(as.numeric(y[X[1]])>=0,"dup(","del("),trimws(Chr),")(",
            paste(Cyto[[trimws(Chr)]][c(cytoRowIndex[1],cytoRowIndex[2]),4],collapse="",sep=""),
            ")chr",trimws(Chr),":g.",x[X[1]],"_",x[X[2]],
            ifelse(as.numeric(y[X[1]])>=0,"dup","del"),sep="")
    })
    CytoBand<-apply(interval,2,function(X){
        cytoRowIndex<-findInterval(x[X],CytoRange,rightmost.closed = TRUE)
        if (all(grepl("p",Cyto[[Chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],perl=TRUE))) cytoRowIndex<-rev(cytoRowIndex)
        paste(Cyto[[Chr]][c(cytoRowIndex[1],cytoRowIndex[2]),4],collapse="->")
    })
    data.frame(ID=rep(Sample,Len), chrom=rep(Chr,Len),loc.start=x[interval[1,]], loc.end= x[interval[2,]], num.mark=num_mark, seg.mean=log2R,
        length=x[interval[2,]]-x[interval[1,]]+1, cytoband=ifelse(log2R > 0.3 | log2R < -0.5,ISCN,CytoBand))
}

DNACopyCallSegment<-function(x,y,chr,Cyto,sampleID){
    CNA.object <- CNA(y,rep(chr,length(x)),x,data.type="logratio",sampleid=sampleID)
    smoothed.CNA.object <- smooth.CNA(CNA.object,smooth.region=3)
    segment.smoothed.CNA.object <- segment(smoothed.CNA.object,verbose=0)
    segment.smoothed.CNA.object$output$length <- segment.smoothed.CNA.object$output$loc.end - segment.smoothed.CNA.object$output$loc.start + 1
    segment.smoothed.CNA.object$output$cytoband <- apply(segment.smoothed.CNA.object$output,1,function(XX){
        getISCN(XX[2],XX[3],XX[4],XX[6],Cyto)
    })
    segment.smoothed.CNA.object$output
}

cghsegK <- function(pos,log,nChr) {
    dt <- data.frame(position=pos,logratio=log,chromosome=rep(nChr,length(pos)))
    smoothed  <- smoothers$cghseg.k(dt)
    range     <- seq(1,nrow(smoothed))
    diff_ <-apply(smoothed,1,function(Y){
        x  <- 2^(1+Y)
        sum(sapply(0:6,function(n){
            sum(abs(x[(x < (n+0.5)) & (x > (n-0.5))] - n))
        }))
    })
    diff_min <- min(diff_)
    if (max(diff_) == diff_min) {
        i_best <- max(range)
    } else {
        i_best <- max(range[diff_ == diff_min])
        if (i_best == max(range)) {
            diff_min_2nd <- unique(diff_)[order(unique(diff_))[2]]
            i_best <- max(range[diff_ == diff_min_2nd])
        }
    }
    smoothed[i_best,,drop=F]
}

loadCNVPolymorphism<-function(CNVPolymorphismFile,chrBool){
    data<-read.delim(CNVPolymorphismFile,header=T)
    if (!chrBool) data$chr<-gsub("[cC]hr","",data$chr,perl=T) 
    data[data$end - data$start>=10000 & data$num_samples>10,]
}

loadCNVdisease<-function(CNVdiseaseFile,chrBool){
    data<-read.delim(CNVdiseaseFile,header=T,fileEncoding = "UTF-8",check.names = F,stringsAsFactors = F)
    colnames(data)<-c("chrom","loc.start","loc.end","type","name_ch")
    if (chrBool) data$chrom<-gsub("[cC]hr","",data$chrom,perl=T)
    data$chrom <- ifelse(data$chrom==23,'X',data$chrom)
    data$type <- ifelse(grepl('del|Loss',data$type,ignore.case = TRUE, perl = TRUE),'Loss','Gain')
    data
}

getLogData<-function(logFiles, sexCutoff){
    logData<-do.call(rbind,mclapply(logFiles,function(X){
        CMD <- paste("cat ",X,"|grep -v -P 'palindromic|Done|finish'|perl -ne 'chomp;if(/redundency\\s*ratio:\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*=\\s*(%[\\d\\.]+)/) {print $2,\"\\t\",$1,\"\\t\",$3,\"\\t\";}if(/mapping\\s*ratio:\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*=\\s*(%[\\d\\.]+)/){print $1,\"\\t\",$3,\"\\t\";}if(/chrY%:\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*=\\s*([\\d\\.]+),\\s*SexType:\\s*([MF])/){print $3,\"\\t\",$4,\"\\n\";}'",sep='')
        c(gsub(".blk|_dep","",X,perl=TRUE),strsplit(system(CMD,intern = TRUE),"\t")[[1]])
    }, mc.cores=8))
    if (ncol(logData)<8){
        logData<-do.call(rbind,mclapply(logFiles,function(X){
            CMD <- paste("cat ",X,"|grep -v -P 'palindromic|Done|finish'|perl -ne 'chomp;if(/mapping\\s*ratio:\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*=\\s*(%[\\d\\.]+)/){print $2,\"\\t\",$1,\"\\t\",$3,\"\\t\";}if(/chrY%:\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*=\\s*([\\d\\.]+),\\s*SexType:\\s*([MF])/){print $3,\"\\t\",$4,\"\\n\";}'",sep='')
            c(gsub(".blk|_dep","",X,perl=TRUE),strsplit(system(CMD,intern = TRUE),"\t")[[1]])
        }, mc.cores=8))
        colnames(logData)<-c("Sample","RC","MappedRC","MappedRC%","chrY%","Gender")
    }else{
        colnames(logData)<-c("Sample","RC","PCRdupRC","PCRdup%","uniqueMappedRC","uniqueMappedRC%","chrY%","Gender")
    }
    logData <- as.data.frame(logData, stringsAsFactors=FALSE)
    logData[,'Sample'] <- gsub("\\..*$","",basename(logData[,'Sample']),perl=T)
    logData[,'Gender'] <- ifelse(as.numeric(logData[,'chrY%']) <= sexCutoff,TRUE,FALSE)
    logData
}

QC <- function(fastqCount, logData, CVrc, CVchrom, outfile="mappingQC.csv") {
    CMD <- paste0("head -n 1 ",fastqCount," | awk -F\"\t\" '{print NF}'")
    NumberField <- as.numeric(system(CMD,intern = TRUE))
    if(NumberField == 6){
        fastq_count <- read.table(fastqCount,header=FALSE,comment.char = "#",col.names=c("Sample","read_count","base_count","meanLength","Q20","Q30"))
    }else if(NumberField == 8){
        fastq_count <- read.table(fastqCount,header=FALSE,comment.char = "#",col.names=c("Sample","read_count","base_count","minLength","maxLength","meanLength","Q20","Q30"))
    }
    fastq_count <- fastq_count[order(basename(as.character(fastq_count[,1])))[(1:nrow(fastq_count)) %% 2==1],]
    fastq_count[,1] <- gsub("-R2", "", gsub("-R1", "", gsub("\\..*$","",basename(fastq_count[,1]),perl=T)))
    #
    logData[,'Gender'] <- ifelse(logData[,'Gender'],"F","M")
    fastq_count <- merge(fastq_count, logData, by="Sample", all=TRUE)
    fastq_count <- merge(fastq_count, CVrc, by="Sample", all=TRUE)
    fastq_count <- merge(fastq_count, CVchrom, by="Sample", all=TRUE)
    print(head(fastq_count))
    write.table(fastq_count, file=outfile, sep=",", quote=FALSE, row.names=F, col.names=T)
    write_xlsx(fastq_count, gsub(".csv",".xlsx",outfile))
}

loadRefSexData <- function(refSexFile, refSampleCols) {
    sexData <- read.table(refSexFile, header=FALSE, stringsAsFactors=FALSE)
    refSexType <- setNames(
        ifelse(toupper(sexData[,2]) == "F", TRUE, ifelse(toupper(sexData[,2]) == "M", FALSE, NA)),
        sexData[,1]
    )[refSampleCols]
    if (any(is.na(refSexType))) {
        stop(sprintf('Missing or invalid sex info in refSexData for: %s', paste(refSampleCols[is.na(refSexType)], collapse=", ")))
    }
    refSexType
}

readDepthMatrix <- function(file, keepChroms) {
    keepCols <- c("chrom", "begin", "end", grep('_dep$', names(fread(file, nrows=0, check.names=FALSE, encoding="UTF-8")), value=TRUE))
    data <- fread(file, header=TRUE, sep="\t", data.table=TRUE, stringsAsFactors=FALSE, check.names=FALSE, encoding="UTF-8", select=keepCols)
    data <- data[chrom %in% keepChroms]
    setnames(data, old=keepCols[-c(1:3)], new=gsub('_dep$','',keepCols[-c(1:3)],perl=TRUE))
    as.data.frame(data, stringsAsFactors=FALSE)
}

prepareRefMatrix <- function(data) {
    setDT(data)
    keepCols <- grep('_dep$', colnames(data), value=TRUE)
    data <- data[, ..keepCols]
    setnames(data, old=keepCols, new=gsub('_dep$','',keepCols,perl=TRUE))
    as.data.frame(data, stringsAsFactors=FALSE)
}

selectCtrlSamples <- function(X, asCtrlsID, GenderBool, corrData, corrThreshold, minSamples, maxSamples) {
    secondary_corrThreshold <- corrThreshold - 0.01
    secondary_minSamples <- minSamples + 10

    trimCorr <- function(currCorr) {
        currCorr <- sort(currCorr[!is.na(currCorr)], decreasing = TRUE)
        if (length(currCorr) >= secondary_minSamples + 3) {
            currCorr <- tail(currCorr, -3)
        }
        currCorr
    }

    cor_all <- trimCorr(corrData[X, asCtrlsID, drop=TRUE])
    cor_group1 <- cor_all[names(cor_all)[GenderBool[names(cor_all)]]]
    cor_group2 <- cor_all[names(cor_all)[!GenderBool[names(cor_all)]]]

    valid_cor_group1 <- cor_group1[cor_group1 >= corrThreshold]
    valid_cor_group2 <- cor_group2[cor_group2 >= corrThreshold]
    n_pairs <- min(length(valid_cor_group1), length(valid_cor_group2)) * 2

    if (n_pairs >= maxSamples) {
        CORX <- c(head(valid_cor_group1, maxSamples / 2), head(valid_cor_group2, maxSamples / 2))
    } else if (n_pairs >= minSamples) {
        CORX <- c(head(valid_cor_group1, n_pairs / 2), head(valid_cor_group2, n_pairs / 2))
    } else {
        secondary_valid_cor_group1 <- cor_group1[cor_group1 >= secondary_corrThreshold]
        secondary_valid_cor_group2 <- cor_group2[cor_group2 >= secondary_corrThreshold]
        n_pairs_secondary <- min(length(secondary_valid_cor_group1), length(secondary_valid_cor_group2)) * 2
        if (n_pairs_secondary >= maxSamples) {
            CORX <- c(head(secondary_valid_cor_group1, maxSamples / 2), head(secondary_valid_cor_group2, maxSamples / 2))
        } else if (n_pairs_secondary >= secondary_minSamples){
            CORX <- c(head(secondary_valid_cor_group1, n_pairs_secondary / 2), head(secondary_valid_cor_group2, n_pairs_secondary / 2))
        } else {
            CORX <- c(head(cor_group1, secondary_minSamples / 2), head(cor_group2, secondary_minSamples / 2))
        }
    }
    CORX
}

calcRefStats <- function(mat) {
    t(apply(mat, 1, function(X){
        X <- as.double(X)
        X <- X[is.finite(X)]
        if (!length(X)) {
            return(c(median=0, mean=0, sd=0))
        }
        Z <- X
        if (length(X) > 5) {
            Z <- X[!(X %in% boxplot.stats(X)$out)]
            if (!length(Z)) {
                Z <- X
            }
        }
        c(
            median=ifelse(length(Z)>2,median(Z,na.rm=T),mean(Z,na.rm=T)),
            mean=mean(Z,na.rm=T),
            sd=ifelse(length(Z)>1,sd(Z,na.rm=T),0)
        )
    }))
}

dotPlot <- function(cData, sample, cCyto, Segment, SegZscore, CNV, CNVdisease, chroms, Ymin = argv$axis_y_min, Ymax = argv$axis_y_max) {
    # 检查输出目录
    if (!dir.exists(argv$outdir)) dir.create(argv$outdir, recursive = TRUE)
    
    # ===== 内部复制数据并去掉染色体 "chr" 前缀 =====
    cData_plot <- cData
    cData_plot$chrom <- gsub("^chr", "", cData_plot$chrom)
    cCyto_plot <- cCyto
    cCyto_plot$chrom <- gsub("^chr", "", cCyto_plot$chrom)
    Segment_plot <- Segment
    Segment_plot$chrom <- gsub("^chr", "", Segment_plot$chrom)
    if (!is.null(SegZscore) && nrow(SegZscore) > 0) {
        SegZscore_plot <- SegZscore
        SegZscore_plot$chrom <- gsub("^chr", "", SegZscore_plot$chrom)
    } else {
        SegZscore_plot <- data.frame()
    }
    CNV_plot <- CNV
    CNV_plot$chrom <- gsub("^chr", "", CNV_plot$chrom)
    CNVdisease_plot <- CNVdisease
    CNVdisease_plot$chrom <- gsub("^chr", "", CNVdisease_plot$chrom)
    chroms_plot <- gsub("^chr", "", chroms)
    
    # 因子水平重设
    cData_plot$chrom <- factor(cData_plot$chrom, levels = chroms_plot)
    Segment_plot$chrom <- factor(Segment_plot$chrom, levels = chroms_plot)
    if (nrow(SegZscore_plot) > 0) {
        SegZscore_plot$chrom <- factor(SegZscore_plot$chrom, levels = chroms_plot)
    }
    cCyto_plot$chrom <- factor(cCyto_plot$chrom, levels = chroms_plot)
    CNV_plot$chrom <- factor(CNV_plot$chrom, levels = chroms_plot)
    CNVdisease_plot$chrom <- factor(CNVdisease_plot$chrom, levels = chroms_plot)
    
    Colors <- c('#4682B4','#6B8E23','#87CEEB','#A0522D','#FF8C00','#6A5ACD','#778899','#DAA520','#B22222','#FF6699')
    
    # 构建SegmentDF
    SegmentDF <- data.frame(
        chrom = c(rbind(as.character(Segment_plot$chrom), as.character(Segment_plot$chrom))),
        loc.start = c(rbind(as.numeric(Segment_plot$loc.start), as.numeric(Segment_plot$loc.end))),
        seg.mean = c(rbind(as.double(Segment_plot$CopyNumber), as.double(Segment_plot$CopyNumber)))
    )
    
    pacen <- cCyto_plot %>% filter(as.character(type) == "acen" & substring(name, 1, 1) == "p")
    pter <- data.frame(
        chrom = rep(pacen$chrom, each = 3),
        x = c(rbind(pacen$start, pacen$end, pacen$start)),
        y = rep(c(Ymin - 0.5, Ymin - 0.3, Ymin - 0.1), length(pacen$type)),
        type = rep(pacen$type, each = 3)
    )
    qacen <- cCyto_plot %>% filter(as.character(type) == "acen" & substring(name, 1, 1) == "q")
    qter <- data.frame(
        chrom = rep(qacen$chrom, each = 3),
        x = c(rbind(qacen$start, qacen$end, qacen$end)),
        y = rep(c(Ymin - 0.3, Ymin - 0.5, Ymin - 0.1), length(qacen$type)),
        type = rep(qacen$type, each = 3)
    )
    
    SegmentDF$chrom <- factor(SegmentDF$chrom, levels = chroms_plot)
    pter$chrom <- factor(pter$chrom, levels = chroms_plot)
    qter$chrom <- factor(qter$chrom, levels = chroms_plot)
    
    # ---- p1 ----
    p1 <- ggplot(data = cData_plot, aes(x = as.numeric(pos), y = as.double(CopyNumber))) +
        geom_point(size = 0.1, aes(colour = CopyNumber)) + 
        scale_colour_gradient2(midpoint = 2, limits = c(0, 4), low = "blue", mid = "gray80", high = "red") +
        geom_hline(yintercept = 2, linetype = 1, color = "springgreen4", linewidth = 0.25) +
        xlab("Chromosome") + ylab("Copy Number") +
        facet_grid(chrom ~ ., scales = "free_x", space = "free_x", labeller = label_value) +
        coord_cartesian(xlim = c(0, 249250621), ylim = c(Ymin - 1, Ymax)) + 
        geom_rect(data = cCyto_plot %>% filter(as.character(type) != "acen"), inherit.aes = FALSE,
                  mapping = aes(xmin = start, xmax = end, ymin = Ymin - 0.5, ymax = Ymin - 0.1, fill = type),
                  linewidth = 0.01, color = 'black') +
        geom_polygon(data = pter, inherit.aes = FALSE, mapping = aes(x = x, y = y, fill = type), color = 'black', linewidth = 0.01) +
        geom_polygon(data = qter, inherit.aes = FALSE, mapping = aes(x = x, y = y, fill = type), color = 'black', linewidth = 0.01) +
        scale_fill_manual(values = c("stalk" = "#647FA4", "gpos25" = "#C8C8C8", "gpos50" = "#C8C8C8",
                                     "gpos75" = "#828282", "gpos100" = "#C8C8C8", "gvar" = "#DCDCDC",
                                     "gneg" = "#FFFFFF", "acen" = "red")) +
        scale_x_continuous(expand = c(0, 0), labels = function(x) paste0(x / 1000000, "M")) +
        scale_y_continuous(breaks = seq(from = Ymin - 1, to = Ymax, by = 1)) +
        geom_text(data = cCyto_plot, inherit.aes = FALSE,
                  mapping = aes(x = start + (end - start) / 2, y = Ymin - 0.65,
                                label = paste(gsub("[Cc]hr", "", chrom, perl = T), name, sep = '')),
                  size = 0.8, angle = 70) +
        geom_vline(data = cCyto_plot, mapping = aes(xintercept = start), linetype = 3, linewidth = 0.1, colour = "#C8C8C8") +
        geom_hline(yintercept = seq(from = Ymin, to = Ymax, by = 1), color = '#C8C8C8', linewidth = 0.1) +
        geom_line(data = cData_plot, inherit.aes = FALSE,
                  aes(x = as.numeric(pos), y = as.numeric(CopyNumberSeg)), linewidth = 0.25, color = "springgreen") +
        new_scale_color() +
        geom_segment(data = CNV_plot, inherit.aes = FALSE,
                     aes(x = start, xend = end, y = Ymax - 0.05, yend = Ymax - 0.05, color = type), linewidth = 0.8, linetype = 1) +
        geom_segment(data = CNVdisease_plot, inherit.aes = FALSE,
                     aes(x = loc.start, xend = loc.end, y = Ymin + 0.05, yend = Ymin + 0.05, color = type), linewidth = 0.8, linetype = 1) +
        scale_color_manual(values = c("Gain" = "red", "Loss" = "blue")) +
        theme(axis.text.x = element_text(angle = 0, size = 5, hjust = 0.5),
              axis.text.y = element_text(size = 5),
              strip.text.y = element_text(angle = 360),
              panel.background = element_blank(),
              panel.grid.major = element_blank(),
              legend.position = "none",
              panel.grid.minor.x = element_blank(),
              panel.grid.minor.y = element_blank(),
              plot.margin = unit(c(0, 0, 0, 0.1), 'cm'),
              panel.spacing = unit(0.01, "lines"))
    ggsave(file.path(argv$outdir, paste0(sample, ".log2r_v.png")), width = 9, height = 16, dpi = 256, device = 'png')
    
    # ---- p2 ----
    p2 <- ggplot(data = cData_plot, aes(x = as.numeric(pos), y = as.double(CopyNumber))) +
        geom_point(size = 0.1, aes(colour = col)) + 
        scale_color_manual(values = c(A = Colors[1], B = Colors[7])) +
        geom_hline(yintercept = 2, linetype = 1, color = "springgreen4", linewidth = 0.25) +
        xlab("Chromosome") + ylab("Copy Number") +
        facet_grid(. ~ chrom, scales = "free_x", space = "free_x", labeller = label_value) +
        coord_cartesian(ylim = c(Ymin - 1, Ymax)) +        
        geom_rect(data = cCyto_plot %>% filter(as.character(type) != "acen"), inherit.aes = FALSE,
                  mapping = aes(xmin = start, xmax = end, ymin = Ymin - 0.5, ymax = Ymin - 0.1, fill = type),
                  color = 'black', linewidth = 0.01) +
        geom_polygon(data = pter, inherit.aes = FALSE, mapping = aes(x = x, y = y, fill = type), color = 'black', linewidth = 0.01) +
        geom_polygon(data = qter, inherit.aes = FALSE, mapping = aes(x = x, y = y, fill = type), color = 'black', linewidth = 0.01) +
        scale_fill_manual(values = c("stalk" = "#647FA4", "gpos25" = "#C8C8C8", "gpos50" = "#C8C8C8",
                                     "gpos75" = "#828282", "gpos100" = "#C8C8C8", "gvar" = "#DCDCDC",
                                     "gneg" = "#FFFFFF", "acen" = "red")) +
        scale_x_continuous(expand = c(0, 0), labels = function(x) paste0(x / 1000000, "M")) +
        scale_y_continuous(breaks = seq(from = Ymin - 1, to = Ymax, by = 1)) +
        geom_text(data = cCyto_plot, inherit.aes = FALSE,
                  mapping = aes(x = start + (end - start) / 2, y = Ymin - 0.8,
                                label = paste(gsub("[Cc]hr", "", chrom, perl = T), name, sep = '')),
                  size = 0.5, angle = 70) +
        geom_hline(yintercept = seq(from = Ymin, to = Ymax, by = 1), color = '#C8C8C8', linewidth = 0.1) +
        geom_line(data = cData_plot, inherit.aes = FALSE,
                  aes(x = as.numeric(pos), y = as.numeric(CopyNumberSeg)), linewidth = 0.25, color = "springgreen") +
        new_scale_color() +
        geom_segment(data = CNV_plot, inherit.aes = FALSE,
                     aes(x = start, xend = end, y = Ymax - 0.05, yend = Ymax - 0.05, color = type), linewidth = 0.8, linetype = 1) +
        geom_segment(data = CNVdisease_plot, inherit.aes = FALSE,
                     aes(x = loc.start, xend = loc.end, y = Ymin + 0.05, yend = Ymin + 0.05, color = type), linewidth = 0.8, linetype = 1) +
        scale_color_manual(values = c("Gain" = "red", "Loss" = "blue")) +
        theme(axis.text.x = element_text(angle = 70, size = 5, hjust = 1),
              axis.text.y = element_text(size = 5),
              panel.background = element_blank(),
              panel.grid.major = element_blank(),
              panel.grid.minor = element_blank(),
              legend.position = "none",
              plot.margin = unit(c(0, 0, 0, 1), 'cm'),
              panel.spacing = unit(0.1, "lines"))
    ggsave(file.path(argv$outdir, paste0(sample, ".log2r_h.png")), width = 24, height = 2, dpi = 256, device = 'png')
    
    # ---- p3 ----
    Segment_plot$zScore <- NULL
    Segment_plot$CopyNumber <- NULL
    Segment_plot$variable <- rep("log2R", nrow(Segment_plot))
    Segment_plot$MosRatio <- NULL
    
    if (nrow(SegZscore_plot) > 0) {
        SegZscore_plot$variable <- rep("zScore", nrow(SegZscore_plot))
        Seg_comb <- rbind(Segment_plot, SegZscore_plot)
        colnames(Seg_comb)[6] <- "value"
    } else {
        colnames(Segment_plot)[6] <- "value"
        Seg_comb <- Segment_plot
    }
    
    cData_plot$MosRatio <- NULL
    mData <- melt(cData_plot, id = c("chrom", "pos", "col", "CopyNumber"))
    
    # 构建正确的 y 轴 scale 列表：每个 facet 行对应一个 scale
    # 行数 = length(unique(chrom)) * length(unique(variable))
    all_levels <- expand.grid(chrom = chroms_plot, variable = c("log2R", "zScore"), stringsAsFactors = FALSE)
    n_rows <- nrow(all_levels)
    # 为每行分配 scale：奇数行（log2R）用第一个 scale，偶数行（zScore）用第二个 scale
    scale_list <- lapply(1:n_rows, function(i) {
        if (i %% 2 == 1) {
            scale_y_continuous(breaks = round(seq(from = -1.2, to = 1.2, by = 0.6), digits = 1), limits = c(-1.2, 1.2))
        } else {
            scale_y_continuous(breaks = seq(from = -8, to = 8, by = 4), limits = c(-8, 8))
        }
    })
    
    p3 <- ggplot(data = mData, aes(x = pos, y = value)) +
        geom_point(size = 0.1, aes(colour = col)) + 
        scale_color_manual(values = c(A = Colors[1], B = Colors[7])) +
        geom_hline(yintercept = 0, linetype = 1, color = "springgreen4", linewidth = 0.25) +
        xlab("Chromosome") + ylab("value") +
        facet_nested(chrom + variable ~ ., scales = "free") +
        facetted_pos_scales(y = scale_list) +
        coord_cartesian(xlim = c(0, 249250621)) + 
        scale_x_continuous(expand = c(0, 0.1), labels = function(x) paste0(x / 1000000, "M")) + 
        geom_segment(data = Seg_comb, inherit.aes = FALSE,
                     aes(x = as.numeric(loc.start), xend = as.numeric(loc.end),
                         y = as.double(value), yend = as.double(value)),
                     linewidth = 0.25, color = "firebrick3", linetype = 1) +
        theme(axis.text.x = element_text(angle = 0, size = 5, hjust = 0.5),
              axis.text.y = element_text(size = 5),
              panel.background = element_blank(),
              panel.grid.major = element_blank(),
              panel.grid.minor.x = element_blank(),
              panel.grid.minor.y = element_line(colour = "#C8C8C8", linewidth = 0.1),
              legend.position = "none",
              plot.margin = unit(c(0, 0, 0, 1), 'cm'),
              panel.spacing = unit(0.1, "lines"))
    ggsave(file.path(argv$outdir, paste0(sample, ".log2RzScore.png")), width = 12, height = 24, dpi = 256, device = 'png')
}

DNAcopyCNVcalling<-function(y,x,chr,sampleID,SexType){
    CNA.object <- CNA(y,chr,x,data.type="logratio",sampleid=sampleID)
    smoothed.CNA.object <- smooth.CNA(CNA.object)
    CN<-ifelse(SexType,ifelse(grepl('Y',chr, ignore.case = TRUE, perl = TRUE),1,2),
                    ifelse(grepl('X|Y',chr, ignore.case = TRUE, perl = TRUE),1,2))
    segment.smoothed.CNA.object <- segment(smoothed.CNA.object,verbose=0)
    dd<-segment.smoothed.CNA.object$output %>% mutate( rounded_seg = as.integer(round((2^seg.mean)*CN*20))) %>%
        mutate(seg_diff = ifelse(rounded_seg - lag(rounded_seg) != 0, 1, 0)) %>%
        mutate(seg_diff = ifelse(is.na(seg_diff), 0, seg_diff)) %>%
        mutate(seg_no = cumsum(seg_diff)) %>% 
        select(-seg_diff, -rounded_seg)
    ddmerge<-left_join(dd,dd %>% group_by(seg_no) %>% summarise(seg_median=median(seg.mean)),seg_medians,by="seg_no");
    do.call(rbind,by(ddmerge,ddmerge$seg_no,function(X){
        data.frame(ID=X[1,'ID'],chrom=X[1,'chrom'],loc.start=X[1,'loc.start'],
            loc.end=X[nrow(X),'loc.end'],num.mark=sum(X$num.mark),seg.mean=X[1,'seg_median'])
    }))
}

cCyto<-do.call(rbind,Cyto)
cCyto$chrom <- factor(cCyto$chrom, levels = Chrs)

CNVPolymorphism<-loadCNVPolymorphism(argv$Polymorphism,chrBool)
colnames(CNVPolymorphism)[1]<-"chrom"
CNVPolymorphism$chrom<-factor(CNVPolymorphism$chrom, levels = Chrs)

CNVdisease<-loadCNVdisease(argv$Disease,chrBool)
CNVdisease$chrom<-factor(CNVdisease$chrom, levels = Chrs)

raw_data <- readDepthMatrix(argv$inputBed, Chrs)
sampleIDs <- colnames(raw_data)[-c(1:3)]
raw_data$pos <- round((raw_data$begin + raw_data$end) / 2)

AutosomeRC_CV <- apply(raw_data[raw_data$chrom %in% Chrs[1:22],sampleIDs,drop=F],2,function(X){
    round(sd(X)/mean(X),digits = 4)
})
AutosomeRC_CV <- cbind(Sample = names(AutosomeRC_CV), AutosomeRC_CV)
#
chromRC_CV <- t(apply(raw_data[,sampleIDs,drop=F],2,function(X){
    tapply(X,factor(raw_data[,"chrom"],levels=Chrs),function(Y){
        round(sd(Y)/mean(Y),digits = 4)
    })
}))
colnames(chromRC_CV) <- paste0('CV_',colnames(chromRC_CV))
chromRC_CV <- cbind(Sample = rownames(chromRC_CV), chromRC_CV)

logFiles <- gsub(".blk|_dep",".log",infiles,perl=TRUE)
LogData <- getLogData(logFiles,argv$sexCutoff)
SexType <- LogData$Gender
names(SexType) <- LogData$Sample
QC(argv$fastqCount, LogData, AutosomeRC_CV, chromRC_CV, outfile=file.path(argv$outdir, "mappingQC.csv"))
rm(LogData, AutosomeRC_CV, chromRC_CV, logFiles)
gc()

allIDs <- sampleIDs
controlIDs <- sampleIDs
GenderBool <- SexType[sampleIDs]
names(GenderBool) <- sampleIDs
if (!is.na(argv$refData)){
    load(argv$refData)
    ref <- prepareRefMatrix(ref)
    refSampleCols <- setdiff(colnames(ref), sampleIDs)
    if (nrow(ref) != nrow(raw_data)) {
        stop('refData row count does not match inputBed bin count')
    }
    raw_data[refSampleCols] <- ref[refSampleCols]
    
    refSexType <- loadRefSexData(argv$refSexData, refSampleCols)
    allIDs <- c(sampleIDs, refSampleCols)
    if (argv$absCtrls) {
        controlIDs <- refSampleCols
    } else {
        controlIDs <- c(sampleIDs, refSampleCols)
    }
    GenderBool <- c(SexType[sampleIDs], refSexType)
    names(GenderBool) <- controlIDs
    rm(ref, refSexType, refSampleCols)
    gc()
}
autosomeData <- as.matrix(raw_data[raw_data$chrom %in% Chrs[1:22], allIDs, drop=FALSE])
autosomeData <- autosomeData[complete.cases(autosomeData),,drop=FALSE]

corrData <- cor(autosomeData[,sampleIDs,drop=FALSE], autosomeData[,controlIDs,drop=FALSE])
write.table(corrData, file=file.path(argv$outdir, "corrQC.matridx.csv"), sep=",", quote=F, row.names=T, col.names=T)
CtrlSampleslsls <- setNames(mclapply(sampleIDs,function(X){
    tryCatch({
        warn_corrThreshold <- argv$corrThreshold+0.04
        fail_corrThreshold <- argv$corrThreshold+0.01
        CORX <- selectCtrlSamples(X, controlIDs, GenderBool, corrData, argv$corrThreshold, argv$minSamples, argv$maxSamples)
        if (!length(CORX)) {
            return(list(CORX = CORX, tag = "FAIL,cor:NA"))
        }
        corrVal <- cor(
            as.numeric(autosomeData[,X]),
            as.numeric(apply(autosomeData[,names(CORX),drop=FALSE], 1, function(Z){median(Z)}))
        )
        if (corrVal >= warn_corrThreshold) {
            tag <- paste0("cor:", corrVal)
        } else if (corrVal >= fail_corrThreshold) {
            tag <- paste0("WARNING,cor:", corrVal)
        } else {
            tag <- paste0("FAIL,cor:", corrVal)
        }
        list(CORX = CORX, tag = tag)
    }, error=function(e){
        list(error = conditionMessage(e))
    })
}, mc.cores=8), sampleIDs)

ctrlErrors <- vapply(CtrlSampleslsls, function(X){!is.null(X$error)}, logical(1))
if (any(ctrlErrors)) {
    stop(sprintf(
        "Control selection failed for sample(s): %s; first error: %s",
        paste(names(CtrlSampleslsls)[ctrlErrors], collapse=", "),
        CtrlSampleslsls[[which(ctrlErrors)[1]]]$error
    ))
}

corrMatrix <- as.data.frame(do.call(rbind, lapply(sampleIDs, function(X){
    res <- CtrlSampleslsls[[X]]
    CORX <- res$CORX
    samplesCORX <- paste(names(CORX), "(", round(CORX, digits = 3), ")", sep = "", collapse = ";")
    ll <- length(CORX)
    c(X, res$tag, ll, ncol(corrData), round(ll/(ncol(corrData)-1), digits = 3), samplesCORX)
})), stringsAsFactors = FALSE)
colnames(corrMatrix) <- c("SampleID", "TagQual", "CtrlSamplesNum", "TotalSamplesNum", "CtrlSamplesRatio", "CtrlSamplesList")
write.table(corrMatrix, file = file.path(argv$outdir, argv$corrQC), sep = "\t", quote = FALSE, row.names = FALSE, col.names = TRUE)
#print(CtrlSampleslsls)

sampleRefStats <- setNames(mclapply(sampleIDs, function(sampleID){
    ctrlIDs <- names(CtrlSampleslsls[[sampleID]]$CORX)
    if (!length(ctrlIDs)) {
        stop(sprintf('No reference controls were found for sample %s', sampleID))
    }
    currRefStats <- as.data.frame(calcRefStats(as.matrix(raw_data[,ctrlIDs,drop=FALSE])), stringsAsFactors=FALSE)
    sexChrBool <- raw_data$chrom %in% Chrs[23:24]
    sameSexCtrlIDs <- ctrlIDs[GenderBool[ctrlIDs] == SexType[sampleID]]
    if (any(sexChrBool) && length(sameSexCtrlIDs)) {
        currRefStats[sexChrBool,] <- as.data.frame(
            calcRefStats(as.matrix(raw_data[sexChrBool,sameSexCtrlIDs,drop=FALSE])),
            stringsAsFactors=FALSE
        )
    }
    currRefStats
}, mc.cores=8), sampleIDs)
rm(autosomeData, corrData, corrMatrix, ctrlErrors)
gc()
#print(sampleRefStats)
#print(dim(raw_data))

# ===== Preload gene annotation if provided =====
if (!is.na(argv$geneAnnbed) && !exists("geneAnno")) {
    geneAnno <- fread(argv$geneAnnbed, header=TRUE, data.table=FALSE)
    if (nrow(geneAnno) != nrow(raw_data)) {
        stop("Gene annotation file row count does not match raw_data!")
    }
    flog.info("Gene annotation file loaded: %s", argv$geneAnnbed)
} else if (!is.na(argv$geneAnnbed)) {
    # geneAnno already exists from earlier? (not needed)
}

MosRatioCutoff <- 0.15

# ===== Prepare variables for parallel processing =====
ctrlSamples <- CtrlSampleslsls
refStatsList <- sampleRefStats
raw_data_local <- raw_data
geneAnno_local <- if (!is.na(argv$geneAnnbed) && exists("geneAnno")) geneAnno else NULL
sexType_local <- SexType
cyto_local <- Cyto
parData_local <- parData
cnvPolymorphism_local <- CNVPolymorphism
cnvDisease_local <- CNVdisease
chrs_local <- Chrs
argv_local <- argv
centromere_local <- centromere
cCyto_local <- cCyto
mosRatioCutoff_local <- MosRatioCutoff

# ===== Parallel processing with explicit argument passing =====
results <- mclapply(sampleIDs, function(sampleID, ctrlSamples, refStatsList, raw_data, geneAnno, SexType, Cyto, parData, CNVPolymorphism, CNVdisease, Chrs, argv, centromere, cCyto, MosRatioCutoff) {
    ctrlIDs <- names(ctrlSamples[[sampleID]]$CORX)
    male <- !as.logical(SexType[sampleID])
    cat(sampleID,"\n",file=stderr())
    currRefStats <- refStatsList[[sampleID]]
    cData <- data.frame(chrom=raw_data$chrom, pos=raw_data$pos,
        log2R = ifelse(currRefStats$median>0, log2((as.double(raw_data[[sampleID]])+0.01)/as.double(currRefStats$median)), 0),
        zScore = ifelse(currRefStats$sd>0, (as.double(raw_data[[sampleID]])-as.double(currRefStats$mean))/as.double(currRefStats$sd), 0),
        col=unlist(sapply(Chrs,function(Y){
            ifelse(findInterval(raw_data[raw_data$chrom %in% Y,'pos'],
                c(Cyto[[Y]]$start,Cyto[[Y]][nrow(Cyto[[Y]]),'end']),rightmost.closed=TRUE)%%2==1,"A","B")
        }))
    )
    cData$chrom <- factor(cData$chrom, levels=Chrs)

    # --- Segmentation (same as original, using passed parameters) ---
    Seg <- as.data.frame(do.call(rbind, tapply(seq_along(cData$log2R), cData$chrom, function(Y){
        nChr <- which(Chrs %in% cData$chrom[Y[1]])
        if (nChr %in% c(13,14,15,21,22)) {
            qter = cData$pos[Y] >= centromere[nChr,2]
            a <- cData$pos[Y[qter]]
            b <- cData$log2R[Y[qter]]
            LowessRaw <- lowess(a,b,f=2/length(a),delta=0.001)
            DNACopyCallSegment(LowessRaw$x, LowessRaw$y, Chrs[nChr], Cyto, sampleID)
        } else {
            Lchr <- list(pter = cData$pos[Y] <= centromere[nChr,2], qter = cData$pos[Y] >= centromere[nChr,2])
            do.call(rbind, lapply(Lchr, function(ter){
                a <- cData$pos[Y[ter]]
                b <- cData$log2R[Y[ter]]
                Len <- length(a)
                if (Len < 10 || all(b==0)) {
                    DF <- data.frame(ID=rep(sampleID, Len), chrom=rep(Chrs[nChr], Len),
                                     loc.start=raw_data$begin[Y[ter]], loc.end=raw_data$end[Y[ter]],
                                     num.mark=Len, seg.mean=b, length=raw_data$end[Y[ter]]-raw_data$begin[Y[ter]]+1)
                    DF$cytoband <- apply(DF,1,function(XX) getISCN(XX[2],XX[3],XX[4],XX[6],Cyto))
                    DF
                } else {
                    LowessRaw <- lowess(a,b,f=2/Len,delta=0.001)
                    DNACopyCallSegment(LowessRaw$x, LowessRaw$y, Chrs[nChr], Cyto, sampleID)
                }
            }))
        }
    })))
    write.table(Seg, file=file.path(argv$outdir, paste0(sampleID, "_raw_seg.tsv")), sep="\t", quote=FALSE, row.names=F, col.names=T)
    # The following refinement steps are identical to original, so we copy them verbatim:
    Seg <- Seg %>% mutate(shiftMean = shift(seg.mean, n=1L, fill=NA, type="lag", give.names=FALSE),
                    diffseg = seg.mean - shiftMean,
                    threshold = cut(seg.mean,breaks = c(-Inf,-2.3219281,-0.5,0.3,0.8875253,Inf),right = FALSE),
                    Shift = shift(threshold, n=1L, fill=NA, type="lag", give.names=FALSE),
                    Lead = shift(threshold, n=1L, fill=NA, type="lead", give.names=FALSE),
                    ShiftChrom = shift(chrom, n=1L, fill=NA, type="lag", give.names=FALSE) ) %>% 
            mutate(seg_diff = ifelse(is.na(diffseg) | is.na(ShiftChrom) | is.na(Shift) | chrom==ShiftChrom & (abs(diffseg)<0.1 | (!is.na(Shift) & !is.na(Lead) & threshold!=Shift & threshold!=Lead & num.mark <=20 & as.character(Shift)!="[-0.5,0.3)" & as.character(Lead)!="[-0.5,0.3)") |  (threshold==Shift & (as.character(threshold)=="[-0.5,0.3)" | num.mark <=10))) , 0, 1 ) ) %>% 
            mutate(seg_no = cumsum(seg_diff))%>% 
            select(-seg_diff,-cytoband,-threshold,-Shift,-Lead ,-diffseg,-ShiftChrom,-shiftMean) %>% 
            group_by(seg_no) %>% 
            summarise(ID=first(ID),chrom=first(chrom),loc.start = first(loc.start), loc.end = max(loc.end), seg.mean=sum(num.mark*seg.mean)/sum(num.mark), num.mark=sum(num.mark),length=loc.end-loc.start) %>%
            select(-seg_no) %>%
            mutate(shiftMean = shift(seg.mean, n=1L, fill=NA, type="lag", give.names=FALSE),
                    diffseg = seg.mean - shiftMean,
                    threshold = cut(seg.mean,breaks = c(-Inf,-2.3219281,-0.5,0.3,0.8875253,Inf),right = FALSE),
                    Shift = shift(threshold, n=1L, fill=NA, type="lag", give.names=FALSE),
                    Lead = shift(threshold, n=1L, fill=NA, type="lead", give.names=FALSE),
                    ShiftChrom = shift(chrom, n=1L, fill=NA, type="lag", give.names=FALSE) ) %>% 
            mutate(seg_diff = ifelse(is.na(diffseg) | is.na(ShiftChrom) | is.na(Shift) | chrom==ShiftChrom & (abs(diffseg)<0.1 | (!is.na(Shift) & !is.na(Lead) & threshold!=Shift & threshold!=Lead & num.mark <=20 & as.character(Shift)!="[-0.5,0.3)" & as.character(Lead)!="[-0.5,0.3)") |  (threshold==Shift & (as.character(threshold)=="[-0.5,0.3)" | num.mark <=10))) , 0, 1 ) ) %>% 
            mutate(seg_no = cumsum(seg_diff))%>% 
            select(-seg_diff,-threshold,-Shift,-Lead ,-diffseg,-ShiftChrom,-shiftMean) %>% 
            group_by(seg_no) %>% 
            summarise(ID=first(ID),chrom=first(chrom),loc.start = first(loc.start), loc.end = max(loc.end), seg.mean=sum(num.mark*seg.mean)/sum(num.mark),num.mark=sum(num.mark),length=loc.end-loc.start) %>%
            select(-seg_no) %>% 
            relocate(num.mark, .before = seg.mean) %>% 
            rowwise() %>% 
            mutate(cytoband = getISCN(chrom,loc.start, loc.end,seg.mean,Cyto))
    Seg$zScore <- apply(Seg,1,function(M){
        currZscore <- cData[as.character(cData$chrom) %in% M["chrom"] & cData$pos >=as.numeric(M["loc.start"]) & cData$pos <=as.numeric(M["loc.end"]),"zScore"]
        if(length(currZscore)){
            currZscore[is.nan(currZscore) | is.na(currZscore) | is.null(currZscore) | is.infinite(currZscore)] <- 0
            return(ifelse(length(currZscore)>3,median(currZscore,na.rm=T),mean(currZscore,na.rm=T)))
        }else{
            return(0)
        }
    })
    SegZscore <- do.call(rbind, tapply(seq_along(cData$zScore), cData$chrom, function(Y){
        nChr <- which(Chrs %in% cData$chrom[Y[1]])
        if (nChr %in% c(13,14,15,21,22)) {
            Lchr <- list(qter = cData$pos[Y] >= centromere[nChr,2])
        } else {
            Lchr <- list(pter = cData$pos[Y] <= centromere[nChr,2], qter = cData$pos[Y] >= centromere[nChr,2])
        }
        do.call(rbind, lapply(Lchr, function(ter){
            a <- cData$pos[Y[ter]]
            b <- cData$zScore[Y[ter]]
            if (length(a) < 10 || all(b==0) || (!male && nChr==24)) {
                CallSegment(a,b,Chrs[nChr],Cyto,sampleID)
            } else {
                LowessRaw <- lowess(a,b,f=2/length(a),delta=0.001)
                FL <- cghFLasso(LowessRaw$y, nucleotide.position=LowessRaw$x, missing.PlugIn=TRUE, FDR=0.01)
                cghsegKSmooth <- cghsegK(LowessRaw$x, FL$Esti.CopyN, nChr)
                CallSegment(a, cghsegKSmooth[1,], Chrs[nChr], Cyto, sampleID)
            }
        }))
    }))
    cData$seg <- cData$log2R
    for(i in 1:nrow(Seg)) {
        cData$seg[which(cData$chrom %in% Seg$chrom[i] & cData$pos >= Seg$loc.start[i] & cData$pos <= Seg$loc.end[i])] <- Seg$seg.mean[i]
    }
    if(male){
        raw_data_chromGenderBool <- raw_data$chrom %in% Chrs[1:22]
        seg_chromGenderBool <- Seg$chrom %in% Chrs[1:22]
        baseCN <- ifelse(raw_data_chromGenderBool,2,1)
        idx <- foverlaps(as.data.table(raw_data), parData, by.x=c("chrom", "begin", "end"), type="any", which=TRUE, nomatch=F)
        baseCN[idx$xid] <- 2
        cData$CopyNumber <- baseCN*(2^cData$log2R)
        cData$CopyNumberSeg <- baseCN*(2^cData$seg)
        cData$MosRatio <- round(abs(cData$CopyNumber-baseCN)/1, digits=2)
        Seg$CopyNumber <- ifelse(seg_chromGenderBool, 2*(2^Seg$seg.mean), 2^Seg$seg.mean)
        Seg$MosRatio <- ifelse(seg_chromGenderBool, round(abs(Seg$CopyNumber-2)/1, digits=2), round(abs(Seg$CopyNumber-1)/1, digits=2))
    } else {
        raw_data_chromGenderBool <- raw_data$chrom %in% Chrs[24]
        seg_chromGenderBool <- Seg$chrom %in% Chrs[24]
        cData$CopyNumber <- ifelse(raw_data_chromGenderBool, 0.001*(2^cData$log2R), 2*(2^cData$log2R))
        cData$CopyNumberSeg <- ifelse(raw_data_chromGenderBool, 0.001*(2^cData$seg), 2*(2^cData$seg))
        cData$MosRatio <- ifelse(raw_data_chromGenderBool, round(abs(cData$CopyNumber-0)/1, digits=2), round(abs(cData$CopyNumber-2)/1, digits=2))
        Seg$CopyNumber <- ifelse(seg_chromGenderBool, 0.001*(2^Seg$seg.mean), 2*(2^Seg$seg.mean))
        Seg$MosRatio <- ifelse(seg_chromGenderBool, round(abs(Seg$CopyNumber-0)/1, digits=2), round(abs(Seg$CopyNumber-2)/1, digits=2))
    }
    Seg$chrom <- factor(Seg$chrom, levels=Chrs)
    SegZscore$chrom <- factor(SegZscore$chrom, levels=Chrs)

    # Write filtered seg files
    write_xlsx(Seg %>% filter(((MosRatio > MosRatioCutoff & num.mark>=1000) | ((seg.mean < -0.5 | seg.mean > 0.3) & num.mark>=2 & num.mark<1000) | ((seg.mean < -0.577767 | seg.mean > 0.4114262) & num.mark<2)) & abs(zScore)>3 & !(grepl("^([Cc]hr)?6$",chrom,perl=T) & loc.start >= argv$HLAstart & loc.end <= argv$HLAend)) %>%
        mutate(type = ifelse(seg.mean <0,"DEL",ifelse(seg.mean >0,"DUP","Normal")),
               AnnotSV_ID = paste(sub("[cChr]","",chrom,perl=T),loc.start,loc.end,type,"1",sep="_")) %>%
        relocate(type, .before = num.mark) %>% rename(start = loc.start, end = loc.end) %>%
        arrange(desc(num.mark * abs(zScore))),
        file.path(argv$outdir, paste0(sampleID, "_seg.xlsx")), col_names = TRUE)
    write.table(Seg %>% filter(((MosRatio > MosRatioCutoff & num.mark>=1000) | ((seg.mean < -0.5 | seg.mean > 0.3) & num.mark>=2 & num.mark<1000) | ((seg.mean < -0.577767 | seg.mean > 0.4114262) & num.mark<2)) & abs(zScore)>3 & !(grepl("^([Cc]hr)?6$",chrom,perl=T) & loc.start >= argv$HLAstart & loc.end <= argv$HLAend)) %>%
        mutate(type = ifelse(seg.mean <0,"DEL",ifelse(seg.mean >0,"DUP","Normal")),
               AnnotSV_ID = paste(sub("[cChr]","",chrom,perl=T),loc.start,loc.end,type,"1",sep="_")) %>%
        relocate(type, .before = num.mark) %>% rename(start = loc.start, end = loc.end) %>%
        arrange(desc(num.mark * abs(zScore))),
        file=file.path(argv$outdir, paste0(sampleID, "_seg.tsv")), sep="\t", quote=FALSE, row.names=F, col.names=T)
    write.table(Seg %>% filter(!(grepl("^([Cc]hr)?6$",chrom,perl=T) & loc.start >= argv$HLAstart & loc.end <= argv$HLAend)) %>%
        mutate(type = ifelse(seg.mean <0,"DEL",ifelse(seg.mean >0,"DUP","Normal")),
               AnnotSV_ID = paste(sub("[cChr]","",chrom,perl=T),loc.start,loc.end,type,"1",sep="_")) %>%
        relocate(type, .before = num.mark) %>% rename(start = loc.start, end = loc.end) %>%
        arrange(desc(num.mark * abs(zScore))),
        file=file.path(argv$outdir, paste0(sampleID, "_NoFilt_seg.tsv")), sep="\t", quote=FALSE, row.names=F, col.names=T)
    ploidy <- data.frame(chrom=Chrs, CopyNumber=round(tapply(1:nrow(Seg), factor(Seg$chrom, levels=Chrs), function(chridx){
        ChrCN <- Seg[chridx, 'CopyNumber']
        ChrNumMark <- Seg[chridx, 'num.mark']
        ChrCNbool <- ChrCN <= 4
        sum(ChrNumMark[ChrCNbool] * ChrCN[ChrCNbool]) / sum(ChrNumMark[ChrCNbool])
    }), digits=3))
    ploidy$chrom <- paste0("chr", ploidy$chrom)
    write.table(ploidy, file=file.path(argv$outdir, paste0(sampleID, "_ploidy.tsv")), sep="\t", quote=FALSE, row.names=F, col.names=T)

    # Write .normalize.bed and .CN.bed
    norm_bed <- cbind(raw_data[,c("chrom","begin","end")], cData[,c("log2R","seg","CopyNumber","CopyNumberSeg","MosRatio","zScore")])
    norm_bed$chrom <- paste0("chr", norm_bed$chrom)   # 添加 chr 前缀
    write.table(norm_bed, file=file.path(argv$outdir, paste0(sampleID, '.normalize.bed')), sep="\t", quote=F, row.names=F, col.names=F)
    cn_bed <- data.frame(
        chrom = paste0("chr", raw_data$chrom),
        start = raw_data$begin,
        end = raw_data$end,
        copyNumber = round(cData$CopyNumber, 2)   # 保留两位小数
    )
    write.table(cn_bed, file = file.path(argv$outdir, paste0(sampleID, ".CN.bed")),
            sep = "\t", quote = FALSE, row.names = FALSE, col.names = FALSE)

    # MAPD output
    log2r_diff <- abs(diff(cData$log2R))
    mapd_df <- data.frame(window_start=raw_data$begin[-1], window_end=raw_data$end[-1], abs_diff=log2r_diff)
    write.table(mapd_df, file=file.path(argv$outdir, paste0(sampleID, ".log2r.mapd.tsv")), sep="\t", quote=F, row.names=F, col.names=T)
    write.table(data.frame(MAPD=median(log2r_diff, na.rm=TRUE)),
                file=file.path(argv$outdir, paste0(sampleID, ".log2r.mapd.summary.tsv")), sep="\t", quote=F, row.names=F, col.names=T)

    # .ctrl.norm.RData
    ctrlIDs <- names(ctrlSamples[[sampleID]]$CORX)
    if (length(ctrlIDs) > 0) {
        ctrl_norm_mat <- raw_data[, ctrlIDs, drop=FALSE]
        save(ctrl_norm_mat, file=file.path(argv$outdir, paste0(sampleID, ".ctrl.norm.RData")))
    }

    # .cnvRef.RData
    ref_stats <- data.frame(
        chrom = raw_data$chrom,
        start = raw_data$begin,
        end = raw_data$end,
        mean = currRefStats$mean,
        median = currRefStats$median,
        sd = currRefStats$sd,
        cv = ifelse(currRefStats$mean != 0, currRefStats$sd / currRefStats$mean, NA)
    )
    save(ref_stats, file=file.path(argv$outdir, paste0(sampleID, ".cnvRef.RData")))

    # Build external controls CN data frame (if gene annotation provided)
    ctrlDF <- NULL
    if (!is.null(geneAnno)) {
        ctrlData_numeric <- as.matrix(raw_data[, ctrlIDs, drop=FALSE])
        curr_median <- currRefStats$median
        ctrl_log2r <- log2((ctrlData_numeric + 0.01) / (curr_median + 0.01))
        ctrl_log2r <- sweep(ctrl_log2r, 2, apply(ctrl_log2r, 2, median, na.rm=TRUE), "-")
        ctrl_log2r[!is.finite(ctrl_log2r)] <- 0

        isFemale <- SexType[sampleID]
        baseCN <- rep(2, nrow(raw_data))
        if (isFemale) {
            baseCN[raw_data$chrom == "chrY"] <- 0.0015
        } else {
            baseCN[raw_data$chrom %in% c("chrX", "chrY")] <- 1
        }
        if (exists("parData") && nrow(parData) > 0) {
            chrRanges <- data.table(chrom = raw_data$chrom, start = raw_data$begin, end = raw_data$end)
            
            # X 染色体 PAR 区域
            parX <- parData[chrom == "X"]
            if (nrow(parX) > 0) {
                setkey(parX, chrom, begin, end)
                idxX <- foverlaps(chrRanges, parX, by.x = c("chrom", "start", "end"),
                                  type = "any", which = TRUE, nomatch = 0)
                if (length(idxX) > 0) {
                    if (max(idxX$xid) <= length(baseCN)) {
                        baseCN[idxX$xid] <- 2
                    } else {
                        warning("PAR X overlap index out of range for sample ", sampleID, ". Skipping.")
                    }
                }
            }
            
            # Y 染色体 PAR 区域
            parY <- parData[chrom == "Y"]
            if (nrow(parY) > 0) {
                setkey(parY, chrom, begin, end)
                idxY <- foverlaps(chrRanges, parY, by.x = c("chrom", "start", "end"),
                                  type = "any", which = TRUE, nomatch = 0)
                if (length(idxY) > 0) {
                    if (max(idxY$xid) <= length(baseCN)) {
                        baseCN[idxY$xid] <- 2
                    } else {
                        warning("PAR Y overlap index out of range for sample ", sampleID, ". Skipping.")
                    }
                }
            }
        }
        ctrlCN <- round(sweep(2^ctrl_log2r, 1, baseCN, "*"), 2)
        ctrlDF <- cbind(geneAnno[, 1:4], as.data.frame(ctrlCN))
    }

    # dotPlot (unchanged, uses global-like variables but they are in the environment)
    dotPlot(cData, sampleID, cCyto, Seg, SegZscore, CNVPolymorphism, CNVdisease, Chrs)

    # Return the collected data for later pedigree merging
    list(sample = sampleID,
         copy_number = cData$CopyNumber,
         ctrl_df = ctrlDF,
         mapd = log2r_diff)
}, ctrlSamples = CtrlSampleslsls,      # 传递主进程的变量
   refStatsList = sampleRefStats,
   raw_data = raw_data,
   geneAnno = geneAnno_local,
   SexType = sexType_local,
   Cyto = cyto_local,
   parData = parData_local,
   CNVPolymorphism = cnvPolymorphism_local,
   CNVdisease = cnvDisease_local,
   Chrs = chrs_local,
   argv = argv_local,
   centromere = centromere_local,
   cCyto = cCyto_local,
   MosRatioCutoff = mosRatioCutoff_local,
   mc.cores = 8)

# ===== Collect results =====
all_copy_numbers <- setNames(lapply(results, `[[`, "copy_number"), sampleIDs)
ctrl_cn_data_list <- setNames(lapply(results, `[[`, "ctrl_df"), sampleIDs)
# Remove NULL entries
ctrl_cn_data_list <- ctrl_cn_data_list[!sapply(ctrl_cn_data_list, is.null)]
# Also collect MAPD if needed
MAPD <- setNames(lapply(results, function(x) median(x$mapd, na.rm=TRUE)), sampleIDs)
print(MAPD)

# ===== Write .ctrl.copynumber.txt with pedigree members =====
if (!is.na(argv$geneAnnbed) && length(ctrl_cn_data_list) > 0) {
    for (sid in sampleIDs) {
        if (!sid %in% names(ctrl_cn_data_list)) next
        base_df <- ctrl_cn_data_list[[sid]]
        
        # 1. 提取注释列（假设前4列为 chrom, start, end, gene_name）
        anno_df <- base_df[, 1:4, drop = FALSE]
        # 确保染色体列带有 "chr" 前缀
        if (!all(grepl("^chr", anno_df[,1]))) {
            anno_df[,1] <- paste0("chr", anno_df[,1])
        }
        
        # 2. 提取外部对照列（注释列之后的所有列）
        ext_df <- base_df[, 5:ncol(base_df), drop = FALSE]
        ext_colnames <- colnames(ext_df)
        
        # 3. 自身列（从 all_copy_numbers 获取，已两位小数）
        self_vec <- round(all_copy_numbers[[sid]], 2)
        self_df <- data.frame(self_vec, check.names = FALSE)
        colnames(self_df) <- sid
        
        # 4. 家系成员列（同家系其他样本，且不在外部对照中）
        ped_df <- NULL
        if (!is.null(sample2ped) && sid %in% names(sample2ped)) {
            ped_id <- sample2ped[[sid]]
            other_members <- names(sample2ped)[sample2ped == ped_id & names(sample2ped) != sid]
            if (length(other_members) > 0) {
                # 排除已经在外部对照中的成员
                ped_members <- setdiff(other_members, ext_colnames)
                if (length(ped_members) > 0) {
                    ped_list <- lapply(ped_members, function(mem) {
                        if (mem %in% names(all_copy_numbers)) {
                            round(all_copy_numbers[[mem]], 2)
                        } else {
                            flog.warn("Copy number for pedigree member %s not found, using NA", mem)
                            rep(NA, nrow(base_df))
                        }
                    })
                    ped_df <- as.data.frame(do.call(cbind, ped_list))
                    colnames(ped_df) <- ped_members
                }
            }
        }
        
        # 5. 按顺序合并：注释列 + 自身列 + 家系成员列 + 外部对照列
        final_df <- anno_df
        final_df <- cbind(final_df, self_df)
        if (!is.null(ped_df)) final_df <- cbind(final_df, ped_df)
        final_df <- cbind(final_df, ext_df)
        
        # 6. 写入文件
        out_file <- file.path(argv$outdir, paste0(sid, ".ctrl.copynumber.txt"))
        write.table(final_df, out_file, sep = "\t", quote = FALSE, row.names = FALSE, col.names = TRUE)
        flog.info("Written control copy number file for %s", sid)
    }
} else if (!is.na(argv$geneAnnbed)) {
    flog.warn("No control copy number data frames generated; check gene annotation and sample processing.")
}

# ===== Global outputs: All.chrom.CN.tsv and heatmaps =====
cnFiles <- Sys.glob(file.path(argv$outdir, "*_ploidy.tsv"))
if (length(cnFiles) > 0) {
    # Use a safer approach: read each file and combine
    cn_list <- list()
    for (f in cnFiles) {
        sample <- gsub("_ploidy.tsv", "", basename(f))
        dat <- read.table(f, header=TRUE, sep="\t", stringsAsFactors=FALSE)
        dat$sampleID <- sample
        cn_list[[sample]] <- dat
    }
    CNdata <- do.call(rbind, cn_list)
    CNcasted <- reshape2::dcast(CNdata, chrom ~ sampleID, value.var="CopyNumber")
    write.table(CNcasted, file=file.path(argv$outdir, argv$chromCN), sep="\t", quote=FALSE, row.names=F, col.names=T)

    pCN <- ggplot(CNdata, aes(x=sampleID, y=chrom)) + geom_tile(aes(color=as.numeric(CopyNumber), fill=as.numeric(CopyNumber))) +
        scale_colour_gradient2(midpoint=2, limits=c(0,4), low="blue", mid="white", high="red") +
        scale_fill_gradient2(midpoint=2, limits=c(0,4), low="blue", mid="white", high="red") +
        theme(axis.text.x = element_text(angle=70, size=5, hjust=1), axis.text.y = element_text(size=5),
              panel.background = element_blank(), legend.position="bottom", plot.margin=unit(c(0,0,0,1),'cm'), panel.spacing=unit(0.1,"lines"))
    ggsave(file.path(argv$outdir, argv$heatmapCN), width=16, height=9, dpi=256, device='png')
}

# ===== Merge log2R tracks =====
log2rFiles <- Sys.glob(file.path(argv$outdir, "*.normalize.bed"))
if (length(log2rFiles) > 0) {
    first_norm_file <- log2rFiles[1]
    CMD <- paste0("head -n 1 ", first_norm_file, " | awk -F\"\t\" '{print NF}'")
    NumberField <- as.numeric(system(CMD, intern = TRUE))
    # Build command with full paths
    file_list_str <- paste(log2rFiles, collapse = " ")
    
    # 基础命令（合并所有文件）
    base_cmd <- paste0(
        "(ls ", file_list_str, " | perl -ne 'chomp;push @a,$_;if(eof){print \"#chr\\tstart\\tend\\t\",join(\"\\t\",map {my $bn=$_;$bn=~s|^.*/||;$bn=~s/\\.normalize\\.bed$//;$bn.\"_log2r\"} @a),\"\\n\"}' ; ",
        "ls ", file_list_str, " | perl -ne 'chomp;push @a,$_;if(eof){print \"cut -f1-3 $a[0] | sort -k1,1V -k2,2n -k3,3n |paste - \",join(\"\\t\",map {\"<(sort -k1,1V -k2,2n -k3,3n $_ | awk '\\''{print \\$4}'\\'')\"}  @a),\"\\n\";}'|bash)"
    )
    
    # 版本1：保留chr（原始版本）
    CMD1 <- paste0(
        base_cmd, " | ",
        bgzip, " -c -@8 > ", file.path(argv$outdir, "All.join.log2r.with_chr.bed.gz"),
        " && ", tabix, " -p bed ", file.path(argv$outdir, "All.join.log2r.with_chr.bed.gz")
    )
    system(CMD1)
    
    # 版本2：去掉chr
    CMD2 <- paste0(
        base_cmd, " | ",
        "awk 'BEGIN{OFS=\"\\t\"} {if(NR==1){print; next} {sub(/^chr/,\"\",$1); print}}' | ",
        bgzip, " -c -@8 > ", file.path(argv$outdir, "All.join.log2r.bed.gz"),
        " && ", tabix, " -p bed ", file.path(argv$outdir, "All.join.log2r.bed.gz")
    )
    system(CMD2)
}

# ===== Merge segments for combined heatmap =====
if (!file.exists(file.path(argv$outdir, "merge.bed"))) {
    segFiles <- Sys.glob(file.path(argv$outdir, "*_seg.tsv"))
    if (length(segFiles) > 0) {
        segFile_str <- paste(segFiles, collapse=" ")
        CMD <- paste0("ls ", segFile_str," | xargs -i echo \"sed '1d' {} | cut -f2-4\""," | bash"," | sort -k1,1V -k2,2n -k3,3n"," | awk 'BEGIN{OFS=\"\\t\"} {if($1!~/^chr/) $1=\"chr\"$1; print}'"," | ", bedtools, " merge >", file.path(argv$outdir, "merge.bed"))
        system(CMD)
    }
}

if (file.exists(file.path(argv$outdir, "merge.bed")) && file.exists(file.path(argv$outdir, "All.join.log2r.with_chr.bed.gz"))) {
    CNVdata <- read.table(pipe(paste(tabix, " -hfp bed -R", file.path(argv$outdir, "merge.bed"), file.path(argv$outdir, "All.join.log2r.with_chr.bed.gz"))), header = T, sep = "\t", check.names = F, comment.char = "!", stringsAsFactors = F, fileEncoding = "UTF-8")
    if (nrow(CNVdata) > 0) {
        colnames(CNVdata)[1] <- gsub("#","",colnames(CNVdata)[1])
        if(!chrBool) CNVdata <- CNVdata %>% mutate(chr = gsub("[Cc]hr","",chr,perl=T))
        CNVdata <- CNVdata %>% mutate(idx = do.call(c, tapply(start, factor(chr, levels=Chrs), seq_along)))
        idNames <- c("chr","start","end","idx")
        if ("gene" %in% colnames(CNVdata)) {
            idNames <- c("chr","start","end","gene","idx")
            if (any(c("polymorphism","mapability") %in% colnames(CNVdata))) {
                idNames <- c("chr","start","end","gene","polymorphism","mapability","idx")
            }
        }
        mCNVdata <- melt(CNVdata, id=idNames, variable="sampleID") %>% mutate(sampleID = gsub("_log2r","",sampleID,perl=T,ignore.case=T))
        mCNVdata$chr <- factor(mCNVdata$chr, levels=Chrs)

        pp1 <- ggplot(mCNVdata, aes(x=start, y=sampleID)) + 
            geom_tile(aes(color=as.numeric(value), fill=as.numeric(value))) +
            scale_colour_gradient2(midpoint=0, limits=c(-1.2,1.2), low="blue", mid="white", high="red") + 
            scale_fill_gradient2(midpoint=0, limits=c(-1.2,1.2), low="blue", mid="white", high="red") + 
            facet_grid(chr~., scales="free_x", space="free_x") +
            scale_x_continuous(expand = c(0, 0)) +
            theme(axis.text.x = element_text(angle=70, size=5, hjust=1), axis.text.y = element_text(size=5),
                  panel.background = element_blank(), legend.position="bottom", plot.margin = unit(c(0,0,0,1),'cm'), panel.spacing = unit(0.1, "lines"))
        ggsave(file.path(argv$outdir, "heatmap.png"), width=18, height=32, dpi=256, device='png')

        N_samples <- length(sampleIDs)
        timesN_samples <- N_samples %/% 20
        if (timesN_samples > 16) timesN_samples <- 16
        if (timesN_samples < 1) timesN_samples <- 1
        pp2 <- ggplot(mCNVdata, aes(x=idx, y=sampleID)) + 
            geom_tile(aes(color=as.numeric(value), fill=as.numeric(value))) +
            scale_colour_gradient2(midpoint=0, limits=c(-1.2,1.2), low="blue", mid="white", high="red") + 
            scale_fill_gradient2(midpoint=0, limits=c(-1.2,1.2), low="blue", mid="white", high="red") + 
            facet_grid(.~chr, scales="free_x", space="free_x") +
            scale_x_continuous(expand = c(0, 0)) +
            theme(axis.text.x = element_text(angle=70, size=5, hjust=1), axis.text.y = element_text(size=5),
                  panel.background = element_blank(), legend.position="right", plot.margin = unit(c(0,0,0,1),'cm'), panel.spacing = unit(0.1, "lines"))
        ggsave(file.path(argv$outdir, "heatmap_h.png"), width=24, height=3*timesN_samples, dpi=256, device='png')

        pp3 <- ggplot(mCNVdata, aes(x=start, y=sampleID)) + 
            geom_tile(aes(color=as.numeric(value), fill=as.numeric(value))) +
            scale_colour_gradient2(midpoint=0, limits=c(-1.2,1.2), low="blue", mid="white", high="red") +
            scale_fill_gradient2(midpoint=0, limits=c(-1.2,1.2), low="blue", mid="white", high="red") + 
            facet_grid(.~chr, scales="free_x", space="free_x") +
            scale_x_continuous(expand = c(0, 0)) +
            theme(axis.text.x = element_text(angle=70, size=5, hjust=1), axis.text.y = element_text(size=5),
                  panel.background = element_blank(), legend.position="right", plot.margin = unit(c(0,0,0,1),'cm'), panel.spacing = unit(0.1, "lines"))
        ggsave(file.path(argv$outdir, "heatmap_pos_h.png"), width=24, height=3*timesN_samples, dpi=256, device='png')
    }
}