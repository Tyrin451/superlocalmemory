// Neural Glass — Skill Evolution Tab
// Browse skill performance, evolution history, and health status (v3.4.10)
// API: /api/behavioral/assertions (category=skill_performance, skill_correlation)
//      /api/behavioral/tool-events (tool_name=Skill)
//      /api/entity/list (type filter for skill entities)

(function() {
  'use strict';

  window.loadSkillEvolution = function() {
    fetchSkillOverview();
    fetchSkillPerformance();
  };

  function fetchSkillOverview() {
    var el = document.getElementById('skills-overview-cards');
    if (!el) return;

    // Compatibility notice + ECC credit + docs links
    var noticeHtml =
      '<div class="card" style="padding:12px 16px;margin-bottom:16px;border-left:3px solid #8b5cf6">' +
        '<div style="font-size:0.8125rem;color:#555">' +
          '<i class="bi bi-info-circle" style="color:#8b5cf6;margin-right:6px"></i>' +
          '<strong>Skill Evolution</strong> currently tracks <strong>Claude Code</strong> skills. ' +
          'The <code>/api/v3/tool-event</code> endpoint accepts events from any IDE client. ' +
          'Enhanced observation support available with ' +
          '<a href="https://github.com/affaan-m/everything-claude-code" target="_blank" style="color:#8b5cf6">Everything Claude Code (ECC)</a> ' +
          'via <code>slm ingest --source ecc</code>.' +
        '</div>' +
        '<div style="font-size:0.75rem;color:#888;margin-top:8px">' +
          '<a href="https://superlocalmemory.com/skill-evolution" target="_blank" style="color:#8b5cf6;margin-right:12px"><i class="bi bi-globe"></i> Learn more</a>' +
          '<a href="https://github.com/qualixar/superlocalmemory/blob/main/docs/skill-evolution.md" target="_blank" style="color:#8b5cf6"><i class="bi bi-book"></i> Documentation</a>' +
        '</div>' +
      '</div>';
    el.innerHTML = noticeHtml + '<div id="skills-overview-inner"></div>';
    el = document.getElementById('skills-overview-inner');

    // Fetch tool events for Skill calls + assertions for skill_performance
    Promise.all([
      fetch('/api/behavioral/tool-events?tool_name=Skill&limit=500').then(function(r) { return r.json(); }),
      fetch('/api/behavioral/assertions?category=skill_performance&limit=50').then(function(r) { return r.json(); }),
      fetch('/api/behavioral/assertions?category=skill_correlation&limit=20').then(function(r) { return r.json(); }),
    ]).then(function(results) {
      var events = results[0].events || [];
      var perfAssertions = results[1].assertions || [];
      var corrAssertions = results[2].assertions || [];

      // Count unique skills from events
      var skillNames = {};
      events.forEach(function(e) {
        var name = extractSkillName(e);
        if (name) skillNames[name] = (skillNames[name] || 0) + 1;
      });

      var html = '<div class="row g-3 mb-4">' +
        overviewCard('Total Skill Events', events.length, 'bi-lightning-charge', 'var(--ng-accent)') +
        overviewCard('Unique Skills', Object.keys(skillNames).length, 'bi-grid-3x3', '#8b5cf6') +
        overviewCard('Performance Assertions', perfAssertions.length, 'bi-graph-up', '#10b981') +
        overviewCard('Skill Correlations', corrAssertions.length, 'bi-link-45deg', '#f59e0b') +
      '</div>';

      el.innerHTML = html;
    }).catch(function() {
      el.innerHTML = '<div class="alert alert-warning">Could not load skill overview</div>';
    });
  }

  function fetchSkillPerformance() {
    var el = document.getElementById('skills-list');
    if (!el) return;

    Promise.all([
      fetch('/api/behavioral/assertions?category=skill_performance&limit=50').then(function(r) { return r.json(); }),
      fetch('/api/behavioral/assertions?category=skill_correlation&limit=20').then(function(r) { return r.json(); }),
      fetch('/api/behavioral/tool-events?tool_name=Skill&limit=500').then(function(r) { return r.json(); }),
    ]).then(function(results) {
      var perfAssertions = results[0].assertions || [];
      var corrAssertions = results[1].assertions || [];
      var events = results[2].events || [];

      var html = '';

      // Section 1: Skill Performance
      html += '<h5 style="margin-bottom:16px"><i class="bi bi-lightning-charge" style="color:#8b5cf6"></i> Skill Performance</h5>';

      if (perfAssertions.length === 0 && events.length === 0) {
        html += '<div class="card" style="padding:24px;text-align:center;color:#888">' +
          '<i class="bi bi-lightning-charge" style="font-size:2.5rem;display:block;margin-bottom:12px;opacity:0.3"></i>' +
          '<div style="font-size:1rem;margin-bottom:4px;color:#444">No skill performance data yet</div>' +
          '<div style="font-size:0.8125rem">' +
            'Skill tracking starts automatically after the enriched hook captures data.<br>' +
            'Use skills in your sessions — performance assertions will appear after consolidation.' +
          '</div>' +
        '</div>';
      } else if (perfAssertions.length > 0) {
        html += '<div class="row g-3">';
        perfAssertions.forEach(function(a) {
          html += renderSkillCard(a);
        });
        html += '</div>';
      } else {
        // We have events but no assertions yet (need consolidation)
        html += '<div class="card" style="padding:16px;margin-bottom:16px">' +
          '<div style="font-size:0.875rem;color:#555">' +
            '<i class="bi bi-info-circle" style="color:#8b5cf6;margin-right:6px"></i>' +
            events.length + ' skill events collected. Run consolidation to generate performance assertions.' +
          '</div>' +
        '</div>';

        // Show raw event summary
        var skillCounts = {};
        events.forEach(function(e) {
          var name = extractSkillName(e);
          if (name) skillCounts[name] = (skillCounts[name] || 0) + 1;
        });

        html += '<div class="row g-3">';
        Object.keys(skillCounts).sort(function(a, b) {
          return skillCounts[b] - skillCounts[a];
        }).forEach(function(name) {
          html += '<div class="col-md-6 col-lg-4"><div class="card" style="padding:16px;border-left:3px solid #8b5cf6">' +
            '<div style="display:flex;justify-content:space-between;align-items:center">' +
              '<div style="font-weight:600;font-size:0.9375rem">' +
                '<i class="bi bi-lightning-charge" style="color:#8b5cf6;margin-right:4px"></i>' +
                escapeHtml(name) +
              '</div>' +
              '<span class="badge" style="background:#8b5cf620;color:#8b5cf6;font-size:0.75rem">' + skillCounts[name] + ' events</span>' +
            '</div>' +
          '</div></div>';
        });
        html += '</div>';
      }

      // Section 2: Skill Correlations
      if (corrAssertions.length > 0) {
        html += '<h5 style="margin-top:32px;margin-bottom:16px"><i class="bi bi-link-45deg" style="color:#f59e0b"></i> Skill Correlations</h5>';
        html += '<div class="row g-3">';
        corrAssertions.forEach(function(a) {
          html += '<div class="col-md-6"><div class="card" style="padding:12px">' +
            '<div style="font-size:0.875rem">' +
              '<strong>' + escapeHtml(a.trigger_condition || '') + '</strong>' +
            '</div>' +
            '<div style="font-size:0.8125rem;color:#555;margin-top:4px">' +
              escapeHtml(a.action || '') +
            '</div>' +
            '<div style="font-size:0.75rem;color:#888;margin-top:4px">' +
              'Confidence: ' + ((a.confidence || 0) * 100).toFixed(0) + '%' +
            '</div>' +
          '</div></div>';
        });
        html += '</div>';
      }

      el.innerHTML = html;
    }).catch(function(err) {
      el.innerHTML = '<div class="text-center" style="padding:24px;color:var(--ng-text-tertiary)">' +
        'Error loading skill data: ' + err.message + '</div>';
    });
  }

  function renderSkillCard(assertion) {
    var conf = assertion.confidence || 0;
    var confPct = (conf * 100).toFixed(0);
    var confColor = conf >= 0.7 ? '#10b981' : conf >= 0.5 ? '#f59e0b' : '#ef4444';

    // Extract skill name from trigger_condition
    var skillName = (assertion.trigger_condition || '').replace('when considering skill ', '');

    return '<div class="col-md-6 col-lg-4">' +
      '<div class="card" style="padding:16px;border-left:3px solid #8b5cf6;cursor:pointer">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">' +
          '<div style="font-weight:600;font-size:0.9375rem">' +
            '<i class="bi bi-lightning-charge" style="color:#8b5cf6;margin-right:4px"></i>' +
            escapeHtml(skillName) +
          '</div>' +
          '<span class="badge" style="background:' + confColor + ';color:#fff;font-size:0.75rem">' +
            confPct + '%' +
          '</span>' +
        '</div>' +
        '<div style="font-size:0.8125rem;color:#555;margin-bottom:8px">' +
          escapeHtml(assertion.action || 'No performance data yet') +
        '</div>' +
        '<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.75rem;color:#888">' +
          '<span>Evidence: ' + (assertion.evidence_count || 0) + ' invocations</span>' +
          '<span>Reinforced: ' + (assertion.reinforcement_count || 0) + 'x</span>' +
        '</div>' +
      '</div>' +
    '</div>';
  }

  function extractSkillName(event) {
    var input = event.input_summary || '';
    var output = event.output_summary || '';

    // Try input_summary (enriched hook format)
    if (input) {
      try {
        var inp = JSON.parse(input);
        if (inp.skill) return inp.skill;
      } catch(e) {}
    }

    // Try output_summary (ECC ingestion format)
    if (output) {
      try {
        var out = JSON.parse(output);
        if (out.commandName) return out.commandName;
      } catch(e) {}
    }

    return null;
  }

  function overviewCard(label, value, icon, color) {
    return '<div class="col-md-3 col-6"><div class="card" style="padding:12px;text-align:center">' +
      '<i class="bi ' + icon + '" style="color:' + color + ';font-size:1.125rem;display:block;margin-bottom:4px"></i>' +
      '<div style="font-size:1.25rem;font-weight:600">' + value + '</div>' +
      '<div style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:#888">' + label + '</div>' +
    '</div></div>';
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }
})();
