#!/usr/bin/env python3
"""
TCP/UDP echo client boilerplate.
"""
import argparse
import json
import time
import socket
import csv
import threading

UDP_MAX = 65535
UDP_TIMEOUT = 5

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
def to_ms(time_s):
    return time_s * 1000;


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
        
    payload = b'\x00' * payload_bytes
    results = []
    lock = threading.Lock()

    def client_worker(client_id):
        worker_results = []

        t_conn_start = now_mono()
        t_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        t_socket.connect((host, port))
        t_conn_end = now_mono()
        connect_time_ms = to_ms(t_conn_end - t_conn_start)

        for req_num in range(requests):
            t_send = now_mono()
            t_socket.sendall(payload)
            response = recv_data(t_socket, payload_bytes)
            t_recv = now_mono()

            rtt_ms = to_ms(t_recv - t_send)

            worker_results.append({
                "protocol": "tcp",
                "client_id": client_id,
                "client_count": clients,
                "payload_bytes": payload_bytes,
                "request_num": req_num,
                "connect_time_ms": round(connect_time_ms, 4),
                "rtt_ms": round(rtt_ms, 4),
                "timestamp": now_wall(),
            })

        t_socket.close()
        with lock:
            results.extend(worker_results)
            
    threads = []
    for i in range(clients):
        t = threading.Thread(target=client_worker, args=(i,))
        threads.append(t)
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    results.sort(key=lambda r: (r["client_id"], r["request_num"]))
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)

def run_udp_client(host: str, port: int, log_path: str,
                   payload_bytes: int, requests: int, clients: int) -> None:
    """Run the UDP client benchmark."""
    
    payload = b'\x00' * payload_bytes
    results = []
    lock = threading.Lock()
    
    def client_worker(client_id):
        worker_results = []
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.settimeout(UDP_TIMEOUT)
        
        for req_num in range(requests):
            t_send = now_mono()
            client_socket.sendto(payload, (host, port))
            try:
                response, _ = client_socket.recvfrom(UDP_MAX)
            except socket.timeout:
                worker_results.append({
                    "protocol": "udp",
                    "client_id": client_id,
                    "client_count": clients,
                    "payload_bytes": payload_bytes,
                    "request_num": req_num,
                    "connect_time_ms": 0.0,
                    "rtt_ms": -1.0,
                    "timestamp": now_wall(),
                })
                continue
            t_recv = now_mono()
            
            rtt_ms = to_ms(t_recv - t_send)
            worker_results.append({
                "protocol": "udp",
                "client_id": client_id,
                "client_count": clients,
                "payload_bytes": payload_bytes,
                "request_num": req_num,
                "connect_time_ms": 0.0,
                "rtt_ms": round(rtt_ms, 4),
                "timestamp": now_wall(),
            })

        client_socket.close()

        with lock:
            results.extend(worker_results)
            
    threads = []
    for i in range(clients):
        t = threading.Thread(target=client_worker, args=(i,))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    results.sort(key=lambda r: (r["client_id"], r["request_num"]))
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    

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
