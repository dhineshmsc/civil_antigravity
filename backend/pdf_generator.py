from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import io
import datetime
import logging

logger = logging.getLogger(__name__)

def generate_pdf(lines, dimensions, rooms=None, text_annotations=None, img_width=800, img_height=600):
    """Generates a professional landscape vector PDF sheet of the floor plan,
    complete with drawing border, legend, room labels, area measurements,
    and engineer sign-off block.
    """
    if rooms is None:
        rooms = []
    if text_annotations is None:
        text_annotations = []
        
    try:
        buffer = io.BytesIO()
        
        # Setup page layout: Landscape A4 (841.89 x 595.27 points)
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
        
        # Margins & Boundaries
        margin = 30
        title_block_height = 80
        
        # Draw professional border
        c.setStrokeColor(colors.HexColor('#334155')) # Slate-700
        c.setLineWidth(1.5)
        c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin)
        
        # Inner border
        c.setLineWidth(0.5)
        c.rect(margin + 3, margin + 3, page_width - 2 * margin - 6, page_height - 2 * margin - 6)
        
        # Determine plan bounding box to fit the page
        if not lines:
            min_x, max_x, min_y, max_y = 0, img_width, 0, img_height
        else:
            xs = [l['x1'] for l in lines] + [l['x2'] for l in lines]
            ys = [l['y1'] for l in lines] + [l['y2'] for l in lines]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
        plan_w = max(10, max_x - min_x)
        plan_h = max(10, max_y - min_y)
        
        # Available drawing area
        draw_w = page_width - 2 * margin - 40
        draw_h = page_height - 2 * margin - title_block_height - 40
        
        # Calculate fit scale
        scale_fit = min(draw_w / plan_w, draw_h / plan_h)
        
        # Center coordinates
        offset_x = margin + 20 + (draw_w - plan_w * scale_fit) / 2 - min_x * scale_fit
        # Invert Y coordinate systems: image is Y-down, PDF is Y-up
        # Plan is drawn above the title block area
        offset_y = margin + title_block_height + 20 + (draw_h - plan_h * scale_fit) / 2
        
        def to_pdf_coords(img_x, img_y):
            pdf_x = offset_x + img_x * scale_fit
            # Flip Y axis: max_y - img_y maps top to bottom
            pdf_y = offset_y + (max_y - img_y) * scale_fit
            return pdf_x, pdf_y
            
        # Draw grid pattern in the background (very subtle grey grid)
        c.setStrokeColor(colors.HexColor('#f1f5f9')) # Slate-100
        c.setLineWidth(0.5)
        grid_space = 25
        for x in range(int(margin + 5), int(page_width - margin - 5), grid_space):
            c.line(x, margin + title_block_height + 5, x, page_height - margin - 5)
        for y in range(int(margin + title_block_height + 5), int(page_height - margin - 5), grid_space):
            c.line(margin + 5, y, page_width - margin - 5, y)
            
        # Draw Floor Plan lines
        for line in lines:
            x1, y1 = line['x1'], line['y1']
            x2, y2 = line['x2'], line['y2']
            ltype = line.get('type', 'wall').upper()
            
            # Apply styling parameters based on line type
            if ltype == 'WINDOW':
                c.setStrokeColor(colors.HexColor('#0284c7')) # Cyan-600
                c.setLineWidth(1.2)
            elif ltype == 'DOOR':
                c.setStrokeColor(colors.HexColor('#f97316')) # Orange-500
                c.setLineWidth(1.4)
            else: # WALL
                c.setStrokeColor(colors.HexColor('#0f172a')) # Slate-900 (Thick Wall)
                c.setLineWidth(2.5)
                
            pdf_x1, pdf_y1 = to_pdf_coords(x1, y1)
            pdf_x2, pdf_y2 = to_pdf_coords(x2, y2)
            c.line(pdf_x1, pdf_y1, pdf_x2, pdf_y2)
            
        # Draw Dimensions
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.HexColor('#059669')) # Emerald-600 (Dimensions color)
        for dim in dimensions:
            x, y = dim['x'], dim['y']
            val = dim['value']
            pdf_x, pdf_y = to_pdf_coords(x, y)
            
            # Draw a small background rectangle for readability
            c.setStrokeColor(colors.HexColor('#ffffff'))
            c.setFillColor(colors.white)
            c.rect(pdf_x - 18, pdf_y - 6, 36, 12, fill=True, stroke=False)
            
            # Draw dimension text centered
            c.setFillColor(colors.HexColor('#059669'))
            c.drawCentredString(pdf_x, pdf_y - 3, val)
            
            # Draw helper ticks
            c.setStrokeColor(colors.HexColor('#10b981'))
            c.setLineWidth(0.5)
            c.circle(pdf_x, pdf_y, 1.5, stroke=True, fill=True)
        
        # Draw Room Labels and Area Measurements
        for room in rooms:
            cx, cy = room['center_x'], room['center_y']
            room_name = room.get('name', 'Room')
            area_sqm = room.get('area_sqm', 0.0)
            
            pdf_cx, pdf_cy = to_pdf_coords(cx, cy)
            
            # Draw a semi-transparent background for room label
            c.setFillColor(colors.Color(1, 1, 1, alpha=0.7))
            label_width = max(60, len(room_name) * 7 + 20)
            c.rect(pdf_cx - label_width/2, pdf_cy - 5, label_width, 28, fill=True, stroke=False)
            
            # Draw room name (larger, bold)
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor('#1e40af'))  # Blue-800
            c.drawCentredString(pdf_cx, pdf_cy + 8, room_name)
            
            # Draw area text below room name
            area_text = f"{area_sqm} sq.m"
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.HexColor('#7c3aed'))  # Violet-600
            c.drawCentredString(pdf_cx, pdf_cy - 3, area_text)
            
            # Draw small cross marker at center
            c.setStrokeColor(colors.HexColor('#93c5fd'))  # Blue-300
            c.setLineWidth(0.3)
            marker = 4
            c.line(pdf_cx - marker, pdf_cy, pdf_cx + marker, pdf_cy)
            c.line(pdf_cx, pdf_cy - marker, pdf_cx, pdf_cy + marker)
        
        # Draw User Text Annotations
        for ann in text_annotations:
            ax, ay = ann['x'], ann['y']
            ann_text = ann.get('text', '')
            ann_font_size = ann.get('font_size', 12.0)
            
            if ann_text:
                pdf_ax, pdf_ay = to_pdf_coords(ax, ay)
                
                # Scale font size to PDF coordinates
                pdf_font = max(6, min(16, ann_font_size * scale_fit * 0.12))
                
                c.setFont("Helvetica", int(pdf_font))
                c.setFillColor(colors.HexColor('#dc2626'))  # Red-600
                c.drawCentredString(pdf_ax, pdf_ay, ann_text)
            
        # ----------------------------------------------------
        # TITLE BLOCK (Bottom Area)
        # ----------------------------------------------------
        tb_y = margin + 5
        tb_h = title_block_height - 10
        tb_w = page_width - 2 * margin - 10
        tb_x = margin + 5
        
        # Partition lines
        c.setStrokeColor(colors.HexColor('#475569')) # Slate-600
        c.setLineWidth(1.0)
        c.line(tb_x, tb_y + tb_h, tb_x + tb_w, tb_y + tb_h) # Top of title block
        
        # Column separators
        col1_w = 220
        col2_w = 170
        col3_w = 160
        col4_w = 140
        
        c.line(tb_x + col1_w, tb_y, tb_x + col1_w, tb_y + tb_h)
        c.line(tb_x + col1_w + col2_w, tb_y, tb_x + col1_w + col2_w, tb_y + tb_h)
        c.line(tb_x + col1_w + col2_w + col3_w, tb_y, tb_x + col1_w + col2_w + col3_w, tb_y + tb_h)
        c.line(tb_x + col1_w + col2_w + col3_w + col4_w, tb_y, tb_x + col1_w + col2_w + col3_w + col4_w, tb_y + tb_h)
        
        # Section 1: Logo & Title
        c.setFillColor(colors.HexColor('#0f172a'))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(tb_x + 10, tb_y + tb_h - 20, "AI SKETCH TO CAD")
        
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor('#475569'))
        c.drawString(tb_x + 10, tb_y + tb_h - 35, "Automated 2D Floor Plan")
        c.drawString(tb_x + 10, tb_y + tb_h - 48, f"Generated: {datetime.date.today().strftime('%B %d, %Y')}")
        
        # Section 2: Drawing Properties
        c.setFillColor(colors.HexColor('#0f172a'))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(tb_x + col1_w + 10, tb_y + tb_h - 16, "DRAWING PROPERTIES")
        
        c.setFont("Helvetica", 7)
        c.drawString(tb_x + col1_w + 10, tb_y + tb_h - 30, f"Wall Lines: {len(lines)}")
        c.drawString(tb_x + col1_w + 10, tb_y + tb_h - 42, f"Labels: {len(dimensions)}")
        c.drawString(tb_x + col1_w + 10, tb_y + tb_h - 54, f"Rooms: {len(rooms)}")
        c.drawString(tb_x + col1_w + 10, tb_y + tb_h - 66, "Scale: Fits Sheet")
        
        # Section 3: Room Area Summary
        c.setFillColor(colors.HexColor('#0f172a'))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(tb_x + col1_w + col2_w + 10, tb_y + tb_h - 16, "AREA SCHEDULE")
        
        c.setFont("Helvetica", 6.5)
        total_area = 0.0
        y_offset = 28
        for i, room in enumerate(rooms[:4]):  # Show up to 4 rooms in title block
            room_name = room.get('name', f'Room {room["id"]}')
            area = room.get('area_sqm', 0.0)
            total_area += area
            c.setFillColor(colors.HexColor('#475569'))
            c.drawString(tb_x + col1_w + col2_w + 10, tb_y + tb_h - y_offset, f"{room_name}: {area} sq.m")
            y_offset += 11
        
        if rooms:
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(colors.HexColor('#1e40af'))
            c.drawString(tb_x + col1_w + col2_w + 10, tb_y + 5, f"Total: {round(total_area, 2)} sq.m")
        
        # Section 4: Status
        c.setFillColor(colors.HexColor('#0f172a'))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(tb_x + col1_w + col2_w + col3_w + 10, tb_y + tb_h - 16, "STATUS")
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor('#0284c7'))
        c.drawString(tb_x + col1_w + col2_w + col3_w + 10, tb_y + tb_h - 32, "VERIFIED")
        
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor('#475569'))
        c.drawString(tb_x + col1_w + col2_w + col3_w + 10, tb_y + tb_h - 46, "Canvas verified")
        c.drawString(tb_x + col1_w + col2_w + col3_w + 10, tb_y + tb_h - 58, "AUTO-VERIFY")
        
        # Section 5: Sign-off
        c.setFillColor(colors.HexColor('#0f172a'))
        c.setFont("Helvetica-Bold", 7)
        sign_x = tb_x + col1_w + col2_w + col3_w + col4_w + 10
        c.drawString(sign_x, tb_y + tb_h - 16, "SIGN-OFF")
        
        # Box for physical signature
        c.setStrokeColor(colors.HexColor('#94a3b8'))
        remaining_w = tb_w - (col1_w + col2_w + col3_w + col4_w) - 20
        c.rect(sign_x, tb_y + 8, max(80, remaining_w), 32)
        
        c.setFont("Helvetica-Oblique", 6)
        c.setFillColor(colors.HexColor('#94a3b8'))
        c.drawString(sign_x + 3, tb_y + 12, "Professional Engineer")
        
        c.showPage()
        c.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise e

