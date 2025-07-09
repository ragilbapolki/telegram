import requests
import json
from config import WHATSAPP_CONFIG

class WhatsAppGroupHelper:
    """
    Helper untuk mendapatkan informasi WhatsApp Group
    """
    
    def __init__(self):
        self.instance_id = WHATSAPP_CONFIG.get('INSTANCE_ID')
        self.access_token = WHATSAPP_CONFIG.get('ACCESS_TOKEN')
        self.base_url = f"https://api.green-api.com/waInstance{self.instance_id}"
    
    def get_all_chats(self):
        """
        Mendapatkan semua chat termasuk group chat
        """
        try:
            url = f"{self.base_url}/getChats/{self.access_token}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                chats = response.json()
                return chats
            else:
                print(f"Error getting chats: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def get_group_chats_only(self):
        """
        Mendapatkan hanya group chat saja
        """
        all_chats = self.get_all_chats()
        if not all_chats:
            return []
        
        group_chats = []
        for chat in all_chats:
            if chat.get('type') == 'group' and '@g.us' in chat.get('id', ''):
                group_chats.append({
                    'group_id': chat.get('id'),
                    'name': chat.get('name', 'Unknown Group'),
                    'type': chat.get('type'),
                    'last_message': chat.get('lastMessage', {})
                })
        
        return group_chats
    
    def get_group_info(self, group_id):
        """
        Mendapatkan info detail dari group tertentu
        """
        try:
            url = f"{self.base_url}/getGroupData/{self.access_token}"
            payload = {"groupId": group_id}
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting group info: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return None
    
    def print_group_list(self):
        """
        Print daftar semua group dengan format yang rapi
        """
        print("🔍 Mencari WhatsApp Groups...")
        print("=" * 60)
        
        group_chats = self.get_group_chats_only()
        
        if not group_chats:
            print("❌ Tidak ada group chat ditemukan atau error koneksi")
            return