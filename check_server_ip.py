"""
Script kiểm tra IP của máy Server
Chạy trên máy SERVER để lấy IP
"""

import socket
import platform

def get_local_ip():
    """Lấy IP LAN của máy"""
    try:
        # Tạo socket và kết nối đến external server (không thực sự connect)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "Unable to get IP"

def get_all_ips():
    """Lấy tất cả IPs của máy"""
    hostname = socket.gethostname()
    try:
        ips = socket.gethostbyname_ex(hostname)[2]
        return [ip for ip in ips if not ip.startswith("127.")]
    except:
        return []

def main():
    print("\n" + "="*70)
    print(" "*20 + "SERVER IP INFORMATION")
    print("="*70 + "\n")
    
    # OS Info
    print(f"Operating System: {platform.system()} {platform.release()}")
    print(f"Hostname: {socket.gethostname()}")
    print()
    
    # Primary IP
    primary_ip = get_local_ip()
    print(f"Primary LAN IP: {primary_ip}")
    print(f"   Use this IP for clients to connect!")
    print()
    
    # All IPs
    all_ips = get_all_ips()
    if all_ips:
        print(f"All Network Interfaces:")
        for i, ip in enumerate(all_ips, 1):
            print(f"   {i}. {ip}")
        print()
    
    # Connection URLs
    print("="*70)
    print("CLIENT CONNECTION INFORMATION")
    print("="*70)
    print()
    print("Share these URLs with your clients:")
    print()
    print(f"HTTP API (Web Browser):")
    print(f"   http://{primary_ip}:8000/docs")
    print()
    print(f"TCP File Transfer:")
    print(f"   Host: {primary_ip}")
    print(f"   Port: 9000 (no SSL) or 9001 (SSL)")
    print()
    print(f"Multicast Radio:")
    print(f"   Group: 224.1.1.1")
    print(f"   Port: 5007")
    print()
    print(f"gRPC Search:")
    print(f"   Host: {primary_ip}")
    print(f"   Port: 50051")
    print()
    
    # Update .env instruction
    print("="*70)
    print("UPDATE CONFIGURATION")
    print("="*70)
    print()
    print("Update your .env file:")
    print(f'   SERVER_IP="{primary_ip}"')
    print()
    
    # Client setup instruction
    print("="*70)
    print("👥 CLIENT SETUP INSTRUCTIONS")
    print("="*70)
    print()
    print("On CLIENT machines, update connection settings:")
    print()
    print("1. TCP Client:")
    print(f"   client = TCPFileClient(host='{primary_ip}', port=9000)")
    print()
    print("2. gRPC Client:")
    print(f"   client = FileSearchClient(host='{primary_ip}', port=50051)")
    print()
    print("3. Web Browser:")
    print(f"   Open: http://{primary_ip}:8000")
    print()
    
    # Firewall reminder
    print("="*70)
    print("FIREWALL REMINDER")
    print("="*70)
    print()
    print("Make sure these ports are open on SERVER:")
    print("   - TCP: 8000, 9000, 9001, 50051")
    print("   - UDP: 5007")
    print()
    print("Windows:")
    print("   Run PowerShell as Admin, then:")
    print("   New-NetFirewallRule -DisplayName 'File Share' -Direction Inbound -Protocol TCP -LocalPort 8000,9000,9001,50051 -Action Allow")
    print("   New-NetFirewallRule -DisplayName 'File Share Multicast' -Direction Inbound -Protocol UDP -LocalPort 5007 -Action Allow")
    print()
    print("Linux:")
    print("   sudo ufw allow 8000,9000,9001,50051/tcp")
    print("   sudo ufw allow 5007/udp")
    print()
    
    print("="*70)
    print("Server IP check completed!")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")