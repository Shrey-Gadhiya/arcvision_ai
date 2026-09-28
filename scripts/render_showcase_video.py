import os
import math
import wave
import struct
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SEC = 42
TOTAL_FRAMES = FPS * DURATION_SEC

# Paths
OUT_VIDEO_PATH = "c:/Users/zoro/Desktop/byrehasira-arcvision-main/arc_vision_showcase.mp4"
TEMP_RAW_VIDEO = "c:/Users/zoro/Desktop/byrehasira-arcvision-main/temp_raw.mp4"
TEMP_AUDIO = "c:/Users/zoro/Desktop/byrehasira-arcvision-main/temp_audio.wav"
ARTIFACT_DIR = "C:/Users/zoro/.gemini/antigravity-ide/brain/0f05849c-b4ed-4ead-9aa7-b3838f9fbd66"

# Fonts
FONT_TITLE = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 46)
FONT_HEADING = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
FONT_SUB = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
FONT_MONO = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 20)
FONT_MONO_SM = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 15)
FONT_BIG_STAT = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 52)
FONT_PLATE = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 64)

# Color Palette
C_BG = (5, 8, 14)
C_CYAN = (56, 189, 248)
C_AMBER = (245, 158, 11)
C_RED = (239, 68, 68)
C_GREEN = (16, 185, 129)
C_WHITE = (241, 245, 249)
C_DIM = (148, 163, 184)
C_PANEL = (11, 18, 30)
C_BORDER = (14, 165, 233)

def draw_topbar(draw, frame_idx):
    # Top HUD Bar
    draw.rectangle([0, 0, WIDTH, 64], fill=(8, 14, 24))
    draw.line([0, 64, WIDTH, 64], fill=(20, 45, 75), width=2)
    
    # Hexagon Badge
    draw.polygon([(40, 16), (56, 24), (56, 44), (40, 52), (24, 44), (24, 24)], fill=(14, 165, 233))
    draw.text((68, 20), "ARC VISION", font=FONT_HEADING, fill=(255, 255, 255))
    
    # SSB Badge
    draw.rounded_rectangle([270, 22, 530, 46], radius=4, fill=(35, 25, 10), outline=C_AMBER, width=1)
    draw.text((280, 24), "SIH26187 // SASHASTRA SEEMA BAL", font=FONT_MONO_SM, fill=C_AMBER)
    
    # Telemetry
    draw.text((600, 16), "SECTOR: SSB-NORTH-07", font=FONT_MONO_SM, fill=C_DIM)
    draw.text((600, 36), "LAT: 27°18'42\"N  LON: 88°53'14\"E", font=FONT_MONO_SM, fill=C_CYAN)
    
    draw.text((950, 16), "AI INFERENCE ENGINE", font=FONT_MONO_SM, fill=C_DIM)
    draw.text((950, 36), "OPENVINO INT8 // 30 FPS", font=FONT_MONO_SM, fill=C_GREEN)
    
    draw.text((1240, 16), "ENCRYPTION HASH LOCK", font=FONT_MONO_SM, fill=C_DIM)
    draw.text((1240, 36), "SHA-256 BITSTREAM SEAL", font=FONT_MONO_SM, fill=C_CYAN)
    
    # DEFCON Status
    time_sec = frame_idx / FPS
    if 14 <= time_sec < 22:
        # RED ALERT
        pulse = int(abs(math.sin(frame_idx * 0.2)) * 60)
        draw.rounded_rectangle([1600, 16, 1880, 48], radius=6, fill=(180 + pulse, 20, 20), outline=C_RED, width=2)
        draw.text((1618, 22), "DEFCON 1 : CRITICAL BREACH", font=FONT_MONO_SM, fill=(255, 255, 255))
    elif 22 <= time_sec < 29:
        draw.rounded_rectangle([1600, 16, 1880, 48], radius=6, fill=(140, 90, 10), outline=C_AMBER, width=2)
        draw.text((1624, 22), "DEFCON 2 : WATCHLIST HIT", font=FONT_MONO_SM, fill=(255, 255, 255))
    else:
        draw.rounded_rectangle([1600, 16, 1880, 48], radius=6, fill=(10, 40, 25), outline=C_GREEN, width=1)
        draw.text((1640, 22), "DEFCON 4 : NORMAL", font=FONT_MONO_SM, fill=C_GREEN)

