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
import logging
import sys
import pandas as pd
import os

if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

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

    def export_matching_brands_to_excel(self, matching_brands, cycle_year, cycle, filename=None):
        try:
            if not matching_brands:
                logging.warning("Tidak ada data matching brands untuk diekspor.")
                return None

            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"matching_brands_{cycle_year}_{cycle}_{timestamp}.xlsx"

            # Ensure exports directory exists
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            filepath = os.path.join(export_dir, filename)

            # Convert to DataFrame
            df = pd.DataFrame(matching_brands)
            
            # Add metadata sheet
            metadata = {
                'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'Cycle Year': [cycle_year],
                'Cycle': [cycle],
                'Total Records': [len(matching_brands)],
                'Current Date': [CURRENT_DATE]
            }
            metadata_df = pd.DataFrame(metadata)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Matching Brands', index=False)
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
                workbook = writer.book
                if 'Matching Brands' in workbook.sheetnames:
                    worksheet = workbook['Matching Brands']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Format metadata sheet
                if 'Metadata' in workbook.sheetnames:
                    worksheet = workbook['Metadata']
                    worksheet.column_dimensions['A'].width = 20
                    worksheet.column_dimensions['B'].width = 30

            logging.info(f"✓ Successfully exported {len(matching_brands)} matching brands to: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Error exporting matching brands to Excel: {e}")
            return None

    def merge_matching_brands_data(self, matching_brands):
        try:
            if not matching_brands:
                logging.warning("Tidak ada data matching brands untuk dimerge.")
                return []

            grouped_data = {}
            
            for brand in matching_brands:
                key = (
                    str(brand.get('matkl', '')),
                    str(brand.get('cycle_year', '')),
                    str(brand.get('cycle', '')),
                    str(brand.get('vkgrp', ''))
                )
                
                if key not in grouped_data:
                    grouped_data[key] = {'P': [], 'T': []}
                
                source = str(brand.get('source', '')).upper()
                if source in ['P', 'T']:
                    grouped_data[key][source].append(brand)

            # Merge data
            merged_data = []
            merge_stats = {
                'total_groups': len(grouped_data),
                'merged_records': 0,
                'p_only_records': 0,
                't_only_records': 0,
                'no_match_records': 0
            }

            for key, sources in grouped_data.items():
                matkl, cycle_year, cycle, vkgrp = key
                
                p_records = sources['P']
                t_records = sources['T']
                
                if p_records and t_records:
                    for p_record in p_records:
                        merged_record = p_record.copy()
                        if t_records:
                            t_record = t_records[0]  # Atau bisa disesuaikan logika pemilihan
                            
                            merged_record['qty_target_ae'] = t_record.get('qty_target_ae', 0)
                            merged_record['prctr_ae'] = t_record.get('prctr_ae', '')
                            
                            merged_record['merge_status'] = 'MERGED'
                            merged_record['merge_source_p'] = p_record.get('source', '')
                            merged_record['merge_source_t'] = t_record.get('source', '')
                            
                        merged_data.append(merged_record)
                        merge_stats['merged_records'] += 1
                        
                elif p_records:
                    for p_record in p_records:
                        merged_record = p_record.copy()
                        merged_record['qty_target_ae'] = 0  # Default value
                        merged_record['prctr_ae'] = ''      # Default value
                        merged_record['merge_status'] = 'P_ONLY'
                        merged_data.append(merged_record)
                        merge_stats['p_only_records'] += 1
                        
                elif t_records:
                    for t_record in t_records:
                        merged_record = t_record.copy()
                        merged_record['merge_status'] = 'T_ONLY'
                        merged_data.append(merged_record)
                        merge_stats['t_only_records'] += 1
            return merged_data

        except Exception as e:
            logging.error(f"Error merging matching brands data: {e}")
            return []

    def export_merged_data_to_excel(self, merged_data, cycle_year, cycle, filename=None):
        try:
            if not merged_data:
                logging.warning("Tidak ada data merged untuk diekspor.")
                return None
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"merged_brands_{cycle_year}_{cycle}_{timestamp}.xlsx"
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            filepath = os.path.join(export_dir, filename)

            df = pd.DataFrame(merged_data)
            
            merge_summary = df['merge_status'].value_counts().to_dict()
            
            summary_data = []
            for status, count in merge_summary.items():
                summary_data.append({
                    'Merge Status': status,
                    'Count': count,
                    'Percentage': f"{(count/len(merged_data)*100):.2f}%"
                })
            summary_df = pd.DataFrame(summary_data)
            
            metadata = {
                'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                'Cycle Year': [cycle_year],
                'Cycle': [cycle],
                'Total Records': [len(merged_data)],
                'Current Date': [CURRENT_DATE],
                'Merged Records': [merge_summary.get('MERGED', 0)],
                'P Only Records': [merge_summary.get('P_ONLY', 0)],
                'T Only Records': [merge_summary.get('T_ONLY', 0)]
            }
            metadata_df = pd.DataFrame(metadata)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Merged Data', index=False)
                
                summary_df.to_excel(writer, sheet_name='Merge Summary', index=False)
                
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
                
                workbook = writer.book
                
                for sheet_name in ['Merged Data', 'Merge Summary', 'Metadata']:
                    if sheet_name in workbook.sheetnames:
                        worksheet = workbook[sheet_name]
                        
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            
                            adjusted_width = min(max_length + 2, 50)
                            worksheet.column_dimensions[column_letter].width = adjusted_width

            logging.info(f"✓ Successfully exported merged data to: {filepath}")
            logging.info(f"  - Total records: {len(merged_data)}")
            
            return filepath

        except Exception as e:
            logging.error(f"Error exporting merged data to Excel: {e}")
            return None

    def export_all_matching_brands(self):
        """
        Export all matching brands data to a single Excel file with multiple sheets
        """
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            
            if not zpsdt003_data or not brand_data:
                logging.warning("Data zpsdt003 atau brand tidak tersedia.")
                return None

            matching_zpsdt003 = []
            current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')

            for data in zpsdt003_data:
                fromdat = _parse_sap_date(data['fromdat'])
                todat = _parse_sap_date(data['todat'])
                if fromdat and todat and fromdat <= current_date <= todat:
                    matching_zpsdt003.append(data)

            if not matching_zpsdt003:
                logging.warning("Tidak ada data zpsdt003 yang cocok dengan tanggal saat ini.")
                return None

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"all_matching_brands_{timestamp}.xlsx"
            
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            filepath = os.path.join(export_dir, filename)

            all_matching_brands = []
            cycle_summary = []

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                for zpsdt_data in matching_zpsdt003:
                    cycle_year = str(zpsdt_data['cycle_year'])
                    cycle = str(zpsdt_data['cycle'])

                    matching_brands = [
                        brand for brand in brand_data
                        if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
                    ]

                    if matching_brands:
                        for brand in matching_brands:
                            brand_with_cycle = brand.copy()
                            brand_with_cycle['source_cycle_year'] = cycle_year
                            brand_with_cycle['source_cycle'] = cycle
                            all_matching_brands.append(brand_with_cycle)

                        df = pd.DataFrame(matching_brands)
                        sheet_name = f"Cycle_{cycle_year}_{cycle}"[:31]  # Excel sheet name limit
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        
                        cycle_summary.append({
                            'Cycle Year': cycle_year,
                            'Cycle': cycle,
                            'Brand Count': len(matching_brands),
                            'Sheet Name': sheet_name
                        })

                # Export all matching brands to main sheet
                if all_matching_brands:
                    all_df = pd.DataFrame(all_matching_brands)
                    all_df.to_excel(writer, sheet_name='All Matching Brands', index=False)

                # Export summary
                if cycle_summary:
                    summary_df = pd.DataFrame(cycle_summary)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Export metadata
                metadata = {
                    'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    'Total Cycles': [len(matching_zpsdt003)],
                    'Total Brands': [len(all_matching_brands)],
                    'Current Date': [CURRENT_DATE]
                }
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            return filepath

        except Exception as e:
            logging.error(f"Error exporting all matching brands: {e}")
            return None
        
    def create_summary_with_regional(self, merged_brands):
        """
        Create summary JSON with regional_desc grouping
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk summary.")
                return []

            # Group by required fields
            grouped_data = {}
            
            for brand in merged_brands:
                # Process prctr_ae
                prctr_ae = str(brand.get('prctr_ae', ''))
                if prctr_ae in ['0000003998', '3998']:
                    prctr_ae = '3998'
                elif prctr_ae and prctr_ae != '':
                    # Keep the first non-empty value if different
                    pass
                
                # Create grouping key
                key = (
                    str(brand.get('category1', '')),
                    str(brand.get('cycle', '')),
                    str(brand.get('cycle_year', '')),
                    str(brand.get('matkl', '')),
                    str(brand.get('matkl_desc', '')),
                    str(brand.get('regional_desc', '')),
                    str(brand.get('week1', '')),
                    str(brand.get('qty_target_ae', ''))
                )
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        'category1': str(brand.get('category1', '')),
                        'cycle': str(brand.get('cycle', '')),
                        'cycle_year': str(brand.get('cycle_year', '')),
                        'matkl': str(brand.get('matkl', '')),
                        'matkl_desc': str(brand.get('matkl_desc', '')),
                        'regional_desc': str(brand.get('regional_desc', '')),
                        'week1': str(brand.get('week1', '')),
                        'qty_target_ae': brand.get('qty_target_ae', 0),
                        'qty_billing_sum': 0,
                        'prctr_ae': prctr_ae,
                        'record_count': 0
                    }
                
                # Sum qty_billing_sum
                grouped_data[key]['qty_billing_sum'] += float(brand.get('qty_billing_sum', 0) or 0)
                grouped_data[key]['record_count'] += 1
                
                # Handle prctr_ae logic
                current_prctr = grouped_data[key]['prctr_ae']
                if prctr_ae in ['0000003998', '3998']:
                    grouped_data[key]['prctr_ae'] = '3998'
                elif not current_prctr and prctr_ae:
                    grouped_data[key]['prctr_ae'] = prctr_ae

            # Convert to list
            summary_data = list(grouped_data.values())
            
            logging.info(f"✓ Created summary with regional: {len(summary_data)} records from {len(merged_brands)} original records")
            return summary_data

        except Exception as e:
            logging.error(f"Error creating summary with regional: {e}")
            return []

    def create_summary_without_regional(self, merged_brands):
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk summary.")
                return []

            # Group by required fields (without regional_desc)
            grouped_data = {}
            
            for brand in merged_brands:
                # Process prctr_ae
                prctr_ae = str(brand.get('prctr_ae', ''))
                if prctr_ae in ['0000003998', '3998']:
                    prctr_ae = '3998'
                elif prctr_ae and prctr_ae != '':
                    # Keep the first non-empty value if different
                    pass
                
                # Create grouping key (without regional_desc)
                key = (
                    str(brand.get('category1', '')),
                    str(brand.get('cycle', '')),
                    str(brand.get('cycle_year', '')),
                    str(brand.get('matkl', '')),
                    str(brand.get('matkl_desc', '')),
                    str(brand.get('week1', '')),
                    str(brand.get('qty_target_ae', ''))
                )
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        'category1': str(brand.get('category1', '')),
                        'cycle': str(brand.get('cycle', '')),
                        'cycle_year': str(brand.get('cycle_year', '')),
                        'matkl': str(brand.get('matkl', '')),
                        'matkl_desc': str(brand.get('matkl_desc', '')),
                        'week1': str(brand.get('week1', '')),
                        'qty_target_ae': brand.get('qty_target_ae', 0),
                        'qty_billing_sum': 0,
                        'prctr_ae': prctr_ae,
                        'record_count': 0
                    }
                
                # Sum qty_billing_sum
                grouped_data[key]['qty_billing_sum'] += float(brand.get('qty_billing_sum', 0) or 0)
                grouped_data[key]['record_count'] += 1
                
                # Handle prctr_ae logic
                current_prctr = grouped_data[key]['prctr_ae']
                if prctr_ae in ['0000003998', '3998']:
                    grouped_data[key]['prctr_ae'] = '3998'
                elif not current_prctr and prctr_ae:
                    grouped_data[key]['prctr_ae'] = prctr_ae

            # Convert to list
            summary_data = list(grouped_data.values())
            
            logging.info(f"✓ Created summary without regional: {len(summary_data)} records from {len(merged_brands)} original records")
            return summary_data

        except Exception as e:
            logging.error(f"Error creating summary without regional: {e}")
            return []

    def export_summary_to_excel(self, merged_brands, cycle_year, cycle, filename=None):
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk summary.")
                return None

            # Create summaries
            summary_with_regional = self.create_summary_with_regional(merged_brands)
            summary_without_regional = self.create_summary_without_regional(merged_brands)

            if not summary_with_regional and not summary_without_regional:
                logging.warning("Tidak ada data summary untuk diekspor.")
                return None

            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"summary_brands_{cycle_year}_{cycle}_{timestamp}.xlsx"

            # Ensure exports directory exists
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            filepath = os.path.join(export_dir, filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Export summary with regional
                if summary_with_regional:
                    df_regional = pd.DataFrame(summary_with_regional)
                    df_regional.to_excel(writer, sheet_name='Summary With Regional', index=False)
                    
                    # Create statistics for regional summary
                    regional_stats = {
                        'Total Records': [len(summary_with_regional)],
                        'Total Qty Billing Sum': [sum(item['qty_billing_sum'] for item in summary_with_regional)],
                        'Total Qty Target FUF': [sum(item['qty_target_ae'] for item in summary_with_regional)],
                        'Unique Categories': [len(set(item['category1'] for item in summary_with_regional))],
                        'Unique Materials': [len(set(item['matkl'] for item in summary_with_regional))],
                        'Unique Regions': [len(set(item['regional_desc'] for item in summary_with_regional))]
                    }
                    pd.DataFrame(regional_stats).to_excel(writer, sheet_name='Regional Stats', index=False)

                # Export summary without regional
                if summary_without_regional:
                    df_no_regional = pd.DataFrame(summary_without_regional)
                    df_no_regional.to_excel(writer, sheet_name='Summary No Regional', index=False)
                    
                    # Create statistics for non-regional summary
                    no_regional_stats = {
                        'Total Records': [len(summary_without_regional)],
                        'Total Qty Billing Sum': [sum(item['qty_billing_sum'] for item in summary_without_regional)],
                        'Total Qty Target FUF': [sum(item['qty_target_ae'] for item in summary_without_regional)],
                        'Unique Categories': [len(set(item['category1'] for item in summary_without_regional))],
                        'Unique Materials': [len(set(item['matkl'] for item in summary_without_regional))]
                    }
                    pd.DataFrame(no_regional_stats).to_excel(writer, sheet_name='No Regional Stats', index=False)

                # Export metadata
                metadata = {
                    'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    'Cycle Year': [cycle_year],
                    'Cycle': [cycle],
                    'Original Records': [len(merged_brands)],
                    'Summary With Regional Records': [len(summary_with_regional)],
                    'Summary Without Regional Records': [len(summary_without_regional)],
                    'Current Date': [CURRENT_DATE]
                }
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)

                # Auto-adjust column widths
                workbook = writer.book
                for sheet_name in workbook.sheetnames:
                    worksheet = workbook[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            logging.info(f"✓ Successfully exported summary to: {filepath}")
            logging.info(f"  - Summary with regional: {len(summary_with_regional)} records")
            logging.info(f"  - Summary without regional: {len(summary_without_regional)} records")
            
            return filepath

        except Exception as e:
            logging.error(f"Error exporting summary to Excel: {e}")
            return None

    def export_summary_json(self, merged_brands, cycle_year, cycle):
        """
        Export summary data as JSON files
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk summary.")
                return None

            # Create summaries
            summary_with_regional = self.create_summary_with_regional(merged_brands)
            summary_without_regional = self.create_summary_without_regional(merged_brands)

            if not summary_with_regional and not summary_without_regional:
                logging.warning("Tidak ada data summary untuk diekspor.")
                return None

            # Ensure exports directory exists
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export JSON files
            json_files = []
            
            if summary_with_regional:
                json_filename_regional = f"summary_with_regional_{cycle_year}_{cycle}_{timestamp}.json"
                json_filepath_regional = os.path.join(export_dir, json_filename_regional)
                
                with open(json_filepath_regional, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(summary_with_regional, f, ensure_ascii=False, indent=2)
                
                json_files.append(json_filepath_regional)
                logging.info(f"✓ Exported summary with regional to: {json_filepath_regional}")

            if summary_without_regional:
                json_filename_no_regional = f"summary_without_regional_{cycle_year}_{cycle}_{timestamp}.json"
                json_filepath_no_regional = os.path.join(export_dir, json_filename_no_regional)
                
                with open(json_filepath_no_regional, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(summary_without_regional, f, ensure_ascii=False, indent=2)
                
                json_files.append(json_filepath_no_regional)
                logging.info(f"✓ Exported summary without regional to: {json_filepath_no_regional}")

            return json_files

        except Exception as e:
            logging.error(f"Error exporting summary JSON: {e}")
            return None

    def run_report_with_summary(self):
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            if not zpsdt003_data or not brand_data:
                logging.warning("Data zpsdt003 atau brand tidak tersedia.")
                return False

            matching_zpsdt003 = []
            current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')

            for data in zpsdt003_data:
                fromdat = _parse_sap_date(data['fromdat'])
                todat = _parse_sap_date(data['todat'])
                if fromdat and todat and fromdat <= current_date <= todat:
                    matching_zpsdt003.append(data)

            if not matching_zpsdt003:
                logging.warning("Tidak ada data zpsdt003 yang cocok dengan tanggal saat ini.")
                return False

            recipient_emails = self.db_service.get_recipients_from_db()
            total_sent = 0
            national_sent = 0
            regional_sent = 0

            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week = int(zpsdt_data.get('week2', 3))

                matching_brands = [
                    brand for brand in brand_data
                    if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
                ]

                if not matching_brands:
                    continue

                # Merge brands data
                merged_brands = self.merge_matching_brands_data(matching_brands)
                if merged_brands:
                    # Export merged data
                    excel_file = self.export_merged_data_to_excel(
                        merged_brands, cycle_year, cycle
                    )
                    if excel_file:
                        logging.info(f"Merged brands data exported to: {excel_file}")
                    
                    # Export original data
                    original_excel_file = self.export_matching_brands_to_excel(
                        matching_brands, cycle_year, cycle, 
                        f"original_matching_brands_{cycle_year}_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    )
                    if original_excel_file:
                        logging.info(f"Original matching brands exported to: {original_excel_file}")
                    
                    # Export summary data to Excel
                    summary_excel_file = self.export_summary_to_excel(
                        merged_brands, cycle_year, cycle
                    )
                    if summary_excel_file:
                        logging.info(f"Summary data exported to: {summary_excel_file}")
                    
                    # Export summary data to JSON
                    summary_json_files = self.export_summary_json(
                        merged_brands, cycle_year, cycle
                    )
                    if summary_json_files:
                        logging.info(f"Summary JSON files exported: {summary_json_files}")

                previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                
            return True
        except Exception as e:
            logging.error(f"Error during run_report: {e}")
            return False
        
    def generate_regional_report(self, merged_brands, cycle_year, cycle, current_week, regional_desc, current_week2):
        """
        Generate regional report with specific format and calculations
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk regional report.")
                return None

            # Create summaries
            summary_with_regional = self.create_summary_with_regional(merged_brands)
            
            if not summary_with_regional:
                logging.warning("Tidak ada data summary untuk regional report.")
                return None

            # Filter data for specific regional
            regional_data = [item for item in summary_with_regional if item['regional_desc'] == regional_desc]
            
            if not regional_data:
                logging.warning(f"Tidak ada data untuk regional: {regional_desc}")
                return None

            # Calculate omset ideal percentage
            omset_ideal_percentage = (100 / int(current_week)) * int(current_week) if current_week else 0
            
            # Filter data for current week
            current_week_data = [item for item in regional_data if str(item['week1']) == str(current_week)]
            
            # Helper function to safely convert to float
            def safe_float(value):
                try:
                    return float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0

            # PERBAIKAN: Koreksi logika existing vs new brand
            # Existing Brand = prctr_ae != '3998' (bukan 3998)
            # New Brand = prctr_ae == '3998' (adalah 3998)
            
            # Calculate ACH FUF Existing (prctr != 3998) - DIPERBAIKI
            existing_data = [item for item in regional_data if item['prctr_ae'] != '3998']
            existing_current_week = sum(safe_float(item['qty_billing_sum']) for item in existing_data if str(item['week1']) == str(current_week))
            existing_total_billing = sum(safe_float(item['qty_billing_sum']) for item in existing_data)
            existing_total_target = sum(safe_float(item['qty_target_ae']) for item in existing_data)
            existing_percentage = (existing_total_billing / existing_total_target * 100) if existing_total_target > 0 else 0

            # Calculate ACH FUF All Brand (category2 = 'GD')
            gd_data = [item for item in regional_data if item.get('category2') == 'GD' or item.get('category1') == 'GD']
            gd_current_week = sum(safe_float(item['qty_billing_sum']) for item in gd_data if str(item['week1']) == str(current_week))
            gd_total_billing = sum(safe_float(item['qty_billing_sum']) for item in gd_data)
            gd_total_target = sum(safe_float(item['qty_target_ae']) for item in gd_data)
            gd_percentage = (gd_total_billing / gd_total_target * 100) if gd_total_target > 0 else 0

            # Calculate ACH FUF All Brand+PLT (category2 = 'GD' and 'PLT')
            gd_plt_data = [item for item in regional_data if item.get('category2') in ['GD', 'PLT'] or item.get('category1') in ['GD', 'PLT']]
            gd_plt_current_week = sum(safe_float(item['qty_billing_sum']) for item in gd_plt_data if str(item['week1']) == str(current_week))
            gd_plt_total_billing = sum(safe_float(item['qty_billing_sum']) for item in gd_plt_data)
            gd_plt_total_target = sum(safe_float(item['qty_target_ae']) for item in gd_plt_data)
            gd_plt_percentage = (gd_plt_total_billing / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0

            # Get existing brand details (prctr != 3998) - DIPERBAIKI
            existing_by_matkl = {}
            for item in existing_data:
                matkl_desc = item['matkl_desc']
                if matkl_desc not in existing_by_matkl:
                    existing_by_matkl[matkl_desc] = {
                        'current_week_sum': 0,
                        'total_billing': 0,
                        'total_target': 0
                    }
                
                if str(item['week1']) == str(current_week):
                    existing_by_matkl[matkl_desc]['current_week_sum'] += safe_float(item['qty_billing_sum'])
                
                existing_by_matkl[matkl_desc]['total_billing'] += safe_float(item['qty_billing_sum'])
                existing_by_matkl[matkl_desc]['total_target'] += safe_float(item['qty_target_ae'])

            # Calculate new brand data (prctr = 3998) - DIPERBAIKI
            previous_week = str(int(current_week) - 1) if int(current_week) > 1 else '0'
            new_brand_data = {}
            
            for item in regional_data:
                if item['prctr_ae'] == '3998':  # DIPERBAIKI: New brand adalah 3998
                    matkl_desc = item['matkl_desc']
                    week = str(item['week1'])
                    
                    if matkl_desc not in new_brand_data:
                        new_brand_data[matkl_desc] = {
                            'current_week': 0,
                            'previous_week': 0
                        }
                    
                    if week == str(current_week):
                        new_brand_data[matkl_desc]['current_week'] += safe_float(item['qty_billing_sum'])
                    elif week == previous_week:
                        new_brand_data[matkl_desc]['previous_week'] += safe_float(item['qty_billing_sum'])

            # Format report dengan tampilan yang lebih rapi
            report_lines = []
            report_lines.append(f"📊 Report omset weekly W{current_week2} Cycle {cycle} (BOX) {regional_desc} :")
            report_lines.append(f" *Summary {regional_desc} *")
            report_lines.append(f" Cy {cycle} {cycle_year} week {current_week2} omset ideal {omset_ideal_percentage:.0f}% vs FUF")
            report_lines.append("")
            
            # ACH FUF Existing - DIPERBAIKI deskripsi
            report_lines.append(f"% ACH FUF Cy {cycle} (Existing): {existing_current_week:.1f} Box {existing_percentage:.1f}%")
            
            # ACH FUF All Brand
            report_lines.append(f"% ACH FUF Cy {cycle} (All Brand): {gd_current_week:.1f} Box {gd_percentage:.1f}%")
            
            # ACH FUF All Brand+PLT
            report_lines.append(f"% ACH FUF Cy {cycle} (All Brand+PLT): {gd_plt_current_week:.1f} box {gd_plt_percentage:.1f}%")
            
            report_lines.append("")
            report_lines.append("📈 EXISTING BRAND Week 4 vs FUF:")  # DIPERBAIKI deskripsi
            
            # Existing brand details dengan format yang lebih rapi dan sejajar
            if existing_by_matkl:
                for matkl_desc, data in existing_by_matkl.items():
                    percentage = (data['total_billing'] / data['total_target'] * 100) if data['total_target'] > 0 else 0
                    # Format dengan spasi yang konsisten seperti contoh
                    report_lines.append(f"• {matkl_desc:<12} : {data['current_week_sum']:>6.1f} box W4 ({percentage:>2.0f}%)")
            
            report_lines.append("")
            report_lines.append("🆕 NEW BRAND (TW/LW/+/-) :")  # DIPERBAIKI deskripsi
            
            # New brand details dengan format yang lebih rapi dan sejajar
            # Variables untuk grand total
            grand_total_current_week = 0
            grand_total_previous_week = 0
            
            if new_brand_data:
                for matkl_desc, data in new_brand_data.items():
                    difference = data['current_week'] - data['previous_week']
                    sign = "+" if difference >= 0 else ""
                    
                    # Tambahkan ke grand total
                    grand_total_current_week += data['current_week']
                    grand_total_previous_week += data['previous_week']
                    
                    # Format dengan spasi yang konsisten seperti contoh
                    report_lines.append(f"• {matkl_desc:<12} : {data['current_week']:>6.1f} / {data['previous_week']:>6.1f} / {sign}{difference:>6.1f}")
                
                # Tambahkan grand total
                grand_total_difference = grand_total_current_week - grand_total_previous_week
                grand_total_sign = "+" if grand_total_difference >= 0 else ""
                report_lines.append("")
                report_lines.append(f"• {'GRAND TOTAL':<12} : {grand_total_current_week:>6.1f} / {grand_total_previous_week:>6.1f} / {grand_total_sign}{grand_total_difference:>6.1f}")
            else:
                report_lines.append("Tidak ada data new brand untuk periode ini.")

            report_message = "\n".join(report_lines)
            
            logging.info(f"✓ Generated regional report for {regional_desc}")
            return report_message

        except Exception as e:
            logging.error(f"Error generating regional report: {e}")
            return None

    def generate_national_report(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        """
        Generate national report (without regional breakdown)
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk national report.")
                return None

            # Create summary without regional
            summary_without_regional = self.create_summary_without_regional(merged_brands)
            
            if not summary_without_regional:
                logging.warning("Tidak ada data summary untuk national report.")
                return None

            # Calculate omset ideal percentage
            omset_ideal_percentage = (100 / int(current_week)) * int(current_week) if current_week else 0
            
            # Helper function to safely convert to float
            def safe_float(value):
                try:
                    return float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0

            # Calculate ACH FUF Existing (prctr != 3998)
            existing_data = [item for item in summary_without_regional if item['prctr_ae'] != '3998']
            existing_current_week = sum(safe_float(item['qty_billing_sum']) for item in existing_data if str(item['week1']) == str(current_week))
            existing_total_billing = sum(safe_float(item['qty_billing_sum']) for item in existing_data)
            existing_total_target = sum(safe_float(item['qty_target_ae']) for item in existing_data)
            existing_percentage = (existing_total_billing / existing_total_target * 100) if existing_total_target > 0 else 0

            # Calculate ACH FUF All Brand (category2 = 'GD')
            gd_data = [item for item in summary_without_regional if item.get('category2') == 'GD' or item.get('category1') == 'GD']
            gd_current_week = sum(safe_float(item['qty_billing_sum']) for item in gd_data if str(item['week1']) == str(current_week))
            gd_total_billing = sum(safe_float(item['qty_billing_sum']) for item in gd_data)
            gd_total_target = sum(safe_float(item['qty_target_ae']) for item in gd_data)
            gd_percentage = (gd_total_billing / gd_total_target * 100) if gd_total_target > 0 else 0

            # Calculate ACH FUF All Brand+PLT (category2 = 'GD' and 'PLT')
            gd_plt_data = [item for item in summary_without_regional if item.get('category2') in ['GD', 'PLT'] or item.get('category1') in ['GD', 'PLT']]
            gd_plt_current_week = sum(safe_float(item['qty_billing_sum']) for item in gd_plt_data if str(item['week1']) == str(current_week))
            gd_plt_total_billing = sum(safe_float(item['qty_billing_sum']) for item in gd_plt_data)
            gd_plt_total_target = sum(safe_float(item['qty_target_ae']) for item in gd_plt_data)
            gd_plt_percentage = (gd_plt_total_billing / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0

            # Get existing brand details (prctr != 3998)
            existing_by_matkl = {}
            for item in existing_data:
                matkl_desc = item['matkl_desc']
                if matkl_desc not in existing_by_matkl:
                    existing_by_matkl[matkl_desc] = {
                        'current_week_sum': 0,
                        'total_billing': 0,
                        'total_target': 0
                    }
                
                if str(item['week1']) == str(current_week):
                    existing_by_matkl[matkl_desc]['current_week_sum'] += safe_float(item['qty_billing_sum'])
                
                existing_by_matkl[matkl_desc]['total_billing'] += safe_float(item['qty_billing_sum'])
                existing_by_matkl[matkl_desc]['total_target'] += safe_float(item['qty_target_ae'])

            # Calculate new brand data (prctr = 3998)
            previous_week = str(int(current_week) - 1) if int(current_week) > 1 else '0'
            new_brand_data = {}
            
            for item in summary_without_regional:
                if item['prctr_ae'] == '3998':
                    matkl_desc = item['matkl_desc']
                    week = str(item['week1'])
                    
                    if matkl_desc not in new_brand_data:
                        new_brand_data[matkl_desc] = {
                            'current_week': 0,
                            'previous_week': 0
                        }
                    
                    if week == str(current_week):
                        new_brand_data[matkl_desc]['current_week'] += safe_float(item['qty_billing_sum'])
                    elif week == previous_week:
                        new_brand_data[matkl_desc]['previous_week'] += safe_float(item['qty_billing_sum'])

            # Format national report
            report_lines = []
            report_lines.append(f"📊 Report omset weekly W{current_week2} Cycle {cycle} (BOX) NASIONAL :")
            report_lines.append(f" *Summary Nasional* ")
            report_lines.append(f" Cy {cycle} {cycle_year} week {current_week2} omset ideal {omset_ideal_percentage:.0f}% vs FUF")
            report_lines.append("")
            
            # ACH FUF Existing
            report_lines.append(f"% ACH FUF Cy {cycle} (Existing): {existing_current_week:.1f} Box {existing_percentage:.1f}%")
            
            # ACH FUF All Brand
            report_lines.append(f"% ACH FUF Cy {cycle} (All Brand): {gd_current_week:.1f} Box {gd_percentage:.1f}%")
            
            # ACH FUF All Brand+PLT
            report_lines.append(f"% ACH FUF Cy {cycle} (All Brand+PLT): {gd_plt_current_week:.1f} box {gd_plt_percentage:.1f}%")
            
            report_lines.append("")
            report_lines.append("📈 EXISTING BRAND Week 4 vs FUF:")
            
            # Existing brand details
            if existing_by_matkl:
                for matkl_desc, data in existing_by_matkl.items():
                    percentage = (data['total_billing'] / data['total_target'] * 100) if data['total_target'] > 0 else 0
                    report_lines.append(f"• {matkl_desc:<12} : {data['current_week_sum']:>6.1f} box W4 ({percentage:>2.0f}%)")
            
            report_lines.append("")
            report_lines.append("🆕 NEW BRAND (TW/LW/+/-) :")
            
            # New brand details dengan grand total
            # Variables untuk grand total
            grand_total_current_week = 0
            grand_total_previous_week = 0
            
            if new_brand_data:
                for matkl_desc, data in new_brand_data.items():
                    difference = data['current_week'] - data['previous_week']
                    sign = "+" if difference >= 0 else ""
                    
                    # Tambahkan ke grand total
                    grand_total_current_week += data['current_week']
                    grand_total_previous_week += data['previous_week']
                    
                    report_lines.append(f"• {matkl_desc:<12} : {data['current_week']:>6.1f} / {data['previous_week']:>6.1f} / {sign}{difference:>6.1f}")
                
                # Tambahkan grand total
                grand_total_difference = grand_total_current_week - grand_total_previous_week
                grand_total_sign = "+" if grand_total_difference >= 0 else ""
                report_lines.append("")
                report_lines.append(f"• {'GRAND TOTAL':<12} : {grand_total_current_week:>6.1f} / {grand_total_previous_week:>6.1f} / {grand_total_sign}{grand_total_difference:>6.1f}")
            else:
                report_lines.append("Tidak ada data new brand untuk periode ini.")

            report_message = "\n".join(report_lines)
            
            logging.info(f"✓ Generated national report")
            return report_message

        except Exception as e:
            logging.error(f"Error generating national report: {e}")
            return None

    def send_national_report(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        """
        Send national report via WhatsApp and Telegram
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk national report.")
                return False

            # Generate national report
            report_message = self.generate_national_report(
                merged_brands, cycle_year, cycle, current_week, current_week2
            )
            
            if not report_message:
                logging.warning("Gagal generate national report.")
                return False

            success_count = 0
            
            # Send via WhatsApp
            try:
                whatsapp_success = self.whatsapp_service.send_national_report(report_message)
                if whatsapp_success:
                    logging.info(f"✓ WhatsApp national report sent successfully")
                    success_count += 1
                else:
                    logging.warning(f"⚠ Failed to send WhatsApp national report")
            except Exception as e:
                logging.error(f"Error sending WhatsApp national report: {e}")

            # Send via Telegram
            try:
                telegram_success = self.telegram_service.send_message(report_message)
                if telegram_success:
                    logging.info(f"✓ Telegram national report sent successfully")
                    success_count += 1
                else:
                    logging.warning(f"⚠ Failed to send Telegram national report")
            except Exception as e:
                logging.error(f"Error sending Telegram national report: {e}")

            return success_count > 0

        except Exception as e:
            logging.error(f"Error sending national report: {e}")
            return False

    def run_report_with_national_and_regional(self):
        """
        Enhanced version that includes both national and regional reports
        """
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            
            if not zpsdt003_data or not brand_data:
                logging.warning("Data zpsdt003 atau brand tidak tersedia.")
                return False

            matching_zpsdt003 = []
            current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')

            for data in zpsdt003_data:
                fromdat = _parse_sap_date(data['fromdat'])
                todat = _parse_sap_date(data['todat'])
                if fromdat and todat and fromdat <= current_date <= todat:
                    matching_zpsdt003.append(data)

            if not matching_zpsdt003:
                logging.warning("Tidak ada data zpsdt003 yang cocok dengan tanggal saat ini.")
                return False

            total_sent = 0
            national_reports_sent = 0
            regional_reports_sent = 0

            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week2 = int(zpsdt_data.get('week2', 3))
                current_week = int(zpsdt_data.get('week1', 3))

                matching_brands = [
                    brand for brand in brand_data
                    if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
                ]

                if not matching_brands:
                    continue

                # Merge brands data
                merged_brands = self.merge_matching_brands_data(matching_brands)
                if merged_brands:
                    # Export data (existing code)
                    excel_file = self.export_merged_data_to_excel(merged_brands, cycle_year, cycle)
                    if excel_file:
                        logging.info(f"Merged brands data exported to: {excel_file}")
                    
                    original_excel_file = self.export_matching_brands_to_excel(
                        matching_brands, cycle_year, cycle, 
                        f"original_matching_brands_{cycle_year}_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    )
                    if original_excel_file:
                        logging.info(f"Original matching brands exported to: {original_excel_file}")
                    
                    summary_excel_file = self.export_summary_to_excel(merged_brands, cycle_year, cycle)
                    if summary_excel_file:
                        logging.info(f"Summary data exported to: {summary_excel_file}")
                    
                    summary_json_files = self.export_summary_json(merged_brands, cycle_year, cycle)
                    if summary_json_files:
                        logging.info(f"Summary JSON files exported: {summary_json_files}")

                    # Send national report
                    national_success = self.send_national_report(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if national_success:
                        national_reports_sent += 1

                    # Send regional reports
                    regional_success = self.send_regional_reports(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if regional_success:
                        regional_reports_sent += 1

                previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                
            logging.info(f"✓ Total cycles processed:")
            logging.info(f"  - National reports sent: {national_reports_sent}")
            logging.info(f"  - Regional reports sent: {regional_reports_sent}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error during run_report_with_national_and_regional: {e}")
            return False    

    def send_regional_reports(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        """
        Send regional reports via WhatsApp and Telegram
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk regional reports.")
                return False

            # Get unique regional descriptions
            summary_with_regional = self.create_summary_with_regional(merged_brands)
            unique_regionals = list(set(item['regional_desc'] for item in summary_with_regional if item['regional_desc']))

            total_sent = 0
            
            for regional_desc in unique_regionals:
                # Generate report for this regional
                report_message = self.generate_regional_report(
                    merged_brands, cycle_year, cycle, current_week, regional_desc, current_week2
                )
                
                if report_message:
                    # Send via WhatsApp
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
        
    def run_report_with_summary_and_regional(self):
        """
        Enhanced version of run_report_with_summary that includes regional reports
        """
        try:
            zpsdt003_data = self.sap_service.load_zpsdt003_data()
            brand_data = self.sap_service.load_brand_data()
            
            if not zpsdt003_data or not brand_data:
                logging.warning("Data zpsdt003 atau brand tidak tersedia.")
                return False

            matching_zpsdt003 = []
            current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')

            for data in zpsdt003_data:
                fromdat = _parse_sap_date(data['fromdat'])
                todat = _parse_sap_date(data['todat'])
                if fromdat and todat and fromdat <= current_date <= todat:
                    matching_zpsdt003.append(data)

            if not matching_zpsdt003:
                logging.warning("Tidak ada data zpsdt003 yang cocok dengan tanggal saat ini.")
                return False

            total_sent = 0
            regional_reports_sent = 0

            for zpsdt_data in matching_zpsdt003:
                cycle_year = str(zpsdt_data['cycle_year'])
                cycle = str(zpsdt_data['cycle'])
                current_week2 = int(zpsdt_data.get('week2', 3))
                current_week = int(zpsdt_data.get('week1', 3))

                matching_brands = [
                    brand for brand in brand_data
                    if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
                ]

                if not matching_brands:
                    continue

                # Merge brands data
                merged_brands = self.merge_matching_brands_data(matching_brands)
                if merged_brands:
                    # Export merged data
                    excel_file = self.export_merged_data_to_excel(
                        merged_brands, cycle_year, cycle
                    )
                    if excel_file:
                        logging.info(f"Merged brands data exported to: {excel_file}")
                    
                    # Export original data
                    original_excel_file = self.export_matching_brands_to_excel(
                        matching_brands, cycle_year, cycle, 
                        f"original_matching_brands_{cycle_year}_{cycle}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    )
                    if original_excel_file:
                        logging.info(f"Original matching brands exported to: {original_excel_file}")
                    
                    # Export summary data to Excel
                    summary_excel_file = self.export_summary_to_excel(
                        merged_brands, cycle_year, cycle
                    )
                    if summary_excel_file:
                        logging.info(f"Summary data exported to: {summary_excel_file}")
                    
                    # Export summary data to JSON
                    summary_json_files = self.export_summary_json(
                        merged_brands, cycle_year, cycle
                    )
                    if summary_json_files:
                        logging.info(f"Summary JSON files exported: {summary_json_files}")

                    # Send regional reports
                    regional_success = self.send_regional_reports(
                        merged_brands, cycle_year, cycle, current_week, current_week2
                    )
                    if regional_success:
                        regional_reports_sent += 1

                previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
                
            logging.info(f"✓ Total cycles processed with regional reports: {regional_reports_sent}")
            return True
            
        except Exception as e:
            logging.error(f"Error during run_report_with_summary_and_regional: {e}")
            return False

def main():
    app = ReportApp()
    # success = app.run_report_with_summary_and_regional()
    success = app.run_report_with_national_and_regional()
    if success:
        logging.info("✓ Report application completed successfully!")
    else:
        logging.error("X Report application failed!")
    return success


if __name__ == "__main__":
    main()