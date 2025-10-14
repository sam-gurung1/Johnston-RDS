# Johnston (1991) Stereo Shape Distortion RDS Experiment — FINAL HAPLOSCOPE VERSION
# Run this version on dual-screen stereo haploscope setup

from psychopy import core, data, gui, monitors, visual
from psychopy.hardware import keyboard
import numpy as np
import os
import math

# === Participant & Session Info ===
exp_info = {
    "participant": "",
    "session": "1",
    "haploscope_offset_cm": "0.0",  # Optional horizontal calibration per eye
    "haploscope_scale_x": "1.0",    # Optional horizontal stretch compensation
    "screen_distance_cm": "85.0",
    "screen_width_cm": "70.0",      # Update with the measured physical width of each panel
    "interocular_distance_cm": "6.5",
    "participant_keyboard": "auto"   # Choose "auto" or type an attached device name
}

dlg = gui.DlgFromDict(exp_info, title="Johnston RDS Stereo Experiment")
if not dlg.OK:
    core.quit()

exp_info["date"] = data.getDateStr()
exp_info["expName"] = "JohnstonRDS"

# === Data/Experiment Handlers ===
os.makedirs("data", exist_ok=True)
filename = os.path.join("data", f"{exp_info['participant']}_{exp_info['date']}")

this_exp = data.ExperimentHandler(
@@ -39,99 +40,123 @@ this_exp = data.ExperimentHandler(
screen_distance_cm = float(exp_info["screen_distance_cm"])
interocular_distance_cm = float(exp_info["interocular_distance_cm"])
monitor_res_px = (3840, 2160)
screen_width_cm = float(exp_info["screen_width_cm"])

# Haploscope calibration parameters (converted once to float)
haploscope_offset_cm = float(exp_info["haploscope_offset_cm"])
haploscope_scale_x = float(exp_info["haploscope_scale_x"])

# === Stereo Window Setup (left = screen 1, right = screen 0) ===
haplo_monitor = monitors.Monitor("haploscope", width=screen_width_cm, distance=screen_distance_cm)
haplo_monitor.setSizePix(monitor_res_px)

LEFT_SCREEN_INDEX = 1
RIGHT_SCREEN_INDEX = 0

win_left = visual.Window(
    size=monitor_res_px,
    screen=LEFT_SCREEN_INDEX,
    fullscr=True,
    units="cm",
    color=[-1, -1, -1],
    winType="pyglet",
    allowGUI=False,
    monitor=haplo_monitor,
    pos=(0, 0),
    waitBlanking=True,
)
win_right = visual.Window(
    size=monitor_res_px,
    screen=RIGHT_SCREEN_INDEX,
    fullscr=True,
    units="cm",
    color=[-1, -1, -1],
    winType="pyglet",
    allowGUI=False,
    monitor=haplo_monitor,
    pos=(0, 0),
    waitBlanking=True,
)

win_left.mouseVisible = False
win_right.mouseVisible = False

# Stretch compensation for haploscope optics (optional)
win_left.viewScale = [haploscope_scale_x, 1.0]
win_right.viewScale = [haploscope_scale_x, 1.0]

# === Shared termination helper so ESC always exits cleanly ===
_experiment_terminated = {"value": False}


def terminate_experiment():
    """Save data, close windows, and quit safely (idempotent)."""

    if _experiment_terminated["value"]:
        return

    _experiment_terminated["value"] = True

    this_exp.saveAsWideText(filename + ".csv")
    this_exp.saveAsPickle(filename)
    if win_left.winHandle is not None:
        win_left.close()
    if win_right.winHandle is not None:
        win_right.close()
    core.quit()

# === Cylinder Parameters ===
a_cm = 5.0  # Horizontal semi-axis of the elliptical half-cylinder (radius "a" in Johnston)
b_values_cm = [3.35, 5.0, 6.65, 8.3, 9.95]
n_dots = 1500
stim_duration_s = 1.5
stim_half_height_cm = 5.0  # Vertical semi-axis of the elliptical cross-section
aperture_radius_cm = 7.5   # Radius for the circular random-dot aperture

# === Timing Control ===
frame_rate_left = win_left.getActualFrameRate(nIdentical=90, nWarmUpFrames=60) or getattr(win_left, "monitorFrameRate", None)
frame_rate_right = win_right.getActualFrameRate(nIdentical=90, nWarmUpFrames=60) or getattr(win_right, "monitorFrameRate", None)

if not frame_rate_left:
    frame_rate_left = 60.0
if not frame_rate_right:
    frame_rate_right = 60.0

refresh_min_hz = min(frame_rate_left, frame_rate_right)
stim_frames = max(1, int(round(stim_duration_s * refresh_min_hz)))

exp_info["frame_rate_left_hz"] = float(np.round(frame_rate_left, 3))
exp_info["frame_rate_right_hz"] = float(np.round(frame_rate_right, 3))
exp_info["frame_rate_min_hz"] = float(np.round(refresh_min_hz, 3))
exp_info["stimulus_frames"] = int(stim_frames)

print(
    f"Measured refresh rates — Left: {frame_rate_left:.3f} Hz, "
    f"Right: {frame_rate_right:.3f} Hz. Scheduling {stim_frames} frames per trial "
    f"(~{stim_frames / refresh_min_hz:.3f} s) at the slower eye."
)

# === Utility Functions ===
def project_to_screen(x_cm, z_cm, distance_cm, iod_cm):
    """Project 3D coordinates (x, z) for a frontoparallel screen at ``distance_cm``."""

    half_iod = iod_cm / 2.0

    # Convert cylinder-relative depth (z=0 on the screen, positive toward the observer)
    # into the distance from each eye to the 3D point. Clamp to avoid coincident planes.
    depth_from_eye = distance_cm - z_cm
    depth_from_eye = np.where(depth_from_eye <= 0.5, 0.5, depth_from_eye)

    # Scale factor for the intersection of the eye–point ray with the screen plane.
    scale = distance_cm / depth_from_eye

    x_left = -half_iod + scale * (x_cm + half_iod)
    x_right = half_iod + scale * (x_cm - half_iod)

    disparity_cm = x_right - x_left
    disparity_angle_rad = disparity_cm / distance_cm

    # Johnston (1991) analytic disparity prediction for validation
    safe_z = np.clip(z_cm, None, distance_cm - 0.5)
    disparity_formula_rad = (
        iod_cm * safe_z / ((distance_cm ** 2) - (safe_z ** 2))
@@ -292,79 +317,111 @@ for trial in trials:
        n_dots,
        stim_half_height_cm,
        aperture_radius_cm,
        screen_width_cm,
    )

    dots_left = visual.ElementArrayStim(
        win_left,
        nElements=n_dots,
        elementTex=None,
        elementMask="circle",
        xys=np.column_stack((x_left, y_coords)),
        sizes=0.15,
        colors="white"
    )
    dots_right = visual.ElementArrayStim(
        win_right,
        nElements=n_dots,
        elementTex=None,
        elementMask="circle",
        xys=np.column_stack((x_right, y_coords)),
        sizes=0.15,
        colors="white"
    )

    stim_flip_times_left = []
    stim_flip_times_right = []
    stim_clock_left = core.Clock()
    stim_clock_right = core.Clock()

    for frame_index in range(stim_frames):
        fix_left.draw()
        fix_right.draw()
        dots_left.draw()
        dots_right.draw()
        if frame_index == 0:
            win_left.callOnFlip(stim_clock_left.reset)
            win_right.callOnFlip(stim_clock_right.reset)
        win_left.flip()
        win_right.flip()
        stim_flip_times_left.append(stim_clock_left.getTime())
        stim_flip_times_right.append(stim_clock_right.getTime())
        if default_kb.getKeys(["escape"], waitRelease=False):
            terminate_experiment()

    kb.clearEvents()
    kb.clock.reset()

    responded = False
    response_key = None
    response_rt = None

    while not responded:
        fix_left.draw()
        fix_right.draw()
        question_left.draw()
        question_right.draw()
        win_left.flip()
        win_right.flip()

        if default_kb.getKeys(["escape"], waitRelease=False):
            terminate_experiment()

        keys = kb.getKeys(keyList=["1", "2"], waitRelease=False)
        if keys:
            first_key = keys[0]
            response_key = first_key.name
            response_rt = first_key.rt
            responded = True

    response_label = "squashed" if response_key == "1" else "stretched"

    trials.addData("trial_index", trials.thisN)
    trials.addData("b_cm", b_cm)
    trials.addData("response", response_label)
    trials.addData("response_key", response_key)
    trials.addData("rt", response_rt)
    trials.addData("disparity_mean_cm", float(np.mean(disparity_cm)))
    trials.addData("disparity_std_cm", float(np.std(disparity_cm)))
    trials.addData("disparity_angle_mean_rad", float(np.mean(disparity_angle)))
    trials.addData("disparity_formula_mean_rad", float(np.mean(disparity_formula)))
    trials.addData(
        "disparity_angle_formula_diff_rad",
        float(np.mean(disparity_angle - disparity_formula)),
    )

    left_frame_diffs = np.diff(stim_flip_times_left) if len(stim_flip_times_left) > 1 else []
    right_frame_diffs = np.diff(stim_flip_times_right) if len(stim_flip_times_right) > 1 else []

    mean_left_dur = float(np.mean(left_frame_diffs)) if len(left_frame_diffs) > 0 else math.nan
    mean_right_dur = float(np.mean(right_frame_diffs)) if len(right_frame_diffs) > 0 else math.nan
    std_left_dur = float(np.std(left_frame_diffs)) if len(left_frame_diffs) > 0 else math.nan
    std_right_dur = float(np.std(right_frame_diffs)) if len(right_frame_diffs) > 0 else math.nan

    stim_duration_left = float(stim_flip_times_left[-1]) if stim_flip_times_left else math.nan
    stim_duration_right = float(stim_flip_times_right[-1]) if stim_flip_times_right else math.nan

    trials.addData("stim_frames_scheduled", stim_frames)
    trials.addData("frame_count_left", len(stim_flip_times_left))
    trials.addData("frame_count_right", len(stim_flip_times_right))
    trials.addData("stimulus_duration_left_s", stim_duration_left)
    trials.addData("stimulus_duration_right_s", stim_duration_right)
    trials.addData("frame_duration_mean_left_s", mean_left_dur)
    trials.addData("frame_duration_mean_right_s", mean_right_dur)
    trials.addData("frame_duration_std_left_s", std_left_dur)
    trials.addData("frame_duration_std_right_s", std_right_dur)

    this_exp.nextEntry()

# === Cleanup ===
terminate_experiment()
