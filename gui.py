#!/usr/bin/env python3
"""
NiteCrawler Focuser GUI — PyQt5
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIntValidator

NCRAW_CMD = os.environ.get("NCRAW_CMD", "ncraw")

STATE_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    / "ncraw" / "gui_state.json"
)

JOG_STEPS = [1, 10, 100, 1000]
DEFAULT_JOG_STEP = 100

# ── Serial comms ──────────────────────────────────────────────────────────────

def run_ncraw(*args):
    try:
        r = subprocess.run([NCRAW_CMD, *args], capture_output=True, text=True, timeout=6)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return False, f"'{NCRAW_CMD}' not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "Timeout — focuser not responding"

def parse_pos(output, axis):
    for line in output.splitlines():
        if axis.lower() in line.lower():
            for tok in reversed(line.split()):
                if tok.lstrip("-").isdigit():
                    return tok
    s = output.strip()
    return s if s.lstrip("-").isdigit() else "—"


# ── Background worker ─────────────────────────────────────────────────────────

class Worker(QThread):
    done = pyqtSignal(bool, str, str)

    def __init__(self, action_args=None):
        super().__init__()
        # action_args: tuple/list of args to pass to `ncraw` before polling, or None
        self.action_args = tuple(action_args) if action_args else None

    def run(self):
        if self.action_args:
            ok, out = run_ncraw(*self.action_args)
            if not ok:
                self.done.emit(False, out, "")
                return
        ok_f, out_f = run_ncraw("where", "focus")
        ok_r, out_r = run_ncraw("where", "rotation")
        foc = parse_pos(out_f, "Focus")    if ok_f else f"err: {out_f}"
        rot = parse_pos(out_r, "Rotation") if ok_r else f"err: {out_r}"
        self.done.emit(ok_f and ok_r, foc, rot)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NiteCrawler")
        self.setStyleSheet("""
            QWidget            { background: #f0f0f0; color: #1a1a1a; }
            QLabel             { color: #1a1a1a; }
            QLineEdit          { background: #ffffff; color: #1a1a1a;
                                 border: 1px solid #aaaaaa; padding: 4px 8px; }
            QPushButton        { background: #e0e0e0; color: #1a1a1a;
                                 border: 1px solid #aaaaaa; padding: 6px 16px; }
            QPushButton:hover  { background: #d0d0d0; }
            QPushButton:pressed{ background: #bbbbbb; }
            QComboBox          { background: #ffffff; color: #1a1a1a;
                                 border: 1px solid #aaaaaa; padding: 3px 6px; }
            QComboBox QAbstractItemView { background: #ffffff; color: #1a1a1a;
                                          selection-background-color: #d0d0d0; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Title ─────────────────────────────────────────────────────────────
        title = QLabel("NITECRAWLER Focuser/Rotator GUI")
        title.setFont(QFont("Courier", 13, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #cc2200;")
        root.addWidget(title)

        line = QFrame(); line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #aaaaaa;")
        root.addWidget(line)

        # ── Axis grid ─────────────────────────────────────────────────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(32)
        grid.setVerticalSpacing(8)
        root.addLayout(grid)

        axes = [("FOCUSER",  "foc", "#cc2200", "focus"),
                ("ROTATION", "rot", "#cc2200", "rotate")]

        for col, (name, suffix, color, cmd) in enumerate(axes):
            # heading
            lbl = QLabel(name)
            lbl.setFont(QFont("Courier", 9, QFont.Bold))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #555555;")
            grid.addWidget(lbl, 0, col)

            # position display
            disp = QLineEdit("—")
            disp.setReadOnly(True)
            disp.setAlignment(Qt.AlignRight)
            disp.setFont(QFont("Courier", 26, QFont.Bold))
            disp.setFixedWidth(180)
            disp.setStyleSheet(f"background: #ffffff; color: {color}; "
                               "border: 1px solid #aaaaaa; padding: 4px 8px;")
            grid.addWidget(disp, 1, col)

            # "set position" label
            setlbl = QLabel("SET POSITION")
            setlbl.setFont(QFont("Courier", 7))
            setlbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(setlbl, 2, col)

            # entry + goto (with stretch between them)
            row = QHBoxLayout()
            row.setSpacing(6)
            entry = QLineEdit()
            entry.setPlaceholderText("steps")
            entry.setAlignment(Qt.AlignRight)
            entry.setValidator(QIntValidator(-999999, 999999))
            entry.setFont(QFont("Courier", 13, QFont.Bold))
            entry.setFixedWidth(120)
            btn = QPushButton("GO")
            btn.setFont(QFont("Courier", 9, QFont.Bold))
            btn.setFixedWidth(60)
            row.addWidget(entry)
            row.addStretch()
            row.addWidget(btn)
            grid.addLayout(row, 3, col)

            # "jog" label
            joglbl = QLabel("JOG")
            joglbl.setFont(QFont("Courier", 7))
            joglbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(joglbl, 4, col)

            # jog row: [−] [step ▼] [+]
            jog_row = QHBoxLayout()
            jog_row.setSpacing(6)

            minus_btn = QPushButton("−")
            minus_btn.setFont(QFont("Courier", 13, QFont.Bold))
            minus_btn.setFixedWidth(40)

            step_combo = QComboBox()
            step_combo.setFont(QFont("Courier", 10, QFont.Bold))
            for s in JOG_STEPS:
                step_combo.addItem(str(s), s)
            default_idx = step_combo.findData(DEFAULT_JOG_STEP)
            if default_idx >= 0:
                step_combo.setCurrentIndex(default_idx)
            step_combo.setFixedWidth(80)

            plus_btn = QPushButton("+")
            plus_btn.setFont(QFont("Courier", 13, QFont.Bold))
            plus_btn.setFixedWidth(40)

            jog_row.addStretch()
            jog_row.addWidget(minus_btn)
            jog_row.addWidget(step_combo)
            jog_row.addWidget(plus_btn)
            jog_row.addStretch()
            grid.addLayout(jog_row, 5, col)

            setattr(self, f"_{suffix}_disp",  disp)
            setattr(self, f"_{suffix}_entry", entry)
            setattr(self, f"_{suffix}_step",  step_combo)

            btn.clicked.connect(lambda _, c=cmd, e=entry: self._goto(c, e))
            entry.returnPressed.connect(lambda c=cmd, e=entry: self._goto(c, e))
            minus_btn.clicked.connect(
                lambda _, c=cmd, sc=step_combo: self._jog(c, -int(sc.currentData()))
            )
            plus_btn.clicked.connect(
                lambda _, c=cmd, sc=step_combo: self._jog(c, +int(sc.currentData()))
            )

        line2 = QFrame(); line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("color: #aaaaaa;")
        root.addWidget(line2)

        # ── Status bar ────────────────────────────────────────────────────────
        self._status = QLabel("Querying…")
        self._status.setFont(QFont("Courier", 8))
        self._status.setStyleSheet("color: #555555;")
        self._status.setAlignment(Qt.AlignCenter)
        root.addWidget(self._status)

        # Restore persisted state before locking the size
        self._load_state()

        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        self._worker = None
        self._run_worker()

        # ── Polling timer (every 0.5 seconds) ───────────────────────────────
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start(500)  # refresh every 0.5 seconds

    # ── Actions ───────────────────────────────────────────────────────────────

    def _goto(self, axis, entry):
        val = entry.text().strip()
        if not val:
            self._set_status("Enter a step value first", "#cc7700")
            return
        self._run_worker((axis, val))

    def _jog(self, axis, delta):
        # axis is the GUI/CLI axis name ("focus" or "rotate"); the bash CLI
        # accepts "focus" / "rotation" / "rotate" via its axis() helper.
        self._run_worker(("jog", axis, str(delta)))

    # ── Worker ────────────────────────────────────────────────────────────────

    def _run_worker(self, action_args=None):
        self._worker = Worker(action_args)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success, foc, rot):
        if success:
            self._foc_disp.setText(foc)
            self._rot_disp.setText(rot)
            self._set_status(f"Focus: {foc}   Rotation: {rot}", "#227722")
        else:
            self._set_status(foc, "#cc2200")

    def _set_status(self, msg, color="#555555"):
        self._status.setText(msg)
        self._status.setStyleSheet(f"color: {color};")

    def _poll_status(self):
        # Avoid stacking workers if one is already running
        if self._worker is not None and self._worker.isRunning():
            return
        self._run_worker()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_state(self):
        try:
            with open(STATE_PATH) as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        foc_target = state.get("focus_target", "")
        rot_target = state.get("rotation_target", "")
        if isinstance(foc_target, (str, int)):
            self._foc_entry.setText(str(foc_target))
        if isinstance(rot_target, (str, int)):
            self._rot_entry.setText(str(rot_target))

        for suffix, key in (("foc", "focus_jog_step"), ("rot", "rotation_jog_step")):
            combo = getattr(self, f"_{suffix}_step", None)
            if combo is None:
                continue
            try:
                step = int(state.get(key, DEFAULT_JOG_STEP))
            except (TypeError, ValueError):
                continue
            idx = combo.findData(step)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _save_state(self):
        state = {
            "focus_target":      self._foc_entry.text().strip(),
            "rotation_target":   self._rot_entry.text().strip(),
            "focus_jog_step":    int(self._foc_step.currentData()),
            "rotation_jog_step": int(self._rot_step.currentData()),
        }
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_PATH, "w") as f:
                json.dump(state, f, indent=2)
        except OSError:
            pass

    def closeEvent(self, event):
        self._save_state()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
