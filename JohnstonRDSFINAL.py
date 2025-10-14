# ===============================================================
# Johnston (1991) Stereo Shape Distortion RDS Experiment
# FINAL WINDOWS HAPLOSCOPE DEMO — with NONIUS + FUSION PRIME
#   • Nonius bars (alignment helper) in TEST MODE + fusion prime
#   • Fusion prime: brief zero-disparity random dots before each trial
#   • Big/clear stimulus defaults for easy fusion
# ===============================================================

from psychopy import core, data, gui, monitors, visual
from psychopy.hardware import keyboard
import numpy as np
import os, math

# ========================= RIG CONFIG =========================
WIN_TYPE = "glfw"         # GLFW tends to be steadier than pyglet for dual fullscreens on Windows
RIGHT_SCREEN_INDEX = 0    # match Windows “Identify”; swap with LEFT if depth is inverted
LEFT_SCREEN_INDEX  = 1

TEST_MODE    = True       # 10s convex cylinder + nonius to verify mapping/fusion
DYNAMIC_RDS  = False      # True = new random dots each frame. You don't need it for fusion.
POST_FIX_SEC = 0.3        # post-stim fixation to standardize decision time
FUSION_PRIME_SEC = 0.4    # zero-disparity noise before each stimulus — locks vergence
# =============================================================

# === Participant dialog (enter physical params, dot size, etc.) ===
exp_info = {
    "participant": "",
    "session": "1",
    "haploscope_offset_cm": "0.0",     # tweak ±0.1–0.3 if nonius bars don't align
    "haploscope_scale_x": "1.0",       # legacy single stretch
    "haploscope_scale_x_left": "1.0",  # per-eye stretch (left)
    "haploscope_scale_x_right": "1.0", # per-eye stretch (right)
    "screen_distance_cm": "85.0",
    "screen_width_cm": "70.0",         # measured physical width of EACH panel
    "interocular_distance_cm": "6.5",
    "participant_keyboard": "auto",
    "dot_size_cm": "0.25",             # bigger dots = easier to see/fuse
}

dlg = gui.DlgFromDict(exp_info, title="Johnston RDS Stereo Experiment")
if not dlg.OK:
    core.quit()
exp_info["date"] = data.getDateStr()
exp_info["expName"] = "JohnstonRDS"

# === Data files ===
os.makedirs("data", exist_ok=True)
filename = os.path.join("data", f"{exp_info['participant']}_{exp_info['date']}")
this_exp = data.ExperimentHandler(name=exp_info["expName"], extraInfo=exp_info, dataFileName=filename)

# ========================== MONITOR ===========================
screen_distance_cm = float(exp_info["screen_distance_cm"])
screen_width_cm    = float(exp_info["screen_width_cm"])
interocular_cm     = float(exp_info["interocular_distance_cm"])
monitor_res_px     = (3840, 2160)  # set to your panels’ native resolution
dot_size_cm        = float(exp_info["dot_size_cm"])

# Haploscope calibration
haplo_offset_cm = float(exp_info["haploscope_offset_cm"])
scale_single    = float(exp_info["haploscope_scale_x"])
scale_x_left    = float(exp_info.get("haploscope_scale_x_left",  scale_single))
scale_x_right   = float(exp_info.get("haploscope_scale_x_right", scale_single))

# PsychoPy Monitor (tells PsychoPy real cm & px)
haplo_monitor = monitors.Monitor("haploscope", width=screen_width_cm, distance=screen_distance_cm)
haplo_monitor.setSizePix(monitor_res_px)

# === Create windows — RIGHT first, then LEFT (driver-friendly order) ===
win_right = visual.Window(
    size=monitor_res_px, screen=RIGHT_SCREEN_INDEX, fullscr=True,
    units="cm", color=[-1, -1, -1], winType=WIN_TYPE, waitBlanking=True,
    monitor=haplo_monitor, pos=(0, 0)
)
core.wait(0.2)  # small settle
win_left = visual.Window(
    size=monitor_res_px, screen=LEFT_SCREEN_INDEX, fullscr=True,
    units="cm", color=[-1, -1, -1], winType=WIN_TYPE, waitBlanking=True,
    monitor=haplo_monitor, pos=(0, 0)
)

