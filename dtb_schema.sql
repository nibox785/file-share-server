-- Tạo database nếu chưa tồn tại
CREATE DATABASE IF NOT EXISTS file_share 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- Sử dụng database
USE file_share;

-- Drop tables nếu tồn tại (để reset)
-- DROP TABLE IF EXISTS files;
-- DROP TABLE IF EXISTS users;

-- ============================================================================
-- TABLE: users
-- Mô tả: Lưu trữ thông tin người dùng và xác thực
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: blogs
-- Mô tả: Lưu trữ bài viết blog
-- ============================================================================
CREATE TABLE IF NOT EXISTS blogs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    image_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    owner_id INT NOT NULL,
    
    -- Foreign Key
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_blogs_title (title),
    INDEX idx_blogs_owner_id (owner_id),
    INDEX idx_blogs_created_at (created_at DESC),
    
    -- Constraints
    CONSTRAINT chk_blogs_title_not_empty CHECK (CHAR_LENGTH(title) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE: files
-- Mô tả: Lưu trữ metadata của file đã upload
-- ============================================================================
CREATE TABLE IF NOT EXISTS files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    description VARCHAR(500),
    is_public BOOLEAN DEFAULT FALSE,
    download_count INT DEFAULT 0,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    owner_id INT NOT NULL,
    
    -- Foreign Key
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_files_filename (filename),
    INDEX idx_files_original_filename (original_filename),
    INDEX idx_files_owner_id (owner_id),
    INDEX idx_files_uploaded_at (uploaded_at DESC),
    INDEX idx_files_is_public (is_public),
    INDEX idx_files_file_type (file_type),
    
    -- Constraints
    CONSTRAINT chk_files_size_positive CHECK (file_size > 0),
    CONSTRAINT chk_files_download_count_positive CHECK (download_count >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SAMPLE DATA - Dữ liệu mẫu để demo
-- ============================================================================

-- Insert admin user (password: admin123)
-- Hash được tạo bằng bcrypt: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW
INSERT INTO users (username, email, password_hash, is_admin, is_active) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE, TRUE);

-- Insert sample users (password: user123)
INSERT INTO users (username, email, password_hash, is_active) VALUES
('user1', 'user1@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE),
('user2', 'user2@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE),
('testuser', 'test@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE);

-- Insert sample files
INSERT INTO files (filename, original_filename, file_path, file_size, file_type, description, is_public, owner_id) VALUES
('20240115_120000_report.pdf', 'report.pdf', 'static/uploads/20240115_120000_report.pdf', 1048576, '.pdf', 'Báo cáo tháng 1', TRUE, 1),
('20240115_120100_data.xlsx', 'data.xlsx', 'static/uploads/20240115_120100_data.xlsx', 524288, '.xlsx', 'Dữ liệu thống kê', FALSE, 2),
('20240115_120200_image.jpg', 'image.jpg', 'static/uploads/20240115_120200_image.jpg', 2097152, '.jpg', 'Hình ảnh minh họa', TRUE, 1),
('20240115_120300_document.docx', 'document.docx', 'static/uploads/20240115_120300_document.docx', 768432, '.docx', 'Tài liệu hướng dẫn', TRUE, 3);

-- ============================================================================
-- VIEWS - Các view hữu ích
-- ============================================================================

-- View: Danh sách file kèm thông tin owner
CREATE OR REPLACE VIEW vw_files_with_owner AS
SELECT 
    f.id,
    f.filename,
    f.original_filename,
    f.file_size,
    f.file_type,
    f.description,
    f.is_public,
    f.download_count,
    f.uploaded_at,
    u.username as owner_username,
    u.email as owner_email
FROM files f
JOIN users u ON f.owner_id = u.id;

-- View: Thống kê file theo user
CREATE OR REPLACE VIEW vw_user_file_stats AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(f.id) as total_files,
    COALESCE(SUM(f.file_size), 0) as total_size,
    COALESCE(SUM(f.download_count), 0) as total_downloads
FROM users u
LEFT JOIN files f ON u.id = f.owner_id
GROUP BY u.id, u.username;

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

DELIMITER //

-- Procedure: Tăng download count
CREATE PROCEDURE sp_increment_download_count(IN file_id INT)
BEGIN
    UPDATE files 
    SET download_count = download_count + 1 
    WHERE id = file_id;
END //

-- Procedure: Lấy thống kê user
CREATE PROCEDURE sp_get_user_statistics(IN user_id INT)
BEGIN
    SELECT 
        (SELECT COUNT(*) FROM files WHERE owner_id = user_id) as total_files,
        (SELECT COALESCE(SUM(file_size), 0) FROM files WHERE owner_id = user_id) as total_storage,
        (SELECT COALESCE(SUM(download_count), 0) FROM files WHERE owner_id = user_id) as total_downloads;
END //

-- Procedure: Xóa file cũ (quá 30 ngày và không public)
CREATE PROCEDURE sp_cleanup_old_private_files()
BEGIN
    DELETE FROM files 
    WHERE is_public = FALSE 
      AND uploaded_at < DATE_SUB(NOW(), INTERVAL 30 DAY)
      AND download_count = 0;
    
    SELECT ROW_COUNT() as deleted_files;
END //

-- Procedure: Tìm kiếm file
CREATE PROCEDURE sp_search_files(
    IN search_keyword VARCHAR(255),
    IN limit_count INT
)
BEGIN
    SELECT 
        f.*,
        u.username as owner_username
    FROM files f
    JOIN users u ON f.owner_id = u.id
    WHERE 
        (f.filename LIKE CONCAT('%', search_keyword, '%') OR
         f.original_filename LIKE CONCAT('%', search_keyword, '%') OR
         f.description LIKE CONCAT('%', search_keyword, '%'))
        AND f.is_public = TRUE
    ORDER BY f.uploaded_at DESC
    LIMIT limit_count;
END //

DELIMITER ;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Auto update blog updated_at (đã có trong table definition với ON UPDATE)

-- Trigger: Log file deletions (optional)
DELIMITER //

CREATE TRIGGER tr_log_file_deletion
BEFORE DELETE ON files
FOR EACH ROW
BEGIN
    -- Có thể tạo bảng file_deletion_log để lưu lại
    -- INSERT INTO file_deletion_log (file_id, filename, deleted_at)
    -- VALUES (OLD.id, OLD.filename, NOW());
    
    -- Hoặc chỉ để comment ở đây
    -- Log: File deleted - id: OLD.id, name: OLD.filename
END //

DELIMITER ;

-- ============================================================================
-- INDEXES OPTIMIZATION
-- ============================================================================

-- Composite indexes cho search thường dùng
CREATE INDEX idx_files_public_uploaded ON files(is_public, uploaded_at DESC);

-- Full-text search index (nếu cần tìm kiếm nhanh)
-- CREATE FULLTEXT INDEX idx_files_fulltext ON files(filename, original_filename, description);
-- CREATE FULLTEXT INDEX idx_blogs_fulltext ON blogs(title, content);

-- ============================================================================
-- SAMPLE QUERIES - Test các chức năng
-- ============================================================================

-- Test 1: Lấy tất cả users
SELECT * FROM users;

-- Test 2: Lấy files của user1
SELECT * FROM vw_files_with_owner WHERE owner_username = 'user1';

-- Test 3: Thống kê của từng user
SELECT * FROM vw_user_file_stats;

-- Test 4: Tìm kiếm file
CALL sp_search_files('report', 10);

-- Test 5: Tăng download count
CALL sp_increment_download_count(1);

-- Test 6: Thống kê user cụ thể
CALL sp_get_user_statistics(1);

-- Test 7: Lấy files mới nhất
SELECT * FROM vw_files_with_owner ORDER BY uploaded_at DESC LIMIT 5;

-- ============================================================================
-- DATABASE INFORMATION
-- ============================================================================

-- Xem kích thước database
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables
WHERE table_schema = 'file_share'
GROUP BY table_schema;

-- Xem kích thước từng bảng
SELECT 
    table_name AS 'Table',
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
    table_rows AS 'Rows'
FROM information_schema.tables
WHERE table_schema = 'file_share'
ORDER BY (data_length + index_length) DESC;

-- ============================================================================
-- BACKUP & RESTORE COMMANDS
-- ============================================================================

-- Backup database
-- mysqldump -u root -p01658919764 file_share > file_share_backup.sql

-- Restore database
-- mysql -u root -p01658919764 file_share < file_share_backup.sql

-- Backup only structure
-- mysqldump -u root -p01658919764 --no-data file_share > file_share_structure.sql

-- Backup only data
-- mysqldump -u root -p01658919764 --no-create-info file_share > file_share_data.sql

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. Password hash được tạo bằng bcrypt ($2b$12$...)
--    Test passwords: admin123, user123

-- 2. Database sử dụng utf8mb4 để hỗ trợ tiếng Việt và emoji

-- 3. Engine InnoDB hỗ trợ:
--    - Foreign keys
--    - Transactions
--    - Row-level locking
--    - Crash recovery

-- 4. Indexes đã được tối ưu cho:
--    - Search queries
--    - Sorting
--    - Foreign key lookups

-- 5. Stored procedures giúp:
--    - Tái sử dụng logic
--    - Bảo mật
--    - Performance

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- ============================================================================
-- TABLE: blogs
-- Mô tả: Lưu trữ bài viết blog
-- ============================================================================
CREATE TABLE IF NOT EXISTS blogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    image_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER NOT NULL,
    
    -- Foreign Key
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT blogs_title_not_empty CHECK (length(title) > 0)
);

CREATE INDEX idx_blogs_title ON blogs(title);
CREATE INDEX idx_blogs_owner_id ON blogs(owner_id);
CREATE INDEX idx_blogs_created_at ON blogs(created_at DESC);

-- ============================================================================
-- TABLE: files
-- Mô tả: Lưu trữ metadata của file đã upload
-- ============================================================================
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    description VARCHAR(500),
    is_public BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    owner_id INTEGER NOT NULL,
    
    -- Foreign Key
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT files_size_positive CHECK (file_size > 0),
    CONSTRAINT files_download_count_positive CHECK (download_count >= 0)
);

CREATE INDEX idx_files_filename ON files(filename);
CREATE INDEX idx_files_original_filename ON files(original_filename);
CREATE INDEX idx_files_owner_id ON files(owner_id);
CREATE INDEX idx_files_uploaded_at ON files(uploaded_at DESC);
CREATE INDEX idx_files_is_public ON files(is_public);

-- ============================================================================
-- SAMPLE DATA - Dữ liệu mẫu để demo
-- ============================================================================

-- Insert admin user (password: admin123)
INSERT INTO users (username, email, password_hash, is_admin, is_active) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE, TRUE);

-- Insert sample users (password: user123)
INSERT INTO users (username, email, password_hash, is_active) VALUES
('user1', 'user1@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE),
('user2', 'user2@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYdB0IqpgSW', TRUE);

-- Insert sample blogs
INSERT INTO blogs (title, content, owner_id) VALUES
('Hướng dẫn sử dụng hệ thống', 'Đây là hướng dẫn chi tiết về cách sử dụng File Share Network...', 1),
('Giới thiệu giao thức TCP', 'TCP (Transmission Control Protocol) là giao thức truyền dữ liệu tin cậy...', 1),
('Bảo mật với SSL/TLS', 'SSL/TLS giúp mã hóa dữ liệu trong quá trình truyền tải...', 2);

-- Insert sample files
INSERT INTO files (filename, original_filename, file_path, file_size, file_type, description, is_public, owner_id) VALUES
('20240115_120000_report.pdf', 'report.pdf', 'static/uploads/20240115_120000_report.pdf', 1048576, '.pdf', 'Báo cáo tháng 1', TRUE, 1),
('20240115_120100_data.xlsx', 'data.xlsx', 'static/uploads/20240115_120100_data.xlsx', 524288, '.xlsx', 'Dữ liệu thống kê', FALSE, 2),
('20240115_120200_image.jpg', 'image.jpg', 'static/uploads/20240115_120200_image.jpg', 2097152, '.jpg', 'Hình ảnh minh họa', TRUE, 1);

-- ============================================================================
-- VIEWS - Các view hữu ích
-- ============================================================================

-- View: Danh sách file kèm thông tin owner
CREATE VIEW IF NOT EXISTS vw_files_with_owner AS
SELECT 
    f.id,
    f.filename,
    f.original_filename,
    f.file_size,
    f.file_type,
    f.description,
    f.is_public,
    f.download_count,
    f.uploaded_at,
    u.username as owner_username,
    u.email as owner_email
FROM files f
JOIN users u ON f.owner_id = u.id;

-- View: Thống kê file theo user
CREATE VIEW IF NOT EXISTS vw_user_file_stats AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(f.id) as total_files,
    SUM(f.file_size) as total_size,
    SUM(f.download_count) as total_downloads
FROM users u
LEFT JOIN files f ON u.id = f.owner_id
GROUP BY u.id, u.username;

-- ============================================================================
-- TRIGGERS - Tự động cập nhật updated_at
-- ============================================================================

-- Trigger cho bảng blogs
CREATE TRIGGER IF NOT EXISTS update_blogs_timestamp 
AFTER UPDATE ON blogs
BEGIN
    UPDATE blogs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================================
-- FUNCTIONS/STORED PROCEDURES (Cho MySQL/PostgreSQL)
-- ============================================================================

-- Note: SQLite không hỗ trợ stored procedures
-- Dưới đây là syntax cho MySQL:

/*
DELIMITER //

CREATE PROCEDURE sp_increment_download_count(IN file_id INT)
BEGIN
    UPDATE files 
    SET download_count = download_count + 1 
    WHERE id = file_id;
END //

CREATE PROCEDURE sp_get_user_statistics(IN user_id INT)
BEGIN
    SELECT 
        (SELECT COUNT(*) FROM blogs WHERE owner_id = user_id) as total_blogs,
        (SELECT COUNT(*) FROM files WHERE owner_id = user_id) as total_files,
        (SELECT SUM(file_size) FROM files WHERE owner_id = user_id) as total_storage,
        (SELECT SUM(download_count) FROM files WHERE owner_id = user_id) as total_downloads;
END //

DELIMITER ;
*/

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. Password hash được tạo bằng bcrypt ($2b$12$...)
--    Để test: password cho tất cả user mẫu là "user123" hoặc "admin123"

-- 2. File paths trong production nên lưu relative path hoặc sử dụng storage service

-- 3. Indexes đã được tạo cho các trường thường xuyên query:
--    - username, email (users)
--    - title, created_at (blogs)
--    - filename, uploaded_at, is_public (files)

-- 4. Foreign keys có CASCADE DELETE để tự động xóa dữ liệu liên quan
--    khi xóa user

-- 5. Constraints đảm bảo data integrity:
--    - file_size > 0
--    - download_count >= 0
--    - title not empty

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================