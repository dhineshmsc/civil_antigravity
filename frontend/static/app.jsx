// AI Sketch to AutoCAD - Main React Application

const { useState, useEffect, useRef } = React;

// --- Helper Functions ---
function getAngle(x1, y1, x2, y2) {
    return Math.atan2(y2 - y1, x2 - x1);
}

function getLength(x1, y1, x2, y2) {
    return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

// --- Console Log Helper ---
function formatTime() {
    const d = new Date();
    return d.toTimeString().split(' ')[0];
}

// --- Three.js 3D Viewer Component ---
function ThreeViewer({ lines, imgWidth, imgHeight, scale }) {
    const containerRef = useRef(null);
    const sceneRef = useRef(null);
    const rendererRef = useRef(null);
    const cameraRef = useRef(null);
    const controlsRef = useRef(null);
    
    useEffect(() => {
        if (!containerRef.current) return;
        
        // 1. Initialize Scene & Renderer
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x070a13);
        sceneRef.current = scene;
        
        // Subtle blue-ish fog for premium visual depth
        scene.fog = new THREE.FogExp2(0x070a13, 0.015);
        
        const width = containerRef.current.clientWidth;
        const height = containerRef.current.clientHeight;
        
        const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        camera.position.set(0, 20, 25);
        cameraRef.current = camera;
        
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        renderer.shadowMap.enabled = true;
        rendererRef.current = renderer;
        
        // Clear previous content
        containerRef.current.innerHTML = '';
        containerRef.current.appendChild(renderer.domElement);
        
        // 2. Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambientLight);
        
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(20, 40, 20);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        scene.add(dirLight);
        
        const gridHelper = new THREE.GridHelper(100, 100, 0x06b6d4, 0x1e293b);
        gridHelper.position.y = -0.01;
        scene.add(gridHelper);
        
        // 3. Orbit Controls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.maxPolarAngle = Math.PI / 2 - 0.05; // Prevent camera going below floor
        controlsRef.current = controls;
        
        // 4. Handle Window Resize
        const handleResize = () => {
            if (!containerRef.current) return;
            const w = containerRef.current.clientWidth;
            const h = containerRef.current.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        };
        window.addEventListener('resize', handleResize);
        
        // 5. Animation Loop
        let animationFrameId;
        const animate = () => {
            animationFrameId = requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();
        
        return () => {
            cancelAnimationFrame(animationFrameId);
            window.removeEventListener('resize', handleResize);
        };
    }, []);
    
    // Extrude 3D walls when lines or scale change
    useEffect(() => {
        const scene = sceneRef.current;
        if (!scene) return;
        
        // Remove existing meshes from previous render
        const meshesToRemove = [];
        scene.traverse((child) => {
            if (child.isMesh && child.name !== 'floor') {
                meshesToRemove.push(child);
            }
        });
        meshesToRemove.forEach(mesh => scene.remove(mesh));
        
        // Render walls
        const wallMaterial = new THREE.MeshStandardMaterial({
            color: 0x334155, // slate concrete grey
            roughness: 0.5,
            metalness: 0.1,
            side: THREE.DoubleSide
        });
        
        const doorMaterial = new THREE.MeshStandardMaterial({
            color: 0xf97316, // orange frame for door visualization
            transparent: true,
            opacity: 0.4
        });

        const windowMaterial = new THREE.MeshStandardMaterial({
            color: 0x06b6d4, // glowing cyan glass
            transparent: true,
            opacity: 0.6,
            roughness: 0.1
        });
        
        // Extrude parameters in meters
        const wallHeight = 3.0;
        const wallThickness = 0.22;
        
        // Calculate offsets to center the 3D model relative to image coordinate system
        const offset3Dx = (imgWidth * scale) / 2;
        const offset3Dz = (imgHeight * scale) / 2;
        
        lines.forEach((line) => {
            const x1 = line.x1 * scale - offset3Dx;
            const z1 = line.y1 * scale - offset3Dz; // Image Y maps to 3D Z
            const x2 = line.x2 * scale - offset3Dx;
            const z2 = line.y2 * scale - offset3Dz;
            
            const dx = x2 - x1;
            const dz = z2 - z1;
            const len = Math.sqrt(dx*dx + dz*dz);
            if (len === 0) return;
            
            const midX = (x1 + x2) / 2;
            const midZ = (z1 + z2) / 2;
            const angle = Math.atan2(dz, dx);
            
            let wallMesh;
            const lineType = (line.type || 'wall').toUpperCase();
            
            if (lineType === 'WINDOW') {
                // Windows are drawn as small floor walls, then glass, then top wall
                const windowHeight = 1.2;
                const sillHeight = 0.9;
                
                // Bottom Solid Wall
                const gBottom = new THREE.BoxGeometry(len, sillHeight, wallThickness);
                const mBottom = new THREE.Mesh(gBottom, wallMaterial);
                mBottom.position.set(midX, sillHeight / 2, midZ);
                mBottom.rotation.y = -angle;
                scene.add(mBottom);
                
                // Glass Middle
                const gGlass = new THREE.BoxGeometry(len, windowHeight, wallThickness * 0.5);
                const mGlass = new THREE.Mesh(gGlass, windowMaterial);
                mGlass.position.set(midX, sillHeight + windowHeight / 2, midZ);
                mGlass.rotation.y = -angle;
                scene.add(mGlass);
                
                // Top Solid Wall
                const topWallH = wallHeight - sillHeight - windowHeight;
                if (topWallH > 0) {
                    const gTop = new THREE.BoxGeometry(len, topWallH, wallThickness);
                    const mTop = new THREE.Mesh(gTop, wallMaterial);
                    mTop.position.set(midX, wallHeight - topWallH / 2, midZ);
                    mTop.rotation.y = -angle;
                    scene.add(mTop);
                }
            } 
            else if (lineType === 'DOOR') {
                // Doors have an opening, and a visual lintel (header wall) at the top
                const doorHeight = 2.1;
                const headerH = wallHeight - doorHeight;
                
                if (headerH > 0) {
                    const gHeader = new THREE.BoxGeometry(len, headerH, wallThickness);
                    const mHeader = new THREE.Mesh(gHeader, wallMaterial);
                    mHeader.position.set(midX, wallHeight - headerH / 2, midZ);
                    mHeader.rotation.y = -angle;
                    scene.add(mHeader);
                }
                
                // Small indicator arc or thin block to show open door
                const gDoorLeaf = new THREE.BoxGeometry(0.04, doorHeight, len * 0.9);
                const mDoorLeaf = new THREE.Mesh(gDoorLeaf, doorMaterial);
                // Swing it open slightly (45 deg)
                mDoorLeaf.position.set(midX, doorHeight / 2, midZ);
                mDoorLeaf.rotation.y = -angle + Math.PI / 4;
                scene.add(mDoorLeaf);
            } 
            else {
                // Standard solid wall
                const geometry = new THREE.BoxGeometry(len, wallHeight, wallThickness);
                const mesh = new THREE.Mesh(geometry, wallMaterial);
                mesh.position.set(midX, wallHeight / 2, midZ);
                mesh.rotation.y = -angle;
                scene.add(mesh);
            }
        });
        
    }, [lines, imgWidth, imgHeight, scale]);
    
    return (
        <div className="three-container">
            <div className="three-overlay">
                <div><strong>3D Structural Model</strong></div>
                <div>Left Click + Drag: Orbit Camera</div>
                <div>Right Click + Drag: Pan Space</div>
                <div>Scroll wheel: Zoom Camera</div>
            </div>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
        </div>
    );
}

// --- Main App Component ---
function App() {
    // UI Layout Tabs
    const [activeTab, setActiveTab] = useState('upload');
    const [serverOnline, setServerOnline] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [logs, setLogs] = useState([
        { time: formatTime(), type: 'info', msg: 'System initialized. Ready for architectural sketch uploads.' }
    ]);
    
    // Image state
    const [selectedFile, setSelectedFile] = useState(null);
    const [originalImgUrl, setOriginalImgUrl] = useState('');
    const [processedImgUrl, setProcessedImgUrl] = useState('');
    const [imgDimensions, setImgDimensions] = useState({ width: 800, height: 600 });
    
    // CAD vectors
    const [lines, setLines] = useState([]);
    const [dimensions, setDimensions] = useState([]);
    
    // Processing Parameters
    const [thresholdVal, setThresholdVal] = useState(110);
    const [minLineLen, setMinLineLen] = useState(40);
    const [maxLineGap, setMaxLineGap] = useState(15);
    const [gridSnap, setGridSnap] = useState(true);
    const [gridSize, setGridSize] = useState(20);
    const [drawingScale, setDrawingScale] = useState(0.02); // 1 pixel = 0.02m (i.e. 50px = 1m)
    
    // 2D CAD Canvas Editing Tools
    const [activeTool, setActiveTool] = useState('select');
    const [selectedPoint, setSelectedPoint] = useState(null); // { lineId, end: 'start'|'end' }
    const [dragStartPoint, setDragStartPoint] = useState(null);
    const [drawTempLine, setDrawTempLine] = useState(null); // { x1, y1, x2, y2 }
    const [editingDim, setEditingDim] = useState(null); // { id, x, y, value }
    const [dimOverrideText, setDimOverrideText] = useState('');

    const addLog = (msg, type = 'info') => {
        setLogs(prev => [{ time: formatTime(), type, msg }, ...prev]);
    };
    
    // Verify backend is reachable
    useEffect(() => {
        fetch('/')
            .then(() => setServerOnline(true))
            .catch(() => {
                setServerOnline(false);
                addLog('FastAPI Backend connection failed. Ensure server is running on localhost.', 'error');
            });
    }, []);
    
    // File drag & drop and change handlers
    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        setSelectedFile(file);
        const url = URL.createObjectURL(file);
        setOriginalImgUrl(url);
        addLog(`File loaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 'info');
        
        // Reset state for new upload
        setLines([]);
        setDimensions([]);
        setProcessedImgUrl('');
    };
    
    // Handle processing API call
    const processSketch = () => {
        if (!selectedFile) {
            addLog('Please select a sketch image first.', 'warning');
            return;
        }
        
        setIsLoading(true);
        addLog('Sending sketch to AI Detection pipeline...', 'info');
        
        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('threshold_val', thresholdVal.toString());
        formData.append('min_line_len', minLineLen.toString());
        formData.append('max_line_gap', maxLineGap.toString());
        formData.append('grid_snap', gridSnap.toString());
        formData.append('grid_size', gridSize.toString());
        
        fetch('/api/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => { throw new Error(text); });
            }
            return response.json();
        })
        .then(data => {
            setLines(data.lines);
            setDimensions(data.dimensions);
            setProcessedImgUrl(data.debug_image);
            setImgDimensions({ width: data.width, height: data.height });
            
            addLog(`Vectorization complete. Detected ${data.lines.length} wall lines and ${data.dimensions.length} dimension text boxes.`, 'success');
            
            // Auto switch to the 2D CAD Editor for verification
            setActiveTab('cad2d');
        })
        .catch(err => {
            addLog(`Processing failed: ${err.message}`, 'error');
        })
        .finally(() => {
            setIsLoading(false);
        });
    };
    
    // Export vector drawings as DXF
    const handleExportDXF = () => {
        if (lines.length === 0) {
            addLog('No lines to export. Process a sketch first.', 'warning');
            return;
        }
        
        addLog('Requesting DXF generation...', 'info');
        fetch('/api/export/dxf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lines: lines,
                dimensions: dimensions,
                width: imgDimensions.width,
                height: imgDimensions.height,
                scale_factor: drawingScale
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('DXF generation failed.');
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${selectedFile ? selectedFile.name.split('.')[0] : 'floorplan'}.dxf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            
            addLog('AutoCAD DXF generated and downloaded successfully.', 'success');
        })
        .catch(err => {
            addLog(`Export failed: ${err.message}`, 'error');
        });
    };
    
    // Export vector drawings as PDF
    const handleExportPDF = () => {
        if (lines.length === 0) {
            addLog('No plan lines to export.', 'warning');
            return;
        }
        
        addLog('Requesting PDF layout compilation...', 'info');
        fetch('/api/export/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lines: lines,
                dimensions: dimensions,
                width: imgDimensions.width,
                height: imgDimensions.height,
                scale_factor: drawingScale
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('PDF compilation failed.');
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${selectedFile ? selectedFile.name.split('.')[0] : 'floorplan'}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            
            addLog('Landscape CAD sheet PDF downloaded successfully.', 'success');
        })
        .catch(err => {
            addLog(`PDF Export failed: ${err.message}`, 'error');
        });
    };
    
    // --- 2D Vector CAD Editor SVG Handlers ---
    const getCanvasMouseCoords = (e, svgElement) => {
        const rect = svgElement.getBoundingClientRect();
        // Calculate coordinates relative to original image pixel coordinates
        const scaleX = imgDimensions.width / rect.width;
        const scaleY = imgDimensions.height / rect.height;
        let x = (e.clientX - rect.left) * scaleX;
        let y = (e.clientY - rect.top) * scaleY;
        
        if (gridSnap) {
            x = Math.round(x / gridSize) * gridSize;
            y = Math.round(y / gridSize) * gridSize;
        }
        return { x, y };
    };
    
    const handleCanvasMouseDown = (e) => {
        const svg = e.currentTarget;
        const coords = getCanvasMouseCoords(e, svg);
        
        if (activeTool === 'select') {
            // Check if user clicked near any line endpoints (within snapping distance)
            const tolerance = 20; // image px
            let found = null;
            
            for (let line of lines) {
                const dist1 = getLength(coords.x, coords.y, line.x1, line.y1);
                if (dist1 < tolerance) {
                    found = { lineId: line.id, end: 'start' };
                    break;
                }
                const dist2 = getLength(coords.x, coords.y, line.x2, line.y2);
                if (dist2 < tolerance) {
                    found = { lineId: line.id, end: 'end' };
                    break;
                }
            }
            
            if (found) {
                setSelectedPoint(found);
                setDragStartPoint(coords);
            }
        } 
        else if (['wall', 'door', 'window'].includes(activeTool)) {
            // Start drawing a new line
            setDrawTempLine({ x1: coords.x, y1: coords.y, x2: coords.x, y2: coords.y });
        }
    };
    
    const handleCanvasMouseMove = (e) => {
        const svg = e.currentTarget;
        const coords = getCanvasMouseCoords(e, svg);
        
        if (activeTool === 'select' && selectedPoint) {
            // Dragging an existing line endpoint
            setLines(prev => prev.map(line => {
                if (line.id === selectedPoint.lineId) {
                    if (selectedPoint.end === 'start') {
                        return { ...line, x1: coords.x, y1: coords.y };
                    } else {
                        return { ...line, x2: coords.x, y2: coords.y };
                    }
                }
                return line;
            }));
        } 
        else if (drawTempLine) {
            // Updating temporary line layout
            setDrawTempLine(prev => ({ ...prev, x2: coords.x, y2: coords.y }));
        }
    };
    
    const handleCanvasMouseUp = (e) => {
        const svg = e.currentTarget;
        const coords = getCanvasMouseCoords(e, svg);
        
        if (activeTool === 'select' && selectedPoint) {
            setSelectedPoint(null);
            setDragStartPoint(null);
            addLog('Line node updated.', 'info');
        } 
        else if (drawTempLine) {
            // Validate distance, don't create zero lines
            const len = getLength(drawTempLine.x1, drawTempLine.y1, drawTempLine.x2, drawTempLine.y2);
            if (len > 5) {
                const newId = lines.length > 0 ? Math.max(...lines.map(l => l.id)) + 1 : 1;
                const newLine = {
                    id: newId,
                    x1: drawTempLine.x1,
                    y1: drawTempLine.y1,
                    x2: drawTempLine.x2,
                    y2: drawTempLine.y2,
                    type: activeTool === 'wall' ? 'wall' : activeTool
                };
                
                setLines(prev => [...prev, newLine]);
                addLog(`New ${activeTool.toUpperCase()} added to plan.`, 'info');
            }
            setDrawTempLine(null);
        }
    };
    
    // Double click dimension text to edit
    const handleDimDoubleClick = (dim) => {
        setEditingDim(dim);
        setDimOverrideText(dim.value);
    };
    
    const saveDimOverride = () => {
        if (!editingDim) return;
        setDimensions(prev => prev.map(d => {
            if (d.id === editingDim.id) {
                return { ...d, value: dimOverrideText };
            }
            return d;
        }));
        addLog(`Dimension value updated to: "${dimOverrideText}"`, 'info');
        setEditingDim(null);
    };
    
    // Delete line or dimension
    const handleElementClick = (e, item, isDim = false) => {
        e.stopPropagation(); // prevent canvas click triggers
        
        if (activeTool === 'delete') {
            if (isDim) {
                setDimensions(prev => prev.filter(d => d.id !== item.id));
                addLog('Dimension box deleted.', 'warning');
            } else {
                setLines(prev => prev.filter(l => l.id !== item.id));
                addLog(`Line segment #${item.id} deleted.`, 'warning');
            }
        }
    };
    
    return (
        <React.Fragment>
            {/* Header Area */}
            <header className="app-header">
                <div className="brand">
                    <div className="brand-icon">
                        <svg fill="none" viewBox="0 0 24 24" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div className="brand-text">
                        <h1>AutoSketch CAD Engine</h1>
                        <span>Autonomous Vectorizer & Extruder</span>
                    </div>
                </div>
                
                <div className="server-status">
                    <div className={`status-dot ${serverOnline ? '' : 'offline'}`} />
                    <span>Server: {serverOnline ? 'LOCAL DIRECTORY MOUNTED' : 'OFFLINE'}</span>
                </div>
            </header>
            
            <div className="app-container">
                {/* Control Sidebar */}
                <aside className="sidebar">
                    <div>
                        <div className="section-title">
                            <span>1. Sketch Source</span>
                        </div>
                        <div className="upload-zone">
                            <svg fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                            </svg>
                            <div className="upload-text">
                                {selectedFile ? <span><strong>{selectedFile.name}</strong></span> : <span><strong>Drag & Drop Sketch</strong> or click to browse</span>}
                            </div>
                            <div className="upload-hint">Supports JPEG, PNG up to 10MB</div>
                            <input type="file" className="file-input" accept="image/*" onChange={handleFileChange} />
                        </div>
                    </div>
                    
                    <div>
                        <div className="section-title">
                            <span>2. Detection Settings</span>
                        </div>
                        <div className="control-group">
                            <div className="control-item">
                                <div className="control-label">
                                    <span>Adaptive Threshold</span>
                                    <span className="control-value">{thresholdVal}</span>
                                </div>
                                <input type="range" className="control-input" min="30" max="220" value={thresholdVal} onChange={e => setThresholdVal(parseInt(e.target.value))} />
                            </div>
                            <div className="control-item">
                                <div className="control-label">
                                    <span>Min Line Length</span>
                                    <span className="control-value">{minLineLen} px</span>
                                </div>
                                <input type="range" className="control-input" min="15" max="150" value={minLineLen} onChange={e => setMinLineLen(parseInt(e.target.value))} />
                            </div>
                            <div className="control-item">
                                <div className="control-label">
                                    <span>Line Connector Gap</span>
                                    <span className="control-value">{maxLineGap} px</span>
                                </div>
                                <input type="range" className="control-input" min="5" max="60" value={maxLineGap} onChange={e => setMaxLineGap(parseInt(e.target.value))} />
                            </div>
                            
                            <hr style={{ borderColor: 'var(--border-color)', margin: '5px 0' }} />
                            
                            <div className="toggle-item">
                                <span>CAD Grid Snap (Corner Alignment)</span>
                                <label className="toggle-switch">
                                    <input type="checkbox" checked={gridSnap} onChange={e => setGridSnap(e.target.checked)} />
                                    <span className="slider-switch" />
                                </label>
                            </div>
                            
                            {gridSnap && (
                                <div className="control-item" style={{ marginTop: '5px' }}>
                                    <div className="control-label">
                                        <span>Grid Increment Size</span>
                                        <span className="control-value">{gridSize} px</span>
                                    </div>
                                    <input type="range" className="control-input" min="5" max="50" step="5" value={gridSize} onChange={e => setGridSize(parseInt(e.target.value))} />
                                </div>
                            )}
                        </div>
                    </div>
                    
                    <button className="btn btn-primary" onClick={processSketch} disabled={!selectedFile || isLoading}>
                        {isLoading ? (
                            <React.Fragment>
                                <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
                                <span>Analyzing Sketch...</span>
                            </React.Fragment>
                        ) : (
                            <span>Run AI Vectorization</span>
                        )}
                    </button>
                    
                    <div>
                        <div className="section-title">
                            <span>3. CAD Scales & Layout</span>
                        </div>
                        <div className="control-group">
                            <div className="control-item">
                                <div className="control-label">
                                    <span>Workspace Scale (m/px)</span>
                                    <span className="control-value">{drawingScale.toFixed(3)}</span>
                                </div>
                                <input type="range" className="control-input" min="0.005" max="0.1" step="0.005" value={drawingScale} onChange={e => setDrawingScale(parseFloat(e.target.value))} />
                                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                                    Current Ratio: 50 pixels = {(50 * drawingScale).toFixed(2)} meters
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div style={{ marginTop: 'auto' }}>
                        <div className="section-title">
                            <span>4. Exporters</span>
                        </div>
                        <div className="btn-group">
                            <button className="btn btn-success" onClick={handleExportDXF} disabled={lines.length === 0}>
                                DXF (CAD)
                            </button>
                            <button className="btn btn-outline" onClick={handleExportPDF} disabled={lines.length === 0}>
                                PDF Vector
                            </button>
                        </div>
                    </div>
                </aside>
                
                {/* Main Workspace Area */}
                <main className="workspace">
                    {/* Workspace Tabs */}
                    <nav className="tabs-nav">
                        <button className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`} onClick={() => setActiveTab('upload')}>
                            <svg fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                            </svg>
                            <span>Sketch & AI View</span>
                        </button>
                        <button className={`tab-btn ${activeTab === 'cad2d' ? 'active' : ''}`} onClick={() => { if (lines.length > 0) setActiveTab('cad2d'); else addLog('Process a sketch first to view vectorizer CAD editor.', 'warning'); }}>
                            <svg fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
                            </svg>
                            <span>2D Canvas Editor</span>
                        </button>
                        <button className={`tab-btn ${activeTab === 'cad3d' ? 'active' : ''}`} onClick={() => { if (lines.length > 0) setActiveTab('cad3d'); else addLog('Process a sketch first to view 3D architectural model.', 'warning'); }}>
                            <svg fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
                            </svg>
                            <span>3D Extrusion View</span>
                        </button>
                    </nav>
                    
                    {/* Tab 1: Upload View */}
                    <div className={`tab-content ${activeTab === 'upload' ? 'active' : ''}`}>
                        <div className="canvas-viewport">
                            {!originalImgUrl ? (
                                <div className="empty-state">
                                    <svg fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 13.5h3.86a2.25 2.25 0 012.008 1.24l.885 1.77a2.25 2.25 0 002.007 1.24h1.98a2.25 2.25 0 002.007-1.24l.885-1.77a2.25 2.25 0 012.007-1.24h3.86m-18 0h18m-18 0v-7.5A2.25 2.25 0 013.75 3h16.5a2.25 2.25 0 012.25 2.25v7.5m-18 0v-7.5" />
                                    </svg>
                                    <h3>No drawing loaded</h3>
                                    <p>Upload a hand-drawn floor plan sketch in the sidebar, adjust detection thresholds, and run the neural/OpenCV line parser.</p>
                                </div>
                            ) : (
                                <div className="canvas-container">
                                    <img 
                                        src={processedImgUrl || originalImgUrl} 
                                        className="preview-image" 
                                        alt="Sketch layout" 
                                    />
                                    {isLoading && (
                                        <div className="loading-overlay">
                                            <div className="spinner" />
                                            <div className="loading-text">PIXEL CORNER DETECTOR ACTIVE...</div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                    
                    {/* Tab 2: 2D Editor View */}
                    <div className={`tab-content ${activeTab === 'cad2d' ? 'active' : ''}`}>
                        <div className="canvas-viewport cad-canvas-bg">
                            {/* CAD Toolbar */}
                            <div className="canvas-toolbar">
                                <button className={`tool-btn ${activeTool === 'select' ? 'active' : ''}`} title="Select & Drag Nodes" onClick={() => setActiveTool('select')}>
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                                    </svg>
                                </button>
                                <button className={`tool-btn ${activeTool === 'wall' ? 'active' : ''}`} title="Draw Structural Wall" onClick={() => setActiveTool('wall')}>
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                                    </svg>
                                </button>
                                <button className={`tool-btn ${activeTool === 'door' ? 'active' : ''}`} title="Draw Door Insert" onClick={() => setActiveTool('door')}>
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                </button>
                                <button className={`tool-btn ${activeTool === 'window' ? 'active' : ''}`} title="Draw Window Segment" onClick={() => setActiveTool('window')}>
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </button>
                                <button className={`tool-btn ${activeTool === 'delete' ? 'active' : ''}`} title="Delete Entity" onClick={() => setActiveTool('delete')}>
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            </div>
                            
                            {/* Legend Panel */}
                            <div className="canvas-legend">
                                <div className="legend-item"><span className="legend-color wall" /><span>Wall Line</span></div>
                                <div className="legend-item"><span className="legend-color door" /><span>Door Leaf</span></div>
                                <div className="legend-item"><span className="legend-color window" /><span>Window Glass</span></div>
                                <div className="legend-item"><span className="legend-color dim" /><span>Dimension Tag</span></div>
                            </div>
                            
                            <div className="canvas-container" style={{ position: 'relative' }}>
                                {/* Underlying original sketch image for reference verification */}
                                <img 
                                    src={originalImgUrl} 
                                    style={{ opacity: 0.15, pointerEvents: 'none', display: 'block', maxWidth: '100%', maxHeight: '70vh' }} 
                                />
                                
                                {/* Dimension Editing Text Popup */}
                                {editingDim && (
                                    <div 
                                        className="dim-editor-popup" 
                                        style={{ 
                                            left: `${(editingDim.x / imgDimensions.width) * 100}%`, 
                                            top: `${(editingDim.y / imgDimensions.height) * 100}%`,
                                            transform: 'translate(-50%, -100%)' 
                                        }}
                                        onClick={e => e.stopPropagation()}
                                    >
                                        <input 
                                            type="text" 
                                            className="dim-input" 
                                            value={dimOverrideText} 
                                            onChange={e => setDimOverrideText(e.target.value)}
                                            onKeyDown={e => { if (e.key === 'Enter') saveDimOverride(); }}
                                            autoFocus
                                        />
                                        <button className="dim-btn-ok" onClick={saveDimOverride}>OK</button>
                                    </div>
                                )}
                                
                                {/* SVG Interactive Layer */}
                                <svg 
                                    className={`cad-canvas ${activeTool}-tool`}
                                    viewBox={`0 0 ${imgDimensions.width} ${imgDimensions.height}`}
                                    style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
                                    onMouseDown={handleCanvasMouseDown}
                                    onMouseMove={handleCanvasMouseMove}
                                    onMouseUp={handleCanvasMouseUp}
                                >
                                    {/* Draw grid alignments if snapped */}
                                    {gridSnap && (
                                        <defs>
                                            <pattern id="grid" width={gridSize} height={gridSize} patternUnits="userSpaceOnUse">
                                                <circle cx={gridSize} cy={gridSize} r="0.5" fill="#ffffff" opacity="0.15" />
                                            </pattern>
                                        </defs>
                                    )}
                                    {gridSnap && <rect width="100%" height="100%" fill="url(#grid)" pointerEvents="none" />}

                                    {/* Plan Lines rendering */}
                                    {lines.map((line) => {
                                        let strokeColor = 'white';
                                        let strokeWidth = '3';
                                        
                                        if (line.type === 'window') {
                                            strokeColor = 'var(--color-primary)';
                                            strokeWidth = '2';
                                        } else if (line.type === 'door') {
                                            strokeColor = 'var(--color-warning)';
                                            strokeWidth = '2.5';
                                        }
                                        
                                        return (
                                            <g key={`line-${line.id}`}>
                                                {/* Hidden thicker line for easy clicking/interaction */}
                                                <line 
                                                    x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2}
                                                    stroke="transparent" strokeWidth="15" cursor="pointer"
                                                    onClick={(e) => handleElementClick(e, line, false)}
                                                />
                                                {/* The visible CAD vector line */}
                                                <line 
                                                    x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2}
                                                    stroke={strokeColor} strokeWidth={strokeWidth}
                                                    strokeLinecap="round" pointerEvents="none"
                                                />
                                                {/* Render line handles in select tool */}
                                                {activeTool === 'select' && (
                                                    <React.Fragment>
                                                        <circle cx={line.x1} cy={line.y1} r="5" fill="#10b981" stroke="white" strokeWidth="1" cursor="move" />
                                                        <circle cx={line.x2} cy={line.y2} r="5" fill="#10b981" stroke="white" strokeWidth="1" cursor="move" />
                                                    </React.Fragment>
                                                )}
                                            </g>
                                        );
                                    })}
                                    
                                    {/* Draw temp line segment currently in progress */}
                                    {drawTempLine && (
                                        <line 
                                            x1={drawTempLine.x1} y1={drawTempLine.y1} x2={drawTempLine.x2} y2={drawTempLine.y2}
                                            stroke="var(--color-primary)" strokeWidth="2.5" strokeDasharray="5,5" pointerEvents="none"
                                        />
                                    )}
                                    
                                    {/* Plan Dimensions labels rendering */}
                                    {dimensions.map((dim) => (
                                        <g key={`dim-${dim.id}`} onClick={(e) => handleElementClick(e, dim, true)} onDoubleClick={() => handleDimDoubleClick(dim)}>
                                            <circle cx={dim.x} cy={dim.y} r="8" fill="rgba(16, 185, 129, 0.2)" stroke="var(--color-success)" strokeWidth="1" cursor="pointer" />
                                            
                                            {/* Text tag */}
                                            <rect x={dim.x - 20} y={dim.y - 18} width="40" height="12" rx="2" fill="#0f172a" stroke="rgba(255,255,255,0.1)" strokeWidth="0.5" pointerEvents="none" />
                                            <text 
                                                x={dim.x} y={dim.y - 10} 
                                                fill="var(--color-success)" fontSize="8" fontFamily="var(--font-mono)" 
                                                textAnchor="middle" fontWeight="bold" pointerEvents="none"
                                            >
                                                {dim.value}
                                            </text>
                                        </g>
                                    ))}
                                </svg>
                            </div>
                        </div>
                    </div>
                    
                    {/* Tab 3: 3D View */}
                    <div className={`tab-content ${activeTab === 'cad3d' ? 'active' : ''}`}>
                        {activeTab === 'cad3d' && (
                            <ThreeViewer 
                                lines={lines} 
                                imgWidth={imgDimensions.width} 
                                imgHeight={imgDimensions.height} 
                                scale={drawingScale} 
                            />
                        )}
                    </div>
                    
                    {/* Bottom Console Logger */}
                    <div className="console-panel">
                        {logs.map((log, idx) => (
                            <div key={idx} className={`console-line ${log.type}`}>
                                <span className="console-timestamp">[{log.time}]</span>
                                <span>{log.msg}</span>
                            </div>
                        ))}
                    </div>
                </main>
            </div>
        </React.Fragment>
    );
}

// Render root React component
const container = document.getElementById('root');
const root = ReactDOM.createRoot(container);
root.render(<App />);
