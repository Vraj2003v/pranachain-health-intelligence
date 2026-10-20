"""Start PranaPulse so phones and other devices on the same network can open it.

Usage:  python run_network.py [port]
"""
import socket
import sys

import uvicorn

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # no packet is sent; this only picks the active network adapter
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


print(f"\n  On this computer:      http://localhost:{port}")
print(f"  On phone / other device (same Wi-Fi): http://{lan_ip()}:{port}\n")
uvicorn.run("api.main:app", host="0.0.0.0", port=port)
