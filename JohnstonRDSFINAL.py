# Johnston (1991) Stereo Shape Distortion RDS Experiment — FINAL HAPLOSCOPE VERSION
# Run this version on dual-screen stereo haploscope setup

from psychopy import core, data, gui, monitors, visual
from psychopy.hardware import keyboard
import numpy as np
import os

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
    name=exp_info["expName"],
    extraInfo=exp_info,
    dataFileName=filename
)

# === Experiment Configuration ===
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
    pos=(0, 0)
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
    pos=(0, 0)
)

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
frame_rate = win_left.getActualFrameRate(nIdentical=60) or 60.0
stim_frames = max(1, int(round(stim_duration_s * frame_rate)))

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
    )

    return x_left, x_right, disparity_cm, disparity_angle_rad, disparity_formula_rad


def generate_rds(
    a_axis_cm,
    b_axis_cm,
    distance_cm,
    iod_cm,
    n_dots,
    y_semi_axis_cm,
    aperture_radius_cm,
    display_width_cm,
):
    """Create left/right random-dot arrays for Johnston's half-cylinder stimuli."""

    half_display_width = display_width_cm / 2.0

    x_left_all = []
    x_right_all = []
    y_all = []
    disp_cm_all = []
    disp_ang_all = []
    disp_formula_all = []

    dots_needed = n_dots

    while dots_needed > 0:
        # Oversample to compensate for clipping outside the monitors
        batch_size = int(np.ceil(dots_needed * 1.6))
        theta = np.random.uniform(0.0, 2.0 * np.pi, size=batch_size)
        radial = aperture_radius_cm * np.sqrt(np.random.uniform(0.0, 1.0, size=batch_size))
        x = radial * np.cos(theta)
        y = radial * np.sin(theta)

        inside_cylinder = ((x / a_axis_cm) ** 2 + (y / y_semi_axis_cm) ** 2) <= 1.0

        z = np.zeros_like(x)
        if np.any(inside_cylinder):
            x_inside = x[inside_cylinder]
            ellipse_term = 1.0 - (x_inside / a_axis_cm) ** 2
            ellipse_term = np.clip(ellipse_term, 0.0, None)
            z_profile = b_axis_cm * np.sqrt(ellipse_term)
            z[inside_cylinder] = z_profile

        (
            x_left_batch,
            x_right_batch,
            disp_cm_batch,
            disp_ang_batch,
            disp_formula_batch,
        ) = project_to_screen(x, z, distance_cm, iod_cm)

        x_left_batch = x_left_batch - haploscope_offset_cm
        x_right_batch = x_right_batch + haploscope_offset_cm

        in_bounds = (
            (np.abs(x_left_batch) <= half_display_width)
            & (np.abs(x_right_batch) <= half_display_width)
        )

        x_left_all.append(x_left_batch[in_bounds])
        x_right_all.append(x_right_batch[in_bounds])
        y_all.append(y[in_bounds])
        disp_cm_all.append(disp_cm_batch[in_bounds])
        disp_ang_all.append(disp_ang_batch[in_bounds])
        disp_formula_all.append(disp_formula_batch[in_bounds])

        dots_needed = n_dots - sum(arr.size for arr in x_left_all)

    x_left = np.concatenate(x_left_all)[:n_dots]
    x_right = np.concatenate(x_right_all)[:n_dots]
    y = np.concatenate(y_all)[:n_dots]
    disparity_cm = np.concatenate(disp_cm_all)[:n_dots]
    disparity_angle = np.concatenate(disp_ang_all)[:n_dots]
    disparity_formula = np.concatenate(disp_formula_all)[:n_dots]

    return x_left, x_right, y, disparity_cm, disparity_angle, disparity_formula


# === Stimulus Templates ===
fix_left = visual.TextStim(win_left, text="+", pos=(0, 0), height=0.5, color="white")
fix_right = visual.TextStim(win_right, text="+", pos=(0, 0), height=0.5, color="white")

question_text = "Was the cylinder:\n[1] Squashed\n[2] Stretched"
question_left = visual.TextStim(win_left, text=question_text, pos=(0, -5), height=0.7, color="white")
question_right = visual.TextStim(win_right, text=question_text, pos=(0, -5), height=0.7, color="white")

# === Trial Structure ===
conditions = [{"b_cm": value} for value in b_values_cm]
trials = data.TrialHandler(
    trialList=conditions,
    nReps=3,
    method="random",
    extraInfo=exp_info,
    name="trials"
)

this_exp.addLoop(trials)
# === Keyboard Devices ===
available_keyboards = keyboard.getKeyboards()
available_names = [dev.name for dev in available_keyboards]

participant_keyboard_name = exp_info.get("participant_keyboard", "auto")
participant_keyboard = None

if participant_keyboard_name and participant_keyboard_name.lower() != "auto":
    # Allow selecting by numeric index or by exact device name
    if participant_keyboard_name.isdigit():
        idx = int(participant_keyboard_name)
        if 0 <= idx < len(available_keyboards):
            participant_keyboard = available_keyboards[idx]
    else:
        for dev in available_keyboards:
            if dev.name == participant_keyboard_name:
                participant_keyboard = dev
                break
    if participant_keyboard is None and available_keyboards:
        # If the requested device is not found, fall back to the first available device
        participant_keyboard = available_keyboards[0]
else:
    participant_keyboard = available_keyboards[0] if available_keyboards else None

kb = keyboard.Keyboard(device=participant_keyboard)

# Separate keyboard instance that always listens for escape so the experimenter can stop safely
default_kb = keyboard.Keyboard()

if not available_keyboards:
    print("[Warning] No keyboard devices detected by PsychoPy; response collection may fail.")
else:
    print("Detected keyboard devices:")
    for idx, name in enumerate(available_names):
        print(f"  {idx}: {name}")
    if participant_keyboard:
        print(f"Using participant response device: {participant_keyboard.name}")
    else:
        print("Using PsychoPy default keyboard backend for participant responses.")

for trial in trials:
    b_cm = trial["b_cm"]
    (
        x_left,
        x_right,
        y_coords,
        disparity_cm,
        disparity_angle,
        disparity_formula,
    ) = generate_rds(
        a_cm,
        b_cm,
        screen_distance_cm,
        interocular_distance_cm,
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

    for _ in range(max(1, stim_frames)):
        fix_left.draw()
        fix_right.draw()
        dots_left.draw()
        dots_right.draw()
        win_left.flip()
        win_right.flip()
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

    this_exp.nextEntry()

# === Cleanup ===
terminate_experiment()
