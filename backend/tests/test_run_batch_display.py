from app.models import AnalysisRun
from app.run_service import _run_list_payload


def test_batch_runs_uses_gatk_batch_without_changing_existing_batch_priority():
    for pipeline, params, expected in [
        ("gatk", {"batch_no": None, "batch": "MOCK_WES_BATCH"}, "MOCK_WES_BATCH"),
        ("wgs", {"analysis_batch": "MOCK_WGS_BATCH", "batch_no": "project_dir", "batch": "other"}, "MOCK_WGS_BATCH"),
        ("gatk", {}, None),
    ]:
        run = AnalysisRun(analysis_id="MOCK_RUN", pipeline_name=pipeline,
                          status="running", params_json=params)
        result = _run_list_payload(run, sample_count=0, sample_qc_statuses=[],
            projected_qc_status=None, qc_highlights=[], workflow_summary=[], lifecycle=None)
        assert result["batch_no"] == expected
