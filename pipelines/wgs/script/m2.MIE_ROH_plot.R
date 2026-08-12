#!/usr/bin/env Rscript
library(argparser, quietly = TRUE)
suppressPackageStartupMessages(library(VariantAnnotation))
library(ggplot2)
library(reshape2)
library(ggh4x, quietly = TRUE)
library(ggnewscale)
library(scales)
library(DNAcopy,quietly = TRUE)

suppressPackageStartupMessages(library(dplyr))
options(bitmapType = "cairo")
options(scipen = 999)

p <- arg_parser('MIE') %>%
    add_argument('--mie', help='vcf file.',type="character") %>%
    add_argument('--roh', help='result of automap.',type="character") %>%
    add_argument('--outfile', help='output prefix.',type="character") %>%
    add_argument('--cytoband', help='cytoband File.',type="character",default="/sg2/0.houmin/TargetSeqV6/CNV_Annotation_database/cytoBand.txt.gz") %>%
    add_argument('--UPD', help='UPD Disease File.',type="character",default="/sg2/0.houmin/TargetSeqV6/CNV_Annotation_database/Pathogenic_UPD.bed") %>%
    add_argument('--proband', help='proband sampleName.',type="character") %>%
    add_argument('--mappability', help='wgEncodeCrgMapabilityAlign100mer.',type="character",default="/sg2/0.houmin/TargetSeqV6/database/wgEncodeCrgMapabilityAlign100mer.bedGraph.gz") %>%
    add_argument('--Ymin', help='maximum depth', type="integer", default=0) %>%
    add_argument('--Ymax', help='maximum iSize', type="integer", default=9)

argv <- parse_args(p)
cat('Arguments are as follows\n',file=stderr())
str(argv)

for (name in c('mie','roh','cytoband','UPD')) {
    if (is.na(argv[[name]]) && !file.exists(argv[[name]])) {
        print(p);
        stop(sprintf('Argument %s is empty!', name))
    }
}

