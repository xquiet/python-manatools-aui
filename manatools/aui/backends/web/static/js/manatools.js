/**
 * ManaTools Web Backend JavaScript
 * 
 * Handles user interaction events and WebSocket communication with the Python backend.
 */

(function() {
    'use strict';

    // WebSocket connection
    let ws = null;
    let wsReconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 10;
    const RECONNECT_DELAY = 1000;

    /**
     * Initialize the ManaTools client
     */
    function init() {
        console.log('ManaTools Web Client initializing...');
        connectWebSocket();
        attachEventListeners();
    }

    /**
     * Connect to WebSocket server
     */
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = function() {
                console.log('WebSocket connected');
                wsReconnectAttempts = 0;
            };

            ws.onmessage = function(event) {
                handleServerMessage(JSON.parse(event.data));
            };

            ws.onclose = function() {
                console.log('WebSocket disconnected');
                attemptReconnect();
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        } catch (e) {
            console.error('Failed to create WebSocket:', e);
            // Fall back to polling or SSE
            setupFallbackCommunication();
        }
    }

    /**
     * Attempt to reconnect WebSocket
     */
    function attemptReconnect() {
        if (wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            wsReconnectAttempts++;
            console.log(`Reconnecting (attempt ${wsReconnectAttempts})...`);
            setTimeout(connectWebSocket, RECONNECT_DELAY * wsReconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
            setupFallbackCommunication();
        }
    }

    /**
     * Setup fallback communication (POST requests)
     */
    function setupFallbackCommunication() {
        console.log('Using fallback POST communication');
        // Events will be sent via POST to /event endpoint
    }

    /**
     * Send event to server
     */
    function sendEvent(eventData) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(eventData));
        } else {
            // Fallback: POST request
            fetch('/event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventData)
            }).catch(err => console.error('Failed to send event:', err));
        }
    }

    /**
     * Handle message from server
     */
    function handleServerMessage(message) {
        switch (message.type) {
            case 'update':
                applyUpdates(message.updates);
                break;
            case 'refresh':
                document.getElementById('mana-app').innerHTML = message.html;
                attachEventListeners();
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    /**
     * Apply DOM updates from server
     */
    function applyUpdates(updates) {
        if (!Array.isArray(updates)) return;

        updates.forEach(function(update) {
            const target = document.querySelector(update.target);
            if (!target) {
                console.warn('Update target not found:', update.target);
                return;
            }

            switch (update.action) {
                case 'replace':
                    // Create temporary container
                    const temp = document.createElement('div');
                    temp.innerHTML = update.html;
                    const newElement = temp.firstElementChild;
                    if (newElement) {
                        target.replaceWith(newElement);
                        // Re-attach event listeners to the new element
                        attachEventListenersToElement(newElement);
                    }
                    break;
                case 'attr':
                    if (update.value === null || update.value === false) {
                        target.removeAttribute(update.attr);
                    } else if (update.value === true) {
                        target.setAttribute(update.attr, '');
                    } else {
                        target.setAttribute(update.attr, update.value);
                    }
                    break;
                case 'html':
                    target.innerHTML = update.html;
                    attachEventListenersToElement(target);
                    break;
                case 'text':
                    target.textContent = update.text;
                    break;
            }
        });
    }

    /**
     * Attach event listeners to all interactive elements
     */
    function attachEventListeners() {
        const app = document.getElementById('mana-app');
        if (app) {
            attachEventListenersToElement(app);
        }
    }

    /**
     * Attach event listeners to an element and its children
     */
    function attachEventListenersToElement(root) {
        // Buttons
        root.querySelectorAll('.mana-ypushbutton').forEach(function(btn) {
            btn.removeEventListener('click', handleButtonClick);
            btn.addEventListener('click', handleButtonClick);
        });

        // Input fields
        root.querySelectorAll('.mana-yinputfield, .mana-yintfield, .mana-ydatefield, .mana-ytimefield').forEach(function(input) {
            input.removeEventListener('change', handleInputChange);
            input.removeEventListener('input', handleInputInput);
            input.addEventListener('change', handleInputChange);
            input.addEventListener('input', handleInputInput);
        });

        // Checkboxes
        root.querySelectorAll('.mana-ycheckbox').forEach(function(cb) {
            cb.removeEventListener('change', handleCheckboxChange);
            cb.addEventListener('change', handleCheckboxChange);
        });

        // Radio buttons
        root.querySelectorAll('.mana-yradiobutton').forEach(function(rb) {
            rb.removeEventListener('change', handleRadioChange);
            rb.addEventListener('change', handleRadioChange);
        });

        // Combo boxes
        root.querySelectorAll('.mana-ycombobox').forEach(function(select) {
            select.removeEventListener('change', handleSelectChange);
            select.addEventListener('change', handleSelectChange);
        });

        // Selection boxes
        root.querySelectorAll('.mana-yselectionbox').forEach(function(select) {
            select.removeEventListener('change', handleSelectionChange);
            select.addEventListener('change', handleSelectionChange);
        });

        // Multi-line edit
        root.querySelectorAll('.mana-ymultilineedit').forEach(function(textarea) {
            textarea.removeEventListener('change', handleTextareaChange);
            textarea.addEventListener('change', handleTextareaChange);
        });

        // Sliders
        root.querySelectorAll('.mana-yslider').forEach(function(slider) {
            slider.removeEventListener('input', handleSliderInput);
            slider.removeEventListener('change', handleSliderChange);
            slider.addEventListener('input', handleSliderInput);
            slider.addEventListener('change', handleSliderChange);
        });

        // Table rows
        root.querySelectorAll('.mana-ytable tbody tr').forEach(function(row) {
            row.removeEventListener('click', handleTableRowClick);
            row.addEventListener('click', handleTableRowClick);
        });

        // Tree items
        root.querySelectorAll('.mana-tree-item').forEach(function(item) {
            item.removeEventListener('click', handleTreeItemClick);
            item.addEventListener('click', handleTreeItemClick);
        });

        // Tab buttons
        root.querySelectorAll('.mana-tab').forEach(function(tab) {
            tab.removeEventListener('click', handleTabClick);
            tab.addEventListener('click', handleTabClick);
        });

        // Menu items
        root.querySelectorAll('.mana-menu-item').forEach(function(item) {
            item.removeEventListener('click', handleMenuItemClick);
            item.addEventListener('click', handleMenuItemClick);
        });

        // CheckBox frames
        root.querySelectorAll('.mana-checkboxframe-toggle').forEach(function(cb) {
            cb.removeEventListener('change', handleCheckboxFrameToggle);
            cb.addEventListener('change', handleCheckboxFrameToggle);
        });

        // Keyboard shortcuts
        document.removeEventListener('keydown', handleKeyDown);
        document.addEventListener('keydown', handleKeyDown);
    }

    /**
     * Get widget ID from element (handles nested elements)
     */
    function getWidgetId(element) {
        // Check for data-widget-id first (for wrapped inputs)
        if (element.dataset.widgetId) {
            return element.dataset.widgetId;
        }
        // Otherwise use the element's id
        if (element.id) {
            return element.id;
        }
        // Check parent for container widgets
        const container = element.closest('[data-widget-class]');
        return container ? container.id : null;
    }

    // ============================================
    // Event Handlers
    // ============================================

    function handleButtonClick(event) {
        const btn = event.currentTarget;
        if (btn.disabled) return;

        sendEvent({
            type: 'event',
            widget_id: getWidgetId(btn),
            reason: 'Activated',
            data: {}
        });
    }

    function handleInputChange(event) {
        const input = event.target;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(input),
            reason: 'ValueChanged',
            data: { value: input.value }
        });
    }

    function handleInputInput(event) {
        // Debounced live update (optional)
        // For now, we only send on change
    }

    function handleCheckboxChange(event) {
        const cb = event.target;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(cb),
            reason: 'ValueChanged',
            data: { checked: cb.checked }
        });
    }

    function handleRadioChange(event) {
        const rb = event.target;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(rb),
            reason: 'ValueChanged',
            data: { checked: rb.checked }
        });
    }

    function handleSelectChange(event) {
        const select = event.target;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(select),
            reason: 'SelectionChanged',
            data: { selectedIndex: select.selectedIndex }
        });
    }

    function handleSelectionChange(event) {
        const select = event.target;
        const selectedIndices = Array.from(select.selectedOptions).map(opt => parseInt(opt.value));
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(select),
            reason: 'SelectionChanged',
            data: { selectedIndex: selectedIndices }
        });
    }

    function handleTextareaChange(event) {
        const textarea = event.target;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(textarea),
            reason: 'ValueChanged',
            data: { value: textarea.value }
        });
    }

    function handleSliderInput(event) {
        const slider = event.target;
        // Update value display
        const container = slider.closest('.mana-slider-container');
        if (container) {
            const valueDisplay = container.querySelector('.mana-slider-value');
            if (valueDisplay) {
                valueDisplay.textContent = slider.value;
            }
        }
    }

    function handleSliderChange(event) {
        const slider = event.target;
        sendEvent({
            type: 'event',
            widget_id: getWidgetId(slider),
            reason: 'ValueChanged',
            data: { value: parseInt(slider.value) }
        });
    }

    function handleTableRowClick(event) {
        const row = event.currentTarget;
        const table = row.closest('.mana-ytable');
        const rowIndex = Array.from(row.parentElement.children).indexOf(row);

        // Toggle selection
        row.classList.toggle('selected');

        sendEvent({
            type: 'event',
            widget_id: getWidgetId(table),
            reason: 'SelectionChanged',
            data: { selectedIndex: rowIndex }
        });
    }

    function handleTreeItemClick(event) {
        const item = event.currentTarget;
        const tree = item.closest('.mana-ytree');
        
        // Toggle selection
        tree.querySelectorAll('.mana-tree-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');

        sendEvent({
            type: 'event',
            widget_id: getWidgetId(tree),
            reason: 'SelectionChanged',
            data: {}
        });
    }

    function handleTabClick(event) {
        const tab = event.currentTarget;
        const tabIndex = parseInt(tab.dataset.tabIndex);
        const tabWidget = tab.closest('.mana-ydumbtab');

        // Update visual selection
        tabWidget.querySelectorAll('.mana-tab').forEach(t => t.classList.remove('selected'));
        tab.classList.add('selected');

        sendEvent({
            type: 'event',
            widget_id: getWidgetId(tabWidget),
            reason: 'SelectionChanged',
            data: { selectedIndex: tabIndex }
        });
    }

    function handleMenuItemClick(event) {
        const item = event.currentTarget;
        if (item.classList.contains('disabled')) return;

        sendEvent({
            type: 'event',
            widget_id: getWidgetId(item.closest('.mana-ymenubar')),
            reason: 'Activated',
            data: { menuItem: item.textContent }
        });
    }

    function handleCheckboxFrameToggle(event) {
        const cb = event.target;
        const frame = cb.closest('.mana-ycheckboxframe');
        const content = frame.querySelector('.mana-checkboxframe-content');
        
        if (content) {
            content.classList.toggle('mana-disabled', !cb.checked);
        }

        sendEvent({
            type: 'event',
            widget_id: getWidgetId(frame),
            reason: 'ValueChanged',
            data: { checked: cb.checked }
        });
    }

    function handleKeyDown(event) {
        // Handle keyboard shortcuts (Alt+key)
        if (event.altKey && event.key.length === 1) {
            const shortcutKey = event.key.toLowerCase();
            
            // Find widget with matching shortcut
            const widget = document.querySelector(`[data-shortcut="${shortcutKey}"]`);
            if (widget && !widget.disabled) {
                event.preventDefault();
                widget.click();
            }
        }

        // Handle Enter on default button
        if (event.key === 'Enter') {
            const defaultBtn = document.querySelector('.mana-ypushbutton.mana-default');
            const activeElement = document.activeElement;
            
            // Don't trigger if in a text input or textarea
            if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
                if (defaultBtn && !defaultBtn.disabled) {
                    defaultBtn.click();
                }
            }
        }

        // Handle Escape (close/cancel)
        if (event.key === 'Escape') {
            sendEvent({
                type: 'close',
                data: {}
            });
        }
    }

    // ============================================
    // Initialize on DOM ready
    // ============================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
