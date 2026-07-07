import {useMemo} from "react";

export type ParsedSampleRow = {
  rowNumber: number;
  sample_id: string;
  family_id?: string;
  fastq_path: string;
  sex?: string;
  project?: string;
};

export type SampleSheetResult = {
  rows: ParsedSampleRow[];
  errors: string[];
};

export function parseSampleSheetText(text: string): SampleSheetResult {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) return {rows: [], errors: ["sample sheet is empty"]};
  const delimiter = lines[0].includes("\t") ? "\t" : ",";
  const headers = lines[0].split(delimiter).map((header) => header.trim());
  const index = (name: string) => headers.findIndex((header) => header.toLowerCase() === name);
  const sampleIndex = index("sample_id");
  const fastqIndex = index("fastq_path");
  const familyIndex = index("family_id");
  const sexIndex = index("sex");
  const projectIndex = index("project");
  const errors: string[] = [];
  if (sampleIndex < 0) errors.push("sample_id column is required");
  if (fastqIndex < 0) errors.push("fastq_path column is required");
  const seen = new Set<string>();
  const rows: ParsedSampleRow[] = [];

  lines.slice(1).forEach((line, offset) => {
    const rowNumber = offset + 2;
    const cells = line.split(delimiter).map((cell) => cell.trim());
    const sampleId = sampleIndex >= 0 ? cells[sampleIndex] || "" : "";
    const fastqPath = fastqIndex >= 0 ? cells[fastqIndex] || "" : "";
    if (!sampleId) errors.push(`row ${rowNumber} sample_id is required`);
    if (!fastqPath) errors.push(`row ${rowNumber} fastq_path is required`);
    if (sampleId) {
      if (seen.has(sampleId)) errors.push(`duplicate sample_id ${sampleId}`);
      seen.add(sampleId);
    }
    rows.push({
      rowNumber,
      sample_id: sampleId,
      family_id: familyIndex >= 0 ? cells[familyIndex] || "" : "",
      fastq_path: fastqPath,
      sex: sexIndex >= 0 ? cells[sexIndex] || "" : "",
      project: projectIndex >= 0 ? cells[projectIndex] || "" : "",
    });
  });

  return {rows, errors};
}

export function SampleSheetUploader({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const parsed = useMemo(() => parseSampleSheetText(value), [value]);
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>Sample sheet preview</h2>
        <p>CSV/TSV demo parser for planned NIPT/WGS style submissions.</p>
      </div>
      <label className="field full">
        <span>Sample sheet text</span>
        <textarea
          aria-label="Sample sheet text"
          value={value}
          rows={7}
          placeholder="sample_id	fastq_path	sex	project"
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
      {parsed.errors.length ? (
        <div className="inline-error" role="alert">
          {parsed.errors.map((error) => (
            <div key={error}>{error}</div>
          ))}
        </div>
      ) : null}
      <div className="table-wrap">
        <table className="data-table compact">
          <thead>
            <tr>
              <th>row</th>
              <th>sample_id</th>
              <th>family_id</th>
              <th>fastq_path</th>
              <th>sex</th>
              <th>project</th>
            </tr>
          </thead>
          <tbody>
            {parsed.rows.map((row) => (
              <tr key={row.rowNumber}>
                <td>{row.rowNumber}</td>
                <td>{row.sample_id || "missing"}</td>
                <td>{row.family_id || "not set"}</td>
                <td className="path-text">{row.fastq_path || "missing"}</td>
                <td>{row.sex || "not set"}</td>
                <td>{row.project || "not set"}</td>
              </tr>
            ))}
            {parsed.rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-cell">
                  Paste CSV/TSV rows to preview samples.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
