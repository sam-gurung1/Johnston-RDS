# Johnston (1991) Stereo Shape Distortion RDS Experiment — FINAL HAPLOSCOPE VERSION
# Run this version on dual-screen stereo haploscope setup

from psychopy import visual, event, core, gui
import numpy as np
import csv
import os
from datetime import datetime

# === Participant Info Dialog ===
dlg = gui.Dlg(title="Participant Info")
dlg.addField("Participant ID:")
dlg.addField("Session:", 1)
dlg.show()
if not dlg.OK:
    core.quit()

participant_id = dlg.data[0]
session_num = dlg.data[1]

# === File Setup ===
time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"data/{participant_id}_session{session_num}_{time_str}.csv"
os.makedirs("data", exist_ok=True)

csv_file = open(filename, mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['trial', 'b_cm', 'response', 'key', 'timestamp'])

# === Experiment Configuration ===
screen_distance_cm = 107           # Distance from eye to monitor
interocular_distance_cm = 6.5      # Average IPD in cm
monitor_res_px = (1920, 1080)      # Adjust if needed for external monitors

# === Stereo Window Setup (left = screen 1, right = screen 2) ===
win_left = visual.Window(
    size=monitor_res_px, screen=1, fullscr=True, units="cm", color=[-1, -1, -1],
    winType='pyglet', allowGUI=False, monitor='testMonitor', pos=(0, 0)
)
win_right = visual.Window(
    size=monitor_res_px, screen=2, fullscr=True, units="cm", color=[-1, -1, -1],
    winType='pyglet', allowGUI=False, monitor='testMonitor', pos=(0, 0)
)

# === Cylinder Parameters ===
a_cm = 5.0
b_values_cm = [3.35, 5.0, 6.65, 8.3, 9.95]  # Ellipse depths
stim_size_cm = 8.0
n_dots = 1500
stim_duration = 1.5

# === Functions ===
def compute_disparity(z_cm, D_cm, iod_cm):
    return (iod_cm * z_cm) / (D_cm**2 - z_cm**2 + 1e-9)

def generate_rds(a_cm, b_cm, D_cm, iod_cm, n_dots):
    x = np.random.uniform(-a_cm, a_cm, size=n_dots)
    y = np.random.uniform(-a_cm, a_cm, size=n_dots)
    z = b_cm * np.sqrt(1 - (x / a_cm)**2)
    z[np.isnan(z)] = 0
    disparity_cm = compute_disparity(z, D_cm, iod_cm)
    x_left = x - (disparity_cm / 2)
    x_right = x + (disparity_cm / 2)
    return x_left, x_right, y

# === Fixation Crosses ===
fix_left = visual.TextStim(win_left, text='+', pos=(0, 0), height=0.5, color='white')
fix_right = visual.TextStim(win_right, text='+', pos=(0, 0), height=0.5, color='white')

# === Trials ===
trials = b_values_cm * 3  # Repeat each b value 3 times
np.random.shuffle(trials)
clock = core.Clock()

for i, b_cm in enumerate(trials):
    xL, xR, y = generate_rds(a_cm, b_cm, screen_distance_cm, interocular_distance_cm, n_dots)

    dots_left = visual.ElementArrayStim(win_left, nElements=n_dots, elementTex=None, elementMask='circle',
                                        xys=np.column_stack((xL, y)), sizes=0.15, colors='white')
    dots_right = visual.ElementArrayStim(win_right, nElements=n_dots, elementTex=None, elementMask='circle',
                                         xys=np.column_stack((xR, y)), sizes=0.15, colors='white')

    # Present stimulus with fixation
    fix_left.draw()
    fix_right.draw()
    dots_left.draw()
    dots_right.draw()
    win_left.flip()
    win_right.flip()
    core.wait(stim_duration)

    # Response prompt
    prompt = 'Was the cylinder:\n[1] Squashed\n[2] Stretched'
    qL = visual.TextStim(win_left, text=prompt, pos=(0, -5), height=0.7, color='white')
    qR = visual.TextStim(win_right, text=prompt, pos=(0, -5), height=0.7, color='white')
    qL.draw()
    qR.draw()
    win_left.flip()
    win_right.flip()
    clock.reset()

    keys = event.waitKeys(keyList=['1', '2', 'escape'])
    if 'escape' in keys:
        break

    response = 'squashed' if keys[0] == '1' else 'stretched'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    csv_writer.writerow([i+1, b_cm, response, keys[0], timestamp])
    csv_file.flush()

# === Cleanup ===
csv_file.close()
win_left.close()
win_right.close()
core.quit()