def draw_footer(draw, frame_idx, current_stage_name, stage_idx):
    # Bottom Bar
    draw.rectangle([0, HEIGHT - 54, WIDTH, HEIGHT], fill=(8, 14, 24))
    draw.line([0, HEIGHT - 54, WIDTH, HEIGHT - 54], fill=(20, 45, 75), width=2)
    
    # Progress line
    prog_w = int((frame_idx / TOTAL_FRAMES) * WIDTH)
    draw.line([0, HEIGHT - 54, prog_w, HEIGHT - 54], fill=C_CYAN, width=4)
    
    stages = [
        "01 OVERVIEW",
        "02 ARCHITECTURE",
        "03 PERIMETER BREACH",
        "04 CHECKPOINT ANPR",
        "05 FRIGATE NVR",
        "06 SUMMARY"
    ]
    
    x = 40
    for i, st in enumerate(stages):
        is_active = (i == stage_idx)
        bg_col = (14, 165, 233) if is_active else (20, 30, 45)
        txt_col = (0, 0, 0) if is_active else C_DIM
        draw.rounded_rectangle([x, HEIGHT - 42, x + 180, HEIGHT - 14], radius=4, fill=bg_col)
        draw.text((x + 16, HEIGHT - 36), st, font=FONT_MONO_SM, fill=txt_col)
        x += 200
        
    draw.text((WIDTH - 360, HEIGHT - 36), f"STATUS: {current_stage_name}", font=FONT_MONO_SM, fill=C_CYAN)

def render_scene_1(img, draw, frame_idx, sec):
    # Scene 1: Tactical Overview (0 - 7s)
    # Background grid
    for x in range(0, WIDTH, 48):
        draw.line([x, 64, x, HEIGHT - 54], fill=(10, 18, 30), width=1)
    for y in range(64, HEIGHT - 54, 48):
        draw.line([0, y, WIDTH, y], fill=(10, 18, 30), width=1)
        
    # Left Hero Text
    draw.text((120, 170), "AUTONOMOUS BORDER INTELLIGENCE SYSTEM", font=FONT_MONO, fill=C_CYAN)
    draw.text((120, 210), "ARC VISION", font=ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 68), fill=C_WHITE)
    draw.text((120, 290), "AI-Powered Tactical Surveillance Grid for Remote Perimeters", font=FONT_HEADING, fill=(186, 230, 253))
    
    desc_lines = [
        "Transforming legacy CCTV & RTSP cameras into an autonomous border security matrix.",
        "Featuring real-time multi-target tracking, polygon tripwire enforcement, ANPR recognition,",
        "and court-admissible forensic evidence with tamper-evident SHA-256 cryptographic proof."
    ]
    y_pos = 360
    for line in desc_lines:
        draw.text((120, y_pos), line, font=FONT_SUB, fill=C_DIM)
        y_pos += 34
        
    # Metric cards
    metrics = [
        ("18", "Mission Consoles"),
        ("<18ms", "Inference Latency"),
        ("100%", "Air-Gapped Offline"),
        ("SHA-256", "Chain of Custody")
    ]
    card_x = 120
    for val, lbl in metrics:
        draw.rounded_rectangle([card_x, 520, card_x + 220, 640], radius=8, fill=C_PANEL, outline=(25, 55, 90), width=2)
        draw.text((card_x + 24, 536), val, font=FONT_BIG_STAT, fill=C_CYAN)
        draw.text((card_x + 24, 600), lbl, font=FONT_MONO_SM, fill=C_DIM)
        card_x += 240

    # Right Side: Tactical Radar
    cx, cy, radius = 1520, 480, 260
    # Radar rings
    for r in [60, 120, 180, 240]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(20, 70, 110), width=1)
    draw.line([cx - radius, cy, cx + radius, cy], fill=(20, 70, 110), width=1)
    draw.line([cx, cy - radius, cx, cy + radius], fill=(20, 70, 110), width=1)
    
    # Radar sweep line
    angle = (frame_idx * 0.08) % (2 * math.pi)
    sx = cx + int(math.cos(angle) * radius)
    sy = cy + int(math.sin(angle) * radius)
    draw.line([cx, cy, sx, sy], fill=C_CYAN, width=3)
    
    # Blips
    blips = [
        (cx + 80, cy - 60, C_GREEN, "CAM-01 [ACTIVE]"),
        (cx - 120, cy + 90, C_GREEN, "CAM-02 [ACTIVE]"),
        (cx + 140, cy + 110, C_GREEN, "CAM-03 [ACTIVE]"),
        (cx - 70, cy - 130, C_RED, "TARGET #1042 [BREACH]")
    ]
    for bx, by, col, name in blips:
        draw.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=col)
        draw.ellipse([bx - 12, by - 12, bx + 12, by + 12], outline=col, width=1)
        draw.text((bx + 14, by - 8), name, font=FONT_MONO_SM, fill=col)

