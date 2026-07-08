import type {Sample} from "../api";

export type SampleSourceDisplay = {
  primary: string;
  secondary?: string;
  missing: boolean;
};

export function sampleSourceDisplay(sample: Sample): SampleSourceDisplay {
  const r1 = basename(sample.fq1);
  const r2 = basename(sample.fq2);
  const sourceDir = metadataString(sample, "source_dir");
  const sourceFolder = sourceDir ? basename(sourceDir) : "";
  const files = [r1, r2].filter(Boolean);

  if (files.length > 0) {
    return {
      primary: files.join(" / "),
      secondary: sourceFolder ? `Batch ${sourceFolder}` : undefined,
      missing: false,
    };
  }

  if (sourceFolder) {
    return {
      primary: `Batch ${sourceFolder}`,
      secondary: "FASTQ filenames were not captured",
      missing: false,
    };
  }

  return {
    primary: "Path not captured for this run",
    missing: true,
  };
}

function basename(path?: string | null): string {
  if (!path) return "";
  const normalized = path.replace(/\\/g, "/");
  return normalized.split("/").filter(Boolean).pop() || path;
}

function metadataString(sample: Sample, key: string): string {
  const value = sample.metadata?.[key];
  return typeof value === "string" ? value : "";
}
