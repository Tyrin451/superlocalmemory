// SuperLocalMemory v3.4.1 — Graph Event Bus
// Copyright (c) 2026 Varun Pratap Bhardwaj — AGPL-3.0-or-later
// CustomEvent-based pub/sub for graph ↔ chat bidirectional linking.
// Renderer-agnostic — works regardless of which graph engine is active.

var SLMEventBus = (function() {
    var _debounceTimers = {};

    function publish(eventName, detail) {
        window.dispatchEvent(new CustomEvent(eventName, {
            detail: Object.freeze(detail || {}),
        }));
    }

    function publishDebounced(eventName, detail, delayMs) {
        if (_debounceTimers[eventName]) {
            clearTimeout(_debounceTimers[eventName]);
        }
        _debounceTimers[eventName] = setTimeout(function() {
            publish(eventName, detail);
            _debounceTimers[eventName] = null;
        }, delayMs || 200);
    }

    function subscribe(eventName, callback) {
        window.addEventListener(eventName, function(e) {
            callback(e.detail);
        });
    }

    return { publish: publish, publishDebounced: publishDebounced, subscribe: subscribe };
})();

// Expose globally
window.SLMEventBus = SLMEventBus;

// ============================================================================
// EVENT DEFINITIONS
// ============================================================================
// slm:graph:nodeClicked     — { factId, label }   — graph node was clicked
// slm:graph:highlightNode   — { factId }           — highlight a node in graph
// slm:chat:citationClicked  — { factId }           — citation badge clicked in chat
// slm:chat:queryAbout       — { query }             — fill chat input and send

// ============================================================================
// WIRING: Graph → Chat
// ============================================================================

SLMEventBus.subscribe('slm:graph:nodeClicked', function(detail) {
    // Double-click on graph node → fill chat with query about that node
    // (Single click handled by openSigmaNodeDetail in knowledge-graph.js)
});

SLMEventBus.subscribe('slm:chat:queryAbout', function(detail) {
    if (!detail || !detail.query) return;
    var input = document.getElementById('chat-input');
    if (input) {
        input.value = detail.query;
        // Switch to chat panel if on detail panel
        if (typeof showChatPanel === 'function') showChatPanel();
        // Auto-send
        if (typeof sendChatFromInput === 'function') sendChatFromInput();
    }
});

// ============================================================================
// WIRING: Chat → Graph
// ============================================================================

SLMEventBus.subscribe('slm:chat:citationClicked', function(detail) {
    if (!detail || !detail.factId) return;
    // Highlight the cited node in the graph
    if (typeof sigmaHighlightNode === 'function') {
        sigmaHighlightNode(detail.factId);
    }
});

SLMEventBus.subscribe('slm:graph:highlightNode', function(detail) {
    if (!detail || !detail.factId) return;
    if (typeof sigmaHighlightNode === 'function') {
        sigmaHighlightNode(detail.factId);
    }
});
