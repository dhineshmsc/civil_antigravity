from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import logging
import mimetypes

# Register .jsx MIME type for static files serving
mimetypes.add_type("application/javascript", ".jsx")

from backend.processor import process_sketch_image
from backend.dxf_generator import generate_dxf
from backend.pdf_generator import generate_pdf
# from backend.dwf_generator import generate_dwf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Sketch to AutoCAD API",
    description="Vectorize architectural sketch drawings, verify in real-time, and download CAD DXF/PDF/DWF sheets.",
    version="1.1.0"
)

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for export endpoints
class LineItem(BaseModel):
    id: int
    x1: float
    y1: float
    x2: float
    y2: float
    type: str

class DimensionItem(BaseModel):
    id: int
    x: float
    y: float
    value: str

class RoomItem(BaseModel):
    id: int
    name: str
    area_sqm: float
    width_m: Optional[float] = 0.0
    height_m: Optional[float] = 0.0
    center_x: float
    center_y: float
    bbox_x: Optional[float] = 0.0
    bbox_y: Optional[float] = 0.0
    bbox_w: Optional[float] = 0.0
    bbox_h: Optional[float] = 0.0

class TextAnnotationItem(BaseModel):
    id: int
    x: float
    y: float
    text: str
    font_size: Optional[float] = 12.0

class ExportRequest(BaseModel):
    lines: List[LineItem]
    dimensions: List[DimensionItem]
    rooms: List[RoomItem] = []
    text_annotations: List[TextAnnotationItem] = []
    width: int
    height: int
    scale_factor: float = 0.02

# Endpoints
@app.post("/api/process")
async def process_sketch(
    image: UploadFile = File(...),
    threshold_val: int = Form(110),
    min_line_len: int = Form(40),
    max_line_gap: int = Form(15),
    grid_snap: bool = Form(True),
    grid_size: int = Form(20),
    scale_factor: float = Form(0.02)
):
    """Processes uploaded sketch image using OpenCV. Returns lines, dimensions, and rooms list."""
    logger.info(f"Received sketch processing request. File: {image.filename}")
    try:
        # Read uploaded image bytes
        image_bytes = await image.read()
        
        # Process image
        result = process_sketch_image(
            image_bytes=image_bytes,
            threshold_val=threshold_val,
            min_line_len=min_line_len,
            max_line_gap=max_line_gap,
            grid_snap=grid_snap,
            grid_size=grid_size,
            scale_factor=scale_factor
        )
        return result
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/dxf")
async def export_dxf(request: ExportRequest):
    """Generates and streams an AutoCAD DXF file from verified vectors."""
    logger.info("DXF export request received.")
    try:
        # Convert Pydantic models to dictionaries
        lines_dict = [line.model_dump() for line in request.lines]
        dims_dict = [dim.model_dump() for dim in request.dimensions]
        rooms_dict = [room.model_dump() for room in request.rooms]
        annotations_dict = [ann.model_dump() for ann in request.text_annotations]
        
        dxf_data = generate_dxf(
            lines=lines_dict,
            dimensions=dims_dict,
            rooms=rooms_dict,
            text_annotations=annotations_dict,
            img_width=request.width,
            img_height=request.height,
            scale_factor=request.scale_factor
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(dxf_data),
            media_type="application/dxf",
            headers={
                "Content-Disposition": "attachment; filename=floorplan.dxf",
                "Content-Length": str(len(dxf_data))
            }
        )
    except Exception as e:
        logger.error(f"Error exporting DXF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/pdf")
async def export_pdf(request: ExportRequest):
    """Generates and streams a vector PDF from verified vectors."""
    logger.info("PDF export request received.")
    try:
        # Convert Pydantic models to dictionaries
        lines_dict = [line.model_dump() for line in request.lines]
        dims_dict = [dim.model_dump() for dim in request.dimensions]
        rooms_dict = [room.model_dump() for room in request.rooms]
        annotations_dict = [ann.model_dump() for ann in request.text_annotations]
        
        pdf_data = generate_pdf(
            lines=lines_dict,
            dimensions=dims_dict,
            rooms=rooms_dict,
            text_annotations=annotations_dict,
            img_width=request.width,
            img_height=request.height
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=floorplan.pdf",
                "Content-Length": str(len(pdf_data))
            }
        )
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/estimate_pdf")
async def export_estimate_pdf(request: ExportRequest):
    """Generates and streams a PDF estimate for the drawn vectors."""
    logger.info("Estimate PDF export request received.")
    try:
        lines_dict = [line.model_dump() for line in request.lines]
        
        from backend.pdf_generator import generate_estimate_pdf
        
        pdf_data = generate_estimate_pdf(
            lines=lines_dict,
            scale_factor=request.scale_factor
        )
        
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=floorplan_estimate.pdf",
                "Content-Length": str(len(pdf_data))
            }
        )
    except Exception as e:
        logger.error(f"Error exporting Estimate PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/export/dwf")
async def export_dwf(request: ExportRequest):
    """Generates and streams a DWF (Design Web Format) package from verified vectors."""
    logger.info("DWF export request received.")
    try:
        # Convert Pydantic models to dictionaries
        lines_dict = [line.model_dump() for line in request.lines]
        dims_dict = [dim.model_dump() for dim in request.dimensions]
        rooms_dict = [room.model_dump() for room in request.rooms]
        annotations_dict = [ann.model_dump() for ann in request.text_annotations]
        
        dwf_data = generate_dwf(
            lines=lines_dict,
            dimensions=dims_dict,
            rooms=rooms_dict,
            text_annotations=annotations_dict,
            img_width=request.width,
            img_height=request.height,
            scale_factor=request.scale_factor
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(dwf_data),
            media_type="application/x-dwf",
            headers={
                "Content-Disposition": "attachment; filename=floorplan.dwf",
                "Content-Length": str(len(dwf_data))
            }
        )
    except Exception as e:
        logger.error(f"Error exporting DWF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Setup Static Directories and Frontend mounting
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "static"))

# Ensure static folder exists
os.makedirs(static_dir, exist_ok=True)

# Mount static files at /static
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get_frontend():
    """Serves the main single page web application index.html."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    else:
        # Fallback if frontend is not written yet
        return {"status": "Backend running. Please write the frontend files in static/."}

