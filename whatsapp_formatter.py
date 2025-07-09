from datetime import datetime
from config import CURRENT_DATE, SATUAN
import logging

class WhatsAppFormatter:
    """
    Formatter khusus untuk pesan WhatsApp
    """
    
    def __init__(self):
        self.max_message_length = 4000  # Batas karakter WhatsApp
    
    def format_whatsapp_message(self, region_name, zpsdt_data, regional_data, summary_data, previous_week_data=None, regional_notes=None):
        """
        Format pesan lengkap untuk WhatsApp
        
        Args:
            region_name: Nama region
            zpsdt_data: Data ZPSDT003
            regional_data: Data regional
            summary_data: Data summary
            previous_week_data: Data week sebelumnya
            regional_notes: Catatan regional
            
        Returns:
            str: Pesan WhatsApp yang diformat
        """
        try:
            cycle = zpsdt_data.get('cycle', 'N/A')
            cycle_year = zpsdt_data.get('cycle_year', 'N/A')
            current_week = int(zpsdt_data.get('week2', 3))
            
            # Header
            message = f"""📊 *WEEKLY SALES REPORT*
🏢 *{region_name}*
📅 {CURRENT_DATE} | W{current_week} C{cycle} - {cycle_year}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            
            # Summary Section
            message += self._format_summary_section(summary_data, current_week)
            
            # Product Performance Section
            message += self._format_product_performance(summary_data)
            
            # Category Performance Section
            message += self._format_category_performance(summary_data)
            
            # Previous Week Comparison (jika ada)
            if previous_week_data:
                message += self._format_previous_week_comparison(summary_data, previous_week_data)
            
            # Regional Notes (jika ada)
            if regional_notes:
                message += self._format_regional_notes(regional_notes)
            
            # Footer
            message += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            message += f"\n🤖 *Auto Report System*"
            message += f"\n📊 Unit: {SATUAN}"
            message += f"\n🕐 Generated: {datetime.now().strftime('%H:%M:%S')}"
            
            # Potong pesan jika terlalu panjang
            if len(message) > self.max_message_length:
                message = message[:self.max_message_length-100] + "\n\n... (pesan dipotong karena terlalu panjang)"
            
            return message
            
        except Exception as e:
            logging.error(f"Error formatting WhatsApp message: {str(e)}")
            return self._format_error_message(region_name, str(e))
    
    def _format_summary_section(self, summary_data, current_week):
        """Format section summary"""
        existing_sales = summary_data.get('current_week_sales_existing', 0)
        new_sales = summary_data.get('current_week_sales_new', 0)
        achievement = summary_data.get('achievement_pct_existing', 0)
        ideal_pct = summary_data.get('omset_ideal_pct', 0)
        
        # Status icon berdasarkan achievement
        if achievement >= 100:
            status_icon = "🟢"
        elif achievement >= 75:
            status_icon = "🟡"
        else:
            status_icon = "🔴"
        
        return f"""📈 *SUMMARY WEEK {current_week}*
{status_icon} Achievement: *{achievement:.1f}%*
🎯 Ideal Progress: {ideal_pct:.1f}%

📦 Existing Brand: *{existing_sales:,.1f}* {SATUAN}
🆕 New Brand: *{new_sales:,.1f}* {SATUAN}
📊 Total Sales: *{existing_sales + new_sales:,.1f}* {SATUAN}

