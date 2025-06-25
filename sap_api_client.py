"""
SAP API Client for handling SAP data retrieval
"""
import json
import requests
import urllib3
from datetime import datetime, timedelta
from config import (
    SAP_API_URL_ZPSDT003, SAP_USERNAME_ZPSDT003, SAP_PASSWORD_ZPSDT003,
    SAP_API_URL, SAP_USERNAME, SAP_PASSWORD
)

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SAPAPIClient:
    def __init__(self):
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def load_zpsdt003_data(self):
        """
        Load ZPSDT003 data from SAP API
        """
        try:
            print("Retrieving ZPSDT003 data from SAP...")
            
            auth = (SAP_USERNAME_ZPSDT003, SAP_PASSWORD_ZPSDT003)
            
            response = requests.get(
                SAP_API_URL_ZPSDT003,
                auth=auth,
                headers=self.headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('d', {}).get('results', [])
                print(f"Successfully retrieved ZPSDT003 data: {len(results)} records")
                return results
            else:
                print(f"Error retrieving ZPSDT003 data: {response.status_code} - {response.text}")
                return self.get_sample_zpsdt003_data()
                
        except Exception as e:
            print(f"Exception while retrieving ZPSDT003 data: {str(e)}")
            return self.get_sample_zpsdt003_data()
    
    def load_brand_data(self):
        """
        Load brand data from SAP API (ZCDSV_SD_RMWEEKLY_SUM)
        """
        try:
            print("Retrieving brand data from SAP...")
            print(f"API URL: {SAP_API_URL}")
            
            auth = (SAP_USERNAME, SAP_PASSWORD)
            
            response = requests.get(
                SAP_API_URL,
                auth=auth,
                headers=self.headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                brand_results = data.get('d', {}).get('results', [])
                print(f"Successfully retrieved brand data: {len(brand_results)} records")
                
                # Debug: Print sample data structure
                if brand_results:
                    print("Sample brand data structure:")
                    print(json.dumps(brand_results[0], indent=2))
                
                return brand_results
            else:
                print(f"Error retrieving brand data: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Exception while retrieving brand data: {str(e)}")
            return []
    
    def get_sample_zpsdt003_data(self):
        """
        Sample ZPSDT003 data for testing
        """
        current_year = datetime.now().year
        current_cycle = self.get_current_cycle()
        
        today = datetime.now()
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=7)
        
        return [
            {
                "__metadata": {
                    "id": f"http://saphana-whd.wismilak.com:8010/sap/opu/odata/sap/ZCDSV_ZPSDT003_CDS/ZCDSV_ZPSDT003(cycle_year='{current_year}',cycle={current_cycle},week1=1)",
                    "uri": f"http://saphana-whd.wismilak.com:8010/sap/opu/odata/sap/ZCDSV_ZPSDT003_CDS/ZCDSV_ZPSDT003(cycle_year='{current_year}',cycle={current_cycle},week1=1)",
                    "type": "ZCDSV_ZPSDT003_CDS.ZCDSV_ZPSDT003Type"
                },
                "cycle_year": str(current_year),
                "cycle": current_cycle,
                "week1": 1,
                "week2": 3,
                "fromdat": f"/Date({int(start_date.timestamp() * 1000)})/",
                "todat": f"/Date({int(end_date.timestamp() * 1000)})/",
                "harikerja": "5.0"
            }
        ]
    
    def get_current_cycle(self):
        """
        Determine cycle based on current date
        """
        current_month = datetime.now().month
        
        # Simple logic: every 2 months = 1 cycle, starting from January
        cycle = ((current_month - 1) // 2) + 1
        
        # For June (month 6), cycle could be 3 or 5 depending on business rule
        if current_month == 6:
            cycle = 5
        
        print(f"Current month: {current_month}, Calculated cycle: {cycle}")
        return cycle