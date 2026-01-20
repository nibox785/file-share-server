from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import threading
import os

from app.core.config import settings
from app.db.session import engine, ensure_sqlite_indexes
from app.db import base

# Import routers
from app.api import auth, file_manager, streaming, admin

# Import network modules
from app.network.tcp_server import start_tcp_server
from app.network.multicast_server import start_multicast_server
from app.network.grpc_server import start_grpc_server
from app.network.voice_server import start_voice_server

# Tạo database tables
base.Base.metadata.create_all(bind=engine)
ensure_sqlite_indexes()

# Khởi tạo FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="File Share Network - TCP, SSL, Multicast, gRPC, Email",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(file_manager.router, prefix=f"{settings.API_PREFIX}/files", tags=["File Management"])
app.include_router(streaming.router, prefix=f"{settings.API_PREFIX}/streaming", tags=["Streaming"])
app.include_router(admin.router, prefix=f"{settings.API_PREFIX}/admin", tags=["Admin"])

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to File Share Network!",
        "version": "1.0.0",
        "services": {
            "http_api": f"http://localhost:8000{settings.API_PREFIX}",
            "tcp_server": f"{settings.TCP_HOST}:{settings.TCP_PORT}",
            "tcp_ssl_server": f"{settings.TCP_HOST}:{settings.TCP_SSL_PORT}",
            "multicast_radio": f"{settings.MULTICAST_GROUP}:{settings.MULTICAST_PORT}",
            "grpc_server": f"localhost:{settings.GRPC_PORT}",
            "voice_call": f"{settings.TCP_HOST}:{settings.VOICE_PORT}"
        },
        "docs": "http://localhost:8000/docs"
    }

@app.on_event("startup")
def startup_event():
    """
    Khởi động các service mạng khi FastAPI start
    QUAN TRỌNG: Đây là phần tích hợp Lập trình mạng!
    """
    import socket
    
    # Lấy IP thật của máy server
    hostname = socket.gethostname()
    try:
        server_ip = socket.gethostbyname(hostname)
    except:
        server_ip = "localhost"
    
    print("\n" + "="*70)
    print("Starting File Share Network Services...")
    print("="*70 + "\n")
    
    print(f"Server Information:")
    print(f"   Hostname: {hostname}")
    print(f"   Server IP: {server_ip}")
    print(f"   Note: Clients should connect to this IP")
    print()
    
    # 1. TCP Server (no SSL) - Thread 1
    tcp_thread = threading.Thread(
        target=start_tcp_server,
        args=(False,),  # use_ssl=False
        daemon=True
    )
    tcp_thread.start()
    print("TCP Server thread started")
    
    # 2. TCP Server with SSL - Thread 2
    # Chỉ start nếu có SSL certificates
    if os.path.exists(settings.SSL_CERT_FILE) and os.path.exists(settings.SSL_KEY_FILE):
        tcp_ssl_thread = threading.Thread(
            target=start_tcp_server,
            args=(True,),  # use_ssl=True
            daemon=True
        )
        tcp_ssl_thread.start()
        print("TCP SSL Server thread started")
    else:
        print("⚠️  SSL certificates not found. TCP SSL Server disabled.")
        print(f"   Generate with: bash generate_ssl.sh")
    
    # 3. Multicast Server - Thread 3
    multicast_thread = threading.Thread(
        target=start_multicast_server,
        args=("static/audio/sample.mp3",),
        daemon=True
    )
    multicast_thread.start()
    print("Multicast Radio Server thread started")
    
    # 4. gRPC Server - Thread 4
    grpc_thread = threading.Thread(
        target=start_grpc_server,
        daemon=True
    )
    grpc_thread.start()
    print("gRPC Server thread started")

    # 5. Voice Call Server - Thread 5
    voice_thread = threading.Thread(
        target=start_voice_server,
        daemon=True
    )
    voice_thread.start()
    print("Voice Call Server thread started")
    
    print("\n" + "="*70)
    print("All services started successfully!")
    print("="*70 + "\n")
    
    print("Access Points:")
    print(f"   - Local: http://localhost:8000/docs")
    print(f"   - LAN:   http://{server_ip}:8000/docs")
    print()
    print("Network Services (for clients to connect):")
    print(f"   - HTTP API:         {server_ip}:8000")
    print(f"   - TCP File Transfer: {server_ip}:9000")
    print(f"   - TCP SSL Transfer:  {server_ip}:9001")
    print(f"   - Multicast Radio:   {settings.MULTICAST_GROUP}:{settings.MULTICAST_PORT}")
    print(f"   - gRPC Search:       {server_ip}:{settings.GRPC_PORT}")
    print(f"   - Voice Call:        {server_ip}:{settings.VOICE_PORT}")
    print()
    print("Share this IP with clients: " + "="*20)
    print(f"   SERVER_IP = {server_ip}")
    print("=" * 70 + "\n")

@app.on_event("shutdown")
def shutdown_event():
    """Clean up khi tắt server"""
    print("\nShutting down File Share Network...")
    # Các thread daemon sẽ tự động stop khi main process stop

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )