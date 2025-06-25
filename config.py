# config.py - Configuration file for SAP Integration
import os
from datetime import datetime

# Date Configuration
CURRENT_DATE = '2025-06-21'
SATUAN = 'BOX'

# SAP API Configuration
# SAP_API_URL_ZPSDT003 = "http://saphana-whd.wismilak.com:8010/sap/opu/odata/sap/ZCDSV_ZPSDT003_CDS/ZCDSV_ZPSDT003?$format=json"
SAP_API_URL_ZPSDT003 = "https://gajahmada.wismilak.com/sap/opu/odata/sap/ZCDSV_ZPSDT003_CDS/ZCDSV_ZPSDT003?$format=json"
SAP_USERNAME_ZPSDT003 = "wim-rfc"
SAP_PASSWORD_ZPSDT003 = "Initial@999@"

# SAP_API_URL = f"https://saphana-whp.wismilak.com:53000/sap/opu/odata/sap/ZCDSV_SD_RMWEEKLY_SUM_CDS/ZCDSV_SD_RMWEEKLY_SUM(p_date=datetime'{CURRENT_DATE}T00:00:00',p_target_unit='{SATUAN}')/Set?sap-client=350&$format=json"
SAP_API_URL = f"https://gajahmada.wismilak.com/sap/opu/odata/sap/ZCDSV_SD_RMWEEKLY_SUM_CDS/ZCDSV_SD_RMWEEKLY_SUM(p_date=datetime'{CURRENT_DATE}T00:00:00',p_target_unit='{SATUAN}')/Set?$format=json"
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
TELEGRAM_CHAT_ID = "-4987830811"  # Replace with your actual chat ID

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'grafik_v3'
}