def render_scene_2(img, draw, frame_idx, sec):
    # Scene 2: Tri-Tier Architecture (7 - 14s)
    draw.text((120, 100), "TACTICAL CORE ARCHITECTURE", font=FONT_MONO, fill=C_CYAN)
    draw.text((120, 130), "THE TRI-TIER THREAT CORRELATION PIPELINE", font=FONT_TITLE, fill=C_WHITE)
    
    # Theorem Banner
    draw.rounded_rectangle([120, 200, 1800, 280], radius=8, fill=(15, 25, 45), outline=C_CYAN, width=2)
    draw.text((160, 226), "DETECTION (Raw Telemetry)   ≠   EVENT (Rule Trigger)   ≠   INCIDENT (Correlated Threat Dossier)", font=FONT_HEADING, fill=C_WHITE)
    
    # 6 Pipeline Nodes
    nodes = [
        ("01 INGEST", "RTSP / IP Decode", "Decoupled Detect & Record streams with NVDEC/OpenVINO.", "640x360 @ 30fps"),
        ("02 FILTER", "MOG2 Motion Gate", "Background subtraction skips static frames, saving 72% compute.", "Delta > 1.8% Area"),
        ("03 INFERENCE", "YOLOv8 + ByteTrack", "Real-time bounding boxes & Kalman trajectory persistence.", "Person, Car, Truck"),
        ("04 RULES", "Polygon Tripwires", "Directional virtual fences (A -> B) & loitering dwell timers.", "Cross-Product Calc"),
        ("05 CORRELATE", "Incident Engine", "Spatial-temporal correlation yields threat score (0-100).", "Defcon Elevation"),
        ("06 EVIDENCE", "SHA-256 Ledger", "Rolling 10s MP4 segments sealed with cryptographic hashes.", "Immutable Custody")
    ]
    
    active_node = int(((sec - 7) / 7.0) * 6) % 6
    x = 120
    for i, (tag, title, desc, code) in enumerate(nodes):
        is_highlight = (i == active_node)
        border_col = C_CYAN if is_highlight else (25, 55, 85)
        fill_col = (18, 35, 60) if is_highlight else C_PANEL
        
        draw.rounded_rectangle([x, 340, x + 260, 720], radius=8, fill=fill_col, outline=border_col, width=2 if is_highlight else 1)
        
        # Tag
        draw.rounded_rectangle([x + 16, 356, x + 150, 384], radius=4, fill=(10, 20, 35))
        draw.text((x + 24, 360), tag, font=FONT_MONO_SM, fill=C_CYAN)
        
        # Title
        draw.text((x + 16, 400), title, font=FONT_HEADING, fill=C_WHITE)
        
        # Desc
        words = desc.split(" ")
        line1 = " ".join(words[:4])
        line2 = " ".join(words[4:])
        draw.text((x + 16, 460), line1, font=FONT_SUB, fill=C_DIM)
        draw.text((x + 16, 490), line2, font=FONT_SUB, fill=C_DIM)
        
        # Code box
        draw.rounded_rectangle([x + 16, 640, x + 244, 680], radius=4, fill=(5, 10, 18), outline=(20, 45, 75))
        draw.text((x + 24, 650), code, font=FONT_MONO_SM, fill=C_AMBER)
        
        # Connecting arrows
        if i < 5:
            draw.line([x + 260, 530, x + 280, 530], fill=C_CYAN if i <= active_node else (30, 60, 90), width=3)
            draw.polygon([(x + 280, 524), (x + 280, 536), (x + 286, 530)], fill=C_CYAN if i <= active_node else (30, 60, 90))
            
        x += 280

