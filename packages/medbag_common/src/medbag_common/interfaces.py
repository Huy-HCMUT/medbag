"""The functions each person delivers: the interface agreement (WBS 1.3).

Rules for every function:
  - Take data, return one of the models in medbag_common.types. No file paths, no printing,
    no global state.
  - Models and clients (YOLO26n, DINOv2, Gemini) are loaded once by the server and passed in.
  - Never raise for a bad photo: return the "could not" value written in each docstring.
  - Holding a compartment, clearing a hold and sending alerts are the server's decisions;
    the functions only return results.

Each person's package exposes these exact names, e.g. `from prep import rectify`.
server/src/medbag_server/pipelines.py shows the order in which the server calls them.

Coordinates: a Pill's box is in pixels of the straightened tray image (TrayView.image), and
TrayView.cell_boxes says which compartment each region is. All photos are numpy BGR uint8.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Protocol

import numpy as np

from .types import (
    Action,
    Answer,
    CellId,
    CheckResult,
    DoseRef,
    FillResult,
    Fingerprint,
    LabelResult,
    LogEntry,
    Match,
    Pill,
    PreparedLabel,
    RefPhoto,
    Schedule,
    Settings,
    TrayView,
)

# =========================================================================== Joshua · prep


class PreprocessLabel(Protocol):
    def __call__(self, img: np.ndarray) -> PreparedLabel:
        """Label photo -> cropped, straightened label with the patient name blurred.

        Pipeline 1 (SP1). If no label is found or it is blurred, return found/sharp = False
        (the image may be the input photo); the app then asks for a new photo.
        """


class Rectify(Protocol):
    def __call__(self, img: np.ndarray) -> Optional[TrayView]:
        """Tray photo -> straightened TrayView with the 28 compartments, or None if a marker is missing.

        Pipelines 2 and 3 (SP3, SP4, SP6). Uses ArUco ids 0-3 on the tray sheet corners.
        cells[i] and cell_boxes[i] are compartment i (cell = day * 4 + slot).
        """


class ChangedCells(Protocol):
    def __call__(self, before: TrayView, after: TrayView) -> list[CellId]:
        """Compartments that changed between two straightened photos.

        Pipeline 3 after the dose (SP6). Ignores small shifts in position and light (FR-C-13).
        """


# =========================================================================== Sam · label


class ReadLabel(Protocol):
    def __call__(self, label: PreparedLabel, gemini: Any) -> LabelResult:
        """Prepared label -> LabelResult (Gemini first, Tesseract chi_tra as fallback).

        Pipeline 1 (SP1). `gemini` is the client the server made with its API key; it may be
        None when there is no internet. Use Tesseract when it is None, fails or returns
        something that is not the agreed JSON, and set engine = "tesseract" plus a
        fallback_used flag. Fill missing slots from the frequency, never overwrite slots
        read from ticks or icons.
        """


class CheckFields(Protocol):
    def __call__(self, result: LabelResult) -> LabelResult:
        """Same LabelResult with rule problems added to flags.

        Pipeline 1 (SP1). E.g. 每日 2 次 with 1 slot -> frequency_slots_mismatch;
        a missing field -> missing_field; 10 pills a time -> impossible_dose.
        """


# =========================================================================== Alex · pills, voice


class DetectPills(Protocol):
    def __call__(self, view: TrayView, model: Any) -> list[Pill]:
        """Straightened tray -> every pill on it, each with its compartment (YOLO26n, one class).

        Pipelines 2 and 3. Runs once on view.image (the same kind of picture as the training
        annotations in WBS 2.5) and gives each pill the compartment whose cell_box holds the
        box centre. `model` is the YOLO26n model the server loaded at start-up.
        """


class AnswerQuestion(Protocol):
    def __call__(
        self, question: str, schedule: Schedule, log: list[LogEntry], language: str, gemini: Any
    ) -> Answer:
        """Spoken question -> answer text, only from her schedule and log (Should, SP8).

        Return fallback = True with the scripted line when Gemini is None, slow (5 s) or the
        answer fails the keyword safety check (dose, extra, stop ...).
        """


# =========================================================================== Emily · check, alerts


class FingerprintPill(Protocol):
    def __call__(self, view: TrayView, pill: Pill, dino: Any = None) -> Fingerprint:
        """One pill -> colour, size in mm and shape (optionally a DINOv2 embedding).

        Used inside identify and match_fill; the server does not call it.
        """


class Identify(Protocol):
    def __call__(self, view: TrayView, pill: Pill, refs: list[RefPhoto]) -> Match:
        """One pill -> which medicine it is, with sure, unsure or no_match.

        Pipeline 3 (SP4, SP6). Compares the pill's fingerprint with her reference photos.
        """


class MatchFill(Protocol):
    def __call__(
        self,
        view: TrayView,
        pills: list[Pill],
        schedule: Schedule,
        refs: Optional[list[RefPhoto]] = None,
    ) -> FillResult:
        """Fill check of all 28 compartments right after filling (Pipeline 2, SP3).

        There are no reference photos yet on the first fill, so it compares with the schedule
        and the label's appearance (and with refs on a refill), compares the same medicine
        across days, warns about look-alikes and fills refs_to_save. Nothing is saved until
        the family confirms the grid.
        """


class CheckTray(Protocol):
    def __call__(self, dose: DoseRef, matches: list[Match], schedule: Schedule) -> FillResult:
        """Pre-dose check of the due compartment, lid closed (Pipeline 3 before the dose, SP4).

        `matches` = identify() for every pill in dose.cell. Returns one CellStatus for
        dose.cell: ok, wrong, missing, extra, unsure or empty. The server holds the dose for
        wrong, extra, unsure or empty.
        """


class CheckDose(Protocol):
    def __call__(
        self,
        dose: DoseRef,
        before: list[Match],
        after: list[Match],
        changed: list[CellId],
        schedule: Schedule,
    ) -> CheckResult:
        """Dose check after the lid closes (Pipeline 3 after the dose, SP6).

        `before` / `after` = identify() for every pill in the changed compartments, in the
        before and after photos. taken = before minus after in dose.cell. Any changed cell
        other than dose.cell goes into other_changed_cells. An unsure pill gives result = unsure.
        """


class AlertRules(Protocol):
    def __call__(self, log: list[LogEntry], sim_time: datetime, settings: Settings) -> list[Action]:
        """Dose log and the simulator's time -> what the server should do now (Pipeline 4, SP7).

        Second reminder after 15 min, family alert after 30 min, wrong pill not put back
        after 2 min, missed at the next dose time. Nothing while a dose is on hold.
        Each action once: skip one that is already in the log.
        """
