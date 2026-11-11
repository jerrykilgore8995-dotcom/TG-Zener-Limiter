# Local verification, TG12413-style panel v1.1

- Nov 11 2026: Standalone DSP suite via `tools-test.sh` passed seven tests: `basic`, `controls`, `program`, `autotrack`, `detector_clean`, `spectra`, `embedded_memory`.
- The GUI was visually inspected using the included `GUI_TG12413_Authentic_Preview.png`, generated from the same faceplate/knob assets bundled into the JUCE project.
- The new GUI uses dual linked parameter attachments and two independent meters. C++ GUI compilation was **not** run in the local sandbox, because it has no JUCE framework/toolchain. Compile with the Windows GitHub Actions workflow to validate integration and catch any compile errors.
- No compression/limiter mode switch; core is always set to limiting.
