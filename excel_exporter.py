"""
Example usage of the enhanced ReportApp with summary features
"""

from datetime import datetime
import logging
from report_app import ReportApp  # Your main ReportApp class
from summary_processor import SummaryProcessor
from excel_exporter import ExcelExporter

def example_usage():
    """
    Example of how to use the new summary features
    """
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the app
    app = ReportApp()
    
    # Example 1: Run full report with summaries
    print("=== Running Full Report with Summaries ===")
    success = app.run_report_with_summaries()
    
    if success:
        print("✓ Full report with summaries completed successfully!")
    else:
        print("✗ Full report with summaries failed!")
    
    # Example 2: Process summaries for specific merged brands data
    print("\n=== Processing Summaries for Specific Data ===")
    
    # Assuming you have merged_brands data
    sample_merged_brands = [
        {
            'category1': 'Category A',
            'cycle': '1',
            'cycle_year': '2024',
            'matkl': 'MAT001',
            'matkl_desc': 'Material 1',
            'prctr_ae': 'PR001',
            'regional_desc': 'Region A',
            'week1': '1',
            'qty_target_ae': 100,
            'qty_billing': 80,
            'merge_status': 'MERGED'
        },
        {
            'category1': 'Category A',
            'cycle': '1',
            'cycle_year': '2024',
            'matkl': 'MAT001',
            'matkl_desc': 'Material 1',
            'prctr_ae': 'PR001',
            'regional_desc': 'Region B',
            'week1': '1',
            'qty_target_ae': 100,
            'qty_billing': 90,
            'merge_status': 'MERGED'
        },
        {
            'category1': 'Category B',
            'cycle': '1',
            'cycle_year': '2024',
            'matkl': 'MAT002',
            'matkl_desc': 'Material 2',
            'prctr_ae': 'PR002',
            'regional_desc': 'Region A',
            'week1': '2',
            'qty_target_ae': 200,
            'qty_billing': 150,
            'merge_status': 'P_ONLY'
        }
    ]
    
    # Process summaries for this data
    summary_results = app.export_summaries_for_merged_brands(
        sample_merged_brands, '2024', '1'
    )
    
    if summary_results:
        print("✓ Summary processing completed!")
        print(f"  - Combined Excel: {summary_results['combined_excel']}")
        print(f"  - Regional Summary: {len(summary_results['regional_summary'])} records")
        print(f"  - Non-Regional Summary: {len(summary_results['non_regional_summary'])} records")
    else:
        print("✗ Summary processing failed!")
    
    # Example 3: Export category summary
    print("\n=== Exporting Category Summary ===")
    category_file = app.export_summary_by_category(sample_merged_brands, '2024', '1')
    
    if category_file:
        print(f"✓ Category summary exported to: {category_file}")
    else:
        print("✗ Category summary export failed!")
    
    # Example 4: Get basic statistics
    print("\n=== Getting Basic Statistics ===")
    stats = app.get_summary_statistics(sample_merged_brands)
    
    if stats:
        print("✓ Statistics generated:")
        print(f"  - Total records: {stats['total_records']}")
        print(f"  - Total qty billing: {stats['total_qty_billing']}")
        print(f"  - Total qty target: {stats['total_qty_target']}")
        print(f"  - Unique categories: {stats['unique_categories']}")
        print(f"  - Merge status counts: {stats['merge_status_counts']}")
    else:
        print("✗ Statistics generation failed!")

def example_direct_summary_processing():
    """
    Example of using summary processor and excel exporter directly
    """
    print("\n=== Direct Summary Processing Example ===")
    
    # Sample data
    sample_merged_brands = [
        {
            'category1': 'Electronics',
            'cycle': '2',
            'cycle_year': '2024',
            'matkl': 'ELE001',
            'matkl_desc': 'Electronics Item 1',
            'prctr_ae': 'PR100',
            'regional_desc': 'North Region',
            'week1': '10',
            'qty_target_ae': 500,
            'qty_billing': 450,
            'merge_status': 'MERGED'
        },
        {
            'category1': 'Electronics',
            'cycle': '2',
            'cycle_year': '2024',
            'matkl': 'ELE001',
            'matkl_desc': 'Electronics Item 1',
            'prctr_ae': 'PR100',
            'regional_desc': 'South Region',
            'week1': '10',
            'qty_target_ae': 500,
            'qty_billing': 400,
            'merge_status': 'MERGED'
        }
    ]
    
    # Initialize processors
    summary_processor = SummaryProcessor()
    excel_exporter = ExcelExporter()
    
    # Create summaries
    regional_summary = summary_processor.create_summary_with_regional(sample_merged_brands)
    non_regional_summary = summary_processor.create_summary_without_regional(sample_merged_brands)
    
    # Export to Excel
    excel_file = excel_exporter.export_summaries_to_excel(
        regional_summary, non_regional_summary, '2024', '2'
    )
    
    if excel_file:
        print(f"✓ Excel file exported: {excel_file}")
    else:
        print("✗ Excel export failed!")
    
    # Export to JSON
    json_files = summary_processor.export_summaries_to_json(
        regional_summary, non_regional_summary, '2024', '2'
    )
    
    if json_files[0] and json_files[1]:
        print(f"✓ JSON files exported:")
        print(f"  - Regional: {json_files[0]}")
        print(f"  - Non-regional: {json_files[1]}")
    else:
        print("✗ JSON export failed!")

if __name__ == "__main__":
    print("=== Summary Processing Examples ===")
    example_usage()
    example_direct_summary_processing()
    print("\n=== Examples completed! ===")