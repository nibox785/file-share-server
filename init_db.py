import sys
import os
from app.db.session import engine, SessionLocal
from app.db import base
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import Settings

settings = Settings()

def check_database_connection():
    """Kiểm tra kết nối Database (SQLite hoặc MySQL)"""
    db_url = settings.DATABASE_URL
    
    if db_url.startswith("sqlite"):
        print(f"Using SQLite database")
        print(f"Database file: {db_url.replace('sqlite:///', '')}")
        return True
    elif "mysql" in db_url:
        try:
            import pymysql
            connection = pymysql.connect(
                host='localhost',
                user='root',
                password='01658919764',
                charset='utf8mb4'
            )
            print("MySQL connection successful!")
            
            with connection.cursor() as cursor:
                cursor.execute("SHOW DATABASES LIKE 'file_share'")
                result = cursor.fetchone()
                
                if not result:
                    print("Database 'file_share' not found. Creating...")
                    cursor.execute("CREATE DATABASE file_share CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    print("Database 'file_share' created!")
                else:
                    print("Database 'file_share' exists!")
            
            connection.close()
            return True
            
        except Exception as e:
            print(f"MySQL connection failed: {e}")
            print("\nPlease check:")
            print("1. MySQL server is running")
            print("2. Username: root")
            print("3. Password: correct")
            print("4. Port: 3306 (default)")
            return False
    else:
        print(f"Using database: {db_url}")
        return True

def init_database():
    """Tạo tất cả tables"""
    print("\n Creating database tables...")
    try:
        base.Base.metadata.create_all(bind=engine)
        print(" Database tables created successfully!")
        
        # Hiển thị danh sách tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f" Error creating tables: {e}")
        sys.exit(1)

def create_admin_user():
    """Tạo user admin mẫu"""
    db = SessionLocal()
    try:
        # Kiểm tra admin đã tồn tại chưa
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("\n  Admin user already exists")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            return
        
        # Tạo admin user
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            is_admin=True,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\n Admin user created successfully!")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Email: admin@example.com")
        
    except Exception as e:
        print(f"\n Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

def create_sample_users():
    """Tạo vài user mẫu để test"""
    db = SessionLocal()
    try:
        sample_users = [
            {"username": "user1", "email": "user1@example.com", "password": "user123"},
            {"username": "user2", "email": "user2@example.com", "password": "user123"},
            {"username": "testuser", "email": "test@example.com", "password": "test123"},
        ]
        
        created_count = 0
        for user_data in sample_users:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if existing:
                continue
            
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=get_password_hash(user_data["password"]),
                is_active=True
            )
            db.add(user)
            created_count += 1
        
        db.commit()
        
        if created_count > 0:
            print(f"\n Created {created_count} sample users")
            print("   Users: user1, user2, testuser")
            print("   Password: user123 (user1, user2), test123 (testuser)")
        else:
            print("\n  Sample users already exist")
        
    except Exception as e:
        print(f"\n Error creating sample users: {e}")
        db.rollback()
    finally:
        db.close()

def show_database_info():
    """Hiển thị thông tin database"""
    print("\n" + "="*60)
    print(" Database Information")
    print("="*60)
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite"):
        print(f"Database Type: SQLite")
        print(f"Database File: {db_url.replace('sqlite:///', '')}")
    else:
        print(f"Database URL: {db_url}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" Initializing File Share Network Database")
    print("="*60)
    
    # Bước 1: Kiểm tra database connection
    if not check_database_connection():
        print("\n Cannot connect to database. Please check your configuration.")
        sys.exit(1)
    
    # Bước 2: Tạo tables
    init_database()
    
    # Bước 3: Tạo admin user
    create_admin_user()
    
    # Bước 4: Tạo sample users
    create_sample_users()
    
    # Bước 5: Hiển thị thông tin
    show_database_info()
    
    print("\n" + "="*60)
    print("Database initialization completed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Start server: python -m app.main")
    print("3. Test login: username=admin, password=admin123")
    print("4. API Docs: http://localhost:8000/docs")
    print("\n")