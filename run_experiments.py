#!/usr/bin/env python3

import subprocess
import argparse
import time
import os
import sys
import csv
import matplotlib
import statistics
from collections import defaultdict
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROTOCOLS = ["tcp", "udp"]
PAYLOAD_SIZES = [64, 512, 1024, 4096, 8192]
CLIENT_COUNTS = [1, 10, 100, 1000]
REQUESTS_PER_CLIENT = WORKITEMS_PER_CLIENT = 100

PORT = 5001
REMOTE_DIR = "~/cs417/p1/tcp_udp_benchmark"
REMOTE_RESULTS_DIR = os.path.join(REMOTE_DIR, "results")
SERVER_STARTUP_DELAY = 2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")

TCP_PLOT_COLOR = "#1f77b4"
UDP_PLOT_COLOR = "#ff7f0e"


class RunRemote:
    def __init__(self, user, password_file, server_host, client_host):
        self.user = user
        self.password_file = os.path.abspath(password_file)
        self.server_host = server_host
        self.client_host = client_host
        self.server_dest = f"{user}@{server_host}"
        self.client_dest = f"{user}@{client_host}"

        if not os.path.isfile(self.password_file):
            print(f"ERROR: Password file not found: {self.password_file}")
            sys.exit(1)

    def _sshpass_prefix(self):
        return ["sshpass", "-f", self.password_file]

    def _ssh_opts(self):
        return ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]

    def ssh_run(self, host_dest, cmd, background=False, check=True):
        if background:
            remote_cmd = f"nohup bash -c '{cmd}' > /dev/null 2>&1 &"
        else:
            remote_cmd = cmd

        full_cmd = self._sshpass_prefix() + [
            "ssh"
        ] + self._ssh_opts() + [
            host_dest, remote_cmd
        ]

        print(f"SSH into {host_dest} running ${cmd}")
        result = subprocess.run(full_cmd, capture_output=True, text=True)

        if check and result.returncode != 0 and not background:
            print(f"STDERR: {result.stderr.strip()}")

        return result

    # rsync a local file/dir to remote
    def rsync_to(self, host_dest, local_path, remote_path):
        ssh_cmd = f"sshpass -f {self.password_file} ssh {' '.join(self._ssh_opts())}"
        cmd = [
            "rsync", "-avz", "-e", ssh_cmd,
            local_path,
            f"{host_dest}:{remote_path}"
        ]
        print(f"RSYNC: from {local_path} to {host_dest}:{remote_path}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    # rsync a remote file/dir to local
    def rsync_from(self, host_dest, remote_path, local_path):
        ssh_cmd = f"sshpass -f {self.password_file} ssh {' '.join(self._ssh_opts())}"
        cmd = [
            "rsync", "-avz", "-e", ssh_cmd,
            f"{host_dest}:{remote_path}",
            local_path
        ]
        print(f"RSYNC: from {host_dest}:{remote_path} to {local_path}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    def test_connection(self):
        print("Testing SSH connection")
        for dest in [self.server_dest, self.client_dest]:
            result = self.ssh_run(dest, "echo ok", check=False)
            if result.returncode != 0:
                print(f"ERROR: Cannot connect to {dest}")
                print(f"{result.stderr.strip()}")
                sys.exit(1)
            print(f"{dest} : OK")
        print()

    def kill_server(self):
        self.ssh_run(self.server_dest,
                     "pkill -f 'python3.*server.py' || true", check=False)
        time.sleep(0.5)

def setup(runner):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

    for dest in [runner.server_dest, runner.client_dest]:
        runner.ssh_run(dest, f"mkdir -p {REMOTE_RESULTS_DIR}") # {REMOTE_PLOTS_DIR}")

    runner.rsync_to(runner.server_dest,
                    os.path.join(SCRIPT_DIR, "server.py"),
                    f"{REMOTE_DIR}/server.py")

    runner.rsync_to(runner.client_dest,
                    os.path.join(SCRIPT_DIR, "client.py"),
                    f"{REMOTE_DIR}/client.py")

def run_experiment(runner, proto, payload_bytes, clients, requests):
    csv_name = f"{proto}_p{payload_bytes}_c{clients}_r{requests}.csv"
    remote_csv = f"{REMOTE_RESULTS_DIR}/{csv_name}"

    print(f"{proto.upper()} | payload={payload_bytes}B | "
          f"clients={clients} | requests={requests}")

    runner.kill_server()

    server_cmd = (f"cd {REMOTE_DIR} && python3 server.py "
                  f"--proto {proto} "
                  f"--bind 0.0.0.0 "
                  f"--port {PORT} "
                  f"--payload-bytes {payload_bytes} "
                  f"--requests {requests} "
                  f"--clients {clients} "
                  f"--log {REMOTE_DIR}/results/server.log")

    runner.ssh_run(runner.server_dest, server_cmd, background=True)
    time.sleep(SERVER_STARTUP_DELAY)

    client_cmd = (f"cd {REMOTE_DIR} && python3 client.py "
                  f"--proto {proto} "
                  f"--host {runner.server_host} "
                  f"--port {PORT} "
                  f"--payload-bytes {payload_bytes} "
                  f"--requests {requests} "
                  f"--clients {clients} "
                  f"--log {remote_csv}")

    result = runner.ssh_run(runner.client_dest, client_cmd, check=False)

    runner.kill_server()

    if result.returncode != 0:
        print(f"WARNING: Client exited with code {result.returncode}")
        if result.stderr:
            print(f"{result.stderr.strip()}")
        return False
    
    if result.stdout:
        print(f"{result.stdout.strip()}")
    return True


def run_all_experiments(runner):
    print("RUNNING EXPERIMENTS")

    total = len(PROTOCOLS) * len(PAYLOAD_SIZES) * len(CLIENT_COUNTS)
    current = 0
    failed = []

    overall_start = time.monotonic()

    for proto in PROTOCOLS:
        for payload in PAYLOAD_SIZES:
            for clients in CLIENT_COUNTS:
                current += 1
                print(f"\n[{current}/{total}]", end=" ")

                try:
                    success = run_experiment(runner, proto, payload,
                                             clients, REQUESTS_PER_CLIENT)
                    if not success:
                        failed.append(f"{proto}_p{payload}_c{clients}")
                except Exception as e:
                    print(f"  [ERROR] {e}")
                    failed.append(f"{proto}_p{payload}_c{clients}")
                    runner.kill_server()

    runner.kill_server()

    elapsed = time.monotonic() - overall_start
    print(f"Completed {total} experiments in {elapsed:.1f}s")
    print(f"Successful: {total - len(failed)}/{total}")
    if failed:
        print(f"Failed: {failed}")

    return failed


def collect_results(runner):
    runner.rsync_from(runner.client_dest, f"{REMOTE_RESULTS_DIR}/", f"{RESULTS_DIR}/")

    csv_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith(".csv")]
    print(f"Downloaded {len(csv_files)} CSV files.\n")
    
    
def load_all_results():
    """Load all CSV files from results/ into a single list of dicts."""
    all_rows = []
    for filename in sorted(os.listdir(RESULTS_DIR)):
        if not filename.endswith(".csv"):
            continue
        filepath = os.path.join(RESULTS_DIR, filename)
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_rows.append({
                    "protocol": row["protocol"],
                    "client_count": int(row["client_count"]),
                    "payload_bytes": int(row["payload_bytes"]),
                    "request_num": int(row["request_num"]),
                    "client_id": int(row["client_id"]),
                    "connect_time_ms": float(row["connect_time_ms"]),
                    "rtt_ms": float(row["rtt_ms"]),
                })
    return all_rows


# group rows by (protocol, group_key) and compute median of value_key
# return: { protocol: { group_value: median } }
def aggregate(rows, group_key, value_key="rtt_ms"):
    buckets = defaultdict(list)
    for r in rows:
        if r["rtt_ms"] < 0:
            continue 
        buckets[(r["protocol"], r[group_key])].append(r[value_key])

    result = defaultdict(dict)
    for (proto, group_val), values in sorted(buckets.items()):
        result[proto][group_val] = statistics.median(values)

    return result


# group rows by (protocol, group_key).
# return: { protocol: { group_value: throughput_kbps } }
def compute_throughput(rows, group_key):
    buckets = defaultdict(lambda: {"total_bytes": 0, "total_time_ms": 0})
    for r in rows:
        if r["rtt_ms"] < 0:
            continue
        key = (r["protocol"], r[group_key])
        buckets[key]["total_bytes"] += r["payload_bytes"] * 2
        buckets[key]["total_time_ms"] += r["rtt_ms"]

    result = defaultdict(dict)
    for (proto, group_val), data in sorted(buckets.items()):
        if data["total_time_ms"] > 0:
            throughput = data["total_bytes"] * 1000.0 / data["total_time_ms"] / 1024.0
            result[proto][group_val] = throughput

    return result


# generate a single comparison plot (TCP vs UDP) and save to plots
def make_plot(data_tcp, data_udp, xlabel, ylabel, title, filename, logx=False):
    fig, ax = plt.subplots(figsize=(8, 5))

    if data_tcp:
        x_tcp = sorted(data_tcp.keys())
        y_tcp = [data_tcp[x] for x in x_tcp]
        ax.plot(x_tcp, y_tcp, "o-", label="TCP", color=TCP_PLOT_COLOR, linewidth=2)

    if data_udp:
        x_udp = sorted(data_udp.keys())
        y_udp = [data_udp[x] for x in x_udp]
        ax.plot(x_udp, y_udp, "s--", label="UDP", color=UDP_PLOT_COLOR, linewidth=2)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)

    if logx:
        ax.set_xscale("log")

    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


