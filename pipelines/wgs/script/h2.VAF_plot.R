#!/usr/bin/env Rscript

#is_inst2 <- function(pkg) {
#    pkg %in% rownames(installed.packages()) # 
#}
#if (is_inst2('packrat')) packrat::off()
library(argparser, quietly = TRUE)
library(parallel,quietly=TRUE)
suppressPackageStartupMessages(library(dplyr));
library(ggplot2)
library(ggnewscale)
library(Cairo)
library(scales)
options(bitmapType = "cairo")
options(scipen = 999)
library(gridExtra)
library(ggh4x)

p <- arg_parser("VAF") %>%
    add_argument('--vaf', help='result of vcf2vaf.',type="character") %>%
    add_argument('--roh', help='result of automap.',type="character") %>%
    add_argument('--UPD', help='CNV disease File.', type="character",default="/bi/8.xuxiong/work/WES/Pathogenic_UPD.bed") %>%
    add_argument('--cytoband', help='cytoband File.',type="character",default="/bi/database/cytoBand.txt.gz") %>%
    add_argument('--genome', help='Path to genome vaf output PNG file.',type="character",default="VAF.genome.png") %>%
    add_argument('--chrs', help='Path to genome vaf output PNG file.',type="character",default="VAF.chrs.png") %>%
    add_argument('--density', help='Path to vaf density output PNG file.',type="character",default="VAF.density.png");

argv <- parse_args(p)
cat('Arguments are as follows\n',file=stderr())
str(argv)

sample = gsub('\\.vaf$','', basename(argv$vaf),perl=TRUE)

chrs = c("1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","X","Y")
colors <- c('#4682B4','#6B8E23','#87CEEB','#A0522D','#FF8C00','#6A5ACD','#778899','#DAA520','#B22222','#FF6699')
args = commandArgs(trailingOnly=TRUE)
x <- read.table(argv$vaf, header=T,check.names = FALSE,stringsAsFactors = FALSE)
hasChr <- grepl('^chr',x[1,1], ignore.case = TRUE, perl = TRUE)
if (hasChr) {
    chrs<-paste0('chr',chrs)
    print(chrs)
}
x <- x[x$chr %in% chrs,]
loadCytoBand<-function(cytoRData,trimChr=TRUE){#
        cyto<-NA
        if (grepl('\\.RData',cytoRData,perl=TRUE)){
                load(cytoRData)
        }else{
                data<-read.delim(cytoRData,header=F)
                cyto<-data[nchar(as.character(data[,1]))<=5 & as.character(data[,1])!="chrM" ,]
        }
        colnames(cyto)<-c("chr","start","end","name","type")
        cyto$Color<-NA
        cyto[cyto$type=="gneg",]$Color<-rgb(255,255,255, maxColorValue=255)
        cyto[cyto$type=="gpos25",]$Color<-rgb(200,200,200, maxColorValue=255)
        cyto[cyto$type=="gpos50",]$Color<-rgb(200,200,200, maxColorValue=255)
        cyto[cyto$type=="gpos75",]$Color<-rgb(130,130,130, maxColorValue=255)
        cyto[cyto$type=="gpos100",]$Color<-rgb(200,200,200, maxColorValue=255)
        cyto[cyto$type=="acen",]$Color<-"red"            # centromere
        cyto[cyto$type=="stalk",]$Color<-rgb(100,127,164, maxColorValue=255)   # repeat regions
        cyto[cyto$type=="gvar",]$Color<-rgb(220,220,220, maxColorValue=255)       # indented region
	if(trimChr) cyto$chr <- gsub("chr","",cyto$chr)
        chrs<-split(cyto,factor(cyto$chr))
        cat("Done loaded cytoband\n",file=stderr())
        chrs
}
loadUPDdisease<-function(UPDdiseaseFile,chrBool){
    data<-read.table(UPDdiseaseFile,header=F,sep="\t",comment.char = "!",stringsAsFactors = F,
                check.names = F,col.names=c('chr','start','end','UPDdisease'))
    if (!chrBool) data$chr<-gsub("[cC]hr","",data$chrom,perl=T)
    cat("Done loaded UPD\n",file=stderr())
    data
}

if (!is.na(argv$UPD) && file.exists(argv$UPD)){
    UPDdisease<-loadUPDdisease(argv$UPD,hasChr)
    UPDdisease$chr<-factor(UPDdisease$chr, levels = chrs)
}

