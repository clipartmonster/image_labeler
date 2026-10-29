/**
 * Color Depth (Scale) point sampler.
 * Used by /label_images/label_color_depth/.
 *
 * S starts or finishes a light path. D starts or finishes a dark path.
 * Clicks only add colors while a path is open. The first color in a path
 * is Main. A line connects the colors in that path. U = undo. Radius 16.
 */
(function (global) {
    'use strict';

    var MODE = {
        shade: { key: 'shade', label: 'Shade', tint: [40, 90, 220], badge: [128, 64, 200] },
        highlight: { key: 'highlight', label: 'Light', tint: [240, 180, 40], badge: [245, 200, 40] },
    };
    // UI pick: shade | highlight (highlight shown as Light)
    var PICK = { shade: true, highlight: true };
    var SAMPLE_RADIUS = 16; // native image pixels — local window for sample + main fill
    // Marker sizes in display pixels (fixed on screen — not scaled with image zoom).
    var MARKER_PIN_R = 4;
    var MARKER_BADGE_R = 14;
    var MARKER_LABEL_GAP = 38;
    var MAG_SIZE = 72; // loupe diameter in CSS pixels (40% smaller than 120)
    var MAG_ZOOM = 8; // magnifier zoom factor
    // How close two sample colors must be (RGB Euclidean) to share a group number.
    var COLOR_MATCH_TOLERANCE = 12;
    // Exclude canvas/background when estimating the primary fill color.
    var CANVAS_MATCH_TOLERANCE = 28;
    var QUANT = 16; // RGB quantization step for the fill histogram
    var st = null;

    function rgbCss(rgb) {
        return 'rgb(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ')';
    }

    function colorDist(a, b) {
        var dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2];
        return Math.sqrt(dr * dr + dg * dg + db * db);
    }

    // Rec. 709 relative luminance (0–255 scale).
    function luminance(rgb) {
        return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
    }

    function pixelAt(data, x, y, w) {
        var i = (y * w + x) * 4;
        return [data[i], data[i + 1], data[i + 2], data[i + 3]];
    }

    function estimateCanvasColor(imgData) {
        var w = imgData.width;
        var h = imgData.height;
        var data = imgData.data;
        var corners = [
            [0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1],
            [Math.floor(w / 2), 0], [Math.floor(w / 2), h - 1],
            [0, Math.floor(h / 2)], [w - 1, Math.floor(h / 2)],
        ];
        var r = 0, g = 0, b = 0, n = 0;
        corners.forEach(function (p) {
            var c = pixelAt(data, p[0], p[1], w);
            if (c[3] < 8) return;
            r += c[0]; g += c[1]; b += c[2]; n++;
        });
        if (!n) return [255, 255, 255];
        return [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
    }

    function rankHistogram(hist) {
        return Object.keys(hist).map(function (k) {
            var n = parseInt(k, 10);
            return {
                count: hist[k],
                rgb: [(n >> 16) & 255, (n >> 8) & 255, n & 255],
            };
        }).sort(function (a, b) { return b.count - a.count; });
    }

    function quantKey(rgb) {
        var qr = Math.min(255, Math.floor(rgb[0] / QUANT) * QUANT + QUANT / 2);
        var qg = Math.min(255, Math.floor(rgb[1] / QUANT) * QUANT + QUANT / 2);
        var qb = Math.min(255, Math.floor(rgb[2] / QUANT) * QUANT + QUANT / 2);
        return (qr << 16) | (qg << 8) | qb;
    }

    /**
     * Sample-window peaks (non-canvas):
     *   most prominent  → depth cue
     *   2nd prominent   → main fill
     * Shade vs highlight = depth cue darker/lighter than main.
     */
    function estimateLocalPalette(imgData, sx, sy, radius, canvas) {
        var w = imgData.width;
        var h = imgData.height;
        var data = imgData.data;
        if (!canvas) canvas = estimateCanvasColor(imgData);
        var hist = {};
        var r2 = radius * radius;
        var x0 = Math.max(0, sx - radius);
        var x1 = Math.min(w - 1, sx + radius);
        var y0 = Math.max(0, sy - radius);
        var y1 = Math.min(h - 1, sy + radius);

        for (var y = y0; y <= y1; y++) {
            for (var x = x0; x <= x1; x++) {
                if ((x - sx) * (x - sx) + (y - sy) * (y - sy) > r2) continue;
                var i = (y * w + x) * 4;
                if (data[i + 3] < 8) continue;
                var rgb = [data[i], data[i + 1], data[i + 2]];
                if (colorDist(rgb, canvas) < CANVAS_MATCH_TOLERANCE) continue;
                var key = quantKey(rgb);
                hist[key] = (hist[key] || 0) + 1;
            }
        }

        var ranked = rankHistogram(hist);
        var depthCue = ranked[0] ? ranked[0].rgb : null;
        var main = ranked[1] ? ranked[1].rgb : null;
        var layer = resolveDepthLayer(depthCue, main);
        return {
            canvas: canvas,
            depthCue: depthCue,
            main: main,
            // Keep aliases used by older probe/panel paths.
            primary: depthCue,
            secondary: main,
            primaryCount: ranked[0] ? ranked[0].count : 0,
            secondaryCount: ranked[1] ? ranked[1].count : 0,
            mode: layer.mode,
            reason: layer.reason,
            local: true,
            radius: radius,
        };
    }

    /** Depth cue vs main → shade or highlight. */
    function resolveDepthLayer(depthCue, main) {
        if (!depthCue) {
            return { mode: 'shade', reason: 'no colors in window' };
        }
        if (!main) {
            return { mode: 'shade', reason: 'only one color in window — default shade' };
        }
        var dL = luminance(depthCue);
        var mL = luminance(main);
        if (dL + 2 < mL) {
            return { mode: 'shade', reason: 'depth cue darker than main' };
        }
        if (dL > mL + 2) {
            return { mode: 'highlight', reason: 'depth cue lighter than main' };
        }
        return {
            mode: dL <= mL ? 'shade' : 'highlight',
            reason: 'depth cue ≈ main luminance — weak guess',
        };
    }

    /**
     * Classify the pixel under the cursor against the sample-window peaks.
     * Mode always comes from depth-cue vs main (most vs 2nd prominent).
     */
    function classifyColor(rgb, palette) {
        if (!palette) {
            return {
                role: 'unknown',
                label: '…',
                mode: 'shade',
                reason: 'palette not ready',
                base: null,
                rgb: rgb,
            };
        }
        var layer = resolveDepthLayer(palette.depthCue || palette.primary, palette.main || palette.secondary);
        var mode = layer.mode;
        var reason = layer.reason;
        var main = palette.main || palette.secondary;
        var depth = palette.depthCue || palette.primary;

        if (rgb[3] !== undefined && rgb[3] < 8) {
            return {
                role: 'canvas',
                label: 'Empty',
                mode: mode,
                reason: 'transparent',
                base: main,
                rgb: rgb,
            };
        }
        if (palette.canvas && colorDist(rgb, palette.canvas) < CANVAS_MATCH_TOLERANCE) {
            return {
                role: 'canvas',
                label: 'Canvas',
                mode: mode,
                reason: 'matches background',
                base: main,
                rgb: rgb,
            };
        }
        if (!depth) {
            return {
                role: 'unknown',
                label: '…',
                mode: mode,
                reason: 'no colors in window',
                base: null,
                rgb: rgb,
            };
        }

        var nearDepth = colorDist(rgb, depth) < COLOR_MATCH_TOLERANCE * 2;
        var nearMain = main && colorDist(rgb, main) < COLOR_MATCH_TOLERANCE * 2;

        if (nearMain && (!nearDepth || colorDist(rgb, main) <= colorDist(rgb, depth))) {
            return {
                role: 'main',
                label: 'Main',
                mode: mode,
                reason: '2nd peak in window',
                base: main,
                rgb: rgb,
            };
        }
        if (nearDepth) {
            return {
                role: mode,
                label: mode === 'shade' ? 'Shade' : 'Highlight',
                mode: mode,
                reason: reason,
                base: main,
                rgb: rgb,
            };
        }

        // Other color in window — still use window depth-cue decision for mode.
        return {
            role: mode,
            label: mode === 'shade' ? 'Shade' : 'Highlight',
            mode: mode,
            reason: reason + ' (cursor not on a peak)',
            base: main,
            rgb: rgb,
        };
    }

    function predictLayerType(seed, palette) {
        var layer = resolveDepthLayer(
            palette && (palette.depthCue || palette.primary),
            palette && (palette.main || palette.secondary)
        );
        return {
            mode: layer.mode,
            reason: layer.reason,
            base: palette && (palette.main || palette.secondary),
            role: layer.mode,
            depthCue: palette && (palette.depthCue || palette.primary),
        };
    }

    function roleAccent(mode) {
        // Match marker / button colors: yellow light, purple shade.
        if (mode === 'highlight') return { fill: 'rgba(245,200,40,0.95)', text: '#111' };
        return { fill: 'rgba(128,64,200,0.95)', text: '#fff' };
    }

    function effectiveMode() {
        if (!st) return 'shade';
        return st.pickMode === 'highlight' ? 'highlight' : 'shade';
    }

    function updateProbe(dispX, dispY, opts) {
        if (!st || !st.probe) return;
        opts = opts || {};
        if (opts.remove) {
            st.probe.style.background = '#b03030';
            st.probe.style.color = '#ffffff';
            st.probe.style.border = '1px solid #701818';
            st.probe.innerHTML = '<span class="cd-probe-tag">Click to remove</span>';
        } else {
            var px = st.hover && st.hover.px;
            var badge = px || [40, 40, 40];
            st.probe.style.background = rgbCss(badge);
            st.probe.style.color = luminance(badge) > 140 ? '#111111' : '#ffffff';
            st.probe.style.border = '1px solid #000000';
            st.probe.innerHTML = '<span class="cd-probe-tag">Click to add</span>';
        }
        st.probe.style.display = 'flex';

        var pad = 14;
        var left = dispX + pad;
        var top = dispY + pad;
        // Keep probe inside the image wrap.
        var wrapW = st.wrap.clientWidth;
        var wrapH = st.wrap.clientHeight;
        var ox = st.imgOx || 0;
        var oy = st.imgOy || 0;
        st.probe.style.left = '0px';
        st.probe.style.top = '0px';
        var pw = st.probe.offsetWidth || 100;
        var ph = st.probe.offsetHeight || 24;
        if (ox + left + pw > wrapW - 4) left = dispX - pw - pad;
        if (oy + top + ph > wrapH - 4) top = dispY - ph - pad;
        st.probe.style.left = (ox + Math.max(0, left)) + 'px';
        st.probe.style.top = (oy + Math.max(0, top)) + 'px';
    }

    function updateMagnifier(sx, sy, dispX, dispY, cls) {
        if (!st || !st.loupe || !st.srcCanvas) {
            if (st && st.loupe) st.loupe.style.display = 'none';
            return;
        }
        var size = MAG_SIZE;
        var zoom = MAG_ZOOM;
        var r = size / 2;
        var loupe = st.loupe;
        if (loupe.width !== size) {
            loupe.width = size;
            loupe.height = size;
        }
        var lctx = loupe.getContext('2d');
        lctx.clearRect(0, 0, size, size);

        lctx.save();
        lctx.beginPath();
        lctx.arc(r, r, r - 1.5, 0, Math.PI * 2);
        lctx.clip();

        // Crisp magnified native pixels centered on (sx, sy).
        var srcHalf = (size / zoom) / 2;
        lctx.imageSmoothingEnabled = false;
        lctx.drawImage(
            st.srcCanvas,
            sx + 0.5 - srcHalf, sy + 0.5 - srcHalf, size / zoom, size / zoom,
            0, 0, size, size
        );

        // Crosshair on the pixel the user is choosing. No generated sample ring.
        lctx.strokeStyle = 'rgba(0,0,0,0.75)';
        lctx.lineWidth = 1;
        lctx.beginPath();
        lctx.moveTo(r - 8, r);
        lctx.lineTo(r + 8, r);
        lctx.moveTo(r, r - 8);
        lctx.lineTo(r, r + 8);
        lctx.stroke();
        lctx.strokeStyle = 'rgba(255,255,255,0.9)';
        lctx.beginPath();
        lctx.moveTo(r - 7, r);
        lctx.lineTo(r + 7, r);
        lctx.moveTo(r, r - 7);
        lctx.lineTo(r, r + 7);
        lctx.stroke();
        lctx.restore();

        // Outer ring.
        lctx.beginPath();
        lctx.arc(r, r, r - 1.5, 0, Math.PI * 2);
        lctx.strokeStyle = '#111111';
        lctx.lineWidth = 3;
        lctx.stroke();
        lctx.beginPath();
        lctx.arc(r, r, r - 1.5, 0, Math.PI * 2);
        lctx.strokeStyle = 'rgba(0,0,0,0.55)';
        lctx.lineWidth = 1;
        lctx.stroke();

        loupe.style.display = 'block';
        var ox = st.imgOx || 0;
        var oy = st.imgOy || 0;
        // Center loupe on the cursor.
        var left = dispX - size / 2;
        var top = dispY - size / 2;
        loupe.style.left = (ox + left) + 'px';
        loupe.style.top = (oy + top) + 'px';
    }

    function hideMagnifier() {
        if (st && st.loupe) st.loupe.style.display = 'none';
    }

    function renderPalettePanel(palette) {
        if (!st) return;
        var host = st.card.querySelector('[data-palette]');
        if (!host) return;
        var p = palette || st.localPalette;
        var depth = p && (p.depthCue || p.primary);
        var main = p && (p.main || p.secondary);
        if (!depth) {
            host.innerHTML = '<div class="cd-palette-empty">Hover the image</div>';
            return;
        }
        var mode = effectiveMode();
        host.innerHTML =
            '<div class="cd-palette-row">'
            + '<span class="cd-probe-tag" style="display:inline-block;padding:4px 10px;border-radius:4px;'
            + (mode === 'highlight'
                ? 'background:#fff;color:#111;border:1px solid #111;'
                : 'background:#111;color:#fff;border:1px solid #111;')
            + '">' + MODE[mode].label + '</span>'
            + '</div>';
    }

    // Same color (within tight tolerance) → same group number. First new color → 1,
    // next distinct color → 2, etc. Order is first-seen among current selections.
    function assignColorGroup(seed) {
        var maxGroup = 0;
        for (var i = 0; i < st.selections.length; i++) {
            var sel = st.selections[i];
            if (sel.colorGroup > maxGroup) maxGroup = sel.colorGroup;
            if (colorDist(sel.seed, seed) < COLOR_MATCH_TOLERANCE) {
                return sel.colorGroup;
            }
        }
        return maxGroup + 1;
    }

    // After undo/clear, renumber groups by first-seen order so gaps don't linger.
    function reindexColorGroups() {
        if (!st) return;
        var reps = [];
        st.selections.forEach(function (sel) {
            var found = -1;
            for (var i = 0; i < reps.length; i++) {
                if (colorDist(reps[i], sel.seed) < COLOR_MATCH_TOLERANCE) {
                    found = i;
                    break;
                }
            }
            if (found < 0) {
                reps.push(sel.seed.slice(0, 3));
                sel.colorGroup = reps.length;
            } else {
                sel.colorGroup = found + 1;
            }
        });
    }

    // Circle sample in native pixel space. Returns seed color, pixel count, and
    // which 3×3 sections the circle touches.
    function circleSample(imgData, sx, sy, radius) {
        var w = imgData.width;
        var h = imgData.height;
        var data = imgData.data;
        var seed = pixelAt(data, sx, sy, w);
        var count = 0;
        var sectionSet = {};
        var g = st && st.gridSections ? st.gridSections : 0;
        var cw = g ? w / g : 0;
        var ch = g ? h / g : 0;
        var r2 = radius * radius;
        var x0 = Math.max(0, sx - radius);
        var x1 = Math.min(w - 1, sx + radius);
        var y0 = Math.max(0, sy - radius);
        var y1 = Math.min(h - 1, sy + radius);

        for (var y = y0; y <= y1; y++) {
            for (var x = x0; x <= x1; x++) {
                var dx = x - sx;
                var dy = y - sy;
                if (dx * dx + dy * dy > r2) continue;
                count++;
                if (g) {
                    var sRow = Math.min(g - 1, Math.floor(y / ch));
                    var sCol = Math.min(g - 1, Math.floor(x / cw));
                    sectionSet[sRow + ',' + sCol] = true;
                }
            }
        }
        return {
            count: count,
            seed: seed,
            radius: radius,
            sections: Object.keys(sectionSet),
        };
    }

    function getSectionCounts() {
        var counts = {};
        var g = st ? st.gridSections : 0;
        for (var r = 0; r < g; r++)
            for (var c = 0; c < g; c++)
                counts[r + ',' + c] = 0;
        if (!st) return counts;
        st.selections.forEach(function (sel) {
            var secs = sel.sections || (sel.section ? [sel.section] : []);
            secs.forEach(function (key) {
                if (counts[key] != null) counts[key] += 1;
            });
        });
        return counts;
    }

    function renderSectionPanel() {
        if (!st || !st.sectionHost || !st.gridSections) return;
        var counts = getSectionCounts();
        var needed = st.samplesPerSection || 1;
        var total = st.gridSections * st.gridSections;
        var ignoredCount = 0;
        for (var ik in st.ignoredSections) ignoredCount += 1;
        var active = total - ignoredCount;
        var totalNeeded = active * needed;
        var totalDone = 0;
        var sectionsDone = 0;
        for (var k in counts) {
            if (st.ignoredSections[k]) continue;
            totalDone += Math.min(counts[k], needed);
            if (counts[k] >= needed) sectionsDone += 1;
        }
        var pct = totalNeeded > 0 ? Math.round(100 * totalDone / totalNeeded) : 100;

        var html = ''
            + '<div class="cd-panel-meter"><div class="cd-panel-meter-fill" style="width:' + pct + '%;"></div></div>'
            + '<div class="cd-panel-meter-label">'
            +   sectionsDone + ' / ' + active + ' sections complete'
            +   ' <span style="opacity:.6;">(' + totalDone + '/' + totalNeeded
            +   (ignoredCount ? ', ' + ignoredCount + ' skipped' : '') + ')</span>'
            + '</div>'
            + '<div class="cd-panel-grid">';
        for (var r = 0; r < st.gridSections; r++) {
            for (var c = 0; c < st.gridSections; c++) {
                var key = r + ',' + c;
                var n = counts[key] || 0;
                var cls, content;
                if (st.ignoredSections[key]) {
                    cls = 'cd-cell-skip';
                    content = '—';
                } else if (n >= needed) {
                    cls = 'cd-cell-done';
                    content = '✓';
                } else if (n > 0) {
                    cls = 'cd-cell-partial';
                    content = n + '/' + needed;
                } else {
                    cls = 'cd-cell-empty';
                    content = '0/' + needed;
                }
                html += '<div class="cd-cell ' + cls + '" data-section="' + key
                    + '" title="Click to ' + (st.ignoredSections[key] ? 'include' : 'skip')
                    + ' this section">' + content + '</div>';
            }
        }
        html += '</div>'
            + '<div class="cd-panel-hint">Click a section to skip it if there is nothing to sample there.</div>';

        st.sectionHost.innerHTML = html;
        var cells = st.sectionHost.querySelectorAll('.cd-cell[data-section]');
        for (var i = 0; i < cells.length; i++) {
            cells[i].addEventListener('click', (function (sec) {
                return function () {
                    if (st.ignoredSections[sec]) delete st.ignoredSections[sec];
                    else st.ignoredSections[sec] = true;
                    renderSectionPanel();
                };
            })(cells[i].getAttribute('data-section')));
        }
    }

    function uniqueColorRows(mode) {
        // One row per unique color (colorGroup) within this mode; count = how many samples.
        var byGroup = {};
        var order = [];
        st.selections.forEach(function (sel) {
            if (sel.mode !== mode) return;
            var g = sel.colorGroup || 0;
            if (!byGroup[g]) {
                byGroup[g] = { group: g, seed: sel.seed, times: 0 };
                order.push(g);
            }
            byGroup[g].times += 1;
        });
        return order.map(function (g) { return byGroup[g]; });
    }

    function layerItemHtml(row, mode) {
        var times = row.times;
        return '<div class="cd-layer-item">'
            + '<span class="cd-layer-swatch" style="background:' + rgbCss(row.seed) + '"></span>'
            + '<span class="cd-layer-meta">#' + row.group
            + ' · ×' + times
            + (times === 1 ? ' sample' : ' samples')
            + '</span>'
            + '<button type="button" class="cd-layer-x" title="Remove this color"'
            + ' data-remove-group="' + row.group + '" data-remove-mode="' + mode + '">×</button>'
            + '</div>';
    }

    function removeColorGroup(mode, group) {
        if (!st) return;
        group = parseInt(group, 10);
        var kept = [];
        var removed = [];
        st.selections.forEach(function (sel) {
            if (sel.mode === mode && sel.colorGroup === group) removed.push(sel);
            else kept.push(sel);
        });
        if (!removed.length) return;
        st.selections = kept;
        reindexColorGroups();
        redraw();
        renderList();
        renderSectionPanel();
        removed.forEach(function (sel) {
            removePersisted(sel).catch(function (err) {
                console.error('color depth sample remove failed', err);
            });
        });
    }

    function bindLayerRemoveButtons(host) {
        if (!host) return;
        host.querySelectorAll('[data-remove-group]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                removeColorGroup(
                    btn.getAttribute('data-remove-mode'),
                    btn.getAttribute('data-remove-group')
                );
            });
        });
    }

    function selectionsInPath(pathId) {
        var out = [];
        st.selections.forEach(function (sel) {
            if (sel.pathId === pathId) out.push(sel);
        });
        return out;
    }

    function pointLabel(sel) {
        if (!sel || sel.pathRole === 'main' || pathStep(sel) <= 1) return 'M';
        return String(pathStep(sel) - 1);
    }
    function pathStep(sel) {
        var n = 0;
        for (var i = 0; i < st.selections.length; i++) {
            if (st.selections[i].pathId !== sel.pathId) continue;
            n += 1;
            if (st.selections[i] === sel) return n;
        }
        return n;
    }

    function refreshPathRoles() {
        if (!st) return;
        st.paths.forEach(function (path) {
            selectionsInPath(path.id).forEach(function (sel, i) {
                sel.pathRole = i === 0 ? 'main' : 'depth';
                sel.mode = path.kind;
            });
        });
        st.paths = st.paths.filter(function (path) {
            if (st.openPath && st.openPath.id === path.id) return true;
            return selectionsInPath(path.id).length > 0;
        });
        if (st.openPath && st.paths.indexOf(st.openPath) < 0) st.openPath = null;
    }

    function setPathHint(text) {
        if (!st) return;
        var hint = st.card.querySelector('[data-mode-hint]');
        if (hint) hint.textContent = text;
    }

    function applyCursor(hit) {
        if (!st || !st.overlay) return;
        if (hit >= 0) {
            st.overlay.style.cursor = 'pointer';
            return;
        }
        st.overlay.style.cursor = hit >= 0 ? 'pointer' : (st.openPath ? 'crosshair' : 'default');
    }

    function syncDrawChrome() {
        if (!st) return;
        var drawing = !!st.openPath;
        if (st.overlay) st.overlay.classList.toggle('is-drawing', drawing);
        if (st.wrap) st.wrap.classList.toggle('is-drawing', drawing);
        applyCursor(st.hoverMarkerIdx);
        if (!st.srcReady || !st.banner) return;
        if (!drawing) {
            st.banner.style.display = 'none';
            st.banner.classList.remove('is-drawing');
            return;
        }
        var n = selectionsInPath(st.openPath.id).length;
        var kind = st.openPath.kind === 'highlight' ? 'light' : st.openPath.kind === 'shade' ? 'dark' : '';
        st.banner.style.display = 'block';
        st.banner.classList.remove('error');
        st.banner.classList.add('is-drawing');
        st.banner.textContent = n === 0
            ? 'DRAWING — click the main color. Press S for the next path.'
            : ('DRAWING' + (kind ? ' a ' + kind + ' path' : '') + ' — click the next color. Press S for the next path.');
    }

    function syncPathChrome() {
        if (!st) return;
        syncDrawChrome();
        if (!st.openPath) {
            setPathHint('Press S to start a path. The first color is Main.');
            return;
        }
        var n = selectionsInPath(st.openPath.id).length;
        var kind = st.openPath.kind === 'highlight' ? 'Light' : st.openPath.kind === 'shade' ? 'Dark' : '';
        if (!n) {
            setPathHint('Drawing — click the main color, then each depth color. Press S to start the next path.');
            return;
        }
        setPathHint(
            (kind ? kind + ' path. ' : 'Drawing. ')
            + 'Click the next color, or press S to start the next path.'
        );
    }

    function closeOpenPath() {
        if (!st || !st.openPath) return;
        var path = st.openPath;
        st.openPath = null;
        if (!selectionsInPath(path.id).length) {
            st.paths = st.paths.filter(function (item) { return item.id !== path.id; });
            return;
        }
        flushPath(path);
    }

    function inferPathKind(path) {
        var pts = selectionsInPath(path.id);
        if (pts.length < 2) return null;
        var mainL = luminance(pts[0].seed);
        var nextL = luminance(pts[1].seed);
        return nextL >= mainL ? 'highlight' : 'shade';
    }

    function enqueueSave(work) {
        if (!st) return Promise.resolve();
        var run = st.saveQueue.then(work, work);
        st.saveQueue = run.then(function () { return null; }, function () { return null; });
        return run;
    }

    function deletePersistedPath(pathIndex) {
        return enqueueSave(function () {
            if (!st || !st.removeSample || !st.assetId || !st.labelerId) return null;
            return st.removeSample({
                asset_id: parseInt(st.assetId, 10),
                labeler_id: st.labelerId,
                path_index: pathIndex,
            });
        });
    }

    function flushPath(path) {
        if (!st || !path || !st.saveSample) return Promise.resolve();
        var pathIndex = path.id;
        return enqueueSave(function () {
            if (!st) return null;
            var pts = selectionsInPath(pathIndex);
            var clear = Promise.resolve();
            if (st.removeSample && st.assetId && st.labelerId) {
                clear = Promise.resolve(st.removeSample({
                    asset_id: parseInt(st.assetId, 10),
                    labeler_id: st.labelerId,
                    path_index: pathIndex,
                }));
            }
            return clear.then(function () {
                if (!pts.length) {
                    path.persisted = false;
                    return null;
                }
                var chain = Promise.resolve();
                pts.forEach(function (sel, i) {
                    chain = chain.then(function () {
                        return Promise.resolve(st.saveSample({
                            asset_id: parseInt(st.assetId, 10),
                            labeler_id: st.labelerId,
                            path_index: pathIndex,
                            point_index: i,
                            path_kind: path.kind || null,
                            color_hex: toHex(sel.seed),
                            x_coord: sel.x,
                            y_coord: sel.y,
                            image_width: st.natW,
                            image_height: st.natH,
                            pixel_count: sel.count,
                        })).then(function (res) {
                            sel.savedId = res && res.saved_id != null ? res.saved_id : null;
                            sel.pending = false;
                            sel.saveError = null;
                        });
                    });
                });
                return chain.then(function () {
                    path.persisted = true;
                });
            });
        });
    }

    function flushAll() {
        if (!st) return Promise.resolve();
        var paths = st.paths.filter(function (path) {
            return selectionsInPath(path.id).length > 0;
        });
        return paths.reduce(function (chain, path) {
            return chain.then(function () { return flushPath(path); });
        }, Promise.resolve());
    }

    function syncClosedPath(path) {
        if (!path || (st.openPath && st.openPath.id === path.id)) return;
        if (!selectionsInPath(path.id).length) deletePersistedPath(path.id);
        else flushPath(path);
    }

    function applyInferredKind(path) {
        if (!path) return false;
        var kind = inferPathKind(path);
        if (path.kind === kind) return false;
        path.kind = kind;
        refreshPathRoles();
        return true;
    }

    function togglePath() {
        if (!st) return;
        if (st.openPath) closeOpenPath();
        var path = { id: ++st.pathSeq, kind: null };
        st.paths.push(path);
        st.openPath = path;
        syncPathChrome();
        redraw();
        renderList();
    }

    function drawDepthPaths(ctx) {
        st.paths.forEach(function (path) {
            var pts = selectionsInPath(path.id);
            if (pts.length < 2) return;
            ctx.beginPath();
            var started = false;
            pts.forEach(function (sel) {
                var m = markerLayout(sel);
                if (!m) return;
                if (!started) {
                    ctx.moveTo(m.cx, m.cy);
                    started = true;
                } else {
                    ctx.lineTo(m.cx, m.cy);
                }
            });
            if (!started) return;
            ctx.lineJoin = 'round';
            ctx.lineCap = 'round';
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 6;
            ctx.stroke();
            ctx.strokeStyle = path.kind === 'highlight' ? '#d4a020' : path.kind === 'shade' ? '#8040c8' : '#409393';
            ctx.lineWidth = 3;
            ctx.stroke();
        });
    }

    function renderDepthList(host) {
        if (!st.paths.length) {
            host.innerHTML = '<div class="cd-layer-empty">Press S to start a path.</div>';
            return;
        }
        host.innerHTML = st.paths.map(function (path) {
            var pts = selectionsInPath(path.id);
            var light = path.kind === 'highlight';
            var dark = path.kind === 'shade';
            var open = st.openPath && st.openPath.id === path.id;
            var kindName = light ? 'Light' : dark ? 'Dark' : 'Not set yet';
            var colors = pts.length
                ? pts.map(function (sel) {
                    var idx = st.selections.indexOf(sel);
                    var role = pointLabel(sel);
                    return '<div class="cd-layer-item">'
                        + '<span class="cd-layer-swatch" style="background:' + rgbCss(sel.seed) + '"></span>'
                        + '<span class="cd-layer-meta"><strong>' + role + '</strong> · ' + toHex(sel.seed) + '</span>'
                        + '<button type="button" class="cd-layer-x" title="Remove this color"'
                        + ' data-remove-index="' + idx + '">×</button>'
                        + '</div>';
                }).join('')
                : '<div class="cd-layer-empty">Click the image. The first color is Main.</div>';
            return '<section class="cd-depth-path ' + (light ? 'is-light' : dark ? 'is-dark' : '') + (open ? ' is-open' : '') + '">'
                + '<div class="cd-depth-path-title">'
                + '<span>Depth path</span>'
                + '<span class="cd-depth-path-kind">' + kindName + (open ? ' · drawing' : '') + '</span>'
                + '<button type="button" class="cd-layer-x cd-path-x" title="Remove this path"'
                + ' data-remove-path="' + path.id + '">×</button>'
                + '</div>'
                + '<div class="cd-depth-path-colors">' + colors + '</div>'
                + '</section>';
        }).join('');
        host.querySelectorAll('[data-remove-path]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                removePath(parseInt(btn.getAttribute('data-remove-path'), 10));
            });
        });
        host.querySelectorAll('[data-remove-index]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                removeSelectionAt(parseInt(btn.getAttribute('data-remove-index'), 10));
            });
        });
    }

    function renderList() {
        if (!st) return;
        var depthHost = st.card.querySelector('[data-depth-list]');
        if (depthHost) {
            renderDepthList(depthHost);
            return;
        }
        var shadeHost = st.card.querySelector('[data-shade-list]');
        var lightHost = st.card.querySelector('[data-light-list]');
        if (!shadeHost && !lightHost) return;

        var shadeRows = uniqueColorRows('shade');
        var lightRows = uniqueColorRows('highlight');

        if (shadeHost) {
            shadeHost.innerHTML = shadeRows.length
                ? shadeRows.map(function (row) { return layerItemHtml(row, 'shade'); }).join('')
                : '<div class="cd-layer-empty">None yet</div>';
            bindLayerRemoveButtons(shadeHost);
        }
        if (lightHost) {
            lightHost.innerHTML = lightRows.length
                ? lightRows.map(function (row) { return layerItemHtml(row, 'highlight'); }).join('')
                : '<div class="cd-layer-empty">None yet</div>';
            bindLayerRemoveButtons(lightHost);
        }
    }

    function setPickMode(pick) {
        if (!st || !PICK[pick]) return;
        st.pickMode = pick;
        st.card.querySelectorAll('[data-mode]').forEach(function (btn) {
            btn.classList.toggle('active', btn.getAttribute('data-mode') === pick);
        });
        var hint = st.card.querySelector('[data-mode-hint]');
        if (hint) {
            hint.textContent = MODE[pick].label + ' mode — click to place a sample (1 Shade, 2 Light)';
        }
        renderPalettePanel(st.localPalette);
        if (st.hover) {
            updateProbe(st.hover.dx, st.hover.dy);
            scheduleHoverDraw();
        }
    }

    function sizeOverlay() {
        if (!st) return;
        var img = st.img;
        st.natW = img.naturalWidth || 1;
        st.natH = img.naturalHeight || 1;
        // Img element may fill the wrap with object-fit:contain — map overlay
        // to the letterboxed content box so clicks stay aligned.
        var elW = img.clientWidth || img.offsetWidth;
        var elH = img.clientHeight || img.offsetHeight;
        var fit = Math.min(elW / st.natW, elH / st.natH);
        st.dispW = st.natW * fit;
        st.dispH = st.natH * fit;
        st.imgOx = img.offsetLeft + (elW - st.dispW) / 2;
        st.imgOy = img.offsetTop + (elH - st.dispH) / 2;
        st.overlay.width = Math.max(1, Math.round(st.dispW));
        st.overlay.height = Math.max(1, Math.round(st.dispH));
        st.overlay.style.left = st.imgOx + 'px';
        st.overlay.style.top = st.imgOy + 'px';
        st.overlay.style.width = st.dispW + 'px';
        st.overlay.style.height = st.dispH + 'px';
    }

    function redraw() {
        if (!st) return;
        var ctx = st.overlay.getContext('2d');
        ctx.clearRect(0, 0, st.overlay.width, st.overlay.height);

        // Section fills: empty clear, partial yellow, skipped gray.
        // Done sections: no fill — thicker green outline instead.
        if (st.gridSections) {
            var counts = getSectionCounts();
            var needed = st.samplesPerSection || 1;
            var cw = st.dispW / st.gridSections;
            var ch = st.dispH / st.gridSections;
            var doneKeys = [];
            for (var r = 0; r < st.gridSections; r++) {
                for (var c = 0; c < st.gridSections; c++) {
                    var key = r + ',' + c;
                    if (st.ignoredSections[key]) {
                        ctx.fillStyle = 'rgba(120, 120, 130, 0.28)';
                        ctx.fillRect(c * cw, r * ch, cw, ch);
                    } else if ((counts[key] || 0) >= needed) {
                        doneKeys.push({ r: r, c: c });
                    } else if ((counts[key] || 0) > 0) {
                        ctx.fillStyle = 'rgba(255, 200, 0, 0.18)';
                        ctx.fillRect(c * cw, r * ch, cw, ch);
                    }
                }
            }
            ctx.strokeStyle = 'rgba(255, 60, 60, 0.85)';
            ctx.lineWidth = 1;
            for (var i = 1; i < st.gridSections; i++) {
                ctx.beginPath();
                ctx.moveTo(i * cw + 0.5, 0);
                ctx.lineTo(i * cw + 0.5, st.dispH);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(0, i * ch + 0.5);
                ctx.lineTo(st.dispW, i * ch + 0.5);
                ctx.stroke();
            }
            // Thicker green outline for completed panels (no green tint).
            ctx.strokeStyle = 'rgba(20, 180, 60, 0.95)';
            ctx.lineWidth = 3;
            doneKeys.forEach(function (d) {
                ctx.strokeRect(
                    d.c * cw + 1.5,
                    d.r * ch + 1.5,
                    cw - 3,
                    ch - 3
                );
            });
        }

        var scaleX = st.dispW / st.natW;
        var scaleY = st.dispH / st.natH;

        drawDepthPaths(ctx);

        // Markers drawn last so they sit above the path line.
        st.selections.forEach(function (sel, selIdx) {
            var m = markerLayout(sel);
            if (!m) return;
            var cx = m.cx;
            var cy = m.cy;
            var lx = cx;
            var ly = cy;
            var badgeR = m.badgeR;
            var label = pointLabel(sel);
            var badgeRgb = (sel.seed && sel.seed.length >= 3) ? sel.seed : [40, 40, 40];
            var removing = selIdx === st.hoverMarkerIdx;

            var badgeLabel = removing ? '×' : label;
            ctx.font = 'bold 11px Roboto, sans-serif';
            var textW = ctx.measureText(badgeLabel).width;
            var pillW = Math.max(22, textW + 10);
            var pillH = 18;
            var pillR = 9;
            ctx.beginPath();
            ctx.moveTo(lx - pillW / 2 + pillR, ly - pillH / 2);
            ctx.arcTo(lx + pillW / 2, ly - pillH / 2, lx + pillW / 2, ly + pillH / 2, pillR);
            ctx.arcTo(lx + pillW / 2, ly + pillH / 2, lx - pillW / 2, ly + pillH / 2, pillR);
            ctx.arcTo(lx - pillW / 2, ly + pillH / 2, lx - pillW / 2, ly - pillH / 2, pillR);
            ctx.arcTo(lx - pillW / 2, ly - pillH / 2, lx + pillW / 2, ly - pillH / 2, pillR);
            ctx.closePath();
            ctx.fillStyle = removing ? '#b03030' : rgbCss(badgeRgb);
            ctx.fill();
            ctx.lineWidth = removing ? 3 : 2;
            ctx.strokeStyle = '#000000';
            ctx.stroke();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.lineWidth = 3;
            ctx.strokeStyle = removing ? '#000000' : (luminance(badgeRgb) > 140 ? '#ffffff' : '#000000');
            ctx.strokeText(badgeLabel, lx, ly);
            ctx.fillStyle = removing ? '#ffffff' : (luminance(badgeRgb) > 140 ? '#111111' : '#ffffff');
            ctx.fillText(badgeLabel, lx, ly);
        });
    }

    function markerLayout(sel) {
        if (!st || !sel) return null;
        var scaleX = st.dispW / st.natW;
        var scaleY = st.dispH / st.natH;
        var cx = (sel.x + 0.5) * scaleX;
        var cy = (sel.y + 0.5) * scaleY;
        // Fixed on-screen size so markers don't grow when the image is scaled up.
        var badgeR = MARKER_BADGE_R;
        return {
            cx: cx,
            cy: cy,
            lx: cx,
            ly: cy,
            pinR: badgeR,
            badgeR: badgeR,
            hitPinR: badgeR + 2,
            hitBadgeR: badgeR + 2,
        };
    }

    function hitTestMarker(dispX, dispY) {
        if (!st || !st.selections.length) return -1;
        // Only the larger number badge is clickable/hoverable for remove — not the pin.
        for (var i = st.selections.length - 1; i >= 0; i--) {
            var m = markerLayout(st.selections[i]);
            if (!m) continue;
            var dBadge = (dispX - m.lx) * (dispX - m.lx) + (dispY - m.ly) * (dispY - m.ly);
            if (dBadge <= m.hitBadgeR * m.hitBadgeR) return i;
        }
        return -1;
    }

    function removePath(pathId) {
        if (!st) return;
        var removed = [];
        st.selections = st.selections.filter(function (sel) {
            if (sel.pathId !== pathId) return true;
            removed.push(sel);
            return false;
        });
        st.paths = st.paths.filter(function (path) { return path.id !== pathId; });
        if (st.openPath && st.openPath.id === pathId) st.openPath = null;
        refreshPathRoles();
        syncPathChrome();
        reindexColorGroups();
        redraw();
        renderList();
        renderSectionPanel();
        deletePersistedPath(pathId).catch(function (err) {
            console.error('color depth path remove failed', err);
        });
    }

    function removeSelectionAt(index) {
        if (!st || index < 0 || index >= st.selections.length) return;
        var sel = st.selections.splice(index, 1)[0];
        var pathId = sel.pathId;
        var path = null;
        st.paths.forEach(function (item) { if (item.id === pathId) path = item; });
        refreshPathRoles();
        if (path) applyInferredKind(path);
        syncPathChrome();
        reindexColorGroups();
        redraw();
        renderList();
        renderSectionPanel();
        syncClosedPath(path);
    }

    function pointerToNative(event) {
        var rect = st.overlay.getBoundingClientRect();
        var dx = event.clientX - rect.left;
        var dy = event.clientY - rect.top;
        if (dx < 0 || dy < 0 || dx >= st.dispW || dy >= st.dispH) return null;
        var sx = Math.floor(dx * (st.natW / st.dispW));
        var sy = Math.floor(dy * (st.natH / st.dispH));
        sx = Math.max(0, Math.min(st.natW - 1, sx));
        sy = Math.max(0, Math.min(st.natH - 1, sy));
        return { dx: dx, dy: dy, sx: sx, sy: sy };
    }

    function scheduleHoverDraw() {
        if (!st || st._hoverRaf) return;
        st._hoverRaf = requestAnimationFrame(function () {
            st._hoverRaf = null;
            redraw();
        });
    }

    function onMove(event) {
        if (!st || !st.srcReady || !st.imgData) {
            if (st && st.probe) st.probe.style.display = 'none';
            hideMagnifier();
            return;
        }
        var pos = pointerToNative(event);
        if (!pos) {
            st.hover = null;
            st.hoverMarkerIdx = -1;
            st.localPalette = null;
            if (st.probe) st.probe.style.display = 'none';
            hideMagnifier();
            renderPalettePanel(null);
            scheduleHoverDraw();
            return;
        }
        var hit = hitTestMarker(pos.dx, pos.dy);
        st.hoverMarkerIdx = hit;
        var local = estimateLocalPalette(
            st.imgData, pos.sx, pos.sy, SAMPLE_RADIUS, st.canvasColor
        );
        st.localPalette = local;
        var px = pixelAt(st.imgData.data, pos.sx, pos.sy, st.natW);
        var cls = classifyColor(px, local);
        st.hover = { dx: pos.dx, dy: pos.dy, sx: pos.sx, sy: pos.sy, cls: cls, px: px };
        if (hit >= 0) {
            updateProbe(pos.dx, pos.dy, { remove: true });
            hideMagnifier();
        } else if (!st.openPath) {
            if (st.probe) st.probe.style.display = 'none';
            hideMagnifier();
        } else {
            updateProbe(pos.dx, pos.dy);
            updateMagnifier(pos.sx, pos.sy, pos.dx, pos.dy, cls);
        }
        renderPalettePanel(local);
        applyCursor(hit);
        scheduleHoverDraw();
    }

    function onLeave() {
        if (!st) return;
        st.hover = null;
        st.hoverMarkerIdx = -1;
        st.localPalette = null;
        if (st.probe) st.probe.style.display = 'none';
        hideMagnifier();
        renderPalettePanel(null);
        applyCursor(-1);
        scheduleHoverDraw();
    }

    function onClick(event) {
        if (!st || !st.srcReady || !st.imgData) return;
        sizeOverlay();
        var pos = pointerToNative(event);
        if (!pos) return;

        // Click an existing marker to remove it.
        var hit = hitTestMarker(pos.dx, pos.dy);
        if (hit >= 0) {
            removeSelectionAt(hit);
            return;
        }
        if (!st.openPath) {
            setPathHint('Press S to start a path.');
            return;
        }

        var sx = pos.sx;
        var sy = pos.sy;

        var result = circleSample(st.imgData, sx, sy, SAMPLE_RADIUS);
        if (!result.count) return;

        // Always credit the section containing the click center (plus any the
        // circle overlaps), and re-include it if it had been marked skipped.
        var centerSection = null;
        if (st.gridSections) {
            var cw = st.natW / st.gridSections;
            var ch = st.natH / st.gridSections;
            centerSection = Math.min(st.gridSections - 1, Math.floor(sy / ch))
                + ',' + Math.min(st.gridSections - 1, Math.floor(sx / cw));
        }
        var sections = result.sections || [];
        if (centerSection && sections.indexOf(centerSection) < 0) sections.push(centerSection);
        sections.forEach(function (key) {
            if (st.ignoredSections[key]) delete st.ignoredSections[key];
        });

        var seed = result.seed.slice(0, 3);
        var local = estimateLocalPalette(
            st.imgData, sx, sy, SAMPLE_RADIUS, st.canvasColor
        );
        st.localPalette = local;
        renderPalettePanel(local);
        var pathPts = selectionsInPath(st.openPath.id);
        var sel = {
            mode: st.openPath.kind,
            pathId: st.openPath.id,
            pathRole: pathPts.length ? 'depth' : 'main',
            seed: seed,
            colorGroup: assignColorGroup(seed),
            count: result.count,
            radius: result.radius,
            x: sx,
            y: sy,
            sections: sections,
            sampleIndex: st.selections.length + 1,
            predicted: null,
            savedId: null,
            pending: false,
        };
        st.selections.push(sel);
        refreshPathRoles();
        applyInferredKind(st.openPath);
        syncPathChrome();
        redraw();
        renderList();
        renderSectionPanel();
    }

    function toHex(rgb) {
        function h(n) {
            var s = Math.max(0, Math.min(255, n | 0)).toString(16);
            return s.length === 1 ? '0' + s : s;
        }
        return '#' + h(rgb[0]) + h(rgb[1]) + h(rgb[2]);
    }

    function undo() {
        if (!st || !st.selections.length) return;
        var sel = st.selections.pop();
        var pathId = sel.pathId;
        var path = null;
        st.paths.forEach(function (item) { if (item.id === pathId) path = item; });
        refreshPathRoles();
        if (path) applyInferredKind(path);
        syncPathChrome();
        reindexColorGroups();
        redraw();
        renderList();
        renderSectionPanel();
        syncClosedPath(path);
    }

    function clearSelections() {
        if (!st) return;
        st.selections = [];
        st.paths = [];
        st.openPath = null;
        st.pathSeq = 0;
        syncPathChrome();
        reindexColorGroups();
        redraw();
        renderList();
        renderSectionPanel();
        if (st.removeSample && st.assetId && st.labelerId) {
            enqueueSave(function () {
                return st.removeSample({
                    asset_id: parseInt(st.assetId, 10),
                    labeler_id: st.labelerId,
                });
            }).catch(function (err) {
                console.error('color depth clear failed', err);
            });
        }
    }

    function loadPixels() {
        var proxyUrl = '/label_images/image_proxy/?url=' + encodeURIComponent(st.img.src);
        var img2 = new Image();
        img2.onload = function () {
            try {
                var c = document.createElement('canvas');
                c.width = st.natW;
                c.height = st.natH;
                var ctx = c.getContext('2d', { willReadFrequently: true });
                ctx.drawImage(img2, 0, 0, st.natW, st.natH);
                st.srcCanvas = c;
                st.imgData = ctx.getImageData(0, 0, st.natW, st.natH);
                st.canvasColor = estimateCanvasColor(st.imgData);
                st.srcReady = true;
                sizeOverlay();
                redraw();
                renderPalettePanel(null);
                syncDrawChrome();
            } catch (err) {
                if (st.banner) {
                    st.banner.textContent = 'Pixel data unavailable';
                    st.banner.classList.add('error');
                }
            }
        };
        img2.onerror = function () {
            var img3 = new Image();
            img3.crossOrigin = 'anonymous';
            img3.onload = function () {
                try {
                    var c = document.createElement('canvas');
                    c.width = st.natW;
                    c.height = st.natH;
                    var ctx = c.getContext('2d', { willReadFrequently: true });
                    ctx.drawImage(img3, 0, 0, st.natW, st.natH);
                    st.srcCanvas = c;
                    st.imgData = ctx.getImageData(0, 0, st.natW, st.natH);
                    st.canvasColor = estimateCanvasColor(st.imgData);
                    st.srcReady = true;
                    sizeOverlay();
                    redraw();
                    renderPalettePanel(null);
                    syncDrawChrome();
                } catch (err2) {
                    if (st.banner) {
                        st.banner.textContent = 'Pixel data unavailable';
                        st.banner.classList.add('error');
                    }
                }
            };
            img3.onerror = function () {
                if (st.banner) {
                    st.banner.textContent = 'Pixel data unavailable';
                    st.banner.classList.add('error');
                }
            };
            img3.src = st.img.src;
        };
        img2.src = proxyUrl;
    }

    function bindUi() {
        st.card.querySelectorAll('[data-mode]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                setPickMode(btn.getAttribute('data-mode'));
            });
        });
        var undoBtn = st.card.querySelector('[data-undo]');
        if (undoBtn) undoBtn.addEventListener('click', undo);
        var clearBtn = st.card.querySelector('[data-clear]');
        if (clearBtn) clearBtn.addEventListener('click', clearSelections);
    }

    function onResize() {
        if (!st) return;
        sizeOverlay();
        redraw();
    }

    function teardown() {
        if (!st) return;
        if (st.overlay && st.overlay.parentNode) st.overlay.parentNode.removeChild(st.overlay);
        if (st.banner && st.banner.parentNode) st.banner.parentNode.removeChild(st.banner);
        if (st.probe && st.probe.parentNode) st.probe.parentNode.removeChild(st.probe);
        if (st.loupe && st.loupe.parentNode) st.loupe.parentNode.removeChild(st.loupe);
        if (st._onResize) window.removeEventListener('resize', st._onResize);
        st = null;
    }

    function init(card, options) {
        teardown();
        options = options || {};
        var img = card.querySelector('.cd-img, img.design, img.mlw-img, img');
        var wrap = card.querySelector('.cd-img-wrap, .design.dark.container, .mlw-img-wrap');
        if (!img || !wrap) return null;

        wrap.style.position = 'relative';
        var overlay = document.createElement('canvas');
        overlay.className = 'cd-sampler-canvas';
        wrap.appendChild(overlay);

        var banner = document.createElement('div');
        banner.className = 'cd-sampler-banner';
        banner.textContent = 'Loading pixels…';
        wrap.appendChild(banner);

        var probe = document.createElement('div');
        probe.className = 'cd-cursor-probe';
        probe.style.display = 'none';
        wrap.appendChild(probe);

        var loupe = document.createElement('canvas');
        loupe.className = 'cd-loupe';
        loupe.width = MAG_SIZE;
        loupe.height = MAG_SIZE;
        loupe.style.display = 'none';
        wrap.appendChild(loupe);

        st = {
            card: card,
            img: img,
            wrap: wrap,
            overlay: overlay,
            banner: banner,
            probe: probe,
            loupe: loupe,
            pickMode: 'shade',
            canvasColor: null,
            localPalette: null,
            hover: null,
            hoverMarkerIdx: -1,
            selections: [],
            paths: [],
            openPath: null,
            pathSeq: 0,
            saveQueue: Promise.resolve(),
            ignoredSections: {},
            srcReady: false,
            imgData: null,
            srcCanvas: null,
            gridSections: options.gridSections != null ? options.gridSections : 3,
            samplesPerSection: options.samplesPerSection || 1,
            sectionHost: options.sectionHost || card.querySelector('.cd-section-host'),
            assetId: options.assetId || card.getAttribute('data-asset-id'),
            labelerId: options.labelerId || '',
            saveSample: options.saveSample || null,
            removeSample: options.removeSample || null,
            natW: 0, natH: 0, dispW: 0, dispH: 0, imgOx: 0, imgOy: 0,
        };

        bindUi();
        syncPathChrome();
        sizeOverlay();
        loadPixels();
        renderList();
        renderSectionPanel();
        renderPalettePanel();
        redraw();

        overlay.addEventListener('click', onClick);
        overlay.addEventListener('mousemove', onMove);
        overlay.addEventListener('mouseleave', onLeave);
        overlay.addEventListener('contextmenu', function (e) {
            e.preventDefault();
            undo();
        });
        st._onResize = onResize;
        window.addEventListener('resize', st._onResize);
        return st;
    }

    function hotkey(key) {
        if (!st) return false;
        if (key === 'u' || key === 'U') { undo(); return true; }
        if (key === 's' || key === 'S') { togglePath(); return true; }
        return false;
    }

    function autoSkipIncomplete() {
        if (!st || !st.gridSections) return 0;
        var counts = getSectionCounts();
        var needed = st.samplesPerSection || 1;
        var marked = 0;
        for (var r = 0; r < st.gridSections; r++) {
            for (var c = 0; c < st.gridSections; c++) {
                var key = r + ',' + c;
                if (st.ignoredSections[key]) continue;
                if ((counts[key] || 0) < needed) {
                    st.ignoredSections[key] = true;
                    marked += 1;
                }
            }
        }
        renderSectionPanel();
        redraw();
        return marked;
    }

    // Legacy hook used by the older mturk_redirect depth UI, if still present.
    global.depth_sampler_hotkey = hotkey;

    global.ColorDepthSampler = {
        init: init,
        teardown: teardown,
        hotkey: hotkey,
        getState: function () { return st; },
        flushAll: flushAll,
        getSectionCounts: getSectionCounts,
        autoSkipIncomplete: autoSkipIncomplete,
    };
})(window);
