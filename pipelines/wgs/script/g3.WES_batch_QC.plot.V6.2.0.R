#!/bi/software/R-4.0.2/bin/Rscript
library(argparser, quietly=TRUE);
suppressPackageStartupMessages(library(dplyr));
options(bitmapType="cairo")
options(scipen=999)

argv <- list();
p <- arg_parser("WES") %>%
    add_argument('--infile', help='input QC file of this batch.',type="character") %>%
    add_argument('--outfile', help='output png file.',type="character");

argv <- parse_args(p);
cat("Arguments are as follows\n",file=stderr());
str(argv);

if (is.na(argv$infile)) {
    print(p);
    stop(sprintf('Argument infile is empty!'));
}

infile <- argv$infile
outfile <- argv$outfile
batch <- gsub(".QC.tsv","",basename(infile))

## main()
library(ggplot2)
library(reshape2)
library(ggpubr)
library(parallel,quietly=TRUE)
library(ggh4x,quietly=TRUE)
library(ggpmisc)

#
Colors <- c('#4682B4','#6B8E23','#87CEEB','#A0522D','#FF8C00','#6A5ACD','#778899','#DAA520','#B22222','#FF6699')

data_read <- function(file, batch){
        Data <- read.table(file, header=T, comment.char="", stringsAsFactors=F, check.names=F,sep="\t")
        tmp_data <- list()

        tmp_data$batch <- batch

        # tmp_data$sample_seq <- c(1:length(Data$`Sample_ID`))
        tmp_data$samples <- gsub("-.*","",Data$`Sample_ID`)

        # tmp_data$raw_reads <- as.numeric(Data$`Raw_reads`)
        # tmp_data$clean_reads <- as.numeric(Data$`Clean_reads`)

        tmp_data$raw_bases <- as.numeric(Data$`Raw_bases`)/1000000000
        tmp_data$clean_bases <- as.numeric(Data$`Clean_bases`)/1000000000

        tmp_data$raw_gc <- as.numeric(gsub("%","",Data$`Raw_GC%`))
        tmp_data$clean_gc <- as.numeric(gsub("%","",Data$`Clean_GC%`))

        tmp_data$raw_q30 <- as.numeric(gsub("%","",Data$`Raw_Q30%`))
        tmp_data$clean_q30 <- as.numeric(gsub("%","",Data$`Clean_Q30%`))

        tmp_data$reads_with_adapter <- as.numeric(Data$`Reads_with_Adapter`)/1000000

        tmp_data$fold80 <- as.numeric(Data$`FOLD_80_BASE_PENALTY`)

        tmp_data$duplicated_reads <- as.numeric(gsub("%","",Data$`Duplicated_reads%`))

        tmp_data$mapped_reads <- as.numeric(gsub("%","",Data$`Mapped_Reads%`))
        tmp_data$unique_mapped_reads <- as.numeric(gsub("%","",Data$`Unique_Mapped_Reads%`))
        tmp_data$properly_paired_reads <- as.numeric(gsub("%","",Data$`Properly_paired_Reads%`))
        tmp_data$target <- as.numeric(gsub("%","",Data$`On_Target_Reads%`))

        # tmp_data$average_depth <- as.numeric(Data$`Average_Depth`)
        # tmp_data$median_depth <- as.numeric(Data$`Median_Depth`)

        tmp_data$depth20 <- as.numeric(gsub("%","",Data$`>=20X`))
        tmp_data$depth100 <- as.numeric(gsub("%","",Data$`>=100X`))

        tmp_data$l150 <- as.numeric(gsub("%","",Data$`<=100insert_Reads%`)) + as.numeric(gsub("%","",Data$`(100,150]insert_Reads%`))
        tmp_data$l400 <- as.numeric(gsub("%","",Data$`(400,500]insert_Reads%`)) + as.numeric(gsub("%","",Data$`>500insert_Reads%`))
        
        return(as.data.frame(tmp_data))
}


