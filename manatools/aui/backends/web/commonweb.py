"""
Common utilities shared across all web backend widgets.
"""

import html
import re
from typing import Optional


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(str(text)) if text else ""


def format_label_with_shortcut(label: str) -> str:
    """
    Convert '&X' to '<u>X</u>' for keyboard shortcut display.
    Also extracts the shortcut character.
    """
    if not label:
        return ""
    # Replace &X with <u>X</u>, but handle && as literal &
    result = re.sub(r'&&', '\x00', label)  # temporary placeholder for &&
    result = re.sub(r'&(.)', r'<u>\1</u>', result)
    result = result.replace('\x00', '&amp;')
    return result


def extract_shortcut(label: str) -> Optional[str]:
    """Extract the shortcut character from a label with &X notation."""
    if not label:
        return None
    match = re.search(r'&([^&])', label)
    return match.group(1).lower() if match else None


def strip_shortcut(label: str) -> str:
    """Remove &X shortcut notation from label, keeping the character."""
    if not label:
        return ""
    result = re.sub(r'&&', '\x00', label)
    result = re.sub(r'&(.)', r'\1', result)
    return result.replace('\x00', '&')


def build_css_classes(*classes: str) -> str:
    """Build a CSS class string from multiple class names, filtering empty."""
    return " ".join(c for c in classes if c)


def build_style(**styles) -> str:
    """Build an inline style string from keyword arguments."""
    parts = []
    for key, value in styles.items():
        if value is not None:
            # Convert Python names to CSS (background_color -> background-color)
            css_key = key.replace('_', '-')
            parts.append(f"{css_key}: {value}")
    return "; ".join(parts) if parts else ""


def widget_attrs(widget_id: str, widget_class: str, enabled: bool = True, 
                 visible: bool = True, extra_classes: str = "",
                 extra_attrs: dict = None) -> str:
    """
    Build common HTML attributes for a widget element.
    
    Returns a string like: id="..." class="..." data-widget-class="..." [disabled] [hidden]
    """
    classes = build_css_classes(f"mana-{widget_class.lower()}", extra_classes)
    
    attrs = [
        f'id="{escape_html(widget_id)}"',
        f'class="{classes}"',
        f'data-widget-class="{escape_html(widget_class)}"',
    ]
    
    if not enabled:
        attrs.append('disabled')
    
    if not visible:
        attrs.append('style="display: none"')
    
    if extra_attrs:
        for key, value in extra_attrs.items():
            if value is True:
                attrs.append(key)
            elif value is not None and value is not False:
                attrs.append(f'{key}="{escape_html(str(value))}"')
    
    return " ".join(attrs)
