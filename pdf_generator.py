import logging
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import os

class RegionalReportPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for PDF"""
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        )
        
        # Sub header style
        self.sub_header_style = ParagraphStyle(
            'CustomSubHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_LEFT,
            textColor=colors.darkgreen,
            fontName='Helvetica-Bold'
        )
        
        # Normal text style
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )

    def generate_regional_pdf_report(self, merged_brands, cycle_year, cycle, current_week, regional_desc, current_week2, output_path=None):
        """Generate PDF report for regional data"""
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk PDF report.")
                return None

            # Process data (same logic as original method)
            summary_with_regional = self.data_processor.create_summary_with_regional(merged_brands)
            
            if not summary_with_regional:
                logging.warning("Tidak ada data summary untuk PDF report.")
                return None

            # Filter data for specific regional
            regional_data = [item for item in summary_with_regional if item['regional_desc'] == regional_desc]
            
            if not regional_data:
                logging.warning(f"Tidak ada data untuk regional: {regional_desc}")
                return None

            # Calculate data (same as original)
            omset_ideal_percentage = (current_week2 / 4 * 100)
            current_week_data = [item for item in regional_data if str(item['week1']) == str(current_week)]
            
            def safe_float(value):
                try:
                    return float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            # Process category5 summary (same logic)
            category5_summary = {}
            
            for item in regional_data:
                category5 = item.get('category5')
                week = str(item['week1'])
                cycle_item = item.get('cycle')
                
                if category5:
                    if category5 not in category5_summary:
                        category5_summary[category5] = {
                            'qty_billing_sum': 0.0,
                            'qty_target_ae': 0.0,
                            'current_week_targets': set(),
                            'unique_target_values': set(),
                            'weeks_data': {},
                            'category1': item.get('category1'),
                            'category2': item.get('category2'),
                            'category3': item.get('category3'),
                            'order': item.get('order', 0)
                        }
                    
                    if cycle_item == cycle:
                        category5_summary[category5]['qty_billing_sum'] += safe_float(item.get('qty_billing_sum'))
                    
                    target_value = safe_float(item.get('qty_target_ae'))
                    if target_value > 0:
                        if target_value not in category5_summary[category5]['unique_target_values']:
                            category5_summary[category5]['unique_target_values'].add(target_value)
                            category5_summary[category5]['qty_target_ae'] += target_value
                        
                        if week == str(current_week):
                            category5_summary[category5]['current_week_targets'].add(target_value)
                    
                    if cycle_item == cycle:
                        if week not in category5_summary[category5]['weeks_data']:
                            category5_summary[category5]['weeks_data'][week] = 0.0
                        category5_summary[category5]['weeks_data'][week] += safe_float(item.get('qty_billing_sum'))
            
            # Create matched summary
            matched_summary = {}
            for category5, summary_data in category5_summary.items():
                matched_summary[category5] = {
                    'category5': category5,
                    'qty_billing_sum': summary_data['qty_billing_sum'],
                    'qty_target_ae': summary_data['qty_target_ae'],
                    'weeks_data': summary_data['weeks_data'],
                    'category1': summary_data['category1'],
                    'category2': summary_data['category2'],
                    'category3': summary_data['category3'],
                    'order': summary_data['order']
                }
            
            # Group by category3
            category3_groups = {}
            for category5, data in matched_summary.items():
                category3 = data['category3']
                if category3:
                    if category3 not in category3_groups:
                        category3_groups[category3] = {}
                    category3_groups[category3][category5] = data
            
            # Calculate category3 summary
            category3_summary = {}
            for category3, brands in category3_groups.items():
                current_week_sum = 0
                total_billing = 0
                total_target = 0
                
                for category5, data in brands.items():
                    current_week_sum += data['weeks_data'].get(str(current_week), 0)
                    total_billing += data['qty_billing_sum']
                    total_target += data['qty_target_ae']
                
                percentage = (total_billing / total_target * 100) if total_target > 0 else 0
                
                category3_summary[category3] = {
                    'current_week_sum': current_week_sum,
                    'total_billing': total_billing,
                    'total_target': total_target,
                    'percentage': percentage,
                    'brands': brands
                }

            # Calculate GD totals
            gd_current_week = 0
            gd_total_billing = 0
            gd_total_target = 0
            
            for category5, data in matched_summary.items():
                if data['category2'] == 'GD' or data['category1'] == 'GD':
                    gd_current_week += data['weeks_data'].get(str(current_week), 0)
                    gd_total_billing += data['qty_billing_sum']
                    gd_total_target += data['qty_target_ae']
            
            gd_percentage = (gd_total_billing / gd_total_target * 100) if gd_total_target > 0 else 0

            # Calculate GD+PLT totals
            gd_plt_current_week = 0
            gd_plt_total_billing = 0
            gd_plt_total_target = 0
            
            for category5, data in matched_summary.items():
                if data['category2'] in ['GD', 'PLT'] or data['category1'] in ['GD', 'PLT']:
                    gd_plt_current_week += data['weeks_data'].get(str(current_week), 0)
                    gd_plt_total_billing += data['qty_billing_sum']
                    gd_plt_total_target += data['qty_target_ae']
            
            gd_plt_percentage = (gd_plt_total_billing / gd_plt_total_target * 100) if gd_plt_total_target > 0 else 0

            # Generate PDF
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"regional_report_{regional_desc.replace(' ', '_')}_{timestamp}.pdf"
            
            return self._create_pdf(
                output_path, regional_desc, cycle_year, cycle, current_week, current_week2,
                omset_ideal_percentage, category3_groups, category3_summary, matched_summary,
                gd_current_week, gd_total_billing, gd_total_target, gd_percentage,
                gd_plt_current_week, gd_plt_total_billing, gd_plt_total_target, gd_plt_percentage
            )

        except Exception as e:
            logging.error(f"Error generating PDF regional report: {e}")
            return None

    def _create_pdf(self, output_path, regional_desc, cycle_year, cycle, current_week, current_week2,
                    omset_ideal_percentage, category3_groups, category3_summary, matched_summary,
                    gd_current_week, gd_total_billing, gd_total_target, gd_percentage,
                    gd_plt_current_week, gd_plt_total_billing, gd_plt_total_target, gd_plt_percentage):
        """Create the actual PDF document"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Build story
        story = []
        
        # Header
        header_text = f"REPORT OMSET WEEKLY W{current_week2} CYCLE {cycle} (BOX)"
        story.append(Paragraph(header_text, self.header_style))
        
        regional_header = f"{regional_desc.upper()}"
        story.append(Paragraph(regional_header, self.header_style))
        
        summary_text = f"Summary - Cy {cycle} {cycle_year} week {current_week2} omset ideal {omset_ideal_percentage:.0f}% vs FUF"
        story.append(Paragraph(summary_text, self.sub_header_style))
        story.append(Spacer(1, 12))

        previous_week = str(int(current_week) - 1) if int(current_week) > 1 else '0'

        for category3 in sorted(category3_groups.keys()):
            brands = category3_groups[category3]
            
            # Check if this category has meaningful data
            has_meaningful_data = False
            for category5, data in brands.items():
                current_week_sum = data['weeks_data'].get(str(current_week), 0)
                previous_week_sum = data['weeks_data'].get(previous_week, 0)
                if current_week_sum > 0 or previous_week_sum > 0:
                    has_meaningful_data = True
                    break
            
            if not has_meaningful_data:
                continue
            
            # Category header
            story.append(Paragraph(f"{category3} BRAND PERFORMANCE", self.sub_header_style))
            
            # Create brand performance table
            table_data = [['Brand', 'This Week', 'Last Week', '+/-', 'ACH %', 'Total Billing', 'Target']]
            
            sorted_brands = sorted(brands.items(), key=lambda x: (x[1]['order'], x[0]))
            
            for category5, data in sorted_brands:
                current_week_sum = data['weeks_data'].get(str(current_week), 0)
                previous_week_sum = data['weeks_data'].get(previous_week, 0)
                
                if current_week_sum == 0 and previous_week_sum == 0:
                    continue
                
                difference = current_week_sum - previous_week_sum
                ach_percentage = (data['qty_billing_sum'] / data['qty_target_ae'] * 100) if data['qty_target_ae'] > 0 else 0
                
                table_data.append([
                    category5,
                    f"{current_week_sum:.1f}",
                    f"{previous_week_sum:.1f}",
                    f"{difference:+.1f}",
                    f"{ach_percentage:.1f}%",
                    f"{data['qty_billing_sum']:.1f}",
                    f"{data['qty_target_ae']:.1f}"
                ])
            
            if len(table_data) > 1:  # Has data rows
                table = Table(table_data, colWidths=[60*mm, 25*mm, 25*mm, 25*mm, 20*mm, 25*mm, 25*mm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                story.append(table)
                story.append(Spacer(1, 15))

        # Summary Totals Table
        story.append(Paragraph("SUMMARY TOTALS", self.sub_header_style))
        
        summary_table_data = [['Category', 'This Week', 'Last Week', '+/-', 'ACH %', 'Total Billing', 'Target']]
        
        # Calculate previous week totals for each category3
        category3_previous_week = {}
        for category3, brands in category3_groups.items():
            previous_week_sum = 0
            for category5, data in brands.items():
                previous_week_sum += data['weeks_data'].get(previous_week, 0)
            category3_previous_week[category3] = previous_week_sum
        
        # Add category3 summaries
        for category3, summary in sorted(category3_summary.items()):
            if summary['current_week_sum'] == 0:
                continue
            
            current_week_sum = summary['current_week_sum']
            previous_week_sum = category3_previous_week.get(category3, 0)
            difference = current_week_sum - previous_week_sum
            
            summary_table_data.append([
                category3,
                f"{current_week_sum:.1f}",
                f"{previous_week_sum:.1f}",
                f"{difference:+.1f}",
                f"{summary['percentage']:.1f}%",
                f"{summary['total_billing']:.1f}",
                f"{summary['total_target']:.1f}"
            ])
        
        # Add GD summary
        if gd_current_week > 0:
            gd_previous_week = 0
            for category5, data in matched_summary.items():
                if data['category2'] == 'GD' or data['category1'] == 'GD':
                    gd_previous_week += data['weeks_data'].get(previous_week, 0)
            
            gd_difference = gd_current_week - gd_previous_week
            
            summary_table_data.append([
                'GD',
                f"{gd_current_week:.1f}",
                f"{gd_previous_week:.1f}",
                f"{gd_difference:+.1f}",
                f"{gd_percentage:.1f}%",
                f"{gd_total_billing:.1f}",
                f"{gd_total_target:.1f}"
            ])
        
        # Add GD+PLT summary
        if gd_plt_current_week > 0:
            gd_plt_previous_week = 0
            for category5, data in matched_summary.items():
                if data['category2'] in ['GD', 'PLT'] or data['category1'] in ['GD', 'PLT']:
                    gd_plt_previous_week += data['weeks_data'].get(previous_week, 0)
            
            gd_plt_difference = gd_plt_current_week - gd_plt_previous_week
            
            summary_table_data.append([
                'GD+PLT',
                f"{gd_plt_current_week:.1f}",
                f"{gd_plt_previous_week:.1f}",
                f"{gd_plt_difference:+.1f}",
                f"{gd_plt_percentage:.1f}%",
                f"{gd_plt_total_billing:.1f}",
                f"{gd_plt_total_target:.1f}"
            ])
        
        # Create summary table
        summary_table = Table(summary_table_data, colWidths=[60*mm, 25*mm, 25*mm, 25*mm, 20*mm, 25*mm, 25*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(summary_table)
        
        # Footer
        story.append(Spacer(1, 20))
        footer_text = f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(footer_text, self.normal_style))
        
        # Build PDF
        doc.build(story)
        
        logging.info(f"✓ PDF report generated: {output_path}")
        return output_path
    
    def send_regional_pdf_reports(self, merged_brands, cycle_year, cycle, current_week, current_week2, output_dir="reports"):
        """Generate and save PDF reports for all regionals"""
        try:
            if not merged_brands:
                logging.warning("Tidak ada data merged brands untuk PDF reports.")
                return False

            # Create output directory if not exists
            os.makedirs(output_dir, exist_ok=True)

            # Get unique regional descriptions
            summary_with_regional = self.data_processor.create_summary_with_regional(merged_brands)
            unique_regionals = list(set(item['regional_desc'] for item in summary_with_regional if item['regional_desc']))
            total_generated = 0
            
            generated_files = []
            
            for regional_desc in unique_regionals:
                # Generate PDF report for this regional
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"regional_report_{regional_desc.replace(' ', '_')}_{timestamp}.pdf"
                output_path = os.path.join(output_dir, filename)
                
                pdf_path = self.generate_regional_pdf_report(
                    merged_brands, cycle_year, cycle, current_week, regional_desc, current_week2, output_path
                )
                
                if pdf_path:
                    generated_files.append(pdf_path)
                    total_generated += 1
                    logging.info(f"✓ PDF report generated for regional: {regional_desc}")
                else:
                    logging.warning(f"⚠ Failed to generate PDF report for regional: {regional_desc}")

            logging.info(f"✓ Total PDF reports generated: {total_generated}")
            logging.info(f"✓ Generated files: {generated_files}")
            
            return {
                'success': total_generated > 0,
                'total_generated': total_generated,
                'files': generated_files
            }

        except Exception as e:
            logging.error(f"Error generating PDF regional reports: {e}")
            return {
                'success': False,
                'total_generated': 0,
                'files': [],
                'error': str(e)
            }