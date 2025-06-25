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
        message = f"""📊 REPORT OMSET WEEKLY W{current_week} CYCLE {cycle} ({self.satuan})
{region_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 SUMMARY REGIONAL {region_name}
Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.0f}% vs AE

% ACH AE Cy {cycle} (Existing): {summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)

% ACH AE Cy {cycle} (GD): {summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)

% ACH AE Cy {cycle} (GD+PLT): {summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 EXISTING BRAND (selain 3998):
"""
        
        # Existing Brand Section
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['total_qty_billing'] > 0]
        if existing_brands_with_qty:
            for item in existing_brands_with_qty:
                achievement_pct = (item['total_qty_billing'] / item['total_target'] * 100) if item['total_target'] > 0 else 0
                message += f"• {item['wgbez60']}: {item['total_qty_billing']:,.1f} box ({achievement_pct:.1f}%) Vs AE\n"
        else:
            message += "• Tidak ada Existing Brand dengan quantity > 0\n"
        
        message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # NEW BRAND Section dengan format yang diminta
        new_brand_data = [item for item in regional_data if item.get('prctr') == '3998']
        if new_brand_data:
            message += "🆕 NEW BRAND (hanya 3998):\n"
            
            # Group new brand data berdasarkan sales office dan product
            grouped_new_brand = self._group_new_brand_by_sales_office_and_product(new_brand_data, previous_week_data)
            
            # Hitung total brand untuk summary
            total_current = sum([offices['current_week'] for product_data in grouped_new_brand.values() for offices in product_data.values()])
            total_previous = sum([offices['previous_week'] for product_data in grouped_new_brand.values() for offices in product_data.values()])
            total_diff = total_current - total_previous
            
            for product, offices in grouped_new_brand.items():
                if any(office_data['current_week'] > 0 for office_data in offices.values()):
                    message += f"{product}:\n"
                    for sales_office, data in offices.items():
                        if data['current_week'] > 0:  # Hanya tampilkan yang ada qty
                            message += f"  {sales_office}: {data['current_week']:.1f} / {data['previous_week']:.1f} / {data['difference']:+.0f}\n"
                    message += "\n"
            
            # Total brand summary
            message += f"Total brand: {total_current:.1f} / {total_previous:.1f} / {total_diff:+.0f}\n\n"
        
        # Notes Section
        if regional_notes:
            message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 NOTES REGIONAL {region_name}:
{regional_notes}

"""
        
        # Footer
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 Report ini dibuat secara otomatis
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
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

📊 *Summary:*
• Existing Brand: {summary_data['current_week_sales_existing']:,.1f} BOX
• New Brand: {summary_data['current_week_sales_new']:,.1f} BOX
• Achievement: {summary_data['achievement_pct_existing']:.1f}%

🎯 *GD Performance:*
• GD Achievement: {summary_data['gd_achievement_pct']:.1f}%
• GD+PLT Achievement: {summary_data['gd_plt_achievement_pct']:.1f}%
        """
        
        return summary_message
    
    def _group_new_brand_by_sales_office_and_product(self, new_brand_data, previous_week_data):
        """
        Mengelompokkan NEW BRAND berdasarkan product (wgbez60) dan sales_office_name
        """
        grouped_new_brand = {}
        
        # Group data week sekarang
        for item in new_brand_data:
            product = item.get('wgbez60', 'Unknown Product')
            sales_office = item.get('sales_office_name', 'Unknown Office')
            
            if product not in grouped_new_brand:
                grouped_new_brand[product] = {}
            
            if sales_office not in grouped_new_brand[product]:
                grouped_new_brand[product][sales_office] = {
                    'current_week': 0.0,
                    'previous_week': 0.0,
                    'difference': 0.0
                }
            
            grouped_new_brand[product][sales_office]['current_week'] += float(item.get('total_qty_billing', 0))
        
        # Group data week lalu untuk perbandingan
        previous_new_brand = [item for item in previous_week_data if item.get('prctr') == '3998']
        
        for item in previous_new_brand:
            product = item.get('wgbez60', 'Unknown Product')
            sales_office = item.get('sales_office_name', 'Unknown Office')
            
            if product in grouped_new_brand and sales_office in grouped_new_brand[product]:
                grouped_new_brand[product][sales_office]['previous_week'] += float(item.get('total_qty_billing', 0))
        
        # Hitung difference
        for product in grouped_new_brand:
            for sales_office in grouped_new_brand[product]:
                current = grouped_new_brand[product][sales_office]['current_week']
                previous = grouped_new_brand[product][sales_office]['previous_week']
                grouped_new_brand[product][sales_office]['difference'] = current - previous
        
        return grouped_new_brand