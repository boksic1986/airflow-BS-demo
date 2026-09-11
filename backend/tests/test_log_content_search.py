from pathlib import Path
from types import SimpleNamespace

import pytest

from app import diagnostics_service as logs


def test_search_finds_content_before_tail_and_is_literal(tmp_path):
    path = tmp_path / 'analysis.log'
    path.write_text('FASTP [ok]\n' + 'finished\n' * 300)
    result = logs._search_log_file(path, query='fastp [', limit=200)
    assert result['lines'] == ['FASTP [ok]']
    assert result['match_count'] == 1
    assert result['search_complete'] is True


def test_search_bounds_results_and_marks_incomplete_scan(tmp_path):
    path = tmp_path / 'analysis.log'
    path.write_text('match\n' * 300)
    result = logs._search_log_file(path, query='match', limit=2, max_bytes=60)
    assert len(result['lines']) == 2
    assert result['truncated'] is True
    assert result['search_complete'] is False


def test_rule_log_index_uses_only_existing_safe_references(tmp_path):
    master = tmp_path / 'analysis.log'
    (tmp_path / '07_QC').mkdir()
    (tmp_path / '07_QC' / 'synthetic.fastp.log').write_text('fastp detail')
    (tmp_path / '07_QC' / 'link.log').symlink_to(master)
    master.write_text('rule pre_process_cleanFastq:\n'
                      '    log: 07_QC/synthetic.fastp.log\n'
                      '    log: ../escape.log, /etc/passwd, 07_QC/link.log, missing.log\n')
    items = logs._referenced_rule_logs(master, tmp_path, attempt=5, run_id='mock-a5')
    assert len(items) == 1
    assert items[0]['relative_path'] == '07_QC/synthetic.fastp.log'
    assert items[0]['rule'] == 'pre_process_cleanFastq'
    assert items[0]['source'] == 'rule_log'


def test_registered_wgs_log_search_and_unknown_key_rejection(tmp_path, monkeypatch):
    path = tmp_path / 'analysis.log'
    path.write_text('fastp earlier\n' + 'done\n' * 300)
    monkeypatch.setattr(logs, '_get_run', lambda *_: SimpleNamespace(attempt=5))
    monkeypatch.setattr(logs, '_wgs_run_log_items', lambda **_: [
        {'key':'approved', '_path':str(path), 'relative_path':'mirror/analysis.log'}])
    result = logs.get_wgs_run_log(session=None, analysis_id='mock', stream='stdout',
        tail=200, settings=None, key='approved', query='fastp')
    assert result['lines'] == ['fastp earlier']
    assert result['path'] == 'mirror/analysis.log'
    with pytest.raises(logs.LogNotFoundError):
        logs.get_wgs_run_log(session=None, analysis_id='mock', stream='stdout',
            tail=200, settings=None, key='../secret', query='fastp')
