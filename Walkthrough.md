# Johnston RDS Haploscope Script Walkthrough

This document explains the full flow of `JohnstonRDSFINAL.py` so you can see how every
piece fits together when you run the stereogram experiment on a haploscope. The script
is laid out top-to-bottom and executes sequentially, so the same ordering is used here.

## 1. Imports and metadata
```python
from psychopy import core, data, gui, monitors, visual
from psychopy.hardware import keyboard
import numpy as np
import os, math
```
PsychoPy modules provide timing (`core`), data storage (`data`), GUI prompts (`gui`),
monitor calibration (`monitors`), and drawing primitives (`visual`). The `keyboard`
module handles input for both the participant and the global escape shortcut. NumPy is
used for random sampling and geometry, while the standard library supplies filesystem
helpers and math constants.

## 2. Global rig configuration
A block of constants (`WIN_TYPE`, `RIGHT_SCREEN_INDEX`, `TEST_MODE`, etc.) holds
everything that is likely to change between setups. The values are read immediately when
the file executes, so editing them in the source file adjusts how the experiment starts.

Key fields:
- **Window indices** tell PsychoPy which physical screen drives each eye.
- **TEST_MODE** gates a calibration routine that shows nonius bars and a strong convex
  stimulus so you can verify the haploscope alignment before trials start.
- **Dynamic RDS controls** (e.g., `DYNAMIC_RDS`, `DYNAMIC_RDS_UPDATE_EVERY`) determine
  whether fresh noise is generated every frame or whether the stimulus stays static for
  the entire 1.5-second presentation.
- **Timing constants** like `POST_FIX_SEC` and `FUSION_PRIME_SEC` influence how long the
  fixation, prime, and post-stimulus pauses last.

Because these are module-level constants, they are evaluated only once during script
startup but referenced later wherever timing or rendering decisions are made.

## 3. Participant dialog and experiment handler
`exp_info` defines the fields the GUI dialog collects. PsychoPy automatically casts the
keys in this dictionary into editable form fields. `gui.DlgFromDict` shows the dialog and
returns control when the user confirms or cancels; cancelling exits via `core.quit()`.

After the dialog closes, the script stamps the run with a timestamp (`data.getDateStr`)
and an experiment name, then prepares an `ExperimentHandler`. This object writes trial
results to disk (`data/participant_date.csv` and `.psydat`) and stores the metadata that
will appear in the output files.

## 4. Monitor geometry
The dialog entries are converted from strings to floats. These values parameterize a
PsychoPy `Monitor` instance called `haplo_monitor`. It combines the physical panel width,
viewing distance, and pixel resolution (`monitor_res_px`) so PsychoPy can map centimetres
to pixels accurately when drawing stimuli.

The haploscope-specific calibration parameters (`haploscope_offset_cm`,
`haploscope_scale_x_left`, `haploscope_scale_x_right`) are also converted to floats. They
are used later to shift or stretch each eye’s view in the stereo windows.

## 5. Stereo windows
Two full-screen `visual.Window` objects are opened: right eye first, then left eye. Each
window:
- Uses centimetres as drawing units (`units="cm"`).
- Inherits the calibrated `haplo_monitor` so that geometric conversions stay consistent.
- Enables `waitBlanking` to synchronize draws with the monitor refresh.

A short `core.wait(0.2)` separates the window launches to avoid initialization races. The
cursor is hidden for both eyes, and per-eye stretch compensation is applied through
`viewScale`. Non-unity values here scale all subsequent drawing without recomputing the
stimulus coordinates.

## 6. Graceful termination helper
`terminate_experiment()` centralizes the shutdown logic. It saves the experiment data,
closes both windows, and quits PsychoPy. The `_experiment_terminated` flag ensures the
cleanup executes only once even if multiple escape signals fire.

This function is referenced throughout the script whenever an ESC key is detected so that
no matter when the participant quits, data and windows are handled cleanly.

