# QC, logging, and reporting

- Adapters define allowed QC fields and normalize them into the shared QC response.
- The frontend renders normalized values and never parses workflow output files.
- Raw logs remain in controlled evidence storage; the database records opaque keys, hashes, terminal summaries, and structured events.
- Public APIs expose controlled relative paths only.
- Patient names, hospitals, clinical notes, and unrestricted file paths are excluded.

The WGS adapter reads the single frozen batch `QCstat.tsv` and exposes only approved metrics. Future adapters must provide their own parser and allowlist.
