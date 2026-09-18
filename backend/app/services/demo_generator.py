import cv2
import numpy as np
import math
import time
from pathlib import Path
import logging
from app.core.config import settings

logger = logging.getLogger("arc_vision.demo_generator")

def generate_perimeter_breach_video(output_path: Path, num_frames: int = 300, fps: int = 15):
    """
    Generates a 20-second night border surveillance video (1280x720):
    Features border fence, searchlight sweep, and person moving from brush across the fence into restricted zone.
    """
    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    for f_idx in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 1. Dark night background (gradient sky & rugged terrain)
        for y in range(h):
            ratio = y / h
            # Dark navy sky transitioning to rocky ground
            if y < int(h * 0.45):
                frame[y, :] = (15, 12, 18)
            else:
                ground_shade = int(25 + 30 * ratio)
                frame[y, :] = (ground_shade, ground_shade - 5, ground_shade - 10)

        # 2. Distant mountains and border watchtower
        cv2.fillPoly(frame, [np.array([[0, 320], [250, 200], [500, 320]], np.int32)], (22, 20, 28))
        cv2.fillPoly(frame, [np.array([[450, 320], [800, 180], [1100, 320]], np.int32)], (25, 22, 32))
        
        # Watchtower structure on right side
        cv2.rectangle(frame, (1150, 180), (1220, 400), (45, 45, 55), -1)
        cv2.line(frame, (1150, 180), (1220, 400), (35, 35, 40), 2)
        cv2.line(frame, (1220, 180), (1150, 400), (35, 35, 40), 2)
        cv2.rectangle(frame, (1130, 150), (1240, 180), (60, 60, 70), -1)

        # 3. Barbed-wire Border Fence across mid-screen
        fence_y = int(h * 0.58)
        for post_x in range(40, w, 90):
            cv2.line(frame, (post_x, fence_y - 120), (post_x, fence_y + 40), (70, 70, 75), 4)
            # Strands of razor wire
            for strand_offset in [-100, -70, -40, -10, 20]:
                sy = fence_y + strand_offset
                cv2.line(frame, (0, sy), (w, sy), (60, 60, 65), 1)

        # 4. Animated moving person / intruder
        # Trajectory:
        # Frame 0-90: Approaches fence from deep background (walking left to right)
        # Frame 90-180: Pacing near fence (hesitating/surveying)
        # Frame 180-240: Cuts through/crosses fence line into foreground (restricted zone)
        # Frame 240-300: Loitering inside restricted zone
        progress = f_idx / num_frames

        if f_idx < 100:
            px = int(200 + progress * 600)
            py = int(fence_y - 50 + math.sin(f_idx * 0.2) * 5)
            scale = 0.65
        elif f_idx < 180:
            # Pacing back and forth
            osc = math.sin((f_idx - 100) * 0.15)
            px = int(450 + osc * 80)
            py = int(fence_y - 30)
            scale = 0.75
        elif f_idx < 250:
            # Breaching fence and advancing into foreground
            cross_prog = (f_idx - 180) / 70.0
            px = int(450 + cross_prog * 80)
            py = int(fence_y - 20 + cross_prog * 160)
            scale = 0.75 + cross_prog * 0.4
        else:
            # Loitering in restricted zone
            px = int(530 + math.sin(f_idx * 0.1) * 15)
            py = int(fence_y + 140)
            scale = 1.15

        # Draw Person silhouette (head, torso, limbs)
        p_color = (65, 75, 80)
        head_radius = int(14 * scale)
        head_cy = int(py - 70 * scale)
        cv2.circle(frame, (px, head_cy), head_radius, p_color, -1)
        # Torso
        cv2.rectangle(frame, (int(px - 16 * scale), int(py - 55 * scale)), (int(px + 16 * scale), int(py)), p_color, -1)
        # Legs with animated walking cadence
        leg_swing = int(math.sin(f_idx * 0.4) * 12 * scale)
        cv2.line(frame, (int(px - 8 * scale), int(py)), (int(px - 8 * scale + leg_swing), int(py + 50 * scale)), p_color, int(6 * scale))
        cv2.line(frame, (int(px + 8 * scale), int(py)), (int(px + 8 * scale - leg_swing), int(py + 50 * scale)), p_color, int(6 * scale))

        # 5. Overlay Military HUD Telemetry
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(1773780000 + f_idx))
        cv2.putText(frame, f"ARC VISION | CAM-01 NORTH PERIMETER [SEC 4]", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
        cv2.putText(frame, f"NIGHT THERMAL/IR ADAPTIVE | FPS: {fps} | {time_str}Z", (30, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        cv2.putText(frame, "STATUS: PATROL MONITORING ACTIVE", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        out.write(frame)

    out.release()
    logger.info(f"Generated synthetic perimeter breach video: {output_path}")

def generate_checkpoint_anpr_video(output_path: Path, num_frames: int = 300, fps: int = 15):
    """
    Generates a 20-second checkpoint surveillance video (1280x720):
    Vehicle approaches border gate, stops, license plate read.
    """
    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    plate_text = "DL01AB1234"

    for f_idx in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Checkpoint road & inspection bay
        frame[:] = (40, 45, 50)
        # Road lane
        cv2.fillPoly(frame, [np.array([[200, h], [500, 300], [780, 300], [1080, h]], np.int32)], (60, 60, 65))
        # Lane markings
        cv2.line(frame, (640, 300), (640, h), (200, 200, 0), 4)

        # Inspection booth on right
        cv2.rectangle(frame, (850, 240), (1150, 500), (70, 75, 85), -1)
        cv2.rectangle(frame, (880, 280), (1020, 380), (150, 170, 180), -1) # Booth window
        cv2.putText(frame, "SSB CHECKPOST 02", (860, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Security barrier gate (yellow/black stripes)
        barrier_y = 520
        cv2.line(frame, (450, barrier_y), (850, barrier_y), (0, 220, 255), 10)

        # Approaching Vehicle (Car / SUV)
        # Frames 0-160: Enters from distance and approaches stop barrier
        # Frames 160-300: Stationary at barrier for security inspection
        if f_idx < 160:
            v_progress = f_idx / 160.0
        else:
            v_progress = 1.0

        vx = 640
        vy = int(340 + v_progress * 220)
        v_scale = 0.4 + v_progress * 0.75

        vw = int(240 * v_scale)
        vh = int(140 * v_scale)
        x1 = vx - vw // 2
        y1 = vy - vh
        x2 = vx + vw // 2
        y2 = vy

        # Vehicle Body (SUV silhouette)
        cv2.rectangle(frame, (x1, y1 + int(vh * 0.3)), (x2, y2), (25, 45, 95), -1) # Dark navy vehicle body
        cv2.rectangle(frame, (x1 + int(vw * 0.15), y1), (x2 - int(vw * 0.15), y1 + int(vh * 0.45)), (30, 55, 115), -1) # Cabin
        # Windshield
        cv2.rectangle(frame, (x1 + int(vw * 0.2), y1 + int(vh * 0.05)), (x2 - int(vw * 0.2), y1 + int(vh * 0.35)), (160, 180, 195), -1)
        # Headlights
        cv2.circle(frame, (x1 + int(vw * 0.15), y2 - int(vh * 0.2)), int(8 * v_scale), (150, 255, 255), -1)
        cv2.circle(frame, (x2 - int(vw * 0.15), y2 - int(vh * 0.2)), int(8 * v_scale), (150, 255, 255), -1)

        # License Plate (White rectangular plate with crisp Indian registration text)
        pw = int(70 * v_scale)
        ph = int(22 * v_scale)
        px1 = vx - pw // 2
        py1 = y2 - int(vh * 0.25)
        px2 = vx + pw // 2
        py2 = py1 + ph

        cv2.rectangle(frame, (px1, py1), (px2, py2), (250, 250, 250), -1)
        cv2.rectangle(frame, (px1, py1), (px2, py2), (0, 0, 0), 1)

        if v_scale > 0.6:
            font_scale = 0.4 * v_scale
            cv2.putText(frame, plate_text, (px1 + 4, py2 - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1)

        # Telemetry overlay
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(1773780000 + f_idx))
        cv2.putText(frame, f"ARC VISION | CAM-02 CHECKPOINT [LANE 1]", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
        cv2.putText(frame, f"ANPR OPTICAL SENSOR | FPS: {fps} | {time_str}Z", (30, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        
        if f_idx >= 160:
            cv2.putText(frame, "VEHICLE STOPPED FOR ANPR INSPECTION", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "VEHICLE APPROACHING BARRIER", (30, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        out.write(frame)

    out.release()
    logger.info(f"Generated synthetic checkpoint ANPR video: {output_path}")

def ensure_demo_assets():
    settings.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    breach_vid = settings.DEMO_DIR / "night_perimeter_breach.mp4"
    checkpoint_vid = settings.DEMO_DIR / "checkpoint_anpr_vehicle.mp4"

    if not breach_vid.exists() or breach_vid.stat().st_size < 1000:
        logger.info("Building demo video 1: Night Perimeter Breach...")
        generate_perimeter_breach_video(breach_vid, num_frames=240, fps=15)

    if not checkpoint_vid.exists() or checkpoint_vid.stat().st_size < 1000:
        logger.info("Building demo video 2: Checkpoint ANPR...")
        generate_checkpoint_anpr_video(checkpoint_vid, num_frames=240, fps=15)
