import grpc
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.grpc_files import file_search_pb2
    from app.grpc_files import file_search_pb2_grpc
except ImportError:
    print("gRPC files not found. Make sure you've generated them.")
    sys.exit(1)

class FileSearchClient:
    """Client để test gRPC FileSearch service"""
    
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = file_search_pb2_grpc.FileSearchServiceStub(self.channel)
    
    def search_files(self, keyword, limit=10):
        """Tìm kiếm file"""
        try:
            request = file_search_pb2.SearchRequest(
                keyword=keyword,
                limit=limit
            )
            
            response = self.stub.SearchFiles(request)
            
            print(f"\nSearch results for '{keyword}' (found {response.total_count}):")
            for i, file in enumerate(response.files, 1):
                print(f"\n{i}. {file.original_filename}")
                print(f"   ID: {file.id}")
                print(f"   Size: {file.file_size / 1024:.2f} KB")
                print(f"   Type: {file.file_type}")
                print(f"   Owner: {file.owner_username}")
                print(f"   Downloads: {file.download_count}")
                if file.description:
                    print(f"   Description: {file.description}")
            
            return response.files
            
        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()} - {e.details()}")
            return []
    
    def get_file_info(self, file_id):
        """Lấy thông tin chi tiết file"""
        try:
            request = file_search_pb2.FileRequest(file_id=file_id)
            
            file = self.stub.GetFileInfo(request)
            
            print(f"\nFile Information:")
            print(f"   ID: {file.id}")
            print(f"   Filename: {file.original_filename}")
            print(f"   Size: {file.file_size / 1024:.2f} KB")
            print(f"   Type: {file.file_type}")
            print(f"   Owner: {file.owner_username}")
            print(f"   Uploaded: {file.uploaded_at}")
            print(f"   Downloads: {file.download_count}")
            print(f"   Public: {'Yes' if file.is_public else 'No'}")
            if file.description:
                print(f"   Description: {file.description}")
            
            return file
            
        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()} - {e.details()}")
            return None
    
    def list_all_files(self):
        """Liệt kê tất cả file"""
        try:
            request = file_search_pb2.Empty()
            
            response = self.stub.ListAllFiles(request)
            
            print(f"\nAll Files ({response.total_count} total):")
            for i, file in enumerate(response.files, 1):
                print(f"{i}. [{file.id}] {file.original_filename} - {file.file_size / 1024:.2f} KB ({file.owner_username})")
            
            return response.files
            
        except grpc.RpcError as e:
            print(f"gRPC Error: {e.code()} - {e.details()}")
            return []
    
    def close(self):
        """Đóng kết nối"""
        self.channel.close()

# Test script
if __name__ == "__main__":
    print("=== gRPC File Search Client ===\n")
    
    host = input("Server host [localhost]: ").strip() or 'localhost'
    port = input("Server port [50051]: ").strip()
    port = int(port) if port else 50051
    
    client = FileSearchClient(host=host, port=port)
    
    try:
        while True:
            print("\n--- Menu ---")
            print("1. Search files")
            print("2. Get file info by ID")
            print("3. List all files")
            print("4. Exit")
            
            choice = input("\nChoose: ")
            
            if choice == '1':
                keyword = input("Enter search keyword: ")
                limit = input("Limit results [10]: ").strip()
                limit = int(limit) if limit else 10
                client.search_files(keyword, limit)
            
            elif choice == '2':
                file_id = input("Enter file ID: ")
                if file_id.isdigit():
                    client.get_file_info(int(file_id))
                else:
                    print("Invalid file ID")
            
            elif choice == '3':
                client.list_all_files()
            
            elif choice == '4':
                break
            
            else:
                print("Invalid choice")
    
    finally:
        client.close()
        print("\nGoodbye!")