Cyto<-loadCytoBand(argv$cytoband,!hasChr)
x$col<-unlist(sapply(chrs,function(X){
	ifelse(findInterval(x[x$chr %in% X,2],as.numeric(c(Cyto[[X]][,2],Cyto[[X]][nrow(Cyto[[X]]),3])),rightmost.closed = TRUE)%%2==1,"A","B")
}))
x$chr = factor(x$chr, levels=chrs)
cCyto<-do.call(rbind,Cyto)
cCyto$chr <- factor(cCyto$chr, levels = chrs)
Ymin=0;Ymax=1
pacen<-cCyto %>% filter(as.character(type) == "acen" & substring(name, 1, 1)=="p")
pter<-data.frame(chr=rep(pacen$chr,each=3),x=c(rbind(pacen$start,pacen$end,pacen$start)),
    y=rep(c(Ymin-0.16,Ymin-0.085,Ymin-0.01),length(pacen$type)),type=rep(pacen$type,each=3))
qacen<-cCyto %>% filter(as.character(type) == "acen" & substring(name, 1, 1)=="q")
qter<-data.frame(chr=rep(qacen$chr,each=3),x=c(rbind(qacen$start,qacen$end,qacen$end)),
    y=rep(c(Ymin-0.085,Ymin-0.16,Ymin-0.01),length(qacen$type)),type=rep(qacen$type,each=3))

plot_vaf_density<-function(Outfile,Data,MaxX,Type="h",Ylab="Density of VAF"){
    colors <- c('#4682B4','#A0522D','#FF8C00','#87CEEB','#6B8E23','#6A5ACD','#778899','#DAA520','#B22222','#FF6699')
    png(Outfile,pointsize=18,width=900,height=600)
    # CairoPNG(Outfile,width = 900,height = 600,res = 256);
    par(mar=c(5.1,4.5,4.1,2.1))
    plot(Data,
        type=Type,
        xlab="VAF",
        ylab=Ylab,
        col=colors[1],
        xaxt='n',
        pch=1,
        font.lab=1.2,font.main=2,font.axis=1,lwd=2,
        cex.lab=1.5,cex.main=1.5,cex.axis=1,cex.sub=1,cex=0.5,
        main=list("Variant Allele Fraction Density Distribution")
    )
    axis(1,at=seq(0,1,0.2),label=as.character(seq(0,1,0.2)),las=2,srt = 0)
    abline(v=MaxX,col=colors[2],lty=3)
    if (class(Data) == "table"){
        legend("topright",legend=paste("max value at :",MaxX,".",sep=" "),cex=0.8,inset = 0.01)
    }
    if (class(Data) == "density"){
        Lab <- c(paste("0.28 - 0.33 sum of fraction: ",round(sum(Data$y[Data$x>=0.28 & Data$x<=0.38])/sum(Data$y),digits =6),sep=''),
            paste("0.45 - 0.55 sum of fraction: ",round(sum(Data$y[Data$x>=0.45 & Data$x<=0.55])/sum(Data$y),digits =6),sep=''),
            paste("0.62 - 0.72 sum of fraction: ",round(sum(Data$y[Data$x>=0.62 & Data$x<=0.72])/sum(Data$y),digits =6),sep=''))
        legend("topright",legend=Lab,cex=0.8,inset = 0.01)
    }
    box()
    pic=dev.off()
    cat("Done plot Data_range\n",file=stderr())
}

if (file.exists(argv$roh) && as.integer(system(paste0("grep -v -P '^#' ",argv$roh," | wc -l"),intern=T)) > 0 ){
    Seg<-read.table(argv$roh,header=F,comment.char="#")
    colnames(Seg)<-c("chr","start","end","Size(Mb)","Nb_variants","Percentage_homozygosity")
    Seg$chr<-factor(Seg$chr, levels = chrs)
}

