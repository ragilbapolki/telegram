# data_processor.py - Data processing and calculation logic
from collections import defaultdict
from datetime import datetime
from config import CURRENT_DATE, SATUAN

class DataProcessor:
    def __init__(self):
        pass
    
    def group_brand_data_by_region(self, brand_data_list):
        """
        Mengelompokkan brand data berdasarkan regional_desc (regional)
        """
        grouped = {}
        for brand in brand_data_list:
            region = brand.get('regional_desc', 'Unknown Region')
            if region not in grouped:
                grouped[region] = []
            grouped[region].append(brand)
        return grouped
    
    def group_products_by_description(self, product_data):
        """
        Mengelompokkan produk berdasarkan matkl_desc dan sum qty_billing_sum serta qty_target_ae
        """
        grouped_products = defaultdict(lambda: {
            'matkl_desc': '',
            'qty_billing_sum': 0.0,
            'qty_target_ae': 0.0,
            'category1': '',
            'prctr_base': ''
        })
        
        for item in product_data:
            matkl_desc = item.get('matkl_desc', 'Unknown Product')
            
            # Jika belum ada, set basic info
            if not grouped_products[matkl_desc]['matkl_desc']:
                grouped_products[matkl_desc]['matkl_desc'] = matkl_desc
                grouped_products[matkl_desc]['category1'] = item.get('category1', '')
                grouped_products[matkl_desc]['prctr_base'] = item.get('prctr_base', '')
            
            # Sum the values
            grouped_products[matkl_desc]['qty_billing_sum'] += float(item.get('qty_billing_sum', 0))
            grouped_products[matkl_desc]['qty_target_ae'] += float(item.get('qty_target_ae', 0))
        
        # Convert back to list
        return list(grouped_products.values())

    def group_new_brand_by_vkbur_desc_and_product(self, new_brand_data, previous_week_data):
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
            product = item.get('matkl_desc', 'Unknown Product')
            vkbur_desc = item.get('vkbur_desc', 'Unknown Office')
            qty = float(item.get('qty_billing_sum', 0))
            
            grouped_by_product[product][vkbur_desc]['current_week'] += qty
        
        # Process previous week data
        previous_new_brand = [item for item in previous_week_data if item.get('prctr_base') == '0000003998']
        for item in previous_new_brand:
            product = item.get('matkl_desc', 'Unknown Product')
            vkbur_desc = item.get('vkbur_desc', 'Unknown Office')
            qty = float(item.get('qty_billing_sum', 0))
            
            if product in grouped_by_product and vkbur_desc in grouped_by_product[product]:
                grouped_by_product[product][vkbur_desc]['previous_week'] += qty
        
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
        existing_data = [item for item in regional_data if item.get('prctr_base') != '0000003998']
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        
        # Group existing and new brand data by matkl_desc
        grouped_existing = self.group_products_by_description(existing_data)
        grouped_new = self.group_products_by_description(new_brand_data)
        
        current_week_sales_existing = sum([item['qty_billing_sum'] for item in grouped_existing])
        current_week_sales_new = sum([item['qty_billing_sum'] for item in grouped_new])
        
        total_w1_to_current_existing = current_week_sales_existing * current_week
        qty_target_ae_w1_to_current_existing = sum([item['qty_target_ae'] for item in grouped_existing]) * current_week
        achievement_pct_existing = (total_w1_to_current_existing / qty_target_ae_w1_to_current_existing * 100) if qty_target_ae_w1_to_current_existing > 0 else 0
        omset_ideal_pct = (current_week / total_weeks_in_cycle * 100) if total_weeks_in_cycle > 0 else 0
        
        gd_data = [item for item in grouped_existing if item.get('category1') == 'GD']
        gd_current_sales = sum([item['qty_billing_sum'] for item in gd_data])
        gd_qty_target_ae= sum([item['qty_target_ae'] for item in gd_data]) * current_week
        gd_achievement_pct = (gd_current_sales * current_week / gd_qty_target_ae* 100) if gd_qty_target_ae> 0 else 0
        
        gd_plt_data = [item for item in grouped_existing if item.get('category1') in ['GD', 'PLT']]
        gd_plt_current_sales = sum([item['qty_billing_sum'] for item in gd_plt_data])
        gd_plt_qty_target_ae= sum([item['qty_target_ae'] for item in gd_plt_data]) * current_week
        gd_plt_achievement_pct = (gd_plt_current_sales * current_week / gd_plt_qty_target_ae* 100) if gd_plt_qty_target_ae> 0 else 0
        
        total_current_sales = sum([float(item.get('qty_billing_sum', 0)) for item in regional_data])
        
        return {
            'current_week_sales_existing': current_week_sales_existing,
            'current_week_sales_new': current_week_sales_new,
            'total_w1_to_current_existing': total_w1_to_current_existing,
            'qty_target_ae_w1_to_current_existing': qty_target_ae_w1_to_current_existing,
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
    
    def find_best_vkbur(self, regional_data):
        """
        Mencari vkbur yang paling tepat dari data yang tersedia
        """
        if not regional_data:
            return None
        
        sample_data = regional_data[0]
        
        # Prioritas field untuk vkbur
        priority_fields = [
            'vstel',           # Sales organization
            'vkbur_desc',    # Sales office
            'vkbur',     # Direct vkbur
            'kunnr',          # Customer number
            'vkorg',          # Sales organization
            'vtweg',          # Distribution channel
        ]
        
        # Coba setiap field berdasarkan prioritas
        for field in priority_fields:
            if field in sample_data and sample_data[field]:
                vkbur = str(sample_data[field]).strip()
                if vkbur:
                    return vkbur
        
        # Jika tidak ada yang cocok, gunakan regional_desc sebagai fallback
        if 'regional_desc' in sample_data:
            return str(sample_data['regional_desc'])
        
        return None