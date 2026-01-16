import grpc
from concurrent import futures
import sys
import os

# Add app directory to path để import được
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.file import File
from app.models.user import User

# Import generated gRPC code (cần chạy protoc trước)
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. app/grpc_files/file_search.proto
try:
    from app.grpc_files import file_search_pb2
    from app.grpc_files import file_search_pb2_grpc
except ImportError:
    print("⚠️  gRPC files not generated yet. Run:")
    print("   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. app/grpc_files/file_search.proto")
    file_search_pb2 = None
    file_search_pb2_grpc = None

class FileSearchServicer:
    """Implementation của gRPC FileSearchService"""
    
    def SearchFiles(self, request, context):
        """Tìm kiếm file theo keyword"""
        db = SessionLocal()
        try:
            keyword = request.keyword
            limit = request.limit if request.limit > 0 else 10
            
            # Query từ database
            query = db.query(File, User).join(User, File.owner_id == User.id)
            
            if keyword:
                query = query.filter(
                    (File.filename.contains(keyword)) |
                    (File.original_filename.contains(keyword)) |
                    (File.description.contains(keyword))
                )
            
            results = query.limit(limit).all()
            
            # Convert sang protobuf message
            files = []
            for file, user in results:
                file_info = file_search_pb2.FileInfo(
                    id=file.id,
                    filename=file.filename,
                    original_filename=file.original_filename,
                    file_size=file.file_size,
                    file_type=file.file_type,
                    description=file.description or "",
                    is_public=file.is_public,
                    download_count=file.download_count,
                    uploaded_at=file.uploaded_at.isoformat(),
                    owner_id=file.owner_id,
                    owner_username=user.username
                )
                files.append(file_info)
            
            return file_search_pb2.SearchResponse(
                files=files,
                total_count=len(files)
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return file_search_pb2.SearchResponse()
        finally:
            db.close()
    
    def GetFileInfo(self, request, context):
        """Lấy thông tin chi tiết 1 file"""
        db = SessionLocal()
        try:
            file = db.query(File, User).join(User, File.owner_id == User.id)\
                     .filter(File.id == request.file_id).first()
            
            if not file:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("File not found")
                return file_search_pb2.FileInfo()
            
            file_obj, user = file
            
            return file_search_pb2.FileInfo(
                id=file_obj.id,
                filename=file_obj.filename,
                original_filename=file_obj.original_filename,
                file_size=file_obj.file_size,
                file_type=file_obj.file_type,
                description=file_obj.description or "",
                is_public=file_obj.is_public,
                download_count=file_obj.download_count,
                uploaded_at=file_obj.uploaded_at.isoformat(),
                owner_id=file_obj.owner_id,
                owner_username=user.username
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return file_search_pb2.FileInfo()
        finally:
            db.close()
    
    def ListAllFiles(self, request, context):
        """Lấy danh sách tất cả file"""
        db = SessionLocal()
        try:
            results = db.query(File, User).join(User, File.owner_id == User.id).all()
            
            files = []
            for file, user in results:
                file_info = file_search_pb2.FileInfo(
                    id=file.id,
                    filename=file.filename,
                    original_filename=file.original_filename,
                    file_size=file.file_size,
                    file_type=file.file_type,
                    description=file.description or "",
                    is_public=file.is_public,
                    download_count=file.download_count,
                    uploaded_at=file.uploaded_at.isoformat(),
                    owner_id=file.owner_id,
                    owner_username=user.username
                )
                files.append(file_info)
            
            return file_search_pb2.FileList(
                files=files,
                total_count=len(files)
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return file_search_pb2.FileList()
        finally:
            db.close()

def start_grpc_server():
    """Khởi động gRPC server"""
    if not file_search_pb2 or not file_search_pb2_grpc:
        print("Cannot start gRPC server: protobuf files not generated")
        return
    
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        file_search_pb2_grpc.add_FileSearchServiceServicer_to_server(
            FileSearchServicer(), server
        )
        
        port = settings.GRPC_PORT
        server.add_insecure_port(f'[::]:{port}')
        
        server.start()
        print(f"gRPC Server started on port {port}")
        
        server.wait_for_termination()
        
    except Exception as e:
        print(f"❌ gRPC Server error: {e}")