function ch4_make_wave_abcd_unified()
%CH4_MAKE_WAVE_ABCD_UNIFIED
% One-click generator for thesis waveform figures A/B/C/D.
%
% Final intent:
%   A/C: keep waveform shape, shift time to start from 0.
%   B: compress quiet occupied segments, preserve disturbance segments.
%   D: one parking entry, then a long occupied interval with hour-scale drift.

    repoRoot = fileparts(fileparts(mfilename('fullpath')));

    thesisRoot = fullfile('D:\xidian_Master', '研究生论文', '毕业论文');
    dataRoot = fullfile(thesisRoot, '实验数据');
    figCsvDir = fullfile(dataRoot, '第四章', '数据');

    cfg = struct();
    cfg.figA = fullfile(figCsvDir, 'fig_a_win.csv');
    cfg.figB = fullfile(figCsvDir, 'fig_b_win.csv');
    cfg.figC = fullfile(figCsvDir, 'fig_c_win.csv');
    cfg.figDOld = fullfile(figCsvDir, 'fig_d_win.csv');
    cfg.dCandidate = fullfile('D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi', '20240726_停车检测_sheet1_clean.csv');
    cfg.longXDat = fullfile(dataRoot, '2026-03-18 091512.XDat');
    cfg.templateCsv = fullfile(repoRoot, 'tmp', 'ch4_wave_refresh', 'drift_template_norm.csv');
    cfg.templateMetaJson = fullfile(repoRoot, 'tmp', 'ch4_wave_refresh', 'drift_template_meta.json');
    cfg.previewOutDir = fullfile(repoRoot, 'tmp', 'ch4_wave_refresh');
    cfg.outputDir = fullfile(repoRoot, 'images');
    cfg.dOutCsv = fullfile(cfg.previewOutDir, 'fig_d_win_new.csv');
    cfg.ampXYZ = [42, 42, 50];
    cfg.dEventInSec = 102.56;
    cfg.dEventOutSec = 109.94;
    cfg.dPrePadSec = 8.0;
    cfg.dPostPadSec = 8.0;
    cfg.dTargetPreHour = 0.35;
    cfg.dTargetEntryHour = 0.15;
    cfg.dTargetOccHour = 2.98;
    cfg.dTargetExitHour = 0.15;
    cfg.dTargetPostHour = 0.35;

    style = struct();
    style.figPos = [100, 80, 1500, 920];
    style.lineWidth = 1.55;
    style.refWidth = 1.35;
    style.titleSize = 18;
    style.labelSize = 14;
    style.tickSize = 12;
    style.gridAlpha = 0.18;
    style.fontName = 'Microsoft YaHei';

    if ~exist(cfg.outputDir, 'dir'), mkdir(cfg.outputDir); end
    if ~exist(cfg.previewOutDir, 'dir'), mkdir(cfg.previewOutDir); end

    A = shift_time_to_zero(load_mag_csv_auto(cfg.figA));
    [B, bMeta] = compress_b_time(load_mag_csv_auto(cfg.figB));
    C = shift_time_to_zero(load_mag_csv_auto(cfg.figC));
    Dold = load_mag_csv_auto(cfg.figDOld);
    DCand = load_mag_csv_auto(cfg.dCandidate);

    [tmpl, segHoursRel] = load_or_build_template(cfg);
    [occDelta, occInfo] = estimate_parking_signature(Dold);
    D = build_d_from_candidate_event(DCand, tmpl, cfg);

    writetable(struct_to_table(D), cfg.dOutCsv);
    fprintf('[B] duration: %.2f s -> %.2f s\n', bMeta.origDuration, bMeta.newDuration);
    fprintf('[D] rebuilt long-hour window saved: %s\n', cfg.dOutCsv);
    fprintf('[D] relative span: 0.00 -> %.2f h\n', D.t(end));
    fprintf('[D] candidate event: %.2f s -> %.2f s\n', cfg.dEventInSec, cfg.dEventOutSec);
    fprintf('[D] parking signature delta: [%.2f, %.2f, %.2f]\n', occDelta(1), occDelta(2), occDelta(3));
    fprintf('[D] old D main interval: %.2f s -> %.2f s\n', occInfo.mainIntervalT0, occInfo.mainIntervalT1);

    export_wave_figure(A, 'A类正常车流单车停靠场景', fullfile(cfg.outputDir, 'ch4_wave_A'), style, 'Time / s');
    export_wave_figure(B, 'B类占用期过车扰动场景', fullfile(cfg.outputDir, 'ch4_wave_B'), style, 'Time / s');
    export_wave_figure(C, 'C类连续车流稳定窗缺失场景', fullfile(cfg.outputDir, 'ch4_wave_C'), style, 'Time / s');
    export_wave_figure(D, 'D类停车后基线慢漂移场景', fullfile(cfg.outputDir, 'ch4_wave_D'), style, 'Time / h');

    fprintf('\nDone. Exported ch4_wave_A~D into:\n  %s\n', cfg.outputDir);