"""
    
    def _format_product_performance(self, summary_data):
        """Format section performa produk"""
        grouped_existing = summary_data.get('grouped_existing', [])
        grouped_new = summary_data.get('grouped_new', [])
        
        message = "🏆 *TOP PRODUCTS*\n"
        
        # Top 3 Existing Products
        if grouped_existing:
            sorted_existing = sorted(grouped_existing, key=lambda x: x.get('qty_billing_sum', 0), reverse=True)
            message += "\n*Existing Brand:*\n"
            for i, product in enumerate(sorted_existing[:3], 1):
                qty = product.get('qty_billing_sum', 0)
                name = product.get('matkl_desc', 'Unknown')[:30]  # Batasi nama produk
                message += f"{i}. {name}: {qty:,.1f} {SATUAN}\n"
        
        # Top 3 New Products
        if grouped_new:
            sorted_new = sorted(grouped_new, key=lambda x: x.get('qty_billing_sum', 0), reverse=True)
            message += "\n*New Brand:*\n"
            for i, product in enumerate(sorted_new[:3], 1):
                qty = product.get('qty_billing_sum', 0)
                name = product.get('matkl_desc', 'Unknown')[:30]  # Batasi nama produk
                message += f"{i}. {name}: {qty:,.1f} {SATUAN}\n"
        
        return message + "\n"
    
    def _format_category_performance(self, summary_data):
        """Format section performa kategori"""
        gd_achievement = summary_data.get('gd_achievement_pct', 0)
        gd_plt_achievement = summary_data.get('gd_plt_achievement_pct', 0)
        gd_sales = summary_data.get('gd_current_sales', 0)
        gd_plt_sales = summary_data.get('gd_plt_current_sales', 0)
        
        message = "📊 *CATEGORY PERFORMANCE*\n"
        
        # GD Performance
        gd_icon = "🟢" if gd_achievement >= 100 else "🟡" if gd_achievement >= 75 else "🔴"
        message += f"{gd_icon} *GD*: {gd_achievement:.1f}% ({gd_sales:,.1f} {SATUAN})\n"
        
        # GD + PLT Performance
        gd_plt_icon = "🟢" if gd_plt_achievement >= 100 else "🟡" if gd_plt_achievement >= 75 else "🔴"
        message += f"{gd_plt_icon} *GD+PLT*: {gd_plt_achievement:.1f}% ({gd_plt_sales:,.1f} {SATUAN})\n"
        
        return message + "\n"
    
    def _format_previous_week_comparison(self, summary_data, previous_week_data):
        """Format perbandingan dengan week sebelumnya"""
        if not previous_week_data:
            return ""
        
        current_total = summary_data.get('current_week_sales_existing', 0) + summary_data.get('current_week_sales_new', 0)
        previous_total = sum([item.get('qty_billing_sum', 0) for item in previous_week_data])
        
        if previous_total > 0:
            growth = ((current_total - previous_total) / previous_total) * 100
            growth_icon = "📈" if growth >= 0 else "📉"
            
            return f"""📊 *WEEK-ON-WEEK COMPARISON*
{growth_icon} Growth: {growth:+.1f}%
📊 Previous Week: {previous_total:,.1f} {SATUAN}
📊 Current Week: {current_total:,.1f} {SATUAN}

"""
        return ""
    
    def _format_regional_notes(self, regional_notes):
        """Format catatan regional"""
        if not regional_notes or not regional_notes.get('notes'):
            return ""
        
        notes = regional_notes.get('notes', '').strip()
        if len(notes) > 200:  # Batasi panjang notes
            notes = notes[:200] + "..."
        
        return f"""💬 *REGIONAL NOTES*
{notes}

"""
    
    def _format_error_message(self, region_name, error_msg):
        """Format pesan error"""
        return f"""❌ *ERROR REPORT*
🏢 Region: {region_name}
📅 Date: {CURRENT_DATE}
🚨 Error: {error_msg}

Silakan hubungi IT Support untuk bantuan.
"""
    
    def format_summary_only(self, region_name, summary_data, cycle, current_week):
        """
        Format pesan summary singkat saja
        
        Args:
            region_name: Nama region
            summary_data: Data summary
            cycle: Cycle number
            current_week: Week number
            
        Returns:
            str: Pesan summary singkat
        """
        existing_sales = summary_data.get('current_week_sales_existing', 0)
        new_sales = summary_data.get('current_week_sales_new', 0)
        achievement = summary_data.get('achievement_pct_existing', 0)
        
        # Status icon
        if achievement >= 100:
            status_icon = "🟢"
        elif achievement >= 75:
            status_icon = "🟡"
        else:
            status_icon = "🔴"
        
        return f"""📊 *W{current_week} C{cycle} - {region_name}*
{status_icon} Achievement: *{achievement:.1f}%*

📦 Existing: {existing_sales:,.1f} {SATUAN}
🆕 New: {new_sales:,.1f} {SATUAN}
📊 Total: {existing_sales + new_sales:,.1f} {SATUAN}

#WeeklyReport #Cycle{cycle}"""
    
    def format_test_message(self):
        """Format pesan test"""
        return f"""🧪 *TEST MESSAGE*
📅 {CURRENT_DATE}
🕐 {datetime.now().strftime('%H:%M:%S')}

WhatsApp Service berhasil terhubung!
🚀 Report system siap digunakan.

#TestMessage #ReportSystem"""