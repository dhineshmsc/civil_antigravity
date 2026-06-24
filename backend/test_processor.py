import cv2
import numpy as np
import sys
import os

# Append project root to path to resolve imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.processor import process_sketch_image
from backend.dxf_generator import generate_dxf
from backend.pdf_generator import generate_pdf

def create_synthetic_sketch():
    """Generates a synthetic sketch image (black lines on a crumpled/greyish paper background)
    to test the OpenCV parsing algorithm.
    """
    # Create greyish background image (simulating paper)
    img = np.ones((600, 800, 3), dtype=np.uint8) * 220
    
    # Draw some walls (rooms) with black sketched lines
    # Outer boundaries
    cv2.line(img, (100, 100), (700, 100), (40, 40, 40), 3) # Top
    cv2.line(img, (700, 100), (700, 500), (35, 35, 35), 3) # Right
    cv2.line(img, (700, 500), (100, 500), (42, 42, 42), 3) # Bottom
    cv2.line(img, (100, 500), (100, 100), (38, 38, 38), 3) # Left
    
    # Internal dividing wall
    cv2.line(img, (400, 100), (400, 500), (45, 45, 45), 3) # Middle split
    
    # Draw some "hand-drawn text" regions (simulated drawing labels)
    # We can write text that cv2.threshold will pick up as blobs
    cv2.putText(img, "4.5m", (230, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 2)
    cv2.putText(img, "3.5m", (530, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 2)
    
    # Encode as JPEG bytes
    _, encoded_img = cv2.imencode(".jpg", img)
    return encoded_img.tobytes()

def run_tests():
    print("==================================================")
    print("Starting AI Sketch to AutoCAD Processor Tests")
    print("==================================================")
    
    # 1. Create synthetic sketch bytes
    print("[1/4] Generating synthetic hand-drawn sketch...")
    img_bytes = create_synthetic_sketch()
    print(f"      Sketch bytes size: {len(img_bytes)} bytes.")
    
    # 2. Run through the Sketch Processor
    print("[2/4] Executing OpenCV Sketch parsing pipeline...")
    try:
        results = process_sketch_image(
            image_bytes=img_bytes,
            threshold_val=110,
            min_line_len=30,
            max_line_gap=15,
            grid_snap=True,
            grid_size=20
        )
        
        lines = results["lines"]
        dims = results["dimensions"]
        img_w = results["width"]
        img_h = results["height"]
        
        print(f"      Image parsed successfully: {img_w}x{img_h} pixels.")
        print(f"      Detected lines count: {len(lines)}")
        print(f"      Detected dimensions count: {len(dims)}")
        
        assert len(lines) > 0, "Line detection failed - zero lines extracted!"
        assert len(dims) > 0, "Text contour detection failed - zero regions extracted!"
        assert "debug_image" in results, "Missing preprocessed overlay image!"
        print("      PASS: Line and dimension parsing matches requirements.")
        
    except Exception as e:
        print(f"      FAIL: Sketch processor threw exception: {e}")
        sys.exit(1)
        
    # 3. Test DXF Exporter
    print("[3/4] Testing ezdxf CAD export...")
    try:
        dxf_bytes = generate_dxf(
            lines=lines,
            dimensions=dims,
            img_width=img_w,
            img_height=img_h,
            scale_factor=0.02
        )
        print(f"      DXF compiled successfully: {len(dxf_bytes)} bytes.")
        assert len(dxf_bytes) > 0, "Generated DXF file is empty!"
        print("      PASS: DXF CAD output validated.")
    except Exception as e:
        print(f"      FAIL: DXF generator failed: {e}")
        sys.exit(1)
        
    # 4. Test PDF Exporter
    print("[4/4] Testing ReportLab vector PDF export...")
    try:
        pdf_bytes = generate_pdf(
            lines=lines,
            dimensions=dims,
            img_width=img_w,
            img_height=img_h
        )
        print(f"      PDF compiled successfully: {len(pdf_bytes)} bytes.")
        assert len(pdf_bytes) > 0, "Generated PDF file is empty!"
        print("      PASS: PDF drawing sheet output validated.")
    except Exception as e:
        print(f"      FAIL: PDF generator failed: {e}")
        sys.exit(1)

    print("==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! Pipeline verified.")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
