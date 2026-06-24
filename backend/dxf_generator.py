import ezdxf
import io
import math
import logging

logger = logging.getLogger(__name__)

def generate_dxf(lines, dimensions, rooms=None, text_annotations=None, img_width=800, img_height=600, scale_factor=0.02):
    """Generates a DXF document from the vector lines, dimensions, rooms, and text annotations.
    
    Flips the Y-axis to match CAD standard (Y-up) and scales pixels to meters.
    Room labels and area measurements are placed centered in each room.
    """
    if rooms is None:
        rooms = []
    if text_annotations is None:
        text_annotations = []
        
    try:
        # Create a new DXF drawing (DXF R2000 format)
        doc = ezdxf.new('R2000')
        msp = doc.modelspace()
        
        # Setup CAD layers with standard colors
        # Colors: 1 = Red, 2 = Yellow, 3 = Green, 4 = Cyan, 5 = Blue, 6 = Magenta, 7 = White
        doc.layers.new('WALLS', dxfattribs={'color': 7})          # White/Black
        doc.layers.new('WINDOWS', dxfattribs={'color': 4})        # Cyan
        doc.layers.new('DOORS', dxfattribs={'color': 2})          # Yellow
        doc.layers.new('DIMENSIONS', dxfattribs={'color': 3})     # Green
        doc.layers.new('ROOM_LABELS', dxfattribs={'color': 5})    # Blue
        doc.layers.new('ROOM_AREAS', dxfattribs={'color': 6})     # Magenta
        doc.layers.new('ANNOTATIONS', dxfattribs={'color': 1})    # Red
        
        # Draw Lines
        for line in lines:
            x1, y1 = line['x1'], line['y1']
            x2, y2 = line['x2'], line['y2']
            ltype = line.get('type', 'wall').upper()
            
            # Layer assignment based on line type
            if ltype == 'WINDOW':
                layer = 'WINDOWS'
            elif ltype == 'DOOR':
                layer = 'DOORS'
            else:
                layer = 'WALLS'
                
            # Flip Y axis (image is Y-down, CAD is Y-up)
            cad_x1 = x1 * scale_factor
            cad_y1 = (img_height - y1) * scale_factor
            cad_x2 = x2 * scale_factor
            cad_y2 = (img_height - y2) * scale_factor
            
            # Add line to modelspace
            msp.add_line((cad_x1, cad_y1), (cad_x2, cad_y2), dxfattribs={'layer': layer})
            
            # If it is a door, we can add a swing arc representation for advanced aesthetics
            if ltype == 'DOOR':
                # Center point is start of door, radius is door width
                # For simplified CAD representation, a single line is often fine,
                # but adding an arc makes the AutoCAD export feel extremely premium.
                width = math.sqrt((cad_x2 - cad_x1)**2 + (cad_y2 - cad_y1)**2)
                # Drawing simple door arc is optional; standard line is sufficient for basic
                pass
                
        # Draw dimensions / text labels
        for dim in dimensions:
            x, y = dim['x'], dim['y']
            val = dim['value']
            
            cad_x = x * scale_factor
            cad_y = (img_height - y) * scale_factor
            
            # Text size scale relative to scale factor
            text_height = max(0.15, 8.0 * scale_factor)
            
            # Add text entity
            msp.add_text(
                val, 
                dxfattribs={
                    'layer': 'DIMENSIONS', 
                    'height': text_height,
                    'style': 'STANDARD'
                }
            ).set_placement((cad_x, cad_y), align=ezdxf.enums.TextEntityAlignment.CENTER)
        
        # Draw room labels and area measurements
        for room in rooms:
            cx = room['center_x'] * scale_factor
            cy = (img_height - room['center_y']) * scale_factor
            room_name = room.get('name', 'Room')
            area_sqm = room.get('area_sqm', 0.0)
            
            # Room name text (larger, centered in room)
            name_height = max(0.25, 12.0 * scale_factor)
            msp.add_text(
                room_name,
                dxfattribs={
                    'layer': 'ROOM_LABELS',
                    'height': name_height,
                    'style': 'STANDARD'
                }
            ).set_placement((cx, cy + name_height * 0.8), align=ezdxf.enums.TextEntityAlignment.CENTER)
            
            # Area text below room name (smaller)
            area_text = f"{area_sqm} sq.m"
            area_height = max(0.18, 9.0 * scale_factor)
            msp.add_text(
                area_text,
                dxfattribs={
                    'layer': 'ROOM_AREAS',
                    'height': area_height,
                    'style': 'STANDARD'
                }
            ).set_placement((cx, cy - area_height * 0.8), align=ezdxf.enums.TextEntityAlignment.CENTER)
            
            # Draw a light cross marker at room center for reference
            marker_size = max(0.1, 5.0 * scale_factor)
            msp.add_line(
                (cx - marker_size, cy), (cx + marker_size, cy),
                dxfattribs={'layer': 'ROOM_LABELS', 'color': 8}  # Color 8 = dark grey
            )
            msp.add_line(
                (cx, cy - marker_size), (cx, cy + marker_size),
                dxfattribs={'layer': 'ROOM_LABELS', 'color': 8}
            )
        
        # Draw user text annotations
        for ann in text_annotations:
            ax = ann['x'] * scale_factor
            ay = (img_height - ann['y']) * scale_factor
            ann_text = ann.get('text', '')
            ann_font_size = ann.get('font_size', 12.0)
            
            ann_height = max(0.15, ann_font_size * scale_factor * 0.5)
            
            if ann_text:
                msp.add_text(
                    ann_text,
                    dxfattribs={
                        'layer': 'ANNOTATIONS',
                        'height': ann_height,
                        'style': 'STANDARD'
                    }
                ).set_placement((ax, ay), align=ezdxf.enums.TextEntityAlignment.CENTER)
            
        # Write to a string stream (StringIO)
        stream = io.StringIO()
        doc.write(stream)
        
        # Convert StringIO to bytes for streaming
        dxf_bytes = stream.getvalue().encode('utf-8')
        stream.close()
        
        return dxf_bytes
        
    except Exception as e:
        logger.error(f"Error generating DXF file: {e}")
        raise e

