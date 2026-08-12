#!/usr/bin/env Rscript

library(argparser, quietly=TRUE);
library(futile.logger, quietly=TRUE);
library(tidyr, quietly=TRUE);
library(plotrix, quietly=TRUE);
library(maptools, quietly=TRUE);
library(readr, quietly=TRUE);
library(plyr, quietly=TRUE);
suppressPackageStartupMessages(library(dplyr));
library(ggplot2)
library(ggnewscale)
library(ggh4x,quietly=TRUE)
library(Cairo, quietly=TRUE);

# Parse command line.
p = arg_parser('CNVetti plotting') %>%
    add_argument('--reference-fai', help='Path to reference FAI file.',type="character") %>%
    add_argument('--cytoband', help='cytoband file.',type="character") %>%
    add_argument('--UPD', help='CNV disease file.', type="character") %>%
    add_argument('--Disease', help='CNV disease file.', type="character") %>%
    add_argument('--Polymorphism', help='CNV polymorphism file.', type="character") %>%
    add_argument('--roh', help='result of automap.',type="character") %>%
    add_argument('--out-chrom', help='Path to chromsome output PNG file, "%s" will be replaced by chromosome name.',type="character") %>%
    add_argument('--out-genome', help='Path to genome output PNG file.',type="character") %>%
    add_argument('--input-bed', help='Path to input BED file.',type="character") %>%
    add_argument('--vaf-bed', help='Path to input VAF BED file.',type="character") %>%
    add_argument('--samples', help='Comma-separated list of samples to plot for.',type="character") %>%
    add_argument('--gene-beds', help='Comma-separated list of gene BED files.',type="character") %>%
    add_argument('--bcftools', help='bcftools path', type="character", default="/usr/local/bin/bcftools") %>%
    add_argument('--axis-y-min', help='Lower bound of y axis', type="double", default=0) %>%
    add_argument('--axis-y-max', help='Lower bound of y axis', type="double", default=4);

argv <- parse_args(p);
flog.info('Arguments are as follows');
str(argv);

loadCytoBand<-function(cytoRData,ChrBool){#
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
    cyto[cyto$type=="gvar",]$Color<-rgb(220,220,220, maxColorValue=255)    # indented region
    chrs<-split(cyto,factor(cyto$chrom))
    chrs
}

loadCNVPolymorphism<-function(CNVPolymorphismFile,chrBool){
    data<-read.delim(CNVPolymorphismFile,header=T)
    if (!chrBool) data$chr<-gsub("[cC]hr","",data$chr,perl=T)
    colnames(data)[1]<-"chrom"
    data$variable<-rep("CNV",times=nrow(data))
    data[data$end - data$start>=0.01 & data$num_samples>10,]
}

loadCNVdisease<-function(CNVdiseaseFile,chrBool){
    tmpLine<-strsplit(readLines(con=CNVdiseaseFile,n=2,encoding = "UTF-8")[2],split="\t")[[1]]
    ColNames<-c("chrom","loc.start","loc.end","type","name_ch")
    if (length(tmpLine)>length(ColNames)) ColNames<-c("chrom","loc.start","loc.end","type","syndrome","Genotype","Size")
    data<-read.delim(CNVdiseaseFile,header=T,fileEncoding = "UTF-8",check.names = F,stringsAsFactors = F,col.names=ColNames)
    if (!chrBool) data$chrom<-gsub("[cC]hr","",data$chrom,perl=T)
    data$chrom <- ifelse(data$chrom==23,'X',data$chrom)
    data$type <- ifelse(grepl('del|loss',data$type,ignore.case = TRUE, perl = TRUE),'Loss','Gain')
    data$variable<-rep("CNV",times=nrow(data))
    data
}

loadUPDdisease<-function(UPDdiseaseFile,chrBool){
    data<-read.table(UPDdiseaseFile,header=F,sep="\t",comment.char = "!",stringsAsFactors = F,
                check.names = F,col.names=c('chrom','start','end','UPDdisease'))
    if (!chrBool) data$chrom<-gsub("[cC]hr","",data$chrom,perl=T)
    data$variable<-rep("CNV",times=nrow(data))
    data
}

removeDup <- function(str) paste(rle(strsplit(str, "")[[1]])$values, collapse="") # Function to remove duplicated values in a string

for (name in c('reference_fai', 'out_chrom', 'out_genome', 'input_bed', 'vaf_bed','samples')) {
    if (is.na(argv[[name]])) {
        print(p);
        stop(sprintf('Argument %s is empty!', name));
    }
}

if (is.na(argv$samples)) {
    stop('Argument to --samples is empty');
} else {
    argv$samples = strsplit(argv$samples, ',')[[1]];
}

# Define chromosomes.
CHROMS = c(as.character(1:22), "X", "Y")

# Load chromosome lengths.
flog.info('Loading FAI file %s', argv$reference_fai);
chrom_lens = read_tsv(argv$reference_fai, col_names = c('chrom', 'length', 'offset', 'line_chars', 'line_bytes'), col_types = 'cdcii') %>%
    mutate(chrom = gsub("^chr","",chrom,perl=TRUE)) %>% filter(chrom %in% CHROMS) %>%
    select(chrom, length);
chrom_offsets = data.frame(
    chrom=chrom_lens$chrom,
    length=chrom_lens$length,
    offset=c(0, head(cumsum(chrom_lens$length), -1)),
    end=c(tail(cumsum(chrom_lens$length), -1), 0)) %>%
    mutate(label_pos = offset + length / 2.0);
