# Johnston Random-Dot Stereogram (RDS) Experiment

This repository contains a PsychoPy experiment that recreates Johnston's (1991) stereo shape distortion task for a mirror-based haploscope. The goal of this README is to explain everything so you can set up, run, and modify the script even if you have limited coding or PsychoPy experience.

---

## 1. What this experiment does

- Presents a set of 3D random-dot cylinders to the left and right eyes using two monitors mounted in a haploscope.
- Lets the participant decide whether each cylinder looks **"pushed out"** (convex) or **"caved in"** (concave).
- Records the participant's responses so you can analyze stereo perception accuracy later.
- Includes alignment helpers (nonius bars and a "fusion prime") to make it easier to fuse the stereo images.

---

## 2. What you need before you start

1. **Hardware**
   - Two monitors, ideally the same make and model, connected to your computer.
   - A haploscope rig with mirrors that direct each monitor to one eye.
   - A standard keyboard that the participant can use for responses.

2. **Software**
   - [PsychoPy](https://www.psychopy.org/) 2023.2 or newer. Install it via the standalone app or `pip install psychopy` in a Python 3.8+ environment.
   - Graphics drivers that support OpenGL (all modern GPUs do).

3. **Repository files**
   - `JohnstonRDSFINAL.py`: the main experiment script you will run.
   - `CODE_WALKTHROUGH.md`: an in-depth explanation of the code for advanced reference.
   - `README.md` (this file): the quick-start guide.

---

## 3. Folder layout

```
Johnston-RDS/
├── JohnstonRDSFINAL.py      # experiment script to run in PsychoPy
├── CODE_WALKTHROUGH.md      # detailed explanation of every part of the script
├── REVIEW.md                # design review notes
└── README.md                # beginner-friendly setup and usage guide
```

When you run the experiment, PsychoPy will automatically create a `data/` folder in the same directory to store your results.

---

## 4. How to launch the experiment

1. **Open PsychoPy** and choose the **Coder** view (looks like a text editor).
2. Use **File → Open...** to load `JohnstonRDSFINAL.py` from this repository.
3. Double-check that both haploscope monitors are connected and powered on.
4. Press the green **Run** button (or press `Ctrl` + `R`). PsychoPy will prompt you with a dialog asking for:
   - Participant ID (any label you like, e.g., `P001`).
   - Session number (start with `1`).
   - Physical measurements like screen distance and dot size. Defaults are provided; change them if you have measured different values.
5. Click **OK**. Two full-screen windows will open—one on each monitor. The script will handle hiding the mouse and aligning the stimuli.
6. Follow the on-screen instructions. Participants respond using the keyboard keys that appear in the prompt (by default, left arrow for "concave" and right arrow for "convex").
7. At the end of the session, press the `Esc` key once to exit cleanly. PsychoPy saves the data to the `data/` folder using the participant ID and date.

---

## 5. Key features explained simply

| Feature | Why it matters | How to change it |
| --- | --- | --- |
| **Test Mode** (`TEST_MODE = True`) | Shows a 10-second alignment stimulus when the script starts. | Set `TEST_MODE = False` near the top of the file once the haploscope is calibrated. |
| **Dynamic Random Dots** (`DYNAMIC_RDS`) | Adds new dot patterns every frame, which can be harder on your GPU. | Keep `False` for beginners. Switch to `True` only if you need a fully dynamic stimulus. |
| **Fusion Prime** (`FUSION_PRIME_SEC`) | Shows zero-disparity noise before each trial so participants can align their eyes. | Increase the seconds if participants need more time; reduce if they are already well trained. |
| **Haploscope Offset** (`haploscope_offset_cm`) | Shifts the left/right images horizontally to match the mirrors. | Adjust in the opening dialog by small amounts (±0.1 cm) if nonius bars do not overlap. |
| **Dot Size** (`dot_size_cm`) | Bigger dots are easier to fuse; smaller dots look sharper. | Set in the opening dialog. |

---

## 6. Understanding the workflow 

1. **Configuration & dialog**: The script asks for participant and hardware information, then stores it in a data handler.
2. **Window setup**: PsychoPy opens a right-eye window first and then a left-eye window. Both use centimeter units so the geometry math is straightforward.
3. **Alignment helpers**: If `TEST_MODE` is on, you see nonius lines and a practice cylinder to make sure fusion is correct.
4. **Trial loop**: For each cylinder width (`b` value), the script:
   - Generates random-dot patterns for the left and right eyes.
   - Presents a fusion prime (optional) to help the eyes lock together.
   - Shows the actual stimulus for ~1.5 seconds.
   - Collects a keyboard response and stores it in the data handler.
5. **Cleanup**: When the experiment finishes or you press `Esc`, the script saves data files (`.csv` and `.psydat`) and closes both windows safely.

If you want more detail, open `CODE_WALKTHROUGH.md`. It explains each function, variable, and flowchart in a lot more depth.

---

## 7. Troubleshooting tips

- **The two monitors look swapped**: Switch `RIGHT_SCREEN_INDEX` and `LEFT_SCREEN_INDEX` near the top of `JohnstonRDSFINAL.py`.
- **The cylinders look inside-out**: Swap the response keys or reverse the sign of the cylinder depth in the stimulus generation section.
- **My GPU struggles with dynamic dots**: Leave `DYNAMIC_RDS = False` or reduce `DYNAMIC_RDS_BANK_SIZE`.
- **Participants see double images**: Increase `haploscope_offset_cm` in the dialog in steps of 0.1 cm until the nonius bars overlap.

---

## 8. Next steps for learning

- Skim through `CODE_WALKTHROUGH.md` while keeping this README nearby for reference.
- Read the inline comments inside `JohnstonRDSFINAL.py`; they explain why each configuration option and helper function exists.
- Try changing one value at a time (for example, `stim_duration_s` or `n_dots`), then rerun the script to see how the stimulus changes.

You now have everything you need to run the Johnston RDS experiment and start exploring stereo perception on your haploscope. Happy experimenting!
