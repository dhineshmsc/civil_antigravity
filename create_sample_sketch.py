import cv2
import numpy as np

def create_sample():
    # Create greyish background image representing paper
    img = np.ones((600, 800, 3), dtype=np.uint8) * 225
    
    # Draw some "hand-drawn" messy walls
    # Outer boundaries (slightly wobbly)
    cv2.line(img, (95, 102), (702, 98), (40, 40, 40), 3) # Top
    cv2.line(img, (702, 98), (698, 503), (35, 35, 35), 3) # Right
    cv2.line(img, (698, 503), (102, 497), (42, 42, 42), 3) # Bottom
    cv2.line(img, (102, 497), (95, 102), (38, 38, 38), 3) # Left
    
    # Internal room dividers
    cv2.line(img, (398, 102), (402, 497), (45, 45, 45), 3) # Middle wall
    cv2.line(img, (102, 298), (398, 302), (40, 40, 40), 3) # Room division
    
    # Door and Window gaps (we draw walls with gaps or labels)
    # Let's write simulated dimension text annotations
    cv2.putText(img, "5.0m", (220, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 2)
    cv2.putText(img, "4.0m", (520, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (45, 45, 45), 2)
    cv2.putText(img, "3.0m", (60, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (38, 38, 38), 2)
    cv2.putText(img, "Bed 1", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "Bath", (200, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    cv2.putText(img, "Kitchen", (500, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
    
    # Save the file
    cv2.imwrite("sample_sketch.jpg", img)
    print("Created sample_sketch.jpg successfully.")

if __name__ == "__main__":
    create_sample()
