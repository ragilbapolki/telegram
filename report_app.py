# Add these imports to your existing ReportApp
from summary_processor import SummaryProcessor
from excel_exporter import ExcelExporter

# Add these methods to your existing ReportApp class:

def export_summaries_for_merged_brands(self, merged_brands, cycle_year, cycle):
    """
    Create and export summaries for merged brands data
    """
    try:
        if not merged_brands:
            
            previous_week_data = self.sap_service.get_previous_week_data(current_week, cycle, cycle_year)
        
        # Generate consolidated summary report
        if all_summary_results:
            self.generate_consolidated_summary_report(all_summary_results)
        
        return True
        
    except Exception as e:
        logging.error(f"Error during run_report_with_summaries: {e}")
        return False

def generate_consolidated_summary_report(self, all_summary_results):
    """
    Generate a consolidated report for all cycle summaries
    """
    try:
        if not all_summary_results:
            logging.warning("No summary results to consolidate.")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"consolidated_summary_report_{timestamp}.xlsx"
        
        export_dir = "exports"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        filepath = os.path.join(export_dir, filename)
        
        # Prepare consolidated data
        all_regional_data = []
        all_non_regional_data = []
        cycle_summary = []
        
        for result in all_summary_results:
            cycle_year = result['cycle_year']
            cycle = result['cycle']
            results = result['results']
            
            # Add cycle info to each record
            for item in results['regional_summary']:
                item_copy = item.copy()
                item_copy['source_cycle_year'] = cycle_year
                item_copy['source_cycle'] = cycle
                all_regional_data.append(item_copy)
            
            for item in results['non_regional_summary']:
                item_copy = item.copy()
                item_copy['source_cycle_year'] = cycle_year
                item_copy['source_cycle'] = cycle
                all_non_regional_data.append(item_copy)
            
            # Create cycle summary
            cycle_summary.append({
                'cycle_year': cycle_year,
                'cycle': cycle,
                'regional_records': len(results['regional_summary']),
                'non_regional_records': len(results['non_regional_summary']),
                'regional_qty_billing_sum': sum(item.get('qty_billing_sum', 0) for item in results['regional_summary']),
                'non_regional_qty_billing_sum': sum(item.get('qty_billing_sum', 0) for item in results['non_regional_summary']),
                'regional_qty_target_sum': sum(item.get('qty_target_ae', 0) for item in results['regional_summary']),
                'non_regional_qty_target_sum': sum(item.get('qty_target_ae', 0) for item in results['non_regional_summary'])
            })
        
        # Create metadata
        metadata = {
            'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'Report Type': ['Consolidated Summary Report'],
            'Total Cycles': [len(all_summary_results)],
            'Total Regional Records': [len(all_regional_data)],
            'Total Non-Regional Records': [len(all_non_regional_data)],
            'Grand Total Qty Billing (Regional)': [sum(item.get('qty_billing_sum', 0) for item in all_regional_data)],
            'Grand Total Qty Billing (Non-Regional)': [sum(item.get('qty_billing_sum', 0) for item in all_non_regional_data)],
            'Grand Total Qty Target (Regional)': [sum(item.get('qty_target_ae', 0) for item in all_regional_data)],
            'Grand Total Qty Target (Non-Regional)': [sum(item.get('qty_target_ae', 0) for item in all_non_regional_data)]
        }
        
        # Export to Excel
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Consolidated regional data
            if all_regional_data:
                regional_df = pd.DataFrame(all_regional_data)
                regional_df.to_excel(writer, sheet_name='All Regional Summary', index=False)
            
            # Consolidated non-regional data
            if all_non_regional_data:
                non_regional_df = pd.DataFrame(all_non_regional_data)
                non_regional_df.to_excel(writer, sheet_name='All Non-Regional Summary', index=False)
            
            # Cycle summary
            if cycle_summary:
                cycle_df = pd.DataFrame(cycle_summary)
                cycle_df.to_excel(writer, sheet_name='Cycle Summary', index=False)
            
            # Metadata
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Apply formatting
        excel_exporter = ExcelExporter()
        excel_exporter._apply_advanced_formatting(filepath)
        
        logging.info(f"✓ Consolidated summary report generated: {filepath}")
        logging.info(f"  - Total cycles: {len(all_summary_results)}")
        logging.info(f"  - Total regional records: {len(all_regional_data)}")
        logging.info(f"  - Total non-regional records: {len(all_non_regional_data)}")
        
        return filepath
        
    except Exception as e:
        logging.error(f"Error generating consolidated summary report: {e}")
        return None