## 7. Stimulus defaults and refresh probing
The next block sets stimulus geometry (`a_cm`, `b_values_cm`, `n_dots`, etc.). The refresh
rates of both windows are measured with `getActualFrameRate`. Depending on
`MEASURE_BOTH_REFRESH`, the right eye can either reuse the left eye’s measurement or
probe independently. The minimum refresh rate determines how many frames compose the
1.5-second stimulus (`stim_frames`).

## 8. Geometry helpers
### `project_to_screen`
Given a point on or near the cylinder surface (`x_cm`, `z_cm`), this function projects the
point onto each eye’s screen using a pinhole camera model. It returns the left/right
positions plus disparity in centimetres, radians, and the analytic disparity formula used
for logging.

### `generate_rds`
Creates the random-dot stereogram for a half-elliptical cylinder:
1. Samples random points inside a circular aperture.
2. Computes whether each point lies on the curved half-cylinder (`inside`).
3. Projects to each eye using `project_to_screen` and applies the haploscope offset (equal
   and opposite shifts) if supplied.
4. Keeps only dots visible to both eyes, concatenating batches until the requested number
   of dots (`n`) is reached.
5. Returns arrays of left/right x positions, shared y positions, and disparity statistics.

This function is used whenever the script needs dots for the fusion prime or the actual
trial stimulus.

## 9. Reusable drawables
The script constructs PsychoPy stimuli that are drawn repeatedly:
- Fixation cross (`TextStim`) for both eyes.
- Nonius lines (`Line`) that appear during calibration and the fusion prime.
- Response prompt text asking whether the cylinder looked squashed or stretched.
- Two keyboard listeners: `kb` for participant responses and `default_kb` dedicated to
  detecting ESC regardless of context.

## 10. Test mode calibration loop
If `TEST_MODE` is `True`, the script generates a strong convex cylinder and displays it
alongside the nonius bars for 10 seconds. During this time you can verify that depth
appears correct and that the nonius segments fuse into a single vertical line. Afterward,
the script waits for any keypress before proceeding to the actual trials. ESC at any time
runs `terminate_experiment()`.

## 11. Trial structure
`b_values_cm` defines five curvature levels. `TrialHandler` randomizes three repetitions
of each, so there are 15 trials total. For each trial the loop executes the following
sequence:

### a. Fusion prime
- `generate_rds` is called with `b=0` and `offset_cm=0.0` so both eyes receive identical
  coordinates (true zero disparity).
- `prime_frames` draws of the prime occur, showing fixation, nonius, and identical dot
  positions to lock vergence before the depth stimulus.

### b. Cylinder stimulus
- `regenerate_cylinder()` wraps `generate_rds` for the current `b` level.
- If `DYNAMIC_RDS` is enabled, a bank of pre-generated frames is created and cycled
  according to `DYNAMIC_RDS_UPDATE_EVERY`; otherwise a single static array is used.
- Two `ElementArrayStim` objects (`dotsL`, `dotsR`) draw the left/right dot positions each
  frame while the fixation cross remains visible.
- The loop runs for `stim_frames`, respecting escape checks.

### c. Post-fixation pause
A short fixation-only period (`POST_FIX_SEC`) gives participants time before answering.

### d. Response collection
The script clears the keyboard buffer and waits until the participant presses "1" or
"2". Reaction time (`k.rt`) is captured alongside the key. The response label is derived
from the key press ("squashed" vs. "stretched").

### e. Data logging
The trial’s curvature, response, reaction time, and disparity statistics are written to
the `TrialHandler`. When the loop ends, `this_exp.nextEntry()` commits the row so the
`ExperimentHandler` can export the results automatically.

## 12. Shutdown
After all trials, `terminate_experiment()` saves the data files and closes both windows.
This guarantees cleanup even if the loop exits normally.

---
With this walkthrough, you can trace how the script initializes the haploscope hardware,
prepares stereoscopic stimuli, guides the participant through calibration and trials, and
records the outcomes.