rownames(chrom_offsets) = chrom_offsets$chrom;
xlimits = list(
    min = min(chrom_offsets$offset),
    max = max(chrom_offsets$offset + chrom_offsets$length)
);
ylimits = list(
    min = -argv$axis_y_min,
    max = argv$axis_y_max
);

if (!is.na(argv$cytoband) && file.exists(argv$cytoband)){
    Cyto<-loadCytoBand(argv$cytoband,FALSE)
    cCyto<-do.call(rbind,Cyto[CHROMS])
    cCyto$chrom <- factor(cCyto$chrom, levels = CHROMS)
    cCyto$variable<-rep("VAF",times=nrow(cCyto))
    cCyto$aend = chrom_offsets[cCyto$chrom,]$offset+cCyto$end;
    # print(cCyto)
    pacen<-cCyto %>% filter(as.character(type) == "acen" & substring(name, 1, 1)=="p")
    pter<-data.frame(chrom=rep(pacen$chrom,each=3),x=c(rbind(pacen$start,pacen$end,pacen$start)),
        y=rep(c(ylimits$min-0.5,ylimits$min-0.3,ylimits$min-0.1),length(pacen$type)),type=rep(pacen$type,each=3))
    qacen<-cCyto %>% filter(as.character(type) == "acen" & substring(name, 1, 1)=="q")
    qter<-data.frame(chrom=rep(qacen$chrom,each=3),x=c(rbind(qacen$start,qacen$end,qacen$end)),
        y=rep(c(ylimits$min-0.3,ylimits$min-0.5,ylimits$min-0.1),length(qacen$type)),type=rep(qacen$type,each=3))
    pter$chrom<-factor(pter$chrom,levels=CHROMS)
    qter$chrom<-factor(qter$chrom,levels=CHROMS)
}

if (!is.na(argv$Polymorphism) && file.exists(argv$Polymorphism)){
    CNVPolymorphism<-loadCNVPolymorphism(argv$Polymorphism,FALSE)
    CNVPolymorphism$chrom<-factor(CNVPolymorphism$chrom, levels = CHROMS)
}
if (!is.na(argv$Disease) && file.exists(argv$Disease)){
    CNVdisease<-loadCNVdisease(argv$Disease,FALSE)
    CNVdisease$chrom<-factor(CNVdisease$chrom, levels = CHROMS)
}
if (!is.na(argv$UPD) && file.exists(argv$UPD)){
    UPDdisease<-loadUPDdisease(argv$UPD,FALSE)
    UPDdisease$chrom<-factor(UPDdisease$chrom, levels = CHROMS)
}

gene_files = c();
if (!is.na(argv$gene_beds)) {
    gene_files = strsplit(argv$gene_beds, ',')[[1]];
}
# Load gene BEDs.
genes = list();
for (gene_bed in gene_files) {
    genes[[gene_bed]] = read_tsv(gene_bed, col_names = c('chrom', 'begin', 'end', 'gene'), col_types = 'ciic') %>%
	    mutate(chrom = gsub("^chr","",chrom,perl=TRUE)) %>% filter(chrom %in% CHROMS);
}
genes = do.call(rbind, genes);
if (is.null(genes)) {
    genes = data.frame(x=c());
}
genes$offset = chrom_offsets[genes$chrom,]$offset;
genes$apos = (genes$offset + genes$begin + (genes$end - genes$begin) / 2);
genes$pos = (genes$begin + (genes$end - genes$begin) / 2);
genes$abegin = (genes$offset + genes$begin);
genes$aend = (genes$offset + genes$end);

# Prepare loading of mass data.
flog.info('Loading TSV file %s', argv$input_bed);
col_names = c('chrom', 'begin', 'end');
col_types = 'cdd';
for (sample in argv$samples) {
    col_names = c(col_names, paste(sample, 'log2r', sep = '.'))
    col_names = c(col_names, paste(sample, 'log2rSeg', sep = '.'))
    col_names = c(col_names, paste(sample, 'cov', sep = '.'))
    col_names = c(col_names, paste(sample, 'seg', sep = '.'))
    col_types = paste0(col_types, 'dddd');
}
raw_data = read_tsv(argv$input_bed, col_names = col_names, col_types = col_types, na = c('', 'NA', '.')) %>%
    mutate(chrom = gsub("^chr","",chrom,perl=TRUE)) %>% filter(chrom %in% CHROMS) %>%
    mutate(pos = (begin + (end - begin) / 2));
log2_data = bind_cols(select(raw_data, chrom, begin, end, pos), select(raw_data, -chrom, -begin, -end, -pos));

flog.info('Loading VAF file %s', argv$vaf_bed);
col_names = c('chrom', 'begin', 'end','allele');
col_types = 'cddc';
for (sample in argv$samples) {
    col_names = c(col_names, paste(sample, 'vaf', sep = '.'))
    col_types = paste0(col_types, 'd');
}

