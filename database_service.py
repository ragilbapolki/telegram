# database_service.py - Database operations
import mysql.connector
import logging
from config import DB_CONFIG

class DatabaseService:
    def __init__(self):
        self.db_config = DB_CONFIG
    
    def get_recipients_from_db(self):
        """
        Mengambil daftar penerima email dari database
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            cursor.execute("SELECT email FROM email_recipients WHERE is_active = 1")
            result = cursor.fetchall()
            cursor.close()
            connection.close()
            return [email[0] for email in result]
        except Exception as e:
            logging.error(f"Error getting recipients from database: {e}")
            return ["ragil.bapolki@wismilak.com"]
    
    def get_regional_notes(self, regional_id, cycle, week, year):
        """
        Mengambil notes untuk regional tertentu dari database dengan query yang lebih fleksibel
        """
        try:
            connection = mysql.connector.connect(**self.db_config)
            cursor = connection.cursor()
            
            # Query dengan prioritas - coba exact match dulu
            queries_to_try = [
                # 1. Exact match
                ("SELECT note FROM note_customers WHERE regional_id = %s AND cycle = %s AND week = %s AND year = %s ORDER BY created_at DESC LIMIT 1", 
                (regional_id, cycle, week, year)),
                
                # 2. Tanpa week (mungkin week tidak sesuai)
                ("SELECT note FROM note_customers WHERE regional_id = %s AND cycle = %s AND year = %s ORDER BY created_at DESC LIMIT 1", 
                (regional_id, cycle, year)),
                
                # 3. Hanya regional_id dan year (paling fleksibel)
                ("SELECT note FROM note_customers WHERE regional_id = %s AND year = %s ORDER BY created_at DESC LIMIT 1", 
                (regional_id, year)),
                
                # 4. Regional_id sebagai string (jika ada masalah tipe data)
                ("SELECT note FROM note_customers WHERE regional_id = %s AND cycle = %s AND year = %s ORDER BY created_at DESC LIMIT 1", 
                (str(regional_id), str(cycle), str(year))),
            ]
            
            result = None
            for i, (query, params) in enumerate(queries_to_try):
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                if result:
                    break
            
            cursor.close()
            connection.close()
            
            if result:
                note_text = result[0] if result[0] else None
                return note_text
            else:
                return None
                
        except Exception as e:
            logging.error(f"Error getting notes from database: {e}")
            return None