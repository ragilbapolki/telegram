# convert.py
from datetime import datetime
import logging

def _parse_sap_date(sap_date_str):
    """
    Mengkonversi format tanggal SAP "/Date(1704067200000)/" ke datetime
    """
    try:
        if sap_date_str.startswith('/Date(') and sap_date_str.endswith(')/'):
            timestamp = int(sap_date_str[6:-2])
            return datetime.fromtimestamp(timestamp / 1000)
        return None
    except Exception as e:
        logging.error(f"Error parsing SAP date {sap_date_str}: {str(e)}")
        return None