end

function data = shift_time_to_zero(data)
    data.t = data.t - data.t(1);
end

function [data, meta] = compress_b_time(data)
    data = shift_time_to_zero(data);
    t = data.t(:);
    arr = [data.x(:), data.y(:), data.z(:)];
    ref = arr(1,:);

    dist = sqrt(sum((arr - ref).^2, 2));
    occ = dist > 105;
    occ = dilate_mask(occ, 12);

    smooth = [movmean(data.x, 61), movmean(data.y, 61), movmean(data.z, 61)];
    act = sqrt(sum((arr - smooth).^2, 2));

    if any(occ)
        th = prctile(act(occ), 72);
    else
        th = prctile(act, 90);
    end
    disturb = act >= th;
    disturb = dilate_mask(disturb, 18);

    if any(occ)
        firstOcc = find(occ, 1, 'first');
        lastOcc = find(occ, 1, 'last');
    else
        firstOcc = 1;
        lastOcc = numel(occ);
    end

    protect = disturb;
    protect(max(1, firstOcc-25):min(numel(protect), firstOcc+35)) = true;
    protect(max(1, lastOcc-35):min(numel(protect), lastOcc+25)) = true;

    dt = diff(t);
    midOcc = occ(1:end-1) | occ(2:end);
    midProtect = protect(1:end-1) | protect(2:end);
    w = 0.72 * ones(size(dt));
    w(midOcc) = 0.36;
    w(midProtect) = 1.0;

    tNew = [0; cumsum(dt .* w)];
    data.t = tNew;

    meta = struct();
    meta.origDuration = t(end);
    meta.newDuration = tNew(end);
    meta.activityThreshold = th;
end

function maskOut = dilate_mask(maskIn, radius)
    if radius <= 0
        maskOut = maskIn;
        return;
    end
    ker = ones(2 * radius + 1, 1);
    maskOut = conv(double(maskIn(:)), ker, 'same') > 0;
end