# Hide cursors
win_left.mouseVisible = False
win_right.mouseVisible = False

# Per-eye stretch compensation (keep both 1.0 unless asymmetry in optics)
win_left.viewScale  = [scale_x_left,  1.0]
win_right.viewScale = [scale_x_right, 1.0]

# ================== CLEAN EXIT (ESC works anywhere) =================
_experiment_terminated = {"value": False}
def terminate_experiment():
    if _experiment_terminated["value"]:
        return
    _experiment_terminated["value"] = True
    try:
        this_exp.saveAsWideText(filename + ".csv")
        this_exp.saveAsPickle(filename)
    except Exception:
        pass
    for w in (win_left, win_right):
        try:
            if w.winHandle is not None:
                w.close()
        except Exception:
            pass
    core.quit()
# ====================================================================

# ========================= STIMULUS PARAMS ==========================
# Larger defaults for easy fusion; adjust down if your mirrors crop
a_cm = 5.5                  # cylinder half-width (horizontal)
b_values_cm = [3.35, 5.0, 6.65, 8.3, 9.95]
n_dots = 1500
stim_duration_s = 1.5
stim_half_height_cm = 6.0   # cylinder half-height (vertical)
aperture_radius_cm = 10.0   # dot field radius (bigger field = easier fusion)
# ====================================================================

# === Measure per-eye refresh; schedule to the slower eye ===
fr_left  = win_left.getActualFrameRate(nIdentical=90, nWarmUpFrames=60)  or 60.0
fr_right = win_right.getActualFrameRate(nIdentical=90, nWarmUpFrames=60) or 60.0
refresh_min_hz = min(fr_left, fr_right)
stim_frames = int(round(stim_duration_s * refresh_min_hz))
print(f"Refresh L:{fr_left:.2f}Hz R:{fr_right:.2f}Hz → scheduling {stim_frames} frames ({stim_duration_s:.2f}s)")

# ======================== GEOMETRY HELPERS ==========================
def project_to_screen(x_cm, z_cm, distance_cm, iod_cm):
    """Binocular pinhole projection for frontoparallel screen at distance_cm (z=0 plane)."""
    half = iod_cm / 2.0
    depth_from_eye = np.maximum(distance_cm - z_cm, 0.5)  # avoid division explosions
    scale = distance_cm / depth_from_eye
    xL = -half + scale * (x_cm + half)
    xR =  half + scale * (x_cm - half)
    disp_cm = xR - xL
    disp_rad = disp_cm / distance_cm  # small-angle approximation
    safe_z = np.clip(z_cm, None, distance_cm - 0.5)
    disp_formula = (iod_cm * safe_z) / ((distance_cm**2) - (safe_z**2))
    return xL, xR, disp_cm, disp_rad, disp_formula

def generate_rds(a, b, dist, iod, n, y_semi, aperture, width):
    """Return per-eye dot coordinates for a half-elliptical cylinder RDS + disparity stats."""
    half_width = width / 2.0
    xL_all, xR_all, y_all = [], [], []
    dcm_all, dang_all, dfor_all = [], [], []

    needed = n
    while needed > 0:
        batch = int(np.ceil(needed * 1.6))
        theta = np.random.uniform(0, 2*np.pi, batch)
        r = aperture * np.sqrt(np.random.uniform(0, 1, batch))
        x, y = r*np.cos(theta), r*np.sin(theta)

        # Half-cylinder surface: inside ellipse gets z>0 (bulges toward observer), outside z=0
        inside = ((x / a) ** 2 + (y / y_semi) ** 2) <= 1.0
        z = np.zeros_like(x)
        if np.any(inside):
            xin = x[inside]
            z[inside] = b * np.sqrt(np.clip(1 - (xin / a)**2, 0, None))

        xL, xR, dcm, dang, dfor = project_to_screen(x, z, dist, iod)
        # Haploscope horizontal calibration (equal and opposite shifts)
        xL -= haplo_offset_cm
        xR += haplo_offset_cm

        # Keep only dots visible to BOTH eyes (prevents monocular ghosts)
        keep = (np.abs(xL) <= half_width) & (np.abs(xR) <= half_width)
        xL_all.append(xL[keep]); xR_all.append(xR[keep]); y_all.append(y[keep])
        dcm_all.append(dcm[keep]); dang_all.append(dang[keep]); dfor_all.append(dfor[keep])

        needed = n - sum(len(chunk) for chunk in xL_all)

    xL = np.concatenate(xL_all)[:n]; xR = np.concatenate(xR_all)[:n]; y = np.concatenate(y_all)[:n]
    dcm = np.concatenate(dcm_all)[:n]; dang = np.concatenate(dang_all)[:n]; dfor = np.concatenate(dfor_all)[:n]
    return xL, xR, y, dcm, dang, dfor
