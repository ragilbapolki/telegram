"""
Report Generator for creating email reports
"""
from datetime import datetime
from config import CURRENT_DATE, SATUAN, WEEKS_PER_CYCLE

class ReportGenerator:
    def __init__(self):
        self.current_date = datetime.strptime(CURRENT_DATE, '%Y-%m-%d')
    
    def parse_sap_date(self, sap_date_str):
        """
        Convert SAP date format "/Date(1704067200000)/" to datetime
        """
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
        """
        Group brand data by name_reg (regional)
        """
        grouped = {}
        for brand in brand_data_list:
            region = brand.get('name_reg', 'Unknown Region')
            if region not in grouped:
                grouped[region] = []
            grouped[region].append(brand)
        return grouped
    
    def calculate_regional_summary(self, regional_data, current_week, total_weeks_in_cycle):
        """
        Calculate summary for specific regional with new format
        """
        # Filter data that is not prctr 3998 (Existing Brand)
        existing_data = [item for item in regional_data if item.get('prctr') != '3998']
        
        # Filter data only prctr 3998 (New Brand)
        new_brand_data = [item for item in regional_data if item.get('prctr') == '3998']
        
        # Current week sales - Existing
        current_week_sales_existing = sum([float(item.get('total_qty_billing', 0)) for item in existing_data])
        
        # Current week sales - New Brand (3998)
        current_week_sales_new = sum([float(item.get('total_qty_billing', 0)) for item in new_brand_data])
        
        # Total sales from week 1 to current week (simulation - in practice needs separate query)
        total_w1_to_current_existing = current_week_sales_existing * current_week
        
        # Total target from week 1 to current week - Existing
        total_target_w1_to_current_existing = sum([float(item.get('total_target', 0)) for item in existing_data]) * current_week
        
        # Calculate achievement percentage - Existing
        achievement_pct_existing = (total_w1_to_current_existing / total_target_w1_to_current_existing * 100) if total_target_w1_to_current_existing > 0 else 0
        
        # Calculate ideal omset percentage (current_week / total_weeks_in_cycle)
        omset_ideal_pct = (current_week / total_weeks_in_cycle * 100) if total_weeks_in_cycle > 0 else 0
        
        # Calculate GD category data
        gd_data = [item for item in existing_data if item.get('category1') == 'GD']
        gd_current_sales = sum([float(item.get('total_qty_billing', 0)) for item in gd_data])
        gd_total_target = sum([float(item.get('total_target', 0)) for item in gd_data]) * current_week
        gd_achievement_pct = (gd_current_sales * current_week / gd_total_target * 100) if gd_total_target > 0 else 0
        
        # Calculate GD + PLT category data
        gd_plt_data = [item for item in existing_data if item.get('category1') in ['GD', 'PLT']]
        gd_plt_current_sales = sum([float(item.get('total_qty_billing', 0)) for item in gd_plt_data])
        gd_plt_total_target = sum([float(item.get('total_target', 0)) for item in gd_plt_data]) * current_week
        gd_plt_achievement_pct = (gd_plt_current_sales * current_week / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0
        
        # Total EVO (all data including 3998)
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
            'gd_data': gd_data,
            'gd_plt_data': gd_plt_data
        }
    
    def create_regional_email_body(self, region_name, zpsdt003_data, regional_data, summary_data, regional_notes=None):
        """
        Membuat body email untuk regional tertentu dengan format yang diminta
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
                .existing {{ color: #4CAF50; }}
                .gd {{ color: #FF9800; }}
                .gd-plt {{ color: #9C27B0; }}
                .new-brand {{ color: #F44336; }}
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
                <h3>{region_name} Cycle {cycle} {cycle_year} week {current_week} omset ideal {summary_data['omset_ideal_pct']:.0f}% (dalam 1 cycle / current_week contoh {total_weeks}/{current_week} = {summary_data['omset_ideal_pct']:.0f}%) vs AE</h3>
                <div class="achievement existing">
                    % ACH AE Cy {cycle} (Existing): {summary_data['current_week_sales_existing']:,.3f} Box ( {summary_data['achievement_pct_existing']:.10f}% )
                </div>
                <div class="achievement gd">
                    % ACH AE Cy {cycle} (All Brand): {summary_data['gd_current_sales']:,.3f} Box ( {summary_data['gd_achievement_pct']:.10f}% )
                </div>
                <div class="achievement gd-plt">
                    % ACH AE Cy {cycle} (All Brand+PLT): {summary_data['gd_plt_current_sales']:,.3f} Box ( {summary_data['gd_plt_achievement_pct']:.10f}% )
                </div>
            </div>
            <div class="section">
                <h4>📈 Existing Brand (selain 3998):</h4>
        """
        existing_brands_with_qty = [item for item in summary_data['existing_data'] if float(item.get('total_qty_billing', 0)) > 0]
        if existing_brands_with_qty:
            for item in existing_brands_with_qty:
                achievement_pct = (float(item.get('total_qty_billing', 0)) / float(item.get('total_target', 0)) * 100) if float(item.get('total_target', 0)) > 0 else 0
                html_body += f"""
                    <div class="highlight">
                        {item.get('matnr', 'N/A')} ({item.get('wgbez60', 'N/A')}) : {float(item.get('total_qty_billing', 0)):,.3f} box ({achievement_pct:.3f}%) Vs AE
                    </div>
                """
        else:
            html_body += """
                <div class="highlight">
                    Tidak ada Existing Brand dengan quantity > 0
                </div>
            """
        has_both_types = len(summary_data['existing_data']) > 0 and len(summary_data['new_brand_data']) > 0
        if has_both_types:
            sales_offices = list(set([item.get('sales_office_name', 'N/A') for item in regional_data]))
            html_body += f"""
            <h4 class="total-evo">🔄 TOTAL EVO (semua termasuk 3998):</h4>
            """
            for office in sales_offices:
                office_data = [item for item in regional_data if item.get('sales_office_name') == office]
                current_week_total = sum([float(item.get('total_qty_billing', 0)) for item in office_data])
                last_week_total = current_week_total * 1.12  # Asumsi week lalu 12% lebih tinggi
                difference = current_week_total - last_week_total
                html_body += f"""
                <div class="highlight">
                    {office} : {current_week_total:.3f} / {last_week_total:.3f} / {difference:.3f}
                </div>
                """
        new_brands_with_qty = [item for item in summary_data['new_brand_data'] if float(item.get('total_qty_billing', 0)) > 0]
        if new_brands_with_qty:
            html_body += f"""
            <h4 class="new-brand">🆕 NEW BRAND (hanya 3998):</h4>
            """
            for item in new_brands_with_qty:
                achievement_pct = (float(item.get('total_qty_billing', 0)) / float(item.get('total_target', 0)) * 100) if float(item.get('total_target', 0)) > 0 else 0
                html_body += f"""
                <div class="highlight">
                    {item.get('matnr', 'N/A')} ({item.get('wgbez60', 'N/A')}) : {float(item.get('total_qty_billing', 0)):,.3f} box ({achievement_pct:.3f}%) Vs AE
                </div>
                """
        html_body += """
            </div>
        """
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
        """
        Proses utama dengan debugging yang ditingkatkan
        """
        print(f"Memproses laporan untuk tanggal: {CURRENT_DATE}")
        
        # Get recipients from database
        recipient_emails = self.get_recipients_from_db()
        print(f"Recipients from database: {recipient_emails}")
        
        # Load data dari SAP
        zpsdt003_data = self.load_zpsdt003_data()
        brand_data = self.load_brand_data()
        
        print(f"Total ZPSDT003 records: {len(zpsdt003_data)}")
        print(f"Total Brand records: {len(brand_data)}")
        
        # Cari data ZPSDT003 yang sesuai tanggal
        matching_zpsdt003 = self.find_matching_zpsdt003(zpsdt003_data)
        
        if not matching_zpsdt003:
            print(f"Tidak ada data ZPSDT003 yang sesuai untuk tanggal {CURRENT_DATE}")
            matching_zpsdt003 = self.get_sample_zpsdt003_data()
        
        # Proses setiap data yang cocok
        for zpsdt_data in matching_zpsdt003:
            cycle_year = str(zpsdt_data['cycle_year'])
            cycle = str(zpsdt_data['cycle'])
            current_week = int(zpsdt_data.get('week2', 3))
            total_weeks = 4
            
            print(f"Mencari brand data untuk: cycle_year={cycle_year}, cycle={cycle}")
            
            # Filter brand data yang sesuai cycle dan year
            matching_brands = [
                brand for brand in brand_data 
                if str(brand.get('cycle_year', '')) == cycle_year and str(brand.get('cycle', '')) == cycle
            ]
            
            if matching_brands:
                print(f"Ditemukan {len(matching_brands)} brand data untuk Cycle {cycle}, Year {cycle_year}")
                
                # Group by region (name_reg)
                regional_groups = self.group_brand_data_by_region(matching_brands)
                
                print(f"Data dikelompokkan menjadi {len(regional_groups)} regional:")
                for region, count in [(r, len(d)) for r, d in regional_groups.items()]:
                    print(f"  - {region}: {count} records")
                
                # Kirim email terpisah untuk setiap regional
                for region_name, regional_data in regional_groups.items():
                    print(f"\nMemproses regional: {region_name}")
                    
                    # Debug: Print semua field yang tersedia untuk mapping regional_id
                    if regional_data:
                        sample_data = regional_data[0]
                        print(f"DEBUG - Sample data fields: {list(sample_data.keys())}")
                        print(f"DEBUG - Possible regional_id fields:")
                        for key, value in sample_data.items():
                            if any(keyword in key.lower() for keyword in ['reg', 'region', 'office', 'vstel', 'kunnr']):
                                print(f"  {key}: {value}")
                    
                    # Coba beberapa kemungkinan mapping untuk regional_id
                    possible_regional_ids = []
                    if regional_data:
                        data_sample = regional_data[0]
                        possible_regional_ids.extend([
                            data_sample.get('vstel', ''),
                            data_sample.get('sales_office', ''),
                            data_sample.get('regional_id', ''),
                            data_sample.get('kunnr', ''),
                            data_sample.get('name_reg', ''),
                            # Tambahkan field lain yang mungkin
                        ])
                    
                    # Filter yang tidak kosong
                    possible_regional_ids = [rid for rid in possible_regional_ids if rid]
                    
                    regional_notes = None
                    # Coba setiap kemungkinan regional_id
                    for regional_id in possible_regional_ids:
                        print(f"DEBUG - Mencoba regional_id: '{regional_id}'")
                        regional_notes = self.get_regional_notes(regional_id, cycle, current_week, cycle_year)
                        if regional_notes:
                            print(f"DEBUG - Notes ditemukan dengan regional_id: '{regional_id}'")
                            break
                    
                    if not regional_notes:
                        print(f"DEBUG - Notes tidak ditemukan untuk regional {region_name}")
                    
                    # Hitung summary untuk regional ini
                    summary_data = self.calculate_regional_summary(regional_data, current_week, total_weeks)
                    
                    # Buat email body untuk regional ini
                    email_body = self.create_regional_email_body(region_name, zpsdt_data, regional_data, summary_data, regional_notes)
                    
                    # Subject email
                    subject = f"📊 Weekly Report W{current_week} Cycle {cycle} | {region_name} | {CURRENT_DATE}"
                    
                    # Kirim email
                    success = self.send_email(recipient_emails, subject, email_body)
                    
                    if success:
                        print(f"✅ Laporan untuk {region_name} berhasil dikirim")
                        print(f"   - Existing Brand Sales: {summary_data['current_week_sales_existing']:,.3f} BOX")
                        print(f"   - New Brand Sales: {summary_data['current_week_sales_new']:,.3f} BOX")
                        print(f"   - Achievement (Existing): {summary_data['achievement_pct_existing']:.3f}%")
                        print(f"   - Products: {len(regional_data)} items")
                        if regional_notes:
                            print(f"   - Notes: {regional_notes[:50]}...")
                        else:
                            print(f"   - Notes: Tidak ada")
                    else:
                        print(f"❌ Gagal mengirim laporan untuk {region_name}")
            else:
                print(f"⚠️  Data brand tidak ditemukan untuk Cycle {cycle}, Year {cycle_year}")
        
        return True
