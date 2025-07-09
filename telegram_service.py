# telegram_service.py - Fixed Telegram notification service
import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramService:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Test bot connection on initialization
        self._test_bot_connection()
   
    def _test_bot_connection(self):
        """
        Test bot connection and get chat info
        """
        try:
            # Test bot token
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            
            if response.status_code != 200:
                logging.error(f"Invalid bot token: {response.text}")
                return False
                
            bot_info = response.json()
            if bot_info.get('ok'):
                logging.info(f"Bot connected: @{bot_info['result']['username']}")
            
            # Test chat access
            url = f"{self.base_url}/getChat"
            payload = {'chat_id': self.chat_id}
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                chat_info = response.json()
                if chat_info.get('ok'):
                    chat_title = chat_info['result'].get('title', chat_info['result'].get('first_name', 'Unknown'))
                    logging.info(f"Chat accessible: {chat_title}")
                    return True
            else:
                logging.error(f"Chat not accessible: {response.text}")
                logging.error("Possible solutions:")
                logging.error("1. Make sure the bot is added to the group/channel")
                logging.error("2. Send /start to the bot if it's a private chat")
                logging.error("3. Check if TELEGRAM_CHAT_ID is correct")
                return False
                
        except Exception as e:
            logging.error(f"Error testing bot connection: {e}")
            return False
   
    def send_message(self, message):
        """
        Mengirim pesan ke Telegram dengan error handling yang lebih baik
        """
        try:
            # Check if bot token and chat id are configured
            if not self.bot_token or not self.chat_id:
                logging.error("Telegram bot token or chat ID not configured")
                return False
            
            # Telegram has a 4096 character limit per message
            if len(message) > 4000:
                return self._send_long_message(message)
           
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
           
            response = requests.post(url, json=payload, timeout=30)
           
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logging.info(f"Telegram message sent successfully")
                    return True
                else:
                    logging.error(f"Telegram API error: {result}")
                    return False
            else:
                logging.error(f"Telegram HTTP error: {response.status_code} - {response.text}")
                
                # Specific error handling
                if response.status_code == 400:
                    error_data = response.json()
                    if "chat not found" in error_data.get('description', ''):
                        logging.error("SOLUTION: Add the bot to the chat or check TELEGRAM_CHAT_ID")
                    elif "bot was blocked" in error_data.get('description', ''):
                        logging.error("SOLUTION: Unblock the bot in Telegram")
                elif response.status_code == 401:
                    logging.error("SOLUTION: Check TELEGRAM_BOT_TOKEN is correct")
                
                return False
               
        except requests.exceptions.Timeout:
            logging.error("Telegram request timeout")
            return False
        except requests.exceptions.ConnectionError:
            logging.error("Telegram connection error - check internet connection")
            return False
        except Exception as e:
            logging.error(f"Error sending Telegram message: {e}")
            return False
   
    def _send_long_message(self, message):
        """
        Mengirim pesan panjang dengan membagi menjadi beberapa bagian
        """
        try:
            # Split message by sections
            sections = message.split('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
           
            current_message = ""
            for i, section in enumerate(sections):
                test_message = current_message + section
                if i < len(sections) - 1:  # Not the last section
                    test_message += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
                
                if len(test_message) < 4000:
                    current_message = test_message
                else:
                    # Send current message
                    if current_message.strip():
                        success = self.send_message(current_message.strip())
                        if not success:
                            return False
                   
                    # Start new message
                    current_message = section
                    if i < len(sections) - 1:
                        current_message += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
           
            # Send remaining message
            if current_message.strip():
                return self.send_message(current_message.strip())
           
            return True
           
        except Exception as e:
            logging.error(f"Error sending long Telegram message: {e}")
            return False
   
    def send_summary_message(self, region_name, summary_data, cycle, week):
        """
        Mengirim ringkasan singkat ke Telegram
        """
        summary_message = f"""
        """
       
        return self.send_message(summary_message)

    def get_chat_id_from_updates(self):
        """
        Helper method to get chat ID from recent messages
        """
        try:
            url = f"{self.base_url}/getUpdates"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        if 'message' in update:
                            chat_id = update['message']['chat']['id']
                            chat_type = update['message']['chat']['type']
                            chat_title = update['message']['chat'].get('title', 
                                       update['message']['chat'].get('first_name', 'Unknown'))
                            print(f"Chat ID: {chat_id}, Type: {chat_type}, Name: {chat_title}")
                    return True
            return False
        except Exception as e:
            logging.error(f"Error getting updates: {e}")
            return False