def render_scene_3(img, draw, frame_idx, sec):
    # Scene 3: Live Grid & Perimeter Intrusion (14 - 22s)
    draw.text((120, 100), "DETERMINISTIC MISSION SCENARIO 01", font=FONT_MONO, fill=C_RED)
    draw.text((120, 130), "PERIMETER INTRUSION BREACH (CAM-01)", font=FONT_TITLE, fill=C_WHITE)
    
    # Left Video Frame Canvas
    vx, vy, vw, vh = 120, 200, 1080, 600
    draw.rectangle([vx, vy, vx + vw, vy + vh], fill=(4, 9, 16), outline=C_RED, width=2)
    
    # Video HUD bar
    draw.rectangle([vx, vy, vx + vw, vy + 40], fill=(12, 22, 38))
    draw.text((vx + 16, vy + 10), "CAM-01 // NORTH_PERIMETER_NIGHT_IR  [NVDEC 1080p @ 29.8 FPS]", font=FONT_MONO_SM, fill=C_WHITE)
    draw.text((vx + vw - 220, vy + 10), "THERMAL ENHANCED", font=FONT_MONO_SM, fill=C_CYAN)
    
    # Draw simulated perimeter fence (tripwire)
    fence_x = vx + 450
    for fy in range(vy + 50, vy + vh - 20, 20):
        draw.line([fence_x, fy, fence_x, fy + 12], fill=C_AMBER, width=3)
    draw.text((fence_x - 180, vy + 60), "VIRTUAL FENCE ALPHA (A -> B)", font=FONT_MONO_SM, fill=C_AMBER)
    
    # Restricted zone polygon
    zone_pts = [(fence_x + 50, vy + 80), (vx + vw - 40, vy + 120), (vx + vw - 40, vy + vh - 60), (fence_x + 50, vy + vh - 40)]
    draw.polygon(zone_pts, fill=(45, 10, 15), outline=C_RED)
    draw.text((fence_x + 80, vy + 100), "RESTRICTED ZONE SECTOR 4 [NO TRESPASS]", font=FONT_MONO, fill=C_RED)
    
    # Moving Intruder Target
    prog = ((sec - 14) / 8.0)
    tx = int(vx + 340 + prog * 280)
    ty = int(vy + 320 + math.sin(frame_idx * 0.1) * 30)
    
    is_breached = (tx > fence_x)
    box_col = C_RED if is_breached else C_CYAN
    draw.rectangle([tx - 30, ty - 70, tx + 30, ty + 70], outline=box_col, width=3)
    # Target label
    status_str = "CRITICAL: PERSON #1042 (0.95)" if is_breached else "PERSON #1042 (0.91)"
    draw.rectangle([tx - 30, ty - 96, tx + 240, ty - 70], fill=(0, 0, 0))
    draw.text((tx - 24, ty - 92), status_str, font=FONT_MONO_SM, fill=box_col)
    
    # Right Side Alert Dossier
    ax, ay, aw = 1240, 200, 560
    draw.rounded_rectangle([ax, ay, ax + aw, ay + 600], radius=8, fill=C_PANEL, outline=C_RED, width=2)
    
    draw.rectangle([ax, ay, ax + aw, ay + 60], fill=(60, 15, 20))
    draw.text((ax + 24, ay + 16), "CRITICAL INCIDENT DOSSIER #INC-8891", font=FONT_HEADING, fill=C_WHITE)
    
    fields = [
        ("SEVERITY", "CRITICAL (THREAT SCORE: 98/100)", C_RED),
        ("LOCATION", "Sector 4 Northern Buffer, Zone 4B", C_WHITE),
        ("RULE TRIGGER", "Crossed Virtual Fence Alpha (A -> B)", C_AMBER),
        ("DWELL TIME", "14.2 Seconds in Restricted Polygon", C_WHITE),
        ("AUTO ACTION", "Northern Outpost Siren & Patrol Dispatched", C_GREEN),
        ("EVIDENCE FILE", "segment_cam01_20260928_105520.mp4", C_CYAN),
        ("SHA-256 HASH", "a7f89c02d13b48e6f0e9c87d4a21e428f7c9...", C_AMBER)
    ]
    
    fy = ay + 90
    for lbl, val, col in fields:
        draw.text((ax + 24, fy), lbl, font=FONT_MONO_SM, fill=C_DIM)
        draw.text((ax + 24, fy + 22), val, font=FONT_MONO if "HASH" in lbl else FONT_SUB, fill=col)
        fy += 68

