"""Run with installed core SDK and requests; synthetic identities, NO network."""
import importlib.util
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch


def main():
    # Defense in depth: even an unexpected SDK discovery cannot open a socket.
    def blocked(*args, **kwargs): raise AssertionError('network prohibited in probe')
    socket.socket.connect = blocked
    source = Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location('bss_probe', source)
    bss = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bss)
    class Response:
        status_code = 200
        content = b'{"measure_units": []}'
    class Session:
        trust_env = True
        calls = []
        def request(self, method, url, **kwargs):
            assert (method, url) in {('GET', 'https://bss.myhuaweicloud.com'+bss.UNITS),
                                    ('POST', 'https://bss.myhuaweicloud.com'+bss.LIST),
                                    ('POST', 'https://bss.myhuaweicloud.com'+bss.USAGE)}
            assert kwargs['allow_redirects'] is False
            assert kwargs['timeout'] == (10, 30)
            headers = {key.lower(): value for key, value in kwargs['headers'].items()}
            assert headers['authorization'].startswith('SDK-HMAC-SHA256')
            assert headers['x-domain-id'] == 'synthetic-domain'
            assert 'x-project-id' not in headers
            assert kwargs['data'] == signed_bodies[-1]
            if url.endswith(bss.LIST):
                assert kwargs['data'] == '{"offset":0,"limit":1000}'
            if url.endswith(bss.USAGE):
                assert kwargs['data'] == '{"free_resource_ids":["synthetic-resource"]}'
            self.calls.append(url)
            return Response()
    session = Session()
    signed_bodies = []
    from huaweicloudsdkcore.auth.credentials import GlobalCredentials
    original_sign = GlobalCredentials.sign_request
    def capture_sign(self, request):
        signed_bodies.append(request.body)
        return original_sign(self, request)
    signing_patch = patch.object(GlobalCredentials, 'sign_request', capture_sign)
    signing_patch.start()
    call = bss.signed_transport({'ak': 'synthetic-ak', 'sk': 'synthetic-sk', 'domain_id': 'synthetic-domain'}, session)
    assert call('GET', bss.UNITS, None) == {'measure_units': []}
    call('POST', bss.LIST, {'offset': 0, 'limit': 1000})
    call('POST', bss.USAGE, {'free_resource_ids': ['synthetic-resource']})
    assert session.trust_env is False
    try: call('GET', 'https://untrusted.invalid', None)
    except bss.BssError: pass
    else: raise AssertionError('foreign route accepted')
    for code, reason in [(302, 'transport_error'), (403, 'forbidden'), (429, 'rate_limited')]:
        Response.status_code = code
        try: call('GET', bss.UNITS, None)
        except bss.BssError as error: assert str(error) == reason
        else: raise AssertionError('failed response accepted')
    assert len(session.calls) == 6
    signing_patch.stop()
    print(json.dumps({'status': 'passed', 'synthetic_signed_requests': 6, 'network_connections': 0}))


if __name__ == '__main__': main()
