# TG12413-style Zener Limiter - Authentic Rack Face (source v1.1)

A Windows x64 VST3 JUCE/CMake project using the **unchanged provided fast zener limiter DSP**, packaged with a new two-channel, physical-hardware-style EMI TG12413 Zener Limiter rack GUI.

**Status:** seven standalone DSP tests pass; the JUCE/VST3 assembly has not yet been compiled on Windows. The included front-panel image is a composite preview made from the **same bundled faceplate and control PNG assets**, not a DAW screenshot.

## Front panel

The UI uses the **rackmount stereo TG12413/Zener Limiter physical design** as the visual reference: matte blue-grey faceplate, black square meters (with live GR needles), red INPUT and OUTPUT chicken-head control caps, a blue-grey six-position RECOVERY cap on each side, center EMI TG12413 styling, two small white hardware pushbuttons, knee toggle, rack ears/screw hardware, and condensed gold/white silkscreen labels. The COMP/LIMIT mode switch is completely absent because the DSP is permanently in limit mode.

Everything moving on screen is a real clickable JUCE control, not a static image. The audio has **independent L/R detectors but linked parameter settings** in the user-provided implementation; the two sets of panel knobs intentionally modify the same global JUCE parameter. There is **no variable attack, sidechain filter or stereo-linking algorithm** in the provided DSP, so this release does not show pretend variable controls for them. The original TG12413/Zener hardware has features beyond those provided in this plugin; this is a high-fidelity *visual adaptation*, not a 1:1 original-hardware control-for-control recreation or a licensed product.

### Functional controls

- **INPUT:** -18 to +18 dB, 101 positions, shared across L/R.
- **OUTPUT:** -24 to +24 dB, 101 positions, shared across L/R.
- **RECOVERY:** 6 steps, 0.05/0.10/0.25/0.5/1.0/2.0 s, shared across L/R.
- **CELL:** white center pushbutton; enables/disables the measured K2-K20 harmonic cell, with compression always operating.
- **IN:** white center pushbutton; 5ms-smoothed bypass (engages both channels).
- **KNEE:** mechanical-looking center toggle; sharp or soft knee.
- **Two 0-20 dB meters:** each displays its channel's independently detected gain reduction.

**Not adjustable:** attack 8 ms, nominal 8:1 limiting law, crest hold 13 ms. The *gold number scales* follow TG-style numbering; the input/output popup tooltips describe the actual DSP values.

## Build VST3 with GitHub Actions

1. Create a GitHub repository and upload **all files/folders** in this source ZIP to its root, including `.github`, `Assets`, `Source`, and `reference`.
2. Push to `main`, or select **Actions -> Windows x64 VST3 -> Run workflow**.
3. When successful, download the workflow artifact `TG-Zener-Rack-Windows-x64-VST3`.
4. Extract the VST3 bundle under `C:\Program Files\Common Files\VST3` and rescan in your DAW.

Build requires an internet-enabled Windows runner and JUCE **8.0.17-security**, fetched by CMake. The packaged PNG images are **embedded by juce_add_binary_data**; no adjacent resource files are necessary once compiled. Building locally needs Visual Studio 2022 C++, CMake and Git. The JUCE licensing terms apply.

## Regenerating GUI artwork

The committed PNG assets are already generated; CI needs no Python. To modify them locally on a machine with Python Pillow and NumPy, execute `python tools/generate_gui_assets.py`. The script constructs the entire front panel and photographic lighting effects from drawn shapes. It embeds **no downloaded product photos** or third-party artwork. Lato and DejaVu fonts are only used locally to render lettering into the asset, and are **not shipped**.

## Audio-data provenance and test status

The DSP is the user's supplied `TG_Zener_Limiter_Actual_DSP_4Freq_101Steps_CodingAI(1).zip`. The original 2,253,704 byte K2-K20 measurement/harmonic table and existing DSP code were preserved. The table is stored in the binary and loaded once, outside the audio thread. No oversampling or unvalidated analog-circuit claims were added.

- Linux C++17 test suite: `basic`, `controls`, `program`, `autotrack`, `detector_clean`, `spectra`, and `embedded_memory`: **PASSED (Nov 11, 2026)**.
- JUCE Windows VST3 GUI build: **not run**, because no GitHub repository was accessible through the account at the time of packaging.

This independent recreation is not affiliated with or endorsed by EMI, Chandler Limited, or Abbey Road.
