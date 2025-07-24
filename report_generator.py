from datetime import datetime
from config import CURRENT_DATE, SATUAN
import smtplib
import logging
import math
from database_service import DatabaseService
from data_processor import DataProcessor
from sap_service import SAPService
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sap_service import SAPService
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_FROM
import pandas as pd
from datetime import datetime
import os

class ReportGenerator:
    def __init__(self):
        self.current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')
        self.db_service = DatabaseService()
        self.sap_service = SAPService()
        self.data_processor = DataProcessor()
        self.sap_service = SAPService()
    
    def round_up_percentage(self, value, decimals=0):
        """
        Round percentage up to specified decimal places
        """
        multiplier = 10 ** decimals
        return math.ceil(value * multiplier) / multiplier
    
    def parse_sap_date(self, sap_date_str):
        if sap_date_str.startswith('/Date(') and sap_date_str.endswith(')/'):
            timestamp = int(sap_date_str[6:-2])
            return datetime.fromtimestamp(timestamp / 1000)
        return None
    
    def find_matching_zpsdt003(self, zpsdt003_data):
        """
        Find ZPSDT003 data that matches the current date
        """
        matching_data = []
        
        for data in zpsdt003_data:
            fromdat = self.parse_sap_date(data['fromdat'])
            todat = self.parse_sap_date(data['todat'])
            
            if fromdat and todat:
                if fromdat <= self.current_date <= todat:
                    matching_data.append(data)
                    print(f"Found matching data: Cycle {data['cycle']}, Year {data['cycle_year']}")
                    print(f"Date range: {fromdat.strftime('%Y-%m-%d')} to {todat.strftime('%Y-%m-%d')}")
        
        return matching_data
    
    def group_brand_data_by_region(self, brand_data_list):
        grouped = {}
        for brand in brand_data_list:
            region = brand.get('regional_desc', 'Unknown Region')
            if region not in grouped:
                grouped[region] = []
            grouped[region].append(brand)
        return grouped
    
    def calculate_regional_summary(self, regional_data, current_week, total_weeks_in_cycle):
        category3_groups = {}
        for item in regional_data:
            category3 = item.get('category3', 'Unknown')
            if category3 not in category3_groups:
                category3_groups[category3] = []
            category3_groups[category3].append(item)
        
        category3_summary = {}
        for category3, items in category3_groups.items():
            current_week_sales = sum([float(item.get('qty_billing_sum', 0)) for item in items])
            total_w1_to_current = current_week_sales * current_week
            qty_target_ae_w1_to_current = sum([float(item.get('qty_target_ae', 0)) for item in items]) * current_week
            achievement_pct = (total_w1_to_current / qty_target_ae_w1_to_current * 100) if qty_target_ae_w1_to_current > 0 else 0
            achievement_pct = self.round_up_percentage(achievement_pct)
            
            category3_summary[category3] = {
                'current_week_sales': current_week_sales,
                'total_w1_to_current': total_w1_to_current,
                'qty_target_ae_w1_to_current': qty_target_ae_w1_to_current,
                'achievement_pct': achievement_pct,
                'data': items
            }
        
        omset_ideal_pct = (current_week / total_weeks_in_cycle * 100) if total_weeks_in_cycle > 0 else 0
        omset_ideal_pct = self.round_up_percentage(omset_ideal_pct)
        
        gd_data = [item for item in regional_data if item.get('category1') == 'GD']
        gd_current_sales = sum([float(item.get('qty_billing_sum', 0)) for item in gd_data])
        gd_qty_target_ae = sum([float(item.get('qty_target_ae', 0)) for item in gd_data]) * current_week
        gd_achievement_pct = (gd_current_sales * current_week / gd_qty_target_ae * 100) if gd_qty_target_ae > 0 else 0
        gd_achievement_pct = self.round_up_percentage(gd_achievement_pct)
        
        gd_plt_data = [item for item in regional_data if item.get('category1') in ['GD', 'PLT']]
        gd_plt_current_sales = sum([float(item.get('qty_billing_sum', 0)) for item in gd_plt_data])
        gd_plt_qty_target_ae = sum([float(item.get('qty_target_ae', 0)) for item in gd_plt_data]) * current_week
        gd_plt_achievement_pct = (gd_plt_current_sales * current_week / gd_plt_qty_target_ae * 100) if gd_plt_qty_target_ae > 0 else 0
        gd_plt_achievement_pct = self.round_up_percentage(gd_plt_achievement_pct)
        
        total_current_sales = sum([float(item.get('qty_billing_sum', 0)) for item in regional_data])
        
        return {
            'category3_summary': category3_summary,
            'omset_ideal_pct': omset_ideal_pct,
            'gd_current_sales': gd_current_sales,
            'gd_achievement_pct': gd_achievement_pct,
            'gd_plt_current_sales': gd_plt_current_sales,
            'gd_plt_achievement_pct': gd_plt_achievement_pct,
            'total_current_sales': total_current_sales,
            'gd_data': gd_data,
            'gd_plt_data': gd_plt_data
        }
    
    def create_regional_email_body(self, region_name, zpsdt003_data, regional_data, summary_data, regional_notes=None):
        """
        Membuat body email untuk regional tertentu dengan format yang diminta menggunakan category3
        """
        cycle = zpsdt003_data['cycle']
        cycle_year = zpsdt003_data['cycle_year']
        current_week = int(zpsdt003_data.get('week2', 3))
        total_weeks = 4  # Asumsi 4 week dalam 1 cycle, bisa disesuaikan
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                .header {{ background-color: #2196F3; color: white; padding: 15px; text-align: center; margin-bottom: 20px; }}
                .summary {{ background-color: #f0f8ff; padding: 15px; margin-bottom: 20px; border-left: 4px solid #2196F3; }}
                .highlight {{ font-weight: bold; color: #1976D2; }}
                .achievement {{ font-size: 16px; font-weight: bold; margin: 10px 0; }}
                .category-skm {{ color: #4CAF50; }}
                .category-skt {{ color: #FF9800; }}
                .gd {{ color: #FF9800; }}
                .gd-plt {{ color: #9C27B0; }}
                .total-evo {{ color: #2196F3; }}
                .section {{ margin: 20px 0; padding: 15px; background-color: #fafafa; border-radius: 5px; }}
                .notes {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .notes-title {{ font-weight: bold; color: #856404; margin-bottom: 10px; }}
                .notes-content {{ color: #856404; }}
                .footer {{ margin-top: 30px; padding: 15px; background-color: #f5f5f5; font-style: italic; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 Report Omset Weekly W{current_week} Cycle {cycle} ({SATUAN})</h2>
                <p>{region_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="summary">
                <h3>{region_name} Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.2f}% (dalam 1 cycle / current_week contoh {total_weeks}/{current_week} = {summary_data['omset_ideal_pct']:.2f}%) vs AE</h3>
                <div class="achievement gd">
                    % ACH AE Cy {cycle} (All Brand): {summary_data['gd_current_sales']:,.3f} Box ( {summary_data['gd_achievement_pct']:.2f}% )
                </div>
                <div class="achievement gd-plt">
                    % ACH AE Cy {cycle} (All Brand+PLT): {summary_data['gd_plt_current_sales']:,.3f} Box ( {summary_data['gd_plt_achievement_pct']:.2f}% )
                </div>
            </div>
        """
        
        # Display each category3 group
        for category3, category_data in summary_data['category3_summary'].items():
            css_class = 'category-skm' if category3 == 'SKM' else 'category-skt' if category3 == 'SKT' else 'highlight'
            html_body += f"""
            <div class="section">
                <h4 class="{css_class}">📈 Category {category3}:</h4>
                <div class="achievement {css_class}">
                    % ACH AE Cy {cycle} ({category3}): {category_data['current_week_sales']:,.3f} Box ( {category_data['achievement_pct']:.2f}% )
                </div>
            """
            
            # Show items with quantity > 0
            items_with_qty = [item for item in category_data['data'] if float(item.get('qty_billing_sum', 0)) > 0]
            if items_with_qty:
                for item in items_with_qty:
                    achievement_pct = (float(item.get('qty_billing_sum', 0)) / float(item.get('qty_target_ae', 0)) * 100) if float(item.get('qty_target_ae', 0)) > 0 else 0
                    achievement_pct = self.round_up_percentage(achievement_pct)
                    html_body += f"""
                        <div class="highlight">
                            {item.get('matnr', 'N/A')} ({item.get('matkl_desc', 'N/A')}) : {float(item.get('qty_billing_sum', 0)):,.3f} box ({achievement_pct:.2f}%) Vs AE
                        </div>
                    """
            else:
                html_body += f"""
                    <div class="highlight">
                        Tidak ada {category3} dengan quantity > 0
                    </div>
                """
            html_body += "</div>"
        
        vkbur_descs = list(set([item.get('vkbur_desc', 'N/A') for item in regional_data]))
        html_body += f"""
        <div class="section">
            <h4 class="total-evo">🔄 TOTAL EVO (semua category):</h4>
        """
        for office in vkbur_descs:
            office_data = [item for item in regional_data if item.get('vkbur_desc') == office]
            current_week_total = sum([float(item.get('qty_billing_sum', 0)) for item in office_data])
            last_week_total = current_week_total * 1.12  # Asumsi week lalu 12% lebih tinggi
            difference = current_week_total - last_week_total
            html_body += f"""
            <div class="highlight">
                {office} : {current_week_total:.3f} / {last_week_total:.3f} / {difference:.3f}
            </div>
            """
        html_body += "</div>"
        
        if regional_notes:
            html_body += f"""
            <div class="notes">
                <div class="notes-title">📝 Notes Regional {region_name}:</div>
                <div class="notes-content">{regional_notes}</div>
            </div>
            """
        
        html_body += f"""
            <div class="footer">
                📧 Report ini dibuat secara otomatis oleh sistem SAP Integration<br>
                Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                Contact: {EMAIL_FROM}
            </div>
        </body>
        </html>
        """
        return html_body
    
    def send_email(self, recipient_emails, subject, html_body):
        """
        Mengirim email dengan body HTML
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = EMAIL_FROM
            msg['To'] = ', '.join(recipient_emails) if isinstance(recipient_emails, list) else recipient_emails
            msg['Subject'] = subject
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
            server.login(SMTP_USER, SMTP_PASS)
            text = msg.as_string()
            server.sendmail(EMAIL_FROM, recipient_emails, text)
            server.quit()
            print(f"Email berhasil dikirim ke: {recipient_emails}")
            return True
        except Exception as e:
            print(f"Error mengirim email: {str(e)}")
            return False
        
    def process_and_send_report(self):
        recipient_emails = self.db_service.get_recipients_from_db()
        zpsdt003_data = self.sap_service.load_zpsdt003_data()
        brand_data = self.sap_service.load_brand_data()
        matching_zpsdt003 = self.find_matching_zpsdt003(zpsdt003_data)
        
        if not matching_zpsdt003:
            print(f"Tidak ada data ZPSDT003 yang sesuai untuk tanggal {CURRENT_DATE}")
        
        for zpsdt_data in matching_zpsdt003:
            cycle_year = str(zpsdt_data['cycle_year'])
            cycle = str(zpsdt_data['cycle'])
            current_week = int(zpsdt_data.get('week2', 3))
            total_weeks = 4
            
            matching_brands = [
                brand for brand in brand_data 
                if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
            ]
            
            if matching_brands:
                
                regional_groups = self.group_brand_data_by_region(matching_brands)
                
                for region, count in [(r, len(d)) for r, d in regional_groups.items()]:
                    print(f"  - {region}: {count} records")
                
                for region_name, regional_data in regional_groups.items():
                    
                    if regional_data:
                        category3_dist = {}
                        for item in regional_data:
                            category3 = item.get('category3', 'Unknown')
                            category3_dist[category3] = category3_dist.get(category3, 0) + 1
                    
                    regional_notes = None
                    
                    summary_data = self.calculate_regional_summary(regional_data, current_week, total_weeks)
                    
                    email_body = self.create_regional_email_body(region_name, zpsdt_data, regional_data, summary_data, regional_notes)
                    
                    subject = f"📊 Weekly Report W{current_week} Cycle {cycle} | {region_name} | {CURRENT_DATE}"
                    
                    success = self.send_email(recipient_emails, subject, email_body)
                    
                    if success:
                        print(f"   - Category3 Groups: {len(summary_data['category3_summary'])} groups")
                        for category3, data in summary_data['category3_summary'].items():
                            print(f"     - {category3}: {data['current_week_sales']:,.3f} BOX ({data['achievement_pct']:.2f}%)")
                        if regional_notes:
                            print(f"   - Notes: {regional_notes[:50]}...")
                        else:
                            print(f"   - Notes: Tidak ada")
                    else:
                        print(f"❌ Gagal mengirim laporan untuk {region_name}")
            else:
                print(f"⚠️  Data brand tidak ditemukan untuk Cycle {cycle}, Year {cycle_year}")
        
        return True

    def generate_national_report(self, merged_brands, cycle_year, cycle, current_week, current_week2):
        try:
            summary_with_regional = self.data_processor.create_summary_with_regional(merged_brands)
            
            if not summary_with_regional:
                logging.warning("Tidak ada data summary untuk national report.")
                return None

            omset_ideal_percentage = (current_week2 / 4 * 100)
            
            def safe_float(value):
                try:
                    return float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            available_weeks = set()
            available_cycles = set()
            data_samples = {}
            
            for item in summary_with_regional:
                item_cycle = str(item.get('cycle', ''))
                item_week = str(item.get('week1', ''))
                item_brand = item.get('category5', 'Unknown')
                item_value = safe_float(item.get('qty_billing_sum'))
                
                available_cycles.add(item_cycle)
                cycle_week_combo = f"Cy{item_cycle}_W{item_week}"
                available_weeks.add(cycle_week_combo)
                
                if cycle_week_combo not in data_samples:
                    data_samples[cycle_week_combo] = []
                data_samples[cycle_week_combo].append({
                    'brand': item_brand,
                    'value': item_value,
                    'cycle': item_cycle,
                    'week': item_week
                })
            current_week_str = str(current_week)
            current_week2_str = str(current_week2)
            cycle_str = str(cycle)
            
            possible_current_week_keys = [
                f"Cy{cycle_str}_W{current_week2_str}",  
                f"Cy{cycle_str}_W{current_week_str}",   
            ]
            
            if int(cycle_str) > 1:
                possible_current_week_keys.extend([
                    f"Cy{int(cycle_str)-1}_W{current_week2_str}",
                    f"Cy{int(cycle_str)-1}_W{current_week_str}",
                ])
            
            current_week_to_use = None
            current_week_key_found = None
            current_cycle_to_use = cycle_str
            
            for i, test_key in enumerate(possible_current_week_keys):
                is_available = test_key in available_weeks
                has_data = False
                data_count = 0
                
                if is_available and test_key in data_samples:
                    data_with_values = [s for s in data_samples[test_key] if s['value'] > 0]
                    has_data = len(data_with_values) > 0
                    data_count = len(data_with_values)
                
                if has_data and not current_week_to_use:
                    cycle_part, week_part = test_key.replace('Cy', '').split('_W')
                    current_cycle_to_use = cycle_part
                    current_week_to_use = week_part
                    current_week_key_found = test_key
                    break
            
            if not current_week_to_use:
                for test_cycle in sorted(available_cycles, reverse=True):
                    test_key = f"Cy{test_cycle}_W{current_week2_str}"
                    if test_key in available_weeks:
                        current_cycle_to_use = test_cycle
                        current_week_to_use = current_week2_str
                        current_week_key_found = test_key
                        break
                
                if not current_week_to_use:
                    current_cycle_to_use = cycle_str
                    current_week_to_use = current_week2_str
                    current_week_key_found = f"Cy{cycle_str}_W{current_week2_str}"
            
            current_week_int = int(current_week_to_use)
            current_cycle_int = int(current_cycle_to_use)
            
            previous_week_candidates = []
            
            for week_offset in [1, 2, 3]:
                if current_week_int > week_offset:
                    previous_week_candidates.append((current_cycle_to_use, str(current_week_int - week_offset)))
            
            if current_cycle_int > 1:
                prev_cycle_str = str(current_cycle_int - 1)
                previous_week_candidates.append((prev_cycle_str, current_week_to_use))
                for test_week in [str(current_week_int + 1), str(current_week_int - 1), "4", "3", "2", "1"]:
                    if test_week != current_week_to_use:  # Avoid duplicate
                        previous_week_candidates.append((prev_cycle_str, test_week))
            
            previous_cycle = None
            previous_week = None
            
            for i, (candidate_cycle, candidate_week) in enumerate(previous_week_candidates):
                candidate_key = f"Cy{candidate_cycle}_W{candidate_week}"
                is_available = candidate_key in available_weeks
                
                has_data = False
                data_count = 0
                if is_available and candidate_key in data_samples:
                    data_with_values = [s for s in data_samples[candidate_key] if s['value'] > 0]
                    has_data = len(data_with_values) > 0
                    data_count = len(data_with_values)
                
                if has_data and not previous_cycle:
                    previous_cycle = candidate_cycle
                    previous_week = candidate_week
                    break
            
            if not previous_cycle:
                for combo, samples in data_samples.items():
                    if any(s['value'] > 0 for s in samples) and combo != current_week_key_found:
                        parts = combo.replace('Cy', '').split('_W')
                        if len(parts) == 2:
                            previous_cycle = parts[0]
                            previous_week = parts[1]
                            break
                
                if not previous_cycle:
                    previous_cycle = str(current_cycle_int - 1) if current_cycle_int > 1 else current_cycle_to_use
                    previous_week = str(current_week_int - 1) if current_week_int > 1 else "1"
            
            category5_summary = {}
            processed_items = 0
            current_week_matches = 0
            previous_week_matches = 0
            
            current_week_key = f"{current_cycle_to_use}_{current_week_to_use}"
            previous_week_key = f"{previous_cycle}_{previous_week}"
            
            for item in summary_with_regional:
                processed_items += 1
                category5 = item.get('category5')
                week = str(item['week1'])
                cycle_item = str(item.get('cycle'))
                billing_value = safe_float(item.get('qty_billing_sum'))
                target_value = safe_float(item.get('qty_target_ae'))
                
                if not category5:
                    continue
                    
                if category5 not in category5_summary:
                    category5_summary[category5] = {
                        'qty_billing_sum': 0.0,
                        'qty_target_ae': 0.0,
                        'weeks_data': {},
                        'category1': item.get('category1'),
                        'category2': item.get('category2'),
                        'category3': item.get('category3'),
                        'order': item.get('order', 0),
                        'processed_targets': set()
                    }
                
                target_key = f"{cycle_item}_{week}_{category5}"
                if cycle_item == current_cycle_to_use and target_value > 0 and target_key not in category5_summary[category5]['processed_targets']:
                    category5_summary[category5]['qty_target_ae'] += target_value
                    category5_summary[category5]['processed_targets'].add(target_key)
                
                if cycle_item == current_cycle_to_use:
                    category5_summary[category5]['qty_billing_sum'] += billing_value
                
                cycle_week_key = f"{cycle_item}_{week}"
                
                if cycle_week_key not in category5_summary[category5]['weeks_data']:
                    category5_summary[category5]['weeks_data'][cycle_week_key] = 0.0
                category5_summary[category5]['weeks_data'][cycle_week_key] += billing_value
                
                if cycle_item == current_cycle_to_use and week == current_week_to_use:
                    current_week_matches += 1
                elif cycle_item == previous_cycle and week == previous_week:
                    previous_week_matches += 1
            
            matched_summary = {}
            for category5, data in category5_summary.items():
                tw_value = data['weeks_data'].get(current_week_key, 0)
                lw_value = data['weeks_data'].get(previous_week_key, 0)
                total_billing = data['qty_billing_sum']
                total_target = data['qty_target_ae']
                
                if tw_value > 0 or lw_value > 0 or total_billing > 0 or total_target > 0:
                    matched_summary[category5] = {
                        'category5': category5,
                        'qty_billing_sum': total_billing,
                        'qty_target_ae': total_target,
                        'weeks_data': data['weeks_data'],
                        'category1': data['category1'],
                        'category2': data['category2'],
                        'category3': data['category3'],
                        'order': data['order']
                    }
            
            if not matched_summary:
                return 
            
            category3_groups = {}
            for category5, data in matched_summary.items():
                category3 = data['category3'] or 'UNKNOWN'
                if category3 not in category3_groups:
                    category3_groups[category3] = {}
                category3_groups[category3][category5] = data
            
            category3_summary = {}
            for category3, brands in category3_groups.items():
                current_week_sum = 0
                previous_week_sum = 0
                total_billing = 0
                total_target = 0
                
                for category5, data in brands.items():
                    current_week_sum += data['weeks_data'].get(current_week_key, 0)
                    previous_week_sum += data['weeks_data'].get(previous_week_key, 0)
                    total_billing += data['qty_billing_sum']
                    total_target += data['qty_target_ae']
                
                percentage = (total_billing / total_target * 100) if total_target > 0 else 0
                
                category3_summary[category3] = {
                    'current_week_sum': current_week_sum,
                    'previous_week_sum': previous_week_sum,
                    'total_billing': total_billing,
                    'total_target': total_target,
                    'percentage': percentage,
                    'brands': brands
                }

            gd_current_week = 0
            gd_previous_week = 0
            gd_total_billing = 0
            gd_total_target = 0
            
            for category5, data in matched_summary.items():
                if data['category2'] == 'GD' or data['category1'] == 'GD':
                    gd_current_week += data['weeks_data'].get(current_week_key, 0)
                    gd_previous_week += data['weeks_data'].get(previous_week_key, 0)
                    gd_total_billing += data['qty_billing_sum']
                    gd_total_target += data['qty_target_ae']
            
            gd_percentage = (gd_total_billing / gd_total_target * 100) if gd_total_target > 0 else 0

            gd_plt_current_week = 0
            gd_plt_previous_week = 0
            gd_plt_total_billing = 0
            gd_plt_total_target = 0
            
            for category5, data in matched_summary.items():
                if data['category2'] in ['GD', 'PLT'] or data['category1'] in ['GD', 'PLT']:
                    gd_plt_current_week += data['weeks_data'].get(current_week_key, 0)
                    gd_plt_previous_week += data['weeks_data'].get(previous_week_key, 0)
                    gd_plt_total_billing += data['qty_billing_sum']
                    gd_plt_total_target += data['qty_target_ae']
            
            gd_plt_percentage = self.round_up_percentage(gd_plt_total_billing / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0

            report_lines = []
            
            report_lines.append("```")
            report_lines.append(f"📊 NATIONAL REPORT OMSET WEEKLY (BOX)")
            report_lines.append(f"📋 National")
            report_lines.append(f"📅 Cy {current_cycle_to_use} {cycle_year} week {current_week_to_use} omset ideal {omset_ideal_percentage:.0f}% vs FUF")
            report_lines.append("```")
            
            report_lines.append("```")
            report_lines.append(f"CATEGORY TW | LW | +/- | ACH%")
            report_lines.append("─" * 26)
            
            categories_displayed = 0
            for category3, summary in sorted(category3_summary.items()):
                current_week_sum = summary['current_week_sum']
                previous_week_sum = summary['previous_week_sum']
                
                if current_week_sum > 0 or previous_week_sum > 0 or summary['total_billing'] > 0:
                    categories_displayed += 1
                    difference = current_week_sum - previous_week_sum
                    diff_str = f"{difference:3.0f}" if difference >= 0 else f"{difference:4.0f}"
                    category3_name = (category3[:8] + "..") if len(category3) > 8 else category3
                    report_lines.append(f"{category3_name:<6}:{current_week_sum:>6.1f}|{previous_week_sum:>6.1f}|{diff_str:>5s}|{summary['percentage']:>3.0f}%")
            
            if gd_current_week > 0 or gd_previous_week > 0 or gd_total_billing > 0:
                categories_displayed += 1
                gd_difference = gd_current_week - gd_previous_week
                gd_diff_str = f"{gd_difference:3.0f}" if gd_difference >= 0 else f"{gd_difference:4.0f}"
                report_lines.append(f"{'GD':<6}:{gd_current_week:>6.1f}|{gd_previous_week:>6.1f}|{gd_diff_str:>5s}|{gd_percentage:>3.0f}%")
            
            total_tw = sum(s['current_week_sum'] for s in category3_summary.values())
            total_lw = sum(s['previous_week_sum'] for s in category3_summary.values())
            total_billing = sum(s['total_billing'] for s in category3_summary.values())
            total_target = sum(s['total_target'] for s in category3_summary.values())
            total_percentage = (total_billing / total_target * 100) if total_target > 0 else 0
            total_diff = total_tw - total_lw
            total_diff_str = f"{total_diff:3.0f}" if total_diff >= 0 else f"{total_diff:4.0f}"
            
            report_lines.append("─" * 26)
            report_lines.append(f"{'TOTAL':<6}:{total_tw:>6.1f}|{total_lw:>6.1f}|{total_diff_str:>5s}|{total_percentage:>3.0f}%")
            report_lines.append("```")
            report_lines.append("")

            if categories_displayed == 0:
                report_lines.append("❌ Tidak ada data kategori yang dapat ditampilkan.")
                report_lines.append(f"Debug info: Found {len(matched_summary)} brands, {len(category3_groups)} categories")
                report_lines.append("")
            
            # Brand performance sections
            brands_sections_added = 0
            for category3 in sorted(category3_groups.keys()):
                brands = category3_groups[category3]
                meaningful_brands = []
                
                for category5, data in brands.items():
                    current_week_sum = data['weeks_data'].get(current_week_key, 0)
                    previous_week_sum = data['weeks_data'].get(previous_week_key, 0)
                    if current_week_sum > 0 or previous_week_sum > 0 or data['qty_billing_sum'] > 0:
                        meaningful_brands.append((category5, data))
                
                if meaningful_brands:
                    brands_sections_added += 1
                    report_lines.append(f"📈 {category3} BRAND PERFORMANCE:")
                    
                    report_lines.append("```")
                    report_lines.append(f"BRAND      TW | LW | +/- | ACH%")
                    report_lines.append("─" * 26)
                    
                    sorted_brands = sorted(meaningful_brands, key=lambda x: (x[1]['order'], x[0]))
                    
                    for category5, data in sorted_brands:
                        current_week_sum = data['weeks_data'].get(current_week_key, 0)
                        previous_week_sum = data['weeks_data'].get(previous_week_key, 0)
                        
                        difference = current_week_sum - previous_week_sum
                        diff_str = f"{difference:3.0f}" if difference >= 0 else f"{difference:4.0f}"
                        ach_percentage = (data['qty_billing_sum'] / data['qty_target_ae'] * 100) if data['qty_target_ae'] > 0 else 0
                        brand_name = (category5[:10] + "..") if len(category5) > 10 else category5
                        report_lines.append(f"{brand_name:<6}:{current_week_sum:>5.1f}|{previous_week_sum:>5.1f}|{diff_str:>5s}|{ach_percentage:>3.0f}%")
                    
                    report_lines.append("```")
                    report_lines.append("")
            
            if brands_sections_added == 0:
                report_lines.append("❌ Tidak ada data brand yang dapat ditampilkan.")
                report_lines.append("")

            report_message = "\n".join(report_lines)
            return report_message

        except Exception as e:
            logging.error(f"Error generating national report: {e}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return f"❌ Error generating national report: {str(e)}"
    
    def generate_regional_report(self, merged_brands, cycle_year, cycle, current_week, regional_desc, current_week2, merger_detail):
        try:
            if not merged_brands:
                return None
            
            summary_with_regional = self.data_processor.create_summary_with_regional(merged_brands)
            if not summary_with_regional:
                return None
            
            regional_data = [item for item in summary_with_regional if item['regional_desc'] == regional_desc]
            if not regional_data:
                return None
            
            omset_ideal_percentage = (current_week2 / 4 * 100)
            
            def safe_float(value):
                try:
                    return float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            available_weeks = set()
            available_cycles = set()
            data_samples = {}
            regional_items_count = 0
            
            for item in summary_with_regional:
                if item['regional_desc'] == regional_desc:
                    regional_items_count += 1
                    item_cycle = str(item.get('cycle', ''))
                    item_week = str(item.get('week1', ''))
                    item_brand = item.get('category5', 'Unknown')
                    item_value = safe_float(item.get('qty_billing_sum'))
                    
                    available_cycles.add(item_cycle)
                    cycle_week_combo = f"Cy{item_cycle}_W{item_week}"
                    available_weeks.add(cycle_week_combo)
                    
                    if cycle_week_combo not in data_samples:
                        data_samples[cycle_week_combo] = []
                    data_samples[cycle_week_combo].append({
                        'brand': item_brand,
                        'value': item_value,
                        'cycle': item_cycle,
                        'week': item_week
                    })
                    
            for combo, samples in sorted(data_samples.items()):
                sample_count = len(samples)
                total_value = sum(s['value'] for s in samples)
                non_zero_count = len([s for s in samples if s['value'] > 0])
                
                top_brands = sorted([s for s in samples if s['value'] > 0], 
                                key=lambda x: x['value'], reverse=True)[:3]
            
            current_week_str = str(current_week)
            current_week2_str = str(current_week2)
            cycle_str = str(cycle)
            
            possible_current_week_keys = [
                f"Cy{cycle_str}_W{current_week2_str}",
                f"Cy{cycle_str}_W{current_week_str}",
            ]
            
            if int(cycle_str) > 1:
                possible_current_week_keys.extend([
                    f"Cy{int(cycle_str)-1}_W{current_week2_str}",
                    f"Cy{int(cycle_str)-1}_W{current_week_str}",
                ])
            
            current_week_to_use = None
            current_week_key_found = None
            current_cycle_to_use = cycle_str
            
            for i, test_key in enumerate(possible_current_week_keys):
                is_available = test_key in available_weeks
                has_data = False
                data_count = 0
                
                if is_available and test_key in data_samples:
                    data_with_values = [s for s in data_samples[test_key] if s['value'] > 0]
                    has_data = len(data_with_values) > 0
                    data_count = len(data_with_values)
                
                status = f"✓ HAS DATA ({data_count} items)" if has_data else ("✓ AVAILABLE (no values)" if is_available else "✗ not available")
                
                if has_data and not current_week_to_use:
                    cycle_part, week_part = test_key.replace('Cy', '').split('_W')
                    current_cycle_to_use = cycle_part
                    current_week_to_use = week_part
                    current_week_key_found = test_key
                    break
            
            if not current_week_to_use:
                for test_cycle in sorted(available_cycles, reverse=True):
                    test_key = f"Cy{test_cycle}_W{current_week2_str}"
                    if test_key in available_weeks:
                        current_cycle_to_use = test_cycle
                        current_week_to_use = current_week2_str
                        current_week_key_found = test_key
                        break
                
                if not current_week_to_use:
                    current_cycle_to_use = cycle_str
                    current_week_to_use = current_week2_str
                    current_week_key_found = f"Cy{cycle_str}_W{current_week2_str}"
            
            current_week_int = int(current_week_to_use)
            current_cycle_int = int(current_cycle_to_use)
            
            previous_week_candidates = []
            
            for week_offset in [1, 2, 3]:
                if current_week_int > week_offset:
                    previous_week_candidates.append((current_cycle_to_use, str(current_week_int - week_offset)))
            
            if current_cycle_int > 1:
                prev_cycle_str = str(current_cycle_int - 1)
                previous_week_candidates.append((prev_cycle_str, current_week_to_use))
                for test_week in [str(current_week_int + 1), str(current_week_int - 1), "4", "3", "2", "1"]:
                    if test_week != current_week_to_use:  # Avoid duplicate
                        previous_week_candidates.append((prev_cycle_str, test_week))
            
            previous_cycle = None
            previous_week = None
            
            for i, (candidate_cycle, candidate_week) in enumerate(previous_week_candidates):
                candidate_key = f"Cy{candidate_cycle}_W{candidate_week}"
                is_available = candidate_key in available_weeks
                
                has_data = False
                data_count = 0
                if is_available and candidate_key in data_samples:
                    data_with_values = [s for s in data_samples[candidate_key] if s['value'] > 0]
                    has_data = len(data_with_values) > 0
                    data_count = len(data_with_values)
                
                status = f"✓ HAS DATA ({data_count} items)" if has_data else ("✓ AVAILABLE (no values)" if is_available else "✗ not available")
                
                if has_data and not previous_cycle:
                    previous_cycle = candidate_cycle
                    previous_week = candidate_week
                    break
            
            if not previous_cycle:
                for combo, samples in data_samples.items():
                    if any(s['value'] > 0 for s in samples) and combo != current_week_key_found:
                        parts = combo.replace('Cy', '').split('_W')
                        if len(parts) == 2:
                            previous_cycle = parts[0]
                            previous_week = parts[1]
                            break
                
                if not previous_cycle:
                    previous_cycle = str(current_cycle_int - 1) if current_cycle_int > 1 else current_cycle_to_use
                    previous_week = str(current_week_int - 1) if current_week_int > 1 else "1"
            
            category5_summary = {}
            processed_items = 0
            current_week_matches = 0
            previous_week_matches = 0
            
            current_week_key = f"{current_cycle_to_use}_{current_week_to_use}"
            previous_week_key = f"{previous_cycle}_{previous_week}"
            
            for item in summary_with_regional:
                if item['regional_desc'] != regional_desc:
                    continue
                    
                processed_items += 1
                category5 = item.get('category5')
                week = str(item['week1'])
                cycle_item = str(item.get('cycle'))
                billing_value = safe_float(item.get('qty_billing_sum'))
                target_value = safe_float(item.get('qty_target_ae'))
                
                if not category5:
                    continue
                    
                if category5 not in category5_summary:
                    category5_summary[category5] = {
                        'qty_billing_sum': 0.0,
                        'qty_target_ae': 0.0,
                        'weeks_data': {},
                        'category1': item.get('category1'),
                        'category2': item.get('category2'),
                        'category3': item.get('category3'),
                        'order': item.get('order', 0),
                        'processed_targets': set()
                    }
                
                target_key = f"{cycle_item}_{week}_{category5}"
                if cycle_item == current_cycle_to_use and target_value > 0 and target_key not in category5_summary[category5]['processed_targets']:
                    category5_summary[category5]['qty_target_ae'] += target_value
                    category5_summary[category5]['processed_targets'].add(target_key)
                
                if cycle_item == current_cycle_to_use:
                    category5_summary[category5]['qty_billing_sum'] += billing_value
                
                cycle_week_key = f"{cycle_item}_{week}"
                
                if cycle_week_key not in category5_summary[category5]['weeks_data']:
                    category5_summary[category5]['weeks_data'][cycle_week_key] = 0.0
                category5_summary[category5]['weeks_data'][cycle_week_key] += billing_value
                
                if cycle_item == current_cycle_to_use and week == current_week_to_use:
                    current_week_matches += 1
                    if billing_value > 0:
                        logging.debug(f"🔍 TW Match: {category5} += {billing_value} (cycle:{cycle_item}, week:{week})")
                elif cycle_item == previous_cycle and week == previous_week:
                    previous_week_matches += 1
            
            brands_with_tw_data = 0
            brands_with_lw_data = 0
            tw_total_debug = 0
            lw_total_debug = 0
            
            for brand_name, data in category5_summary.items():
                tw_value = data['weeks_data'].get(current_week_key, 0)
                lw_value = data['weeks_data'].get(previous_week_key, 0)
                
                if tw_value > 0:
                    brands_with_tw_data += 1
                    tw_total_debug += tw_value
                if lw_value > 0:
                    brands_with_lw_data += 1
                    lw_total_debug += lw_value
                    
                if tw_value > 0 or lw_value > 0 or data['qty_billing_sum'] > 0:
                    all_weeks = sorted(data['weeks_data'].keys())
                    weeks_info = []
                    for week_key in all_weeks:
                        value = data['weeks_data'][week_key]
                        if value > 0:
                            marker = "🎯TW" if week_key == current_week_key else ("🎯LW" if week_key == previous_week_key else "")
                            weeks_info.append(f"{week_key}={value:.1f}{marker}")
            
            filtered_summary = {}
            for brand_name, data in category5_summary.items():
                tw_value = data['weeks_data'].get(current_week_key, 0)
                lw_value = data['weeks_data'].get(previous_week_key, 0)
                total_billing = data['qty_billing_sum']
                total_target = data['qty_target_ae']
                
                if tw_value > 0 or lw_value > 0 or total_billing > 0 or total_target > 0:
                    filtered_summary[brand_name] = data
            
            
            if not filtered_summary:
                for combo in sorted(data_samples.keys()):
                    count = len([s for s in data_samples[combo] if s['value'] > 0])
                    total = sum(s['value'] for s in data_samples[combo])
                return "❌ Tidak ada data yang dapat ditampilkan untuk periode dan regional ini."
            
            matched_summary = filtered_summary
            
            category3_groups = {}
            for category5, data in matched_summary.items():
                category3 = data['category3'] or 'UNKNOWN'
                if category3 not in category3_groups:
                    category3_groups[category3] = {}
                category3_groups[category3][category5] = data
            
            category3_summary = {}
            for category3, brands in category3_groups.items():
                current_week_sum = 0
                previous_week_sum = 0
                total_billing = 0
                total_target = 0
                
                for category5, data in brands.items():
                    current_week_sum += data['weeks_data'].get(current_week_key, 0)
                    previous_week_sum += data['weeks_data'].get(previous_week_key, 0)
                    total_billing += data['qty_billing_sum']
                    total_target += data['qty_target_ae']
                
                percentage = (total_billing / total_target * 100) if total_target > 0 else 0
                category3_summary[category3] = {
                    'current_week_sum': current_week_sum,
                    'previous_week_sum': previous_week_sum,
                    'total_billing': total_billing,
                    'total_target': total_target,
                    'percentage': percentage,
                    'brands': brands
                }
            
            gd_current_week = 0
            gd_previous_week = 0
            gd_total_billing = 0
            gd_total_target = 0
            
            for category5, data in matched_summary.items():
                if data['category2'] == 'GD' or data['category1'] == 'GD':
                    gd_current_week += data['weeks_data'].get(current_week_key, 0)
                    gd_previous_week += data['weeks_data'].get(previous_week_key, 0)
                    gd_total_billing += data['qty_billing_sum']
                    gd_total_target += data['qty_target_ae']
            
            gd_percentage = (gd_total_billing / gd_total_target * 100) if gd_total_target > 0 else 0
            
            # GD+PLT totals
            gd_plt_current_week = 0
            gd_plt_previous_week = 0
            gd_plt_total_billing = 0
            gd_plt_total_target = 0
            
            for category5, data in matched_summary.items():
                if data['category2'] in ['GD', 'PLT'] or data['category1'] in ['GD', 'PLT']:
                    gd_plt_current_week += data['weeks_data'].get(current_week_key, 0)
                    gd_plt_previous_week += data['weeks_data'].get(previous_week_key, 0)
                    gd_plt_total_billing += data['qty_billing_sum']
                    gd_plt_total_target += data['qty_target_ae']
            
            gd_plt_percentage = self.round_up_percentage(gd_plt_total_billing / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0
            # result_regional_name = merger_detail[0].replace('Merged from: ', '')
            # result_regional_name = merger_detail[0].replace('Merged from: ', '')
            found = any(regional_desc in item for item in merger_detail)
            if found:
                result_regional_name = merger_detail[1].replace('Merged from: ', '')
            else:
                result_regional_name = regional_desc
            # Generate report
            report_lines = []
            report_lines.append("```")
            report_lines.append(f"📊 REPORT OMSET WEEKLY (BOX)")
            report_lines.append(f"📋 {result_regional_name.upper()}")
            report_lines.append(f"📅 Cy {current_cycle_to_use} {cycle_year} week {current_week_to_use} omset ideal {omset_ideal_percentage:.0f}% vs FUF")
            report_lines.append("```")
            
            report_lines.append("```")
            report_lines.append(f"CATEGORY TW | LW | +/- | ACH%")
            report_lines.append("─" * 26)
            
            # Display category3 comparison
            categories_displayed = 0
            for category3, summary in sorted(category3_summary.items()):
                current_week_sum = summary['current_week_sum']
                previous_week_sum = summary['previous_week_sum']
                
                if current_week_sum > 0 or previous_week_sum > 0 or summary['total_billing'] > 0:
                    categories_displayed += 1
                    difference = current_week_sum - previous_week_sum
                    diff_str = f"{difference:3.0f}" if difference >= 0 else f"{difference:4.0f}"
                    category3_name = (category3[:8] + "..") if len(category3) > 8 else category3
                    report_lines.append(f"{category3_name:<6}:{current_week_sum:>6.1f}|{previous_week_sum:>6.1f}|{diff_str:>5s}|{summary['percentage']:>3.0f}%")
            
            if gd_current_week > 0 or gd_previous_week > 0 or gd_total_billing > 0:
                categories_displayed += 1
                gd_difference = gd_current_week - gd_previous_week
                gd_diff_str = f"{gd_difference:3.0f}" if gd_difference >= 0 else f"{gd_difference:4.0f}"
                report_lines.append(f"{'GD':<6}:{gd_current_week:>6.1f}|{gd_previous_week:>6.1f}|{gd_diff_str:>5s}|{gd_percentage:>3.0f}%")
            
            total_tw = sum(s['current_week_sum'] for s in category3_summary.values())
            total_lw = sum(s['previous_week_sum'] for s in category3_summary.values())
            total_billing = sum(s['total_billing'] for s in category3_summary.values())
            total_target = sum(s['total_target'] for s in category3_summary.values())
            total_percentage = (total_billing / total_target * 100) if total_target > 0 else 0
            total_diff = total_tw - total_lw
            total_diff_str = f"{total_diff:3.0f}" if total_diff >= 0 else f"{total_diff:4.0f}"
            
            report_lines.append("─" * 26)
            report_lines.append(f"{'TOTAL':<6}:{total_tw:>6.1f}|{total_lw:>6.1f}|{total_diff_str:>5s}|{total_percentage:>3.0f}%")
            report_lines.append("```")
            report_lines.append("")
            
            if categories_displayed == 0:
                report_lines.append("❌ Tidak ada data kategori yang dapat ditampilkan.")
                report_lines.append(f"Debug info: Found {len(matched_summary)} brands, {len(category3_groups)} categories")
                report_lines.append("")
            
            brands_sections_added = 0
            for category3 in sorted(category3_groups.keys()):
                brands = category3_groups[category3]
                meaningful_brands = []
                
                for category5, data in brands.items():
                    current_week_sum = data['weeks_data'].get(current_week_key, 0)
                    previous_week_sum = data['weeks_data'].get(previous_week_key, 0)
                    if current_week_sum > 0 or previous_week_sum > 0 or data['qty_billing_sum'] > 0:
                        meaningful_brands.append((category5, data))
                
                if meaningful_brands:
                    brands_sections_added += 1
                    report_lines.append(f"📈 {category3} BRAND PERFORMANCE:")
                    report_lines.append("```")
                    report_lines.append(f"BRAND      TW | LW | +/- | ACH%")
                    report_lines.append("─" * 26)
                    
                    sorted_brands = sorted(meaningful_brands, key=lambda x: (x[1]['order'], x[0]))
                    for category5, data in sorted_brands:
                        current_week_sum = data['weeks_data'].get(current_week_key, 0)
                        previous_week_sum = data['weeks_data'].get(previous_week_key, 0)
                        difference = current_week_sum - previous_week_sum
                        diff_str = f"{difference:3.0f}" if difference >= 0 else f"{difference:4.0f}"
                        ach_percentage = (data['qty_billing_sum'] / data['qty_target_ae'] * 100) if data['qty_target_ae'] > 0 else 0
                        brand_name = (category5[:10] + "..") if len(category5) > 10 else category5
                        report_lines.append(f"{brand_name:<6}:{current_week_sum:>5.1f}|{previous_week_sum:>5.1f}|{diff_str:>4s}|{ach_percentage:>3.0f}%")
                    
                    report_lines.append("```")
                    report_lines.append("")
            
            if brands_sections_added == 0:
                report_lines.append("❌ Tidak ada data brand yang dapat ditampilkan.")
                report_lines.append("")
            
            report_message = "\n".join(report_lines)
            
            return report_message
            
        except Exception as e:
            logging.error(f"Error generating regional report: {e}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return f"❌ Error generating report: {str(e)}"