loadCytoBand<-function(cytoRData,ChrBool){
    cyto<-NA
    if (grepl('\\.RData',cytoRData,perl=TRUE)){
        load(cytoRData)
    }else{
        data<-read.delim(cytoRData,header=F)
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
# Shapes <- c(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15)
Colors <- c('#4682B4','#6B8E23','#87CEEB','#A0522D','#FF8C00','#6A5ACD','#778899','#DAA520','#B22222','#FF6699')
chroms <- c(as.character(1:22),"X","Y")
chroms<-paste0("chr",chroms)
Cyto<-loadCytoBand(argv$cytoband,TRUE)
cCyto<-do.call(rbind,Cyto)
cCyto$chrom <- factor(cCyto$chrom, levels = chroms)

Ymin<-argv$Ymin
Ymax<-argv$Ymax

param <- ScanVcfParam(fixed="ALT", info=c("DeNovo","iUPD_Pa","iUPD_Ma","MIE","UPD_Pa","UPD_Ma","Duo_Del"),geno=c("GT","AD","DP"))
# param <- ScanVcfParam(fixed="ALT", info=c("DeNovo","iUPDpat","iUPDmat","MIE","UPDpat","UPDmat","Duo_Del"),geno=c("GT","AD","DP"))
myVCF<-readVcf(argv$mie, "genome", param=param)
samples <- colnames(myVCF)
Proband <- ifelse(is.na(argv$proband),samples[1],argv$proband)

UMscore<-read.table(argv$mappability,header=FALSE,sep="\t",comment.char = "!",stringsAsFactors = FALSE,
                check.names = FALSE,col.names=c('chrom','start','end','score'))
UMscore$chrom <- factor(UMscore$chrom, levels = chroms)
UMscoreByChr<-split(UMscore,factor(UMscore$chrom))

df<-as.data.frame(cbind(chrom=as.character(rowRanges(myVCF)@seqnames),
    start=as.integer(rowRanges(myVCF)@ranges@start),
    sapply(seq_along(colnames(info(myVCF))),function(X){
        sapply(info(myVCF)[[X]],function(Y){ifelse(length(Y),X,NA)})
    })
))
colnames(df)<-c("chrom","start",colnames(info(myVCF)))
df$col <- apply(df[,colnames(info(myVCF))],1,function(X){ifelse(all(is.na(X)),NA,Colors[X[!is.na(X)]])})
df$alpha<-unlist(sapply(chroms,function(X){
	UMscoreByChr[[X]][findInterval(df[df$chrom %in% X,"start"],
        as.numeric(UMscoreByChr[[X]][,"start"]),rightmost.closed = FALSE),"score"]
}))
mdf <- melt(df,id.vars=c("chrom","start","col","alpha"),variable.name = "Type", value.name = "value") %>% filter(!is.na(value))
if(any(!(chroms %in% mdf$chrom))){
	mdf<-rbind(mdf,data.frame(chrom=chroms[!(chroms %in% mdf$chrom)],start =0,col = NA,alpha=0,Type="MIE",value=0))
}
mdf$chrom<- factor(mdf$chrom, levels = chroms)

VAF<-as.data.frame(cbind(chrom=as.character(rowRanges(myVCF)@seqnames),
    start=as.integer(rowRanges(myVCF)@ranges@start),
    sapply(samples,function(s){
        ad <- VariantAnnotation::geno(myVCF[,s])$AD
        ad.ref <- unlist(lapply(ad, "[", 1))
        ad.alt <- unlist(lapply(ad, "[", 2))
        baf <- ad.alt/(ad.alt+ad.ref)
        baf[is.nan(baf)] <- NA
        baf
    })
))
colnames(VAF)<-c("chrom","start",samples)
VAF$col<-unlist(sapply(chroms,function(X){
	ifelse(findInterval(VAF[VAF$chrom %in% X,"start"],
        as.numeric(c(Cyto[[X]][,2],Cyto[[X]][nrow(Cyto[[X]]),3])),rightmost.closed = TRUE)%%2==1,"A","B")
}))
VAF$alpha<-unlist(sapply(chroms,function(X){
	UMscoreByChr[[X]][findInterval(VAF[VAF$chrom %in% X,"start"],
        as.numeric(UMscoreByChr[[X]][,"start"]),rightmost.closed = FALSE),"score"]
}))
VAF$chrom = factor(VAF$chrom, levels=chroms)
mVAF <- melt(VAF,id.vars=c("chrom","start","col","alpha"),variable.name = "Type", value.name = "value") %>% filter(as.numeric(value) >=0.01 & as.numeric(value) <=0.99 & Type==Proband)
MDF<-rbind(cbind(mdf,variable=rep("MIE",times=nrow(mdf))),cbind(mVAF,variable=rep("VAF",times=nrow(mVAF))) )
MDF$chrom<- factor(MDF$chrom, levels = chroms)

UPDdisease<-read.table(argv$UPD,header=FALSE,sep="\t",comment.char = "!",stringsAsFactors = FALSE,
                check.names = FALSE,col.names=c('chrom','start','end','UPDdisease'))
UPDdisease$chrom <- factor(UPDdisease$chrom, levels = chroms)
UPDdisease$variable<-rep("MIE",times=nrow(UPDdisease))

pacen<-cCyto %>% filter(as.character(type) == "acen" & substring(name, 1, 1)=="p")
pter<-data.frame(chrom=rep(pacen$chrom,each=3),x=c(rbind(pacen$start,pacen$end,pacen$start)),
    y=rep(c(Ymin-1,Ymin-0.495,Ymin-0.01),length(pacen$type)),type=rep(pacen$type,each=3))
qacen<-cCyto %>% filter(as.character(type) == "acen" & substring(name, 1, 1)=="q")
qter<-data.frame(chrom=rep(qacen$chrom,each=3),x=c(rbind(qacen$start,qacen$end,qacen$end)),
    y=rep(c(Ymin-0.495,Ymin-1,Ymin-0.01),length(qacen$type)),type=rep(qacen$type,each=3))
pter$chrom<-factor(pter$chrom,levels=chroms)
qter$chrom<-factor(qter$chrom,levels=chroms)


Seg<-read.table(argv$roh,header=F,comment.char="#")
colnames(Seg)<-c("chrom","start","end","Size(Mb)","Nb_variants","Percentage_homozygosity")
Seg$chrom<-factor(Seg$chrom, levels = chroms)
Seg$variable<-rep("VAF",times=nrow(Seg))

name1<-c("iUPD_Pa","iUPD_Ma","UPD_Pa","UPD_Ma")
name2<-c("iUPDpat","iUPDmat","UPDpat","UPDmat")

# for (i in 1:length(name1)){
	# MDF$Type <- gsub ("name1[i]","name2[i]",MDF$Type)
	#MDF[MDF$Type==name1[i]]=name2[i]
# }
MDF$Type <- gsub ("iUPD_Pa","iUPDpat",MDF$Type)
MDF$Type <- gsub ("iUPD_Ma","iUPDmat",MDF$Type)
MDF$Type <- gsub ("UPD_Pa","UPDpat",MDF$Type)
MDF$Type <- gsub ("UPD_Ma","UPDmat",MDF$Type)
write.table(MDF,"mie.txt", row.names =F,sep ="\t")

#picture <- ggplot(data=MDF, aes(x=as.numeric(start), y=as.double(value))) +
picture <- ggplot(data=MDF, aes(x=as.numeric(value), y=as.double(start))) +
    geom_point(aes(colour=Type,shape=Type,alpha=alpha),size=0.8,data = ~ subset(., variable == "MIE")) +
    # scale_color_manual(values=c(DeNovo=Colors[1],iUPDpat=Colors[3],iUPDmat=Colors[4],MIE=Colors[5],UPDpat=Colors[6],UPDmat=Colors[7],Duo_Del=Colors[8])) +
	scale_color_manual(values=c(Colors[1],Colors[3],Colors[4],Colors[5],Colors[6],Colors[7],Colors[8])) +
    scale_shape_manual(values=seq(0,15))+
	# scale_shape_manual(values=c(DeNovo=Shapes[1],iUPDpat=Shapes[2],iUPDmat=Shapes[3],MIE=Shapes[4],UPDpat=Shapes[5],UPDmat=Shapes[6],Duo_Del=Shapes[7]))+
    new_scale_color()+
    geom_point(aes(colour=col,alpha=alpha),size=0.1,data = ~ subset(., variable == "VAF" & Type == Proband)) +
    scale_color_manual(values=c(A=Colors[1],B=Colors[7])) +
    # geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=Ymin, ymax=Ymax),fill='#111111',size=0.1,color=NA,alpha=0.1)
    # picture<-picture+geom_rect(data=Seg,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=0, ymax=1),fill='#FF6347',size=0.1,color=NA,alpha=0.3)
	geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=Ymin, xmax=Ymax, ymin=start, ymax=end),fill='#111111',size=0.1,color=NA,alpha=0.1)
    picture<-picture+geom_rect(data=Seg,inherit.aes=FALSE,mapping=aes(xmin=0, xmax=1, ymin=start, ymax=end),fill='#FF6347',size=0.1,color=NA,alpha=0.3)
    picture<-picture+xlab("Chromosome") + 
    ylab("") +
    # coord_flip()+
    facet_nested(.~chrom + variable, scales="free")+
    #facetted_pos_scales(y = rep(list(
    #    scale_y_continuous(breaks = seq(from=Ymin,to=Ymax,by=(Ymax-Ymin+1)%/%5),limits =c(Ymin, Ymax)),
    #    scale_y_continuous(breaks = seq(from=0,to=1,by=0.5),limits =c(0,1)))
    #,24),scale_x_continuous(expand = c(0, 0),trans="reverse")) +
facetted_pos_scales(x = rep(list(
        scale_x_continuous(breaks = seq(from=Ymin,to=Ymax,by=(Ymax-Ymin+1)%/%5),limits =c(Ymin, Ymax)),
        scale_x_continuous(breaks = seq(from=0,to=1,by=0.5),limits =c(0,1))) 
    ,24),y = scale_y_continuous(expand = c(0, 0),labels=function(x){paste0(x/1000000,"M")},trans="reverse"))+
    theme(axis.text.x = element_text(angle=60,size=5,hjust=1),axis.text.y = element_text(size=5),
            panel.background = element_blank(),panel.grid.major= element_blank(),
            panel.grid.minor.y = element_line(colour="#C8C8C8", size=0.1),strip.placement = "outside",
			legend.position = "bottom",plot.margin = unit(c(0,0,0,0.1),'cm'),panel.spacing = unit(0.01, "lines"))
            
ggsave(argv$outfile, width=20, height=12,dpi=256,device='png')
