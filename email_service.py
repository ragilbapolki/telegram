# email_service.py - Email notification service
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM

class EmailService:
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_pass = SMTP_PASS
        self.email_from = EMAIL_FROM
    
    def send_email(self, recipient_emails, subject, text_body):
        """
        Mengirim email dengan body plain text
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = ', '.join(recipient_emails) if isinstance(recipient_emails, list) else recipient_emails
            msg['Subject'] = subject
            
            text_part = MIMEText(text_body, 'plain')
            msg.attach(text_part)
            
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            server.login(self.smtp_user, self.smtp_pass)
            text = msg.as_string()
            server.sendmail(self.email_from, recipient_emails, text)
            server.quit()
            
            return True
            
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return False