# create all plots from CSV results
def plot_results():
    os.makedirs(PLOTS_DIR, exist_ok=True)

    all_rows = load_all_results()
    if not all_rows:
        print("No results found in results/. Skipping plots.")
        return

    print(f"Loaded {len(all_rows)} data points.\n")

    # graph 1: latency vs payload size (averaged across client counts)
    latency_by_payload = aggregate(all_rows, "payload_bytes")
    make_plot(
        latency_by_payload.get("tcp", {}),
        latency_by_payload.get("udp", {}),
        xlabel="Payload Size (bytes)",
        ylabel="Median RTT (ms)",
        title="Latency vs Payload Size",
        filename="latency_vs_payload.png",
    )

    # graph 2: throughput vs payload size 
    throughput_by_payload = compute_throughput(all_rows, "payload_bytes")
    make_plot(
        throughput_by_payload.get("tcp", {}),
        throughput_by_payload.get("udp", {}),
        xlabel="Payload Size (bytes)",
        ylabel="Throughput (KB/s)",
        title="Throughput vs Payload Size",
        filename="throughput_vs_payload.png",
    )

    # graph 3: latency vs number of clients (log scale x-axis)  
    latency_by_clients = aggregate(all_rows, "client_count")
    make_plot(
        latency_by_clients.get("tcp", {}),
        latency_by_clients.get("udp", {}),
        xlabel="Number of Concurrent Clients",
        ylabel="Median RTT (ms)",
        title="Latency vs Number of Clients",
        filename="latency_vs_clients.png",
        logx=True,
    )

    # graph 4. throughput vs number of clients  
    throughput_by_clients = compute_throughput(all_rows, "client_count")
    make_plot(
        throughput_by_clients.get("tcp", {}),
        throughput_by_clients.get("udp", {}),
        xlabel="Number of Concurrent Clients",
        ylabel="Throughput (KB/s)",
        title="Throughput vs Number of Clients",
        filename="throughput_vs_clients.png",
        logx=True,
    )

    # graph 5. latency vs payload size, per client count  
    plot_latency_by_payload_per_client(all_rows)

    # graph 6. throughput vs payload size, per client count  
    plot_throughput_by_payload_per_client(all_rows)

    # graph 7. TCP connection overhead  
    plot_tcp_connect_time(all_rows)

    # graph 8. UDP packet loss  
    plot_udp_loss(all_rows)

    print("\nAll plots saved to plots/")