function [tmpl, segHoursRel] = load_or_build_template(cfg)
    if exist(cfg.templateCsv, 'file') == 2 && exist(cfg.templateMetaJson, 'file') == 2
        T = readtable(cfg.templateCsv, 'VariableNamingRule', 'preserve');
        meta = jsondecode(fileread(cfg.templateMetaJson));
        durHour = double(meta.selected_segment_duration_hours);
        tmpl = struct();
        tmpl.u = double(T{:, 1});
        tmpl.x = double(T{:, 2});
        tmpl.y = double(T{:, 3});
        tmpl.z = double(T{:, 4});
        segHoursRel = linspace(0, durHour, height(T))';
        return;
    end

    [x, y, z] = parse_xdat_xyz(cfg.longXDat);
    fs = 50;
    blockSec = 60;
    block = fs * blockSec;
    bx = block_median(x, block);
    by = block_median(y, block);
    bz = block_median(z, block);
    trend = [movmean(bx, 11), movmean(by, 11), movmean(bz, 11)];
    hours = ((0:size(trend,1)-1)' * blockSec) / 3600;
    segLen = min(240, size(trend,1));
    [s0, s1] = choose_segment(trend, segLen);
    seg = trend(s0:s1, :);
    segHoursAbs = hours(s0:s1);
    segHoursRel = segHoursAbs - segHoursAbs(1);

    tmpl = struct();
    tmpl.u = linspace(0, 1, size(seg,1))';
    tmpl.x = normalize_segment(seg(:,1));
    tmpl.y = normalize_segment(seg(:,2));
    tmpl.z = normalize_segment(seg(:,3));
end

function [occDelta, info] = estimate_parking_signature(oldD)
    ref = [oldD.x(1), oldD.y(1), oldD.z(1)];
    arr = [oldD.x(:), oldD.y(:), oldD.z(:)];
    dist = sqrt(sum((arr - ref).^2, 2));
    mask = dist > 120;

    runs = [];
    inRun = false;
    s0 = 1;
    for i = 1:numel(mask)
        if mask(i) && ~inRun
            s0 = i;
            inRun = true;
        elseif ~mask(i) && inRun
            runs(end+1,:) = [s0, i-1]; %#ok<AGROW>
            inRun = false;
        end
    end
    if inRun
        runs(end+1,:) = [s0, numel(mask)]; %#ok<AGROW>
    end
    assert(~isempty(runs), 'No occupied interval detected in old D figure.');

    [~, idx] = max(runs(:,2) - runs(:,1));
    sMain = runs(idx,1);
    eMain = runs(idx,2);
    tail0 = round(sMain + 0.60 * (eMain - sMain));

    occ = median(arr(tail0:eMain, :), 1);
    occDelta = occ - ref;

    info = struct();
    info.mainIntervalT0 = oldD.t(sMain);
    info.mainIntervalT1 = oldD.t(eMain);
    info.tailIntervalT0 = oldD.t(tail0);
    info.tailIntervalT1 = oldD.t(eMain);
end

function data = build_d_from_candidate_event(cand, tmpl, cfg)
    tIn = cfg.dEventInSec;
    tOut = cfg.dEventOutSec;
    prePad = cfg.dPrePadSec;
    postPad = cfg.dPostPadSec;

    idx = cand.t >= (tIn - prePad) & cand.t <= (tOut + postPad);
    win = subset_data(cand, idx);
    win = shift_time_to_zero(win);

    t = win.t(:);
    arr = [win.x(:), win.y(:), win.z(:)];

    eventStart = prePad;
    eventEnd = prePad + (tOut - tIn);
    eventDur = eventEnd - eventStart;
    entryEnd = eventStart + 0.25 * eventDur;
    exitStart = eventStart + 0.75 * eventDur;

    preMask = t < eventStart;
    eventMask = t >= eventStart & t <= eventEnd;
    postMask = t > eventEnd;
    assert(nnz(preMask) >= 5 && nnz(postMask) >= 5 && nnz(eventMask) >= 10, 'Candidate D event window too short.');

    preRef = median(arr(preMask,:), 1);
    postRef = median(arr(postMask,:), 1);
    alpha = max(0, min(1, (t - t(1)) ./ max(t(end) - t(1), 1e-9)));
    srcBg = preRef .* (1 - alpha) + postRef .* alpha;
    residual = arr - srcBg;

    segs.pre = t < eventStart;
    segs.entry = t >= eventStart & t < entryEnd;
    segs.occ = t >= entryEnd & t < exitStart;
    segs.exit = t >= exitStart & t <= eventEnd;
    segs.post = t > eventEnd;

    targetHours.pre = cfg.dTargetPreHour;
    targetHours.entry = cfg.dTargetEntryHour;
    targetHours.occ = cfg.dTargetOccHour;
    targetHours.exit = cfg.dTargetExitHour;
    targetHours.post = cfg.dTargetPostHour;

    targetCounts.pre = 90;
    targetCounts.entry = 70;
    targetCounts.occ = numel(tmpl.u);
    targetCounts.exit = 70;
    targetCounts.post = 90;

    order = {'pre','entry','occ','exit','post'};
    tPieces = cell(1, numel(order));
    rPieces = cell(1, numel(order));
    cursor = 0;

    for ii = 1:numel(order)
        key = order{ii};
        mask = segs.(key);
        tSeg = t(mask);
        rSeg = residual(mask,:);
        assert(numel(tSeg) >= 2, 'Candidate D segment too short: %s', key);

        [~, rx] = resample_segment(tSeg, rSeg(:,1), targetCounts.(key));
        [~, ry] = resample_segment(tSeg, rSeg(:,2), targetCounts.(key));
        [~, rz] = resample_segment(tSeg, rSeg(:,3), targetCounts.(key));

        tPiece = linspace(cursor, cursor + targetHours.(key), targetCounts.(key))';
        tPieces{ii} = tPiece;
        rPieces{ii} = [rx(:), ry(:), rz(:)];
        cursor = tPiece(end);
    end

    tOutAll = tPieces{1};
    rOutAll = rPieces{1};
    for ii = 2:numel(order)
        tOutAll = [tOutAll; tPieces{ii}(2:end)]; %#ok<AGROW>
        rOutAll = [rOutAll; rPieces{ii}(2:end,:)]; %#ok<AGROW>
    end

    uFull = linspace(0, 1, numel(tOutAll))';
    driftX = interp1(tmpl.u, tmpl.x, uFull, 'linear', 'extrap') .* cfg.ampXYZ(1);
    driftY = interp1(tmpl.u, tmpl.y, uFull, 'linear', 'extrap') .* cfg.ampXYZ(2);
    driftZ = interp1(tmpl.u, tmpl.z, uFull, 'linear', 'extrap') .* cfg.ampXYZ(3);
    bg = [preRef(1) + driftX, preRef(2) + driftY, preRef(3) + driftZ];

    rng(7);
    rough = randn(numel(tOutAll), 3);
    rough(:,1) = movmean(rough(:,1), 7);
    rough(:,2) = movmean(rough(:,2), 7);
    rough(:,3) = movmean(rough(:,3), 7);
    rough = rough .* (ones(numel(tOutAll),1) * [0.35, 0.35, 0.45]);

    xyz = bg + rOutAll + rough;
    data = struct();
    data.k = (0:numel(tOutAll)-1)';
    data.t = tOutAll;
    data.x = xyz(:,1);
    data.y = xyz(:,2);
    data.z = xyz(:,3);
end

function export_wave_figure(data, label, outBase, style, xLabelStr)
    fig = figure('Color', 'w', 'Position', style.figPos, 'Visible', 'off');
    set(fig, 'DefaultAxesFontName', style.fontName);
    set(fig, 'DefaultTextFontName', style.fontName);

    tlo = tiledlayout(fig, 3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
    ref = [data.x(1), data.y(1), data.z(1)];
    cols = {'x', 'y', 'z'};
    ylabs = {'B_x', 'B_y', 'B_z'};
    axesH = gobjects(3,1);
    for i = 1:3
        ax = nexttile(tlo, i);
        axesH(i) = ax;
        plot(ax, data.t, data.(cols{i}), 'LineWidth', style.lineWidth, 'Color', [0.12 0.47 0.71]);
        hold(ax, 'on');
        yline(ax, ref(i), '--', 'LineWidth', style.refWidth, 'Color', [0.84 0.15 0.16]);
        hold(ax, 'off');
        ylabel(ax, ylabs{i}, 'FontSize', style.labelSize);
        grid(ax, 'on');
        ax.GridAlpha = style.gridAlpha;
        ax.FontSize = style.tickSize;
        if i < 3
            ax.XTickLabel = [];
        else
            xlabel(ax, xLabelStr, 'FontSize', style.labelSize);
        end
    end
    linkaxes(axesH, 'x');
    xlim(axesH(1), [data.t(1), data.t(end)]);
    title(tlo, label, 'FontSize', style.titleSize, 'FontWeight', 'bold');

    export_both(fig, [outBase '.pdf'], [outBase '.png']);
    close(fig);
end

function export_both(fig, pdfPath, pngPath)
    try
        exportgraphics(fig, pdfPath, 'ContentType', 'vector', 'BackgroundColor', 'white');
    catch
        print(fig, pdfPath, '-dpdf', '-painters');
    end
    try
        exportgraphics(fig, pngPath, 'Resolution', 300, 'BackgroundColor', 'white');
    catch
        print(fig, pngPath, '-dpng', '-r300');
    end
end

function data = load_mag_csv_auto(path)
    T = readtable(path, 'VariableNamingRule', 'preserve');
    vars = string(T.Properties.VariableNames);
    low = lower(vars);

    data = struct();
    if any(low == "k")
        data.k = double(T{:, find(low=="k", 1)});
    else
        data.k = (0:height(T)-1)';
    end
    data.t = double(T{:, find(low=="t", 1)});

    if all(ismember(["x","y","z"], low))
        data.x = double(T{:, find(low=="x",1)});
        data.y = double(T{:, find(low=="y",1)});
        data.z = double(T{:, find(low=="z",1)});
    elseif all(ismember(["bx","by","bz"], low))
        data.x = double(T{:, find(low=="bx",1)});
        data.y = double(T{:, find(low=="by",1)});
        data.z = double(T{:, find(low=="bz",1)});
    else
        error('Unsupported CSV columns in %s', path);
    end
end

function T = struct_to_table(data)
    T = table(data.k(:), data.t(:), data.x(:), data.y(:), data.z(:), ...
        'VariableNames', {'k', 't', 'x', 'y', 'z'});
end

function [x, y, z] = parse_xdat_xyz(xdatPath)
    fid = fopen(xdatPath, 'r');
    assert(fid > 0, 'Cannot open XDat: %s', xdatPath);
    c = onCleanup(@() fclose(fid));

    pat = '(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+\d+:\d+:\d+\.\d+';
    x = [];
    y = [];
    z = [];
    while true
        line = fgetl(fid);
        if ~ischar(line), break; end
        tok = regexp(line, pat, 'tokens', 'once');
        if ~isempty(tok)
            x(end+1,1) = str2double(tok{1}); %#ok<AGROW>
            y(end+1,1) = str2double(tok{2}); %#ok<AGROW>
            z(end+1,1) = str2double(tok{3}); %#ok<AGROW>
        end
    end
end

function meds = block_median(x, block)
    n = numel(x);
    fullN = floor(n / block);
    if fullN < 1
        meds = median(x);
        return;
    end
    x0 = x(1:fullN*block);
    x0 = reshape(x0, block, fullN);
    meds = median(x0, 1)';
    if fullN * block < n
        meds(end+1,1) = median(x(fullN*block+1:end)); %#ok<AGROW>
    end
end

function [s0, s1] = choose_segment(trend, segLen)
    n = size(trend,1);
    if n <= segLen
        s0 = 1;
        s1 = n;
        return;
    end
    bestScore = -inf;
    s0 = 1;
    s1 = segLen;
    for s = 1:(n-segLen+1)
        seg = trend(s:s+segLen-1,:);
        delta = seg(end,:) - seg(1,:);
        span = max(seg,[],1) - min(seg,[],1) + 1e-6;
        mono = sum(abs(delta) ./ span);
        rough = 0;
        for i = 1:3
            d2 = diff(seg(:,i), 2);
            rough = rough + mean(abs(d2)) / span(i);
        end
        strength = sum(abs(delta));
        score = strength * mono / (rough + 0.02);
        if score > bestScore
            bestScore = score;
            s0 = s;
            s1 = s + segLen - 1;
        end
    end
end

function y = normalize_segment(x)
    x = x(:) - x(1);
    e = x(end);
    if abs(e) < 1e-9
        e = max(abs(x));
        if e < 1e-9
            e = 1;
        end
    end
    y = x / abs(e);
    if x(end) < 0
        y = -y;
    end
end

function out = subset_data(data, idx)
    out = struct();
    out.k = data.k(idx);
    out.t = data.t(idx);
    out.x = data.x(idx);
    out.y = data.y(idx);
    out.z = data.z(idx);
end

function [tOut, yOut] = resample_segment(tIn, yIn, nOut)
    uIn = linspace(0, 1, numel(tIn))';
    uOut = linspace(0, 1, nOut)';
    tOut = interp1(uIn, tIn(:), uOut, 'linear');
    yOut = interp1(uIn, yIn(:), uOut, 'linear');
end
