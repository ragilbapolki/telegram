# sap_service.py - SAP API integration service
import requests
import logging
from datetime import datetime, timedelta
from config import (
    SAP_API_URL_ZPSDT003, SAP_USERNAME_ZPSDT003, SAP_PASSWORD_ZPSDT003,
    SAP_API_URL, SAP_USERNAME, SAP_PASSWORD, CURRENT_DATE, SATUAN
)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SAPService:
    def __init__(self):
        self.current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')
    
    def parse_sap_date(self, sap_date_str):
        """
        Mengkonversi format tanggal SAP "/Date(1704067200000)/" ke datetime
        """
        if sap_date_str.startswith('/Date(') and sap_date_str.endswith(')/'):
            timestamp = int(sap_date_str[6:-2])
            return datetime.fromtimestamp(timestamp / 1000)
        return None
    
    def load_zpsdt003_data(self):
        """
        Load data ZPSDT003 dari SAP API
        """
        try:
            auth = (SAP_USERNAME_ZPSDT003, SAP_PASSWORD_ZPSDT003)
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                SAP_API_URL_ZPSDT003,
                auth=auth,
                headers=headers,
                verify=False
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('d', {}).get('results', [])
            else:
                logging.error(f"ZPSDT003 API error: {response.status_code}")
                return []
        except Exception as e:
            logging.error(f"Exception loading ZPSDT003 data: {e}")
            return []

    def load_brand_data(self):
        """
        Load data brand dari SAP API (ZCDSV_SD_RMWEEKLY_SUM)
        """
        try:
            auth = (SAP_USERNAME, SAP_PASSWORD)
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                SAP_API_URL,
                auth=auth,
                headers=headers,
                verify=False
            )
            if response.status_code == 200:
                data = response.json()
                brand_results = data.get('d', {}).get('results', [])
                return brand_results
            else:
                logging.error(f"Brand data API error: {response.status_code}")
                return []
        except Exception as e:
            logging.error(f"Exception loading brand data: {e}")
            return []
    
    def get_previous_week_data(self, current_week, cycle, cycle_year):
        """
        Mengambil data week sebelumnya untuk perbandingan
        """
        try:
            # Hitung tanggal week lalu (7 hari yang lalu)
            previous_date = self.current_date - timedelta(days=7)
            previous_date_str = previous_date.strftime('%Y-%m-%d')
            
            # URL untuk data week lalu
            sap_api_url_previous = f"https://gajahmada.wismilak.com/sap/opu/odata/sap/ZCDSV_SD_RMWEEKLY_SUM_AE_CDS/ZCDSV_SD_RMWEEKLY_SUM_AE(p_date=datetime'{previous_date_str}T00:00:00',p_target_unit='{SATUAN}')/Set?$format=json"
            
            auth = (SAP_USERNAME, SAP_PASSWORD)
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                sap_api_url_previous,
                auth=auth,
                headers=headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                previous_results = data.get('d', {}).get('results', [])
                
                # Filter untuk cycle dan year yang sama
                matching_previous = [
                    brand for brand in previous_results 
                    if str(brand.get('cycle_year', '')) == str(cycle_year) and str(brand.get('cycle', '')) == str(cycle)
                ]
                
                return matching_previous
            else:
                logging.error(f"Previous week data API error: {response.status_code}")
                return []
                
        except Exception as e:
            logging.error(f"Exception loading previous week data: {e}")
            return []
    
    def find_matching_zpsdt003(self, zpsdt003_data):
        """
        Mencari data ZPSDT003 yang tanggalnya sesuai dengan CURRENT_DATE
        """
        matching_data = []
        for data in zpsdt003_data:
            fromdat = self.parse_sap_date(data['fromdat'])
            todat = self.parse_sap_date(data['todat'])
            if fromdat and todat:
                if fromdat <= self.current_date <= todat:
                    matching_data.append(data)
        return matching_data