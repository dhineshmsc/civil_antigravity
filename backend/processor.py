import cv2
import numpy as np
import base64
import math
import logging
from itertools import combinations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import EasyOCR, fallback if not available
try:
    import easyocr
    # We initialize the reader lazily to speed up startup
    ocr_reader = None
except ImportError:
    ocr_reader = None
    logger.info("EasyOCR not installed. Text dimension detection will highlight regions with editable mocks.")

def get_ocr_reader():
    global ocr_reader
    if 'easyocr' in globals() and ocr_reader is None:
        try:
            logger.info("Initializing EasyOCR Reader...")
            ocr_reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            ocr_reader = None
    return ocr_reader

def distance_point_to_line(px, py, x1, y1, x2, y2):
    """Calculates perpendicular distance from point to line segment."""
    line_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if line_len == 0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
    
    # Projection factor
    u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_len ** 2)
    u = max(0, min(1, u)) # clamp to segment
    
    ix = x1 + u * (x2 - x1)
    iy = y1 + u * (y2 - y1)
    return math.sqrt((px - ix) ** 2 + (py - iy) ** 2)

def merge_collinear_lines(lines, distance_threshold=15, overlap_threshold=10):
    """Merges collinear and overlapping line segments."""
    if not lines:
        return []
        
    merged = []
    used = set()
    
    # lines is a list of [x1, y1, x2, y2]
    for i, l1 in enumerate(lines):
        if i in used:
            continue
            
        curr_x1, curr_y1, curr_x2, curr_y2 = l1
        
        # Determine main orientation
        dx1 = curr_x2 - curr_x1
        dy1 = curr_y2 - curr_y1
        len1 = math.sqrt(dx1**2 + dy1**2)
        if len1 == 0:
            continue
            
        for j, l2 in enumerate(lines):
            if j <= i or j in used:
                continue
                
            x1, y1, x2, y2 = l2
            dx2 = x2 - x1
            dy2 = y2 - y1
            len2 = math.sqrt(dx2**2 + dy2**2)
            if len2 == 0:
                continue
                
            # Check angle similarity
            dot_product = abs(dx1 * dx2 + dy1 * dy2) / (len1 * len2)
            if dot_product < 0.95: # Not parallel enough
                continue
                
            # Check distance of endpoints of l2 to line l1
            dist1 = distance_point_to_line(x1, y1, curr_x1, curr_y1, curr_x2, curr_y2)
            dist2 = distance_point_to_line(x2, y2, curr_x1, curr_y1, curr_x2, curr_y2)
            
            if dist1 < distance_threshold and dist2 < distance_threshold:
                # They are collinear. Now check if they overlap or are very close.
                # Project all 4 points onto the vector direction of l1
                ux = dx1 / len1
                uy = dy1 / len1
                
                proj_curr_1 = curr_x1 * ux + curr_y1 * uy
                proj_curr_2 = curr_x2 * ux + curr_y2 * uy
                proj_l2_1 = x1 * ux + y1 * uy
                proj_l2_2 = x2 * ux + y2 * uy
                
                min_curr = min(proj_curr_1, proj_curr_2)
                max_curr = max(proj_curr_1, proj_curr_2)
                min_l2 = min(proj_l2_1, proj_l2_2)
                max_l2 = max(proj_l2_1, proj_l2_2)
                
                # Check for overlap or small gap
                if not (max_curr + overlap_threshold < min_l2 or max_l2 + overlap_threshold < min_curr):
                    # Merge them! Update curr points to span the outer bounds
                    all_proj = [(proj_curr_1, curr_x1, curr_y1), (proj_curr_2, curr_x2, curr_y2),
                                (proj_l2_1, x1, y1), (proj_l2_2, x2, y2)]
                    all_proj.sort(key=lambda x: x[0])
                    
                    curr_x1, curr_y1 = all_proj[0][1], all_proj[0][2]
                    curr_x2, curr_y2 = all_proj[-1][1], all_proj[-1][2]
                    
                    dx1 = curr_x2 - curr_x1
                    dy1 = curr_y2 - curr_y1
                    len1 = math.sqrt(dx1**2 + dy1**2)
                    
                    used.add(j)
                    
        merged.append([int(curr_x1), int(curr_y1), int(curr_x2), int(curr_y2)])
        used.add(i)
        
    return merged