Dens <- density(x[x[,5]>0.01 & x[,5]<0.99,5],n=10000)
plot_vaf_density(argv$density,Dens,Dens$x[which.max(Dens$y)],"l","Fraction")
df <- data.frame(chr=x$chr, start=x$start + (x$end - x$start) / 2, vaf=x[,5],col=x$col)  %>% filter(as.numeric(vaf) >=0.01 & as.numeric(vaf) <=0.99)
p1 <- ggplot(data=df, aes(x=start, y=vaf))+
    geom_point( size=0.1,aes(colour =col))+scale_color_manual(values=c(A=colors[1],B=colors[7]))+
    geom_hline(yintercept=c(0.00,0.25,0.5,0.75,1.00), linetype=2, color = "springgreen4", linewidth=0.25) +
    xlab("Chromosome") + ylab("Variant Allele Frequency") +
    facet_grid(chr ~ ., scales="free_x", space="free_x") +
    coord_cartesian(ylim=c(Ymin-0.5, Ymax)) +
    geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=Ymin, ymax=Ymax),fill=NA,size=0.5,color='#7E3D76',alpha=0.2) +
    #geom_segment(data=UPDdisease,inherit.aes=FALSE,mapping=aes(x=start, xend=end, y=Ymax+0.01, yend=Ymax+0.01),color='#7E3D76', linewidth=0.8,linetype=1,alpha=0.4) +
    geom_rect(data=cCyto %>% filter(as.character(type) != "acen"),inherit.aes=FALSE, mapping=aes(xmin=start, xmax=end, ymin=Ymin-0.16, ymax=Ymin-0.01, fill=type),color='black',size=0.01) +
    geom_polygon(data = pter,inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',size=0.01) +
    geom_polygon(data = qter,inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',size=0.01) +
    scale_fill_manual(values=c("stalk"="#647FA4","gpos25"="#C8C8C8","gpos50"="#C8C8C8","gpos75"="#828282","gpos100"="#C8C8C8","gvar"="#DCDCDC","gneg"="#FFFFFF","acen"="red")) +
    scale_x_continuous(expand = c(0, 0))+ scale_y_continuous(breaks = seq(from=Ymin,to=Ymax,by=0.25)) +
    geom_text(data=cCyto,inherit.aes=FALSE,aes(x=start+(end-start)/2, y=Ymin-0.38, label=paste(gsub("[Cc]hr","",chr,perl=T),name,sep='')),size=1.1,angle=45)
if (file.exists(argv$roh) && as.integer(system(paste0("grep -v -P '^#' ",argv$roh," | wc -l"),intern=T)) > 0 ){
    p1<-p1+geom_rect(data=Seg,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=0, ymax=1),fill='#FF6347',size=0.1,color=NA,alpha=0.3) +
        theme(axis.text.x = element_text(angle=15,size=5, hjust=1),axis.text.y = element_text(size=5),panel.background = element_blank(),panel.grid.major = element_blank(),panel.grid.minor = element_blank(),legend.position="none")
}else{
    p1<-p1+theme(axis.text.x = element_text(angle=15,size=5, hjust=1),axis.text.y = element_text(size=5),panel.background = element_blank(),panel.grid.major = element_blank(),panel.grid.minor = element_blank(),legend.position="none")
}
ggsave(argv$chrs, width=12, height=18,dpi = 256,device='png')
p3 <- ggplot(data=df, aes(vaf))+
    geom_density(alpha = 0.1,adjust = 1/3) +
    geom_vline(xintercept=c(0.25,0.5,0.75), linetype=2, color = "springgreen4", linewidth=0.25) +
    xlab("VAF") + ylab("density") +
    facet_grid(. ~ chr, scales="free") +
    force_panelsizes(cols = as.numeric(sapply(chrs,function(X){Cyto[[X]][nrow(Cyto[[X]]),3]})),rows = NULL, respect = NULL)+
    scale_x_continuous(expand = c(0, 0))+
    theme(axis.text.x = element_text(angle=15,size=4, hjust=1),axis.text.y = element_text(size=5),
        panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
        legend.position="none",panel.spacing = unit(0.1, "lines"))
pdf(NULL)
p2 <- ggplot(data=df, aes(x=start, y=vaf))+
    geom_point( size=0.1,aes(colour =col))+
    scale_color_manual(values=c(A=colors[1],B=colors[7]))+
    # geom_point()+
    stat_density2d(aes(alpha = ..density..),geom = "raster", contour = FALSE)+
    # geom_density_2d()+
    geom_hline(yintercept=c(0.00,0.25,0.5,0.75,1.00), linetype=2, color = "springgreen4", linewidth=0.25) +
    xlab("Chromosome") + ylab("Variant Allele Frequency") +
    facet_grid(. ~ chr, scales="free_x", space="free_x") +
    coord_cartesian(ylim=c(Ymin-0.3, Ymax)) +
    #geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=Ymin, ymax=Ymax),fill=NA,size=0.5,color='#7E3D76',alpha=0.2) +
    #geom_segment(data=UPDdisease,inherit.aes=FALSE,mapping=aes(x=start, xend=end, y=Ymax+0.01, yend=Ymax+0.01),color='#7E3D76', linewidth=0.8,linetype=1,alpha=0.4) +
    geom_rect(data=cCyto %>% filter(as.character(type) != "acen"),inherit.aes=FALSE, mapping=aes(xmin=start, xmax=end, ymin=Ymin-0.16, ymax=Ymin-0.01, fill=type),color='black',size=0.01) +
    geom_polygon(data = pter,inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',size=0.01) +
    geom_polygon(data = qter,inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',size=0.01) +
    scale_x_continuous(expand = c(0, 0))+ scale_y_continuous(breaks = seq(from=Ymin,to=Ymax,by=0.25)) +
    scale_fill_manual(values=c("stalk"="#647FA4","gpos25"="#C8C8C8","gpos50"="#C8C8C8","gpos75"="#828282","gpos100"="#C8C8C8","gvar"="#DCDCDC","gneg"="#FFFFFF","acen"="red")) +
    geom_text(data=cCyto,inherit.aes=FALSE,aes(x=start+(end-start)/2, y=Ymin-0.25, label=paste(gsub("[Cc]hr","",chr,perl=T),name,sep='')),size=0.8,angle=70)
if (file.exists(argv$roh) &  as.integer(system(paste0("grep -v -P '^#' ",argv$roh," | wc -l"),intern=T)) > 0 ){
    p2 <- p2+geom_rect(data=Seg,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=0, ymax=1),fill='#FF6347',size=0.01,color=NA,alpha=0.3) +
        theme(axis.text.x = element_text(angle=15,size=4, hjust=1),axis.text.y = element_text(size=5),
        #panel.background = element_blank(),
        panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
        legend.position="none",panel.spacing = unit(0.1, "lines"))
}else{
    p2 <- p2+theme(axis.text.x = element_text(angle=15,size=4, hjust=1),axis.text.y = element_text(size=5),
        #panel.background = element_blank(),
        panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
        legend.position="none",panel.spacing = unit(0.1, "lines"))
}
ggsave(argv$genome, width=24, height=4,dpi = 256,device='png')
# ggsave(argv$genome, width=24, height=5,dpi = 256,device='png',plot = marrangeGrob(list(p3,p2), nrow=2, ncol=1))

p4 <- ggplot(data=df %>% filter(!grepl('X$|Y$',chr,ignore.case = TRUE, perl = TRUE)), aes(x=start, y=vaf)) +
    geom_point( size=0.1,aes(colour =col))+
    scale_color_manual(values=c(A=colors[1],B=colors[7]))+
    # geom_point()+
    stat_density2d(aes(alpha = ..density..),geom = "raster", contour = FALSE)+
    # geom_density_2d()+
    geom_hline(yintercept=c(0.00,0.25,0.5,0.75,1.00), linetype=2, color = "springgreen4", linewidth=0.25) +
    xlab("Chromosome") + ylab("Variant Allele Frequency") +
    facet_grid(. ~ chr, scales="free_x", space="free_x") +
    coord_cartesian(ylim=c(Ymin-0.3, Ymax)) +
    #geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=Ymin, ymax=Ymax),fill=NA,size=0.5,color='#7E3D76',alpha=0.2) +
    #geom_segment(data=UPDdisease,inherit.aes=FALSE,mapping=aes(x=start, xend=end, y=Ymax+0.01, yend=Ymax+0.01),color='#7E3D76', linewidth=0.8,linetype=1,alpha=0.4) +
    geom_rect(data=cCyto %>% filter(as.character(type) != "acen" & !grepl('X$|Y$',chr,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE, mapping=aes(xmin=start, xmax=end, ymin=Ymin-0.16, ymax=Ymin-0.01, fill=type),color='black',size=0.01) +
    geom_polygon(data = pter %>% filter(!grepl('X$|Y$',chr,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',size=0.01) +
    geom_polygon(data = qter %>% filter(!grepl('X$|Y$',chr,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',size=0.01) +
    scale_x_continuous(expand = c(0, 0))+ scale_y_continuous(breaks = seq(from=Ymin,to=Ymax,by=0.25)) +
    scale_fill_manual(values=c("stalk"="#647FA4","gpos25"="#C8C8C8","gpos50"="#C8C8C8","gpos75"="#828282","gpos100"="#C8C8C8","gvar"="#DCDCDC","gneg"="#FFFFFF","acen"="red")) +
    geom_text(data=cCyto %>% filter(!grepl('X$|Y$',chr,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,aes(x=start+(end-start)/2, y=Ymin-0.25, label=paste(gsub("[Cc]hr","",chr,perl=T),name,sep='')),size=0.8,angle=70)
if (file.exists(argv$roh) &  as.integer(system(paste0("grep -v -P '^#' ",argv$roh," | wc -l"),intern=T)) > 0 ){
    p4 <- p4 + geom_rect(data=Seg %>% filter(!grepl('X$|Y$',chr,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=0, ymax=1),fill='#FF6347',size=0.01,color=NA,alpha=0.3) +
        theme(axis.text.x = element_text(angle=15,size=4, hjust=1),axis.text.y = element_text(size=5),
        panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
        legend.position="none",panel.spacing = unit(0.1, "lines"))
}else{
    p4 <- p4 + theme(axis.text.x = element_text(angle=15,size=4, hjust=1),axis.text.y = element_text(size=5),
        panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
        legend.position="none",panel.spacing = unit(0.1, "lines"))
}
ggsave(paste0(argv$genome,'_noXY.png'), width=24, height=4,dpi = 256,device='png')
print(warnings())
