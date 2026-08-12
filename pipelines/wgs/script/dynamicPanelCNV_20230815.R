# paste IDT39_WES.bed <(/nfs/software/cgranges/test/bedcov-cr /nfs/8.xuxiong/work/CNVseq/Stringent.Gain+Loss.hg19.2015-02-03.txt IDT39_WES.bed|awk -F"\t" '{print $5/($3-$2)}' ) <(/nfs/software/cgranges/test/bedcov-cr <(zcat  /nfs/database/wgEncodeCrgMapabilityAlign100mer.bedGraph.gz|awk -F"\t" '($4>0.5){print $0}') IDT39_WES.bed|awk -F"\t" '{print $5/($3-$2)}' )  > IDT39_WES_P_U.bed
# Rscript /bi/8.xuxiong/work/WES/dynamicPanelCNV.R --inDir /ssdnode001/12.xuruiyang/ECS_analysis/V6.3.1_ECSK_run_20221104B_T7/reQC --bedFile BS475.CNV.P_U.bed.gz --geneInfo /bi//0.houmin/database/GeneInfo/Homo_sapiens.gene_info.20221011.txt
library(parallel)
library(data.table)
library(ggplot2)
library(reshape2)
library(grid)
library(ggplotify)
suppressPackageStartupMessages(library(ggcorrplot))
suppressPackageStartupMessages(library(factoextra))
suppressPackageStartupMessages(library(gplots,quietly=TRUE))
options(bitmapType='cairo')
library(argparser, quietly=TRUE)
suppressPackageStartupMessages(library(dplyr))
options(scipen=999)
library(HaarSeg)
library(DNAcopy)

argv <- list(
	inDir = '/bi/8.xuxiong/data/WEScnvTest',
	ctrlDir = '/bi/8.xuxiong/data/WEScnvRef/20210914',
	bedFile = '/bi/8.xuxiong/database/HE.ex20bp_P_U.bed',
	geneInfo = '/nfs/0.houmin/database/GeneInfo/Homo_sapiens.gene_info.20221011.txt',
	minGender = 4,
	minSamples = 10,
	corrThreshold = 0.91,
	absCtrls = FALSE,
	AllFemale = FALSE,
	AllMale = FALSE,
	minRegionCount = 2,
	upperLog2r = 0.3, # 0.3219281 correspond to CN=2.5
	lowerLog2r = -0.5  # -0.5145732 correspond to CN=1.4
);

p <- arg_parser('plotting') %>%
	add_argument('--inDir', help='inDir.', type="character",default="/bi/8.xuxiong/data/WEScnvTest") %>%
	add_argument('--ctrlDir', help='ctrlDir.', type="character",default="/bi/8.xuxiong/data/WEScnvRef/20210914") %>%
	add_argument('--bedFile', help='bedFile.', type="character",default="../IDT39_WES_P_U.bed") %>%
	add_argument('--geneInfo', help='geneInfo.', type="character",default="/nfs/0.houmin/database/GeneInfo/Homo_sapiens.gene_info.20221011.txt") %>%
	add_argument('--corrThreshold', help='correlation Threshold',type="float", default=0.91) %>%
	add_argument('--minGender', help='maximum depth',type="integer", default=4) %>%
	add_argument('--minSamples', help='maximum iSize',type="integer", default=10) %>%
	add_argument('--absCtrls', help='absCtrls or include current samples as ctrls',type="logical", flag=TRUE) %>%
	add_argument('--AllFemale', help='all gender is female',type="logical", flag=TRUE) %>%
	add_argument('--AllMale', help='all gender is male',type="logical", flag=TRUE) %>%
	add_argument('--minRegionCount', help='minimum target Region Count', type="integer", default = 2) %>% 
	add_argument('--upperLog2r', help='upperLog2r', type="float", default = 0.3) %>% 
	add_argument('--lowerLog2r', help='lowerLog2r', type="float", default = -0.5);

argv <- parse_args(p);
cat('Arguments are as follows\n',file=stderr());
str(argv);

sexChr <- c('chrX','chrY')
autosome <- paste0('chr',as.character(1:22))
Chrs <- c(autosome,sexChr)