# Latency vs Payload for each client count, side by side
def plot_latency_by_payload_per_client(all_rows):
    client_counts = sorted(set(r["client_count"] for r in all_rows))
    fig, axes = plt.subplots(1, len(client_counts), figsize=(5 * len(client_counts), 5),
                              sharey=True)
    if len(client_counts) == 1:
        axes = [axes]

    for ax, cc in zip(axes, client_counts):
        subset = [r for r in all_rows if r["client_count"] == cc and r["rtt_ms"] >= 0]

        for proto, color, marker in [("tcp", TCP_PLOT_COLOR, "o"), ("udp", UDP_PLOT_COLOR, "s")]:
            buckets = defaultdict(list)
            for r in subset:
                if r["protocol"] == proto:
                    buckets[r["payload_bytes"]].append(r["rtt_ms"])

            if buckets:
                x = sorted(buckets.keys())
                y = [statistics.median(buckets[p]) for p in x]
                ax.plot(x, y, f"{marker}-", label=proto.upper(), color=color)

        ax.set_title(f"{cc} client{'s' if cc != 1 else ''}")
        ax.set_xlabel("Payload (bytes)")
        ax.grid(True, alpha=0.3)
        ax.legend()

    axes[0].set_ylabel("Median RTT (ms)")
    fig.suptitle("Latency vs Payload Size (by client count)", fontsize=14)
    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, "latency_vs_payload_per_client.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

