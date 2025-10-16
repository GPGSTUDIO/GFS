import sys
import subprocess
if sys.argv[2]=="1":
    if sys.argv[1].startswith("\\\\"):
        process = subprocess.Popen(['gp.exe',sys.argv[1]],stdin=subprocess.PIPE).stdin.write(b"GF\x00\x00\x00\x00\x00\x02X\x00\x00".ljust(512, b'\x00'))
    else:
        with open(sys.argv[1],"wb") as f:
            f.write(b"GF\x00\x00\x00\x00\x00\x02X\x00\x00")
elif sys.argv[2]=="2":
    if sys.argv[1].startswith("\\\\"):
        process = subprocess.Popen(['gp.exe',sys.argv[1]],stdin=subprocess.PIPE).stdin.write(b"GF\x00\x01\x00\x00\x00\x02X\x00\x00".ljust(512, b'\x00'))
    else:
        with open(sys.argv[1],"wb") as f:
            f.write(b"GF\x00\x01\x00\x00\x00\x02X\x00\x00")