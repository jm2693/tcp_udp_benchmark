#!/usr/bin/env python3
"""
TCP/UDP echo client boilerplate.
"""
import argparse
import json
import time

CSV_FIELDS = [
    "protocol",
    "client_id",
    "client_count",
    "payload_bytes",
    "request_num",
    "connect_time_ms",
    "rtt_ms",
    "timestamp",
    ]

##### Suggested helper functions; feel free to modify as needed. #####
def now_wall() -> float:
    return time.time()


def now_mono() -> float:
    return time.monotonic()


def log_event(fp, event: dict):
    fp.write(json.dumps(event, sort_keys=True) + "\n")
    fp.flush()
    
def recv_data(socket, payload_size) -> bytes:
    data = b''
    while len(data) < payload_size:
        chunk = socket.recv(payload_size - len(data))
        if not chunk:
            return data
        
        data += chunk
        
    return data

##### Required functions to implement. Do not change signatures. #####
def run_tcp_client(host: str, port: int, log_path: str,
                   payload_bytes: int, requests: int, clients: int) -> None:
    """Run the TCP client benchmark."""
    
    def client_worker():
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
    
    proto = args.proto
    host = args.host
    port = args.port
    payload_bytes = args.payload_bytes
    requests = args.requests
    clients = args.clients
    log = args.log
    
    if proto == "tcp":
        run_tcp_client(host, port, log, payload_bytes, requests, clients)
    else:
        run_udp_client(host, port, log, payload_bytes, requests, clients)
        
    


if __name__ == "__main__":
    main()
