"""
Database Manager for handling all database operations
"""
import mysql.connector
import logging
from config import DB_CONFIG, DEFAULT_RECIPIENTS

class DatabaseManager:
    def __init__(self):
        self.db_config = DB_CONFIG
    
    def get_connection(self):
        """Create and return database connection"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Exception as e:
            logging.error(f"Error connecting to database: {e}")
            raise
    
    def get_recipients_from_db(self):
        """
        Get list of email recipients from database
        """
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            query = "SELECT email FROM email_recipients WHERE is_active = 1"
            cursor.execute(query)
            result = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            recipients = [email[0] for email in result]
            return recipients if recipients else DEFAULT_RECIPIENTS
            
        except Exception as e:
            logging.error(f"Error getting recipients from database: {e}")
            print(f"Error getting recipients from database: {e}")
            return DEFAULT_RECIPIENTS
    
    def get_regional_notes(self, regional_id, cycle, week, year):
        """
        Get notes for specific regional from database
        Fixed: Made sure all parameters are properly handled
        """
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Convert parameters to proper types
            regional_id = str(regional_id) if regional_id else ''
            cycle = str(cycle) if cycle else ''
            week = str(week) if week else ''
            year = str(year) if year else ''
            
            query = """
            SELECT note_text, created_at
            FROM note_customers 
            WHERE regional_id = %s AND cycle = %s AND week = %s AND year = %s
            AND note_text IS NOT NULL AND note_text != ''
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            # Debug logging
            logging.info(f"Searching notes for: regional_id={regional_id}, cycle={cycle}, week={week}, year={year}")
            print(f"Searching notes for: regional_id={regional_id}, cycle={cycle}, week={week}, year={year}")
            
            cursor.execute(query, (regional_id, cycle, week, year))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if result and result[0]:
                note_text = result[0].strip()
                created_at = result[1]
                print(f"Found note: '{note_text}' created at {created_at}")
                return note_text
            else:
                print(f"No notes found for regional_id={regional_id}, cycle={cycle}, week={week}, year={year}")
                return None
                
        except Exception as e:
            logging.error(f"Error getting notes from database: {e}")
            print(f"Error getting notes from database: {e}")
            return None
    
    def get_all_notes_for_debug(self):
        """
        Debug method to see all notes in database
        """
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            query = """
            SELECT regional_id, cycle, week, year, note_text, created_at
            FROM note_customers 
            WHERE note_text IS NOT NULL AND note_text != ''
            ORDER BY created_at DESC
            LIMIT 10
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            print("\n=== DEBUG: Recent notes in database ===")
            for row in results:
                print(f"Regional: {row[0]}, Cycle: {row[1]}, Week: {row[2]}, Year: {row[3]}")
                print(f"Note: {row[4]}")
                print(f"Created: {row[5]}")
                print("-" * 50)
            
            return results
            
        except Exception as e:
            logging.error(f"Error getting debug notes: {e}")
            print(f"Error getting debug notes: {e}")
            return []