import requests
import json
import logging
import base64
import os
import mimetypes
from typing import List, Dict, Optional
from config import GREEN_API_INSTANCE_ID, GREEN_API_ACCESS_TOKEN
from config import DB_CONFIG
import mysql.connector

class EnhancedWhatsAppService:
    def __init__(self):
        self.instance_id = GREEN_API_INSTANCE_ID
        self.access_token = GREEN_API_ACCESS_TOKEN
        self.base_url = f"https://api.green-api.com/waInstance{self.instance_id}"
        self.db_config = DB_CONFIG
        
        # Verify credentials on initialization
        if not self.instance_id or not self.access_token:
            logging.error("WhatsApp Green API credentials not configured")
            raise ValueError("GREEN_API_INSTANCE_ID and GREEN_API_ACCESS_TOKEN must be set")
    
    def get_connection(self):
        """Create and return database connection"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Exception as e:
            logging.error(f"Error connecting to database: {e}")
            raise
    
    def get_group_id_from_db(self, group_type=None):
        """Get group ID from database with optional group type filter"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            if group_type:
                query = """
                    SELECT group_id 
                    FROM whatsapp_groups 
                    WHERE is_active = 1 AND group_type = %s
                """
                cursor.execute(query, (group_type,))
            else:
                query = """
                    SELECT group_id 
                    FROM whatsapp_groups 
                    WHERE is_active = 1
                """
                cursor.execute(query)
            
            result = cursor.fetchone()
            
            if result:
                group_id = result[0]
                return group_id
            else:
                return None

        except Exception as e:
            logging.error(f"Error getting group ID from database: {str(e)}")
            return None
        finally:
            if 'connection' in locals():
                connection.close()
    
    def send_text_message(self, chat_id: str, message: str) -> bool:
        """
        Send text message to WhatsApp chat (individual or group)
        
        Args:
            chat_id: Chat ID (phone number with country code for individual, or group ID for groups)
            message: Message text to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            url = f"{self.base_url}/sendMessage/{self.access_token}"
            
            payload = {
                "chatId": chat_id,
                "message": message
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('idMessage'):
                    logging.info(f"WhatsApp text message sent successfully to {chat_id}")
                    return True
                else:
                    logging.error(f"Failed to send WhatsApp text message: {result}")
                    return False
            else:
                logging.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending WhatsApp text message: {str(e)}")
            return False
    
    def send_file_message(self, chat_id: str, file_path: str, caption: str = "") -> bool:
        """
        Send file (PDF, image, document) to WhatsApp chat
        
        Args:
            chat_id: Chat ID (phone number with country code for individual, or group ID for groups)
            file_path: Path to the file to send
            caption: Optional caption for the file
            
        Returns:
            bool: True if file sent successfully, False otherwise
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logging.error(f"File not found: {file_path}")
                return False
            
            # Get file info
            file_name = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # Read and encode file
            with open(file_path, 'rb') as file:
                file_data = file.read()
                file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Determine the appropriate endpoint based on file type
            if mime_type and mime_type.startswith('image/'):
                url = f"{self.base_url}/sendFileByUpload/{self.access_token}"
                payload = {
                    "chatId": chat_id,
                    "file": file_base64,
                    "fileName": file_name,
                    "caption": caption
                }
            else:
                # For documents (PDF, etc.)
                url = f"{self.base_url}/sendFileByUpload/{self.access_token}"
                payload = {
                    "chatId": chat_id,
                    "file": file_base64,
                    "fileName": file_name,
                    "caption": caption
                }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('idMessage'):
                    logging.info(f"WhatsApp file sent successfully to {chat_id}: {file_name}")
                    return True
                else:
                    logging.error(f"Failed to send WhatsApp file: {result}")
                    return False
            else:
                logging.error(f"WhatsApp file API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending WhatsApp file: {str(e)}")
            return False
    
    def send_group_message(self, group_id: str, message: str) -> bool:
        """
        Send message to WhatsApp group
        
        Args:
            group_id: WhatsApp group ID (format: phone_number-group_timestamp@g.us)
            message: Message text to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        return self.send_text_message(group_id, message)
    
    def send_group_file(self, group_id: str, file_path: str, caption: str = "") -> bool:
        """
        Send file to WhatsApp group
        
        Args:
            group_id: WhatsApp group ID (format: phone_number-group_timestamp@g.us)
            file_path: Path to the file to send
            caption: Optional caption for the file
            
        Returns:
            bool: True if file sent successfully, False otherwise
        """
        return self.send_file_message(group_id, file_path, caption)
    
    def send_regional_report(self, message: str) -> bool:
        """
        Send regional report to appropriate WhatsApp group (using database)
        
        Args:
            message: Report message to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Get group ID from database
            group_id = self.get_group_id_from_db('regional')
            
            # If no regional group found, try to get default group
            if not group_id:
                group_id = self.get_group_id_from_db()
            
            if not group_id:
                logging.error("No WhatsApp group found in database")
                return False
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ WhatsApp regional report sent to group: {group_id}")
            else:
                logging.error(f"✗ Failed to send WhatsApp regional report to group")
            
            return success
            
        except Exception as e:
            logging.error(f"Error sending regional WhatsApp report: {str(e)}")
            return False

    def send_regional_report_with_pdf(self, message: str, pdf_files: List[str]) -> bool:
        """
        Send regional report with text message first, then PDF files
        
        Args:
            message: Report text message to send first
            pdf_files: List of PDF file paths to send after text message
            
        Returns:
            bool: True if both text and PDF sent successfully, False otherwise
        """
        try:
            # Get group ID from database
            group_id = self.get_group_id_from_db('regional')
            
            # If no regional group found, try to get default group
            if not group_id:
                group_id = self.get_group_id_from_db()
            
            if not group_id:
                logging.error("No WhatsApp group found in database for regional report")
                return False
            
            # Step 1: Send text message first
            logging.info("📱 Sending regional report text message...")
            text_success = self.send_group_message(group_id, message)
            
            if not text_success:
                logging.error("Failed to send text message, skipping PDF")
                return False
            
            # Step 2: Send PDF files (with small delay between each)
            pdf_success_count = 0
            
            if pdf_files:
                logging.info(f"📄 Sending {len(pdf_files)} PDF file(s)...")
                
                for i, pdf_path in enumerate(pdf_files):
                    if os.path.exists(pdf_path):
                        # Create caption with file info
                        file_name = os.path.basename(pdf_path)
                        caption = f"📊 Regional Report PDF - {file_name}"
                        
                        # Send PDF file
                        pdf_success = self.send_group_file(group_id, pdf_path, caption)
                        
                        if pdf_success:
                            pdf_success_count += 1
                            logging.info(f"✓ PDF {i+1}/{len(pdf_files)} sent: {file_name}")
                        else:
                            logging.error(f"✗ Failed to send PDF {i+1}/{len(pdf_files)}: {file_name}")
                        
                        # Small delay between files to avoid rate limits
                        import time
                        time.sleep(2)
                    else:
                        logging.error(f"PDF file not found: {pdf_path}")
            
            # Summary
            total_success = text_success and (pdf_success_count == len(pdf_files) if pdf_files else True)
            
            if total_success:
                logging.info(f"✓ Regional report sent successfully: text + {pdf_success_count} PDF(s)")
            else:
                logging.warning(f"⚠ Partial success: text={text_success}, PDFs={pdf_success_count}/{len(pdf_files) if pdf_files else 0}")
            
            return total_success
            
        except Exception as e:
            logging.error(f"Error sending regional WhatsApp report with PDF: {str(e)}")
            return False

    def send_national_report(self, message: str) -> bool:
        """
        Send national report to appropriate WhatsApp group (using database)
        
        Args:
            message: National report message to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            logging.info("Sending national report to WhatsApp...")
            
            # Get national group ID from database
            group_id = self.get_group_id_from_db('national')
            
            # If no national group found, try to get default group
            if not group_id:
                group_id = self.get_group_id_from_db()
            
            if not group_id:
                logging.error("No WhatsApp group found in database for national report")
                return False
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ WhatsApp national report sent to group: {group_id}")
            else:
                logging.error(f"✗ Failed to send WhatsApp national report to group")
            
            return success
            
        except Exception as e:
            logging.error(f"Error sending national WhatsApp report: {str(e)}")
            return False

    def send_national_report_with_pdf(self, message: str, pdf_files: List[str]) -> bool:
        """
        Send national report with text message first, then PDF files
        
        Args:
            message: Report text message to send first
            pdf_files: List of PDF file paths to send after text message
            
        Returns:
            bool: True if both text and PDF sent successfully, False otherwise
        """
        try:
            logging.info("Sending national report with PDF to WhatsApp...")
            
            # Get national group ID from database
            group_id = self.get_group_id_from_db('national')
            
            # If no national group found, try to get default group
            if not group_id:
                group_id = self.get_group_id_from_db()
            
            if not group_id:
                logging.error("No WhatsApp group found in database for national report")
                return False
            
            # Step 1: Send text message first
            logging.info("📱 Sending national report text message...")
            text_success = self.send_group_message(group_id, message)
            
            if not text_success:
                logging.error("Failed to send text message, skipping PDF")
                return False
            
            # Step 2: Send PDF files (with small delay between each)
            pdf_success_count = 0
            
            if pdf_files:
                logging.info(f"📄 Sending {len(pdf_files)} PDF file(s)...")
                
                for i, pdf_path in enumerate(pdf_files):
                    if os.path.exists(pdf_path):
                        # Create caption with file info
                        file_name = os.path.basename(pdf_path)
                        caption = f"📊 National Report PDF - {file_name}"
                        
                        # Send PDF file
                        pdf_success = self.send_group_file(group_id, pdf_path, caption)
                        
                        if pdf_success:
                            pdf_success_count += 1
                            logging.info(f"✓ PDF {i+1}/{len(pdf_files)} sent: {file_name}")
                        else:
                            logging.error(f"✗ Failed to send PDF {i+1}/{len(pdf_files)}: {file_name}")
                        
                        # Small delay between files to avoid rate limits
                        import time
                        time.sleep(2)
                    else:
                        logging.error(f"PDF file not found: {pdf_path}")
            
            # Summary
            total_success = text_success and (pdf_success_count == len(pdf_files) if pdf_files else True)
            
            if total_success:
                logging.info(f"✓ National report sent successfully: text + {pdf_success_count} PDF(s)")
            else:
                logging.warning(f"⚠ Partial success: text={text_success}, PDFs={pdf_success_count}/{len(pdf_files) if pdf_files else 0}")
            
            return total_success
            
        except Exception as e:
            logging.error(f"Error sending national WhatsApp report with PDF: {str(e)}")
            return False