def render_scene_4(img, draw, frame_idx, sec):
    # Scene 4: Checkpoint ANPR (22 - 29s)
    draw.text((120, 100), "DETERMINISTIC MISSION SCENARIO 02", font=FONT_MONO, fill=C_AMBER)
    draw.text((120, 130), "CHECKPOINT ANPR & WATCHLIST MATCH (CAM-02)", font=FONT_TITLE, fill=C_WHITE)
    
    # Left ANPR Panel
    lx, ly, lw, lh = 120, 200, 960, 600
    draw.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=8, fill=C_PANEL, outline=C_AMBER, width=2)
    
    draw.text((lx + 32, ly + 28), "VEHICLE NUMBER PLATE LOCALIZATION & OCR", font=FONT_HEADING, fill=C_WHITE)
    draw.text((lx + 32, ly + 68), "Multi-layer Indian Standard License Plate Format Validator", font=FONT_SUB, fill=C_DIM)
    
    # Simulated High-Res Indian Number Plate
    px, py, pw, ph = lx + 80, ly + 140, 780, 180
    draw.rounded_rectangle([px, py, px + pw, py + ph], radius=12, fill=(254, 240, 138), outline=(0, 0, 0), width=6)
    
    # IND blue strip
    draw.rectangle([px + 8, py + 8, px + 80, py + ph - 8], fill=(3, 105, 161))
    draw.text((px + 18, py + 70), "IND", font=FONT_HEADING, fill=(255, 255, 255))
    
    # Plate Text
    draw.text((px + 140, py + 48), "DL 01 AB 1234", font=FONT_PLATE, fill=(0, 0, 0))
    
    # Watchlist Match Alert Box
    draw.rounded_rectangle([lx + 40, ly + 360, lx + lw - 40, ly + 460], radius=8, fill=(80, 20, 25), outline=C_RED, width=2)
    draw.text((lx + 64, ly + 380), "ALERT: SUSPECT BORDER WATCHLIST MATCH DETECTED", font=FONT_HEADING, fill=C_RED)
    draw.text((lx + 64, ly + 420), "Tag: SMUGGLING INTERDICTION // Plate Flagged by SSB Headquarters", font=FONT_SUB, fill=C_WHITE)
    
    # Metrics
    metrics = [
        ("OCR CONFIDENCE", "98.7% (CRNN)", C_GREEN),
        ("REGEX FORMAT", "PASS [DL-01-AB-1234]", C_CYAN),
        ("MATCH LATENCY", "42 ms", C_AMBER)
    ]
    mx = lx + 40
    for lbl, val, col in metrics:
        draw.rounded_rectangle([mx, ly + 490, mx + 270, ly + 560], radius=6, fill=(15, 25, 40))
        draw.text((mx + 16, ly + 500), lbl, font=FONT_MONO_SM, fill=C_DIM)
        draw.text((mx + 16, ly + 524), val, font=FONT_MONO, fill=col)
        mx += 295
        
    # Right Side: Face Intelligence & Interlock
    rx, ry, rw = 1120, 200, 680
    draw.rounded_rectangle([rx, ry, rx + rw, ry + 600], radius=8, fill=C_PANEL, outline=(25, 55, 85), width=2)
    
    draw.text((rx + 32, ry + 28), "FACE & RE-ID CORRELATION", font=FONT_HEADING, fill=C_WHITE)
    
    draw.rounded_rectangle([rx + 32, ry + 90, rx + 160, ry + 220], radius=8, fill=(20, 30, 48), outline=C_CYAN, width=2)
    draw.text((rx + 54, ry + 140), "TARGET\nPHOTO", font=FONT_MONO_SM, fill=C_CYAN)
    
    draw.text((rx + 190, ry + 100), "MATCH: SUBJECT #882 (Cosine Sim: 0.89)", font=FONT_HEADING, fill=C_RED)
    draw.text((rx + 190, ry + 145), "Watchlist: INTERPOL Red Notice Cross-Ref", font=FONT_SUB, fill=C_WHITE)
    draw.text((rx + 190, ry + 180), "Cross-Camera Trajectory: CAM-02 -> CAM-04", font=FONT_SUB, fill=C_AMBER)
    
    # Automated Action
    draw.rounded_rectangle([rx + 32, ry + 260, rx + rw - 32, ry + 560], radius=8, fill=(15, 30, 50), outline=C_GREEN, width=1)
    draw.text((rx + 56, ry + 290), "AUTOMATED COMMAND RELAY ENGAGED", font=FONT_HEADING, fill=C_GREEN)
    draw.text((rx + 56, ry + 340), "● Barrier Boom Lock Activated (Local GPIO Relay)", font=FONT_SUB, fill=C_WHITE)
    draw.text((rx + 56, ry + 380), "● Checkpoint Tactical Audio Klaxon Triggered", font=FONT_SUB, fill=C_WHITE)
    draw.text((rx + 56, ry + 420), "● High-Resolution Evidence Dossier Auto-Archived", font=FONT_SUB, fill=C_WHITE)
    draw.text((rx + 56, ry + 480), "Tamper Seal: SHA-256 e81b24d7809a...", font=FONT_MONO, fill=C_CYAN)