# ====================================================================

# === Reusable drawables ===
fix_left  = visual.TextStim(win_left,  text="+", pos=(0, 0), height=0.7, color="white")
fix_right = visual.TextStim(win_right, text="+", pos=(0, 0), height=0.7, color="white")

# NONIUS BARS: short vertical lines above (left eye) and below (right eye) fixation.
# When haploscope_offset_cm is good, they should appear as ONE straight vertical line through the '+'
nonius_left  = visual.Line(win_left,  start=(0, +1.5), end=(0, +2.5), lineWidth=3, lineColor="white")
nonius_right = visual.Line(win_right, start=(0, -1.5), end=(0, -2.5), lineWidth=3, lineColor="white")

question_text = "Was the cylinder:\n[1] Squashed\n[2] Stretched"
question_left  = visual.TextStim(win_left,  text=question_text, pos=(0, -5), height=0.7, color="white")
question_right = visual.TextStim(win_right, text=question_text, pos=(0, -5), height=0.7, color="white")

# Keyboards
kb = keyboard.Keyboard()
default_kb = keyboard.Keyboard()  # listens for ESC anywhere

# ============================== TEST MODE =============================
if TEST_MODE:
    print("TEST MODE: 10 s convex cylinder + nonius bars. Swap LEFT/RIGHT indices if it looks concave.")
    b_test = 9.95
    xL, xR, y, *_ = generate_rds(a_cm, b_test, screen_distance_cm, interocular_cm,
                                 n_dots, stim_half_height_cm, aperture_radius_cm, screen_width_cm)
    dotsL = visual.ElementArrayStim(win_left,  nElements=n_dots, elementTex=None, elementMask="circle",
                                    xys=np.column_stack((xL, y)), sizes=max(dot_size_cm, 0.25), colors="white")
    dotsR = visual.ElementArrayStim(win_right, nElements=n_dots, elementTex=None, elementMask="circle",
                                    xys=np.column_stack((xR, y)), sizes=max(dot_size_cm, 0.25), colors="white")
    clock = core.Clock()
    while clock.getTime() < 10:
        # Draw fixation + NONIUS + big cylinder
        fix_left.draw();  fix_right.draw()
        nonius_left.draw(); nonius_right.draw()
        dotsL.draw(); dotsR.draw()
        win_left.flip(); win_right.flip()
        if default_kb.getKeys(["escape"], waitRelease=False): terminate_experiment()

    print("Adjust 'haploscope_offset_cm' until the nonius bars form ONE straight line. Press any key to continue...")
    while not kb.getKeys(waitRelease=False):
        fix_left.draw();  fix_right.draw()
        nonius_left.draw(); nonius_right.draw()
        win_left.flip();   win_right.flip()
        if default_kb.getKeys(["escape"], waitRelease=False): terminate_experiment()
# ======================================================================

# ============================= TRIALS =================================
conditions = [{"b_cm": b} for b in b_values_cm]
trials = data.TrialHandler(trialList=conditions, nReps=3, method="random", extraInfo=exp_info)
this_exp.addLoop(trials)

deg_per_rad = 180.0 / np.pi

