# telegram_chat_id_finder.py - Find your Telegram Chat ID

import requests
import json
from config import TELEGRAM_BOT_TOKEN

def find_chat_id():
    """
    Find all available chat IDs for your bot
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in config!")
        return
    
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    print("🔍 Finding Telegram Chat IDs...")
    print("=" * 50)
    
    # Step 1: Test bot token
    print("1. Testing bot token...")
    url = f"{base_url}/getMe"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ Invalid bot token: {response.text}")
        return
    
    bot_info = response.json()
    if bot_info.get('ok'):
        bot_username = bot_info['result']['username']
        bot_name = bot_info['result']['first_name']
        print(f"✅ Bot connected: {bot_name} (@{bot_username})")
    else:
        print(f"❌ Bot error: {bot_info}")
        return
    
    # Step 2: Get recent updates
    print("\n2. Getting recent messages...")
    url = f"{base_url}/getUpdates"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"❌ Error getting updates: {response.text}")
        return
    
    data = response.json()
    if not data.get('ok'):
        print(f"❌ API error: {data}")
        return
    
    updates = data.get('result', [])
    if not updates:
        print("⚠️  No recent messages found!")
        print("\n📝 TO GET CHAT ID:")
        print("1. Send a message to your bot")
        print("2. Or add your bot to a group")
        print("3. Then run this script again")
        return
    
    print(f"✅ Found {len(updates)} recent messages")
    print("\n3. Available Chat IDs:")
    print("-" * 40)
    
    seen_chats = set()
    for update in updates:
        if 'message' in update:
            chat = update['message']['chat']
            chat_id = chat['id']
            chat_type = chat['type']
            
            if chat_id not in seen_chats:
                seen_chats.add(chat_id)
                
                # Get chat name
                if chat_type == 'private':
                    chat_name = f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
                    chat_name = chat_name or chat.get('username', 'Unknown')
                elif chat_type in ['group', 'supergroup']:
                    chat_name = chat.get('title', 'Unknown Group')
                elif chat_type == 'channel':
                    chat_name = chat.get('title', 'Unknown Channel')
                else:
                    chat_name = 'Unknown'
                
                print(f"Chat ID: {chat_id}")
                print(f"Type: {chat_type}")
                print(f"Name: {chat_name}")
                print(f"Config format: TELEGRAM_CHAT_ID = {chat_id}")
                print("-" * 40)
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Copy one of the Chat IDs above")
    print("2. Update your config.py with:")
    print("   TELEGRAM_CHAT_ID = [your_chosen_chat_id]")
    print("3. Run your report application again")

def test_specific_chat_id(chat_id):
    """
    Test if a specific chat ID works
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return False
    
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    print(f"🧪 Testing Chat ID: {chat_id}")
    
    # Try to get chat info
    url = f"{base_url}/getChat"
    payload = {'chat_id': chat_id}
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        chat_info = response.json()
        if chat_info.get('ok'):
            result = chat_info['result']
            chat_type = result.get('type', 'unknown')
            
            if chat_type == 'private':
                chat_name = f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
            else:
                chat_name = result.get('title', 'Unknown')
            
            print(f"✅ Chat ID {chat_id} is valid!")
            print(f"   Type: {chat_type}")
            print(f"   Name: {chat_name}")
            return True
        else:
            print(f"❌ Chat error: {chat_info}")
            return False
    else:
        print(f"❌ HTTP error: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def send_test_message(chat_id):
    """
    Send a test message to verify the chat ID works
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found!")
        return False
    
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    print(f"📤 Sending test message to Chat ID: {chat_id}")
    
    url = f"{base_url}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': '🧪 Test message from Report Application\n\nIf you see this, the Chat ID is working correctly! ✅',
        'parse_mode': 'Markdown'
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('ok'):
            print("✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Message error: {result}")
            return False
    else:
        print(f"❌ HTTP error: {response.status_code}")
        print(f"   Response: {response.text}")
        return False