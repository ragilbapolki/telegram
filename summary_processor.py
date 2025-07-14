from datetime import datetime
import logging
import json
import os

class SummaryProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_summary_with_regional(self, merged_brands):
        """
        Create summary based on: category1, cycle, cycle_year, matkl, matkl_desc, 
        prctr_ae, regional_desc, week1, qty_target_ae
        """
        try:
            if not merged_brands:
                self.logger.warning("No merged brands data to summarize.")
                return []
            
            summary_dict = {}
            
            for brand in merged_brands:
                # Create grouping key
                key = (
                    str(brand.get('category1', '')),
                    str(brand.get('cycle', '')),
                    str(brand.get('cycle_year', '')),
                    str(brand.get('matkl', '')),
                    str(brand.get('matkl_desc', '')),
                    str(brand.get('prctr_ae', '')),
                    str(brand.get('regional_desc', '')),
                    str(brand.get('week1', '')),
                    str(brand.get('qty_target_ae', ''))
                )
                
                if key not in summary_dict:
                    summary_dict[key] = {
                        'category1': str(brand.get('category1', '')),
                        'cycle': str(brand.get('cycle', '')),
                        'cycle_year': str(brand.get('cycle_year', '')),
                        'matkl': str(brand.get('matkl', '')),
                        'matkl_desc': str(brand.get('matkl_desc', '')),
                        'prctr_ae': str(brand.get('prctr_ae', '')),
                        'regional_desc': str(brand.get('regional_desc', '')),
                        'week1': str(brand.get('week1', '')),
                        'qty_target_ae': brand.get('qty_target_ae', 0),
                        'qty_billing_sum': 0,
                        'record_count': 0
                    }
                
                # Sum qty_billing
                qty_billing = brand.get('qty_billing', 0)
                if isinstance(qty_billing, (int, float)):
                    summary_dict[key]['qty_billing_sum'] += qty_billing
                else:
                    try:
                        summary_dict[key]['qty_billing_sum'] += float(qty_billing)
                    except (ValueError, TypeError):
                        pass
                
                summary_dict[key]['record_count'] += 1
            
            # Convert to list
            summary_list = list(summary_dict.values())
            
            self.logger.info(f"Created regional summary with {len(summary_list)} groups from {len(merged_brands)} records")
            return summary_list
            
        except Exception as e:
            self.logger.error(f"Error creating regional summary: {e}")
            return []
    
    def create_summary_without_regional(self, merged_brands):
        """
        Create summary based on: category1, cycle, cycle_year, matkl, matkl_desc, 
        prctr_ae, week1, qty_target_ae (without regional_desc)
        """
        try:
            if not merged_brands:
                self.logger.warning("No merged brands data to summarize.")
                return []
            
            summary_dict = {}
            
            for brand in merged_brands:
                # Create grouping key (without regional_desc)
                key = (
                    str(brand.get('category1', '')),
                    str(brand.get('cycle', '')),
                    str(brand.get('cycle_year', '')),
                    str(brand.get('matkl', '')),
                    str(brand.get('matkl_desc', '')),
                    str(brand.get('prctr_ae', '')),
                    str(brand.get('week1', '')),
                    str(brand.get('qty_target_ae', ''))
                )
                
                if key not in summary_dict:
                    summary_dict[key] = {
                        'category1': str(brand.get('category1', '')),
                        'cycle': str(brand.get('cycle', '')),
                        'cycle_year': str(brand.get('cycle_year', '')),
                        'matkl': str(brand.get('matkl', '')),
                        'matkl_desc': str(brand.get('matkl_desc', '')),
                        'prctr_ae': str(brand.get('prctr_ae', '')),
                        'week1': str(brand.get('week1', '')),
                        'qty_target_ae': brand.get('qty_target_ae', 0),
                        'qty_billing_sum': 0,
                        'record_count': 0
                    }
                
                # Sum qty_billing
                qty_billing = brand.get('qty_billing', 0)
                if isinstance(qty_billing, (int, float)):
                    summary_dict[key]['qty_billing_sum'] += qty_billing
                else:
                    try:
                        summary_dict[key]['qty_billing_sum'] += float(qty_billing)
                    except (ValueError, TypeError):
                        pass
                
                summary_dict[key]['record_count'] += 1
            
            # Convert to list
            summary_list = list(summary_dict.values())
            
            self.logger.info(f"Created non-regional summary with {len(summary_list)} groups from {len(merged_brands)} records")
            return summary_list
            
        except Exception as e:
            self.logger.error(f"Error creating non-regional summary: {e}")
            return []
    
    def export_summaries_to_json(self, regional_summary, non_regional_summary, cycle_year, cycle):
        """
        Export both summaries to JSON files
        """
        try:
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Export regional summary
            regional_filename = f"summary_regional_{cycle_year}_{cycle}_{timestamp}.json"
            regional_filepath = os.path.join(export_dir, regional_filename)
            
            regional_data = {
                'metadata': {
                    'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cycle_year': cycle_year,
                    'cycle': cycle,
                    'summary_type': 'with_regional',
                    'total_records': len(regional_summary)
                },
                'summary': regional_summary
            }
            
            with open(regional_filepath, 'w', encoding='utf-8') as f:
                json.dump(regional_data, f, ensure_ascii=False, indent=2)
            
            # Export non-regional summary
            non_regional_filename = f"summary_non_regional_{cycle_year}_{cycle}_{timestamp}.json"
            non_regional_filepath = os.path.join(export_dir, non_regional_filename)
            
            non_regional_data = {
                'metadata': {
                    'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cycle_year': cycle_year,
                    'cycle': cycle,
                    'summary_type': 'without_regional',
                    'total_records': len(non_regional_summary)
                },
                'summary': non_regional_summary
            }
            
            with open(non_regional_filepath, 'w', encoding='utf-8') as f:
                json.dump(non_regional_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✓ Regional summary exported to: {regional_filepath}")
            self.logger.info(f"✓ Non-regional summary exported to: {non_regional_filepath}")
            
            return regional_filepath, non_regional_filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting summaries to JSON: {e}")
            return None, None
    
    def process_summaries(self, merged_brands, cycle_year, cycle):
        """
        Main method to process both summaries
        """
        try:
            # Create summaries
            regional_summary = self.create_summary_with_regional(merged_brands)
            non_regional_summary = self.create_summary_without_regional(merged_brands)
            
            # Export to JSON
            regional_json, non_regional_json = self.export_summaries_to_json(
                regional_summary, non_regional_summary, cycle_year, cycle
            )
            
            return {
                'regional_summary': regional_summary,
                'non_regional_summary': non_regional_summary,
                'regional_json_path': regional_json,
                'non_regional_json_path': non_regional_json
            }
            
        except Exception as e:
            self.logger.error(f"Error processing summaries: {e}")
            return None