def render_scene_5(img, draw, frame_idx, sec):
    # Scene 5: Frigate NVR Scrubber (29 - 36s)
    draw.text((120, 100), "STORAGE & FORENSIC SUITE", font=FONT_MONO, fill=C_CYAN)
    draw.text((120, 130), "FRIGATE-CLASS MULTI-TIER NVR SCRUBBER", font=FONT_TITLE, fill=C_WHITE)
    
    # Scrubber Box
    sx, sy, sw, sh = 120, 200, 1680, 240
    draw.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=8, fill=C_PANEL, outline=(25, 55, 90), width=2)
    
    draw.text((sx + 32, sy + 24), "24-HOUR MULTI-TIER CONTINUOUS & INCIDENT SCRUBBER", font=FONT_HEADING, fill=C_WHITE)
    
    # Legend
    draw.ellipse([sx + 1050, sy + 32, sx + 1062, sy + 44], fill=C_CYAN)
    draw.text((sx + 1070, sy + 28), "Continuous (Blue)", font=FONT_MONO_SM, fill=C_WHITE)
    
    draw.ellipse([sx + 1280, sy + 32, sx + 1292, sy + 44], fill=C_AMBER)
    draw.text((sx + 1300, sy + 28), "Motion Activity (Yellow)", font=FONT_MONO_SM, fill=C_WHITE)
    
    draw.ellipse([sx + 1520, sy + 32, sx + 1532, sy + 44], fill=C_RED)
    draw.text((sx + 1540, sy + 28), "Incident (Red)", font=FONT_MONO_SM, fill=C_WHITE)
    
    # Scrubber Track
    tx, ty, tw, th = sx + 32, sy + 76, sw - 64, 70
    draw.rectangle([tx, ty, tx + tw, ty + th], fill=(15, 23, 42))
    draw.rectangle([tx, ty + 10, tx + tw, ty + th - 10], fill=(20, 50, 80)) # continuous blue
    
    # Motion ticks (yellow)
    motion_pos = [0.12, 0.18, 0.29, 0.44, 0.52, 0.74, 0.88]
    for p in motion_pos:
        mx = tx + int(p * tw)
        draw.rectangle([mx, ty, mx + 8, ty + th], fill=C_AMBER)
        
    # Incident ticks (red)
    draw.rectangle([tx + int(0.64 * tw), ty, tx + int(0.64 * tw) + 18, ty + th], fill=C_RED)
    
    # Moving Playhead
    playhead_prog = (0.55 + ((sec - 29) / 7.0) * 0.18) % 1.0
    px = tx + int(playhead_prog * tw)
    draw.line([px, ty - 10, px, ty + th + 10], fill=C_WHITE, width=4)
    draw.polygon([(px - 8, ty - 14), (px + 8, ty - 14), (px, ty - 4)], fill=C_WHITE)
    
    # Time markers
    draw.text((tx, ty + th + 14), "00:00:00", font=FONT_MONO_SM, fill=C_DIM)
    draw.text((tx + tw // 4, ty + th + 14), "06:00:00", font=FONT_MONO_SM, fill=C_DIM)
    draw.text((tx + tw // 2, ty + th + 14), "12:00:00", font=FONT_MONO_SM, fill=C_DIM)
    draw.text((px - 70, ty + th + 14), "15:42:19 (PLAYHEAD)", font=FONT_MONO_SM, fill=C_CYAN)
    draw.text((tx + tw - 80, ty + th + 14), "23:59:59", font=FONT_MONO_SM, fill=C_DIM)
    
    # 3 Architecture Cards Below
    cards = [
        ("Best-Frame Selection Engine", "Evaluates detection confidence, bounding box area, and Laplacian edge sharpness to save pristine clean & annotated thumbnails."),
        ("Decoupled Stream Roles", "Low-resolution 640x360 detect stream feeds GPU/CPU inference, while full-resolution archival stream records lossless 10-second segments."),
        ("Tamper-Evident SHA-256 Ledger", "Every recorded segment and exported incident clip is sealed with SHA-256 bitstream checksums, guaranteeing legal chain of custody.")
    ]
    cx = 120
    for title, desc in cards:
        draw.rounded_rectangle([cx, 480, cx + 530, 740], radius=8, fill=C_PANEL, outline=(25, 55, 90), width=1)
        draw.text((cx + 24, 508), title, font=FONT_HEADING, fill=C_CYAN)
        
        # Word wrap
        words = desc.split(" ")
        lines = []
        cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 42:
                lines.append(" ".join(cur))
                cur = []
        if cur: lines.append(" ".join(cur))
        
        ly = 570
        for l in lines:
            draw.text((cx + 24, ly), l, font=FONT_SUB, fill=C_DIM)
            ly += 32
        cx += 575

def render_scene_6(img, draw, frame_idx, sec):
    # Scene 6: Summary & Mission Complete (36 - 42s)
    draw.rounded_rectangle([WIDTH // 2 - 250, 140, WIDTH // 2 + 250, 184], radius=20, fill=(10, 40, 25), outline=C_GREEN, width=2)
    draw.text((WIDTH // 2 - 200, 150), "MISSION ACCOMPLISHED // SIH26187", font=FONT_MONO, fill=C_GREEN)
    
    draw.text((WIDTH // 2 - 580, 220), "ARC VISION: SECURING BORDER PERIMETERS", font=ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 54), fill=C_WHITE)
    draw.text((WIDTH // 2 - 460, 290), "Autonomous AI Surveillance Grid Built for Ministry of Home Affairs & SSB", font=FONT_HEADING, fill=C_CYAN)
    
    # 4 Highlights
    highlights = [
        ("18", "Tactical Mission Consoles", "Complete tactical SOC with RBAC tiers (Admin, Commander, Operator, Auditor)."),
        ("0 Cloud", "100% Air-Gapped", "Fully functional without external internet dependency, built for remote border outposts."),
        ("<18ms", "Edge OpenVINO Latency", "Decoupled MOG2 motion gating saves 72% compute, yielding high FPS on standard hardware."),
        ("SHA-256", "Forensic Cryptography", "Every segment and evidence crop is cryptographically hashed for chain of custody.")
    ]
    
    hx = 120
    for big, title, sub in highlights:
        draw.rounded_rectangle([hx, 380, hx + 390, 640], radius=8, fill=C_PANEL, outline=C_CYAN, width=2)
        draw.text((hx + 24, 404), big, font=FONT_BIG_STAT, fill=C_CYAN)
        draw.text((hx + 24, 480), title, font=FONT_HEADING, fill=C_WHITE)
        
        words = sub.split(" ")
        l1 = " ".join(words[:5])
        l2 = " ".join(words[5:])
        draw.text((hx + 24, 536), l1, font=FONT_SUB, fill=C_DIM)
        draw.text((hx + 24, 568), l2, font=FONT_SUB, fill=C_DIM)
        hx += 430
        
    draw.rounded_rectangle([320, 690, 1600, 750], radius=8, fill=(35, 25, 10), outline=C_AMBER, width=2)
    draw.text((360, 706), "PRODUCTION-READY BORDER DEPLOYMENT // PROUDLY ENGINEERED FOR SIH26187", font=FONT_MONO, fill=C_AMBER)

def generate_video_frames():
    print(f"Generating {TOTAL_FRAMES} frames...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(TEMP_RAW_VIDEO, fourcc, FPS, (WIDTH, HEIGHT))
    
    for i in range(TOTAL_FRAMES):
        sec = i / FPS
        # Create base image
        img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
        draw = ImageDraw.Draw(img)
        
        # Render Topbar
        draw_topbar(draw, i)
        
        # Determine Stage
        if sec < 7:
            stage_idx = 0
            stage_name = "OVERVIEW"
            render_scene_1(img, draw, i, sec)
        elif sec < 14:
            stage_idx = 1
            stage_name = "ARCHITECTURE PIPELINE"
            render_scene_2(img, draw, i, sec)
        elif sec < 22:
            stage_idx = 2
            stage_name = "PERIMETER INTRUSION (CAM-01)"
            render_scene_3(img, draw, i, sec)
        elif sec < 29:
            stage_idx = 3
            stage_name = "CHECKPOINT ANPR (CAM-02)"
            render_scene_4(img, draw, i, sec)
        elif sec < 36:
            stage_idx = 4
            stage_name = "FRIGATE NVR SCRUBBER"
            render_scene_5(img, draw, i, sec)
        else:
            stage_idx = 5
            stage_name = "SUMMARY & CALL TO ACTION"
            render_scene_6(img, draw, i, sec)
            
        # Render Footer
        draw_footer(draw, i, stage_name, stage_idx)
        
        # Convert PIL image to OpenCV BGR
        cv_frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        out.write(cv_frame)
        
        if i % 150 == 0:
            print(f"Rendered {i}/{TOTAL_FRAMES} frames ({(i/TOTAL_FRAMES)*100:.1f}%)")
            
    out.release()
    print("Raw video render complete.")

def synthesize_audio():
    print("Synthesizing audio soundtrack...")
    sample_rate = 44100
    total_samples = int(sample_rate * DURATION_SEC)
    t = np.linspace(0, DURATION_SEC, total_samples, False)
    
    # 1. Base cinematic sub-bass drone (55Hz + 110Hz with slow modulation)
    sub_drone = 0.22 * np.sin(2 * np.pi * 55 * t) + 0.12 * np.sin(2 * np.pi * 110 * t)
    sub_drone *= (0.8 + 0.2 * np.sin(2 * np.pi * 0.25 * t))
    
    # 2. Scene transitions whoosh / riser
    transition_times = [0.0, 7.0, 14.0, 22.0, 29.0, 36.0]
    fx_track = np.zeros(total_samples)
    
    for tt in transition_times:
        idx_start = int(tt * sample_rate)
        dur_samples = int(0.6 * sample_rate)
        if idx_start + dur_samples < total_samples:
            dt = np.linspace(0, 0.6, dur_samples, False)
            sweep = 0.25 * np.sin(2 * np.pi * (300 + 800 * dt) * dt) * np.exp(-dt * 4)
            fx_track[idx_start:idx_start+dur_samples] += sweep
            
    # 3. Radar pings during Scene 1 (0 to 7s)
    for ping_t in [1.5, 3.2, 5.0]:
        pidx = int(ping_t * sample_rate)
        pdur = int(0.25 * sample_rate)
        dt = np.linspace(0, 0.25, pdur, False)
        fx_track[pidx:pidx+pdur] += 0.28 * np.sin(2 * np.pi * 880 * dt) * np.exp(-dt * 15)
        
    # 4. Siren alert during Scene 3 (14 to 22s)
    siren_idx_start = int(14.0 * sample_rate)
    siren_idx_end = int(22.0 * sample_rate)
    st = t[siren_idx_start:siren_idx_end]
    siren_freq = 550 + 250 * np.sin(2 * np.pi * 1.5 * st)
    fx_track[siren_idx_start:siren_idx_end] += 0.2 * np.sin(2 * np.pi * siren_freq * st)
    
    # 5. ANPR double confirmation beep at 23.5s
    for bt in [23.5, 23.75]:
        bidx = int(bt * sample_rate)
        bdur = int(0.12 * sample_rate)
        dt = np.linspace(0, 0.12, bdur, False)
        fx_track[bidx:bidx+bdur] += 0.25 * np.sin(2 * np.pi * 1050 * dt) * np.exp(-dt * 20)
        
    # Combine & normalize
    audio = sub_drone + fx_track
    audio = np.clip(audio, -0.95, 0.95)
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Write to 16-bit stereo WAV
    stereo = np.column_stack((audio_int16, audio_int16))
    with wave.open(TEMP_AUDIO, 'w') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo.tobytes())
    print("Audio synthesis complete.")

def mux_final_mp4():
    print("Muxing video & audio with FFmpeg...")
    # FFmpeg command
    cmd = f'ffmpeg -y -i "{TEMP_RAW_VIDEO}" -i "{TEMP_AUDIO}" -c:v libx264 -preset fast -pix_fmt yuv420p -c:a aac -b:a 192k "{OUT_VIDEO_PATH}"'
    res = os.system(cmd)
    if res == 0:
        print(f"Successfully generated showcase video: {OUT_VIDEO_PATH}")
        # Copy to artifact dir as well
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        artifact_video = os.path.join(ARTIFACT_DIR, "arc_vision_showcase.mp4")
        import shutil
        shutil.copyfile(OUT_VIDEO_PATH, artifact_video)
        print(f"Copied to artifact directory: {artifact_video}")
    else:
        print(f"FFmpeg muxing returned code {res}")
        
    # Cleanup temp files
    if os.path.exists(TEMP_RAW_VIDEO): os.remove(TEMP_RAW_VIDEO)
    if os.path.exists(TEMP_AUDIO): os.remove(TEMP_AUDIO)

if __name__ == "__main__":
    generate_video_frames()
    synthesize_audio()
    mux_final_mp4()
