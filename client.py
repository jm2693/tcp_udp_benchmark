#!/usr/bin/env python3
"""
TCP/UDP echo client boilerplate.
"""
import argparse
import json
import time

##### Suggested helper functions; feel free to modify as needed. #####
def now_wall() -> float:
    return time.time()


def now_mono() -> float:
    return time.monotonic()


def log_event(fp, event: dict):
    fp.write(json.dumps(event, sort_keys=True) + "\n")
    fp.flush()

##### Required functions to implement. Do not change signatures. #####
def run_tcp_client(host: str, port: int, log_path: str,
                   payload_bytes: int, requests: int, clients: int) -> None:
    """Run the TCP client benchmark."""
    pass


def run_udp_client(host: str, port: int, log_path: str,
                   payload_bytes: int, requests: int, clients: int) -> None:
    """Run the UDP client benchmark."""
    pass


def parse_args() -> argparse.Namespace:
    """Parse CLI args.

    Required flags:
    - --proto tcp|udp
    - --host
    - --port
    - --payload-bytes
    - --requests
    - --clients
    - --log
    """
    p = argparse.ArgumentParser(description="TCP/UDP echo client for benchmarking")
    p.add_argument("--proto", choices=["tcp", "udp"], required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, default=5001)
    p.add_argument("--payload-bytes", type=int, default=64)
    p.add_argument("--requests", type=int, default=1)
    p.add_argument("--clients", type=int, default=1)
    p.add_argument("--log", required=True)
    return p.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()
    pass


if __name__ == "__main__":
    main()
