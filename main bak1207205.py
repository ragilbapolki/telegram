# Updated main.py dengan fitur National Report - Fixed Version + Data Merging
import logging
from datetime import datetime
from config import CURRENT_DATE, SATUAN
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
        
    def run_report(self, include_national=True):
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            if not zpsdt003_data or not brand_data:
                return False
            matching_zpsdt003 = []
            current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')
            
            for data in zpsdt003_data:
                fromdat = self._parse_sap_date(data['fromdat'])
                todat = self._parse_sap_date(data['todat'])
                if fromdat and todat:
                    if fromdat <= current_date <= todat:
                        matching_zpsdt003.append(data)
            
            if not matching_zpsdt003:
                return False
            recipient_emails = self.db_service.get_recipients_from_db()
            total_sent = 0
            national_sent = 0
            regional_sent = 0
            
            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week = int(zpsdt_data.get('week2', 3))
                
                # Filter brand data yang sesuai
                matching_brands = [
                    brand for brand in brand_data 
                    if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
                ]
                
                if not matching_brands:
                    continue
                
                # ROMBAK DATA - Merge data berdasarkan matkl, cycle_year, cycle, vkgrp
                merged_brands = self._merge_brand_data(matching_brands)
                
                # Ambil data week sebelumnya
                previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                
                # NATIONAL REPORT - Process all data as one (kirim dulu sebelum regional)
                if include_national:
                    national_success = self._process_national_report(
                        zpsdt_data, 
                        merged_brands,  # Gunakan merged_brands
                        previous_week_data, 
                        recipient_emails,
                        current_week
                    )
                    
                    if national_success:
                        national_sent += 1
                        logging.info("   ✓ NATIONAL REPORT berhasil dikirim")
                    else:
                        logging.error("   ✗ NATIONAL REPORT gagal dikirim")
                
                # REGIONAL REPORT - Group by region (existing logic)
                regional_groups = {}
                for brand in merged_brands:  # Gunakan merged_brands
                    region = brand.get('regional_desc', 'Unknown Region')
                    if region not in regional_groups:
                        regional_groups[region] = []
                    regional_groups[region].append(brand)
                
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
                        regional_sent += 1
            
            total_sent = national_sent + regional_sent
            return total_sent > 0
        except Exception as e:
            import traceback
            logging.error(f"Error in run_report: {str(e)}")
            logging.error(traceback.format_exc())
            return False
    
    def _merge_brand_data(self, matching_brands):
        """
        Merombak data matching_brands dengan menggabungkan data berdasarkan:
        - matkl, cycle_year, cycle, vkgrp
        - Prioritas source 'P' untuk data utama
        - Source 'T' untuk qty_target_ae dan prctr_ae
        """
        try:
            # Group data berdasarkan key: matkl + cycle_year + cycle + vkgrp
            grouped_data = {}
            
            for brand in matching_brands:
                key = f"{brand.get('matkl', '')}-{brand.get('cycle_year', '')}-{brand.get('cycle', '')}-{brand.get('vkgrp', '')}"
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        'source_p': None,
                        'source_t': None,
                        'others': []
                    }
                
                source = brand.get('source', '').upper()
                if source == 'P':
                    grouped_data[key]['source_p'] = brand
                elif source == 'T':
                    grouped_data[key]['source_t'] = brand
                else:
                    grouped_data[key]['others'].append(brand)
            
            # Buat JSON baru dengan menggabungkan data
            merged_brands = []
            
            for key, data_group in grouped_data.items():
                source_p = data_group['source_p']
                source_t = data_group['source_t']
                others = data_group['others']
                
                # Jika ada source P, gunakan sebagai base
                if source_p:
                    merged_item = source_p.copy()
                    
                    # Jika ada source T, ambil qty_target_ae dan prctr_ae dari source T
                    if source_t:
                        merged_item['qty_target_ae'] = source_t.get('qty_target_ae', 0)
                        merged_item['prctr_ae'] = source_t.get('prctr_ae', '')
                        
                    else:
                        # Jika tidak ada source T, kosongkan qty_target_ae dan prctr_ae
                        merged_item['qty_target_ae'] = 0
                        merged_item['prctr_ae'] = ''
                        
                    merged_brands.append(merged_item)
                
                # Jika tidak ada source P, tapi ada source T
                elif source_t:
                    merged_item = source_t.copy()
                    merged_brands.append(merged_item)
                
                # Jika tidak ada source P dan T, gunakan yang pertama dari others
                elif others:
                    merged_item = others[0].copy()
                    merged_item['qty_target_ae'] = 0
                    merged_item['prctr_ae'] = ''
                    merged_brands.append(merged_item)
            
            logging.info(f"Data merging completed: {len(matching_brands)} original -> {len(merged_brands)} merged")
            return merged_brands
            
        except Exception as e:
            logging.error(f"Error in _merge_brand_data: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            # Return original data if merge fails
            return matching_brands
    
    def _process_national_report(self, zpsdt_data, national_data, previous_week_data, recipient_emails, current_week):
        try:
            if not national_data:
                return False
            summary_data = self._calculate_regional_summary(national_data, current_week, 4)
            try:
                if hasattr(self.report_formatter, 'format_national_telegram_message'):
                    telegram_message = self.report_formatter.format_national_telegram_message(
                        zpsdt_data, national_data, summary_data, previous_week_data
                    )
                else:
                    # Fallback ke format regional dengan nama "NASIONAL"
                    telegram_message = self.report_formatter.format_telegram_message(
                        "NASIONAL", zpsdt_data, national_data, summary_data, previous_week_data, None
                    )
                if hasattr(self.report_formatter, 'format_national_whatsapp_message'):
                    whatsapp_message = self.report_formatter.format_national_whatsapp_message(
                        zpsdt_data, national_data, summary_data, previous_week_data
                    )
                else:
                    whatsapp_message = self.report_formatter.format_whatsapp_message(
                        "NASIONAL", zpsdt_data, national_data, summary_data, previous_week_data, None
                    )
                
                if hasattr(self.report_formatter, 'format_national_email_body'):
                    email_body = self.report_formatter.format_national_email_body(
                        zpsdt_data, national_data, summary_data, previous_week_data
                    )
                else:
                    # Fallback ke format regional dengan nama "NASIONAL"
                    email_body = self.report_formatter.format_email_body(
                        "NASIONAL", zpsdt_data, national_data, summary_data, previous_week_data, None
                    )
            except Exception as format_error:
                import traceback
                logging.error(f"Error formatting national report: {str(format_error)}")
                logging.error(traceback.format_exc())
                return False
            cycle = zpsdt_data['cycle']
            subject = f"📊 National Weekly Report W{current_week} Cycle {cycle} | NASIONAL | {CURRENT_DATE}"
            try:
                if hasattr(self.telegram_service, 'send_national_message'):
                    telegram_success = self.telegram_service.send_national_message(telegram_message)
                else:
                    telegram_success = False
            except Exception as e:
                logging.error(f"Error sending national telegram: {str(e)}")
                telegram_success = False
            try:
                if hasattr(self.whatsapp_service, 'send_national_report'):
                    if whatsapp_message and whatsapp_message.strip():
                        whatsapp_success = self.whatsapp_service.send_national_report(whatsapp_message)
                    else:
                        whatsapp_success = False
                else:
                    whatsapp_success = False
            except Exception as e:
                logging.error(f"Error sending national whatsapp: {str(e)}")
                whatsapp_success = False
            
            # Kirim email
            try:
                email_success = self.email_service.send_email(recipient_emails, subject, email_body)
            except Exception as e:
                logging.error(f"Error sending national email: {str(e)}")
                email_success = False
            
            # Evaluasi hasil
            success_count = sum([telegram_success, whatsapp_success, email_success])
            
            if success_count >= 2:  # At least 2 out of 3 channels success
                return True
            else:
                return False
                
        except Exception as e:
            import traceback
            logging.error(f"Error in _process_national_report: {str(e)}")
            logging.error(traceback.format_exc())
            return False
    
    def _process_regional_report(self, region_name, zpsdt_data, regional_data, previous_week_data, recipient_emails, current_week):
        try:
            vkbur = self._find_best_vkbur(regional_data)
            regional_notes = None
            if vkbur:
                cycle = zpsdt_data['cycle']
                cycle_year = zpsdt_data['cycle_year']
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
            try:
                # Validasi message tidak kosong
                if whatsapp_message and whatsapp_message.strip():
                    whatsapp_success = self.whatsapp_service.send_regional_report(whatsapp_message)
                else:
                    whatsapp_success = False
            except Exception as e:
                logging.error(f"Error sending regional whatsapp: {str(e)}")
                whatsapp_success = False
            # Kirim summary ke Telegram juga
            summary_msg = self.report_formatter.format_summary_message(region_name, summary_data, cycle, current_week)
            self.telegram_service.send_summary_message(region_name, summary_data, cycle, current_week)
            # Kirim email
            email_success = self.email_service.send_email(recipient_emails, subject, email_body)
            
            # Evaluasi hasil - lebih fleksibel untuk regional
            success_count = sum([telegram_success, whatsapp_success, email_success])
            
            return success_count >= 1  # At least 1 channel success for regional
            
        except Exception as e:
            logging.error(f"     ✗ Error processing {region_name}: {str(e)}")
            return False
    
    def _parse_sap_date(self, sap_date_str):
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
        
        try:
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
        except Exception as e:
            logging.error(f"Error calculating regional summary: {str(e)}")
            # Return default values to prevent crash
            return {
                'current_week_sales_existing': 0,
                'current_week_sales_new': 0,
                'total_w1_to_current_existing': 0,
                'qty_target_ae_w1_to_current_existing': 0,
                'achievement_pct_existing': 0,
                'omset_ideal_pct': 0,
                'gd_current_sales': 0,
                'gd_achievement_pct': 0,
                'gd_plt_current_sales': 0,
                'gd_plt_achievement_pct': 0,
                'total_current_sales': 0,
                'existing_data': [],
                'new_brand_data': [],
                'grouped_existing': [],
                'grouped_new': [],
                'gd_data': [],
                'gd_plt_data': []
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
    app = ReportApp()
    success = app.run_report(include_national=True)  # Set False untuk skip national report
    
    if success:
        print("\n✓ Report application completed successfully!")
    else:
        print("\nX Report application failed!")
    
    return success

if __name__ == "__main__":
    main()