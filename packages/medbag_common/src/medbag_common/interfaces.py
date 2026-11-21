"""The methods each owner delivers (WBS 1.3, interface agreement).

Rules for every method:
  - Take data, return one of the models in medbag_common.types. No file paths, no printing,
    no global state.
  - Models and clients (YOLO26n, DINOv2, Gemini) are loaded once by the server and passed in.
  - Never raise for a bad photo: return the "could not" value written in each docstring.
  - Holding a compartment, clearing a hold and sending alerts are the server's decisions;
    the methods only return results.

Each owner's package exposes these exact names, e.g. `from prep import rectify`.
The server's pipelines.py calls them in the order shown in the Demo Flow diagram.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Protocol

import numpy as np

from .types import (
    Answer,
    CellId,
    CheckResult,
    DoseRef,
    FillResult,
    Fingerprint,
    LabelResult,
    LogEntry,
    Match,
    Action,
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
        """Tray photo -> TrayView with 28 compartment crops, or None if any marker is missing.

        Pipelines 2 and 3 (SP3, SP4, SP6). Uses ArUco ids 0-3 on the tray sheet corners.
        """


class ChangedCells(Protocol):
    def __call__(self, before: TrayView, after: TrayView) -> list[CellId]:
        """Compartments that changed between two straightened photos.

        Pipeline 3 bottom row (SP6). Ignores small shifts in position and light (FR-C-13).
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
    def __call__(self, cell_img: np.ndarray, cell: CellId, model: Any) -> list[Pill]:
        """One compartment crop -> the pills in it (YOLO26n, one class: pill).

        Pipelines 2 and 3. `model` is the YOLO26n model the server loaded at start-up.
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
    def __call__(self, crop: np.ndarray, mm_per_px: float, dino: Any = None) -> Fingerprint:
        """Pill crop -> colour, size in mm and shape (optionally DINOv2 embedding)."""


class Identify(Protocol):
    def __call__(
        self, cell_img: np.ndarray, pill: Pill, mm_per_px: float, refs: list[RefPhoto]
    ) -> Match:
        """One detected pill -> which medicine, with sure, unsure or no_match.

        Pipeline 3 (SP4, SP6). Compares the pill's fingerprint with her reference photos.
        """


class MatchFill(Protocol):
    def __call__(
        self,
        view: TrayView,
        pills: dict[CellId, list[Pill]],
        schedule: Schedule,
        refs: Optional[list[RefPhoto]] = None,
    ) -> FillResult:
        """Fill check of all 28 compartments (Pipeline 2, SP3).

        Compares with the schedule and the label's appearance (and with refs on refills),
        compares the same medicine across days, warns about look-alikes and fills
        refs_to_save. Nothing is saved until the family confirms the grid.
        """


class CheckTray(Protocol):
    def __call__(
        self, view: TrayView, pills: list[Pill], dose: DoseRef, schedule: Schedule, refs: list[RefPhoto]
    ) -> FillResult:
        """Pre-dose check of the due compartment, lid closed (Pipeline 3 top row, SP4).

        Returns one CellStatus for dose.cell: ok, wrong, missing, extra, unsure or empty.
        The server puts the dose on hold for wrong, extra, unsure or empty.
        """


class CheckDose(Protocol):
    def __call__(
        self,
        dose: DoseRef,
        before: dict[CellId, list[Match]],
        after: dict[CellId, list[Match]],
        changed: list[CellId],
        schedule: Schedule,
    ) -> CheckResult:
        """Dose check after the lid closes (Pipeline 3 bottom row, SP6).

        taken = before minus after in the due compartment. Any changed cell other than
        dose.cell goes into other_changed_cells. An unsure pill gives result = unsure.
        """


class AlertRules(Protocol):
    def __call__(
        self, log: list[LogEntry], sim_time: datetime, settings: Settings
    ) -> list[Action]:
        """Dose log and the simulator's time -> what to do now (Pipeline 4, SP7).

        Second reminder after 15 min, family alert after 30 min, wrong pill not put back
        after 2 min, missed at the next dose time. Nothing while a dose is on hold.
        Each action once: skip one that is already in the log.
        """
