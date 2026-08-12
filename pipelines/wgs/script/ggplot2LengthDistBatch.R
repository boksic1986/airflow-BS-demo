#!/usr/bin/env Rscript
rm(list=ls())
getProgramName<-function(arguments){
	args <- commandArgs(trailingOnly = FALSE)
	sub("--file=", "", args[grep("--file=", args)])
}
program <- getProgramName()
args <- commandArgs(trailingOnly = TRUE)
if (length(args)<2) {
	stop(sprintf("Please input the information of arguments:
	args[1]		infile
	args[2]		outfile
	args[3]     length_cutoff
Example:
	Rscript %s /data1/data/xuxiong/urine_cfDNA/20191101 urine_cfDNA_iSize 750
Usage:
	Rscript %s infile outfile",program,program,program)
	)
}

inDir <- args[1]
outfile <- args[2]
length_cutoff <- as.numeric(args[3])
library(ggplot2)
library(reshape2)
options(scipen=999)
options(bitmapType='cairo')
infiles<-Sys.glob(paste(inDir,"*iSizeFreq.tsv",sep=.Platform$file.sep))

plot_heatmap<-function(M,outfile){
    library(gplots)
    png(file =paste(outfile,"heatmap.png",sep='_'),height=900,width=600)
    # pdf(file =paste(outfile,'heatmap.pdf',sep='_'),height=9,width=6)#column
    heatmap.2(M, col=greenred(75), scale="none",key=TRUE,keysize=1,#,labRow=NA
        symkey=FALSE,density.info="histogram", trace="none", cexRow=0.8, cexCol=0.9, margins=c(10,10))
    dev.off()
}

Data<-do.call(cbind,lapply(infiles,function(X){
		D<-read.table(X,header=F)
		as.numeric(D[2,])/sum(as.numeric(D[2,]))
	}))
colnames(Data)<-gsub(".iSizeFreq.tsv","",basename(infiles),perl=T)
Data<-as.data.frame(Data)
insert_ranges<- c(97,117,126,146,175,200,250,300,350,400,500)
accumData<-apply(Data,2,function(X){
			tapply(X[97:500],findInterval(97:500,insert_ranges[-length(insert_ranges)]),sum)
		})

rownames(accumData)<-sapply(seq_along(insert_ranges)[-length(insert_ranges)],function(X){
	paste(insert_ranges[X:(X+1)],collapse=",")
})
if (ncol(accumData) >=2){
	plot_heatmap(t(accumData),file.path(dirname(outfile), "accumData"))
}
Data$length<-as.character(read.table(infiles[1],header=F)[1,])

DF<-melt(Data, id.var='length')

theme_update(plot.title = element_text(hjust = 0.5))
P<-ggplot(DF, aes(x=as.numeric(length), y=as.numeric(value),col =variable)) +
	geom_line() +
	scale_x_continuous(expand = c(0, 0)) +
	coord_cartesian(xlim=c(0,length_cutoff)) +
	xlab("Length(bp)") +
	ylab("Fraction") +
	ggtitle("cfDNA Length Distribution")

ggsave(paste0(outfile, ".png"), width=16, height=9,dpi=200,device='png')