def get_summary_statistics(self, merged_brands):
    """
    Get basic statistics for merged brands data
    """
    try:
        if not merged_brands:
            return {}
        
        stats = {
            'total_records': len(merged_brands),
            'total_qty_billing': sum(item.get('qty_billing', 0) for item in merged_brands),
            'total_qty_target': sum(item.get('qty_target_ae', 0) for item in merged_brands),
            'unique_categories': len(set(item.get('category1', '') for item in merged_brands)),
            'unique_matkl': len(set(item.get('matkl', '') for item in merged_brands)),
            'unique_prctr': len(set(item.get('prctr_ae', '') for item in merged_brands)),
            'merge_status_counts': {}
        }
        
        # Count merge statuses
        for item in merged_brands:
            status = item.get('merge_status', 'UNKNOWN')
            stats['merge_status_counts'][status] = stats['merge_status_counts'].get(status, 0) + 1
        
        return stats
        
    except Exception as e:
        logging.error(f"Error getting summary statistics: {e}")
        return {}

def export_summary_by_category(self, merged_brands, cycle_year, cycle):
    """
    Export summary grouped by category1
    """
    try:
        if not merged_brands:
            logging.warning("No merged brands data to summarize by category.")
            return None
        
        # Group by category1
        category_summary = {}
        
        for brand in merged_brands:
            category = str(brand.get('category1', 'Unknown'))
            
            if category not in category_summary:
                category_summary[category] = {
                    'category1': category,
                    'record_count': 0,
                    'qty_billing_sum': 0,
                    'qty_target_sum': 0,
                    'unique_matkl': set(),
                    'unique_prctr': set(),
                    'merge_status_counts': {}
                }
            
            category_summary[category]['record_count'] += 1
            category_summary[category]['qty_billing_sum'] += brand.get('qty_billing', 0)
            category_summary[category]['qty_target_sum'] += brand.get('qty_target_ae', 0)
            category_summary[category]['unique_matkl'].add(str(brand.get('matkl', '')))
            category_summary[category]['unique_prctr'].add(str(brand.get('prctr_ae', '')))
            
            status = brand.get('merge_status', 'UNKNOWN')
            category_summary[category]['merge_status_counts'][status] = \
                category_summary[category]['merge_status_counts'].get(status, 0) + 1
        
        # Convert to list and clean up sets
        category_list = []
        for category, data in category_summary.items():
            clean_data = data.copy()
            clean_data['unique_matkl_count'] = len(data['unique_matkl'])
            clean_data['unique_prctr_count'] = len(data['unique_prctr'])
            clean_data['merged_count'] = data['merge_status_counts'].get('MERGED', 0)
            clean_data['p_only_count'] = data['merge_status_counts'].get('P_ONLY', 0)
            clean_data['t_only_count'] = data['merge_status_counts'].get('T_ONLY', 0)
            
            # Remove sets and dict for Excel export
            del clean_data['unique_matkl']
            del clean_data['unique_prctr']
            del clean_data['merge_status_counts']
            
            category_list.append(clean_data)
        
        # Export to Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"category_summary_{cycle_year}_{cycle}_{timestamp}.xlsx"
        
        export_dir = "exports"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        filepath = os.path.join(export_dir, filename)
        
        # Create metadata
        metadata = {
            'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'Report Type': ['Category Summary'],
            'Cycle Year': [cycle_year],
            'Cycle': [cycle],
            'Total Categories': [len(category_list)],
            'Total Records': [sum(item['record_count'] for item in category_list)],
            'Total Qty Billing': [sum(item['qty_billing_sum'] for item in category_list)],
            'Total Qty Target': [sum(item['qty_target_sum'] for item in category_list)]
        }
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Export category summary
            category_df = pd.DataFrame(category_list)
            category_df.to_excel(writer, sheet_name='Category Summary', index=False)
            
            # Export metadata
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        # Apply formatting
        excel_exporter = ExcelExporter()
        excel_exporter._apply_advanced_formatting(filepath)
        
        logging.info(f"✓ Category summary exported to: {filepath}")
        logging.info(f"  - Total categories: {len(category_list)}")
        
        return filepath
        
    except Exception as e:
        logging.error(f"Error exporting category summary: {e}")
        return None

