import requests
import json
import logging
from typing import List, Dict, Optional
from config import GREEN_API_INSTANCE_ID, GREEN_API_ACCESS_TOKEN
from config import DB_CONFIG
import mysql.connector

class WhatsAppService:
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
    
    def get_group_id_from_db(self):
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            query = """
                SELECT group_id 
                FROM whatsapp_groups 
                WHERE is_active = 1
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                group_id = result[0]  # FIXED: ambil isi string dari tuple
                return group_id
            else:
                return None

        except Exception as e:
            logging.error(f"Error getting group ID from database: {str(e)}")
            return None
    
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
                    logging.info(f"WhatsApp message sent successfully to {chat_id}")
                    return True
                else:
                    logging.error(f"Failed to send WhatsApp message: {result}")
                    return False
            else:
                logging.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending WhatsApp message: {str(e)}")
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
    
    def send_regional_report(self, message: str) -> bool:
        """
        Send regional report to appropriate WhatsApp group (using database)
        
        Args:
            region_name: Name of the region
            message: Report message to send
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Get group ID from database
            group_id = self.get_group_id_from_db()
            
            # If no specific group found, try to get default group
            if not group_id:
                group_id = self.get_group_id_from_db()
            
            if not group_id:
                return False
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ WhatsApp report sent to group: {group_id}")
            else:
                logging.error(f"✗ Failed to send WhatsApp report to group")
            
            return success
            
        except Exception as e:
            logging.error(f"Error sending regional WhatsApp report: {str(e)}")
            return False