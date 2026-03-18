"""Web backend MenuBar implementation."""
from ...yui_common import YWidget, YMenuItem
from .commonweb import widget_attrs, escape_html

class YMenuBarWeb(YWidget):
    """Menu bar widget."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._menus = []
    
    def widgetClass(self):
        return "YMenuBar"
    
    def addMenu(self, label: str, icon_name: str = "") -> YMenuItem:
        menu = YMenuItem(label, icon_name, is_menu=True)
        self._menus.append(menu)
        return menu
    
    def _render_menu_item(self, item) -> str:
        if item.isSeparator():
            return '<hr class="mana-menu-separator">'
        
        if item.isMenu() and item.hasChildren():
            children_html = ""
            for child in item.childrenBegin():
                children_html += self._render_menu_item(child)
            return f'''<div class="mana-menu">
                <span class="mana-menu-label">{escape_html(item.label())}</span>
                <div class="mana-submenu">{children_html}</div>
            </div>'''
        else:
            disabled = " disabled" if not item.enabled() else ""
            return f'<div class="mana-menu-item{disabled}">{escape_html(item.label())}</div>'
    
    def render(self) -> str:
        menus_html = ""
        for menu in self._menus:
            menus_html += self._render_menu_item(menu)
        
        attrs = widget_attrs(self.id(), "YMenuBar", self._enabled, self._visible)
        return f'<nav {attrs}>{menus_html}</nav>'
