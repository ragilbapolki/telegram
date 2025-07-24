import pandas as pd
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

class ExportManager:
    def __init__(self, base_export_path: str = "exports"):
        """
        Initialize ExportManager with base export path
        
        Args:
            base_export_path: Base directory for all exports
        """
        self.base_export_path = base_export_path
        self._ensure_export_directory()
    
    def _ensure_export_directory(self):
        """Ensure export directory exists"""
        try:
            os.makedirs(self.base_export_path, exist_ok=True)
            logging.info(f"Export directory ensured: {self.base_export_path}")
        except Exception as e:
            logging.error(f"Error creating export directory: {e}")
    
    def _generate_timestamp(self) -> str:
        """Generate timestamp string for filenames"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def export_merged_data_to_excel(self, merged_brands: List[Dict], cycle_year: str, cycle: str) -> Optional[str]:
        """
        Export merged brands data to Excel file
        
        Args:
            merged_brands: List of merged brand data dictionaries
            cycle_year: Cycle year string
            cycle: Cycle string
            
        Returns:
            Path to exported file or None if failed
        """
        try:
            if not merged_brands:
                logging.warning("No merged brands data to export")
                return None
            
            timestamp = self._generate_timestamp()
            filename = f"merged_brands_{cycle_year}_{cycle}_{timestamp}.xlsx"
            filepath = os.path.join(self.base_export_path, filename)
            
            # Convert to DataFrame
            df = pd.DataFrame(merged_brands)
            
            # Export to Excel with multiple sheets if data is complex
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Merged_Data', index=False)
                
                # Add summary sheet if possible
                if len(df) > 0:
                    summary_data = {
                        'Total Records': len(df),
                        'Cycle Year': cycle_year,
                        'Cycle': cycle,
                        'Export Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Columns': list(df.columns)
                    }
                    summary_df = pd.DataFrame([summary_data])
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            logging.info(f"Merged brands data exported successfully to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting merged brands data: {e}")
            return None
    
    def export_matching_brands_to_excel(self, matching_brands: List[Dict], cycle_year: str, cycle: str, filename: str = None) -> Optional[str]:
        """
        Export original matching brands data to Excel file
        
        Args:
            matching_brands: List of original brand data dictionaries
            cycle_year: Cycle year string
            cycle: Cycle string
            filename: Optional custom filename
            
        Returns:
            Path to exported file or None if failed
        """
        try:
            if not matching_brands:
                logging.warning("No matching brands data to export")
                return None
            
            if not filename:
                timestamp = self._generate_timestamp()
                filename = f"original_matching_brands_{cycle_year}_{cycle}_{timestamp}.xlsx"
            
            filepath = os.path.join(self.base_export_path, filename)
            
            # Convert to DataFrame
            df = pd.DataFrame(matching_brands)
            
            # Export to Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Original_Data', index=False)
                
                # Add metadata sheet
                metadata = {
                    'Total Records': len(df),
                    'Cycle Year': cycle_year,
                    'Cycle': cycle,
                    'Export Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Data Type': 'Original Matching Brands'
                }
                metadata_df = pd.DataFrame([metadata])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            logging.info(f"Original matching brands exported successfully to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting original matching brands: {e}")
            return None
    
    def export_summary_to_excel(self, merged_brands: List[Dict], cycle_year: str, cycle: str) -> Optional[str]:
        """
        Export summary data to Excel file
        
        Args:
            merged_brands: List of merged brand data dictionaries
            cycle_year: Cycle year string
            cycle: Cycle string
            
        Returns:
            Path to exported file or None if failed
        """
        try:
            if not merged_brands:
                logging.warning("No data to create summary")
                return None
            
            timestamp = self._generate_timestamp()
            filename = f"summary_{cycle_year}_{cycle}_{timestamp}.xlsx"
            filepath = os.path.join(self.base_export_path, filename)
            
            # Create summary data
            df = pd.DataFrame(merged_brands)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Main summary sheet
                df.to_excel(writer, sheet_name='Summary_Data', index=False)
                
                # Statistical summary if numeric columns exist
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    stats_summary = df[numeric_cols].describe()
                    stats_summary.to_excel(writer, sheet_name='Statistics')
                
                # Categorical summary
                categorical_cols = df.select_dtypes(include=['object']).columns
                if len(categorical_cols) > 0:
                    cat_summary = {}
                    for col in categorical_cols[:5]:  # Limit to first 5 categorical columns
                        cat_summary[col] = df[col].value_counts().head(10).to_dict()
                    
                    # Convert to DataFrame for export
                    cat_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in cat_summary.items()]))
                    cat_df.to_excel(writer, sheet_name='Categorical_Summary')
                
                # Export info sheet
                info_data = {
                    'Total Records': len(df),
                    'Total Columns': len(df.columns),
                    'Cycle Year': cycle_year,
                    'Cycle': cycle,
                    'Export Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Numeric Columns': len(numeric_cols),
                    'Categorical Columns': len(categorical_cols)
                }
                info_df = pd.DataFrame([info_data])
                info_df.to_excel(writer, sheet_name='Export_Info', index=False)
            
            logging.info(f"Summary data exported successfully to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting summary data: {e}")
            return None
    
    def export_summary_json(self, merged_brands: List[Dict], cycle_year: str, cycle: str) -> Optional[List[str]]:
        """
        Export summary data to JSON files
        
        Args:
            merged_brands: List of merged brand data dictionaries
            cycle_year: Cycle year string
            cycle: Cycle string
            
        Returns:
            List of paths to exported JSON files or None if failed
        """
        try:
            if not merged_brands:
                logging.warning("No data to export to JSON")
                return None
            
            timestamp = self._generate_timestamp()
            exported_files = []
            
            # Export full data JSON
            full_data_filename = f"full_data_{cycle_year}_{cycle}_{timestamp}.json"
            full_data_filepath = os.path.join(self.base_export_path, full_data_filename)
            
            with open(full_data_filepath, 'w', encoding='utf-8') as f:
                json.dump(merged_brands, f, indent=2, ensure_ascii=False, default=str)
            
            exported_files.append(full_data_filepath)
            logging.info(f"Full data JSON exported to: {full_data_filepath}")
            
            # Export summary statistics JSON
            df = pd.DataFrame(merged_brands)
            
            summary_stats = {
                'export_info': {
                    'total_records': len(df),
                    'total_columns': len(df.columns),
                    'cycle_year': cycle_year,
                    'cycle': cycle,
                    'export_date': datetime.now().isoformat(),
                    'columns': list(df.columns)
                }
            }
            
            # Add numeric summaries
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                numeric_summary = {}
                for col in numeric_cols:
                    numeric_summary[col] = {
                        'count': int(df[col].count()),
                        'mean': float(df[col].mean()) if not df[col].isna().all() else None,
                        'std': float(df[col].std()) if not df[col].isna().all() else None,
                        'min': float(df[col].min()) if not df[col].isna().all() else None,
                        'max': float(df[col].max()) if not df[col].isna().all() else None
                    }
                summary_stats['numeric_summary'] = numeric_summary
            
            # Add categorical summaries
            categorical_cols = df.select_dtypes(include=['object']).columns
            if len(categorical_cols) > 0:
                categorical_summary = {}
                for col in categorical_cols[:10]:  # Limit to first 10 columns
                    value_counts = df[col].value_counts().head(10)
                    categorical_summary[col] = {
                        'unique_count': int(df[col].nunique()),
                        'top_values': value_counts.to_dict()
                    }
                summary_stats['categorical_summary'] = categorical_summary
            
            # Export summary JSON
            summary_filename = f"summary_stats_{cycle_year}_{cycle}_{timestamp}.json"
            summary_filepath = os.path.join(self.base_export_path, summary_filename)
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_stats, f, indent=2, ensure_ascii=False, default=str)
            
            exported_files.append(summary_filepath)
            logging.info(f"Summary statistics JSON exported to: {summary_filepath}")
            
            return exported_files
            
        except Exception as e:
            logging.error(f"Error exporting JSON data: {e}")
            return None
    
    def export_custom_data(self, data: Any, filename: str, file_format: str = 'json') -> Optional[str]:
        """
        Export custom data in specified format
        
        Args:
            data: Data to export
            filename: Name of the file (without extension)
            file_format: Format to export ('json', 'excel', 'csv')
            
        Returns:
            Path to exported file or None if failed
        """
        try:
            timestamp = self._generate_timestamp()
            
            if file_format.lower() == 'json':
                filepath = os.path.join(self.base_export_path, f"{filename}_{timestamp}.json")
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                    
            elif file_format.lower() in ['excel', 'xlsx']:
                filepath = os.path.join(self.base_export_path, f"{filename}_{timestamp}.xlsx")
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                    df.to_excel(filepath, index=False)
                else:
                    # Handle other data types
                    df = pd.DataFrame({'data': [str(data)]})
                    df.to_excel(filepath, index=False)
                    
            elif file_format.lower() == 'csv':
                filepath = os.path.join(self.base_export_path, f"{filename}_{timestamp}.csv")
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                    df.to_csv(filepath, index=False, encoding='utf-8')
                else:
                    # Handle other data types
                    df = pd.DataFrame({'data': [str(data)]})
                    df.to_csv(filepath, index=False, encoding='utf-8')
                    
            else:
                logging.error(f"Unsupported file format: {file_format}")
                return None
            
            logging.info(f"Custom data exported successfully to: {filepath}")
            return filepath
            
        except Exception as e:
            logging.error(f"Error exporting custom data: {e}")
            return None
    
    def cleanup_old_files(self, days_old: int = 30):
        """
        Clean up export files older than specified days
        
        Args:
            days_old: Number of days after which files should be deleted
        """
        try:
            if not os.path.exists(self.base_export_path):
                return
            
            current_time = datetime.now()
            deleted_count = 0
            
            for filename in os.listdir(self.base_export_path):
                filepath = os.path.join(self.base_export_path, filename)
                
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    age_days = (current_time - file_time).days
                    
                    if age_days > days_old:
                        os.remove(filepath)
                        deleted_count += 1
                        logging.info(f"Deleted old export file: {filename}")
            
            logging.info(f"Cleanup completed. Deleted {deleted_count} old files.")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
    
    def get_export_info(self) -> Dict[str, Any]:
        """
        Get information about export directory and files
        
        Returns:
            Dictionary with export directory information
        """
        try:
            if not os.path.exists(self.base_export_path):
                return {
                    'export_path': self.base_export_path,
                    'exists': False,
                    'total_files': 0,
                    'total_size_mb': 0
                }
            
            files = os.listdir(self.base_export_path)
            total_size = 0
            file_types = {}
            
            for filename in files:
                filepath = os.path.join(self.base_export_path, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    total_size += size
                    
                    ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'export_path': self.base_export_path,
                'exists': True,
                'total_files': len(files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types,
                'latest_files': sorted(files, key=lambda x: os.path.getctime(os.path.join(self.base_export_path, x)), reverse=True)[:5]
            }
            
        except Exception as e:
            logging.error(f"Error getting export info: {e}")
            return {
                'export_path': self.base_export_path,
                'error': str(e)
            }