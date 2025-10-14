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
DYNAMIC_RDS_UPDATE_EVERY = 2  # regenerate every N frames when DYNAMIC_RDS=True (cuts GPU cost)
DYNAMIC_RDS_BANK_SIZE = 12    # number of pre-generated frames to cycle when dynamic noise is enabled
POST_FIX_SEC = 0.3        # post-stim fixation to standardize decision time
FUSION_PRIME_SEC = 0.4    # zero-disparity noise before each stimulus — locks vergence
MEASURE_BOTH_REFRESH = False  # set True if panels have very different refresh caps
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
@@ -94,105 +97,128 @@ def terminate_experiment():
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

# === Measure refresh; optionally skip the second probe to speed up launch ===
fr_left = win_left.getActualFrameRate(nIdentical=90, nWarmUpFrames=60) or 60.0
if MEASURE_BOTH_REFRESH:
    fr_right = win_right.getActualFrameRate(nIdentical=90, nWarmUpFrames=60) or 60.0
else:
    fr_right = fr_left
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

def generate_rds(a, b, dist, iod, n, y_semi, aperture, width, offset_cm=None):
    """Return per-eye dot coordinates for a half-elliptical cylinder RDS + disparity stats."""
    half_width = width / 2.0
    offset_cm = haplo_offset_cm if offset_cm is None else offset_cm

    xL_chunks, xR_chunks, y_chunks = [], [], []
    dcm_chunks, dang_chunks, dfor_chunks = [], [], []

    collected = 0
    while collected < n:
        remaining = n - collected
        batch = max(int(np.ceil(remaining * 1.6)), 64)
        theta = np.random.uniform(0, 2 * np.pi, batch)
        r = aperture * np.sqrt(np.random.uniform(0, 1, batch))
        x, y = r * np.cos(theta), r * np.sin(theta)

        # Half-cylinder surface: inside ellipse gets z>0 (bulges toward observer), outside z=0
        inside = ((x / a) ** 2 + (y / y_semi) ** 2) <= 1.0
        z = np.zeros_like(x)
        if np.any(inside):
            xin = x[inside]
            z[inside] = b * np.sqrt(np.clip(1 - (xin / a) ** 2, 0, None))

        xL, xR, dcm, dang, dfor = project_to_screen(x, z, dist, iod)
        if offset_cm:
            # Haploscope horizontal calibration (equal and opposite shifts)
            xL -= offset_cm
            xR += offset_cm

        # Keep only dots visible to BOTH eyes (prevents monocular ghosts)
        keep = (np.abs(xL) <= half_width) & (np.abs(xR) <= half_width)
        kept = int(np.count_nonzero(keep))
        if kept == 0:
            continue

        xL_chunks.append(xL[keep])
        xR_chunks.append(xR[keep])
        y_chunks.append(y[keep])
        dcm_chunks.append(dcm[keep])
        dang_chunks.append(dang[keep])
        dfor_chunks.append(dfor[keep])
        collected += kept

    def _cat(chunks):
        if len(chunks) == 1:
            return chunks[0][:n]
        return np.concatenate(chunks, axis=0)[:n]

    xL = _cat(xL_chunks)
    xR = _cat(xR_chunks)
    y = _cat(y_chunks)
    dcm = _cat(dcm_chunks)
    dang = _cat(dang_chunks)
    dfor = _cat(dfor_chunks)
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
@@ -213,104 +239,122 @@ if TEST_MODE:
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
        n_dots, stim_half_height_cm, aperture_radius_cm, screen_width_cm,
        offset_cm=0.0  # force zero-disparity regardless of haploscope offset
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
    def regenerate_cylinder():
        return generate_rds(
            a_cm, b, screen_distance_cm, interocular_cm,
            n_dots, stim_half_height_cm, aperture_radius_cm, screen_width_cm
        )

    if DYNAMIC_RDS:
        bank_len = max(int(DYNAMIC_RDS_BANK_SIZE), 1)
        rds_bank = [regenerate_cylinder() for _ in range(bank_len)]
        bank_index = 0
        xL, xR, y, dcm, dang, dfor = rds_bank[bank_index]
    else:
        xL, xR, y, dcm, dang, dfor = regenerate_cylinder()
    baseL = np.column_stack((xL, y))
    baseR = np.column_stack((xR, y))

    dotsL = visual.ElementArrayStim(win_left,  nElements=n_dots, elementTex=None, elementMask="circle",
                                    xys=baseL, sizes=dot_size_cm, colors="white")
    dotsR = visual.ElementArrayStim(win_right, nElements=n_dots, elementTex=None, elementMask="circle",
                                    xys=baseR, sizes=dot_size_cm, colors="white")

    update_interval = max(int(DYNAMIC_RDS_UPDATE_EVERY), 1)

    for f in range(stim_frames):
        if DYNAMIC_RDS and f % update_interval == 0:
            if f != 0:
                bank_index = (bank_index + 1) % len(rds_bank)
                if bank_index == 0:
                    rds_bank = [regenerate_cylinder() for _ in range(len(rds_bank))]
                xL_dyn, xR_dyn, y_dyn, *_ = rds_bank[bank_index]
            else:
                xL_dyn, xR_dyn, y_dyn = xL, xR, y
            dotsL.xys = np.column_stack((xL_dyn, y_dyn))
            dotsR.xys = np.column_stack((xR_dyn, y_dyn))
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
    trials.addData("refresh_min_hz", refresh_min_hz)
    trials.addData("refresh_left_hz", fr_left)
    trials.addData("refresh_right_hz", fr_right)
    this_exp.nextEntry()

# ============================ CLEANUP ============================
terminate_experiment()
