import logging
import pandas as pd
from datetime import datetime
import os
from database_manager import DatabaseManager

class DataProcessor:
    def __init__(self, db_manager: DatabaseManager | None = None):
        # jika tidak disuplai, buat DatabaseManager sendiri
        self.db_manager = db_manager or DatabaseManager()
        
        # Create exports directory if it doesn't exist
        self.export_dir = "exports"
        os.makedirs(self.export_dir, exist_ok=True)

    def export_to_excel(self, data, filename_prefix, sheet_name="Data"):
        """
        Export data to Excel file with timestamp
        """
        try:
            if not data:
                logging.warning(f"Tidak ada data untuk export: {filename_prefix}")
                return None
                
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.xlsx"
            filepath = os.path.join(self.export_dir, filename)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets[sheet_name]
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
            
            logging.info(f"✓ Data exported to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting to Excel: {e}")
            return None

    def export_matching_brands_analysis(self, matching_brands):
        """
        Export analysis of matching brands data before merger
        """
        try:
            if not matching_brands:
                logging.warning("Tidak ada data matching brands untuk analisis.")
                return None

            # Create analysis data
            analysis_data = []
            
            # Create separate lookups for P and T records
            p_records_lookup = {}
            t_records_lookup = {}
            
            for brand in matching_brands:
                source = str(brand.get('source', '')).upper()
                matkl = str(brand.get('matkl', ''))
                cycle = str(brand.get('cycle', ''))
                cycle_year = str(brand.get('cycle_year', ''))
                week1 = str(brand.get('week1', ''))
                
                # Match key: matkl + cycle + cycle_year (tanpa vkgrp)
                match_key = (matkl, cycle, cycle_year, week1)
                
                if source == 'P':
                    if match_key not in p_records_lookup:
                        p_records_lookup[match_key] = []
                    p_records_lookup[match_key].append(brand)
                elif source == 'T':
                    if match_key not in t_records_lookup:
                        t_records_lookup[match_key] = []
                    t_records_lookup[match_key].append(brand)

            # Get all unique match keys
            all_match_keys = set(p_records_lookup.keys()) | set(t_records_lookup.keys())
            
            # Create analysis records
            for match_key in all_match_keys:
                matkl, cycle, cycle_year = match_key
                
                p_records = p_records_lookup.get(match_key, [])
                t_records = t_records_lookup.get(match_key, [])
                
                p_count = len(p_records)
                t_count = len(t_records)
                
                # Determine match status
                if p_count > 0 and t_count > 0:
                    match_status = "BOTH_SOURCES"
                elif p_count > 0:
                    match_status = "P_ONLY"
                elif t_count > 0:
                    match_status = "T_ONLY"
                else:
                    match_status = "NO_DATA"
                
                analysis_record = {
                    'match_key': f"{matkl}|{cycle}|{cycle_year}",
                    'matkl': matkl,
                    'cycle': cycle,
                    'cycle_year': cycle_year,
                    'p_records_count': p_count,
                    't_records_count': t_count,
                    'total_records': p_count + t_count,
                    'match_status': match_status,
                    'can_merge': 'YES' if p_count > 0 and t_count > 0 else 'NO'
                }
                
                # Add sample data from P source
                if p_records:
                    sample_p = p_records[0]
                    analysis_record.update({
                        'p_sample_matkl_desc': sample_p.get('matkl_desc', ''),
                        'p_sample_category1': sample_p.get('category1', ''),
                        'p_sample_regional_desc': sample_p.get('regional_desc', ''),
                        'p_sample_qty_billing_sum': sample_p.get('qty_billing_sum', 0),
                        'p_sample_vkgrp': sample_p.get('vkgrp', '')
                    })
                
                # Add sample data from T source
                if t_records:
                    sample_t = t_records[0]
                    analysis_record.update({
                        't_sample_qty_target_ae': sample_t.get('qty_target_ae', 0),
                        't_sample_prctr_ae': sample_t.get('prctr_ae', ''),
                        't_sample_vkgrp': sample_t.get('vkgrp', '')
                    })
                
                analysis_data.append(analysis_record)
            
            # Sort by match_status and matkl
            analysis_data.sort(key=lambda x: (x['match_status'], x['matkl']))
            
            # Export to Excel
            # filepath = self.export_to_excel(analysis_data, "01_matching_brands_analysis", "Analysis")
            
            # raw_filepath = self.export_to_excel(matching_brands, "01_matching_brands_raw", "Raw_Data")
            
            return {
                # 'analysis_file': filepath,
                # 'raw_file': raw_filepath,
                'analysis_summary': {
                    'total_match_keys': len(all_match_keys),
                    'both_sources': len([x for x in analysis_data if x['match_status'] == 'BOTH_SOURCES']),
                    'p_only': len([x for x in analysis_data if x['match_status'] == 'P_ONLY']),
                    't_only': len([x for x in analysis_data if x['match_status'] == 'T_ONLY']),
                    'total_p_records': len([b for b in matching_brands if b.get('source', '').upper() == 'P']),
                    'total_t_records': len([b for b in matching_brands if b.get('source', '').upper() == 'T'])
                }
            }
            
        except Exception as e:
            logging.error(f"Error in matching brands analysis: {e}")
            return None

    def merge_matching_brands_data(self, matching_brands):
        try:
            if not matching_brands:
                logging.warning("Tidak ada data matching brands untuk dimerge.")
                return []
            # Export analysis before merger
            analysis_result = self.export_matching_brands_analysis(matching_brands)

            grouped_data = {}

            for brand in matching_brands:
                source = str(brand.get('source', '')).upper()
                matkl = str(brand.get('matkl', ''))
                regional_desc = str(brand.get('regional_desc', ''))
                cycle = str(brand.get('cycle', ''))
                week = str(brand.get('week1', ''))  # jika field-nya bernama 'week1'

                match_key = (matkl, regional_desc, cycle, week)

                if match_key not in grouped_data:
                    grouped_data[match_key] = {'P': [], 'T': []}

                grouped_data[match_key][source].append(brand)

            # Merge data with aggregation
            merged_data = []
            merge_stats = {
                'total_groups': len(grouped_data),
                'merged_records': 0,
                'p_only_records': 0,
                't_only_records': 0,
                'successful_matches': 0,
                'failed_matches': 0
            }

            for match_key, group_data in grouped_data.items():
                p_records = group_data['P']
                t_records = group_data['T']

                # unpack 4 elemen sesuai match_key
                matkl, regional_desc, cycle, week = match_key
                match_key_str = f"{matkl}|{regional_desc}|{cycle}|{week}"

                if not p_records and not t_records:
                    continue

                qty_billing_sum = sum(float(p.get('qty_billing_sum', 0) or 0) for p in p_records)
                qty_target_ae = sum(float(t.get('qty_target_ae', 0) or 0) for t in t_records)

                merged_record = {
                    'matkl': matkl,
                    'regional_desc': regional_desc,
                    'cycle': cycle,
                    'week': week,
                    'qty_billing_sum': qty_billing_sum,
                    'qty_target_ae': qty_target_ae,
                    'merge_match_key': match_key_str
                }

                sample_record = p_records[0] if p_records else t_records[0]
                for key, value in sample_record.items():
                    if key not in merged_record and key not in ['source', 'qty_billing_sum', 'qty_target_ae']:
                        merged_record[key] = value

                if p_records and t_records:
                    merged_record['merge_status'] = 'MERGED'
                    merged_record['merge_source_p'] = 'P'
                    merged_record['merge_source_t'] = 'T'
                    merge_stats['merged_records'] += 1
                    merge_stats['successful_matches'] += 1

                elif p_records and not t_records:
                    merged_record['merge_status'] = 'P_ONLY'
                    merged_record['merge_source_p'] = 'P'
                    merged_record['merge_source_t'] = 'NOT_FOUND'
                    merge_stats['p_only_records'] += 1
                    merge_stats['failed_matches'] += 1

                elif t_records and not p_records:
                    merged_record['merge_status'] = 'T_ONLY'
                    merged_record['merge_source_p'] = 'NOT_FOUND'
                    merged_record['merge_source_t'] = 'T'
                    merge_stats['t_only_records'] += 1
                    merge_stats['failed_matches'] += 1

                merged_data.append(merged_record)

            # merged_filepath = self.export_to_excel(merged_data, "02_merged_data", "Merged_Data")
            # if merged_filepath:
            #     logging.info(f"✓ Merged data exported to: {merged_filepath}")
            #     logging.info(f"  - Merge stats: {merge_stats}")
            #     logging.info(f"  - Total output records: {len(merged_data)}")
            #     logging.info(f"  - Match success rate: {merge_stats['successful_matches']}/{merge_stats['successful_matches'] + merge_stats['failed_matches']} groups")

            return merged_data

        except Exception as e:
            logging.error(f"Error merging matching brands data: {e}")
            return []

    def enhance_merged_data_with_orders(self, merged_data):
        try:
            if not merged_data:
                logging.warning("Tidak ada merged data untuk di-enhance.")
                return []

            if not self.db_manager:
                logging.warning("Database manager tidak tersedia.")
                return merged_data

            # Get all brand orders from database
            brand_orders = self.db_manager.get_brand_orders()
            
            # Create lookup dictionary for faster access
            order_lookup = {}
            for brand_order in brand_orders:
                matkl = str(brand_order.get('matkl', ''))
                order_lookup[matkl] = brand_order.get('order', 111)  # Default order 111 if not found
            
            # Enhance merged data with orders
            enhanced_data = []
            for record in merged_data:
                enhanced_record = record.copy()
                matkl = str(record.get('matkl', ''))
                
                # Add order field
                enhanced_record['order'] = order_lookup.get(matkl, 222)
                
                enhanced_data.append(enhanced_record)
            
            # Export enhanced data
            enhanced_filepath = self.export_to_excel(enhanced_data, "03_enhanced_with_orders", "Enhanced_Data")
            if enhanced_filepath:
                logging.info(f"✓ Enhanced data exported to: {enhanced_filepath}")
            
            logging.info(f"✓ Enhanced {len(enhanced_data)} records with brand orders")
            return enhanced_data

        except Exception as e:
            logging.error(f"Error enhancing merged data with orders: {e}")
            return merged_data
    
    def create_summary_with_regional(self, merged_brands):
        try:
            if not merged_brands:
                return []
            
            regional_mappings = self.db_manager.get_regional_mapping()
            if not regional_mappings:
                return []
            
            regional_map = {}
            regional_order_map = {}
            
            for mapping in regional_mappings:
                original_regional = mapping[0]  
                merged_regional = mapping[1]    
                order = mapping[2]             
                
                regional_map[original_regional] = merged_regional
                
                if merged_regional not in regional_order_map:
                    regional_order_map[merged_regional] = order
                else:
                    regional_order_map[merged_regional] = min(regional_order_map[merged_regional], order)
            
            detailed_data_for_excel = []
            
            for brand in merged_brands:
                original_regional = brand.get('regional_desc', '')
                merged_regional = regional_map.get(original_regional, original_regional)
                
                is_merged = original_regional != merged_regional
                merger_group = merged_regional if is_merged else "NO_MERGE"
                merger_status = "MERGED" if is_merged else "ORIGINAL"
                
                detailed_record = {
                    'category1': str(brand.get('category1', '')),
                    'cycle': str(brand.get('cycle', '')),
                    'cycle_year': str(brand.get('cycle_year', '')),
                    'matkl': str(brand.get('matkl', '')),
                    'matkl_desc': str(brand.get('matkl_desc', '')),
                    'category3': str(brand.get('category3', '')),
                    'category5': str(brand.get('category5', '')),
                    'week1': str(brand.get('week1', '')),
                    
                    'original_regional_desc': original_regional,
                    'merged_regional_desc': merged_regional,
                    'regional_order': regional_order_map.get(merged_regional, 9999),
                    
                    'merger_status': merger_status,
                    'merger_group': merger_group,
                    'is_merged': is_merged,
                    
                    'qty_target_ae_original': float(brand.get('qty_target_ae', 0) or 0),
                    'qty_billing_sum_original': float(brand.get('qty_billing_sum', 0) or 0),
                    
                    'record_id': len(detailed_data_for_excel) + 1
                }
                
                detailed_data_for_excel.append(detailed_record)
            
            grouped_data = {}
            
            for record in detailed_data_for_excel:
                key = (
                    record['category1'],
                    record['cycle'],
                    record['cycle_year'],
                    record['matkl'],
                    record['matkl_desc'],
                    record['merged_regional_desc'],
                    record['category3'],
                    record['category5'],
                    record['week1']
                )
                
                if key not in grouped_data:
                    grouped_data[key] = {
                        'category1': record['category1'],
                        'cycle': record['cycle'],
                        'cycle_year': record['cycle_year'],
                        'matkl': record['matkl'],
                        'matkl_desc': record['matkl_desc'],
                        'regional_desc': record['merged_regional_desc'],
                        'category3': record['category3'],
                        'category5': record['category5'],
                        'week1': record['week1'],
                        'qty_target_ae': 0,
                        'qty_billing_sum': 0,
                        'regional_order': record['regional_order'],
                        'record_count': 0,
                        'original_regionals': [],
                        'merger_groups': set(),
                        'has_merged_data': False
                    }
                
                # Accumulate values
                grouped_data[key]['qty_target_ae'] += record['qty_target_ae_original']
                grouped_data[key]['qty_billing_sum'] += record['qty_billing_sum_original']
                grouped_data[key]['record_count'] += 1
                
                # Track originals and merger info
                if record['original_regional_desc'] not in grouped_data[key]['original_regionals']:
                    grouped_data[key]['original_regionals'].append(record['original_regional_desc'])
                
                grouped_data[key]['merger_groups'].add(record['merger_group'])
                
                if record['is_merged']:
                    grouped_data[key]['has_merged_data'] = True
            
            summary_data = []
            for data in grouped_data.values():
                merger_groups_list = list(data['merger_groups'])
                
                if data['has_merged_data']:
                    merger_status = "CONTAINS_MERGED"
                    merger_group = data['regional_desc']  
                else:
                    merger_status = "NO_MERGE"
                    merger_group = "NO_MERGE"
                
                summary_record = {
                    'category1': data['category1'],
                    'cycle': data['cycle'],
                    'cycle_year': data['cycle_year'],
                    'matkl': data['matkl'],
                    'matkl_desc': data['matkl_desc'],
                    'regional_desc': data['regional_desc'],
                    'category3': data['category3'],
                    'category5': data['category5'],
                    'week1': data['week1'],
                    'qty_target_ae': data['qty_target_ae'],
                    'qty_billing_sum': data['qty_billing_sum'],
                    'regional_order': data['regional_order'],
                    'record_count': data['record_count'],
                    
                    # FIELD BARU untuk tracking merger
                    'original_regionals': ', '.join(data['original_regionals']),
                    'merger_status': merger_status,
                    'merger_group': merger_group,
                    'has_merged_data': data['has_merged_data'],
                    'merger_detail': f"Merged from: {', '.join(data['original_regionals'])}" if len(data['original_regionals']) > 1 else "No merge"
                }
                
                summary_data.append(summary_record)
            
            summary_data.sort(key=lambda x: x.get('regional_order', 9999))
            
            # self._export_regional_merger_to_excel(
            #         detailed_data_for_excel, 
            #         summary_data, 
            #         regional_mappings
            #     )
            
            return summary_data
            
        except Exception as e:
            logging.error(f"Error creating summary with merged regional: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def _export_regional_merger_to_excel(self, detailed_data, summary_data, regional_mappings):
        """
        Export regional merger data to Excel with multiple sheets for verification
        """
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"regional_merger_analysis_{timestamp}.xlsx"
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                
                # Sheet 1: Summary Data (Main Results)
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    
                    # Format numerical columns
                    numerical_cols = ['qty_target_ae', 'qty_billing_sum', 'regional_order', 'record_count']
                    for col in numerical_cols:
                        if col in summary_df.columns:
                            summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce').fillna(0)
                    
                    summary_df.to_excel(writer, sheet_name='Summary_Data', index=False)
                    
                    # Auto-adjust column widths for summary
                    worksheet = writer.sheets['Summary_Data']
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
                
                # Sheet 2: Detailed Data (Before Grouping)
                if detailed_data:
                    detailed_df = pd.DataFrame(detailed_data)
                    
                    # Format numerical columns
                    numerical_cols = ['qty_target_ae_original', 'qty_billing_sum_original', 'regional_order', 'record_id']
                    for col in numerical_cols:
                        if col in detailed_df.columns:
                            detailed_df[col] = pd.to_numeric(detailed_df[col], errors='coerce').fillna(0)
                    
                    detailed_df.to_excel(writer, sheet_name='Detailed_Data', index=False)
                    
                    # Auto-adjust column widths for detailed data
                    worksheet = writer.sheets['Detailed_Data']
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
                
                # Sheet 3: Regional Mappings
                if regional_mappings:
                    mapping_data = []
                    for mapping in regional_mappings:
                        mapping_data.append({
                            'Original_Regional': mapping[0],
                            'Merged_Regional': mapping[1],
                            'Order': mapping[2]
                        })
                    
                    mapping_df = pd.DataFrame(mapping_data)
                    mapping_df.to_excel(writer, sheet_name='Regional_Mappings', index=False)
                    
                    # Auto-adjust column widths for mappings
                    worksheet = writer.sheets['Regional_Mappings']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 30)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Sheet 4: Verification Summary
                if summary_data and detailed_data:
                    verification_data = self._create_verification_data(detailed_data, summary_data)
                    if verification_data:
                        verification_df = pd.DataFrame(verification_data)
                        verification_df.to_excel(writer, sheet_name='Verification', index=False)
                        
                        # Auto-adjust column widths for verification
                        worksheet = writer.sheets['Verification']
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 40)
                            worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Sheet 5: Merger Statistics
                if summary_data:
                    stats_data = self._create_merger_statistics(summary_data)
                    if stats_data:
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='Merger_Statistics', index=False)
                        
                        # Auto-adjust column widths for statistics
                        worksheet = writer.sheets['Merger_Statistics']
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 35)
                            worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logging.info(f"Excel file exported successfully: {filename}")
            print(f"Excel file created: {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"Error exporting to Excel: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _create_verification_data(self, detailed_data, summary_data):
        """
        Create verification data to check if sum calculations are correct
        """
        try:
            verification_results = []
            
            # Create a lookup for summary data
            summary_lookup = {}
            for summary in summary_data:
                key = (
                    summary['category1'],
                    summary['cycle'],
                    summary['cycle_year'],
                    summary['matkl'],
                    summary['matkl_desc'],
                    summary['regional_desc'],
                    summary['category3'],
                    summary['category5'],
                    summary['week1']
                )
                summary_lookup[key] = summary
            
            # Group detailed data by the same key
            detailed_groups = {}
            for detail in detailed_data:
                key = (
                    detail['category1'],
                    detail['cycle'],
                    detail['cycle_year'],
                    detail['matkl'],
                    detail['matkl_desc'],
                    detail['merged_regional_desc'],
                    detail['category3'],
                    detail['category5'],
                    detail['week1']
                )
                
                if key not in detailed_groups:
                    detailed_groups[key] = []
                detailed_groups[key].append(detail)
            
            # Verify calculations
            for key, details in detailed_groups.items():
                summary = summary_lookup.get(key)
                if not summary:
                    continue
                    
                # Calculate sums from detailed data
                calculated_qty_target = sum(float(d.get('qty_target_ae_original', 0)) for d in details)
                calculated_qty_billing = sum(float(d.get('qty_billing_sum_original', 0)) for d in details)
                
                # Get summary values
                summary_qty_target = float(summary.get('qty_target_ae', 0))
                summary_qty_billing = float(summary.get('qty_billing_sum', 0))
                
                # Check for discrepancies
                target_diff = abs(calculated_qty_target - summary_qty_target)
                billing_diff = abs(calculated_qty_billing - summary_qty_billing)
                
                verification_results.append({
                    'Regional_Desc': summary['regional_desc'],
                    'Category1': summary['category1'],
                    'Cycle': summary['cycle'],
                    'MATKL': summary['matkl'],
                    'MATKL_Desc': summary['matkl_desc'],
                    'Detail_Records_Count': len(details),
                    'Summary_Record_Count': summary.get('record_count', 0),
                    'Calculated_Qty_Target': round(calculated_qty_target, 2),
                    'Summary_Qty_Target': round(summary_qty_target, 2),
                    'Target_Difference': round(target_diff, 2),
                    'Calculated_Qty_Billing': round(calculated_qty_billing, 2),
                    'Summary_Qty_Billing': round(summary_qty_billing, 2),
                    'Billing_Difference': round(billing_diff, 2),
                    'Has_Discrepancy': target_diff > 0.01 or billing_diff > 0.01,
                    'Merger_Status': summary.get('merger_status', ''),
                    'Original_Regionals': summary.get('original_regionals', '')
                })
            
            return verification_results
            
        except Exception as e:
            logging.error(f"Error creating verification data: {e}")
            return []

    def _create_merger_statistics(self, summary_data):
        """
        Create statistics about the merger process
        """
        try:
            stats = []
            
            # Count by merger status
            merger_status_count = {}
            total_records = len(summary_data)
            total_qty_target = 0
            total_qty_billing = 0
            
            # Regional statistics
            regional_stats = {}
            
            for record in summary_data:
                # Merger status count
                status = record.get('merger_status', 'UNKNOWN')
                merger_status_count[status] = merger_status_count.get(status, 0) + 1
                
                # Total quantities
                total_qty_target += float(record.get('qty_target_ae', 0))
                total_qty_billing += float(record.get('qty_billing_sum', 0))
                
                # Regional statistics
                regional = record.get('regional_desc', 'UNKNOWN')
                if regional not in regional_stats:
                    regional_stats[regional] = {
                        'count': 0,
                        'qty_target': 0,
                        'qty_billing': 0,
                        'has_merged': record.get('has_merged_data', False)
                    }
                
                regional_stats[regional]['count'] += 1
                regional_stats[regional]['qty_target'] += float(record.get('qty_target_ae', 0))
                regional_stats[regional]['qty_billing'] += float(record.get('qty_billing_sum', 0))
            
            # Overall statistics
            stats.append({
                'Statistic_Type': 'OVERALL',
                'Description': 'Total Records',
                'Count': total_records,
                'Percentage': 100.0,
                'Qty_Target_Sum': round(total_qty_target, 2),
                'Qty_Billing_Sum': round(total_qty_billing, 2)
            })
            
            # Merger status statistics
            for status, count in merger_status_count.items():
                percentage = (count / total_records * 100) if total_records > 0 else 0
                stats.append({
                    'Statistic_Type': 'MERGER_STATUS',
                    'Description': f'Status: {status}',
                    'Count': count,
                    'Percentage': round(percentage, 2),
                    'Qty_Target_Sum': '',
                    'Qty_Billing_Sum': ''
                })
            
            # Regional statistics
            for regional, data in regional_stats.items():
                percentage = (data['count'] / total_records * 100) if total_records > 0 else 0
                stats.append({
                    'Statistic_Type': 'REGIONAL',
                    'Description': f'Regional: {regional}',
                    'Count': data['count'],
                    'Percentage': round(percentage, 2),
                    'Qty_Target_Sum': round(data['qty_target'], 2),
                    'Qty_Billing_Sum': round(data['qty_billing'], 2)
                })
            
            return stats
            
        except Exception as e:
            logging.error(f"Error creating merger statistics: {e}")
            return []

    def create_summary_without_regional(self, merged_brands):
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk summary.")
                return []

            # Group by required fields (without regional_desc)
            grouped_data = {}
            enhanced_merged_data = self.enhance_merged_data_with_orders(merged_brands)
            
            for brand in enhanced_merged_data:
                # Process category3
                category3 = str(brand.get('category3', ''))
                
                # Create grouping key (without regional_desc)
                key = (
                    str(brand.get('category1', '')),
                    str(brand.get('cycle', '')),
                    str(brand.get('cycle_year', '')),
                    str(brand.get('matkl', '')),
                    str(brand.get('matkl_desc', '')),
                    str(brand.get('week1', '')),
                    str(brand.get('qty_target_ae', '')),
                    str(brand.get('category3', '')),
                    str(brand.get('category5', ''))
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
                        'category3': str(brand.get('category3', '')),
                        'category5': str(brand.get('category5', '')),
                        'order': brand.get('order', 555),  # Include order field
                        'record_count': 0
                    }
                
                # Sum qty_billing_sum
                grouped_data[key]['qty_billing_sum'] += float(brand.get('qty_billing_sum', 0) or 0)
                grouped_data[key]['record_count'] += 1
                
                # Keep the minimum order (for sorting purposes)
                current_order = grouped_data[key]['order']
                brand_order = brand.get('order', 666)
                if brand_order < current_order:
                    grouped_data[key]['order'] = brand_order

            # Convert to list and sort by order
            summary_data = list(grouped_data.values())
            summary_data.sort(key=lambda x: x['order'])
            
            logging.info(f"✓ Created summary without regional: {len(summary_data)} records from {len(merged_brands)} original records")
            return summary_data

        except Exception as e:
            logging.error(f"Error creating summary without regional: {e}")
            return []

    def export_all_results(self, results):
        """
        Export all results to a single Excel file with multiple sheets
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"06_complete_results_{timestamp}.xlsx"
            filepath = os.path.join(self.export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Export each result to different sheets
                if results.get('enhanced_merged_data'):
                    df_enhanced = pd.DataFrame(results['enhanced_merged_data'])
                    df_enhanced.to_excel(writer, sheet_name='Enhanced_Merged', index=False)
                
                if results.get('summary_with_regional'):
                    df_regional = pd.DataFrame(results['summary_with_regional'])
                    df_regional.to_excel(writer, sheet_name='Summary_Regional', index=False)
                
                if results.get('summary_without_regional'):
                    df_no_regional = pd.DataFrame(results['summary_without_regional'])
                    df_no_regional.to_excel(writer, sheet_name='Summary_No_Regional', index=False)
                
                # Auto-adjust column widths for all sheets
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
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
            
            logging.info(f"✓ Complete results exported to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting complete results: {e}")
            return None

    def process_complete_workflow(self, matching_brands):
        try:
            merged_data = self.merge_matching_brands_data(matching_brands)
            if not merged_data:
                return {
                    'enhanced_merged_data': [],
                    'summary_with_regional': [],
                    'summary_without_regional': []
                }
            
            enhanced_merged_data = self.enhance_merged_data_with_orders(merged_data)
            
            summary_with_regional = self.create_summary_with_regional(enhanced_merged_data)
            summary_without_regional = self.create_summary_without_regional(enhanced_merged_data)
            
            # Step 4: Export all results in one file
            results = {
                'enhanced_merged_data': enhanced_merged_data,
                'summary_with_regional': summary_with_regional,
                'summary_without_regional': summary_without_regional
            }
            
            complete_filepath = self.export_all_results(results)
            if complete_filepath:
                logging.info(f"✓ Complete workflow results exported to: {complete_filepath}")
            
            return results
            
        except Exception as e:
            logging.error(f"Error in complete workflow: {e}")
            return {
                'enhanced_merged_data': [],
                'summary_with_regional': [],
                'summary_without_regional': []
            }
    