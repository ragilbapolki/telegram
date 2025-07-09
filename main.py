
# Updated main.py logging configuration to handle Unicode
import logging
from datetime import datetime
from config import CURRENT_DATE, SATUAN, REPORT_CONFIG
from sap_service import SAPService
from database_service import DatabaseService
from data_processor import DataProcessor
from report_formatter import ReportFormatter
from email_service import EmailService
from telegram_service import TelegramService
from whatsapp_service import WhatsAppService
import sys
import os

# Fix Windows console encoding for Unicode
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Setup logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('report_app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ReportApp:
    def __init__(self):
        self.sap_service = SAPService()
        self.db_service = DatabaseService()
        self.data_processor = DataProcessor()
        self.report_formatter = ReportFormatter()
        self.email_service = EmailService()
        self.telegram_service = TelegramService()
        self.whatsapp_service = WhatsAppService()
        
    def run_report(self):
        """
        Menjalankan proses report lengkap
        """
        try:
            logging.info(f"=== Memulai proses report untuk tanggal: {CURRENT_DATE} ===")
            
            # 1. Load data dari SAP
            logging.info("1. Mengambil data dari SAP...")
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            
            logging.info(f"   - ZPSDT003 records: {len(zpsdt003_data)}")
            logging.info(f"   - Brand records: {len(brand_data)}")
            
            if not zpsdt003_data or not brand_data:
                logging.error("Data SAP tidak lengkap, menghentikan proses")
                return False
            
            # 2. Cari data ZPSDT003 yang sesuai tanggal
            logging.info("2. Mencari data ZPSDT003 yang sesuai...")
            matching_zpsdt003 = []
            current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')
            
            for data in zpsdt003_data:
                fromdat = self._parse_sap_date(data['fromdat'])
                todat = self._parse_sap_date(data['todat'])
                if fromdat and todat:
                    if fromdat <= current_date <= todat:
                        matching_zpsdt003.append(data)
            
            if not matching_zpsdt003:
                logging.error(f"Tidak ada data ZPSDT003 yang sesuai untuk tanggal {CURRENT_DATE}")
                return False
            
            logging.info(f"   - Ditemukan {len(matching_zpsdt003)} data yang cocok")
            
            # 3. Get recipients dari database
            logging.info("3. Mengambil daftar penerima...")
            recipient_emails = self.db_service.get_recipients_from_db()
            logging.info(f"   - Recipients: {len(recipient_emails)} email")
            
            # 4. Process setiap data yang cocok
            total_sent = 0
            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week = int(zpsdt_data.get('week2', 3))
                
                logging.info(f"4. Memproses Cycle {cycle}, Year {cycle_year}, Week {current_week}")
                
                # Filter brand data yang sesuai
                matching_brands = [
                    brand for brand in brand_data 
                    if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
                ]
                
                if not matching_brands:
                    logging.warning(f"   - Tidak ada brand data untuk Cycle {cycle}, Year {cycle_year}")
                    continue
                
                logging.info(f"   - Ditemukan {len(matching_brands)} brand data")
                
                # Ambil data week sebelumnya
                previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                logging.info(f"   - Previous week data: {len(previous_week_data)} records")
                
                # Group by region
                regional_groups = {}
                for brand in matching_brands:
                    region = brand.get('regional_desc', 'Unknown Region')
                    if region not in regional_groups:
                        regional_groups[region] = []
                    regional_groups[region].append(brand)
                logging.info(f"   - Dikelompokkan menjadi {len(regional_groups)} regional")
                
                # Process setiap regional
                for region_name, regional_data in regional_groups.items():
                    success = self._process_regional_report(
                        region_name, 
                        zpsdt_data, 
                        regional_data, 
                        previous_week_data, 
                        recipient_emails,
                        current_week
                    )
                    
                    if success:
                        total_sent += 1
            
            logging.info(f"=== Proses selesai. Total laporan berhasil dikirim: {total_sent} ===")
            return True
            
        except Exception as e:
            logging.error(f"Error dalam proses report: {str(e)}")
            return False
    
    def _process_regional_report(self, region_name, zpsdt_data, regional_data, previous_week_data, recipient_emails, current_week):
        """
        Memproses laporan untuk satu regional
        """
        try:
            logging.info(f"     Processing {region_name}...")
            
            # Cari vkbur untuk notes
            vkbur = self._find_best_vkbur(regional_data)
            
            # Ambil notes dari database
            regional_notes = None
            if vkbur:
                cycle = zpsdt_data['cycle']
                cycle_year = zpsdt_data['cycle_year']
                # regional_notes = self.db_service.get_regional_notes(vkbur, cycle, current_week, cycle_year)
            
            # Hitung summary
            summary_data = self._calculate_regional_summary(regional_data, current_week, 4)
            
            # Format laporan
            telegram_message = self.report_formatter.format_telegram_message(
                region_name, zpsdt_data, regional_data, summary_data, previous_week_data, regional_notes
            )
            
            email_body = self.report_formatter.format_email_body(
                region_name, zpsdt_data, regional_data, summary_data, previous_week_data, regional_notes
            )

            # Format laporan
            whatsapp_message = self.report_formatter.format_whatsapp_message(
                region_name, zpsdt_data, regional_data, summary_data, previous_week_data, regional_notes
            )
            
            # Subject
            cycle = zpsdt_data['cycle']
            subject = f"📊 Weekly Report W{current_week} Cycle {cycle} | {region_name} | {CURRENT_DATE}"
            
            # Kirim ke Telegram
            telegram_success = self.telegram_service.send_message(telegram_message)
            
            # Kirim ke Whatsapp
            whatsapp_success = self.whatsapp_service.send_regional_report(whatsapp_message)

            # Kirim summary ke Telegram juga
            summary_msg = self.report_formatter.format_summary_message(region_name, summary_data, cycle, current_week)
            self.telegram_service.send_summary_message(region_name, summary_data, cycle, current_week)
            
            # Kirim email
            email_success = self.email_service.send_email(recipient_emails, subject, email_body)
            
            # Log hasil - using safe characters for Windows console
            if telegram_success and email_success and whatsapp_success:
                logging.info(f"     ✓ {region_name} - Berhasil kirim Telegram & Email")
                logging.info(f"        - Existing: {summary_data['current_week_sales_existing']:,.1f} BOX")
                logging.info(f"        - New Brand: {summary_data['current_week_sales_new']:,.1f} BOX")
                logging.info(f"        - Achievement: {summary_data['achievement_pct_existing']:.1f}%")
                if regional_notes:
                    logging.info(f"        - Notes: Ada")
                return True
            else:
                logging.error(f"     X {region_name} - Gagal kirim (Telegram: {telegram_success}, Email: {email_success})")
                return False
                
        except Exception as e:
            logging.error(f"     X Error processing {region_name}: {str(e)}")
            return False
    
    def _parse_sap_date(self, sap_date_str):
        """
        Mengkonversi format tanggal SAP "/Date(1704067200000)/" ke datetime
        """
        if sap_date_str.startswith('/Date(') and sap_date_str.endswith(')/'):
            timestamp = int(sap_date_str[6:-2])
            return datetime.fromtimestamp(timestamp / 1000)
        return None
    
    def _find_best_vkbur(self, regional_data):
        """
        Mencari vkbur yang paling tepat dari data yang tersedia
        """
        if not regional_data:
            return None
        
        sample_data = regional_data[0]
        
        # Prioritas field untuk vkbur
        priority_fields = [
            'vstel',           # Sales organization
            'vkbur_desc',    # Sales office
            'vkbur',     # Direct vkbur
            'kunnr',          # Customer number
            'vkorg',          # Sales organization
            'vtweg',          # Distribution channel
        ]
        
        # Coba setiap field berdasarkan prioritas
        for field in priority_fields:
            if field in sample_data and sample_data[field]:
                vkbur = str(sample_data[field]).strip()
                if vkbur:
                    return vkbur
        
        # Jika tidak ada yang cocok, gunakan regional_desc sebagai fallback
        if 'regional_desc' in sample_data:
            return str(sample_data['regional_desc'])
        
        return None
    
    def _calculate_regional_summary(self, regional_data, current_week, total_weeks_in_cycle):
        """
        Menghitung summary untuk regional tertentu
        """
        from collections import defaultdict
        
        existing_data = [item for item in regional_data if item.get('prctr_base') != '0000003998']
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        
        # Group existing and new brand data by matkl_desc
        grouped_existing = self._group_products_by_description(existing_data)
        grouped_new = self._group_products_by_description(new_brand_data)
        
        current_week_sales_existing = sum([item['qty_billing_sum'] for item in grouped_existing])
        current_week_sales_new = sum([item['qty_billing_sum'] for item in grouped_new])
        
        total_w1_to_current_existing = current_week_sales_existing * current_week
        qty_target_ae_w1_to_current_existing = sum([item['qty_target_ae'] for item in grouped_existing]) * current_week
        achievement_pct_existing = (total_w1_to_current_existing / qty_target_ae_w1_to_current_existing * 100) if qty_target_ae_w1_to_current_existing > 0 else 0
        omset_ideal_pct = (current_week / total_weeks_in_cycle * 100) if total_weeks_in_cycle > 0 else 0
        
        gd_data = [item for item in grouped_existing if item.get('category1') == 'GD']
        gd_current_sales = sum([item['qty_billing_sum'] for item in gd_data])
        gd_qty_target_ae= sum([item['qty_target_ae'] for item in gd_data]) * current_week
        gd_achievement_pct = (gd_current_sales * current_week / gd_qty_target_ae* 100) if gd_qty_target_ae> 0 else 0
        
        gd_plt_data = [item for item in grouped_existing if item.get('category1') in ['GD', 'PLT']]
        gd_plt_current_sales = sum([item['qty_billing_sum'] for item in gd_plt_data])
        gd_plt_qty_target_ae= sum([item['qty_target_ae'] for item in gd_plt_data]) * current_week
        gd_plt_achievement_pct = (gd_plt_current_sales * current_week / gd_plt_qty_target_ae* 100) if gd_plt_qty_target_ae> 0 else 0
        
        total_current_sales = sum([float(item.get('qty_billing_sum', 0)) for item in regional_data])
        
        return {
            'current_week_sales_existing': current_week_sales_existing,
            'current_week_sales_new': current_week_sales_new,
            'total_w1_to_current_existing': total_w1_to_current_existing,
            'qty_target_ae_w1_to_current_existing': qty_target_ae_w1_to_current_existing,
            'achievement_pct_existing': achievement_pct_existing,
            'omset_ideal_pct': omset_ideal_pct,
            'gd_current_sales': gd_current_sales,
            'gd_achievement_pct': gd_achievement_pct,
            'gd_plt_current_sales': gd_plt_current_sales,
            'gd_plt_achievement_pct': gd_plt_achievement_pct,
            'total_current_sales': total_current_sales,
            'existing_data': existing_data,
            'new_brand_data': new_brand_data,
            'grouped_existing': grouped_existing,
            'grouped_new': grouped_new,
            'gd_data': gd_data,
            'gd_plt_data': gd_plt_data
        }
    
    def _group_products_by_description(self, product_data):
        """
        Mengelompokkan produk berdasarkan matkl_desc dan sum qty_billing_sum serta qty_target_ae
        """
        from collections import defaultdict
        
        grouped_products = defaultdict(lambda: {
            'matkl_desc': '',
            'qty_billing_sum': 0.0,
            'qty_target_ae': 0.0,
            'category1': '',
            'prctr_base': ''
        })
        
        for item in product_data:
            matkl_desc = item.get('matkl_desc', 'Unknown Product')
            
            # Jika belum ada, set basic info
            if not grouped_products[matkl_desc]['matkl_desc']:
                grouped_products[matkl_desc]['matkl_desc'] = matkl_desc
                grouped_products[matkl_desc]['category1'] = item.get('category1', '')
                grouped_products[matkl_desc]['prctr_base'] = item.get('prctr_base', '')
            
            # Sum the values
            grouped_products[matkl_desc]['qty_billing_sum'] += float(item.get('qty_billing_sum', 0))
            grouped_products[matkl_desc]['qty_target_ae'] += float(item.get('qty_target_ae', 0))
        
        # Convert back to list
        return list(grouped_products.values())

def main():
    """
    Entry point aplikasi
    """
    print("🚀 Starting Report Application...")
    print(f"📅 Date: {CURRENT_DATE}")
    print(f"📊 Unit: {SATUAN}")
    print("=" * 50)
    
    app = ReportApp()
    success = app.run_report()
    
    if success:
        print("\n✓ Report application completed successfully!")
    else:
        print("\nX Report application failed!")
    
    return success

if __name__ == "__main__":
    main()