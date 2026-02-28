# TCP and UDP Benchmarking

## Important files / dirs

client.py - Source code to run TCP and UDP echo client  
server.py - Source code to run TCP and UDP echo server  
run_experiments.py - Single script to SSH into two separate iLab machines,  
                     run client and server code on each respectively,  
                     format results into CSV files,  
                     copy result CSV files back onto local machine,  
                     plot experiment graphs based on result files. 

                     Note: The entire process can take multiple minutes (10-20 in my tests)

/plots - Plotted results are stored here as .png files   
/results - Raw results are stored here as .csv files  

## Prerequisites 

- Python3 installed on local machine and iLab machines  
- matplotlib installed on local machine for plotting  
- sshpass installed on local machine for remote ssh  
- rsync installed on local and iLab machines  

## Setup

Create a password file containing your iLab password (single line, no trailing newline):  
`echo -n "your_ilab_password" > password.txt`

The .gitignore file already has "/password.txt"  
If you choose to store the password in a differently-named file, make sure to add it to the .gitignore  

## Usage

After the prerequisites and setup have been satisfied, usage can be done in a single command.  
Note: This script / experiment is meant to be used from start to finish,  
      meaning, running the script will both perform the experiments AND plot the results  

```bash
python3 run_experiments.py \
    --user YOUR_NETID \
    --password-file password.txt \
    --server-host SERVER_MACHINE.cs.rutgers.edu \
    --client-host CLIENT_MACHINE.cs.rutgers.edu
```

This will:
- Upload `server.py` and `client.py` to the respective iLab machines
- Run all 40 experiments on iLab machines(2 protocols × 5 payload sizes × 4 client counts)  
- Download CSV results to `results/` using rsync
- Generate plots in `plots/` 


We can also run `client.py` and `server.py` independently
Ex:
On the server machine:
```bash
python3 server.py --proto tcp --bind 0.0.0.0 --port 5001 \
    --payload-bytes 1024 --requests 100 --clients 10 --log server.log
```

On the client machine:
```bash
python3 client.py --proto tcp --host SERVER_HOSTNAME --port 5001 \
    --payload-bytes 1024 --requests 100 --clients 10 --log results/output.csv
```

| Flag | Description | Default |
|------|-------------|---------|
| `--proto` | Protocol: `tcp` or `udp` | required |
| `--bind` | Server bind address | `0.0.0.0` |
| `--host` | Server hostname (client only) | required |
| `--port` | Port number | `5001` |
| `--payload-bytes` | Bytes per request | `64` |
| `--requests` | Requests per client | `100` |
| `--clients` | Number of concurrent clients | `1` |
| `--log` | Output log/CSV file path | required |

## Outputs

### CSV files

```bash
protocol, client_id, client_count, payload_bytes, request_num, connect_time_ms, rtt_ms, timestamp
```

- `connect_time_ms`: TCP 3-way handshake time (0 for UDP)
- `rtt_ms`: Round-trip time for one send/receive. Negative values indicate errors:
  - `-1.0`: UDP timeout (packet lost)
  - `-2.0`: UDP send error (e.g., MTU exceeded)

### Plots generated

1. **Latency vs Payload Size** — median RTT across all client counts
2. **Throughput vs Payload Size** — aggregate KB/s
3. **Latency vs Number of Clients** — how concurrency affects RTT
4. **Throughput vs Number of Clients** — how concurrency affects throughput
5. **Latency vs Payload (per client count)** — side-by-side breakdown
6. **Throughput vs Payload (per client count)** — side-by-side breakdown
7. **TCP Connection Setup Time** — handshake overhead by client count
8. **UDP Packet Loss** — loss rate by client count


## Example:

`brew install sshpass`
`brew install python-matplotlib`
`echo -n "my_password" > password.txt`
```bash
      python3 run_experiments.py --user NETID --password-file password.txt \
      --server-host batch.cs.rutgers.edu \
      --client-host cheese.cs.rutgers.edu
```

The experiments are run by using two iLab Machines (client and server machines):
  1. rsync client.py and server.py to both ilab machines
  2. SSH into machine A to run server 
  3. SSH into machine B to run client 
  4. Kill server after each experiment
  5. rsync results/ and plots/ back to local