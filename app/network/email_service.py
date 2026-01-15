import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class EmailService:
    """Service gửi email (SMTP)"""
    
    @staticmethod
    async def send_email(to_email: str, subject: str, body_html: str):
        """
        Gửi email
        
        Args:
            to_email: Email người nhận
            subject: Tiêu đề
            body_html: Nội dung HTML
        """
        try:
            # Tạo message
            message = MIMEMultipart("alternative")
            message["From"] = settings.SMTP_FROM
            message["To"] = to_email
            message["Subject"] = subject
            
            # Attach HTML body
            html_part = MIMEText(body_html, "html")
            message.attach(html_part)
            
            # Gửi email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                start_tls=True,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
            )
            
            return True
            
        except Exception as e:
            print(f"Email sending error: {e}")
            return False
    
    @staticmethod
    async def send_download_link(
        to_email: str,
        filename: str,
        download_url: str,
        sender_name: str = "File Share Network"
    ):
        """
        Gửi link download file qua email
        
        Args:
            to_email: Email người nhận
            filename: Tên file
            download_url: URL download
            sender_name: Tên người gửi
        """
        subject = f"📎 {sender_name} shared a file with you"
        
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                    border-radius: 10px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
                .file-info {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-left: 4px solid #4CAF50;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>File Shared</h1>
                </div>
                <div class="content">
                    <p>Hello!</p>
                    <p><strong>{sender_name}</strong> has shared a file with you:</p>
                    
                    <div class="file-info">
                        <strong>Filename:</strong> {filename}
                    </div>
                    
                    <p>Click the button below to download:</p>
                    
                    <a href="{download_url}" class="button">📥 Download File</a>
                    
                    <p style="margin-top: 30px; color: #666; font-size: 14px;">
                        Or copy this link: <br>
                        <code>{download_url}</code>
                    </p>
                    
                    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
                    
                    <p style="color: #999; font-size: 12px;">
                        This is an automated email from File Share Network. 
                        Please do not reply to this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await EmailService.send_email(to_email, subject, body_html)