# data_processor.py - Data processing and calculation logic
from collections import defaultdict
from datetime import datetime
from config import CURRENT_DATE, SATUAN

class DataProcessor:
    def __init__(self):
        pass
    
    def group_brand_data_by_region(self, brand_data_list):
        """
        Mengelompokkan brand data berdasarkan name_reg (regional)
        """
        grouped = {}
        for brand in brand_data_list:
            region = brand.get('name_reg', 'Unknown Region')
            if region not in grouped:
                grouped[region] = []
            grouped[region].append(brand)
        return grouped
    
    def group_products_by_description(self, product_data):
        """
        Mengelompokkan produk berdasarkan wgbez60 dan sum total_qty_billing serta total_target
        """
        grouped_products = defaultdict(lambda: {
            'wgbez60': '',
            'total_qty_billing': 0.0,
            'total_target': 0.0,
            'category1': '',
            'prctr': ''
        })
        
        for item in product_data:
            wgbez60 = item.get('wgbez60', 'Unknown Product')
            
            # Jika belum ada, set basic info
            if not grouped_products[wgbez60]['wgbez60']:
                grouped_products[wgbez60]['wgbez60'] = wgbez60
                grouped_products[wgbez60]['category1'] = item.get('category1', '')
                grouped_products[wgbez60]['prctr'] = item.get('prctr', '')
            
            # Sum the values
            grouped_products[wgbez60]['total_qty_billing'] += float(item.get('total_qty_billing', 0))
            grouped_products[wgbez60]['total_target'] += float(item.get('total_target', 0))
        
        # Convert back to list
        return list(grouped_products.values())

    def group_new_brand_by_sales_office_and_product(self, new_brand_data, previous_week_data):
        """
        Mengelompokkan NEW BRAND berdasarkan product dan sales office dengan format baru
        """
        # Group by product first
        grouped_by_product = defaultdict(lambda: defaultdict(lambda: {
            'current_week': 0.0,
            'previous_week': 0.0,
            'difference': 0.0
        }))
        
        # Process current week data
        for item in new_brand_data:
            product = item.get('wgbez60', 'Unknown Product')
            sales_office = item.get('sales_office_name', 'Unknown Office')
            qty = float(item.get('total_qty_billing', 0))
            
            grouped_by_product[product][sales_office]['current_week'] += qty
        
        # Process previous week data
        previous_new_brand = [item for item in previous_week_data if item.get('prctr') == '3998']
        for item in previous_new_brand:
            product = item.get('wgbez60', 'Unknown Product')
            sales_office = item.get('sales_office_name', 'Unknown Office')
            qty = float(item.get('total_qty_billing', 0))
            
            if product in grouped_by_product and sales_office in grouped_by_product[product]:
                grouped_by_product[product][sales_office]['previous_week'] += qty
        
        # Calculate differences and totals
        result = {}
        for product, offices in grouped_by_product.items():
            result[product] = {
                'offices': {},
                'total_current': 0.0,
                'total_previous': 0.0,
                'total_difference': 0.0
            }
            
            for office, data in offices.items():
                current = data['current_week']
                previous = data['previous_week']
                difference = current - previous
                
                result[product]['offices'][office] = {
                    'current_week': current,
                    'previous_week': previous,
                    'difference': difference
                }
                
                result[product]['total_current'] += current
                result[product]['total_previous'] += previous
                result[product]['total_difference'] += difference
        
        return result
    
    def calculate_regional_summary(self, regional_data, current_week, total_weeks_in_cycle):
        """
        Menghitung summary untuk regional tertentu dengan format baru
        """
        existing_data = [item for item in regional_data if item.get('prctr') != '3998']
        new_brand_data = [item for item in regional_data if item.get('prctr') == '3998']
        
        # Group existing and new brand data by wgbez60
        grouped_existing = self.group_products_by_description(existing_data)
        grouped_new = self.group_products_by_description(new_brand_data)
        
        current_week_sales_existing = sum([item['total_qty_billing'] for item in grouped_existing])
        current_week_sales_new = sum([item['total_qty_billing'] for item in grouped_new])
        
        total_w1_to_current_existing = current_week_sales_existing * current_week
        total_target_w1_to_current_existing = sum([item['total_target'] for item in grouped_existing]) * current_week
        achievement_pct_existing = (total_w1_to_current_existing / total_target_w1_to_current_existing * 100) if total_target_w1_to_current_existing > 0 else 0
        omset_ideal_pct = (current_week / total_weeks_in_cycle * 100) if total_weeks_in_cycle > 0 else 0
        
        gd_data = [item for item in grouped_existing if item.get('category1') == 'GD']
        gd_current_sales = sum([item['total_qty_billing'] for item in gd_data])
        gd_total_target = sum([item['total_target'] for item in gd_data]) * current_week
        gd_achievement_pct = (gd_current_sales * current_week / gd_total_target * 100) if gd_total_target > 0 else 0
        
        gd_plt_data = [item for item in grouped_existing if item.get('category1') in ['GD', 'PLT']]
        gd_plt_current_sales = sum([item['total_qty_billing'] for item in gd_plt_data])
        gd_plt_total_target = sum([item['total_target'] for item in gd_plt_data]) * current_week
        gd_plt_achievement_pct = (gd_plt_current_sales * current_week / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0
        
        total_current_sales = sum([float(item.get('total_qty_billing', 0)) for item in regional_data])
        
        return {
            'current_week_sales_existing': current_week_sales_existing,
            'current_week_sales_new': current_week_sales_new,
            'total_w1_to_current_existing': total_w1_to_current_existing,
            'total_target_w1_to_current_existing': total_target_w1_to_current_existing,
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
    
    def find_best_regional_id(self, regional_data):
        """
        Mencari regional_id yang paling tepat dari data yang tersedia
        """
        if not regional_data:
            return None
        
        sample_data = regional_data[0]
        
        # Prioritas field untuk regional_id
        priority_fields = [
            'vstel',           # Sales organization
            'sales_office',    # Sales office
            'regional_id',     # Direct regional_id
            'kunnr',          # Customer number
            'vkorg',          # Sales organization
            'vtweg',          # Distribution channel
        ]
        
        # Coba setiap field berdasarkan prioritas
        for field in priority_fields:
            if field in sample_data and sample_data[field]:
                regional_id = str(sample_data[field]).strip()
                if regional_id:
                    return regional_id
        
        # Jika tidak ada yang cocok, gunakan name_reg sebagai fallback
        if 'name_reg' in sample_data:
            return str(sample_data['name_reg'])
        
        return None