# Update the main function to use the new method
def main():
    app = ReportApp()
    success = app.run_report_with_summaries()  # Use the enhanced method
    if success:
        logging.info("✓ Report application with summaries completed successfully!")
    else:
        logging.error("X Report application with summaries failed!")
    return successlogging.warning("No merged brands data to create summaries.")
            return None
        
        # Initialize processors
        summary_processor = SummaryProcessor()
        excel_exporter = ExcelExporter()
        
        # Process summaries
        summary_results = summary_processor.process_summaries(merged_brands, cycle_year, cycle)
        
        if not summary_results:
            logging.error("Failed to process summaries.")
            return None
        
        # Export to Excel
        excel_file = excel_exporter.export_summaries_to_excel(
            summary_results['regional_summary'],
            summary_results['non_regional_summary'],
            cycle_year,
            cycle
        )
        
        # Export individual summaries if needed
        regional_excel = excel_exporter.export_individual_summary(
            summary_results['regional_summary'],
            "Regional Summary",
            cycle_year,
            cycle
        )
        
        non_regional_excel = excel_exporter.export_individual_summary(
            summary_results['non_regional_summary'],
            "Non-Regional Summary",
            cycle_year,
            cycle
        )
        
        logging.info(f"✓ Summary processing completed:")
        logging.info(f"  - Combined Excel: {excel_file}")
        logging.info(f"  - Regional Excel: {regional_excel}")
        logging.info(f"  - Non-Regional Excel: {non_regional_excel}")
        logging.info(f"  - Regional JSON: {summary_results['regional_json_path']}")
        logging.info(f"  - Non-Regional JSON: {summary_results['non_regional_json_path']}")
        
        return {
            'combined_excel': excel_file,
            'regional_excel': regional_excel,
            'non_regional_excel': non_regional_excel,
            'regional_json': summary_results['regional_json_path'],
            'non_regional_json': summary_results['non_regional_json_path'],
            'regional_summary': summary_results['regional_summary'],
            'non_regional_summary': summary_results['non_regional_summary']
        }
        
    except Exception as e:
        logging.error(f"Error exporting summaries for merged brands: {e}")
        return None

def run_report_with_summaries(self):
    """
    Enhanced run_report that includes summary generation
    """
    try:
        # Run the existing report logic
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
        
        all_summary_results = []

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

            # Generate merged brands
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
                
                # NEW: Generate summaries
                summary_results = self.export_summaries_for_merged_brands(
                    merged_brands, cycle_year, cycle
                )
                
                if summary_results:
                    all_summary_results.append({
                        'cycle_year': cycle_year,
                        'cycle': cycle,
                        'results': summary_results
                    })
                    
                    logging.info(f"✓ Summaries generated for cycle {cycle_year}-{cycle}")
                else:
                    logging.warning(f"Failed to generate summaries for cycle {cycle_year}-{cycle}")