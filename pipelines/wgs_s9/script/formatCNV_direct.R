#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("usage: formatCNV_direct.R <seg.tsv> <CNVseq.bed>", call. = FALSE)
}

input_file <- args[[1]]
output_file <- args[[2]]

if (!file.exists(input_file)) {
  stop(sprintf("input file does not exist: %s", input_file), call. = FALSE)
}

seg <- read.table(
  input_file,
  header = TRUE,
  sep = "	",
  stringsAsFactors = FALSE,
  check.names = FALSE,
  encoding = "UTF-8",
  quote = "",
  comment.char = ""
)

required <- c("chrom", "start", "end", "CopyNumber", "zScore", "type", "MosRatio")
missing <- setdiff(required, names(seg))
if (length(missing) > 0) {
  stop(sprintf("missing required columns: %s", paste(missing, collapse = ",")), call. = FALSE)
}

mos_ratio <- suppressWarnings(as.numeric(seg[["MosRatio"]]))
keep <- !is.na(mos_ratio) & mos_ratio > 0.3
out <- seg[keep, c("chrom", "start", "end", "CopyNumber", "zScore", "type"), drop = FALSE]
if (nrow(out) > 0) {
  out[["type"]] <- ifelse(out[["type"]] == "DEL", "-", "+")
}

dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
write.table(out, file = output_file, sep = "	", quote = FALSE, row.names = FALSE, col.names = FALSE)