if (grepl('\\.vcf(\\.gz)?$',argv$vaf_bed,perl=TRUE)) {
    #CMD <- paste0(argv$bcftools," view --threads 8 -i 'N_ALT=1 & AVG(FMT/DP)>15 & MIN(FMT/DP)>5 & MIN(FMT/GQ)>15 & QUAL > 30 & MAX(FORMAT/AD[*:1]/FORMAT/DP[*]) > 0.1' ",
    #        argv$vaf_bed," | ",argv$bcftools," +fill-tags - -- -t FORMAT/VAF |",argv$bcftools," query -Hf '%CHROM\t%POS\t%END\t%REF/%ALT[\t%VAF]\n'")
    CMD <- paste0(argv$bcftools," view --threads 8 -i 'N_ALT=1 & QUAL > 30 ' ",
            argv$vaf_bed," | ",argv$bcftools," +fill-tags - -- -t FORMAT/VAF |",argv$bcftools," query -Hf '%CHROM\t%POS\t%END\t%REF/%ALT[\t%VAF]\n'")
	print(CMD)
    vaf_data <-read.table(pipe(CMD), header=T,comment.char="!",check.names = FALSE,stringsAsFactors = FALSE,na.strings = ".") %>%
            rename_all(function(X){gsub('#?\\[[0-9]+\\]','',X,ignore.case = T, perl=T)}) %>%
            rename_all(function(X){gsub('(\\.bam)?:VAF$','.vaf',X,ignore.case = T, perl=T)}) %>%
            rename(chrom = CHROM, begin = POS, end = END, allele = `REF/ALT`) %>%
            mutate(chrom = gsub("^chr","",chrom,perl=TRUE)) %>% filter(chrom %in% CHROMS) %>%
            mutate(pos = (begin + (end - begin) / 2));
}else{
    vaf_data <- read_tsv(argv$vaf_bed, col_names = col_names, col_types = col_types, na = c('', 'NA', '.'), skip=1) %>%
        mutate(chrom = gsub("^chr","",chrom,perl=TRUE)) %>% filter(chrom %in% CHROMS) %>%
        mutate(pos = (begin + (end - begin) / 2));
}
log2_vaf <- bind_cols(select(vaf_data, chrom, begin, end, pos), select(vaf_data, -chrom, -begin, -end, -pos, -allele));
print(head(log2_vaf))

data_slices = list();
for (sample in argv$samples) {
    slice = log2_data %>%
        select(chrom, pos,
            log2r = ends_with(paste(sample, 'log2r', sep = '.')),
            # sex = starts_with(paste(sample, 'seg', sep = '.')),
            ncov = starts_with(paste(sample, 'cov', sep = '.')),
            seg = starts_with(paste(sample, 'seg', sep = '.'))) %>%
        mutate( sample = sample, chrom = ifelse(chrom=='23','X',ifelse(chrom=='24','Y',chrom)));
    slice$offset = chrom_offsets[slice$chrom,]$offset;
    slice = slice %>%
        mutate(apos = pos + offset) %>%  # absolute pos
        # mutate(  # to bp
        #     # ncov = 2^(ncov)*ifelse(sex==1,ifelse(chrom=='Y',0.05,2),ifelse(grepl('[XY]',chrom,ignore.case = TRUE, perl = TRUE),1,2)),
        #     # seg = 2^(seg)*ifelse(sex==1,ifelse(chrom=='Y',0.05,2),ifelse(grepl('[XY]',chrom,ignore.case = TRUE, perl = TRUE),1,2)),
        #     pos = pos,
        #     apos = apos
        # ) %>%
        select(-offset) %>%
        mutate(col = ifelse(findInterval(apos,as.numeric(c(0,sort(cCyto$aend))),rightmost.closed = TRUE)%%2==1,"A","B"));
    data_slices[[sample]] = slice;
}
all_data = do.call(rbind, data_slices);
all_data$sample = factor(all_data$sample, levels = argv$samples);

data_slices_vaf = list();
for (sample in argv$samples) {
    slice = log2_vaf %>%
        select(chrom, pos, vaf = starts_with(paste(sample, 'vaf', sep = '.'))) %>%
        mutate( sample = sample, chrom = ifelse(chrom=='23','X',ifelse(chrom=='24','Y',chrom))) %>%
        filter(as.numeric(vaf)>=0.01 & as.numeric(vaf)<=0.99) %>%
        mutate( deltaVAF = abs(vaf-0.5));
    slice$offset = chrom_offsets[slice$chrom,]$offset;
    slice = slice %>% mutate(apos = pos + offset) %>% select(-offset) %>%
        mutate(col = ifelse(findInterval(apos,as.numeric(c(0,sort(cCyto$aend))),rightmost.closed = TRUE)%%2==1,"A","B"));
#    ranges(slice$vaf)
    data_slices_vaf[[sample]] = slice;
}
all_vaf = do.call(rbind, data_slices_vaf);
all_vaf$sample = factor(all_vaf$sample, levels = argv$samples);

nsamples = length(argv$samples);

cols = list(
    ncov = "lightgray",
    seg = "red",
    extremes = "magenta",
    gene_region = "#DFFF00AA",
    gene_name = "black",
    grid = "darkgray"
);

# genome-wide plotting
flog.info("Plotting genome to %s", argv$out_genome);
CairoPNG(sprintf(argv$out_genome), width = 1200 * 4, height = 300 * nsamples * 4, res = 64 * 4 );
par(omi = rep(1.0, 4), mar = c(0,0,0,0), mfrow = c(nsamples*2, 1));

