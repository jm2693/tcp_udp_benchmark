#!/usr/bin/env python3
"""
TCP/UDP echo server boilerplate.
"""

import argparse
import json
import time
import socket
import threading

UDP_MAX = 65535
CSV_fields = ["protocol", "client_id", "client_count", "payload_bytes"]

##### Suggested helper functions; feel free to modify as needed. #####
def now_wall() -> float:
    return time.time()


def now_mono() -> float:
    return time.monotonic()


def log_event(fp, event: dict):
    fp.write(json.dumps(event, sort_keys=True) + "\n")
    fp.flush()
    
def recv_data(socket, payload_bytes) -> bytes:
    data = b''
    while len(data) < payload_bytes:
        chunk = socket.recv(payload_bytes - len(data))
        if not chunk: 
            return data
        
        data += chunk
        
    return data

##### Required functions to implement. Do not change signatures. #####
def run_tcp_server(bind: str, port: int, log_path: str,
                   payload_bytes: int, requests: int, clients: int) -> None:
    """Run the TCP server benchmark."""
    
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((bind, port))
    server_socket.listen(clients)
    
    def handle_client(client_socket, client_addr) -> None:
        while True:
            data = recv_data(server_socket, payload_bytes)
            if not data or len(data) < payload_bytes:
                break
            
            client_socket.sendall(data)
        
        client_socket.close()
        
    with open(log_path, "w") as log_fp:
        log_event(log_fp, {
            "event": "server_start",
            "protocol": "tcp",
            "bind": bind,
            "port": port,
            "payload_bytes": payload_bytes,
            "requests": requests,
            "clients": clients,
            "timestamp": now_wall()
        })
        
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()


def run_udp_server(bind: str, port: int, log_path: str,
                   payload_bytes: int, requests: int, clients: int) -> None:
    """Run the UDP server benchmark."""
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((bind, port))

    with open(log_path, "w") as log_fp:
        log_event(log_fp, {
            "event": "server_start",
            "protocol": "udp",
            "bind": bind,
            "port": port,
            "payload_bytes": payload_bytes,
            "requests": requests,
            "clients": clients,
            "timestamp": now_wall()
        })

        while True:
            data, addr = server_socket.recvfrom(UDP_MAX)
            if not data:
                break
            
            server_socket.sendto(data, addr)

        server_socket.close()


def parse_args() -> argparse.Namespace:
    """Parse CLI args.

    Required flags:
    - --proto tcp|udp
    - --bind
    - --port
    - --payload-bytes
    - --requests
    - --clients
    - --log
    """
    p = argparse.ArgumentParser(description="TCP/UDP echo server for benchmarking")
    p.add_argument("--proto", choices=["tcp", "udp"], required=True)
    p.add_argument("--bind", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5001)
    p.add_argument("--payload-bytes", type=int, default=1)
    p.add_argument("--requests", type=int, default=1)
    p.add_argument("--clients", type=int, default=1)
    p.add_argument("--log", required=True)
    return p.parse_args()


def main() -> None:
    """Entry point."""
    args = parse_args()
    
    proto = args.proto
    bind = args.bind
    port = args.port
    payload_bytes = args.payload_bytes
    requests = args.requests
    clients = args.clients
    log = args.log
    
    if proto == "tcp":
        run_tcp_server(bind, port, log, payload_bytes, requests, clients)
    else:
        run_udp_server(bind, port, log, payload_bytes, requests, clients)


if __name__ == "__main__":
    main()
