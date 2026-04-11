// SuperLocalMemory v3.4.1 — Memory Timeline (D3.js v7)
// Copyright (c) 2026 Varun Pratap Bhardwaj — AGPL-3.0-or-later
// Horizontal timeline: facts + temporal events + consolidation over time.

var memoryTimelineState = {
    range: '7d',
    groupBy: 'category',
    events: [],
    svg: null,
    zoom: null,
};

var TRUST_COLORS = { high: '#198754', medium: '#ffc107', low: '#dc3545', unknown: '#6c757d' };

function trustColor(score) {
    if (score === null || score === undefined) return TRUST_COLORS.unknown;
    if (score >= 0.7) return TRUST_COLORS.high;
    if (score >= 0.4) return TRUST_COLORS.medium;
    return TRUST_COLORS.low;
}

// ============================================================================
// INIT
// ============================================================================

function initMemoryTimeline() {
    // Zoom buttons
    document.querySelectorAll('#timeline-zoom-group button').forEach(function(btn) {
        btn.addEventListener('click', function() {
            setZoomLevel(btn.dataset.zoom);
        });
    });
    // Group-by buttons
    document.querySelectorAll('#timeline-group-by-group button').forEach(function(btn) {
        btn.addEventListener('click', function() {
            setGroupBy(btn.dataset.groupby);
        });
    });
    // Listen for refresh events (fire-and-forget from other components)
    window.addEventListener('slm:timeline:refresh', function() {
        fetchTimelineData(memoryTimelineState.range, memoryTimelineState.groupBy);
    });
    // Initial load
    fetchTimelineData('7d', 'category');
}

// ============================================================================
// DATA FETCH
// ============================================================================

function fetchTimelineData(range, groupBy) {
    memoryTimelineState.range = range;
    memoryTimelineState.groupBy = groupBy;

    var container = document.getElementById('memory-timeline-chart');
    if (!container) return;

    fetch('/api/v3/timeline/?range=' + range + '&group_by=' + groupBy + '&limit=1000')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            memoryTimelineState.events = data.events || [];
            renderTimeline(memoryTimelineState.events, container, groupBy);
        })
        .catch(function(e) {
            container.innerHTML = '';
            var msg = document.createElement('div');
            msg.className = 'text-muted small text-center py-4';
            msg.textContent = 'Timeline unavailable: ' + e.message;
            container.appendChild(msg);
        });
}

// ============================================================================
// D3 RENDERING
// ============================================================================

function renderTimeline(events, container, groupBy) {
    container.innerHTML = '';
    if (!events || events.length === 0) {
        var msg = document.createElement('div');
        msg.className = 'text-muted small text-center py-4';
        msg.textContent = 'No memory events in this time range.';
        container.appendChild(msg);
        return;
    }

    if (typeof d3 === 'undefined') {
        container.textContent = 'D3.js not loaded.';
        return;
    }

    var width = container.clientWidth || 800;
    var height = 260;
    var margin = { top: 20, right: 20, bottom: 30, left: 100 };

    // Parse timestamps
    events.forEach(function(e) {
        e._date = new Date(e.timestamp);
        if (groupBy === 'community') {
            e._category = e.community_id !== null ? ('C' + e.community_id) : 'Unknown';
        } else {
            e._category = e.category || 'semantic';
        }
    });

    // Build categories
    var categories;
    if (groupBy === 'community') {
        var counts = {};
        events.forEach(function(e) { counts[e._category] = (counts[e._category] || 0) + 1; });
        var sorted = Object.entries(counts).sort(function(a, b) { return b[1] - a[1]; });
        var top10 = sorted.slice(0, 10).map(function(pair) { return pair[0]; });
        if (sorted.length > 10) {
            categories = top10.concat(['Other']);
            events.forEach(function(e) {
                if (top10.indexOf(e._category) === -1) e._category = 'Other';
            });
        } else {
            categories = sorted.map(function(pair) { return pair[0]; });
        }
    } else {
        categories = ['semantic', 'episodic', 'opinion', 'temporal', 'consolidation'];
    }

    // Scales
    var xDomain = d3.extent(events, function(e) { return e._date; });
    var xScale = d3.scaleTime()
        .domain(xDomain)
        .range([margin.left, width - margin.right]);

    var yScale = d3.scaleBand()
        .domain(categories)
        .range([margin.top, height - margin.bottom])
        .padding(0.3);

    // SVG
    var svg = d3.select(container).append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('font-size', '11px');

    // Axes
    var xAxisG = svg.append('g')
        .attr('transform', 'translate(0,' + (height - margin.bottom) + ')')
        .call(d3.axisBottom(xScale).ticks(6).tickFormat(d3.timeFormat('%b %d')));

    svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',0)')
        .call(d3.axisLeft(yScale));

    // Data points
    var circles = svg.selectAll('circle')
        .data(events)
        .join('circle')
        .attr('cx', function(d) { return xScale(d._date); })
        .attr('cy', function(d) { return yScale(d._category) + yScale.bandwidth() / 2; })
        .attr('r', 4)
        .attr('fill', function(d) { return trustColor(d.trust_score); })
        .attr('stroke', '#fff')
        .attr('stroke-width', 0.5)
        .attr('cursor', 'pointer')
        .attr('opacity', 0.8)
        .on('click', function(event, d) { onTimelinePointClick(d); })
        .on('mouseover', function(event, d) { showTimelineTooltip(event, d); })
        .on('mouseout', hideTimelineTooltip);

    // Zoom (x-axis only)
    var zoom = d3.zoom()
        .scaleExtent([0.5, 20])
        .translateExtent([[margin.left, 0], [width - margin.right, height]])
        .extent([[margin.left, 0], [width - margin.right, height]])
        .on('zoom', function(event) {
            var newX = event.transform.rescaleX(xScale);
            xAxisG.call(d3.axisBottom(newX).ticks(6).tickFormat(d3.timeFormat('%b %d')));
            circles.attr('cx', function(d) { return newX(d._date); });
        });

    svg.call(zoom);
    memoryTimelineState.svg = svg;
    memoryTimelineState.zoom = zoom;
}

