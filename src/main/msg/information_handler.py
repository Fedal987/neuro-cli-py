import time
import requests
import socket

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

