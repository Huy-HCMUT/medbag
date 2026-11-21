# Old simulator (reference only)

The first simulator is a single HTML page on claude.ai: <https://claude.ai/artifact/Db5mZFLwPTek8aGdThcEej>.
It runs by itself in the browser with click mode only, and does not match the current flowcharts.
Use it as a reference for the look and the scripted lines, not as the starting code.

## Worth reusing

- The tray drawing: 7 × 4 grid, ArUco corner markers, lit / unlocked / locked compartments, lid cover.
- The pill shapes (white, orange, yellow capsule, blue) and the "in her hand" area.
- The scripted lines in English and 中文, and reading them aloud with `speechSynthesis` (FR-V-01, V-06, V-09).
- The own clock with pause and speed, the scenarios (normal week, filling mistake on Wednesday) and "jump to day" (FR-B-02, B-04).
- The alert list with "Mark handled".

## Must change to match the flowcharts and FR v2

| Old simulator | Now (flowchart · FR) |
|---|---|
| Extra or missing pill before a dose is only spoken; the compartment still opens | Wrong, extra, unsure pill or empty compartment puts the dose **on hold**: stays locked, "please wait", family clears it (SP4, SP5, SP9 · FR-C-02) |
| Dose marked **missed after 30 min** | Family alert after 30 min; missed only when the **next dose** starts; taken later = "taken late" (SP7 · FR-C-10) |
| You click pills out; the page decides the result | **Photo mode**: send the after photo to the server, show and speak its result; click mode only as a fallback after 5 s (FR-B-05, B-08) |
| Fill check is simulated; "Fix mistakes" fixes everything | **Guided filling** one medicine at a time, fill check from the server, reference photos saved after the family confirms (SP2, SP3 · FR-P-09, P-12) |
| Family app is on the same page | Family app is its own page on the phone (`/family`) |
| Dose times and delays are fixed in the code | Read from the server, `GET /api/settings` (FR-F-11) |
| No unsure pill, no change in another compartment, no refill | Unsure → family confirms (SP9), other-compartment change → alert (FR-C-13), refill (FR-P-15, Should) |
| No big button, no face screen, no voice questions | Big button repeats the last line (Must, FR-V-03); face screen and voice questions are Should |
| Loads Google Fonts from the internet | Bundle the fonts or use system fonts, so the dose path runs offline (FR-S-03) |