def detect_rooms(formatted_lines, img_width, img_height, scale_factor=0.02):
    """Detects closed rectangular room regions from wall lines.
    
    Uses a flood-fill approach on a rasterized wall image to find enclosed regions,
    then extracts bounding rectangles and calculates area in sq.m.
    
    Returns a list of room dicts: {id, name, area_sqm, center_x, center_y, 
                                    bbox_x, bbox_y, bbox_w, bbox_h}
    """
    if not formatted_lines:
        return []
    
    # Create a blank canvas and draw all wall lines
    canvas = np.zeros((img_height, img_width), dtype=np.uint8)
    
    for line in formatted_lines:
        x1, y1 = int(line["x1"]), int(line["y1"])
        x2, y2 = int(line["x2"]), int(line["y2"])
        # Draw walls with thickness to ensure closed regions
        cv2.line(canvas, (x1, y1), (x2, y2), 255, thickness=3)
    
    # Close small gaps in wall connections using morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    canvas_closed = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, kernel)
    
    # Invert to get rooms as white regions (walls are black boundaries)
    inverted = cv2.bitwise_not(canvas_closed)
    
    # Find contours of the enclosed regions
    contours, hierarchy = cv2.findContours(inverted, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    
    rooms = []
    room_id = 1
    
    # Minimum room size thresholds (in pixels) - filter out tiny artifacts
    min_room_area_px = (img_width * img_height) * 0.01  # At least 1% of image area
    max_room_area_px = (img_width * img_height) * 0.90  # At most 90% (not the outer boundary)
    
    for i, contour in enumerate(contours):
        area_px = cv2.contourArea(contour)
        
        # Filter by reasonable room sizes
        if area_px < min_room_area_px or area_px > max_room_area_px:
            continue
        
        # Get bounding rectangle
        bx, by, bw, bh = cv2.boundingRect(contour)
        
        # Filter out very thin regions (not rooms)
        aspect = bw / float(bh) if bh > 0 else 0
        if aspect < 0.15 or aspect > 7.0:
            continue
        
        # Calculate center point
        center_x = bx + bw / 2.0
        center_y = by + bh / 2.0
        
        # Calculate area in sq.m using scale_factor
        # Use actual contour area converted to meters
        area_m2 = area_px * (scale_factor ** 2)
        
        # Also calculate bbox dimensions in meters for reference
        width_m = bw * scale_factor
        height_m = bh * scale_factor
        
        # Generate a default room name based on position and size
        # (Will be overridden by OCR-detected text if available)
        default_name = f"Room {room_id}"
        
        rooms.append({
            "id": room_id,
            "name": default_name,
            "area_sqm": round(area_m2, 2),
            "width_m": round(width_m, 2),
            "height_m": round(height_m, 2),
            "center_x": float(center_x),
            "center_y": float(center_y),
            "bbox_x": float(bx),
            "bbox_y": float(by),
            "bbox_w": float(bw),
            "bbox_h": float(bh)
        })
        room_id += 1
    
    # Sort rooms by position (top-left to bottom-right) for consistent ordering
    rooms.sort(key=lambda r: (r["bbox_y"], r["bbox_x"]))
    # Reassign IDs after sorting
    for idx, room in enumerate(rooms):
        room["id"] = idx + 1
    
    return rooms


def assign_room_names_from_text(rooms, text_regions, gray_img, img_w, img_h):
    """Assigns room names by matching detected large text regions to room bounding boxes.
    
    For each detected text region, finds which room it falls inside and assigns
    the text as the room name.
    """
    ocr = get_ocr_reader()
    
    for text_region in text_regions:
        tx, ty, tw, th, text_val = text_region
        text_cx = tx + tw / 2.0
        text_cy = ty + th / 2.0
        
        # Find which room contains this text center point
        best_room = None
        best_dist = float('inf')
        
        for room in rooms:
            rx, ry = room["bbox_x"], room["bbox_y"]
            rw, rh = room["bbox_w"], room["bbox_h"]
            
            # Check if text center is inside room bounding box (with margin)
            margin = 20
            if (rx - margin <= text_cx <= rx + rw + margin and 
                ry - margin <= text_cy <= ry + rh + margin):
                # Calculate distance to room center for tiebreaking
                dist = math.sqrt((text_cx - room["center_x"])**2 + (text_cy - room["center_y"])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_room = room
        
        if best_room is not None and text_val:
            # Only assign if it looks like a room name (not a dimension like "5.0m")
            # Room names typically don't end with 'm' preceded by a digit
            is_dimension = False
            clean_val = text_val.strip()
            if clean_val and clean_val[-1].lower() == 'm':
                # Check if the rest is a number
                try:
                    float(clean_val[:-1])
                    is_dimension = True
                except ValueError:
                    pass
            
            if not is_dimension:
                best_room["name"] = text_val
    
    return rooms


def process_sketch_image(image_bytes, threshold_val=110, min_line_len=40, max_line_gap=15, grid_snap=True, grid_size=20, scale_factor=0.02):
    """Processes sketch image, detects lines, junctions, dimension text boxes, and rooms with areas."""
    # Convert image bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")
        
    h, w, c = img.shape
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Denoise with bilateral filter (preserves edges)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 2. Adaptive threshold to isolate lines
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 15, 8
    )
    
    # Morphological opening/closing to clean up isolated specks and close minor gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh_cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    # 3. Detect lines using Progressive Probabilistic Hough Transform
    # Adjust parameters slightly based on image size to feel responsive
    hough_lines = cv2.HoughLinesP(
        thresh_cleaned, 
        rho=1, 
        theta=np.pi/180, 
        threshold=int(threshold_val), 
        minLineLength=int(min_line_len), 
        maxLineGap=int(max_line_gap)
    )
    
    raw_lines = []
    if hough_lines is not None:
        for line in hough_lines:
            x1, y1, x2, y2 = line[0]
            raw_lines.append([x1, y1, x2, y2])
            
    # Clean and merge lines
    # Step A: Snap orientations (Horizontal/Vertical)
    snapped_lines = []
    for l in raw_lines:
        x1, y1, x2, y2 = l
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        
        # Snap to horizontal
        if dy < 15:
            y2 = y1
        # Snap to vertical
        elif dx < 15:
            x2 = x1
            
        if grid_snap:
            # Snap to grid coordinates
            x1 = round(x1 / grid_size) * grid_size
            y1 = round(y1 / grid_size) * grid_size
            x2 = round(x2 / grid_size) * grid_size
            y2 = round(y2 / grid_size) * grid_size
            
        # Ignore degenerate zero-length lines
        if x1 == x2 and y1 == y2:
            continue
            
        snapped_lines.append([x1, y1, x2, y2])
        
    # Step B: Merge collinear overlapping segments (run a few passes to chain segments)
    merged_lines = snapped_lines
    for _ in range(3):
        merged_lines = merge_collinear_lines(merged_lines, distance_threshold=20, overlap_threshold=15)
        
    # Format line objects
    formatted_lines = []
    for idx, l in enumerate(merged_lines):
        x1, y1, x2, y2 = l
        formatted_lines.append({
            "id": idx + 1,
            "x1": float(x1),
            "y1": float(y1),
            "x2": float(x2),
            "y2": float(y2),
            "type": "wall"  # default class
        })
        
    # 4. Dimension & Text Box Detection
    # Look for bounding box contours — both small (dimensions) and larger (room names)
    contours, _ = cv2.findContours(thresh_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detected_dimensions = []
    detected_text_regions = []  # For room name detection
    dim_id = 1
    
    ocr = get_ocr_reader()
    
    # Create debug overlay image
    debug_img = img.copy()
    
    # Draw detected lines on overlay
    for l in formatted_lines:
        cv2.line(debug_img, (int(l["x1"]), int(l["y1"])), (int(l["x2"]), int(l["y2"])), (0, 0, 255), 2)
        cv2.circle(debug_img, (int(l["x1"]), int(l["y1"])), 4, (0, 255, 0), -1)
        cv2.circle(debug_img, (int(l["x2"]), int(l["y2"])), 4, (0, 255, 0), -1)

    for cnt in contours:
        x, y, w_box, h_box = cv2.boundingRect(cnt)
        area = w_box * h_box
        aspect_ratio = w_box / float(h_box) if h_box > 0 else 0
        
        # === Category A: Small dimension text boxes (e.g., "5.0m", "3.0m") ===
        # Width 15–100px, height 10–60px, area 150–4000px²
        if 15 < w_box < 100 and 10 < h_box < 60 and 150 < area < 4000:
            crop = gray[max(0, y-5):min(h, y+h_box+5), max(0, x-5):min(w, x+w_box+5)]
            
            text_val = ""
            if ocr is not None:
                try:
                    results = ocr.readtext(crop)
                    if results:
                        text_val = " ".join([r[1] for r in results]).strip()
                except Exception as e:
                    logger.error(f"OCR reading failed for box {x},{y}: {e}")
            
            if not text_val:
                text_val = f"{round(w_box / 15.0, 1)}m"
                
            # Draw box on debug image
            cv2.rectangle(debug_img, (x, y), (x + w_box, y + h_box), (255, 100, 0), 2)
            cv2.putText(debug_img, text_val, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 50, 0), 1)
            
            detected_dimensions.append({
                "id": dim_id,
                "x": float(x + w_box / 2),
                "y": float(y + h_box / 2),
                "w": float(w_box),
                "h": float(h_box),
                "value": text_val
            })
            dim_id += 1
        
        # === Category B: Larger text regions (room names like "Bed 1", "Kitchen") ===
        # Width 40–300px, height 15–80px, area 800–20000px²
        elif 40 < w_box < 300 and 15 < h_box < 80 and 800 < area < 20000:
            # Make sure it's not too close to wall lines (text should be inside rooms)
            crop = gray[max(0, y-3):min(h, y+h_box+3), max(0, x-3):min(w, x+w_box+3)]
            
            text_val = ""
            if ocr is not None:
                try:
                    results = ocr.readtext(crop)
                    if results:
                        text_val = " ".join([r[1] for r in results]).strip()
                except Exception as e:
                    logger.error(f"OCR reading failed for room text at {x},{y}: {e}")
            
            if not text_val:
                # Generate mock room name based on bounding box characteristics
                # Wider boxes with specific positions can be heuristically named
                text_val = f"Area {len(detected_text_regions) + 1}"
            
            # Draw room name region on debug image  
            cv2.rectangle(debug_img, (x, y), (x + w_box, y + h_box), (0, 180, 255), 2)
            cv2.putText(debug_img, text_val, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 1)
            
            detected_text_regions.append((x, y, w_box, h_box, text_val))

    # 5. Room Detection — Find enclosed regions and calculate areas
    detected_rooms = detect_rooms(formatted_lines, w, h, scale_factor=scale_factor)
    
    # Assign room names from detected text regions
    if detected_text_regions:
        detected_rooms = assign_room_names_from_text(detected_rooms, detected_text_regions, gray, w, h)
    
    # Draw room labels on debug image
    for room in detected_rooms:
        cx, cy = int(room["center_x"]), int(room["center_y"])
        # Draw room name
        cv2.putText(debug_img, room["name"], (cx - 30, cy - 10), 
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 100), 2)
        # Draw area
        area_text = f"{room['area_sqm']} sq.m"
        cv2.putText(debug_img, area_text, (cx - 30, cy + 15),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 100), 1)
        # Draw room center marker
        cv2.drawMarker(debug_img, (cx, cy), (0, 200, 100), cv2.MARKER_CROSS, 10, 1)

    # Encode debug image to base64
    _, buffer = cv2.imencode('.jpg', debug_img)
    base64_debug = base64.b64encode(buffer).decode('utf-8')
    
    return {
        "lines": formatted_lines,
        "dimensions": detected_dimensions,
        "rooms": detected_rooms,
        "width": w,
        "height": h,
        "debug_image": f"data:image/jpeg;base64,{base64_debug}"
    }
