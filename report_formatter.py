# report_formatter.py - Format laporan untuk email dan telegram
from datetime import datetime
from config import SATUAN

class ReportFormatter:
    def __init__(self):
        self.satuan = SATUAN
    
    def _get_existing_brands_robust(self, regional_data, summary_data, current_week):
        """
        Ambil data existing brands dengan filter yang tepat untuk current week
        """
        if 'grouped_existing' in summary_data and summary_data['grouped_existing']:
            existing_brands_from_summary = [
                {
                    'matkl_desc': item.get('matkl_desc', 'Unknown Product'),
                    'qty_current_week': float(item.get('qty_billing_sum', 0)),
                    'qty_target_ae': float(item.get('qty_target_ae', 0))
                }
                for item in summary_data['grouped_existing']
                if float(item.get('qty_billing_sum', 0)) > 0
            ]
            
            if existing_brands_from_summary:
                return existing_brands_from_summary
        
        # Strategy 2: Ambil dari regional_data berdasarkan week yang tepat
        current_week_existing_data = []
        for item in regional_data:
            # Filter untuk existing brand (bukan new brand)
            if item.get('prctr_base') != '0000003998':
                # Filter berdasarkan week yang tepat
                item_week = int(item.get('week2', 0))
                if item_week == current_week:
                    current_week_existing_data.append(item)
        
        if not current_week_existing_data:
            # Strategy 3: Jika tidak ada data untuk current week, ambil data terbaru
            print(f"Warning: Tidak ada data untuk week {current_week}, menggunakan semua data existing brand")
            current_week_existing_data = [
                item for item in regional_data 
                if item.get('prctr_base') != '0000003998'
            ]
        
        # Group by product untuk current week
        grouped_existing = {}
        for item in current_week_existing_data:
            product = item.get('matkl_desc', 'Unknown Product')
            qty_billing = float(item.get('qty_billing_sum', 0))
            
            if qty_billing > 0:  # Hanya ambil yang ada quantity
                if product not in grouped_existing:
                    grouped_existing[product] = {
                        'qty_current_week': 0.0,
                        'qty_target_ae': 0.0,
                        'matkl_desc': product
                    }
                
                grouped_existing[product]['qty_current_week'] += qty_billing
                
                # Coba ambil target AE jika ada
                if 'qty_target_ae' in item:
                    grouped_existing[product]['qty_target_ae'] = float(item.get('qty_target_ae', 0))
        
        # Convert to list
        existing_brands_with_qty = [
            {
                'matkl_desc': product,
                'qty_current_week': data['qty_current_week'],
                'qty_target_ae': data['qty_target_ae']
            }
            for product, data in grouped_existing.items()
        ]
        
        return existing_brands_with_qty
    
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
    
    def _format_header(self, region_name, cycle, current_week, is_national=False):
        """
        Format header yang reusable untuk semua platform
        """
        title = "NATIONAL REPORT" if is_national else "REPORT"
        region_display = "INDONESIA NASIONAL" if is_national else region_name
        
        return {
            'title': f"{title} OMSET WEEKLY W{current_week} CYCLE {cycle}",
            'region': region_display,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _format_summary_section(self, summary_data, cycle, cycle_year, current_week):
        """
        Format bagian summary yang reusable
        """
        return {
            'cycle_info': f"Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.0f}% vs AE",
            'existing_ach': f"% ACH AE Cy {cycle} (Existing): {summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)",
            'gd_ach': f"% ACH AE Cy {cycle} (GD): {summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)",
            'gd_plt_ach': f"% ACH AE Cy {cycle} (GD+PLT): {summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)"
        }
    
    def _format_existing_brands_section(self, existing_brands, current_week, max_items=None):
        """
        Format existing brands section yang reusable
        """
        if not existing_brands:
            return {
                'items': [],
                'total_brands': 0,
                'total_qty': 0,
                'has_data': False
            }
        
        # Sort dan limit jika diperlukan
        sorted_brands = sorted(existing_brands, key=lambda x: x['qty_current_week'], reverse=True)
        if max_items:
            sorted_brands = sorted_brands[:max_items]
        
        formatted_items = []
        for i, item in enumerate(sorted_brands, 1):
            achievement_pct = (item['qty_current_week'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
            formatted_items.append({
                'rank': i,
                'product': item['matkl_desc'],
                'qty': item['qty_current_week'],
                'achievement_pct': achievement_pct
            })
        
        return {
            'items': formatted_items,
            'total_brands': len(existing_brands),
            'total_qty': sum([item['qty_current_week'] for item in existing_brands]),
            'has_data': True
        }
    
    def _format_new_brand_section(self, new_brand_data, previous_week_data, max_items=None):
        """
        Format new brand section yang reusable
        """
        if not new_brand_data:
            return {
                'items': [],
                'total_current': 0,
                'total_previous': 0,
                'total_diff': 0,
                'has_data': False
            }
        
        grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
        
        # Filter dan sort
        new_brand_items = [(product, data) for product, data in grouped_new_brand.items() if data['current_week'] > 0]
        new_brand_items.sort(key=lambda x: x[1]['current_week'], reverse=True)
        
        if max_items:
            new_brand_items = new_brand_items[:max_items]
        
        formatted_items = []
        for i, (product, data) in enumerate(new_brand_items, 1):
            formatted_items.append({
                'rank': i,
                'product': product,
                'current_week': data['current_week'],
                'previous_week': data['previous_week'],
                'difference': data['difference']
            })
        
        # Calculate totals
        total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
        total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
        total_diff = total_current - total_previous
        
        return {
            'items': formatted_items,
            'total_current': total_current,
            'total_previous': total_previous,
            'total_diff': total_diff,
            'total_brands': len([product for product, data in grouped_new_brand.items() if data['current_week'] > 0]),
            'has_data': True
        }
    
    def _format_regional_breakdown(self, national_data, current_week):
        """
        Format regional breakdown yang reusable
        """
        regional_groups = {}
        
        for item in national_data:
            regional_key = item.get('regional', 'Unknown Regional')
            
            if regional_key not in regional_groups:
                regional_groups[regional_key] = {
                    'existing_sales': 0.0,
                    'new_brand_sales': 0.0,
                    'total_sales': 0.0
                }
            
            qty_billing = float(item.get('qty_billing_sum', 0))
            
            if item.get('prctr_base') == '0000003998':  # New brand
                regional_groups[regional_key]['new_brand_sales'] += qty_billing
            else:  # Existing brand
                regional_groups[regional_key]['existing_sales'] += qty_billing
            
            regional_groups[regional_key]['total_sales'] += qty_billing
        
        # Sort regional berdasarkan total sales
        sorted_regionals = sorted(regional_groups.items(), key=lambda x: x[1]['total_sales'], reverse=True)
        
        return [
            {
                'name': regional_name,
                'existing_sales': data['existing_sales'],
                'new_brand_sales': data['new_brand_sales'],
                'total_sales': data['total_sales']
            }
            for regional_name, data in sorted_regionals
            if data['total_sales'] > 0
        ]
    
    def format_telegram_message(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan untuk Telegram
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        
        # Header
        header = self._format_header(region_name, cycle, current_week)
        summary = self._format_summary_section(summary_data, cycle, cycle_year, current_week)
        
        message = f"""📊 **{header['title']}** ({self.satuan})
*{header['region']}* - {header['timestamp']}

📈 **SUMMARY {region_name}**
{summary['cycle_info']}
{summary['existing_ach']}
{summary['gd_ach']}
{summary['gd_plt_ach']}

📈 **EXISTING BRAND Week {current_week} vs AE:**
"""
        
        # Existing brands section - GUNAKAN DATA YANG SUDAH DIKELOMPOKKAN
        existing_brands = self._get_existing_brands_robust(regional_data, summary_data, current_week)
        existing_section = self._format_existing_brands_section(existing_brands, current_week)
        
        if existing_section['has_data']:
            max_length = max(8, max(len(item['product']) for item in existing_section['items']))
            
            # Debug: Print untuk melihat data yang diambil
            print(f"DEBUG: Existing brands data for week {current_week}:")
            for item in existing_section['items'][:3]:  # Print 3 item pertama
                print(f"  - {item['product']}: {item['qty']:.1f} box")
            
            for item in existing_section['items']:
                product_name = item['product'].ljust(max_length)
                # GUNAKAN qty dari existing_section yang sudah dikelompokkan
                message += f"• `{product_name}` : {item['qty']:,.1f} box W{current_week} ({item['achievement_pct']:.1f}%)\n"
        else:
            message += f"• Tidak ada Existing Brand dengan quantity > 0 di Week {current_week}\n"
        
        message += "\n"
        
        # New brand section
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        new_brand_section = self._format_new_brand_section(new_brand_data, previous_week_data)
        
        if new_brand_section['has_data']:
            message += "🆕 **NEW BRAND (TW/LW/+/-)** :\n"
            
            if new_brand_section['items']:
                max_new_brand_length = max(8, max(len(item['product']) for item in new_brand_section['items']))
                
                for item in new_brand_section['items']:
                    product_name = item['product'].ljust(max_new_brand_length)
                    message += f"`{product_name}` : {item['current_week']:.1f} / {item['previous_week']:.1f} / {item['difference']:+.0f}\n"
            
            message += f"**Total brand**: {new_brand_section['total_current']:.1f} / {new_brand_section['total_previous']:.1f} / {new_brand_section['total_diff']:+.0f}\n\n"

        message += (
            "📧 Report ini dibuat secara otomatis\n"
            f"*Generated*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return message
    
    def format_whatsapp_message(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan untuk WhatsApp
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        
        # Header
        header = self._format_header(region_name, cycle, current_week)
        summary = self._format_summary_section(summary_data, cycle, cycle_year, current_week)
        
        message = f"""📊 *{header['title']}* ({self.satuan})
_{header['region']}_ - {header['timestamp']}

📈 *SUMMARY {region_name}*
{summary['cycle_info']}
{summary['existing_ach']}
{summary['gd_ach']}
{summary['gd_plt_ach']}

📈 *EXISTING BRAND Week {current_week} vs AE:*
"""
        
        # Existing brands section - PERBAIKAN DI SINI JUGA
        existing_brands = self._get_existing_brands_robust(regional_data, summary_data, current_week)
        existing_section = self._format_existing_brands_section(existing_brands, current_week)
        
        if existing_section['has_data']:
            max_length = max(8, max(len(item['product']) for item in existing_section['items']))
            
            for item in existing_section['items']:
                product_name = item['product'].ljust(max_length)
                message += f"{product_name} : {item['qty']:,.1f} box W{current_week} ({item['achievement_pct']:.1f}%)\n"
        else:
            message += f"• Tidak ada Existing Brand dengan quantity > 0 di Week {current_week}\n"
        
        message += "\n"
        
        # New brand section
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        new_brand_section = self._format_new_brand_section(new_brand_data, previous_week_data)
        
        if new_brand_section['has_data']:
            message += "🆕 *NEW BRAND (TW/LW/+/-)*:\n"
            
            if new_brand_section['items']:
                max_new_brand_length = max(9, max(len(item['product']) for item in new_brand_section['items']))
                
                for item in new_brand_section['items']:
                    product_name = item['product'].ljust(max_new_brand_length)
                    diff_symbol = "+" if item['difference'] >= 0 else ""
                    message += f"{product_name} : {item['current_week']:.1f} / {item['previous_week']:.1f} / {diff_symbol}{item['difference']:.0f}\n"
            
            total_brand_text = "Total brand".ljust(max_new_brand_length if 'max_new_brand_length' in locals() else 8)
            total_diff_symbol = "+" if new_brand_section['total_diff'] >= 0 else ""
            message += f"*{total_brand_text}* : {new_brand_section['total_current']:.1f} / {new_brand_section['total_previous']:.1f} / {total_diff_symbol}{new_brand_section['total_diff']:.0f}\n\n"

        message += (
            "📧 Report ini dibuat secara otomatis\n"
            f"_Generated_: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

📊 *Summary:*
• Existing Brand: {summary_data['current_week_sales_existing']:,.1f} BOX
• New Brand: {summary_data['current_week_sales_new']:,.1f} BOX
• Achievement: {summary_data['achievement_pct_existing']:.1f}%

🎯 *GD Performance:*
• GD Achievement: {summary_data['gd_achievement_pct']:.1f}%
• GD+PLT Achievement: {summary_data['gd_plt_achievement_pct']:.1f}%
        """
        
        return summary_message
    
    def format_whatsapp_message_compact(self, region_name, zpsdt003_data, regional_data, summary_data, previous_week_data, regional_notes=None):
        """
        Format pesan WhatsApp versi kompak
        """
        cycle = zpsdt003_data['cycle']
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
        
        # Top 5 existing brands
        existing_brands = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        existing_brands.sort(key=lambda x: x['qty_billing_sum'], reverse=True)
        
        for i, item in enumerate(existing_brands[:5]):
            achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
            message += f"{i+1}. *{item['matkl_desc']}*: {item['qty_billing_sum']:,.1f} ({achievement_pct:.1f}%)\n"
        
        # Top 5 new brands
        new_brand_data = [item for item in regional_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            message += "\n🆕 *NEW BRAND*\n"
            
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            new_brand_items = [(product, data) for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            new_brand_items.sort(key=lambda x: x[1]['current_week'], reverse=True)
            
            for product, data in new_brand_items[:5]:
                diff_symbol = "+" if data['difference'] >= 0 else ""
                message += f"*{product}*: {data['current_week']:.1f} ({diff_symbol}{data['difference']:.0f})\n"
            
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            total_diff_symbol = "+" if total_diff >= 0 else ""
            message += f"*Total*: {total_current:.1f} ({total_diff_symbol}{total_diff:.0f})\n"
        
        message += f"\n_Auto-generated {datetime.now().strftime('%H:%M')}_"
        
        return message
    
    def format_national_telegram_message(self, zpsdt003_data, national_data, summary_data, previous_week_data):
        """
        Format pesan Telegram untuk laporan nasional
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        
        # Header
        header = self._format_header("NASIONAL", cycle, current_week, is_national=True)
        summary = self._format_summary_section(summary_data, cycle, cycle_year, current_week)
        
        message = f"""🇮🇩 **{header['title']}** ({self.satuan})
*{header['region']}* - {header['timestamp']}

📊 **SUMMARY NASIONAL**
{summary['cycle_info']}
{summary['existing_ach']}
{summary['gd_ach']}
{summary['gd_plt_ach']}

📈 **TOP 10 EXISTING BRAND Vs AE (NASIONAL):**
"""
        
        # Top 10 existing brands
        existing_section = self._format_existing_brands_section(
            [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0],
            current_week, 
            max_items=10
        )
        
        if existing_section['has_data']:
            max_length = max(8, max(len(item['product']) for item in existing_section['items']))
            
            for item in existing_section['items']:
                product_name = item['product'].ljust(max_length)
                message += f"{item['rank']:2d}. `{product_name}` : {item['qty']:,.1f} box ({item['achievement_pct']:.1f}%)\n"
            
            message += f"\n**Total {existing_section['total_brands']} Existing Brands**: {existing_section['total_qty']:,.1f} box\n"
        else:
            message += "• Tidak ada Existing Brand dengan quantity > 0\n"
        
        message += "\n"
        
        # Top 10 new brands
        new_brand_data = [item for item in national_data if item.get('prctr_base') == '0000003998']
        new_brand_section = self._format_new_brand_section(new_brand_data, previous_week_data, max_items=10)
        
        if new_brand_section['has_data']:
            message += "🆕 **TOP 10 NEW BRAND (TW/LW/+/-)** :\n"
            
            if new_brand_section['items']:
                max_new_brand_length = max(8, max(len(item['product']) for item in new_brand_section['items']))
                
                for item in new_brand_section['items']:
                    product_name = item['product'].ljust(max_new_brand_length)
                    message += f"{item['rank']:2d}. `{product_name}` : {item['current_week']:.1f} / {item['previous_week']:.1f} / {item['difference']:+.0f}\n"
            
            message += f"\n**Total {new_brand_section['total_brands']} New Brands**: {new_brand_section['total_current']:.1f} / {new_brand_section['total_previous']:.1f} / {new_brand_section['total_diff']:+.0f}\n\n"
        
        return message
    
    def format_national_whatsapp_message(self, zpsdt003_data, national_data, summary_data, previous_week_data):
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        
        # Header dengan formatting WhatsApp
        message = f"""🇮🇩 *NATIONAL REPORT OMSET W{current_week} CYCLE {cycle}* ({self.satuan})
_INDONESIA NASIONAL_ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 *SUMMARY NASIONAL*
Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.0f}% vs AE

% ACH AE Cy {cycle} (Existing): {summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)
% ACH AE Cy {cycle} (GD): {summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)
% ACH AE Cy {cycle} (GD+PLT): {summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)

📈 *TOP 10 EXISTING BRAND Vs AE:*
"""
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        existing_brands_with_qty.sort(key=lambda x: x['qty_billing_sum'], reverse=True)
        if existing_brands_with_qty:
            top_10_existing = existing_brands_with_qty[:10]
            max_existing_length = max(8, max(len(item['matkl_desc']) for item in top_10_existing))
            for i, item in enumerate(top_10_existing, 1):
                achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
                product_name = item['matkl_desc'].ljust(max_existing_length)
                message += f"{i:2d}. {product_name} : {item['qty_billing_sum']:,.1f} box ({achievement_pct:.1f}%)\n"
            total_existing_brands = len(existing_brands_with_qty)
            total_existing_qty = sum([item['qty_billing_sum'] for item in existing_brands_with_qty])
            message += f"\n*Total {total_existing_brands} Existing Brands*: {total_existing_qty:,.1f} box\n"
        else:
            message += "• Tidak ada Existing Brand dengan quantity > 0\n"
        message += "\n"
        new_brand_data = [item for item in national_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            message += "🆕 *TOP 10 NEW BRAND (TW/LW/+/-)*:\n"
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            new_brand_items = [(product, data) for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            new_brand_items.sort(key=lambda x: x[1]['current_week'], reverse=True)
            top_10_new_brand = new_brand_items[:10]
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            if top_10_new_brand:
                max_new_brand_length = max(8, max(len(product) for product, _ in top_10_new_brand))
                for i, (product, data) in enumerate(top_10_new_brand, 1):
                    product_name = product.ljust(max_new_brand_length)
                    message += f"{i:2d}. {product_name} : {data['current_week']:.1f} / {data['previous_week']:.1f} / {data['difference']:+.0f}\n"
            total_new_brands = len([product for product, data in grouped_new_brand.items() if data['current_week'] > 0])
            message += f"\n*Total {total_new_brands} New Brands*: {total_current:.1f} / {total_previous:.1f} / {total_diff:+.0f}\n\n"
        message += self._format_regional_breakdown_whatsapp(national_data, current_week)
        message += (
            "\n📧 Report nasional dibuat secara otomatis\n"
            f"_Generated_: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return message

    def format_national_email_body(self, zpsdt003_data, national_data, summary_data, previous_week_data):
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        # Header HTML
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2E8B57; color: white; padding: 15px; text-align: center; border-radius: 8px; }}
                .summary {{ background-color: #f0f8ff; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4CAF50; }}
                .section {{ margin: 20px 0; }}
                .brand-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .brand-table th, .brand-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .brand-table th {{ background-color: #4CAF50; color: white; }}
                .brand-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 30px; text-align: center; }}
                .regional-summary {{ background-color: #fff8dc; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🇮🇩 NATIONAL REPORT OMSET WEEKLY W{current_week} CYCLE {cycle} ({self.satuan})</h2>
                <p>INDONESIA NASIONAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h3>📊 SUMMARY NASIONAL</h3>
                <p><strong>Cycle {cycle} {cycle_year} week {current_week}</strong> omset ideal {summary_data['omset_ideal_pct']:.0f}% vs AE</p>
                <ul>
                    <li>% ACH AE Cy {cycle} (Existing): <strong>{summary_data['current_week_sales_existing']:,.1f} Box ({summary_data['achievement_pct_existing']:.1f}%)</strong></li>
                    <li>% ACH AE Cy {cycle} (GD): <strong>{summary_data['gd_current_sales']:,.1f} Box ({summary_data['gd_achievement_pct']:.1f}%)</strong></li>
                    <li>% ACH AE Cy {cycle} (GD+PLT): <strong>{summary_data['gd_plt_current_sales']:,.1f} Box ({summary_data['gd_plt_achievement_pct']:.1f}%)</strong></li>
                </ul>
            </div>
        """
        existing_brands_with_qty = [item for item in summary_data['grouped_existing'] if item['qty_billing_sum'] > 0]
        existing_brands_with_qty.sort(key=lambda x: x['qty_billing_sum'], reverse=True)
        if existing_brands_with_qty:
            html_body += """
            <div class="section">
                <h3>📈 TOP 15 EXISTING BRAND Vs AE (NASIONAL)</h3>
                <table class="brand-table">
                    <thead>
                        <tr>
                            <th>No</th>
                            <th>Product Name</th>
                            <th>Current Week (Box)</th>
                            <th>Achievement (%)</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            top_15_existing = existing_brands_with_qty[:15]
            for i, item in enumerate(top_15_existing, 1):
                achievement_pct = (item['qty_billing_sum'] / item['qty_target_ae'] * 100) if item['qty_target_ae'] > 0 else 0
                html_body += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{item['matkl_desc']}</td>
                            <td>{item['qty_billing_sum']:,.1f}</td>
                            <td>{achievement_pct:.1f}%</td>
                        </tr>
                """
            html_body += """
                    </tbody>
                </table>
            """
            total_existing_brands = len(existing_brands_with_qty)
            total_existing_qty = sum([item['qty_billing_sum'] for item in existing_brands_with_qty])
            html_body += f"<p><strong>Total {total_existing_brands} Existing Brands: {total_existing_qty:,.1f} box</strong></p>"
        else:
            html_body += "<p>• Tidak ada Existing Brand dengan quantity > 0</p>"
        html_body += "</div>"
        new_brand_data = [item for item in national_data if item.get('prctr_base') == '0000003998']
        if new_brand_data:
            html_body += """
            <div class="section">
                <h3>🆕 TOP 15 NEW BRAND (TW/LW/+/-)</h3>
                <table class="brand-table">
                    <thead>
                        <tr>
                            <th>No</th>
                            <th>Product Name</th>
                            <th>This Week</th>
                            <th>Last Week</th>
                            <th>Difference</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            grouped_new_brand = self._group_new_brand_by_product_only(new_brand_data, previous_week_data)
            new_brand_items = [(product, data) for product, data in grouped_new_brand.items() if data['current_week'] > 0]
            new_brand_items.sort(key=lambda x: x[1]['current_week'], reverse=True)
            top_15_new_brand = new_brand_items[:15]
            for i, (product, data) in enumerate(top_15_new_brand, 1):
                diff_style = "color: green;" if data['difference'] > 0 else "color: red;" if data['difference'] < 0 else ""
                html_body += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{product}</td>
                            <td>{data['current_week']:.1f}</td>
                            <td>{data['previous_week']:.1f}</td>
                            <td style="{diff_style}">{data['difference']:+.0f}</td>
                        </tr>
                """
            html_body += """
                    </tbody>
                </table>
            """
            total_current = sum([data['current_week'] for data in grouped_new_brand.values()])
            total_previous = sum([data['previous_week'] for data in grouped_new_brand.values()])
            total_diff = total_current - total_previous
            total_new_brands = len([product for product, data in grouped_new_brand.items() if data['current_week'] > 0])
            diff_style = "color: green;" if total_diff > 0 else "color: red;" if total_diff < 0 else ""
            html_body += f"<p><strong>Total {total_new_brands} New Brands: {total_current:.1f} / {total_previous:.1f} / <span style='{diff_style}'>{total_diff:+.0f}</span></strong></p>"
        html_body += "</div>"
        html_body += self._format_regional_breakdown_email(national_data, current_week)
        # Footer
        html_body += f"""
            <div class="footer">
                <p>📧 Report nasional dibuat secara otomatis</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        return html_body
    def _format_regional_breakdown(self, national_data, current_week):
        regional_groups = {}
        for item in national_data:
            # Ambil regional info - sesuaikan dengan struktur data Anda
            # Misalnya dari field 'vkbur_desc' atau field lain yang menunjukkan regional
            regional_key = item.get('regional', 'Unknown Regional')
            
            if regional_key not in regional_groups:
                regional_groups[regional_key] = {
                    'existing_sales': 0.0,
                    'new_brand_sales': 0.0,
                    'total_sales': 0.0
                }
            
            qty_billing = float(item.get('qty_billing_sum', 0))
            
            # Pisahkan berdasarkan existing vs new brand
            if item.get('prctr_base') == '0000003998':  # New brand
                regional_groups[regional_key]['new_brand_sales'] += qty_billing
            else:  # Existing brand
                regional_groups[regional_key]['existing_sales'] += qty_billing
            
            regional_groups[regional_key]['total_sales'] += qty_billing
        
        # Format output
        breakdown_message = "📍 **REGIONAL BREAKDOWN**\n"
        
        # Sort regional berdasarkan total sales
        sorted_regionals = sorted(regional_groups.items(), key=lambda x: x[1]['total_sales'], reverse=True)
        
        for regional_name, data in sorted_regionals:
            if data['total_sales'] > 0:  # Hanya tampilkan yang ada sales
                breakdown_message += f"• **{regional_name}**\n"
                breakdown_message += f"  - Existing: {data['existing_sales']:,.1f} Box\n"
                breakdown_message += f"  - New Brand: {data['new_brand_sales']:,.1f} Box\n"
                breakdown_message += f"  - Total: {data['total_sales']:,.1f} Box\n\n"
        return breakdown_message
    def _format_regional_breakdown_whatsapp(self, national_data, current_week):
        # Group data berdasarkan regional
        regional_groups = {}
        
        for item in national_data:
            regional_key = item.get('regional', 'Unknown Regional')
            if regional_key not in regional_groups:
                regional_groups[regional_key] = {
                    'existing_sales': 0.0,
                    'new_brand_sales': 0.0,
                    'total_sales': 0.0
                }
            
            qty_billing = float(item.get('qty_billing_sum', 0))
            
            if item.get('prctr_base') == '0000003998':  # New brand
                regional_groups[regional_key]['new_brand_sales'] += qty_billing
            else:  # Existing brand
                regional_groups[regional_key]['existing_sales'] += qty_billing
            
            regional_groups[regional_key]['total_sales'] += qty_billing
        breakdown_message = "📍 *REGIONAL BREAKDOWN*\n"
        sorted_regionals = sorted(regional_groups.items(), key=lambda x: x[1]['total_sales'], reverse=True)
        for regional_name, data in sorted_regionals:
            if data['total_sales'] > 0:
                breakdown_message += f"• *{regional_name}*\n"
                breakdown_message += f"  Existing: {data['existing_sales']:,.1f} | New: {data['new_brand_sales']:,.1f}\n"
                breakdown_message += f"  Total: {data['total_sales']:,.1f} Box\n\n"
        return breakdown_message
    def _format_regional_breakdown_email(self, national_data, current_week):
        regional_groups = {}
        for item in national_data:
            regional_key = item.get('regional', 'Unknown Regional')
            if regional_key not in regional_groups:
                regional_groups[regional_key] = {
                    'existing_sales': 0.0,
                    'new_brand_sales': 0.0,
                    'total_sales': 0.0
                }
            qty_billing = float(item.get('qty_billing_sum', 0))
            if item.get('prctr_base') == '0000003998':  # New brand
                regional_groups[regional_key]['new_brand_sales'] += qty_billing
            else:  # Existing brand
                regional_groups[regional_key]['existing_sales'] += qty_billing
            regional_groups[regional_key]['total_sales'] += qty_billing
        html_breakdown = """
        <div class="section">
            <h3>📍 REGIONAL BREAKDOWN</h3>
            <table class="brand-table">
                <thead>
                    <tr>
                        <th>Regional</th>
                        <th>Existing Sales (Box)</th>
                        <th>New Brand Sales (Box)</th>
                        <th>Total Sales (Box)</th>
                    </tr>
                </thead>
                <tbody>
        """
        sorted_regionals = sorted(regional_groups.items(), key=lambda x: x[1]['total_sales'], reverse=True)
        for regional_name, data in sorted_regionals:
            if data['total_sales'] > 0:
                html_breakdown += f"""
                    <tr>
                        <td><strong>{regional_name}</strong></td>
                        <td>{data['existing_sales']:,.1f}</td>
                        <td>{data['new_brand_sales']:,.1f}</td>
                        <td>{data['total_sales']:,.1f}</td>
                    </tr>
                """
        html_breakdown += """
                </tbody>
            </table>
        </div>
        """
        return html_breakdown