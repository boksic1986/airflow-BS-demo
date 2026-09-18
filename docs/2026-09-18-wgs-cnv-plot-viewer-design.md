# WGS CNV plot viewer design

## Decision and scope

Add a read-only **CNV plot** tab beside the existing Run Detail `QC` tab for
WGS runs. It presents the native per-sample genome CNV PNG already produced by
the workflow. It is not a QC decision, a CNV interpretation tool, or a new
analysis step.

The viewer retains the native PNG; it does not convert the plot to HTML or SVG.
Recreating a rasterized native plot as HTML/SVG would require a second plotting
implementation and could alter its presentation. An SVG that embeds the PNG
has no loading benefit.

This proposal adds no native WGS script, image build, DAG, database table,
pending behavior, result download, CNV calling parameter, or production
publication.

## Observed output contract

The inspected V4.2.1 test batch has one file per selected sample at:

```text
03_CNV/<sample_id>.CNV_genome.png
```

The six observed plots are RGB PNGs at `4800 x 1200`, approximately
0.41–0.45 MiB each (2.62 MiB total). Network transfer is modest, but decoding
one image requires roughly 23 MiB of browser pixel memory. The viewer therefore
loads one selected image only and does not preload an entire batch.

The observed test directory is evidence for the naming contract only. Runtime
code must resolve images from the run's frozen bound project root, never from a
hard-coded test path.

## Restricted backend contract

Add two WGS-only, authenticated endpoints:

```text
GET /api/runs/{analysis_id}/cnv-plots
GET /api/runs/{analysis_id}/cnv-plots/{sample_id}
```

The list response contains only selected sample IDs with an `available` flag
and an opaque per-image URL. It returns no absolute project path, raw artifact
directory, clinical fields, image bytes, or guessed sample IDs.

For both endpoints the backend must:

1. load the current attempt's frozen runtime binding and resolve its contained
   batch root with the same authorization boundary used by WGS QC/artifacts;
2. use only the current selected sample IDs from the run projection;
3. form the exact relative path `03_CNV/<sample_id>.CNV_genome.png` after
   validating the sample identity; and
4. reject symlinks, traversal, non-regular files, an unbound/missing result
   root, an unselected sample and non-WGS runs.

The image endpoint streams `image/png` with an inline safe filename,
`X-Content-Type-Options: nosniff` and the existing private/no-store response
policy. It does not expose a generic artifact download endpoint or accept a
path/query supplied by the browser.

An unavailable plot is ordinary result availability, not workflow/QC failure.
The list endpoint remains successful; its item has `available:false`. A
missing, unreadable or invalid selected image returns the existing controlled
not-available message, never a filesystem error.

## Run Detail presentation

- Add `CNV plot` to the WGS Run Detail tab list immediately after `QC`.
- On tab activation, fetch only the plot list (sample ID plus availability).
- The panel is a two-column layout: a narrow, vertically scrollable left list
  of sample IDs and a wide right image pane.
- Select the first available sample once; choosing a different row changes only
  the right image URL. Do not fetch hidden/nonselected images or encode them in
  JSON/base64.
- Render the native image with `max-width:100%`, `height:auto`, and
  `object-fit:contain`; the image pane may horizontally scroll at narrow
  viewport widths rather than crop CNV coordinates.
- Preserve the selected sample when normal Run Detail refresh occurs. A failed
  image request leaves the sample list visible and shows a compact inline error
  in the right pane.
- When no selected sample has a plot, show `暂无 CNV plot` in the pane. GATK and
  adapters without the WGS capability do not render this tab.

The tab contains only sample IDs and the native image. It deliberately excludes
clinical notes, QC tags, CNV text summaries, arbitrary artifact controls,
annotation filters and upload/download actions.

## Minimal implementation and validation

1. Add the controlled backend list/stream handlers beside existing WGS artifact
   resolution, reusing bound-root and selected-sample checks.
2. Add API client types/functions and a small `WgsCnvPlotTab` component; add
   `CNV plot` only to the WGS tab array.
3. Add synthetic focused tests for: selected available PNG, unavailable PNG,
   unselected sample rejection, traversal/symlink rejection, non-WGS absence,
   one-image-only front-end loading and selection switching.

No real image needs to enter Git. The existing inspected output is sufficient
for naming/size evidence; component tests use a synthetic small PNG response.
Do not run a biological workflow, re-download results or add a broad artifact
browser as part of this work.

## Acceptance and rollback

Acceptance requires a WGS run to list only its selected samples, load a single
authorized PNG when chosen, switch images without eager batch loading, and keep
missing images non-fatal. The image must not be reachable through an arbitrary
path or another run/sample identity.

Rollback removes the two endpoints and the WGS-only tab/component. It does not
alter CNV result files, bindings, QC records, workflow status or analysis data.
