from __future__ import annotations

import argparse
import ipaddress
import json
import subprocess


EXPECTED_NETWORK = "nipt_analysis_test_net"
EXPECTED_SUBNET = "192.168.199.0/24"
EXPECTED_GATEWAY = "192.168.199.1"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default=EXPECTED_NETWORK)
    args = parser.parse_args()
    if args.network != EXPECTED_NETWORK:
        raise SystemExit(f"network must be {EXPECTED_NETWORK}")
    payload = json.loads(
        subprocess.check_output(
            ["docker", "network", "inspect", args.network], text=True
        )
    )[0]
    configs = payload.get("IPAM", {}).get("Config", [])
    if configs != [{"Subnet": EXPECTED_SUBNET, "Gateway": EXPECTED_GATEWAY}]:
        raise SystemExit(f"unexpected IPAM config: {configs!r}")
    subnet = ipaddress.ip_network(EXPECTED_SUBNET)
    seen: dict[str, str] = {}
    for item in payload.get("Containers", {}).values():
        name = str(item.get("Name") or "")
        address = str(item.get("IPv4Address") or "").split("/", 1)[0]
        if not name or not address:
            continue
        ip = ipaddress.ip_address(address)
        if ip not in subnet or str(ip) in {EXPECTED_GATEWAY, str(subnet.network_address), str(subnet.broadcast_address)}:
            raise SystemExit(f"invalid attachment {name}={address}")
        if address in seen:
            raise SystemExit(f"duplicate attachment IP {address}: {seen[address]}, {name}")
        seen[address] = name
    print(json.dumps({"network": args.network, "subnet": EXPECTED_SUBNET, "gateway": EXPECTED_GATEWAY, "attachments": seen}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