for trial in trials:
    b = trial["b_cm"]

    # ---------------- FUSION PRIME (zero-disparity noise) ----------------
    # We render a dot field with b=0 (z=0 for all points). For true zero-disparity,
    # we also FORCE both eyes to see IDENTICAL xys (use LEFT positions for both).
    prime_frames = int(round(FUSION_PRIME_SEC * refresh_min_hz))
    xL_p, xR_p, y_p, *_ = generate_rds(
        a_cm, 0.0,  # b=0 → flat plane at the screen → xL==xR in projection
        screen_distance_cm, interocular_cm,
        n_dots, stim_half_height_cm, aperture_radius_cm, screen_width_cm
    )
    prime_xy = np.column_stack((xL_p, y_p))  # identical positions to both eyes → guarantees zero disparity
    primeL = visual.ElementArrayStim(win_left,  nElements=n_dots, elementTex=None, elementMask="circle",
                                     xys=prime_xy, sizes=dot_size_cm, colors="white")
    primeR = visual.ElementArrayStim(win_right, nElements=n_dots, elementTex=None, elementMask="circle",
                                     xys=prime_xy, sizes=dot_size_cm, colors="white")

    for _ in range(prime_frames):
        fix_left.draw();  fix_right.draw()
        nonius_left.draw(); nonius_right.draw()  # show nonius during prime to fine-tune offset live
        primeL.draw();    primeR.draw()
        win_left.flip();  win_right.flip()
        if default_kb.getKeys(["escape"], waitRelease=False): terminate_experiment()
    # ---------------------------------------------------------------------

    # ---------------------- CYLINDER STIMULUS -----------------------------
    # Generate one static RDS for this condition (unless DYNAMIC_RDS=True)
    xL, xR, y, dcm, dang, dfor = generate_rds(
        a_cm, b, screen_distance_cm, interocular_cm,
        n_dots, stim_half_height_cm, aperture_radius_cm, screen_width_cm
    )
    baseL = np.column_stack((xL, y))
    baseR = np.column_stack((xR, y))

    dotsL = visual.ElementArrayStim(win_left,  nElements=n_dots, elementTex=None, elementMask="circle",
                                    xys=baseL, sizes=dot_size_cm, colors="white")
    dotsR = visual.ElementArrayStim(win_right, nElements=n_dots, elementTex=None, elementMask="circle",
                                    xys=baseR, sizes=dot_size_cm, colors="white")

    for f in range(stim_frames):
        if DYNAMIC_RDS:
            xL, xR, y, *_ = generate_rds(
                a_cm, b, screen_distance_cm, interocular_cm,
                n_dots, stim_half_height_cm, aperture_radius_cm, screen_width_cm
            )
            dotsL.xys = np.column_stack((xL, y))
            dotsR.xys = np.column_stack((xR, y))
        fix_left.draw();  fix_right.draw()
        # (no nonius during the actual depth stimulus — reduces distraction)
        dotsL.draw();     dotsR.draw()
        win_left.flip();  win_right.flip()
        if default_kb.getKeys(["escape"], waitRelease=False): terminate_experiment()
    # ---------------------------------------------------------------------

    # Post-stim fixation (brief pause before the question)
    for _ in range(int(POST_FIX_SEC * refresh_min_hz)):
        fix_left.draw();  fix_right.draw()
        win_left.flip();  win_right.flip()
        if default_kb.getKeys(["escape"], waitRelease=False): terminate_experiment()

    # ----------------------------- RESPONSE -------------------------------
    kb.clearEvents(); kb.clock.reset()
    response_key, response_rt = None, None
    while response_key is None:
        fix_left.draw();  fix_right.draw()
        question_left.draw(); question_right.draw()
        win_left.flip();  win_right.flip()
        if default_kb.getKeys(["escape"], waitRelease=False): terminate_experiment()
        keys = kb.getKeys(["1", "2"], waitRelease=False)
        if keys:
            k = keys[0]
            response_key, response_rt = k.name, k.rt
    response_label = "squashed" if response_key == "1" else "stretched"
    # ---------------------------------------------------------------------

    # Log trial data
    trials.addData("b_cm", b)
    trials.addData("response_key", response_key)
    trials.addData("response_label", response_label)
    trials.addData("rt", response_rt)
    trials.addData("disparity_mean_cm", float(np.mean(dcm)))
    trials.addData("disparity_std_cm", float(np.std(dcm)))
    trials.addData("disparity_angle_mean_deg", float(np.mean(dang) * deg_per_rad))
    this_exp.nextEntry()

# ============================ CLEANUP ============================
terminate_experiment()

