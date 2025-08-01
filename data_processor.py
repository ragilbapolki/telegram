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

    def merge_matching_brands_data(self, matching_brands, cycle_year):
        try:
            if not matching_brands:
                logging.warning("Tidak ada data matching brands untuk dimerge.")
                return []
            
            # STEP 1: Export raw data awal untuk pengecekan
            # logging.info("STEP 1: Exporting raw matching brands data...")
            # raw_data_filepath = self.export_to_excel(
            #     matching_brands, 
            #     f"01_raw_data_{cycle_year}", 
            #     f"Raw_Data_{cycle_year}"
            # )
            # if raw_data_filepath:
            #     logging.info(f"Raw data exported to: {raw_data_filepath}")

            # Export analysis before merger
            analysis_result = self.export_matching_brands_analysis(matching_brands)

            # Get brand orders from database for enhancement
            order_lookup = {}
            if self.db_manager:
                try:
                    brand_orders = self.db_manager.get_brand_orders()
                    
                    for i, brand_order in enumerate(brand_orders):
                        if isinstance(brand_order, tuple):
                            if len(brand_order) >= 2:
                                matkl = str(brand_order[1]) if brand_order[1] is not None else ''  # matkl is at index 1
                                
                                order_value = 111  # default
                                
                                for idx in [0, 3, 4, 5]:  # Check common positions for order field
                                    if idx < len(brand_order) and brand_order[idx] is not None:
                                        try:
                                            potential_order = int(brand_order[idx])
                                            if 1 <= potential_order <= 999:  # Reasonable order range
                                                order_value = potential_order
                                                if i < 3:
                                                    logging.info(f"DEBUG: Found order {order_value} at index {idx}")
                                                break
                                        except (ValueError, TypeError):
                                            continue
                                
                            else:
                                logging.warning(f"DEBUG: Unexpected tuple length: {len(brand_order)}")
                                continue
                        elif isinstance(brand_order, dict):
                            # Dictionary format
                            matkl = str(brand_order.get('matkl', ''))
                            order_value = brand_order.get('order', 111)
                        else:
                            logging.warning(f"DEBUG: Unexpected brand_order type: {type(brand_order)}")
                            continue
                        
                        if matkl:  # Only add if matkl is not empty
                            order_lookup[matkl] = order_value
                            
                            if len(order_lookup) <= 5:
                                logging.info(f"DEBUG: Added to lookup - matkl: '{matkl}' -> order: {order_value}")
                    
                    sample_keys = list(order_lookup.keys())[:5]
                    logging.info(f"DEBUG: Sample lookup keys: {sample_keys}")
                    
                except Exception as e:
                    logging.error(f"DEBUG: Exception details: {str(e)}")
            else:
                logging.warning("Database manager tidak tersedia untuk brand orders.")

            # STEP 2: Filter and group data with cycle_year validation
            logging.info(f"STEP 2: Filtering data for cycle_year: {cycle_year}")
            
            # Filter data berdasarkan cycle_year
            filtered_brands = []
            for brand in matching_brands:
                brand_cycle_year = str(brand.get('cycle_year', ''))
                if brand_cycle_year == str(cycle_year):
                    filtered_brands.append(brand)
            
            # logging.info(f"Filtered {len(filtered_brands)} records from {len(matching_brands)} total records for cycle_year {cycle_year}")
            
            # # Export filtered data
            # filtered_data_filepath = self.export_to_excel(
            #     filtered_brands, 
            #     f"02_filtered_data_{cycle_year}", 
            #     f"Filtered_Data_{cycle_year}"
            # )
            # if filtered_data_filepath:
            #     logging.info(f"Filtered data exported to: {filtered_data_filepath}")

            # Group filtered data
            grouped_data = {}
            grouping_debug = []

            for brand in filtered_brands:
                source = str(brand.get('source', '')).upper()
                matkl = str(brand.get('matkl', ''))
                regional_desc = str(brand.get('regional_desc', ''))
                cycle = str(brand.get('cycle', ''))
                week = str(brand.get('week1', ''))  # jika field-nya bernama 'week1'
                cycle_year_check = str(brand.get('cycle_year', ''))

                match_key = (matkl, regional_desc, cycle, week)

                if match_key not in grouped_data:
                    grouped_data[match_key] = {'P': [], 'T': []}

                grouped_data[match_key][source].append(brand)
                
                # Debug info untuk grouping
                if len(grouping_debug) < 10:  # Simpan 10 record pertama untuk debug
                    grouping_debug.append({
                        'source': source,
                        'matkl': matkl,
                        'regional_desc': regional_desc,
                        'cycle': cycle,
                        'week': week,
                        'cycle_year': cycle_year_check,
                        'match_key': f"{matkl}|{regional_desc}|{cycle}|{week}"
                    })

            # STEP 3: Export grouping debug info
            # grouping_debug_filepath = self.export_to_excel(
            #     grouping_debug, 
            #     f"03_grouping_debug_{cycle_year}", 
            #     f"Grouping_Debug_{cycle_year}"
            # )
            # if grouping_debug_filepath:
            #     logging.info(f"Grouping debug data exported to: {grouping_debug_filepath}")

            # STEP 4: Merge data with aggregation and brand orders enhancement
            logging.info("STEP 4: Merging grouped data...")
            merged_data = []
            merge_stats = {
                'total_groups': len(grouped_data),
                'merged_records': 0,
                'p_only_records': 0,
                't_only_records': 0,
                'successful_matches': 0,
                'failed_matches': 0,
                'enhanced_with_orders': 0,
                'default_orders_used': 0,
                'cycle_year_mismatches': 0
            }

            pre_merge_debug = []
            debug_counter = 0
            
            for match_key, group_data in grouped_data.items():
                p_records = group_data['P']
                t_records = group_data['T']

                # unpack 4 elemen sesuai match_key
                matkl, regional_desc, cycle, week = match_key
                match_key_str = f"{matkl}|{regional_desc}|{cycle}|{week}"

                if not p_records and not t_records:
                    continue

                # PERBAIKAN: Filter qty_target_ae berdasarkan cycle_year yang sama
                qty_billing_sum = sum(float(p.get('qty_billing_sum', 0) or 0) for p in p_records)
                
                # Filter T records berdasarkan cycle_year sebelum sum qty_target_ae
                valid_t_records = []
                for t_record in t_records:
                    t_cycle_year = str(t_record.get('cycle_year', ''))
                    if t_cycle_year == str(cycle_year):
                        valid_t_records.append(t_record)
                    else:
                        merge_stats['cycle_year_mismatches'] += 1
                        logging.warning(f"Cycle year mismatch: expected {cycle_year}, got {t_cycle_year} for matkl {matkl}")
                
                qty_target_ae = sum(float(t.get('qty_target_ae', 0) or 0) for t in valid_t_records)

                merged_record = {
                    'matkl': matkl,
                    'regional_desc': regional_desc,
                    'cycle': cycle,
                    'week': week,
                    'cycle_year': cycle_year,  # Tambahkan cycle_year ke merged record
                    'qty_billing_sum': qty_billing_sum,
                    'qty_target_ae': qty_target_ae,
                    'merge_match_key': match_key_str,
                    'p_records_count': len(p_records),
                    't_records_count': len(t_records),
                    'valid_t_records_count': len(valid_t_records)  # Jumlah T records yang valid cycle_year
                }

                # DEBUG: Enhanced brand order lookup with detailed logging
                debug_counter += 1
                if debug_counter <= 10:  # Log 10 record pertama untuk debug
                    pre_merge_debug.append({
                        'debug_record_no': debug_counter,
                        'matkl': matkl,
                        'matkl_type': str(type(matkl)),
                        'matkl_in_lookup': matkl in order_lookup,
                        'p_records_count': len(p_records),
                        't_records_count': len(t_records),
                        'valid_t_records_count': len(valid_t_records),
                        'qty_billing_sum': qty_billing_sum,
                        'qty_target_ae': qty_target_ae,
                        'cycle_year_filter': cycle_year
                    })
                    
                    # if matkl in order_lookup:
                    #     logging.info(f"DEBUG Record {debug_counter}: Found order = {order_lookup[matkl]}")
                    # else:
                    #     # Check if there are similar keys
                    #     similar_keys = [k for k in order_lookup.keys() if matkl.lower() in k.lower() or k.lower() in matkl.lower()]
                    #     logging.info(f"DEBUG Record {debug_counter}: Similar keys found: {similar_keys[:3]}")

                brand_order = order_lookup.get(matkl, 222)  # Default 222 if not found
                merged_record['order'] = brand_order
                
                if brand_order != 222:  # If found in brand orders
                    merge_stats['enhanced_with_orders'] += 1
                else:
                    merge_stats['default_orders_used'] += 1

                sample_record = p_records[0] if p_records else (valid_t_records[0] if valid_t_records else t_records[0])
                for key, value in sample_record.items():
                    if key not in merged_record and key not in ['source', 'qty_billing_sum', 'qty_target_ae']:
                        merged_record[key] = value

                # Update merge status logic untuk consider valid T records
                if p_records and valid_t_records:
                    merged_record['merge_status'] = 'MERGED'
                    merged_record['merge_source_p'] = 'P'
                    merged_record['merge_source_t'] = 'T'
                    merge_stats['merged_records'] += 1
                    merge_stats['successful_matches'] += 1

                elif p_records and not valid_t_records:
                    merged_record['merge_status'] = 'P_ONLY'
                    merged_record['merge_source_p'] = 'P'
                    merged_record['merge_source_t'] = 'NOT_FOUND' if not t_records else 'INVALID_CYCLE_YEAR'
                    merge_stats['p_only_records'] += 1
                    merge_stats['failed_matches'] += 1

                elif valid_t_records and not p_records:
                    merged_record['merge_status'] = 'T_ONLY'
                    merged_record['merge_source_p'] = 'NOT_FOUND'
                    merged_record['merge_source_t'] = 'T'
                    merge_stats['t_only_records'] += 1
                    merge_stats['failed_matches'] += 1

                merged_data.append(merged_record)

            # STEP 5: Export pre-merge debug info
            # pre_merge_debug_filepath = self.export_to_excel(
            #     pre_merge_debug, 
            #     f"04_pre_merge_debug_{cycle_year}", 
            #     f"Pre_Merge_Debug_{cycle_year}"
            # )
            # if pre_merge_debug_filepath:
            #     logging.info(f"Pre-merge debug data exported to: {pre_merge_debug_filepath}")

            # STEP 6: Export final merged data
            # merged_filepath = self.export_to_excel(
            #     merged_data, 
            #     f"05_final_merged_{cycle_year}", 
            #     f"Final_Merged_Data_{cycle_year}"
            # )
            # if merged_filepath:
            #     logging.info(f"Final merged data exported to: {merged_filepath}")
            #     logging.info(f"MERGE STATS for cycle_year {cycle_year}:")
            #     logging.info(f"  - Total groups processed: {merge_stats['total_groups']}")
            #     logging.info(f"  - Successful matches: {merge_stats['successful_matches']}")
            #     logging.info(f"  - Failed matches: {merge_stats['failed_matches']}")
            #     logging.info(f"  - Match success rate: {merge_stats['successful_matches']}/{merge_stats['successful_matches'] + merge_stats['failed_matches']} groups")
            #     logging.info(f"  - Records with brand orders: {merge_stats['enhanced_with_orders']}")
            #     logging.info(f"  - Records with default orders: {merge_stats['default_orders_used']}")
            #     logging.info(f"  - Cycle year mismatches: {merge_stats['cycle_year_mismatches']}")

            # STEP 7: Export merge statistics summary
            merge_summary = [{
                'cycle_year': cycle_year,
                'raw_records_count': len(matching_brands),
                'filtered_records_count': len(filtered_brands),
                'total_groups': merge_stats['total_groups'],
                'merged_records': merge_stats['merged_records'],
                'p_only_records': merge_stats['p_only_records'],
                't_only_records': merge_stats['t_only_records'],
                'successful_matches': merge_stats['successful_matches'],
                'failed_matches': merge_stats['failed_matches'],
                'enhanced_with_orders': merge_stats['enhanced_with_orders'],
                'default_orders_used': merge_stats['default_orders_used'],
                'cycle_year_mismatches': merge_stats['cycle_year_mismatches'],
                'match_success_rate': f"{merge_stats['successful_matches']}/{merge_stats['successful_matches'] + merge_stats['failed_matches']}" if (merge_stats['successful_matches'] + merge_stats['failed_matches']) > 0 else "0/0"
            }]
            
            # summary_filepath = self.export_to_excel(
            #     merge_summary, 
            #     f"06_merge_summary_{cycle_year}", 
            #     f"Merge_Summary_{cycle_year}"
            # )
            # if summary_filepath:
            #     logging.info(f"Merge summary exported to: {summary_filepath}")

            return merged_data

        except Exception as e:
            logging.error(f"Error merging matching brands data: {e}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
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
            # enhanced_filepath = self.export_to_excel(enhanced_data, "03_enhanced_with_orders", "Enhanced_Data")
            # if enhanced_filepath:
            #     logging.info(f"✓ Enhanced data exported to: {enhanced_filepath}")
            
            # logging.info(f"✓ Enhanced {len(enhanced_data)} records with brand orders")
            # return enhanced_data

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
    
    def create_summary_with_sales_office(self, merged_brands):
        """
        Create summary data grouped by sales office (vkbur_desc)
        Similar to create_summary_with_regional but for sales office level
        """
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk summary sales office.")
                return []
            
            # Get sales office mappings from database (if any mapping exists)
            sales_office_mappings = []
            if self.db_manager:
                try:
                    # Assuming there's a method to get sales office mappings
                    # If not available, we'll use direct mapping
                    sales_office_mappings = self.db_manager.get_sales_office_mapping()
                except AttributeError:
                    logging.info("No sales office mapping method available, using direct mapping")
                    sales_office_mappings = []
            
            # Create mapping dictionaries
            sales_office_map = {}
            sales_office_order_map = {}
            
            if sales_office_mappings:
                # If mappings exist in database
                for mapping in sales_office_mappings:
                    original_sales_office = mapping[0]  # original vkbur_desc
                    merged_sales_office = mapping[1]    # mapped vkbur_desc
                    order = mapping[2]                  # order for sorting
                    
                    sales_office_map[original_sales_office] = merged_sales_office
                    
                    if merged_sales_office not in sales_office_order_map:
                        sales_office_order_map[merged_sales_office] = order
                    else:
                        sales_office_order_map[merged_sales_office] = min(
                            sales_office_order_map[merged_sales_office], order
                        )
            else:
                # Direct mapping (no transformation) - each sales office maps to itself
                unique_sales_offices = set()
                for brand in merged_brands:
                    vkbur_desc = brand.get('vkbur_desc', '')
                    if vkbur_desc:
                        unique_sales_offices.add(vkbur_desc)
                
                # Create direct mapping with alphabetical order
                for i, sales_office in enumerate(sorted(unique_sales_offices)):
                    sales_office_map[sales_office] = sales_office
                    sales_office_order_map[sales_office] = i + 1
            
            # Create detailed data for processing
            detailed_data_for_excel = []
            
            for brand in merged_brands:
                original_sales_office = brand.get('vkbur_desc', '')
                merged_sales_office = sales_office_map.get(original_sales_office, original_sales_office)
                
                is_merged = original_sales_office != merged_sales_office
                merger_group = merged_sales_office if is_merged else "NO_MERGE"
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
                    
                    # Sales office specific fields
                    'original_vkbur_desc': original_sales_office,
                    'merged_vkbur_desc': merged_sales_office,
                    'sales_office_order': sales_office_order_map.get(merged_sales_office, 9999),
                    
                    # Regional info (for context)
                    'regional_desc': str(brand.get('regional_desc', '')),
                    
                    # Merger tracking
                    'merger_status': merger_status,
                    'merger_group': merger_group,
                    'is_merged': is_merged,
                    
                    # Quantities
                    'qty_target_ae_original': float(brand.get('qty_target_ae', 0) or 0),
                    'qty_billing_sum_original': float(brand.get('qty_billing_sum', 0) or 0),
                    
                    'record_id': len(detailed_data_for_excel) + 1
                }
                
                detailed_data_for_excel.append(detailed_record)
            
            # Group data by sales office and other key fields
            grouped_data = {}
            
            for record in detailed_data_for_excel:
                key = (
                    record['category1'],
                    record['cycle'],
                    record['cycle_year'],
                    record['matkl'],
                    record['matkl_desc'],
                    record['merged_vkbur_desc'],  # Group by merged sales office
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
                        'vkbur_desc': record['merged_vkbur_desc'],  # Use merged sales office
                        'category3': record['category3'],
                        'category5': record['category5'],
                        'week1': record['week1'],
                        'qty_target_ae': 0,
                        'qty_billing_sum': 0,
                        'sales_office_order': record['sales_office_order'],
                        'record_count': 0,
                        'original_sales_offices': [],
                        'merger_groups': set(),
                        'has_merged_data': False,
                        'regional_contexts': set()  # Track which regionals are involved
                    }
                
                # Accumulate values
                grouped_data[key]['qty_target_ae'] += record['qty_target_ae_original']
                grouped_data[key]['qty_billing_sum'] += record['qty_billing_sum_original']
                grouped_data[key]['record_count'] += 1
                
                # Track originals and merger info
                if record['original_vkbur_desc'] not in grouped_data[key]['original_sales_offices']:
                    grouped_data[key]['original_sales_offices'].append(record['original_vkbur_desc'])
                
                grouped_data[key]['merger_groups'].add(record['merger_group'])
                grouped_data[key]['regional_contexts'].add(record['regional_desc'])
                
                if record['is_merged']:
                    grouped_data[key]['has_merged_data'] = True
            
            # Create final summary data
            summary_data = []
            for data in grouped_data.values():
                merger_groups_list = list(data['merger_groups'])
                regional_contexts_list = list(data['regional_contexts'])
                
                if data['has_merged_data']:
                    merger_status = "CONTAINS_MERGED"
                    merger_group = data['vkbur_desc']
                else:
                    merger_status = "NO_MERGE"
                    merger_group = "NO_MERGE"
                
                summary_record = {
                    'category1': data['category1'],
                    'cycle': data['cycle'],
                    'cycle_year': data['cycle_year'],
                    'matkl': data['matkl'],
                    'matkl_desc': data['matkl_desc'],
                    'vkbur_desc': data['vkbur_desc'],  # Sales office
                    'category3': data['category3'],
                    'category5': data['category5'],
                    'week1': data['week1'],
                    'qty_target_ae': data['qty_target_ae'],
                    'qty_billing_sum': data['qty_billing_sum'],
                    'sales_office_order': data['sales_office_order'],
                    'record_count': data['record_count'],
                    
                    # Context information
                    'regional_contexts': ', '.join(sorted(regional_contexts_list)),
                    
                    # Merger tracking fields
                    'original_sales_offices': ', '.join(data['original_sales_offices']),
                    'merger_status': merger_status,
                    'merger_group': merger_group,
                    'has_merged_data': data['has_merged_data'],
                    'merger_detail': f"Merged from: {', '.join(data['original_sales_offices'])}" if len(data['original_sales_offices']) > 1 else "No merge"
                }
                
                summary_data.append(summary_record)
            
            # Sort by sales office order
            summary_data.sort(key=lambda x: x.get('sales_office_order', 9999))
            
            # Export to Excel for verification (optional - uncomment if needed)
            # self._export_sales_office_merger_to_excel(
            #     detailed_data_for_excel, 
            #     summary_data, 
            #     sales_office_mappings
            # )
            
            logging.info(f"✓ Created summary with sales office: {len(summary_data)} records from {len(merged_brands)} original records")
            return summary_data
            
        except Exception as e:
            logging.error(f"Error creating summary with sales office: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _export_sales_office_merger_to_excel(self, detailed_data, summary_data, sales_office_mappings):
 
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sales_office_merger_analysis_{timestamp}.xlsx"
            filepath = os.path.join(self.export_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # Sheet 1: Summary Data (Main Results)
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    
                    # Format numerical columns
                    numerical_cols = ['qty_target_ae', 'qty_billing_sum', 'sales_office_order', 'record_count']
                    for col in numerical_cols:
                        if col in summary_df.columns:
                            summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce').fillna(0)
                    
                    summary_df.to_excel(writer, sheet_name='Summary_Data', index=False)
                    self._auto_adjust_columns(writer, 'Summary_Data')
                
                # Sheet 2: Detailed Data (Before Grouping)
                if detailed_data:
                    detailed_df = pd.DataFrame(detailed_data)
                    
                    # Format numerical columns
                    numerical_cols = ['qty_target_ae_original', 'qty_billing_sum_original', 'sales_office_order', 'record_id']
                    for col in numerical_cols:
                        if col in detailed_df.columns:
                            detailed_df[col] = pd.to_numeric(detailed_df[col], errors='coerce').fillna(0)
                    
                    detailed_df.to_excel(writer, sheet_name='Detailed_Data', index=False)
                    self._auto_adjust_columns(writer, 'Detailed_Data')
                
                # Sheet 3: Sales Office Mappings
                if sales_office_mappings:
                    mapping_data = []
                    for mapping in sales_office_mappings:
                        mapping_data.append({
                            'Original_Sales_Office': mapping[0],
                            'Merged_Sales_Office': mapping[1],
                            'Order': mapping[2]
                        })
                    
                    mapping_df = pd.DataFrame(mapping_data)
                    mapping_df.to_excel(writer, sheet_name='Sales_Office_Mappings', index=False)
                    self._auto_adjust_columns(writer, 'Sales_Office_Mappings')
                
                # Sheet 4: Verification Summary
                if summary_data and detailed_data:
                    verification_data = self._create_sales_office_verification_data(detailed_data, summary_data)
                    if verification_data:
                        verification_df = pd.DataFrame(verification_data)
                        verification_df.to_excel(writer, sheet_name='Verification', index=False)
                        self._auto_adjust_columns(writer, 'Verification')
                
                # Sheet 5: Sales Office Statistics
                if summary_data:
                    stats_data = self._create_sales_office_statistics(summary_data)
                    if stats_data:
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='Sales_Office_Statistics', index=False)
                        self._auto_adjust_columns(writer, 'Sales_Office_Statistics')
            
            logging.info(f"✓ Sales office analysis exported to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting sales office analysis: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _auto_adjust_columns(self, writer, sheet_name):
        """Helper method to auto-adjust column widths"""
        try:
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
        except Exception as e:
            logging.error(f"Error auto-adjusting columns for {sheet_name}: {e}")

    def _create_sales_office_verification_data(self, detailed_data, summary_data):
        """
        Create verification data to check if sum calculations are correct for sales office
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
                    summary['vkbur_desc'],
                    summary['category3'],
                    summary['category5'],
                    summary['week1']
                )
                summary_lookup[key] = summary
            
            detailed_groups = {}
            for detail in detailed_data:
                key = (
                    detail['category1'],
                    detail['cycle'],
                    detail['cycle_year'],
                    detail['matkl'],
                    detail['matkl_desc'],
                    detail['merged_vkbur_desc'],
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
                    'Sales_Office_Desc': summary['vkbur_desc'],
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
                    'Original_Sales_Offices': summary.get('original_sales_offices', ''),
                    'Regional_Contexts': summary.get('regional_contexts', '')
                })
            return verification_results
            
        except Exception as e:
            logging.error(f"Error creating sales office verification data: {e}")
            return []

    def _create_sales_office_statistics(self, summary_data):
        """
        Create statistics about the sales office merger process
        """
        try:
            stats = []
            
            # Count by merger status
            merger_status_count = {}
            total_records = len(summary_data)
            total_qty_target = 0
            total_qty_billing = 0
            
            # Sales office statistics
            sales_office_stats = {}
            regional_distribution = {}
            
            for record in summary_data:
                # Merger status count
                status = record.get('merger_status', 'UNKNOWN')
                merger_status_count[status] = merger_status_count.get(status, 0) + 1
                
                # Total quantities
                total_qty_target += float(record.get('qty_target_ae', 0))
                total_qty_billing += float(record.get('qty_billing_sum', 0))
                
                # Sales office statistics
                sales_office = record.get('vkbur_desc', 'UNKNOWN')
                if sales_office not in sales_office_stats:
                    sales_office_stats[sales_office] = {
                        'count': 0,
                        'qty_target': 0,
                        'qty_billing': 0,
                        'has_merged': record.get('has_merged_data', False)
                    }
                
                sales_office_stats[sales_office]['count'] += 1
                sales_office_stats[sales_office]['qty_target'] += float(record.get('qty_target_ae', 0))
                sales_office_stats[sales_office]['qty_billing'] += float(record.get('qty_billing_sum', 0))
                
                # Regional distribution
                regional_contexts = record.get('regional_contexts', '')
                if regional_contexts:
                    regions = [r.strip() for r in regional_contexts.split(',')]
                    for region in regions:
                        if region:
                            regional_distribution[region] = regional_distribution.get(region, 0) + 1
            
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
            
            # Sales office statistics
            for sales_office, data in sales_office_stats.items():
                percentage = (data['count'] / total_records * 100) if total_records > 0 else 0
                stats.append({
                    'Statistic_Type': 'SALES_OFFICE',
                    'Description': f'Sales Office: {sales_office}',
                    'Count': data['count'],
                    'Percentage': round(percentage, 2),
                    'Qty_Target_Sum': round(data['qty_target'], 2),
                    'Qty_Billing_Sum': round(data['qty_billing'], 2)
                })
            
            # Regional distribution statistics
            for region, count in regional_distribution.items():
                percentage = (count / total_records * 100) if total_records > 0 else 0
                stats.append({
                    'Statistic_Type': 'REGIONAL_DISTRIBUTION',
                    'Description': f'Regional Context: {region}',
                    'Count': count,
                    'Percentage': round(percentage, 2),
                    'Qty_Target_Sum': '',
                    'Qty_Billing_Sum': ''
                })
            
            return stats
            
        except Exception as e:
            logging.error(f"Error creating sales office statistics: {e}")
            return []