# Throughput vs Payload for each client count, side by side
def plot_throughput_by_payload_per_client(all_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    client_counts = sorted(set(r["client_count"] for r in all_rows))
    fig, axes = plt.subplots(1, len(client_counts), figsize=(5 * len(client_counts), 5),
                              sharey=True)
    if len(client_counts) == 1:
        axes = [axes]

    for ax, cc in zip(axes, client_counts):
        subset = [r for r in all_rows if r["client_count"] == cc and r["rtt_ms"] >= 0]

        for proto, color, marker in [("tcp", TCP_PLOT_COLOR, "o"), ("udp", UDP_PLOT_COLOR, "s")]:
            buckets = defaultdict(lambda: {"bytes": 0, "ms": 0})
            for r in subset:
                if r["protocol"] == proto:
                    buckets[r["payload_bytes"]]["bytes"] += r["payload_bytes"] * 2
                    buckets[r["payload_bytes"]]["ms"] += r["rtt_ms"]

            if buckets:
                x = sorted(buckets.keys())
                y = [buckets[p]["bytes"] * 1000.0 / buckets[p]["ms"] / 1024.0
                     for p in x if buckets[p]["ms"] > 0]
                x = [p for p in x if buckets[p]["ms"] > 0]
                ax.plot(x, y, f"{marker}-", label=proto.upper(), color=color)

        ax.set_title(f"{cc} client{'s' if cc != 1 else ''}")
        ax.set_xlabel("Payload (bytes)")
        ax.grid(True, alpha=0.3)
        ax.legend()

    axes[0].set_ylabel("Throughput (KB/s)")
    fig.suptitle("Throughput vs Payload Size (by client count)", fontsize=14)
    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, "throughput_vs_payload_per_client.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

# Bar chart of TCP connection setup time by client count
def plot_tcp_connect_time(all_rows):
    tcp_rows = [r for r in all_rows if r["protocol"] == "tcp" and r["request_num"] == 0]
    if not tcp_rows:
        return

    buckets = defaultdict(list)
    for r in tcp_rows:
        buckets[r["client_count"]].append(r["connect_time_ms"])

    x = sorted(buckets.keys())
    y = [statistics.median(buckets[cc]) for cc in x]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([str(c) for c in x], y, color= TCP_PLOT_COLOR, alpha=0.8)
    ax.set_xlabel("Number of Concurrent Clients")
    ax.set_ylabel("Median Connect Time (ms)")
    ax.set_title("TCP Connection Setup Time vs Client Count")
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, "tcp_connect_time.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

# Bar chart of UDP packet loss rate by client count
def plot_udp_loss(all_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    udp_rows = [r for r in all_rows if r["protocol"] == "udp"]
    if not udp_rows:
        return

    buckets = defaultdict(lambda: {"total": 0, "lost": 0})
    for r in udp_rows:
        buckets[r["client_count"]]["total"] += 1
        if r["rtt_ms"] < 0:
            buckets[r["client_count"]]["lost"] += 1

    x = sorted(buckets.keys())
    y = [buckets[cc]["lost"] / buckets[cc]["total"] * 100.0 if buckets[cc]["total"] > 0 else 0
         for cc in x]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([str(c) for c in x], y, color=UDP_PLOT_COLOR, alpha=0.8)
    ax.set_xlabel("Number of Concurrent Clients")
    ax.set_ylabel("Packet Loss (%)")
    ax.set_title("UDP Packet Loss vs Client Count")
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    path = os.path.join(PLOTS_DIR, "udp_packet_loss.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

def parse_args():
    p = argparse.ArgumentParser(description="TCP/UDP benchmark automation")
    p.add_argument("--user", required=True, help="User netID")
    p.add_argument("--password-file", required=True, help="Path to file containing iLab password")
    p.add_argument("--server-host", required=True, help="Hostname of server iLab machine)")
    p.add_argument("--client-host", required=True, help="Hostname of client iLab machine")
    p.add_argument("--port", type=int, default=5001)
    return p.parse_args()


def main():
    args = parse_args()

    global PORT
    PORT = args.port

    runner = RunRemote(
        user=args.user,
        password_file=args.password_file,
        server_host=args.server_host,
        client_host=args.client_host,
    )

    runner.test_connection()
    setup(runner)
    failed = run_all_experiments(runner)
    collect_results(runner)
    plot_results()

    print("Completed running and plotting experiments")
    if not failed:
        print("All experiments succeeded")
    print(f"Results: {RESULTS_DIR}/")
    print(f"Plots:   {PLOTS_DIR}/")


if __name__ == "__main__":
    main()