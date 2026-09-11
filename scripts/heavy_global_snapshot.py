"""Entry point; deploy beside canonical heavy_snapshot_core.py."""
import importlib.util
from pathlib import Path

source = Path(__file__).with_name('heavy_snapshot_core.py')
if not source.is_file():
    source = Path(__file__).resolve().parents[1] / 'backend/app/heavy_global_snapshot.py'
spec = importlib.util.spec_from_file_location('heavy_snapshot_core', source)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
collect = core.collect
project_snapshot = core.project_snapshot
read_snapshot = core.read_snapshot
write_snapshot = core.write_snapshot
subprocess = core.subprocess
if __name__ == '__main__':
    core.main()
