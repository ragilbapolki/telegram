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
        
        # Group type mapping based on your database schema
        self.GROUP_TYPES = {
            'sales_office': 1,
            'regional': 2, 
            'national': 3,
            'l': 4
        }
        
        # Verify credentials on initialization
        if not self.instance_id or not self.access_token:
            logging.error("WhatsApp Green API credentials not configured")
            raise ValueError("GREEN_API_INSTANCE_ID and GREEN_API_ACCESS_TOKEN must be set")
    
    def get_connection(self):
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Exception as e:
            logging.error(f"Error connecting to database: {e}")
            raise
    
    def get_group_id_from_db(self, group_type=None):
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            if group_type:
                type_id = self.GROUP_TYPES.get(group_type.lower())
                if type_id is None:
                    logging.error(f"Invalid group_type: {group_type}. Valid types: {list(self.GROUP_TYPES.keys())}")
                    return None
                
                query = """
                    SELECT group_id 
                    FROM whatsapp_groups 
                    WHERE is_active = 1 AND type = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(query, (type_id,))
            else:
                query = """
                    SELECT group_id 
                    FROM whatsapp_groups 
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(query)
            
            result = cursor.fetchone()
            
            if result:
                group_id = result[0]
                logging.info(f"Found group_id: {group_id} for type: {group_type}")
                return group_id
            else:
                logging.warning(f"No active WhatsApp group found for type: {group_type}")
                return None

        except Exception as e:
            logging.error(f"Error getting group ID from database: {str(e)}")
            return None
        finally:
            if 'connection' in locals():
                connection.close()
    
    def send_text_message(self, chat_id: str, message: str) -> bool:
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
        return self.send_text_message(group_id, message)
    
    def send_national_report(self, message: str) -> bool:
        try:
            logging.info("Sending national report to WhatsApp...")
            
            # Get national group ID from database (type = 3)
            group_id = self.get_group_id_from_db('national')
            
            # If no national group found, try to get default group
            if not group_id:
                logging.warning("No national WhatsApp group found, trying default group")
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

    def send_regional_report(self, message: str) -> bool:
        try:
            # Get regional group ID from database (type = 2)
            group_id = self.get_group_id_from_db('regional')
            
            # If no regional group found, try to get default group
            if not group_id:
                logging.warning("No regional WhatsApp group found, trying default group")
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

    def send_sales_office_report(self, message: str) -> bool:
        try:
            logging.info("Sending sales office report to WhatsApp...")
            
            # Get sales office group ID from database (type = 1)
            group_id = self.get_group_id_from_db('sales_office')
            
            # If no sales office group found, try to get default group
            if not group_id:
                logging.warning("No sales office WhatsApp group found, trying default group")
                group_id = self.get_group_id_from_db()
            
            if not group_id:
                logging.error("No WhatsApp group found in database for sales office report")
                return False
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ WhatsApp sales office report sent to group: {group_id}")
            else:
                logging.error(f"✗ Failed to send WhatsApp sales office report to group")
            
            return success
            
        except Exception as e:
            logging.error(f"Error sending sales office WhatsApp report: {str(e)}")
            return False

    def get_all_group_types(self) -> Dict[str, int]:
        return self.GROUP_TYPES.copy()

    def list_active_groups(self) -> List[Dict]:
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT id, group_id, group_name, type, is_active, created_at, updated_at
                FROM whatsapp_groups 
                WHERE is_active = 1
                ORDER BY type, created_at DESC
            """
            cursor.execute(query)
            
            results = cursor.fetchall()
            
            # Add readable type names
            type_names = {1: 'Sales Office', 2: 'Regional', 3: 'National', 4: 'L'}
            for result in results:
                result['type_name'] = type_names.get(result['type'], 'Unknown')
            
            return results
            
        except Exception as e:
            logging.error(f"Error listing active groups: {str(e)}")
            return []
        finally:
            if 'connection' in locals():
                connection.close()