// ============================================================================
// INTERACTIONS
// ============================================================================

function onTimelinePointClick(d) {
    // Fire event bus (fire-and-forget — Phase 3 adds listener)
    if (d.id) {
        window.dispatchEvent(new CustomEvent('slm:graph:highlight', {
            detail: { nodeIds: [d.id] },
        }));
    }
    // Open detail modal if available
    if (typeof openMemoryDetail === 'function' && d.id) {
        openMemoryDetail(d.id);
    }
}

function showTimelineTooltip(event, d) {
    var tooltip = document.getElementById('timeline-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'timeline-tooltip';
        tooltip.style.cssText = 'position:fixed;background:#333;color:#fff;padding:6px 10px;border-radius:6px;font-size:0.75rem;z-index:9999;pointer-events:none;max-width:300px;';
        document.body.appendChild(tooltip);
    }
    tooltip.textContent = (d.content_preview || 'No preview') + ' | ' + (d.category || '') + ' | Trust: ' + (d.trust_score !== null ? (d.trust_score * 100).toFixed(0) + '%' : 'N/A');
    tooltip.style.left = (event.clientX + 10) + 'px';
    tooltip.style.top = (event.clientY - 30) + 'px';
    tooltip.style.display = 'block';
}

function hideTimelineTooltip() {
    var tooltip = document.getElementById('timeline-tooltip');
    if (tooltip) tooltip.style.display = 'none';
}

// ============================================================================
// CONTROLS
// ============================================================================

function setZoomLevel(level) {
    var rangeMap = { day: '1d', week: '7d', month: '30d' };
    var range = rangeMap[level] || '7d';

    // Update button active state
    document.querySelectorAll('#timeline-zoom-group button').forEach(function(b) {
        b.classList.toggle('active', b.dataset.zoom === level);
    });
    fetchTimelineData(range, memoryTimelineState.groupBy);
}

function setGroupBy(mode) {
    document.querySelectorAll('#timeline-group-by-group button').forEach(function(b) {
        b.classList.toggle('active', b.dataset.groupby === mode);
    });
    fetchTimelineData(memoryTimelineState.range, mode);
}

// ============================================================================
// AUTO-INIT (when Knowledge Graph tab opens)
// ============================================================================

// Deferred init — only load when the graph tab becomes visible
var _timelineInitDone = false;
function tryInitTimeline() {
    if (_timelineInitDone) return;
    var panel = document.getElementById('memory-timeline-panel');
    if (panel && panel.offsetParent !== null) {
        _timelineInitDone = true;
        initMemoryTimeline();
    }
}

// Check on tab switch
document.addEventListener('shown.bs.tab', function() {
    setTimeout(tryInitTimeline, 100);
});
// Also check on DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { setTimeout(tryInitTimeline, 500); });
} else {
    setTimeout(tryInitTimeline, 500);
}
