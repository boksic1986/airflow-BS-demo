"""Offline subprocess boundary: execute real DAG functions with HTTP/SSH captured."""
import importlib
import io
import json
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch


def main():
    value=json.loads(sys.stdin.readline())
    wire=sys.stdout
    with redirect_stdout(io.StringIO()):
        dag=importlib.import_module('bio_'+value['pipeline'])
        calls=[];commands=[]
        def backend(path,**kw):
            calls.append({'path':path,**kw})
            wire.write(json.dumps({'backend':{'path':path,**kw}})+'\n');wire.flush()
            return json.loads(sys.stdin.readline())
        def ssh(command,**kw):
            commands.append(command)
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        context={'dag_run':SimpleNamespace(conf=value['conf'],run_id=value['dag_run_id'])}
        with patch.object(dag,'_backend_json',backend),patch.object(dag.subprocess,'run',ssh):
            run=dag.run_stage_on_200 if value['pipeline']=='wgs' else dag.run_stage
            for stage in ('prepare','step1_upload'):
                run(stage,**context)
            assert not calls and not commands
            if value['stage']=='finalize_run':dag.register_stage(value['stage'],**context)
            else:run(value['stage'],**context)
    print(json.dumps({'calls':calls,'commands':commands}))


if __name__=='__main__':main()
