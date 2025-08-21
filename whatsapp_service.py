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
        """Get group ID from database based on group type"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            # Use numeric type ID, not string names
            if group_type:
                if isinstance(group_type, str) and group_type in self.GROUP_TYPES:
                    type_id = self.GROUP_TYPES[group_type]
                elif isinstance(group_type, int):
                    type_id = group_type
                else:
                    logging.warning(f"Invalid group_type: {group_type}")
                    type_id = None
                
                if type_id:
                    query = """
                        SELECT group_id 
                        FROM whatsapp_groups 
                        WHERE is_active = 1 AND type = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    cursor.execute(query, (type_id,))
                    logging.info(f"Searching for group with type_id: {type_id}")
                else:
                    # Fallback to any active group
                    query = """
                        SELECT group_id 
                        FROM whatsapp_groups 
                        WHERE is_active = 1
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    cursor.execute(query)
            else:
                # Fallback to any active group
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
        """Send text message with enhanced error reporting"""
        try:
            url = f"{self.base_url}/sendMessage/{self.access_token}"
            
            payload = {
                "chatId": chat_id,
                "message": message
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            logging.info(f"Sending WhatsApp message to {chat_id}")
            logging.debug(f"API URL: {url}")
            logging.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            logging.info(f"API Response Status: {response.status_code}")
            logging.debug(f"API Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('idMessage'):
                    logging.info(f"✓ WhatsApp message sent successfully to {chat_id}, Message ID: {result.get('idMessage')}")
                    return True
                else:
                    logging.error(f"✗ Failed to send WhatsApp message. API returned: {result}")
                    return False
            else:
                logging.error(f"✗ WhatsApp API HTTP Error: {response.status_code}")
                logging.error(f"Response body: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logging.error("✗ WhatsApp API request timeout (30s)")
            return False
        except requests.exceptions.ConnectionError:
            logging.error("✗ WhatsApp API connection error - check internet connection")
            return False
        except Exception as e:
            logging.error(f"✗ Unexpected error sending WhatsApp message: {str(e)}")
            return False
    
    def send_group_message(self, group_id: str, message: str) -> bool:
        return self.send_text_message(group_id, message)
    
    def send_national_report(self, message: str) -> bool:
        """Send national report - fixed version"""
        try:
            logging.info("=== Sending national report to WhatsApp ===")
            
            # First, try to get national group from database (type = 3)
            group_id = self.get_group_id_from_db('national')  # This will use type = 3
            
            # If no national group found, try the active regional group (type = 2) 
            if not group_id:
                logging.warning("No national group (type=3) found in DB, trying regional group (type=2)")
                group_id = self.get_group_id_from_db(2)  # Direct numeric type
            
            # Last fallback to hardcoded group
            if not group_id:
                logging.warning("No groups found in DB, using hardcoded fallback group")
                group_id = ''
            
            if not group_id:
                logging.error("✗ No WhatsApp group available for national report")
                return False
            
            logging.info(f"Using group ID: {group_id}")
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ National WhatsApp report sent successfully")
            else:
                logging.error(f"✗ Failed to send national WhatsApp report")
            
            return success
            
        except Exception as e:
            logging.error(f"✗ Error in send_national_report: {str(e)}")
            return False

    def send_regional_report(self, message: str) -> bool:
        """Send regional report - fixed version"""
        try:
            logging.info("=== Sending regional report to WhatsApp ===")
            
            # Get regional group ID from database (type = 2)
            group_id = self.get_group_id_from_db('regional')  # This will use type = 2
            
            # If no regional group found, use the active one we see in your DB
            if not group_id:
                logging.warning("No regional group found via function, using direct query")
                group_id = ''  # This is the active type=2 group in your DB
            
            if not group_id:
                logging.error("✗ No WhatsApp group available for regional report")
                return False
            
            logging.info(f"Using group ID: {group_id}")
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ Regional WhatsApp report sent successfully")
            else:
                logging.error(f"✗ Failed to send regional WhatsApp report")
            
            return success
            
        except Exception as e:
            logging.error(f"✗ Error in send_regional_report: {str(e)}")
            return False

    def send_sales_office_report(self, message: str) -> bool:
        """Send sales office report - fixed version"""
        try:
            logging.info("=== Sending sales office report to WhatsApp ===")
            
            # Get sales office group ID from database
            group_id = self.get_group_id_from_db('sales_office')
            
            if not group_id:
                logging.warning("No sales office group found, trying fallback")
                group_id = self.get_group_id_from_db()  # Get any active group
            
            if not group_id:
                logging.error("✗ No WhatsApp group available for sales office report")
                return False
            
            logging.info(f"Using group ID: {group_id}")
            
            # Send the message
            success = self.send_group_message(group_id, message)
            
            if success:
                logging.info(f"✓ Sales office WhatsApp report sent successfully")
            else:
                logging.error(f"✗ Failed to send sales office WhatsApp report")
            
            return success
            
        except Exception as e:
            logging.error(f"✗ Error in send_sales_office_report: {str(e)}")
            return False

    def test_api_connection(self) -> bool:
        """Test WhatsApp API connection"""
        try:
            url = f"{self.base_url}/getSettings/{self.access_token}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                logging.info("✓ WhatsApp API connection successful")
                return True
            else:
                logging.error(f"✗ WhatsApp API connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"✗ Error testing API connection: {str(e)}")
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