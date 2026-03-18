#!/usr/bin/env python3
"""
Demo application for testing the ManaTools Web Backend.

Run with:
    YUI_BACKEND=web python demo_app.py

Then open http://127.0.0.1:8080 in your browser.
"""

import os
import sys

# Ensure web backend is selected
os.environ['YUI_BACKEND'] = 'web'

# Add the package to path for testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manatools.aui.yui import YUI


def main():
    # Get the widget factory
    factory = YUI.widgetFactory()
    app = YUI.application()
    
    # Set application info
    app.setApplicationTitle("ManaTools Web Demo")
    app.setProductName("ManaTools AUI Web Backend Demo")
    
    # Create main dialog
    dialog = factory.createMainDialog()
    
    # Create main layout
    vbox = factory.createVBox(dialog)
    
    # Header
    factory.createHeading(vbox, "Welcome to ManaTools Web Backend")
    factory.createLabel(vbox, "This demo shows various widgets rendered in your browser.")
    
    factory.createVSpacing(vbox, 16)
    
    # Input section
    frame = factory.createFrame(vbox, "Input Widgets")
    frame_vbox = factory.createVBox(frame)
    
    name_input = factory.createInputField(frame_vbox, "Your &Name:")
    name_input.setValue("World")
    
    password_input = factory.createPasswordField(frame_vbox, "&Password:")
    
    age_input = factory.createIntField(frame_vbox, "&Age:", 0, 120, 25)
    
    factory.createVSpacing(vbox, 8)
    
    # Selection section
    frame2 = factory.createFrame(vbox, "Selection Widgets")
    frame2_vbox = factory.createVBox(frame2)
    
    # Checkbox
    checkbox = factory.createCheckBox(frame2_vbox, "&Enable notifications", True)
    
    # Combo box
    combo = factory.createComboBox(frame2_vbox, "&Color:")
    combo.addItem("Red")
    combo.addItem("Green")
    combo.addItem("Blue")
    combo.addItem("Yellow")
    
    # Selection box
    selection = factory.createSelectionBox(frame2_vbox, "Select &Items:")
    selection.addItem("Item 1")
    selection.addItem("Item 2")
    selection.addItem("Item 3")
    selection.addItem("Item 4")
    selection.addItem("Item 5")
    
    factory.createVSpacing(vbox, 8)
    
    # Progress bar
    progress = factory.createProgressBar(vbox, "Progress:", 100)
    progress.setValue(65)
    
    factory.createVSpacing(vbox, 8)
    
    # Output label
    output_label = factory.createLabel(vbox, "Click a button to see events...")
    
    factory.createVSpacing(vbox, 16)
    
    # Button bar
    hbox = factory.createHBox(vbox)
    factory.createHStretch(hbox)
    
    greet_button = factory.createPushButton(hbox, "&Greet")
    clear_button = factory.createPushButton(hbox, "&Clear")
    ok_button = factory.createPushButton(hbox, "&OK")
    ok_button.setDefault(True)
    cancel_button = factory.createPushButton(hbox, "Ca&ncel")
    
    # Open dialog
    dialog.open()
    
    # Event loop
    running = True
    while running:
        event = dialog.waitForEvent()
        
        widget = event.widget()
        
        if widget == ok_button:
            name = name_input.value()
            output_label.setText(f"OK clicked! Hello, {name}!")
            
        elif widget == cancel_button:
            output_label.setText("Cancel clicked - goodbye!")
            running = False
            
        elif widget == greet_button:
            name = name_input.value() or "World"
            output_label.setText(f"Hello, {name}! Age: {age_input.value()}")
            
        elif widget == clear_button:
            name_input.setValue("")
            password_input.setValue("")
            age_input.setValue(25)
            checkbox.setChecked(False)
            progress.setValue(0)
            output_label.setText("Fields cleared!")
            
        elif widget == checkbox:
            status = "enabled" if checkbox.isChecked() else "disabled"
            output_label.setText(f"Notifications {status}")
            
        elif widget == combo:
            output_label.setText(f"Color selected: {combo.value()}")
            
        elif widget == age_input:
            output_label.setText(f"Age changed to: {age_input.value()}")
            
        # Check for cancel event (window close, Escape key)
        from manatools.aui.yui_common import YEventType
        if event.eventType() == YEventType.CancelEvent:
            output_label.setText("Dialog closing...")
            running = False
    
    # Clean up
    dialog.destroy()
    print("Demo finished!")


if __name__ == "__main__":
    main()