geom_plt <- function(tmp_data, outfile){
        tmp_data <- tmp_data
        outfile <- outfile

        # p1_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "raw_reads","clean_reads"))), id="samples")
        # p1 <- ggplot(data=p1_data, aes(x=samples, y=value, group=variable, color=variable))+
        #     geom_point(size=1)+
        #     geom_line(linetype="dashed", size=0.8)+
        #     xlab("Samples")+ 
        #     ylab("Reads Count")+
        #     theme_bw()+
        #     ggtitle("Final weight, by diet")+
        # 
        #     theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_text(size=15), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.key = element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
        #     scale_colour_discrete(name="Reads Count", breaks=c("raw_reads","clean_reads"), labels=c("Raw_reads", "Clean_reads"))


        p2_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "raw_bases","clean_bases"))), id="samples")
        p2 <- ggplot(data=p2_data, aes(x=samples, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_line(linetype="dashed", size=0.8)+
            xlab("Samples")+
            ylab("Raw_bases(G)")+
            theme_bw()+
            ggtitle("Raw_bases")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text = element_text(size=15), legend.key = element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="Bases Count", breaks=c("raw_bases","clean_bases"), labels=c("Raw_bases", "Clean_bases"))


        p3_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "raw_q30","clean_q30"))), id="samples")
        p3 <- ggplot(data=p3_data, aes(x=samples, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_line(linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("Q30(%)")+
            theme_bw()+
            ggtitle("Q30")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text=element_text(size=15), legend.key=element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="Q30(%)", breaks=c("raw_q30","clean_q30"), labels=c("Raw_Q30%", "Clean_Q30%"))+
            expand_limits(y=96)

        p4_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "raw_gc","clean_gc"))), id="samples")
        p4 <- ggplot(data=p4_data, aes(x=samples, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_line(linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("GC(%)")+
            theme_bw()+
            ggtitle("GC")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text=element_text(size=15), legend.key=element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="GC(%)", breaks=c("raw_gc","clean_gc"), labels=c("Raw_GC%", "Clean_GC%"))


        p5 <- ggplot(data=tmp_data, aes(x=samples, y=reads_with_adapter, group=1))+
            geom_point(colour="red", size=1)+
            geom_line(colour="red", linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab(expression(paste(plain("Reads_with_Adapter (")%*%10^6, ")")))+
            theme_bw()+
            ggtitle("Reads_with_Adapter")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15))


        p6 <- ggplot(data=tmp_data, aes(x=samples, y=fold80, group=1))+
            geom_point(colour="red", size=1)+
            geom_line(colour="red", linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("FOLD_80_BASE_PENALTY")+
            theme_bw()+
            ggtitle("FOLD_80")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15))


        p7 <- ggplot(data=tmp_data, aes(x=samples, y=duplicated_reads, group=1))+
            geom_point(colour="red", size=1)+
            geom_line(colour="red", linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("Duplicated_reads(%)")+
            theme_bw()+
            ggtitle("Duplicated_reads")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15))


        p8_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "mapped_reads", "properly_paired_reads", "unique_mapped_reads", "target"))), id="samples")
        p8 <- ggplot(data=p8_data, aes(x=samples, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_line(linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("Mapping(%)")+
            theme_bw()+
            ggtitle("Mapping")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text=element_text(size=15), legend.key=element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="比对率(%)", breaks=c("mapped_reads", "properly_paired_reads", "unique_mapped_reads", "target"), labels=c("Mapped_Reads%", "Properly_paired_Reads%", "Unique_Mapped_Reads%", "On_Target_Reads%"))+
            expand_limits(y=105)

        # p9_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "average_depth", "median_depth"))), id="samples")
        # p9 <- ggplot(data=p9_data, aes(x=samples, y=value, group=variable, color=variable))+
        #     geom_point(size=1)+
        #     geom_line(linetype="dashed", size=0.8)+
        #     xlab("Samples")+ 
        #     ylab("Depth")+
        #     theme_bw()
        #     theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_text(angle=75,size=10,hjust=1), axis.text.y=element_text(size=15), legend.title=element_blank(), legend.key = element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
        #     scale_colour_discrete(name="Depth", breaks=c("average_depth", "median_depth"), labels=c("Average_Depth", "Median_Depth"))+
        #     expand_limits(y=250)

        p10_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "depth20", "depth100"))), id="samples")
        p10 <- ggplot(data=p10_data, aes(x=samples, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_line(linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("Depth(%)")+
            theme_bw()+
            ggtitle("Depth")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_blank(), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text=element_text(size=15), legend.key=element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="Depth(%)", breaks=c("depth20", "depth100"), labels=c(">=20X", ">=100X"))+
            expand_limits(y=105)

        p11_data <- melt(as.data.frame(subset(tmp_data, select = c("samples", "l150", "l400"))), id="samples")
        p11 <- ggplot(data=p11_data, aes(x=samples, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_line(linetype="dashed", size=0.8)+
            xlab("Samples")+ 
            ylab("Insert_reads(%)")+
            theme_bw()+
            ggtitle("Insert_reads")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_text(angle=75,size=10,hjust=1), axis.title.x=element_blank(), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text=element_text(size=15), legend.key = element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="Length of Insert Reads(%)", breaks=c("l150", "l400"), labels=c("<=150insert_Reads%", ">400insert_Reads%"))+
            expand_limits(y=16)

        p12_data <- melt(as.data.frame(subset(tmp_data, select = c("raw_bases", "l150", "l400"))), id="raw_bases")
        p12 <- ggplot(data=p12_data, aes(x=raw_bases, y=value, group=variable, color=variable))+
            geom_point(size=1)+
            geom_smooth(method="lm",formula = y ~ x, se=FALSE)+
            stat_poly_eq(formula = y ~ x, aes(label = paste(..eq.label.., ..rr.label.., sep = "~~~~")), parse=TRUE, label.x.npc=0.9, size=5)+
            xlab("Raw_bases(G)")+ 
            ylab("Insert_reads(%)")+
            theme_bw()+
            ggtitle("Insert_reads VS Raw_bases")+
            theme(plot.title = element_text(size=15, hjust = 0.5), axis.text.x=element_text(size=15), axis.title.x=element_text(size=15), axis.text.y=element_text(size=15), axis.title.y=element_text(size=15), legend.title=element_blank(), legend.text=element_text(size=15), legend.key = element_blank(), legend.background = element_blank(), legend.direction="horizontal", legend.justification=c(0,1), legend.position=c(0,1))+
            scale_colour_discrete(name="Length of Insert Reads(%)", breaks=c("l150", "l400"), labels=c("<=150insert_Reads%", ">400insert_Reads%"))+
            scale_x_continuous(expand=c(0, 0))

        pdf(NULL)
        # p_tmp <- ggarrange(p2,p3,p4,p5,p6,p7,p8,p10, ncol=2, nrow=4, align="hv", heights=c(1,1,1,1,1,1,1,1), common.legend=FALSE, hjust=0, vjust=0)
        ggarrange(p2,p3,p4,p5,p6,p7,p8,p10,p11,p12, ncol=2, nrow=5, align="v")
        ggsave(outfile, width=24, height=24, dpi=256, device="png")
}

if (file.exists(infile)){
    print(infile)
    tmp_data <- data_read(infile, batch)
    geom_plt(tmp_data, outfile)
}


















