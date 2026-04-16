#!/usr/bin/env python3
"""
NiteCrawler Focuser GUI — PyQt5
"""

import sys, os, subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator

NCRAW_CMD = os.environ.get("NCRAW_CMD", "ncraw")

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

    def __init__(self, axis=None, value=None):
        super().__init__()
        self.axis  = axis
        self.value = value

    def run(self):
        if self.axis and self.value is not None:
            ok, out = run_ncraw(self.axis, self.value)
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

            setattr(self, f"_{suffix}_disp",  disp)
            setattr(self, f"_{suffix}_entry", entry)

            btn.clicked.connect(lambda _, c=cmd, e=entry: self._goto(c, e))
            entry.returnPressed.connect(lambda c=cmd, e=entry: self._goto(c, e))

        line2 = QFrame(); line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("color: #aaaaaa;")
        root.addWidget(line2)

        # ── Status bar ────────────────────────────────────────────────────────
        self._status = QLabel("Querying…")
        self._status.setFont(QFont("Courier", 8))
        self._status.setStyleSheet("color: #555555;")
        self._status.setAlignment(Qt.AlignCenter)
        root.addWidget(self._status)

        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        self._worker = None
        self._run_worker()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _goto(self, axis, entry):
        val = entry.text().strip()
        if not val:
            self._set_status("Enter a step value first", "#cc7700")
            return
        self._run_worker(axis=axis, value=val)

    # ── Worker ────────────────────────────────────────────────────────────────

    def _run_worker(self, axis=None, value=None):
        self._set_status("Working…", "#cc7700")
        self._worker = Worker(axis, value)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
