from datetime import datetime
from config import CURRENT_DATE
from sap_service import SAPService
from database_service import DatabaseService
from data_processor import DataProcessor
from report_formatter import ReportFormatter
from email_service import EmailService
from telegram_service import TelegramService
from whatsapp_service import WhatsAppService
from convert import _parse_sap_date
from export_manager import ExportManager
from report_generator import ReportGenerator
from pdf_generator import RegionalReportPDFGenerator
from whatsapp import EnhancedWhatsAppService
import logging

class ReportApp:
    def __init__(self):
        self.sap_service = SAPService()
        self.db_service = DatabaseService()
        self.data_processor = DataProcessor()
        self.report_formatter = ReportFormatter()
        self.email_service = EmailService()
        self.telegram_service = TelegramService()
        self.whatsapp_service = WhatsAppService()
        self.export_manager = ExportManager()
        self.report_generator = ReportGenerator()
        self.pdf_generator = RegionalReportPDFGenerator()
        self.whatsapp = EnhancedWhatsAppService()

    def run_report_with_summary(self):
        """
        Main method to run report with summary
        """
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            
            if not zpsdt003_data or not brand_data:
                logging.warning("Data zpsdt003 atau brand tidak tersedia.")
                return False

            matching_zpsdt003 = self._get_matching_zpsdt003(zpsdt003_data)
            
            if not matching_zpsdt003:
                logging.warning("Tidak ada data zpsdt003 yang cocok dengan tanggal saat ini.")
                return False

            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week = int(zpsdt_data.get('week2', 3))

                matching_brands = self._get_matching_brands(brand_data, cycle_year, cycle)
                
                if not matching_brands:
                    continue

                # Merge brands data
                merged_brands = self.data_processor.merge_matching_brands_data(matching_brands)
                
                # if merged_brands:
                    # Export all data
                    # self._export_all_data(merged_brands, matching_brands, cycle_year, cycle)
                    
                    # Get previous week data
                    # previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                
            return True
            
        except Exception as e:
            logging.error(f"Error during run_report: {e}")
            return False

    def run_report_with_national_and_regional(self):
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            
            if not zpsdt003_data or not brand_data:
                return False
            
            # Filter brand_data untuk category1 = 'GD' saja
            filtered_brand_data = [
                brand for brand in brand_data 
                if brand.get('category1') == 'GD'
            ]
            
            # Jika tidak ada data setelah filtering, return False
            if not filtered_brand_data:
                return False
                
            matching_zpsdt003 = self._get_matching_zpsdt003(zpsdt003_data)
            if not matching_zpsdt003:
                return False
                
            national_reports_sent = 0
            regional_reports_sent = 0
            
            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week2 = int(zpsdt_data.get('week2', 3))
                current_week = int(zpsdt_data.get('week1', 3))
                
                # Gunakan filtered_brand_data instead of brand_data
                merged_brands = self.data_processor.merge_matching_brands_data(filtered_brand_data)
                
                if merged_brands:
                    national_success = self._send_national_report(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if national_success:
                        national_reports_sent += 1
                        
                    regional_success = self._send_regional_reports(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if regional_success:
                        regional_reports_sent += 1
                        
            return True
            
        except Exception as e:
            return False
    
    def _get_matching_zpsdt003(self, zpsdt003_data):
        matching_zpsdt003 = []
        current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')

        for data in zpsdt003_data:
            fromdat = _parse_sap_date(data['fromdat'])
            todat = _parse_sap_date(data['todat'])
            if fromdat and todat and fromdat <= current_date <= todat:
                matching_zpsdt003.append(data)

        return matching_zpsdt003

    def _get_matching_brands(self, brand_data, cycle_year, cycle):
        return [
            brand for brand in brand_data
            if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
        ]

    def _export_all_data(self, merged_brands, matching_brands, cycle_year, cycle):
        """
        Export all data types
        """
        # Export merged data
        # excel_file = self.export_manager.export_merged_data_to_excel(merged_brands, cycle_year, cycle)
        # if excel_file:
            # logging.info(f"Merged brands data exported to: {excel_file}")
        
        # Export original data
        # original_excel_file = self.export_manager.export_matching_brands_to_excel(
        #     matching_brands, cycle_year, cycle, 
        #     f"original_matching_brands_{cycle_year}_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        # )
        # if original_excel_file:
        #     logging.info(f"Original matching brands exported to: {original_excel_file}")
        
        # Export summary data
        summary_excel_file = self.export_manager.export_summary_to_excel(merged_brands, cycle_year, cycle)
        if summary_excel_file:
            logging.info(f"Summary data exported to: {summary_excel_file}")
        
        # Export summary JSON
        summary_json_files = self.export_manager.export_summary_json(merged_brands, cycle_year, cycle)
        if summary_json_files:
            logging.info(f"Summary JSON files exported: {summary_json_files}")

    def _send_national_report(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        """
        Send national report via WhatsApp and Telegram
        """
        try:
            # Generate national report
            report_message = self.report_generator.generate_national_report(
                merged_brands, cycle_year, cycle, current_week, current_week2
            )
            
            if not report_message:
                logging.warning("Failed to generate national report message.")
                return False
            
            success_count = 0
            
            # Send via WhatsApp
            try:
                whatsapp_success = self.whatsapp_service.send_national_report(report_message)
                if whatsapp_success:
                    logging.info("✓ National WhatsApp report sent successfully")
                    success_count += 1
                else:
                    logging.warning("⚠ Failed to send national WhatsApp report")
            except Exception as e:
                logging.error(f"Error sending national WhatsApp report: {e}")
            
            # Send via Telegram
            try:
                telegram_success = self.telegram_service.send_message(report_message)
                if telegram_success:
                    logging.info("✓ National Telegram report sent successfully")
                    success_count += 1
                else:
                    logging.warning("⚠ Failed to send national Telegram report")
            except Exception as e:
                logging.error(f"Error sending national Telegram report: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logging.error(f"Error in _send_national_report: {e}")
            return False

    def _send_regional_reports(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk regional reports.")
                return False

            summary_with_regional = self.data_processor.create_summary_with_regional(merged_brands)
            unique_regionals = list(set(item['regional_desc'] for item in summary_with_regional if item['regional_desc']))
            merger_detail = list(set(item['merger_detail'] for item in summary_with_regional if item['merger_detail']))
            total_sent = 0
            
            for regional_desc in unique_regionals:
                report_message = self.report_generator.generate_regional_report(
                    merged_brands, cycle_year, cycle, current_week, regional_desc, current_week2, merger_detail
                )
                
                if report_message:
                    try:
                        whatsapp_success = self.whatsapp_service.send_regional_report(report_message)
                        if whatsapp_success:
                            logging.info(f"✓ WhatsApp report sent for regional: {regional_desc}")
                        else:
                            logging.warning(f"⚠ Failed to send WhatsApp report for regional: {regional_desc}")
                    except Exception as e:
                        logging.error(f"Error sending WhatsApp report for {regional_desc}: {e}")

                    # Send via Telegram
                    try:
                        telegram_success = self.telegram_service.send_message(report_message)
                        if telegram_success:
                            logging.info(f"✓ Telegram report sent for regional: {regional_desc}")
                            total_sent += 1
                        else:
                            logging.warning(f"⚠ Failed to send Telegram report for regional: {regional_desc}")
                    except Exception as e:
                        logging.error(f"Error sending Telegram report for {regional_desc}: {e}")

            logging.info(f"✓ Total regional reports sent: {total_sent}")
            return total_sent > 0

        except Exception as e:
            logging.error(f"Error sending regional reports: {e}")
            return False