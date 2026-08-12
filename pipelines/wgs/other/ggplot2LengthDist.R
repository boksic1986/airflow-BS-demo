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
	Rscript %s D191220P2-DZX00074U_L3.iSizeFreq.tsv D191220P2-DZX00074U_L3.iSize 500
	ls *iSizeFreq.tsv|perl -ne 'chomp;$s=$_; $s=~s/\\.tsv$//;print \"Rscript %s $_ $s 1000\\n\"'|bash
Usage:
	Rscript %s infile outfile",program,program,program)
	)
}

infile <- args[1]
outfile <- args[2]
length_cutoff <- as.numeric(args[3])
library(ggplot2)
options(scipen=999)
options(bitmapType='cairo')
Data<-read.table(infile,header=F)

find_peaks <- function (x, m = 3){
    shape <- diff(sign(diff(x, na.pad = FALSE)))
    pks <- sapply(which(shape < 0), FUN = function(i){
       z <- i - m + 1
       z <- ifelse(z > 0, z, 1)
       w <- i + m + 1
       w <- ifelse(w < length(x), w, length(x))
       if(all(x[c(z : i, (i + 2) : w)] <= x[i + 1])) return(i + 1) else return(numeric(0))
    })
     pks <- unlist(pks)
     pks
}
# aa=100:1
# bb=sin(aa/3)
# cc=aa*bb
# plot(cc, type="l")
# abline(v=find_peaks(cc))

DF<-data.frame(length=as.numeric(Data[1,]),count=as.numeric(Data[2,])/sum(as.numeric(Data[2,])))
theme_update(plot.title = element_text(hjust = 0.5))
xx<-as.numeric(Data[1,])
yy<-as.numeric(Data[2,])
zz<-find_peaks(yy)
Xx<-xx[zz]
Xx<-Xx[Xx>=100 & Xx<=length_cutoff]
cat(Xx,"\n",sep="\t")
P<-ggplot(DF, aes(x=length, y=count)) + 
	geom_line(colour = 'blue') + 
	scale_x_continuous(expand = c(0, 0)) +
	coord_cartesian(xlim=c(0,length_cutoff)) +
	xlab("length(bp)") + 
    ylab("count") +
	ggtitle("cfDNA length Distribution")+
	geom_vline(xintercept = Xx,linetype="dashed", color = "orange", size=0.5)+
	annotate("text",x=Xx,y=0,label=Xx,hjust=0.5,size=1.5,angle=90)
ggsave(paste0(outfile, ".png"), width=16, height=9,dpi=200,device='png')