for (s in argv$samples) {
    # Limit data to current sample for plotting.
    flog.info("  => %s", s);
    sub_df = all_data %>%
        filter(as.character(sample) == s & !is.na(ncov) & !is.na(seg)) %>%
        mutate(rounded_seg = as.integer(round(seg * 10))) %>%
        mutate(seg_diff = ifelse(rounded_seg - lag(rounded_seg) != 0, 1, 0)) %>%
        mutate(seg_diff = ifelse(is.na(seg_diff), 0, seg_diff)) %>%
        mutate(seg_no = cumsum(seg_diff)) %>%
        select(-seg_diff, -rounded_seg);
    # Compute segment medians and join with original value
    seg_medians = sub_df %>%
        group_by(seg_no) %>%
        summarise(seg_median = median(seg));
    sub_df = left_join(sub_df, seg_medians, by = "seg_no");
    sub_df$chrom<-factor(sub_df$chrom,levels=CHROMS)
    sub_df$variable<-rep('CNV',times=length(sub_df$chrom))

    # Draw coverage as point cloud
    flog.info("    => coverage");
    plot(ncov ~ apos,
        data = sub_df,
        col = cols$ncov,
        bg = cols$ncov,
        axes = FALSE,
        cex = 0.1,
        pch = 22,
        xlim = as.double(xlimits),
        ylim = as.double(ylimits),
        xaxs='i'
    );
    # mtext(s, 2, 4, cex=0.8);
    mtext(expression('CN'), 2, 2);
    abline(h=c(0,1,2,3,4),lty=5,lwd=c(0.6,0.2,0.2,0.2,0.2),col=c('black','black','green','black','black'))
    box();
    axis(2);

    # Overlay coverage point cloud with segmentation
    flog.info("    => segmentation");
    points(
        seg_median ~ apos,
        data = sub_df,
        col = cols$seg,
        bg = cols$seg,
        cex = 0.3,
        pch = 22
    );

    # Draw marker for too small and too large values
    flog.info("    => markers");
    too_small = sub_df %>% filter(seg < ylimits$min);
    too_small$seg = rep(ylimits$min, length(too_small$seg));
    points(
        seg ~ apos,
        data = too_small,
        col = cols$extremes,
        bg = cols$extremes,
        cex = 1,
        pch = 25);
    too_small = sub_df %>% filter(seg > ylimits$max);
    too_small$seg = rep(ylimits$max, length(too_small$seg));
    points(
        seg ~ apos,
        data = too_small,
        col = cols$extremes,
        bg = cols$extremes,
        cex = 1,
        pch = 24);
    for (offset in tail(chrom_offsets$offset, -1)) {
        abline(v = offset);
    }
    if (nrow(genes) > 0) {
        flog.info('    => %d genes', nrow(genes));
        ys = head(rep(c(-2, -2.5, -3, -3.5, -4), length(genes$apos)), length(genes$apos));
        rect(
            xleft = genes$abegin,
            ybottom = ylimits$min,
            xright = genes$aend,
            ytop = ylimits$max,
            density = NA,
            col = cols$gene_region
        );
        pointLabel(
            genes$apos,
            ys,
            labels = genes$gene,
            col = cols$gene_name);
    } else {
        flog.info('    => no genes');
    }
    # title and bottom label
    if (s == argv$samples[[1]]) {
        mtext(sprintf(s), 3, 2);
    }
    flog.info("  => %s", s);
    sub_vaf = all_vaf %>% filter(as.character(sample) == s & !is.na(vaf));

    plot(
        vaf ~ apos,
        data = sub_vaf,
        col = "lightgray",
        bg = "lightgray",
        axes = FALSE,
        cex = 0.1,
        pch = 22,
        xlim = as.double(xlimits),
        ylim = c(0,1),
        xaxs='i'
    );
    # mtext(s, 2, 4, cex=0.8);
    mtext(expression('VAF'), 2, 2);
    abline(h=c(0.33,0.5,0.67),lty=5,lwd=c(0.2,0.2,0.2),col='black')
    box();
    axis(2);
    if (s == argv$samples[[nsamples]]) {
        axis(1, at=chrom_offsets$label_pos, labels=chrom_offsets$chrom, tick=FALSE, line=NA, cex.axis=0.8);
        mtext("chromosomes", 1, 2);
    }
    for (offset in tail(chrom_offsets$offset, -1)) {
        abline(v = offset);
    }

    p1 <- ggplot(data=sub_df, aes(x=pos, y=ncov)) +
        # geom_point(size=0.1,aes(colour =col)) + scale_color_manual(values=c(A=Colors[1],B=Colors[7])) +
		# geom_point(aes(colour = ncov,size=abs(as.numeric(ncov)-2)*0.04+0.06)) +
        geom_point(aes(colour = ncov), size=0.1) +
        scale_colour_gradient2(midpoint=2,limits=c(0,4),low = "blue",mid = "gray80",high = "red") + #scale_colour_gradient2(midpoint = 2,low = "blue",mid = "gray80",high = "red") +
        geom_hline(yintercept=2, linetype=1, color = "springgreen4", linewidth=0.25) +
        xlab("Chromosome") +
        ylab("Copy Number") +
        facet_grid(chrom ~ ., scales="free_x", space="free_x") +
        coord_cartesian(xlim=c(0,249250621),ylim=c(ylimits$min-1, ylimits$max)) +
        geom_rect(data=cCyto %>% filter(as.character(type) != "acen"),inherit.aes=FALSE, mapping=aes(xmin=start, xmax=end, ymin=ylimits$min-0.5, ymax=ylimits$min-0.1, fill=type),linewidth=0.01,color='black') +
        geom_polygon(data = pter,inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',linewidth=0.01) +
        geom_polygon(data = qter,inherit.aes=FALSE,mapping=aes(x=x, y=y,fill=type),color='black',linewidth=0.01) +
        scale_fill_manual(values=c("stalk"="#647FA4","gpos25"="#C8C8C8","gpos50"="#C8C8C8","gpos75"="#828282","gpos100"="#C8C8C8","gvar"="#DCDCDC","gneg"="#FFFFFF","acen"="red")) +
        scale_x_continuous(expand = c(0, 0),labels=function(x){paste0(x*1e-6,"M")}) +
        scale_y_continuous(breaks = seq(from=ylimits$min-1, ylimits$max,by=1)) +
        geom_text(data=cCyto,inherit.aes=FALSE,mapping=aes(x=start+(end-start)/2, y=ylimits$min-0.65, label=paste(gsub("[Cc]hr","",chrom,perl=T),name,sep='')), size=0.8,angle=70) +
        geom_vline(data=cCyto,mapping=aes(xintercept=start), linetype=3, linewidth=0.1,colour = "#C8C8C8") +
        geom_hline(yintercept=seq(from=ylimits$min,to=ylimits$max,by=1), color='#C8C8C8', linewidth=0.1)+
        geom_line(aes(x=pos, y=seg),linewidth=0.25,color="springgreen") +
        new_scale_color()+
        geom_segment(data=CNVPolymorphism,inherit.aes=FALSE,aes(x=start, xend=end, y=ylimits$max-0.05, yend=ylimits$max-0.05,color=type), linewidth=0.8,linetype=1) +
        geom_segment(data=CNVdisease,inherit.aes=FALSE,aes(x=loc.start, xend=loc.end, y=ylimits$min+0.05, yend=ylimits$min+0.05,color=type), linewidth=0.8,linetype=1) +
        scale_color_manual(values=c("Gain"="red","Loss"="blue")) +
        theme(axis.text.x = element_text(angle=0,size=5,hjust=0.5),axis.text.y = element_text(size=5),
            strip.text.y = element_text(angle=360),
            panel.background = element_blank(),panel.grid.major = element_blank(),
            legend.position = "none",panel.grid.minor.x = element_blank() ,panel.grid.minor.y = element_blank(),
            plot.margin = unit(c(0,0,0,0.1),'cm'),panel.spacing = unit(0.01, "lines"))
    ggsave(paste0("03_CNV/", s, ".CN_v.png"), width=9, height=15,dpi=256,device='png')

    MDF<-rbind(data.frame(chrom=sub_df$chrom,pos=sub_df$pos,value=sub_df$ncov,variable=rep("CNV",times=length(sub_df$chrom)),col=sub_df$col),
               data.frame(chrom=sub_vaf$chrom,pos=sub_vaf$pos,value=sub_vaf$vaf,variable=rep("VAF",times=length(sub_vaf$chrom)),col=sub_vaf$col))
    MDF$chrom<- factor(MDF$chrom, levels = CHROMS)

    ROHfile <- paste0("./AutoMap/",s,".bam/",s,".bam.HomRegions.tsv")
    if (!is.na(argv$roh) && file.exists(argv$roh)){
        ROHfile <- argv$roh
    }
    if (file.exists(ROHfile) && as.integer(system(paste0("grep -v -P '^#' ",ROHfile," | wc -l"),intern=T))>0 ){
        Seg<-read.table(ROHfile,header=F,comment.char="#",col.names=c("chrom","start","end","Size(Mb)","Nb_variants","Percentage_homozygosity"))
        Seg$chrom<-gsub("[cC]hr","",Seg$chrom,perl=T)
        Seg$chrom<-factor(Seg$chrom, levels = CHROMS)
        Seg$variable<-rep("VAF",times=nrow(Seg))
    }

    p2 <- ggplot(data=MDF, aes(x=value, y=pos)) +
    geom_point(mapping=aes(colour = value),size=0.1,data = ~ subset(., variable == "CNV")) +
    # geom_point(mapping=aes(colour = value, size = abs(as.numeric(value)-2)*0.05+0.06),data = ~ subset(., variable == "CNV")) +
    scale_size(range = c(0.1,0.4),breaks = seq(ylimits$min,ylimits$max)) +
    scale_colour_gradient2(midpoint=2,limits=c(ylimits$min,ylimits$max),low = "blue",mid = "gray80",high = "red") +
    geom_vline(xintercept=seq(from=ylimits$min,to=ylimits$max,by=1), color='#C8C8C8', linewidth=0.1)+
    new_scale_color()+
    geom_segment(data=CNVPolymorphism,inherit.aes=FALSE,aes(x=ylimits$max-0.05, xend=ylimits$max-0.05, y=start, yend=end,color=type), linewidth=0.8,linetype=1) +
    geom_segment(data=CNVdisease,inherit.aes=FALSE,aes(x=ylimits$min+0.05, xend=ylimits$min+0.05, y=loc.start, yend=loc.end,color=type), linewidth=0.8,linetype=1) +
    scale_color_manual(values=c("Gain"="red","Loss"="blue")) +
    geom_line(data=sub_df,inherit.aes=FALSE,mapping=aes(x=seg_median, y=pos),linewidth=0.25,color="springgreen",orientation="y") +
    new_scale_color()+
    # geom_point(color='#4682B4',size=0.1,data = ~ subset(., variable == "VAF")) +
    geom_point(mapping=aes(colour = col),size=0.1,data = ~ subset(., variable == "VAF")) +
    scale_color_manual(values=c(A='#4682B4',B='#778899'))+
    geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=ylimits$min, xmax=ylimits$max, ymin=start, ymax=end),fill='gray75',linewidth=0.1,color=NA,alpha=0.1)+
    geom_rect(data=cCyto,inherit.aes=FALSE, mapping=aes(xmin=0, xmax=1, ymin=start, ymax=end),fill=NA,color='black',linewidth=0.05) +
    geom_text(data=cCyto,inherit.aes=FALSE,mapping=aes(x=0.2, y=start+(end-start)/2, label=paste(gsub("[Cc]hr","",chrom,perl=T),name,sep='')), size=0.8,angle=10)
    if (file.exists(ROHfile) && as.integer(system(paste0("grep -v -P '^#' ",ROHfile," | wc -l"),intern=T))>0 ){
        p2<-p2+geom_rect(data=Seg,inherit.aes=FALSE,mapping=aes(xmin=0, xmax=1, ymin=start, ymax=end),fill='#FF6347',linewidth=0.1,color=NA,alpha=0.3)
    }
    p2<-p2+xlab("Chromosome") +
    ylab("Position(Mb)") +
    facet_nested(.~chrom + variable, scales="free")+
    facetted_pos_scales(x = rep(list(
        scale_x_continuous(breaks = seq(from=ylimits$min,to=ylimits$max,by=1),limits =c(ylimits$min, ylimits$max)),
        scale_x_continuous(breaks = seq(from=0,to=1,by=0.5),limits =c(0,1)))
    ,24),y = scale_y_continuous(expand = c(0, 0),labels=function(x){paste0(x/1000000,"M")},trans="reverse"))+
    theme(axis.text.x = element_text(angle=60,size=5,hjust=1),axis.text.y = element_text(size=5),
            panel.background = element_blank(),panel.grid.major= element_blank(),#panel.grid.minor.x = element_blank() ,
            panel.grid.minor.y = element_line(colour="#C8C8C8", linewidth=0.1),strip.placement = "outside",
			legend.position = c(0.82,0.157),legend.direction = "horizontal",plot.margin = unit(c(0,0,0,0.1),'cm'),panel.spacing = unit(0.01, "lines"))
    ggsave(paste0("03_CNV/", s, ".CNV_VAF.png"), width=16, height=9,dpi=256,device='png')

    p4 <- ggplot(data=MDF %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)), aes(x=value, y=pos)) +
    geom_point(mapping=aes(colour = value),size=0.1,data = ~ subset(., variable == "CNV")) +
    # geom_point(mapping=aes(colour = value, size = abs(as.numeric(value)-2)*0.05+0.06),data = ~ subset(., variable == "CNV")) +
    scale_size(range = c(0.1,0.4),breaks = seq(ylimits$min,ylimits$max)) +
    scale_colour_gradient2(midpoint=2,limits=c(ylimits$min,ylimits$max),low = "blue",mid = "gray80",high = "red") +
    geom_vline(xintercept=seq(from=ylimits$min,to=ylimits$max,by=1), color='#C8C8C8', linewidth=0.1)+
    new_scale_color()+
    geom_segment(data=CNVPolymorphism %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,aes(x=ylimits$max-0.05, xend=ylimits$max-0.05, y=start, yend=end,color=type), linewidth=0.8,linetype=1) +
    geom_segment(data=CNVdisease %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,aes(x=ylimits$min+0.05, xend=ylimits$min+0.05, y=loc.start, yend=loc.end,color=type), linewidth=0.8,linetype=1) +
    scale_color_manual(values=c("Gain"="red","Loss"="blue")) +
    geom_line(data=sub_df %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(x=seg_median, y=pos),linewidth=0.25,color="springgreen",orientation="y") +
    new_scale_color()+
    # geom_point(color='#4682B4',size=0.1,data = ~ subset(., variable == "VAF")) +
    geom_point(mapping=aes(colour = col),size=0.1,data = ~ subset(., variable == "VAF")) +
    scale_color_manual(values=c(A='#4682B4',B='#778899'))+
    geom_rect(data=UPDdisease %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(xmin=ylimits$min, xmax=ylimits$max, ymin=start, ymax=end),fill='gray75',linewidth=0.1,color=NA,alpha=0.1)+
    geom_rect(data=cCyto %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE, mapping=aes(xmin=0, xmax=1, ymin=start, ymax=end),fill=NA,color='black',linewidth=0.05) +
    geom_text(data=cCyto %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(x=0.2, y=start+(end-start)/2, label=paste(gsub("[Cc]hr","",chrom,perl=T),name,sep='')), size=0.8,angle=10)
    if (file.exists(ROHfile) && as.integer(system(paste0("grep -v -P '^#' ",ROHfile," | wc -l"),intern=T))>0 ){
        p4<-p4+geom_rect(data=Seg %>% filter(!grepl('X$|Y$',chrom,ignore.case = TRUE, perl = TRUE)),inherit.aes=FALSE,mapping=aes(xmin=0, xmax=1, ymin=start, ymax=end),fill='#FF6347',linewidth=0.1,color=NA,alpha=0.3)
    }
    p4<-p4+xlab("Chromosome") +
    ylab("Position(Mb)") +
    facet_nested(.~chrom + variable, scales="free")+
    facetted_pos_scales(x = rep(list(
        scale_x_continuous(breaks = seq(from=ylimits$min,to=ylimits$max,by=1),limits =c(ylimits$min, ylimits$max)),
        scale_x_continuous(breaks = seq(from=0,to=1,by=0.5),limits =c(0,1)))
    ,24),y = scale_y_continuous(expand = c(0, 0),labels=function(x){paste0(x/1000000,"M")},trans="reverse"))+
    theme(axis.text.x = element_text(angle=60,size=5,hjust=1),axis.text.y = element_text(size=5),
            panel.background = element_blank(),panel.grid.major= element_blank(),#panel.grid.minor.x = element_blank() ,
            panel.grid.minor.y = element_line(colour="#C8C8C8", linewidth=0.1),strip.placement = "outside",
			legend.position = c(0.82,0.157),legend.direction = "horizontal",plot.margin = unit(c(0,0,0,0.1),'cm'),panel.spacing = unit(0.01, "lines"))
    ggsave(paste0("03_CNV/", s, ".CNV_VAF_noXY.png"), width=16, height=9,dpi=256,device='png')

    p3 <- ggplot(data=MDF, aes(x=pos, y=value)) +
    geom_point(mapping=aes(colour = col),size=0.1,data = ~ subset(., variable == "VAF")) +
    scale_color_manual(values=c(A='#4682B4',B='#778899'))+
    geom_rect(data=UPDdisease,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=ylimits$min, ymax=ylimits$max),fill='gray75',linewidth=0.1,color=NA,alpha=0.1)+
    new_scale_color()+
    geom_point(mapping=aes(colour = value),size=0.1,data = ~ subset(., variable == "CNV")) +
    scale_colour_gradient2(midpoint=2,limits=c(ylimits$min,ylimits$max),low = "blue",mid = "gray80",high = "red") +
    geom_hline(yintercept=seq(from=ylimits$min,to=ylimits$max,by=1), color='#C8C8C8', linewidth=0.1)+
    new_scale_color()+
    geom_segment(data=CNVPolymorphism,inherit.aes=FALSE,aes(x=start, xend=end,y=ylimits$max-0.05, yend=ylimits$max-0.05,color=type), linewidth=0.8,linetype=1) +
    geom_segment(data=CNVdisease,inherit.aes=FALSE,aes(x=loc.start, xend=loc.end,y=ylimits$min+0.05, yend=ylimits$min+0.05,color=type), linewidth=0.8,linetype=1) +
    scale_color_manual(values=c("Gain"="red","Loss"="blue")) +
    geom_line(data=sub_df,inherit.aes=FALSE,mapping=aes(x=pos, y=seg_median),linewidth=0.25,color="springgreen") +
    geom_rect(data=cCyto,inherit.aes=FALSE, mapping=aes(xmin=start, xmax=end, ymin=ylimits$min-0.5, ymax=ylimits$min-0.1, fill=type),color='black',linewidth=0.05) +
    scale_fill_manual(values=c("stalk"="#647FA4","gpos25"="#C8C8C8","gpos50"="#C8C8C8","gpos75"="#828282","gpos100"="#C8C8C8","gvar"="#DCDCDC","gneg"="#FFFFFF","acen"="red")) +
    geom_text(data=cCyto,inherit.aes=FALSE,mapping=aes(x=start+(end-start)/2, y=ylimits$min-0.65, label=paste(gsub("[Cc]hr","",chrom,perl=T),name,sep='')), size=0.8,angle=70) +
    geom_vline(data=cCyto,mapping=aes(xintercept=start), linetype=3, linewidth=0.1,colour = "#C8C8C8")
    if (file.exists(ROHfile) &&
		as.integer(system(paste0("grep -v -P '^#' ",ROHfile," | wc -l"),intern=T))>0 ){
        p3<-p3+geom_rect(data=Seg,inherit.aes=FALSE,mapping=aes(xmin=start, xmax=end, ymin=0, ymax=1),fill='#FF6347',linewidth=0.1,color=NA,alpha=0.3)
    }
    p3<-p3+ylab("value") +
    xlab("Position(Mb)") +
    facet_nested(variable~chrom, scales="free",space="free_x")+
    facetted_pos_scales(y = rep(list(
        scale_y_continuous(breaks = seq(from=ylimits$min,to=ylimits$max,by=1),limits =c(ylimits$min, ylimits$max)),
        scale_y_continuous(breaks = seq(from=0,to=1,by=0.5),limits =c(0,1)))
    ,24),x=rep(list(scale_x_continuous(expand = c(0, 0),labels=function(x){paste0(x/1000000,"M")})),24) )+
    theme(axis.text.x = element_text(angle=60,size=5,hjust=1),axis.text.y = element_text(size=5),
            panel.background = element_blank(),#panel.grid.major= element_blank(),#panel.grid.minor.x = element_blank() ,
            panel.grid.minor.y = element_line(colour="#C8C8C8", linewidth=0.1),strip.placement = "outside",
			legend.position = "none",legend.direction = "horizontal",plot.margin = unit(c(0,0,0,0.1),'cm'),panel.spacing = unit(0.01, "lines"))
    ggsave(paste0("03_CNV/", s, ".CNV_VAF_h.png"), width=16, height=4,dpi=256,device='png')
}
dev.off();
#q("no");
# chromosome-wise plotting

