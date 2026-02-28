#!/usr/bin/env python3

import subprocess
import argparse
import time
import os
import sys

PROTOCOLS = ["tcp", "udp"]
PAYLOAD_SIZES = [64, 512, 1024, 4096, 8192]
CLIENT_COUNTS = [1, 10, 100, 1000]
REQUESTS_PER_CLIENT = WORKITEMS_PER_CLIENT = 100

PORT = 5001
REMOTE_DIR = "~/cs417/p1/tcp_udp_benchmark"
REMOTE_RESULTS_DIR = os.path.join(REMOTE_DIR, "results")
REMOTE_PLOTS_DIR = os.path.join(REMOTE_DIR, "plots")
SERVER_STARTUP_DELAY = 2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")


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
        cmd = self._sshpass_prefix() + [
            "rsync", "-avz", "-e",
            f"ssh {' '.join(self._ssh_opts())}",
            local_path,
            f"{host_dest}:{remote_path}"
        ]
        print(f"RSYNC: from {host_dest} {local_path} to {remote_path}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    # rsync a remote file/dir to local
    def rsync_from(self, host_dest, remote_path, local_path):
        cmd = self._sshpass_prefix() + [
            "rsync", "-avz", "-e",
            f"ssh {' '.join(self._ssh_opts())}",
            f"{host_dest}:{remote_path}",
            local_path
        ]
        print(f"RSYNC: from {host_dest} {remote_path} to {local_path}")
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
        runner.ssh_run(dest, f"mkdir -p {REMOTE_RESULTS_DIR} {REMOTE_PLOTS_DIR}")

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
            print(f"  {result.stderr.strip()[:200]}")
        return False
    else:
        if result.stdout:
            print(f"  {result.stdout.strip()}")
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

    print("Completed running experiments")
    if not failed:
        print("All experiments succeeded")
    print(f"Next: run your plotting script against {RESULTS_DIR}/")


if __name__ == "__main__":
    main()