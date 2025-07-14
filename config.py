# config.py - Configuration file for SAP Integration
import os
from datetime import datetime

# Date Configuration
# CURRENT_DATE = '2025-06-21'
CURRENT_DATE = datetime.now().strftime('%Y-%m-%d')
SATUAN = 'BOX'

# SAP API Configuration
# SAP_API_URL_ZPSDT003 = "http://saphana-whd.wismilak.com:8010/sap/opu/odata/sap/ZCDSV_ZPSDT003_CDS/ZCDSV_ZPSDT003?$format=json"
SAP_API_URL_ZPSDT003 = "https://gajahmada.wismilak.com/sap/opu/odata/sap/ZCDSV_ZPSDT003_CDS/ZCDSV_ZPSDT003?$format=json"
SAP_USERNAME_ZPSDT003 = "wim-rfc"
SAP_PASSWORD_ZPSDT003 = "Initial@999@"

# SAP_API_URL = f"https://saphana-whp.wismilak.com:53000/sap/opu/odata/sap/ZCDSV_SD_RMWEEKLY_SUM_CDS/ZCDSV_SD_RMWEEKLY_SUM(p_date=datetime'{CURRENT_DATE}T00:00:00',p_target_unit='{SATUAN}')/Set?sap-client=350&$format=json"
SAP_API_URL = f"https://gajahmada.wismilak.com/sap/opu/odata/sap/ZCDSV_SD_RMWEEKLY_SUM_AE_CDS/ZCDSV_SD_RMWEEKLY_SUM_AE(p_date=datetime'{CURRENT_DATE}T00:00:00',p_target_unit='{SATUAN}')/Set?$format=json"
SAP_USERNAME = "wim-rfc"
SAP_PASSWORD = "Initial@999@"

# Email Configuration
SMTP_HOST = "mail.wismilak.com"
SMTP_PORT = 465
SMTP_USER = "ragil.bapolki@wismilak.com"
SMTP_PASS = "Sapyes@2025"
EMAIL_FROM = "noreply@wismilak.com"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8180858435:AAH3du51mPkqmk_IvJX-uK-KYvZ4uzPnrNQ"
# TELEGRAM_CHAT_ID = "-4987830811" #group
TELEGRAM_CHAT_ID = "1081601567" #pribadi

# WhatsApp Green API configuration
GREEN_API_INSTANCE_ID = "7105275644"  # Your Green API instance ID
GREEN_API_ACCESS_TOKEN = "e78fc9fbe0924191a976341e80a8edc377b46def788845fca8"  # Your Green API access token

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'grafik_v3'
}

# Report configuration
REPORT_CONFIG = {
    'max_retries': 3,
    'retry_delay': 5,  # seconds
    'timeout': 30,     # seconds
    'enable_telegram': True,
    'enable_email': True,
    'enable_whatsapp': True
}
