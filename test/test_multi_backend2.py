#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manatools AUI backend smoke-test.

Tests Qt, GTK, NCurses, and Web backends with an identical widget layout:

  Heading
  Label (backend name)
  InputField "Username"
  InputField "Password"   (password mode)
  ComboBox   "Select option"
  CheckBox   "Enable features"
  ProgressBar "Progress"
  MultiLineEdit "Notes"
  DateField   "Date"
  RadioButtons Low / Medium / High  (inside an HBox)
  Frame  "Advanced"  → CheckBoxFrame inside
  HBox   OK | Cancel buttons
  Label  (status / last event)

Usage
-----
    python test_backends.py          # auto-detect all available backends
    python test_backends.py qt
    python test_backends.py gtk
    python test_backends.py ncurses
    python test_backends.py web      # serves on http://localhost:8080
"""

import os
import sys
import time

# Allow running from the examples/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _probe_backends() -> list[str]:
    """Return the names of all backends whose dependencies are satisfied."""
    available = []

    try:
        import PySide6.QtWidgets          # noqa: F401
        available.append("qt")
        print("✓ Qt backend available (PySide6)")
    except ImportError:
        print("✗ Qt backend not available (PySide6 required)")

    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk     # noqa: F401
        available.append("gtk")
        print("✓ GTK backend available (GTK4)")
    except (ImportError, ValueError) as e:
        print(f"✗ GTK backend not available: {e}")

    try:
        import curses                     # noqa: F401
        available.append("ncurses")
        print("✓ NCurses backend available")
    except ImportError as e:
        print(f"✗ NCurses backend not available: {e}")

    # Web backend: built-in http.server + threading — always available
    available.append("web")
    print("✓ Web backend available (built-in HTTP + WebSocket)")

    return available


# ---------------------------------------------------------------------------
# Web backend – standalone factory / dialog (no server stub needed here;
# the real YDialogWeb starts its own HTTP server when open() / waitForEvent()
# is called).  We implement a thin WebFactory that mirrors the factory API
# used by the other backends.
# ---------------------------------------------------------------------------

def _build_web_factory():
    """
    Import all web-backend widget classes and return a factory object whose
    createXxx() methods match the interface used by YUI_ui().widgetFactory().

    This avoids requiring the full manatools package to be installed; the
    widget modules are loaded directly from the package tree if it is on
    sys.path, or from the local uploads directory used during development.
    """
    try:
        # Production import path (package installed / on sys.path)
        from manatools.aui.backends.web.dialogweb      import YDialogWeb
        from manatools.aui.backends.web.hboxweb         import YHBoxWeb
        from manatools.aui.backends.web.labelweb        import YLabelWeb
        from manatools.aui.backends.web.pushbuttonweb   import YPushButtonWeb
        from manatools.aui.backends.web.inputfieldweb   import YInputFieldWeb
        from manatools.aui.backends.web.comboboxweb     import YComboBoxWeb
        from manatools.aui.backends.web.checkboxweb     import YCheckBoxWeb
        from manatools.aui.backends.web.checkboxframeweb import YCheckBoxFrameWeb
        from manatools.aui.backends.web.progressbarweb  import YProgressBarWeb
        from manatools.aui.backends.web.multilineditweb import YMultiLineEditWeb
        from manatools.aui.backends.web.datefieldweb    import YDateFieldWeb
        from manatools.aui.backends.web.radiobuttonweb  import YRadioButtonWeb
        from manatools.aui.backends.web.frameweb        import YFrameWeb
        from manatools.aui.backends.web.alignmentweb    import YAlignmentWeb
        from manatools.aui.backends.web.intfieldweb     import YIntFieldWeb
        from manatools.aui.backends.web.imageweb        import YImageWeb
        from manatools.aui.backends.web.dumbtabweb      import YDumbTabWeb
        from manatools.aui.backends.web.panedweb        import YPanedWeb
        from manatools.aui.backends.web.menubarweb      import YMenuBarWeb

    except ImportError as e:
        raise RuntimeError(
            f"Cannot import web backend widgets ({e}). "
            "Make sure the manatools package is on sys.path."
        ) from e

    class WebFactory:
        """
        Thin factory that mirrors the YWidgetFactory API used by the demo.
        Each createXxx() instantiates the corresponding web widget and wires
        it into the parent's children list (via the parent= kwarg that every
        web widget already accepts).
        """

        # ---- Dialogs -------------------------------------------------------

        def createMainDialog(self) -> YDialogWeb:
            return YDialogWeb()

        def createPopupDialog(self) -> YDialogWeb:
            from manatools.aui.yui_common import YDialogType
            return YDialogWeb(dialog_type=YDialogType.YPopupDialog)

        # ---- Layout --------------------------------------------------------

        def createVBox(self, parent):
            """VBox is rendered as a flex-column HBox variant."""
            box = YHBoxWeb(parent=parent)
            # Mark as vertical so CSS can style it appropriately
            box._is_vbox = True
            return box

        def createHBox(self, parent):
            return YHBoxWeb(parent=parent)

        # ---- Labels --------------------------------------------------------

        def createHeading(self, parent, text: str):
            return YLabelWeb(parent=parent, text=text, isHeading=True)

        def createLabel(self, parent, text: str):
            return YLabelWeb(parent=parent, text=text)

        def createOutputField(self, parent, text: str):
            return YLabelWeb(parent=parent, text=text, isOutputField=True)

        # ---- Input ---------------------------------------------------------

        def createInputField(self, parent, label: str, password_mode: bool = False):
            return YInputFieldWeb(parent=parent, label=label,
                                  password_mode=password_mode)

        def createMultiLineEdit(self, parent, label: str):
            return YMultiLineEditWeb(parent=parent, label=label)

        def createIntField(self, parent, label: str,
                           min_val: int = 0, max_val: int = 100,
                           initial: int = 0):
            return YIntFieldWeb(parent=parent, label=label,
                                minVal=min_val, maxVal=max_val,
                                initialVal=initial)

        def createDateField(self, parent, label: str):
            return YDateFieldWeb(parent=parent, label=label)

        # ---- Buttons -------------------------------------------------------

        def createPushButton(self, parent, label: str, icon_name=None,
                             icon_only: bool = False):
            return YPushButtonWeb(parent=parent, label=label,
                                  icon_name=icon_name, icon_only=icon_only)

        # ---- Selection widgets ---------------------------------------------

        def createComboBox(self, parent, label: str, editable: bool = False):
            return YComboBoxWeb(parent=parent, label=label, editable=editable)

        def createCheckBox(self, parent, label: str, checked: bool = False):
            return YCheckBoxWeb(parent=parent, label=label, is_checked=checked)

        def createCheckBoxFrame(self, parent, label: str, checked: bool = False):
            return YCheckBoxFrameWeb(parent=parent, label=label, checked=checked)

        def createRadioButton(self, parent, label: str, checked: bool = False):
            return YRadioButtonWeb(parent=parent, label=label,
                                   isChecked=checked)

        # ---- Progress / status ---------------------------------------------

        def createProgressBar(self, parent, label: str,
                              max_value: int = 100, initial: int = 0):
            w = YProgressBarWeb(parent=parent, label=label,
                                max_value=max_value)
            if initial:
                w.setValue(initial)
            return w

        # ---- Containers ----------------------------------------------------

        def createFrame(self, parent, label: str):
            return YFrameWeb(parent=parent, label=label)

        def createAlignment(self, parent, hor_align=None, vert_align=None):
            from manatools.aui.yui_common import YAlignmentType
            return YAlignmentWeb(
                parent=parent,
                horAlign=hor_align or YAlignmentType.YAlignUnchanged,
                vertAlign=vert_align or YAlignmentType.YAlignUnchanged,
            )

        # ---- Misc ----------------------------------------------------------

        def createImage(self, parent, filename: str):
            return YImageWeb(parent=parent, imageFileName=filename)

        def createDumbTab(self, parent):
            return YDumbTabWeb(parent=parent)

        def createPaned(self, parent, dimension=None):
            from manatools.aui.yui_common import YUIDimension
            return YPanedWeb(parent=parent,
                             dimension=dimension or YUIDimension.YD_HORIZ)

        def createMenuBar(self, parent):
            return YMenuBarWeb(parent=parent)

    return WebFactory()


# ---------------------------------------------------------------------------
# Shared dialog builder  – identical layout for every backend
# ---------------------------------------------------------------------------

def _build_dialog(factory, backend_name: str):
    """
    Build the complete widget tree using only factory calls.
    Returns a dict of named widgets so the event loop can inspect them.
    """
    dialog = factory.createMainDialog()
    vbox   = factory.createVBox(dialog)

    # ── Heading + info ──────────────────────────────────────────────────────
    factory.createHeading(vbox, f"manatools AUI — {backend_name.upper()} backend")
    factory.createLabel(vbox, "Fill in the form and click OK or Cancel.")

    # ── Text inputs ─────────────────────────────────────────────────────────
    username  = factory.createInputField(vbox, "&Username")
    password  = factory.createInputField(vbox, "&Password", True)

    # ── ComboBox ────────────────────────────────────────────────────────────
    combo = factory.createComboBox(vbox, "Select &option:", False)
    for opt in ("Option 1", "Option 2", "Option 3",
                "Option 4", "Option 5", "Option 6"):
        combo.addItem(opt)

    # ── CheckBox ────────────────────────────────────────────────────────────
    checkbox = factory.createCheckBox(vbox, "&Enable features")

    # ── Radio buttons (Low / Medium / High) ────────────────────────────────
    radio_box = factory.createHBox(vbox)
    factory.createLabel(radio_box, "Priority:")
    radio_low    = factory.createRadioButton(radio_box, "&Low",    True)
    radio_medium = factory.createRadioButton(radio_box, "&Medium", False)
    radio_high   = factory.createRadioButton(radio_box, "&High",   False)

    # ── ProgressBar ─────────────────────────────────────────────────────────
    progress = factory.createProgressBar(vbox, "Progress", 100, 35)

    # ── MultiLineEdit ───────────────────────────────────────────────────────
    notes = factory.createMultiLineEdit(vbox, "&Notes")
    notes.setValue("Enter any notes here.\nSupports multiple lines.")

    # ── DateField ───────────────────────────────────────────────────────────
    date_field = factory.createDateField(vbox, "&Date")

    # ── Frame with CheckBoxFrame inside ─────────────────────────────────────
    frame       = factory.createFrame(vbox, "Advanced &Options")
    cbframe     = factory.createCheckBoxFrame(frame, "&Enable advanced", False)
    adv_notes   = factory.createLabel(cbframe, "Advanced settings are disabled.")

    # ── Status label ────────────────────────────────────────────────────────
    status = factory.createLabel(vbox, "")

    # ── Buttons ─────────────────────────────────────────────────────────────
    hbox          = factory.createHBox(vbox)
    ok_button     = factory.createPushButton(hbox, "&OK")
    cancel_button = factory.createPushButton(hbox, "&Cancel")

    widgets = dict(
        dialog        = dialog,
        username      = username,
        password      = password,
        combo         = combo,
        checkbox      = checkbox,
        radio_low     = radio_low,
        radio_medium  = radio_medium,
        radio_high    = radio_high,
        progress      = progress,
        notes         = notes,
        date_field    = date_field,
        cbframe       = cbframe,
        status        = status,
        ok_button     = ok_button,
        cancel_button = cancel_button,
    )
    return widgets


# ---------------------------------------------------------------------------
# Event loop  – shared for all backends
# ---------------------------------------------------------------------------

def _run_event_loop(widgets, backend_name: str):
    """
    Drives waitForEvent() until the dialog is closed, updating the status
    label in response to each widget interaction.
    """
    import manatools.aui.yui_common as yui

    dialog        = widgets["dialog"]
    username      = widgets["username"]
    password      = widgets["password"]
    combo         = widgets["combo"]
    checkbox      = widgets["checkbox"]
    radio_low     = widgets["radio_low"]
    radio_medium  = widgets["radio_medium"]
    radio_high    = widgets["radio_high"]
    progress      = widgets["progress"]
    notes         = widgets["notes"]
    date_field    = widgets["date_field"]
    cbframe       = widgets["cbframe"]
    status        = widgets["status"]
    ok_button     = widgets["ok_button"]
    cancel_button = widgets["cancel_button"]

    while True:
        event = dialog.waitForEvent()
        typ   = event.eventType()

        if typ == yui.YEventType.CancelEvent:
            dialog.destroy()
            break

        if typ != yui.YEventType.WidgetEvent:
            continue

        wdg = event.widget()

        if wdg == cancel_button:
            status.setText("Cancelled.")
            dialog.destroy()
            break

        elif wdg == ok_button:
            # Collect all field values for summary
            radios = {
                radio_low:    "Low",
                radio_medium: "Medium",
                radio_high:   "High",
            }
            chosen_radio = next(
                (label for btn, label in radios.items() if btn.isChecked()),
                "none",
            )
            status.setText(
                f"OK — user='{username.value()}' "
                f"pwd='{password.value()}' "
                f"combo='{combo.value()}' "
                f"check={checkbox.isChecked()} "
                f"priority={chosen_radio} "
                f"date='{date_field.value()}'"
            )

        elif wdg == combo:
            status.setText(f"Combo → '{combo.value()}'")

        elif wdg == checkbox:
            status.setText(
                f"'{checkbox.label()}' → {'ON' if checkbox.isChecked() else 'OFF'}"
            )

        elif wdg == cbframe:
            state = "enabled" if cbframe.isChecked() else "disabled"
            status.setText(f"Advanced options {state}")

        elif wdg in (radio_low, radio_medium, radio_high):
            chosen = next(
                (lbl for btn, lbl in {
                    radio_low: "Low", radio_medium: "Medium",
                    radio_high: "High"
                }.items() if btn.isChecked()),
                "?",
            )
            status.setText(f"Priority → {chosen}")

        elif wdg == notes:
            # ValueChanged on the textarea
            status.setText(f"Notes updated ({len(notes.value())} chars)")

        elif wdg == date_field:
            status.setText(f"Date → '{date_field.value()}'")

        elif wdg == progress:
            status.setText(f"Progress → {progress.value()}%")

    print(f"[{backend_name}] Dialog closed.")


# ---------------------------------------------------------------------------
# Per-backend entry points
# ---------------------------------------------------------------------------

def test_web(port: int = 8080):
    """
    Run the demo using the pure-Python web backend.

    Opens the dialog (which starts an HTTP server), prints the URL, and
    blocks in waitForEvent() until the user clicks Cancel or closes the tab.
    """
    print(f"\n{'='*60}")
    print("Testing WEB backend")
    print(f"{'='*60}")

    try:
        factory = _build_web_factory()
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    widgets = _build_dialog(factory, "web")
    dialog  = widgets["dialog"]

    # Override the default port if needed
    if hasattr(dialog, '_server') and dialog._server:
        pass  # already started — shouldn't happen before open()
    # Inject the desired port before the server starts
    dialog._preferred_port = port

    print(f"\nOpening web dialog on http://localhost:{port}/")
    print("Open the URL in a browser, interact with the form,")
    print("then click Cancel (or close the tab) to exit.\n")

    # open() starts the HTTP + WebSocket server
    dialog.open()

    try:
        _run_event_loop(widgets, "web")
    except KeyboardInterrupt:
        print("\nInterrupted — destroying dialog.")
        try:
            dialog.destroy()
        except Exception:
            pass


def test_native(backend_name: str):
    """
    Run the demo using any of the native backends (qt / gtk / ncurses).
    Delegates to the YUI factory the same way the original script did.
    """
    print(f"\n{'='*60}")
    print(f"Testing {backend_name.upper()} backend")
    print(f"{'='*60}")

    os.environ["YUI_BACKEND"] = backend_name

    try:
        from manatools.aui.yui import YUI, YUI_ui
        import manatools.aui.yui_common as yui

        # Force re-detection so the env-var is honoured
        YUI._instance = None
        YUI._backend  = None

        backend = YUI.backend()
        print(f"Using backend: {backend.value}")

        ui      = YUI_ui()
        factory = ui.widgetFactory()

        if backend_name == "ncurses":
            print(
                "\nNCurses tips:\n"
                "  ComboBox  — SPACE to expand, arrows to navigate, ENTER to select\n"
                "  CheckBox  — SPACE to toggle\n"
                "  RadioBtn  — arrows to move, SPACE to select\n"
            )
            input("Press Enter to start...")

        widgets = _build_dialog(factory, backend_name)
        widgets["dialog"].open() if hasattr(widgets["dialog"], "open") else None

        _run_event_loop(widgets, backend_name)

    except Exception as e:
        print(f"Error with backend '{backend_name}': {e}")
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def test_all_backends():
    available = _probe_backends()
    print(f"\nAvailable backends: {available}\n")

    for i, backend in enumerate(available):
        if backend == "web":
            test_web()
        else:
            if backend == "ncurses" or i == 0:
                pass  # ncurses prompt is inside test_native()
            else:
                input("Press Enter to test next backend...")
            test_native(backend)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        requested = sys.argv[1].lower()
        port      = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

        if requested == "web":
            test_web(port=port)
        else:
            test_native(requested)
    else:
        test_all_backends()