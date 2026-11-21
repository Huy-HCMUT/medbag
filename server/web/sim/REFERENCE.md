# Old simulator (reference only)

The first simulator is a single HTML page on claude.ai: <https://claude.ai/artifact/Db5mZFLwPTek8aGdThcEej>.
It draws the tray and lets you click pills; it does not use photos and does not match the current flowcharts.
Use it as a reference for the scripted lines and controls, not as the starting code.

## The new simulator is photo-based

The main view is the **camera view**: a real test photo of the paper tray, straightened by the server.
Only what a photo cannot show is drawn on top of it.

```
┌───────────────── Bag simulator ─────────────────┐
│  Mon 12:30   [Lid: closed]   face   speaker line │
│ ┌──────── camera view = real tray photo ───────┐ │
│ │  straightened photo of the paper tray        │ │
│ │  + orange border on the due compartment      │ │  drawn on top, using
│ │  + lock icons on the other compartments      │ │  cell_boxes from rectify
│ │  + YOLO boxes and the result after a check   │ │
│ └──────────────────────────────────────────────┘ │
│  Scene: [Takes correct pills] [Takes wrong pill] │  the presenter picks what
│         [Leaves one] [Does nothing] [Big button] │  happens; no clicking pills
└──────────────────────────────────────────────────┘
```

One dose:
1. At the dose time the simulator sends the **before** photo (lid closed) to `POST /api/tray` (pre-dose check). The due compartment lights up, or the dose is held.
2. The presenter picks a scene. The simulator sends the matching **after** photo to `POST /api/check`.
3. It shows the after photo with the server's boxes, speaks the result and changes the face.

Which photo goes with which dose and scene comes from `data/manifest.json` (WBS 2.4).
A dose with no photos in the manifest falls back to click mode and says so on screen.

## Worth reusing from the old page

- The scripted lines in English and 中文, and reading them aloud with `speechSynthesis` (FR-V-01, V-06, V-09).
- The own clock with pause and speed, the scenarios and "jump to day" (FR-B-02, B-04).
- The alert list with "Mark handled".
- The drawn tray and clickable pills, only as the click-mode fallback (FR-B-08).

## Must change to match the flowcharts and FR v2

| Old simulator | Now (flowchart · FR) |
|---|---|
| Drawn tray; you click pills out; the page decides the result | **Photo mode**: real before/after photos from `manifest.json`, results from the server; click mode only as a fallback after 5 s (FR-B-05, B-08) |
| Extra or missing pill before a dose is only spoken; the compartment still opens | Wrong, extra, unsure pill or empty compartment puts the dose **on hold**: stays locked, "please wait", family clears it (SP4, SP5, SP9 · FR-C-02) |
| Dose marked **missed after 30 min** | Family alert after 30 min; missed only when the **next dose** starts; taken later = "taken late" (SP7 · FR-C-10) |
| Fill check is simulated; "Fix mistakes" fixes everything | **Guided filling** one medicine at a time, fill check from the server on a full-tray photo, reference photos saved after the family confirms (SP2, SP3 · FR-P-09, P-12) |
| Family app is on the same page | Family app is its own page on the phone (`/family`) |
| Dose times and delays are fixed in the code | Read from the server, `GET /api/settings` (FR-F-11) |
| No unsure pill, no change in another compartment, no refill | Unsure → family confirms (SP9), other-compartment change → alert (FR-C-13), refill (FR-P-15, Should) |
| No big button, no face screen, no voice questions | Big button repeats the last line (Must, FR-V-03); face screen and voice questions are Should |
| Loads Google Fonts from the internet | Bundle the fonts or use system fonts, so the dose path runs offline (FR-S-03) |
