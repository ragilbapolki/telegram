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
                merged_brands = self.data_processor.merge_matching_brands_data(matching_brands, cycle_year)
                
                # if merged_brands:
                    # Export all data
                    # self._export_all_data(merged_brands, matching_brands, cycle_year, cycle)
                    
                    # Get previous week data
                    # previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                
            return True
            
        except Exception as e:
            logging.error(f"Error during run_report: {e}")
            return False

    def run_report_with_national_regional_and_sales_office(self):
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
            sales_office_reports_sent = 0
            
            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week2 = int(zpsdt_data.get('week2', 3))
                current_week = int(zpsdt_data.get('week1', 3))
                
                # Gunakan filtered_brand_data instead of brand_data
                merged_brands = self.data_processor.merge_matching_brands_data(filtered_brand_data, cycle_year)
                
                if merged_brands:
                    # Send National Report
                    national_success = self._send_national_report(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if national_success:
                        national_reports_sent += 1
                        
                    # Send Regional Reports (Ordered)
                    regional_success = self._send_regional_reports_ordered(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if regional_success:
                        regional_reports_sent += 1
                        
                    # Send Sales Office Reports
                    sales_office_success = self._send_sales_office_reports(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if sales_office_success:
                        sales_office_reports_sent += 1
                        
            logging.info(f"Reports sent - National: {national_reports_sent}, Regional: {regional_reports_sent}, Sales Office: {sales_office_reports_sent}")
            return True
            
        except Exception as e:
            logging.error(f"Error in run_report_with_national_regional_and_sales_office: {e}")
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
                merged_brands = self.data_processor.merge_matching_brands_data(filtered_brand_data, cycle_year)
                
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
        
        # Export summary data
        summary_excel_file = self.export_manager.export_summary_to_excel(merged_brands, cycle_year, cycle)
        if summary_excel_file:
            logging.info(f"Summary data exported to: {summary_excel_file}")
        
        # Export summary JSON
        summary_json_files = self.export_manager.export_summary_json(merged_brands, cycle_year, cycle)
        if summary_json_files:
            logging.info(f"Summary JSON files exported: {summary_json_files}")

    def _send_national_report(self, merged_brands, cycle_year, cycle, current_week, current_week2):
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

    def _send_regional_reports_ordered(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk regional reports.")
                return False

            summary_with_regional = self.data_processor.create_summary_with_regional(merged_brands)
            unique_regionals = list(set(item['regional_desc'] for item in summary_with_regional if item['regional_desc']))
            merger_detail = list(set(item['merger_detail'] for item in summary_with_regional if item['merger_detail']))
            
            # Sort regionals - assuming format like "Regional 1", "Regional 2", etc.
            def extract_regional_number(regional_desc):
                """Extract number from regional description for sorting"""
                try:
                    # Try to extract number from strings like "Regional 1", "Regional 2"
                    parts = regional_desc.lower().split()
                    for part in parts:
                        if part.isdigit():
                            return int(part)
                    # If no number found, return the string for alphabetical sorting
                    return float('inf')
                except:
                    return float('inf')
            
            # Sort unique_regionals by extracted number
            sorted_regionals = sorted(unique_regionals, key=extract_regional_number)
            
            total_sent = 0
            
            logging.info(f"Sending regional reports in order: {sorted_regionals}")
            
            for regional_desc in sorted_regionals:
                logging.info(f"Processing regional: {regional_desc}")
                
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

            logging.info(f"✓ Total ordered regional reports sent: {total_sent}")
            return total_sent > 0

        except Exception as e:
            logging.error(f"Error sending ordered regional reports: {e}")
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

    def _send_sales_office_reports(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk sales office reports.")
                return False

            # Get unique sales offices from merged brands data
            summary_with_sales_office = self.data_processor.create_summary_with_sales_office(merged_brands)
            unique_sales_offices = list(set(item['vkbur_desc'] for item in summary_with_sales_office if item.get('vkbur_desc')))
            merger_detail = list(set(item['merger_detail'] for item in summary_with_sales_office if item['merger_detail']))
            
            # Sort sales offices alphabetically
            sorted_sales_offices = sorted(unique_sales_offices)
            
            total_sent = 0
            
            logging.info(f"Sending sales office reports for: {sorted_sales_offices}")
            
            for vkbur_desc in sorted_sales_offices:
                logging.info(f"Processing sales office: {vkbur_desc}")
                
                # Generate sales office report
                report_message = self.report_generator.generate_sales_office_report(
                    merged_brands, cycle_year, cycle, current_week, vkbur_desc, current_week2, merger_detail
                )
                
                if report_message:
                    try:
                        whatsapp_success = self.whatsapp_service.send_sales_office_report(report_message)
                        if whatsapp_success:
                            logging.info(f"✓ WhatsApp report sent for sales office: {vkbur_desc}")
                        else:
                            logging.warning(f"⚠ Failed to send WhatsApp report for sales office: {vkbur_desc}")
                    except Exception as e:
                        logging.error(f"Error sending WhatsApp report for {vkbur_desc}: {e}")

                    # Send via Telegram
                    try:
                        telegram_success = self.telegram_service.send_message(report_message)
                        if telegram_success:
                            logging.info(f"✓ Telegram report sent for sales office: {vkbur_desc}")
                            total_sent += 1
                        else:
                            logging.warning(f"⚠ Failed to send Telegram report for sales office: {vkbur_desc}")
                    except Exception as e:
                        logging.error(f"Error sending Telegram report for {vkbur_desc}: {e}")
                else:
                    logging.warning(f"Failed to generate report message for sales office: {vkbur_desc}")

            logging.info(f"✓ Total sales office reports sent: {total_sent}")
            return total_sent > 0

        except Exception as e:
            logging.error(f"Error sending sales office reports: {e}")
            return False