for (c in CHROMS) {
    flog.info("Plotting chr%s to %s", c, sprintf(argv$out_chrom, c));
    CairoPNG(sprintf(argv$out_chrom, c), width = chrom_offsets[c,]$length %/% 30000, height = 450 * nsamples * 3,res = 256);
    par(omi = c(0.4,1,0.6,0.1), mar = c(0,0,0,0), mfrow = c(nsamples * 3, 1));
    for (s in argv$samples) {
        # Limit data to current chromosome.
        sub_vaf = all_vaf %>% filter(chrom == c & as.character(sample) == s & !is.na(vaf));

        if (nrow(sub_vaf)>3){
            flog.info("  => %s", s);
            plot(
                density(sub_vaf$vaf,adjust = 1/2),
                type = 'l',
                xlim = c(0,1),
                data = sub_vaf,
                col = "lightgray",
                bg = "lightgray",
                # axes = FALSE,
                cex = 0.25,
                pch = 22,
                xaxs='i',yaxs="i",main=NULL
            );
            mtext(s, 2, 4);
            mtext("Density", 2, 2);
            abline(v=c(0.33,0.5,0.67),lty=5,lwd=c(0.2,0.2,0.2),col='black')
        }
        flog.info("  => %s", s);
        sub_df = all_data %>%
            filter(chrom == c & as.character(sample) == s & !is.na(ncov) & !is.na(seg)) %>%
            mutate(rounded_seg = as.integer(round(seg * 10))) %>%
            mutate(seg_diff = ifelse(rounded_seg - lag(rounded_seg) != 0, 1, 0)) %>%
            mutate(seg_diff = ifelse(is.na(seg_diff), 0, seg_diff)) %>%
            mutate(seg_no = cumsum(seg_diff)) %>%
            select(-seg_diff, -rounded_seg);
        # Compute segment medians and join with original value
        seg_medians = sub_df %>%
            group_by(seg_no) %>%
            summarise(seg_median = median(seg));
        sub_df = left_join(sub_df, seg_medians, by = "seg_no");

        # Draw coverage as point cloud
        plot(
            ncov ~ pos,
            data = sub_df,
            col = cols$ncov,
            bg = cols$ncov,
            axes = FALSE,
            cex = 0.25,
            pch = 22,
            xlim = c(0, chrom_offsets[c,]$length),
            ylim = as.double(ylimits),
            xaxs='i',yaxs="i"
        );
        mtext(s, 2, 4);
        mtext("CN", 2, 2);
        abline(h=c(0,1,2,3,4),lty=5,lwd=c(0.6,0.2,0.2,0.2,0.2),col=c('black','black','green','black','black'))
        box();
        axis(2);
        # Overlay coverage point cloud with segmentation
        points(
            seg ~ pos,
            data = sub_df,
            col = cols$seg,
            bg = cols$seg,
            cex = 0.2,
            pch = 22
        );
        # Draw marker for too small and too large values
        too_small = sub_df %>% filter(seg < ylimits$min);
        too_small$seg = rep(ylimits$min, length(too_small$seg));
        points(
            seg ~ pos,
            data = too_small,
            col = cols$extremes,
            bg = cols$extremes,
            cex = 1,
            pch = 25);
        too_small = sub_df %>% filter(seg > ylimits$max);
        too_small$seg = rep(ylimits$max, length(too_small$seg));
        points(
            seg ~ pos,
            data = too_small,
            col = cols$extremes,
            bg = cols$extremes,
            cex = 1,
            pch = 24);
        if (s == argv$samples[[1]]) {
            mtext(sprintf("chr%s", c), 3, 2);
        }
		chrom_genes = data.frame()
        if (nrow(genes)) chrom_genes = genes %>% filter(chrom == c);
        if (nrow(chrom_genes) > 0) {
            flog.info('    => %d genes', nrow(chrom_genes));

            ys = head(rep(c(-2, -2.5, -3, -3.5, -4), length(chrom_genes$pos)), length(chrom_genes$pos));
            rect(
                xleft = chrom_genes$begin,
                ybottom = ylimits$min,
                xright = chrom_genes$end,
                ytop = ylimits$max,
                density = NA,
                col = cols$gene_region
            );
            pointLabel(
                chrom_genes$pos,
                ys,
                labels = chrom_genes$gene,
                col = cols$gene_name);
        } else {
            flog.info('    => no genes');
        }
        if(nrow(sub_vaf)>0){
            flog.info("  => %s", s);
            plot(
                vaf ~ pos,
                data = sub_vaf,
                col = "lightgray",
                bg = "lightgray",
                # axes = FALSE,
                cex = 0.25,
                pch = 22,
                xlim = c(0, chrom_offsets[c,]$length),
                ylim = c(0,1),
                xaxs='i',yaxs="i"
            );
            mtext(s, 2, 4);
            mtext("VAF", 2, 2);
            abline(h=c(0.33,0.5,0.67),lty=5,lwd=c(0.2,0.2,0.2),col='black')
            if (s == argv$samples[[nsamples]]) {
                axis(1);
                mtext("position [bp]", 1, 2);
            }
        }
    }
    dev.off();
}
CMD<-paste('convert -resize 35%x35% -append',paste(sprintf(argv$out_chrom, c(1:22,'X','Y')),collapse=' ',sep=''),paste("03_CNV/",argv$samples[[1]],'.cnv_chrom.png',sep='')," && rm -rf ",paste(sprintf(argv$out_chrom, c(1:22,'X','Y')),collapse=' ',sep=''),sep=' ');
print(CMD);
system(CMD);