if (file.exists(argv$geneInfo)){
	geneInfoData <- fread(argv$geneInfo,header=T,sep="\t",data.table=TRUE,stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8") %>%
		filter(Symbol %in% c("SMN1","ASS1","PTS","PAH","CPT1A","MMACHC","ASL","GCDH","HPD","DMD")) %>%
		select(GeneID,Symbol)
}else{
	stop(sprintf('file: %s is not exists!', argv$geneInfo));
}
if (file.exists(argv$bedFile)){
	firstLine <- read.table(file = argv$bedFile,header = F,nrows = 1)
	if (length(firstLine) > 4){
		bedColNames <- c("chrom","start","end","geneSymbol","Polymorphism","UniqueMappability")
	}else if (length(firstLine) == 4){
		bedColNames <- c("chrom","start","end","geneSymbol")
	}else{
		bedColNames <- c("chrom","start","end")
		stop(sprintf('bedFile: %s has few columns!', argv$bedFile));
	}
	BedData <- fread(argv$bedFile,header=F,sep="\t",data.table=TRUE,stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8",col.names=bedColNames) %>%
				filter(chrom %in% Chrs)
	BedDataCNV <- BedData %>% filter(geneSymbol %in% c(geneInfoData$GeneID,geneInfoData$Symbol))
	setkey(BedDataCNV, chrom, start, end)
}else{
	stop(sprintf('file: %s is not exists!', argv$bedFile));
}

CNVcalling<-function(y,x,chr,sampleID,connecter){
	CNA.object <- CNA(y,rep(chr,length(x)),x,data.type="logratio",sampleid=sampleID)
	smoothed.CNA.object <- smooth.CNA(CNA.object,smooth.region=3)
	# segment.smoothed.CNA.object <- segment(smoothed.CNA.object,min.width=5,undo.splits = "sdundo",undo.SD=6,verbose=1)
	segment.smoothed.CNA.object <- segment(smoothed.CNA.object,min.width=2,alpha = 0.02,verbose=0)
	# segment.smoothed.CNA.object <- segment(smoothed.CNA.object,min.width=2,alpha = 0.02,undo.splits="prune",undo.prune=0.05,undo.SD=1.5,verbose=0)
	# segment.smoothed.CNA.object <- segment(smoothed.CNA.object,verbose=0)
	write.table(segment.smoothed.CNA.object$output,file=connecter,sep="\t",quote = FALSE,row.names =F,col.names=F)
	Seg <- rep(NA,length(x))
	for(i in 1:nrow(segment.smoothed.CNA.object$segRows)) {
		Seg[seq(segment.smoothed.CNA.object$segRows[i,1],segment.smoothed.CNA.object$segRows[i,2])] <- as.numeric(segment.smoothed.CNA.object$output$seg.mean[i])
	}
	Seg
}

# CNVcalling<-function(y,x,chr,sampleID,connecter){
# 	seg.data = haarSeg(y,breaksFdrQ=1e-20);
# 	nrowSegmentsTable <-nrow(seg.data$SegmentsTable)
# 	outputTable<-cbind(rep(sampleID,nrowSegmentsTable),rep(chr,nrowSegmentsTable),x[seg.data$SegmentsTable[,1]],
# 	x[seg.data$SegmentsTable[,1]+seg.data$SegmentsTable[,2]-1],seg.data$SegmentsTable[,2],seg.data$SegmentsTable[,3])
# 	write.table(outputTable,file=connecter,sep="\t",quote = FALSE,row.names =F,col.names=F)
# 	seg.data$Segmented
# }

genderBychromStat <- function(chromStatFiles, sampleID) {
	lChromStat<-do.call(rbind,mclapply(chromStatFiles,function(X){
		data<-fread(X,header=T,sep="\t",data.table=FALSE,stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8")
		data[data[,1] %in% sexChr,3]
	},mc.cores=16))
	colnames(lChromStat)<-c('chrX','chrY')
	rownames(lChromStat)<-sampleID
	set.seed(123)
	res.km <- kmeans(scale(lChromStat), 2, nstart = 25)
	print(rownames(res.km$centers)[which.max(res.km$centers[,1])])
	pdf(NULL)
	s <- fviz_cluster(res.km, data = lChromStat, palette = c("#2E9FDF", "#00AFBB"),labelsize=9, 
			repel = T, geom = c("point", "text"),ellipse.type = "convex", ggtheme = theme_bw()
	)
	ggsave("sexKmeans.png", width=16, height=9,dpi=256,device='png')
}
# genderBychromStat(Sys.glob("*.1.chromStat.txt"),sampleID)
 
ggheat<-function(m, rescaling='none', clustering='none', labCol=T, labRow=T, border=FALSE, heatscale= c(low='blue',high='red')) {
	require(reshape)
	require(ggplot2)
	library(ggpubr)
	library(ggdendro)
	colhclust <- hclust(d = dist(x = scale(t(m),center=T),method="manhattan"), method="ward.D")
	dend_data <- dendro_data(as.dendrogram(colhclust), type = "rectangle")
	# dendro.plot <- ggdendrogram(data = as.dendrogram(colhclust), rotate = F, labels = F, leaf_labels = F)
	p <- ggplot(dend_data$segments) + geom_segment(aes(x = x, y = y, xend = xend, yend = yend)) +
		# geom_text(data = dend_data$labels, aes(x, y, label = label), hjust = 1, angle = 90, size = 6) +
		theme(axis.text.x = element_blank(), axis.ticks.x = element_blank(),panel.background=element_blank(), 
		axis.ticks.x.top = element_blank(), axis.ticks.x.bottom = element_blank(),
		axis.title.x.top = element_blank(),axis.title.x.bottom = element_blank(),
		axis.text.x.top = element_blank(), axis.text.x.bottom = element_blank(),
		axis.title.x = element_blank(), plot.caption =  element_blank(), plot.title = element_blank(),
		plot.subtitle =element_blank(),
		plot.margin = unit(c(5.5,5.5,0,5.5),'pt'))
	if(is.function(rescaling)){ 
		m<-rescaling(m)
	} else {
		if(rescaling=='column') m<-scale(m, center=T)
		if(rescaling=='row') m<-t(scale(t(m),center=T))
	}
	if(is.function(clustering)) {
		m<-clustering(m)
	}else{
		if(clustering=='row') m<-m[hclust(dist(m,method="manhattan"), method="ward.D")$order, ]
		if(clustering=='column') m<-m[,hclust(dist(t(m),method="manhattan"), method="ward.D")$order]
		if(clustering=='both') m<-m[hclust(dist(m,method="manhattan"), method="ward.D")$order ,hclust(dist(t(m),method="manhattan"), method="ward.D")$order]
	}
	rows<-dim(m)[1]
	cols<-dim(m)[2]
	melt.m<-cbind(rowInd=rep(1:rows, times=cols), colInd=rep(1:cols, each=rows) ,melt(m))
	g2<-ggplot(data=melt.m)
	if(border==TRUE) g2<-g2+geom_rect(aes(xmin=colInd-1,xmax=colInd,ymin=rowInd-1,ymax=rowInd, fill=value),colour='white')
	if(border==FALSE) g2<-g2+geom_rect(aes(xmin=colInd-1,xmax=colInd,ymin=rowInd-1,ymax=rowInd, fill=value))
	if(labCol==T) g2<-g2+scale_x_continuous(breaks=(1:cols)-0.5, labels=colnames(m))
	if(labCol==F) g2<-g2+scale_x_continuous(breaks=(1:cols)-0.5, labels=rep('',cols))
	if(labRow==T) g2<-g2+scale_y_continuous(breaks=(1:rows)-0.5, labels=rownames(m))
	if(labRow==F) g2<-g2+scale_y_continuous(breaks=(1:rows)-0.5, labels=rep('',rows))    
	g2<-g2 + theme(axis.title = element_blank(),title = element_blank(),plot.subtitle = element_blank(),
		plot.title = element_blank(),plot.caption = element_blank(), axis.ticks = element_blank(), 
		axis.text.x = element_text(angle=60,size=9,hjust=0.5),
		panel.background=element_blank(), plot.margin = unit(c(0,5.5,5.5,5.5),'pt')) +
		scale_fill_gradient2(low=heatscale[1],mid='white',high=heatscale[2])
	ggarrange(p, g2, ncol = 1, nrow = 2, align = "hv", legend = "right", 
		heights = c(1, 3), common.legend = TRUE, hjust = 0, vjust = 0)
	ggsave("ggheatmapByBins.png", width=16, height=9,dpi=256,device='png')
	return(g2)
}

getSexByY<-function(DataYnorm,sampleNames,outfile="heatmap_sexY.png"){
    pdf(NULL)
    h<-base2grob(~heatmap.2(DataYnorm,hclustfun = function(x){hclust(x, method="ward.D")},
        distfun=function(x) {dist(x,method="manhattan")},dendrogram="col",
        labCol=sampleNames,
        col=greenred(75), scale="row",key=TRUE,key.xlab='NRC',keysize=1,symkey=FALSE,#labRow=NA,
        density.info="histogram", trace="none",,margins=c(10,10)))
    ggsave(filename=outfile,plot = h, width=16, height=9,dpi=256,device='png')
    # colhclust <- as.hclust(h$colDendrogram)
	colhclust <- hclust(d = dist(x = scale(t(DataYnorm),center=T),method="manhattan"), method="ward.D")
    groups <- cutree(colhclust,2)
    SexType <- groups == 1
    YRC<-apply(DataYnorm,2,function(X){sum(as.numeric(X),na.rm=T)})
	if (grepl("Y",outfile,ignore.case=F,perl=T)){
    	if(median(YRC[SexType])>median(YRC[!SexType])) SexType <- !SexType
	}else{
		if(median(YRC[SexType])<median(YRC[!SexType])) SexType <- !SexType
	}
	names(SexType)<-sampleNames
    SexType
}

getSexByXYbins<-function(DataXYnorm,sampleNames,outfile1="heatmap_sex.png",outfile2="sexKmeansByBins.png"){
	# p<-ggheat(DataXYnorm,clustering='column',rescaling='row',labCol=T,labRow=T,border=F,heatscale= c(low='blue',high='red'))
	pdf(NULL)
    h<-base2grob(~heatmap.2(DataXYnorm,hclustfun = function(x){hclust(x, method="ward.D")},
        distfun=function(x) {dist(x,method="manhattan")},dendrogram="col",
        labCol=sampleNames,
        col=greenred(75), scale="row",key=TRUE,key.xlab='NRC',keysize=1,symkey=FALSE,#labRow=NA,
        density.info="histogram", trace="none",margins=c(10,10)))
	ggsave(filename=outfile1,plot = h, width=16, height=9,dpi=256,device='png')
	colhclust <- hclust(d = dist(x = scale(t(DataXYnorm),center=T),method="manhattan"), method="ward.D")
    # colhclust <- as.hclust(h$colDendrogram)
    groups <- cutree(colhclust,2)
    SexType <- groups == 1
    XRC<-apply(DataXYnorm[1:(nrow(DataXYnorm)%/%2),],2,function(X){sum(as.numeric(X),na.rm=T)})
    if(median(XRC[SexType])<median(XRC[!SexType])) SexType <- !SexType
	names(SexType)<-sampleNames

	tDataXYnorm<-t(DataXYnorm)
	res.km <- kmeans(scale(tDataXYnorm), 2, nstart = 25)
	fviz_cluster(res.km, data = tDataXYnorm, palette = c("#2E9FDF", "#00AFBB"),labelsize=9, 
			repel = T, geom = c("point", "text"),ellipse.type = "convex", ggtheme = theme_bw()
	)
	ggsave(outfile2, width=16, height=9,dpi=256,device='png')
	# print(lapply((by(tDataXYnorm,res.km$cluster,function(X){
	# 	apply(X,1,function(Y){sum(Y[1:(length(Y)%/%2)])})
	# })),sum))
	cluster1<-apply(tDataXYnorm[res.km$cluster==1,,drop=F],1,function(Y){sum(Y[1:(length(Y)%/%2)])})
	cluster2<-apply(tDataXYnorm[res.km$cluster==2,,drop=F],1,function(Y){sum(Y[1:(length(Y)%/%2)])})
	if (median(cluster1)>median(cluster2)){
		SexType2 <- res.km$cluster==1
	}else{
		SexType2 <- res.km$cluster==2
	}
	print(setequal(SexType,SexType2))
    SexType
}

infiles<-sort(Sys.glob(paste(argv$inDir,"*.1.depth",sep=.Platform$file.sep)))
sampleID<-gsub("(-HE|-CSID)?\\.realigned\\.[bcr]+am\\.1\\.depth$|(-HE|-CSID)?\\.dedup(ed)?\\.[bcr]+am\\.1\\.depth$|(-HE|-CSID)?\\.[bcr]+am\\.1\\.depth$","",basename(infiles),perl=T)

lData<-mclapply(infiles,function(X){
	fread(X,header=F,sep="\t",data.table=FALSE,stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8")
},mc.cores=16)
names(lData)<-sampleID
print(names(lData))

if(grepl("[Cc]hr",lData[[1]][1,1],ignore.case = TRUE, perl = TRUE)){
	chrBool<-TRUE
}

Data<-do.call(cbind,lapply(lData,function(X){X[,4]}))
GC<-do.call(cbind,lapply(lData,function(X){X[,6]}))
Data[apply(Data,1,mean)<5,]<-NA
dataChr<-lData[[1]][,1]
dataStart<-lData[[1]][,2]
AutosomeData<-Data[dataChr %in% autosome,,drop=F]
AutosomeSum<-apply(AutosomeData,2,sum,na.rm=T)

DataNorm<-sapply(1:ncol(Data),function(X){
	as.numeric(Data[,X])/AutosomeSum[X]*1e7
})
colnames(DataNorm)<-sampleID

CVall<-apply(DataNorm,1,function(Z){
	sd(Z)/mean(Z)
})

AutosomeData<-DataNorm[dataChr %in% autosome,,drop=F]
xyData<-DataNorm[dataChr %in% sexChr,,drop=F]
isNAXY<-apply(xyData,1,function(X){!all(is.na(X))})
isNA<-apply(DataNorm,1,function(X){!all(is.na(X))})

corrData<-cor(AutosomeData[apply(AutosomeData,1,function(X){!any(is.na(X)) }),])

# print(corrData)
write.table(t(sapply(colnames(corrData),function(X){
	filtered<-corrData[rownames(corrData[,X,drop=F])!=X & corrData[,X]>=argv$corrThreshold,X,drop=F]
	ll<-length(filtered)
	c(X,ll,nrow(corrData),round(ll/(nrow(corrData)-1),digits =3))
})),file="corrQC.csv",sep="\t",quote = FALSE,row.names =F,col.names=F)
# corrDataNoOne<-outer(row.names(corrData), colnames(corrData),`!=`)

p<-ggcorrplot(corrData, type = "full",lab = TRUE,outline.color = "white") +
	scale_fill_gradient(limits=c(0.99*min(corrData), 1),low = "white",high = "red")
ggsave("corrPlot.png", width=16, height=9,dpi=256,device='png')
# q("no")

if (length(infiles)>= argv$minSamples){
	GenderBool<-getSexByXYbins(xyData[isNAXY,,drop=F],sampleID)
	if (nrow(DataNorm[dataChr %in% 'chrY' & isNA,,drop=F])>10){
		GenderBoolByY<-getSexByY(DataNorm[dataChr %in% 'chrY' & isNA,,drop=F],sampleID)
		if (!all(GenderBool==GenderBoolByY)){
			GenderBool<-ifelse(GenderBool!=GenderBoolByY,GenderBoolByY,GenderBool)
		}
	}
	GenderCount <- tapply(GenderBool,GenderBool,length)
}

if (argv$AllFemale){
	GenderBool<-rep(TRUE,length=length(sampleID))
	names(GenderBool)<-sampleID
}else if (argv$AllMale){
	GenderBool<-rep(FALSE,length=length(sampleID))
	names(GenderBool)<-sampleID
}else if (argv$absCtrls || (!is.na(argv$ctrlDir) && (length(infiles)< argv$minSamples || min(GenderCount) < argv$minGender))) {
	ctrlsfiles<-Sys.glob(paste(argv$ctrlDir,"*.1.depth",sep=.Platform$file.sep))
	if (length(ctrlsfiles)){
		ctrlsID<-gsub("(-HE|-CSID)?\\.realigned\\.[bcr]+am\\.1\\.depth$|(-HE|-CSID)?\\.dedup(ed)?\\.[bcr]+am\\.1\\.depth$|(-HE|-CSID)?\\.[bcr]+am\\.1\\.depth$","",basename(ctrlsfiles),perl=T)
		AllFiles <- c(infiles,ctrlsfiles)
		if (argv$absCtrls) AllFiles <- ctrlsfiles
		lDataAll<-mclapply(AllFiles,function(X){
			fread(X,header=F,sep="\t",data.table=FALSE,stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8")
		},mc.cores=16)

		DataAll<-do.call(cbind,lapply(lDataAll,function(X){X[,4]}))
		DataAll[apply(DataAll,1,mean)<5,]<-NA
		AutosomeDataAll<-DataAll[dataChr %in% autosome,,drop=F]
		AutosomeSumAll<-apply(AutosomeDataAll,2,sum,na.rm=T)

		DataNormAll<-sapply(1:ncol(DataAll),function(X){
			as.numeric(DataAll[,X])/AutosomeSumAll[X]*1e7
		})
		if (argv$absCtrls) {
			colnames(DataNormAll)<-ctrlsID
		}else{
			colnames(DataNormAll)<-c(sampleID,ctrlsID)
		}
		CVall<-apply(DataNormAll,1,function(Z){
			sd(Z)/mean(Z)
		})
		AutosomeDataAll<-DataNormAll[dataChr %in% autosome,,drop=F]
		xyDataAll<-DataNormAll[dataChr %in% sexChr,,drop=F]
		isNAXYDataAll<-apply(xyDataAll,1,function(X){!all(is.na(X))})
		corrDataAll<-cor(AutosomeDataAll[apply(AutosomeDataAll,1,function(X){!all(is.na(X))}),,drop=F])
		p<-ggcorrplot(corrDataAll, type = "full",lab = TRUE) + scale_fill_gradient(limits=c(0.99*min(corrDataAll), 1),low = "white",high = "red")
		ggsave("corrPlotCtrls.png", width=16, height=9,dpi=256,device='png')
		GenderBoolAll<-getSexByXYbins(xyDataAll[isNAXYDataAll,,drop=F],colnames(DataNormAll),"heatmap_sexWithCtrls.png","sexKmeansByBinsWithCtrls.png")
		if (! argv$absCtrls) {
			isNADataNormAll<-apply(DataNormAll,1,function(X){!all(is.na(X))})
			if (nrow(DataNormAll[dataChr %in% 'chrY' & isNADataNormAll,,drop=F])>10){
				GenderBoolByYAll<-getSexByY(DataNormAll[dataChr %in% 'chrY' & isNADataNormAll,,drop=F],colnames(DataNormAll))
				if (!all(GenderBoolAll==GenderBoolByYAll)){
					GenderBoolAll<-ifelse(GenderBoolAll!=GenderBoolByYAll,GenderBoolByYAll,GenderBoolAll)
				}
				GenderBoolByY<-GenderBoolByYAll[sampleID]
			}
			GenderBool<-GenderBoolAll[sampleID]
			print(GenderBool)
		}
	}
}

if(!all(file.exists(paste0(sampleID,".seg.merge.bed")))){
	minLog2r <- argv$lowerLog2r
	maxLog2r <- argv$upperLog2r
	mclapply(sampleID,function(X){
		cat(X,"\n",file=stderr())
		conn <- file(paste0(X,".seg.tsv"),"w")
		if(X %in% sampleID[GenderBool]) {
			if(exists("corrDataAll")){
				corX<-corrDataAll[rownames(corrDataAll) %in% X,GenderBoolAll]
			}else{
				corX<-corrData[rownames(corrData) %in% X,GenderBool]
			}
		}else{
			if(exists("corrDataAll")){
				corX<-corrDataAll[rownames(corrDataAll) %in% X,!GenderBoolAll]
			}else{
				corX<-corrData[rownames(corrData) %in% X,!GenderBool]
			}
		}
		CORX<-corX[corX>=argv$corrThreshold & !(names(corX) %in% X)]
		# print(length(CORX))
		if(length(CORX)<=5){
			CORX<-head(sort(corX[!(names(corX) %in% X)],decreasing=TRUE),n=10)
		}
		DataNormCtrls<-DataNorm[,colnames(DataNorm) %in% names(CORX),drop=F]
		if(exists("DataNormAll")){
			DataNormCtrls<-DataNormAll[,colnames(DataNormAll) %in% names(CORX),drop=F]
		}
		MeanMedianSD <- t(apply(DataNormCtrls,1,function(Z){
			ZZ <- Z
			if (length(Z)>5) {
				ZZ <- Z[!(Z %in% boxplot.stats(Z)$out)]
			}
			c(mean(ZZ,na.rm =T),median(ZZ,na.rm =T),sd(ZZ,na.rm =T))
		}))
		log2r<-log2((DataNorm[,X]+0.01)/MeanMedianSD[,2]+0.01)
		zScore<- (DataNorm[,X]-MeanMedianSD[,1])/MeanMedianSD[,3]
		zScore[is.nan(zScore) | is.na(zScore) | is.null(zScore) | is.infinite(zScore)] <- 0
		CV<-apply(DataNormCtrls,1,function(Z){
			sd(Z)/mean(Z)
		})
		sample_log2r <- cbind(lData[[X]][lData[[X]][,1] %in% Chrs,1:3],
			do.call(rbind,lapply(Chrs[Chrs %in% lData[[X]][,1]],function(Y){
				chrBoolean <- dataChr %in% Y;
				ncov <- log2r[chrBoolean];
				sZscore <- zScore[chrBoolean]
				sCV <- CV[chrBoolean];
				sCVall <- CVall[chrBoolean];
				seg <- ncov;
				if (length(ncov[!(is.na(ncov))])>200) {
					ncov[is.na(ncov)]<-0
					seg <- CNVcalling(ncov,dataStart[chrBoolean],Y,X,conn)
				}
				baseCN<-2;
				if(X %in% sampleID[GenderBool]) {
					baseCN <- ifelse(grepl('Y',Y,ignore.case = T, perl = T),0.05,2)
				}else{
					baseCN <- ifelse(grepl('[XY]',Y,ignore.case = T, perl = T),1,2)
				}
				cn <- 2^(ncov)*baseCN
				cns <- 2^(seg)*baseCN
				cbind(ncov,seg,cn,cns,abs(cn-2),sCV,sCVall,sZscore)
			}))
		,lData[[X]][lData[[X]][,1] %in% Chrs,4:6])
		close(conn)
		ploidy<-data.frame(chrom=Chrs[Chrs %in% lData[[X]][,1]],CopyNumber=round(tapply(sample_log2r[,6],factor(sample_log2r[,1],levels=Chrs[Chrs %in% sample_log2r[,1]]),function(Y){
			mean(Y[Y<=4],na.rm=TRUE)
		}),digits =3) )
		write.table(ploidy,file=paste0(X,"_ploidy.tsv"),sep="\t",quote = FALSE,row.names =F,col.names=T)
		colnames(sample_log2r) <- c("chrom","start","end","log2R","log2rSeg","CN","CNseg","MosRatio","CV","CVall","zScore","depth","RC","GC")
		if (file.exists(argv$bedFile)){
			if (ncol(BedData)>3 & nrow(sample_log2r)==nrow(BedData) ){
				sample_log2r<-cbind(sample_log2r,BedData[,-(1:3)])
				if (ncol(BedData)==4) {
					colnames(sample_log2r) <- c("chrom","start","end","log2R","log2rSeg","CN","CNseg","MosRatio","CV","CVall","zScore","depth","RC","GC","geneSymbol")
				}else{
					colnames(sample_log2r) <- c("chrom","start","end","log2R","log2rSeg","CN","CNseg","MosRatio","CV","CVall","zScore","depth","RC","GC","geneSymbol","Polymorphism","UniqueMappability")
				}
			}
		}
		write.table(sample_log2r,file=paste0(X,'.normalize.bed'),sep="\t",quote = F,row.names=F,col.names=F)
		Seg<-NULL
		if (file.exists(argv$bedFile) & nrow(sample_log2r)==nrow(BedData) & "Polymorphism" %in% colnames(sample_log2r)){
			sample_log2r<-sample_log2r %>% mutate(length=(end-start+1),GCcount = round(length*GC)) %>%
				mutate(mergedSeg = ifelse(log2rSeg > maxLog2r | log2rSeg < minLog2r ,log2rSeg,log2R)) %>%
				mutate(threshold = cut(mergedSeg,breaks = c(-Inf,minLog2r, maxLog2r,Inf),right = FALSE) ) %>%
				mutate(seg_diff = ifelse(threshold==lag(threshold) & chrom==lag(chrom) & (sapply(strsplit(geneSymbol, ":"), `[`,1) == sapply(strsplit(lag(geneSymbol), ":"), `[`,1) | start - shift(end, n=1L, fill=0, type="lag") < 1000000),0,1)) %>% 
				mutate(seg_diff = ifelse(is.na(seg_diff), 0, seg_diff)) %>% 
				mutate(seg_no = cumsum(seg_diff)) %>% 
				select(-seg_diff)
			Seg <- sample_log2r %>% group_by(seg_no) %>% summarise(chrom=first(chrom),start = first(start), end = max(end), 
				num.mark=n(), log2R = ifelse(num.mark>3,median(log2R,na.rm=T),mean(log2R,na.rm=T)), log2rSeg = first(log2rSeg),
				CN = ifelse(num.mark>3,median(CN,na.rm=T),mean(CN,na.rm=T)), CNseg = first(CNseg),
				CV = ifelse(num.mark>3,median(CV,na.rm=T),mean(CV,na.rm=T)), CVall = ifelse(num.mark>3,median(CVall,na.rm=T),mean(CVall,na.rm=T)),
				GC = 1.0*sum(GCcount,na.rm=T)/sum(length,na.rm=T),
				Polymorphism = mean(Polymorphism,na.rm=T),
				UniqueMappability = mean(UniqueMappability,na.rm=T),
				zScore = ifelse(num.mark>3,median(zScore,na.rm=T),mean(zScore,na.rm=T)) ) %>%
				select(-seg_no);
			idx <- foverlaps(as.data.table(Seg), BedDataCNV, by.x=c("chrom", "start", "end"), type="any", which=TRUE)
			# filter((log2R < minLog2r | log2R > maxLog2r ) & num.mark >= argv$minRegionCount & Polymorphism<0.5 & UniqueMappability>0.5) %>%
			# Seg <- Seg %>% filter((log2R < minLog2r | log2R > maxLog2r ) & ifelse(seq_along(chrom) %in% idx$xid[!is.na(idx$yid)],num.mark >= 1 , num.mark >= argv$minRegionCount)) %>%
			Seg <- Seg %>% filter((((log2R < minLog2r | log2R > maxLog2r) & num.mark>= argv$minRegionCount ) | ((log2R < -0.577767 | log2R > 0.4114262) & num.mark<2 & CV < 0.5)) & abs(zScore)>3 & !(grepl("^([Cc]hr)?6$",chrom,perl=T) & start>=28477797 & end<=33448354)) %>%
				mutate(type = ifelse(log2R < minLog2r,"DEL",ifelse(log2R > maxLog2r,"DUP","Normal"))) %>%
				mutate(AnnotSV_ID = paste(sub("[cC]hr","",chrom,perl=T),start,end,type,"1",sep="_")) %>% 
				relocate(type, .before = num.mark) %>%
				arrange(desc(num.mark * abs(zScore)));
		}else{
			sample_log2r<-sample_log2r %>% mutate(length=(end-start+1),GCcount = round(length*GC)) %>%
				mutate(mergedSeg = ifelse(log2rSeg > maxLog2r | log2rSeg < minLog2r ,log2rSeg,log2R)) %>%
				mutate(threshold = cut(mergedSeg,breaks = c(-Inf,minLog2r, maxLog2r,Inf),right = FALSE) ) %>%
				mutate(seg_diff = ifelse(threshold==lag(threshold) & chrom==lag(chrom),0,1)) %>% 
				mutate(seg_diff = ifelse(is.na(seg_diff), 0, seg_diff)) %>% 
				mutate(seg_no = cumsum(seg_diff)) %>% 
				select(-seg_diff)
			Seg <- sample_log2r %>% group_by(seg_no) %>% summarise(chrom=first(chrom),start = first(start), end = max(end),
				num.mark=n(), log2R = ifelse(num.mark>3,median(log2R,na.rm=T),mean(log2R,na.rm=T)), log2rSeg = first(log2rSeg),
				CN = ifelse(num.mark>3,median(CN,na.rm=T),mean(CN,na.rm=T)), CNseg = first(CNseg),
				CV = ifelse(num.mark>3,median(CV,na.rm=T),mean(CV,na.rm=T)), CVall = ifelse(num.mark>3,median(CVall,na.rm=T),mean(CVall,na.rm=T)),
				GC = 1.0*sum(GCcount,na.rm=T)/sum(length,na.rm=T),
				zScore = ifelse(num.mark>3,median(zScore,na.rm=T),mean(zScore,na.rm=T)) ) %>%
				select(-seg_no);
			idx <- foverlaps(as.data.table(Seg), BedDataCNV, by.x=c("chrom", "start", "end"), type="any", which=TRUE)
			# Seg <- Seg %>% filter((log2R < minLog2r | log2R > maxLog2r ) & ifelse(seq_along(chrom) %in% idx$xid[!is.na(idx$yid)],num.mark >= 1 , num.mark >= argv$minRegionCount)) %>%
			Seg <- Seg %>% filter((( (log2R < minLog2r | log2R > maxLog2r) & num.mark>= argv$minRegionCount) | ((log2R < -0.577767 | log2R > 0.4114262) & num.mark<2 & CV < 0.5)) & abs(zScore)>3 & !(grepl("^([Cc]hr)?6$",chrom,perl=T) & start>=28477797 & end<=33448354)) %>%
				mutate(type = ifelse(log2R < minLog2r,"DEL",ifelse(log2R > maxLog2r,"DUP","Normal"))) %>%
				mutate(AnnotSV_ID = paste(sub("[cC]hr","",chrom,perl=T),start,end,type,"1",sep="_")) %>% 
				relocate(type, .before = num.mark) %>%
				arrange(desc(num.mark * abs(zScore)));
		}
		write.table(Seg,file=paste0(X,".seg.merge.bed"),sep="\t",quote = FALSE,row.names =F,col.names=T)
		# write.table(Seg %>% select(chrom,start,end,type),file=paste0(X,".seg.bed"),sep="\t",quote = FALSE,row.names =F,col.names=F)
		nrow(Seg)
	},mc.cores=16)
	# })
}

write.table(cbind(names(GenderBool),ifelse(GenderBool,'F','M')),file="gender.csv",sep=",",quote = F,row.names=F,col.names=F)

cnFiles <- paste(Sys.glob("*_ploidy.tsv"), collapse=" ");
CMD <- paste0("ls ",cnFiles,"|xargs -i awk -F\"\\t\" '\''(NR>1){s=FILENAME;gsub(/_ploidy\\.tsv/,\"\",s);print s\"\\t\"$0}'\'' {} ")
CNdata <- read.table(pipe(CMD),header = F, sep = "\t", check.names = F, comment.char = "!",stringsAsFactors = F, fileEncoding = "UTF-8",col.names=c("sampleID","chrom","CN"));
CNcasted <- reshape2::dcast( CNdata, chrom~sampleID, value.var="CN");
write.table(CNcasted,file="All.chrom.CN.tsv",sep="\t",quote = FALSE,row.names =F,col.names=T)

pCN<-ggplot(CNdata,aes(x=sampleID,y=chrom)) +geom_tile(aes(color=as.numeric(CN),fill=as.numeric(CN)))+
scale_colour_gradient2(midpoint=2,limits=c(0,4),low = "blue",mid = "white",high = "red") + 
scale_fill_gradient2(midpoint=2,limits=c(0,4),low = "blue",mid = "white",high = "red") + 
theme(axis.text.x = element_text(angle=70,size=5, hjust=1),axis.text.y = element_text(size=5),
			panel.background = element_blank(),
			legend.position = "bottom",plot.margin = unit(c(0,0,0,1),'cm'),panel.spacing = unit(0.1, "lines"));
ggsave("heatmap.chrom.CN.png", width=16, height=9,dpi=256,device='png')

log2rFiles <- paste(Sys.glob("*.normalize.bed"),collapse=" ");
CMD <- paste0("head -n 1 ",sampleID[1],".normalize.bed | awk -F\"\t\" '{print NF}'")
NumberField<-as.numeric(system(CMD,intern = TRUE))
CMD <- paste0("(ls ",log2rFiles, " | perl -ne 'chomp;push @a,$_;if(eof){print \"#chr\\tstart\\tend\\t\",join(\"\\t\",map {$_=~s/\\.normalize\\.bed$//;$_.\"_log2r\"} @a),\"\n\"}' ;ls ",log2rFiles," | perl -ne 'chomp;push @a,$_;if(eof){print \"cut -f1-3 $a[0] |sort -k1,1V -k2,2n -k3,3n |paste - \",join(\"\\t\",map {\"<(sort -k1,1V -k2,2n -k3,3n $_ | awk '\\''{print \\$4}'\\'')\"}  @a),\"\\n\";}'|bash) | bgzip -c -@8 >All.join.log2r.bed.gz && tabix -fp bed All.join.log2r.bed.gz");
if(NumberField>14){
	CMD <- paste0("(ls ",log2rFiles, " | perl -ne 'chomp;push @a,$_;if(eof){print \"#chr\\tstart\\tend\\tgene\\t\",join(\"\\t\",map {$_=~s/\\.normalize\\.bed$//;$_.\"_log2r\"} @a),\"\n\"}' ;ls ",log2rFiles," | perl -ne 'chomp;push @a,$_;if(eof){print \"cut -f1-3,15 $a[0] |sort -k1,1V -k2,2n -k3,3n |paste - \",join(\"\\t\",map {\"<(sort -k1,1V -k2,2n -k3,3n $_ | awk '\\''{print \\$4}'\\'')\"}  @a),\"\\n\";}'|bash) | bgzip -c -@8 >All.join.log2r.bed.gz && tabix -fp bed All.join.log2r.bed.gz");
}
system(CMD)

is_bin_on_path = function(bin) {
  exit_code = suppressWarnings(system2("command", args = c("-v", bin), stdout = FALSE))
  return(exit_code == 0)
}

if(!file.exists("merge.bed")){
	segFile <- paste(Sys.glob("*.seg.merge.bed"),collapse=" ");
	if(is_bin_on_path("bedtools")) {
		BEDTOOLS <- "bedtools"
	}else{
		BEDTOOLS <- "/bi/software/bedtools"
	}
	CMD <- paste0("ls ",segFile,"|xargs -i echo \"sed '1d' {} \"|bash|sort -k1,1V -k2,2n -k3,3n|",BEDTOOLS," merge >merge.bed")
	print(CMD)
	system(CMD)
}

CNVdata<-read.table(pipe("tabix -hfp bed -R merge.bed All.join.log2r.bed.gz"), 
        header = T, sep = "\t", check.names = F, comment.char = "!",stringsAsFactors = F, fileEncoding = "UTF-8");
colnames(CNVdata)[1]<-gsub("#","",colnames(CNVdata)[1])
if(!chrBool) CNVdata <- CNVdata %>% mutate(chr = gsub("[Cc]hr","",chr,perl=T))
CNVdata <- CNVdata %>% mutate(idx = do.call(c,tapply(start,factor(chr, levels=Chrs),seq_along)))
idNames <- c("chr","start","end","idx");
if ("gene" %in% colnames(CNVdata)) {
    idNames <- c("chr","start","end","gene","idx");
    if (any(c("polymorphism","mapability") %in% colnames(CNVdata))) {
        idNames <- c("chr","start","end","gene","polymorphism","mapability","idx");
    }
}
mCNVdata<-melt(CNVdata,id=idNames,variable="sampleID") %>% mutate(sampleID = gsub("_log2r","",sampleID,perl=T,ignore.case=T))
mCNVdata$chr<-factor(mCNVdata$chr, levels=Chrs)

pp1<-ggplot(mCNVdata,aes(x=start,y=sampleID))+ 
	geom_tile(aes(color=as.numeric(value),fill=as.numeric(value))) +
#    scale_colour_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "gray80",high = "red") + 
    scale_colour_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "white",high = "red") + 
	scale_fill_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "white",high = "red") + 
    facet_grid(chr~.,scales="free_x", space="free_x") +
    scale_x_continuous(expand = c(0, 0)) +
    theme(axis.text.x = element_text(angle=70,size=5, hjust=1),axis.text.y = element_text(size=5),
			panel.background = element_blank(),
            #panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
			legend.position = "bottom",plot.margin = unit(c(0,0,0,1),'cm'),panel.spacing = unit(0.1, "lines"));
ggsave("heatmap.png", width=18, height=32,dpi=256,device='png')
# ggsave("heatmap.pdf", width=18, height=32,device='pdf')

N_samples <-length(sampleID)
timesN_samples <- N_samples %/% 20
if (timesN_samples < 1) timesN_samples <- 1
pp2<-ggplot(mCNVdata,aes(x=idx,y=sampleID)) + 
    geom_tile(aes(color=as.numeric(value),fill=as.numeric(value))) +
    scale_colour_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "white",high = "red") + 
	scale_fill_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "white",high = "red") + 
    facet_grid(.~chr,scales="free_x", space="free_x")+
    scale_x_continuous(expand = c(0, 0)) +
    theme(axis.text.x = element_text(angle=70,size=5, hjust=1),axis.text.y = element_text(size=5),
			panel.background = element_blank(),
            #panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
			legend.position = "right",plot.margin = unit(c(0,0,0,1),'cm'),panel.spacing = unit(0.1, "lines"));
ggsave("heatmap_h.png", width=24, height=3*timesN_samples,dpi=256,device='png')
# ggsave("heatmap_h.pdf", width=24, height=3*timesN_samples,device='pdf') 

pp3<-ggplot(mCNVdata,aes(x=start,y=sampleID)) + 
    geom_tile(aes(color=as.numeric(value),fill=as.numeric(value))) +
    scale_colour_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "white",high = "red") +
	scale_fill_gradient2(midpoint=0,limits=c(-1.2,1.2),low = "blue",mid = "white",high = "red") + 
    facet_grid(.~chr,scales="free_x", space="free_x") +
    scale_x_continuous(expand = c(0, 0)) +
    theme(axis.text.x = element_text(angle=70,size=5, hjust=1),axis.text.y = element_text(size=5),
			panel.background = element_blank(),
            #panel.grid.major = element_blank(),panel.grid.minor = element_blank(),
			legend.position = "right",plot.margin = unit(c(0,0,0,1),'cm'),panel.spacing = unit(0.1, "lines"));
ggsave("heatmap_pos_h.png", width=24, height=3*timesN_samples,dpi=256,device='png')
# ggsave("heatmap_pos_h.pdf", width=24, height=3*timesN_samples,device='pdf')

# 1. 根据每个target region的normalized depth，case在ctrls 中的偏离程度和样本间的波动性（CV）
# 2. number of target region
# 3. |copynumber-2| （与2的绝对值）
# 4. non-unique region占比
# 5. 与CNV多态性区域overlap占比
# 6. target reiogn的GC%
