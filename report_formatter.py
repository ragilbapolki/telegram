# report_formatter.py - Format laporan untuk email dan telegram
from datetime import datetime
from config import SATUAN

class ReportFormatter:
    def __init__(self):
        self.satuan = SATUAN
    
    def format_telegram_message(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan untuk Telegram dengan struktur yang diminta
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        total_weeks = 4
        
        # Header
        message = f"""📊 **REPORT OMSET WEEKLY W{current_week} CYCLE {cycle}** ({self.satuan})
*{region_name}* - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 **SUMMARY {region_name}**
Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.0f}% vs AE
% ACH AE Cy {cycle} (Existing): {summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)
% ACH AE Cy {cycle} (GD): {summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)
% ACH AE Cy {cycle} (GD+PLT): {summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)

📈 **EXISTING BRAND Vs AE:**
"""
        
        # Existing Brand Section dengan padding untuk alignment
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        if existing_brands_with_qty:
            # Tentukan panjang maksimum untuk padding (minimum 8 karakter)
            max_length = max(8, max(len(item['matkl_desc']) for item in existing_brands_with_qty))
            
            for item in existing_brands_with_qty:
                achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
                # Padding nama produk agar sama panjang
                product_name = item['matkl_desc'].ljust(max_length)
                message += f"• `{product_name}` : {item['qty_billing_sum']:,.1f} box ({achievement_pct:.1f}%)\n"
        else:
            message += "• Tidak ada Existing Brand dengan quantity > 0\n"
        
        message += "\n"
        
        # NEW BRAND Section dengan format yang diminta (per brand)
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            message += "🆕 **NEW BRAND (TW/LW/+/-)** :\n"
            
            # Group new brand data berdasarkan product saja (tidak per sales office)
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            
            # Hitung total brand untuk summary
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            
            # Padding untuk NEW BRAND juga agar konsisten
            new_brand_products = [product for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            if new_brand_products:
                max_new_brand_length = max(8, max(len(product) for product in new_brand_products))
                
                for product, data in grouped_new_brand.items():
                    if data['current_week'] > 0:  # Hanya tampilkan yang ada qty
                        product_name = product.ljust(max_new_brand_length)
                        message += f"`{product_name}` : {data['current_week']:.1f} / {data['previous_week']:.1f} / {data['difference']:+.0f}\n"
            
            # Total brand summary
            message += f"**Total brand**: {total_current:.1f} / {total_previous:.1f} / {total_diff:+.0f}\n\n"

        message += (
            "📧 Report ini dibuat secara otomatis\n"
            f"*Generated*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return message
    
    def format_email_body(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format body email (sama dengan telegram untuk konsistensi)
        """
        return self.format_telegram_message(region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes)
    
    def format_summary_message(self, region_name, summary_data, cycle, week):
        """
        Format ringkasan singkat untuk Telegram
        """
        summary_message = f"""
🏢 *{region_name}* - Cycle {cycle} Week {week}

# 📊 *Summary:*
# • Existing Brand: {summary_data['current_week_sales_existing']:,.1f} BOX
# • New Brand: {summary_data['current_week_sales_new']:,.1f} BOX
# • Achievement: {summary_data['achievement_pct_existing']:.1f}%

# 🎯 *GD Performance:*
# • GD Achievement: {summary_data['gd_achievement_pct']:.1f}%
# • GD+PLT Achievement: {summary_data['gd_plt_achievement_pct']:.1f}%
#         """
        
        return summary_message
    
    def _group_new_brand_by_product_only(self, new_brand_data, previous_week_data):
        """
        Mengelompokkan NEW BRAND berdasarkan product saja (tanpa breakdown per sales office)
        """
        grouped_new_brand = {}
        
        # Group data week sekarang berdasarkan product
        for item in new_brand_data:
            product = item.get('matkl_desc', 'Unknown Product')
            
            if product not in grouped_new_brand:
                grouped_new_brand[product] = {
                    'current_week': 0.0,
                    'previous_week': 0.0,
                    'difference': 0.0
                }
            
            grouped_new_brand[product]['current_week'] += float(item.get('qty_billing_sum', 0))
        
        # Group data week lalu untuk perbandingan
        previous_new_brand = [item for item in previous_week_data if item.get('prctr_base') == '0000003998']
        
        for item in previous_new_brand:
            product = item.get('matkl_desc', 'Unknown Product')
            
            if product not in grouped_new_brand:
                grouped_new_brand[product] = {
                    'current_week': 0.0,
                    'previous_week': 0.0,
                    'difference': 0.0
                }
            
            grouped_new_brand[product]['previous_week'] += float(item.get('qty_billing_sum', 0))
        
        # Hitung difference
        for product in grouped_new_brand:
            current = grouped_new_brand[product]['current_week']
            previous = grouped_new_brand[product]['previous_week']
            grouped_new_brand[product]['difference'] = current - previous
        
        return grouped_new_brand
    
    def _group_new_brand_by_sales_office_and_product(self, new_brand_data, previous_week_data):
        """
        Mengelompokkan NEW BRAND berdasarkan product (matkl_desc) dan vkbur_desc
        (Method ini tetap dipertahankan untuk backward compatibility jika diperlukan)
        """
        grouped_new_brand = {}
        
        # Group data week sekarang
        for item in new_brand_data:
            product = item.get('matkl_desc', 'Unknown Product')
            sales_office = item.get('vkbur_desc', 'Unknown Office')
            
            if product not in grouped_new_brand:
                grouped_new_brand[product] = {}
            
            if sales_office not in grouped_new_brand[product]:
                grouped_new_brand[product][sales_office] = {
                    'current_week': 0.0,
                    'previous_week': 0.0,
                    'difference': 0.0
                }
            
            grouped_new_brand[product][sales_office]['current_week'] += float(item.get('qty_billing_sum', 0))
        
        # Group data week lalu untuk perbandingan
        previous_new_brand = [item for item in previous_week_data if item.get('prctr_base') == '0000003998']
        
        for item in previous_new_brand:
            product = item.get('matkl_desc', 'Unknown Product')
            sales_office = item.get('vkbur_desc', 'Unknown Office')
            
            if product in grouped_new_brand and sales_office in grouped_new_brand[product]:
                grouped_new_brand[product][sales_office]['previous_week'] += float(item.get('qty_billing_sum', 0))
        
        # Hitung difference
        for product in grouped_new_brand:
            for sales_office in grouped_new_brand[product]:
                current = grouped_new_brand[product][sales_office]['current_week']
                previous = grouped_new_brand[product][sales_office]['previous_week']
                grouped_new_brand[product][sales_office]['difference'] = current - previous
        
        return grouped_new_brand
    
    def format_whatsapp_message(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan untuk WhatsApp dengan struktur yang lebih sederhana dan rapi
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        total_weeks = 4
        
        # Header dengan formatting WhatsApp
        message = f"""📊 *REPORT OMSET WEEKLY W{current_week} CYCLE {cycle}* ({self.satuan})
    _{region_name}_ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    📈 *SUMMARY {region_name}*
    Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.0f}% vs AE

    % ACH AE Cy {cycle} (Existing): {summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)
    % ACH AE Cy {cycle} (GD): {summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)
    % ACH AE Cy {cycle} (GD+PLT): {summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)

    📈 *EXISTING BRAND Vs AE:*
    """
        
        # Existing Brand Section dengan padding untuk alignment yang rapi
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        if existing_brands_with_qty:
            # Tentukan panjang maksimum untuk padding existing brands
            max_existing_length = max(8, max(len(item['matkl_desc']) for item in existing_brands_with_qty))
            
            for item in existing_brands_with_qty:
                achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
                # Padding nama produk agar titik dua (:) sejajar
                product_name = item['matkl_desc'].ljust(max_existing_length)
                message += f"{product_name} : {item['qty_billing_sum']:,.1f} box ({achievement_pct:.1f}%)\n"
        else:
            message += "• Tidak ada Existing Brand dengan quantity > 0\n"
        
        message += "\n"
        
        # NEW BRAND Section dengan format WhatsApp
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            message += "🆕 *NEW BRAND (TW/LW/+/-)*:\n"
            
            # Group new brand data berdasarkan product saja
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            
            # Hitung total brand untuk summary
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            
            # Format NEW BRAND untuk WhatsApp dengan padding yang rapi
            new_brand_products = [product for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            if new_brand_products:
                # Tentukan panjang maksimum untuk padding new brands
                max_new_brand_length = max(9, max(len(product) for product in new_brand_products))
                
                for product, data in grouped_new_brand.items():
                    if data['current_week'] > 0:  # Hanya tampilkan yang ada qty
                        # Padding nama produk agar titik dua (:) sejajar
                        product_name = product.ljust(max_new_brand_length)
                        diff_symbol = "+" if data['difference'] >= 0 else ""
                        message += f"{product_name} : {data['current_week']:.1f} / {data['previous_week']:.1f} / {diff_symbol}{data['difference']:.0f}\n"
            
            # Total brand summary dengan padding yang konsisten
            total_brand_text = "Total brand".ljust(max_new_brand_length if 'max_new_brand_length' in locals() else 8)
            total_diff_symbol = "+" if total_diff >= 0 else ""
            message += f"*{total_brand_text}* : {total_current:.1f} / {total_previous:.1f} / {total_diff_symbol}{total_diff:.0f}\n\n"
            
        message += (
            "📧 Report ini dibuat secara otomatis\n"
            f"_Generated_: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return message

    def format_whatsapp_message_compact(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan WhatsApp yang lebih kompak untuk grup dengan banyak pesan
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        
        # Header kompak
        message = f"""📊 *WEEKLY W{current_week} CYCLE {cycle}* - {region_name}
    _{datetime.now().strftime('%Y-%m-%d %H:%M')}_

    📈 *SUMMARY*
    Existing: {summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)
    GD: {summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)
    GD+PLT: {summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)

    📈 *TOP EXISTING BRANDS*
    """
        
        # Hanya tampilkan top 5 existing brands
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        existing_brands_with_qty.sort(key=lambda x: x['qty_billing_sum'], reverse=True)
        
        for i, item in enumerate(existing_brands_with_qty[:5]):  # Top 5 saja
            achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
            message += f"{i+1}. *{item['matkl_desc']}*: {item['qty_billing_sum']:,.1f} ({achievement_pct:.1f}%)\n"
        
        # NEW BRAND Section kompak
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            message += "\n🆕 *NEW BRAND*\n"
            
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            
            # Hanya tampilkan yang memiliki quantity current week > 0
            new_brand_items = [(product, data) for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            new_brand_items.sort(key=lambda x: x[1]['current_week'], reverse=True)
            
            for product, data in new_brand_items[:5]:  # Top 5 new brand
                diff_symbol = "+" if data['difference'] >= 0 else ""
                message += f"*{product}*: {data['current_week']:.1f} ({diff_symbol}{data['difference']:.0f})\n"
            
            # Total new brand
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            total_diff_symbol = "+" if total_diff >= 0 else ""
            message += f"*Total*: {total_current:.1f} ({total_diff_symbol}{total_diff:.0f})\n"
        
        message += f"\n_Auto-generated {datetime.now().strftime('%H:%M')}_"
        
        return message

    def format_whatsapp_message_table_style(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan WhatsApp dengan style tabel menggunakan karakter khusus
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        
        # Header
        message = f"""📊 *REPORT OMSET W{current_week} CYCLE {cycle}*
    🏢 *{region_name}* - {datetime.now().strftime('%m/%d %H:%M')}

    ┌─────────────────────────────────┐
    │           📈 SUMMARY            │
    ├─────────────────────────────────┤
    │ Existing: {summary_data['current_week_sales_existing']:>6.1f} Box ({summary_data['achievement_pct_existing']:>5.1f}%) │
    │ GD      : {summary_data['gd_current_sales']:>6.1f} Box ({summary_data['gd_achievement_pct']:.1f}%) │
    │ GD+PLT  : {summary_data['gd_plt_current_sales']:>6.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%) │
    └─────────────────────────────────┘

    📈 *EXISTING BRAND TOP 10*
    """
        
        # Existing Brand dalam format tabel
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        existing_brands_with_qty.sort(key=lambda x: x['qty_billing_sum'], reverse=True)
        
        for i, item in enumerate(existing_brands_with_qty[:10]):  # Top 10
            achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
            
            # Truncate nama produk jika terlalu panjang
            product_name = item['matkl_desc'][:12] if len(item['matkl_desc']) > 12 else item['matkl_desc']
            
            message += f"│ {i+1:2d}. {product_name:<12} │ {item['qty_billing_sum']:>6.1f} │ {achievement_pct:>5.1f}% │\n"
        
        # NEW BRAND Section
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            message += "\n🆕 *NEW BRAND (TW/LW/Δ)*\n"
            
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            
            new_brand_items = [(product, data) for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            new_brand_items.sort(key=lambda x: x[1]['current_week'], reverse=True)
            
            for product, data in new_brand_items[:8]:  # Top 8 new brand
                product_name = product[:12] if len(product) > 12 else product
                diff_symbol = "+" if data['difference'] >= 0 else ""
                message += f"│ {product_name:<12} │ {data['current_week']:>4.1f} │ {data['previous_week']:>4.1f} │ {diff_symbol}{data['difference']:>4.0f} │\n"
            
            # Total new brand
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            total_diff_symbol = "+" if total_diff >= 0 else ""
            message += f"├─────────────────────────────────┤\n"
            message += f"│ *TOTAL*       │ {total_current:>4.1f} │ {total_previous:>4.1f} │ {total_diff_symbol}{total_diff:>4.0f} │\n"
            message += f"└─────────────────────────────────┘\n"
        
        message += f"\n_Auto-report {datetime.now().strftime('%H:%M')}_"
        
        return message