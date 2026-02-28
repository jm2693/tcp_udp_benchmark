The experiments are run by using two iLab Machines (client and server machines):
  1. rsync client.py and server.py to both ilab machines
  2. SSH into machine A to run server 
  3. SSH into machine B to run client 
  4. Kill server after each experiment
  5. rsync results/ and plots/ back to local

Usage:
  python3 run_experiments.py --user NETID --password-file pass.txt \
      --server-host ilab1.cs.rutgers.edu \
      --client-host ilab2.cs.rutgers.edu

  pass.txt should contain your ilab password (one line, no newline).
  we can achieve this simply by doing the following:
    $echo "ilab_password" > pass.txt

Prerequisites:
  - sshpass installed locally 
  - Python 3 available on both ilab machines