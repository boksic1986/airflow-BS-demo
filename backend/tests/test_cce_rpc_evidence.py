"""A storage-RPC label alone cannot grant automatic recovery."""
import pytest
from test_cce_recovery_evidence import evidence,validate,digest


@pytest.mark.parametrize('fault',[None,'operation','http_status','status_reason','transient_reason','creation_state'])
def test_exact_storage_rpc_fields_required_for_candidate(evidence,fault):
    _,candidate,terminal=evidence
    row=candidate['failures'][0]
    row.update(category='WORKER_CREATE_STORAGE_RPC_UNAVAILABLE',operation='create_namespaced_job',
        http_status=500,status_reason='InternalError',transient_reason='STORAGE_RPC_UNAVAILABLE_PEER_RESET')
    if fault:row[fault]=None
    terminal['plugin_failure_sha256']=digest(candidate)
    if fault:
        with pytest.raises(ValueError):validate(evidence)
    else:assert validate(evidence)['category']=='worker_create_storage_rpc_unavailable'
