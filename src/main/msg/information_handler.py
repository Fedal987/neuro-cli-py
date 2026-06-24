"""
    Neuro-cli
    author@Fedal987
    Powered by HeronStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

import time
import requests
import socket
import platform
import psutil


os = platform.system()
cpu_core_count = psutil.cpu_count(logical=False)
cpu_usage = psutil.cpu_percent(interval=1)
memory = psutil.virtual_memory()
total_mem = memory.total
used_mem = memory.used
avaliable_mem = memory.available
disk = psutil.disk_usage('/')
total_disk = disk.total
used_disk = disk.used
avaliable_disk = disk.free
local_nw = psutil.net_if_addrs()

def local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def ip():
    local_ip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    local_ip.connect(("8.8.8.8", 80))
    global_ip = requests.get("https://myip.ipip.net", timeout=5).text
    return global_ip, local_ip.getsockname()[0]

if __name__ == "__main__":
    print(local_time())
    print(ip())

