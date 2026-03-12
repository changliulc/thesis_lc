clc; clearvars; clear functions; close all;

%% -------------------------- 路径与输出目录 ------------------------------
thisFile = mfilename('fullpath');
if isempty(thisFile)
    rootDir = pwd;
else
    rootDir = fileparts(thisFile);
end

rawDataFile   = fullfile(rootDir, 'processedVehicleData_3class_REAL (2).mat');
assetsDir     = fullfile(rootDir, 'ch3_assets_plus_matlab');
matlabDataDir = fullfile(assetsDir, 'matlab_data');
outDir        = fullfile(rootDir, 'figures');
if ~exist(outDir, 'dir'); mkdir(outDir); end

assert(exist(rawDataFile, 'file')==2, '未找到原始数据文件：%s', rawDataFile);

%% -------------------------- 全局绘图风格 --------------------------------
fontCN = pick_chinese_font();
fprintf('选用字体 fontCN = %s\n', fontCN);
set_plot_defaults(fontCN);

%% -------------------------- 关键参数（与论文一致） -----------------------
fs      = 50;     % 采样率 (Hz)
N0      = 10;     % 基线估计窗口长度（采样点数）
wR      = 0.15;   % Sakoe--Chiba 窗口比例
lambda  = 0.05;   % DTW 步进惩罚项
L       = 176;    % 离线统一定长长度

classNames = {'小型车','中型车','大型车'};

fprintf('=== 第三章图片生成开始 ===\n');
fprintf('rootDir = %s\n', rootDir);
fprintf('outDir  = %s\n\n', outDir);

%% -------------------------- 载入原始数据 --------------------------------
S = load(rawDataFile);
ProcessedData = S.ProcessedData;
targetLength  = S.targetLength;

%% ========================================================================
%  1) 三类车辆代表性三轴波形（1行3列）
% ========================================================================
fprintf('[1/6] 生成三类代表性三轴波形图...\n');

[repIdx, repLen, repScore] = select_representative_samples(ProcessedData, targetLength, fs, N0, L);

fprintf('  代表性样本索引（1-based）：小型=%d，中型=%d，大型=%d\n', repIdx(1), repIdx(2), repIdx(3));
fprintf('  对应长度 N：              小型=%d，中型=%d，大型=%d\n', repLen(1), repLen(2), repLen(3));

cropCfg.frac   = 0.10;
cropCfg.margin = 5;

fig = figure('Color','w','Position',[100 100 1100 320]);
tl = tiledlayout(fig, 1, 3, 'TileSpacing','compact', 'Padding','compact');

waveformExamples = struct();
axHandles = gobjects(1,3);
tMaxAll = 0; yMaxAll = 0;

for c = 1:3
    idx = repIdx(c); N = repLen(c);
    [~, dB, b, t] = extract_event(ProcessedData{c}{idx}, N, fs, N0);
    useIdx = crop_by_mag(b, cropCfg.frac, cropCfg.margin);

    t_use  = t(useIdx) - t(useIdx(1));
    dB_use = dB(useIdx, :);
    b_use  = b(useIdx);

    ax = nexttile(tl, c);
    axHandles(c) = ax;

    % plot(ax, t_use, dB_use(:,1)); hold(ax,'on');
    % plot(ax, t_use, dB_use(:,2));
    % plot(ax, t_use, dB_use(:,3));
    % grid(ax,'on'); box(ax,'on');
    % 
    % xlabel(ax, '时间 / s');
    % if c==1
    %     ylabel(ax, '磁场扰动 / nT');
    %     legend(ax, {'X轴','Y轴','Z轴'}, 'Location','best');
    % end
   h1 = plot(ax, t_use, dB_use(:,1)); hold(ax,'on');
h2 = plot(ax, t_use, dB_use(:,2));
h3 = plot(ax, t_use, dB_use(:,3));
grid(ax,'on'); box(ax,'on');

xlabel(ax, '时间 / s');
if c==1
    ylabel(ax, '磁场扰动 / nT');
end

legend(ax, [h1 h2 h3], {'X轴','Y轴','Z轴'}, 'Location','best', 'Box','off');
    title(ax, classNames{c}, 'FontWeight','normal');

    tMaxAll = max(tMaxAll, max(t_use));
    yMaxAll = max(yMaxAll, max(abs(dB_use(:))));

    waveformExamples(c).className = classNames{c};
    waveformExamples(c).index     = idx;
    waveformExamples(c).N         = N;
    waveformExamples(c).score     = repScore(c);
    waveformExamples(c).t         = t_use;
    waveformExamples(c).dB        = dB_use;
    waveformExamples(c).b         = b_use;

    T = table(t_use, dB_use(:,1), dB_use(:,2), dB_use(:,3), b_use, ...
        'VariableNames', {'t_s','dBx_nT','dBy_nT','dBz_nT','b_nT'});
    writetable(T, fullfile(outDir, sprintf('waveform_class%d_idx%d.csv', c, idx)));
end

if yMaxAll > 0
    for c = 1:3
        xlim(axHandles(c), [0, tMaxAll]);
        ylim(axHandles(c), 1.10 * yMaxAll * [-1, 1]);
    end
end

save_png(fig, fullfile(outDir, 'ch3_waveform_by_class.png'), 300);
close(fig);
save(fullfile(outDir, 'ch3_waveform_examples.mat'), 'waveformExamples', 'cropCfg', 'fs', 'N0');

%% ========================================================================
%  2) 车速变化引起的时间伸缩动机图
% ========================================================================
fprintf('[2/6] 生成时间伸缩动机图...\n');

cStretch = 2;
lenVec = double(targetLength{cStretch}(:));

q = 0.15;
idxSort = sortrows([(1:numel(lenVec))', lenVec], 2);
nAll = size(idxSort,1);
shortPool = idxSort(1: max(1, round(q*nAll)), 1);
longPool  = idxSort(max(1, round((1-q)*nAll)) : nAll, 1);

idxShort = pick_max_energy(ProcessedData{cStretch}, lenVec, shortPool, fs, N0);
idxLong  = pick_max_energy(ProcessedData{cStretch}, lenVec, longPool,  fs, N0);

[~, ~, b_s, t_s] = extract_event(ProcessedData{cStretch}{idxShort}, lenVec(idxShort), fs, N0);
[~, ~, b_l, t_l] = extract_event(ProcessedData{cStretch}{idxLong},  lenVec(idxLong),  fs, N0);

fig = figure('Color','w','Position',[100 100 900 420]);
plot(t_s, b_s, 'LineWidth', 1.6); hold on;
plot(t_l, b_l, 'LineWidth', 1.6);
grid on; box on;

xlabel('时间 / s');
ylabel('模值序列 b[n] / nT');
legend({sprintf('短时长样本（N=%d）', lenVec(idxShort)), ...
        sprintf('长时长样本（N=%d）', lenVec(idxLong))}, 'Location','best');
title(sprintf('车速变化引起的时间伸缩示意（%s）', classNames{cStretch}), 'FontWeight','normal');

save_png(fig, fullfile(outDir, 'fig_motivation_speed.png'), 300);
close(fig);

%% ========================================================================
%  3) DTW 对齐示意图（展示 ΔBz）
% ========================================================================
fprintf('[3/6] 生成 DTW 对齐示意图...\n');

[~, dB_s, ~, ~] = extract_event(ProcessedData{cStretch}{idxShort}, lenVec(idxShort), fs, N0);
[~, dB_l, ~, ~] = extract_event(ProcessedData{cStretch}{idxLong},  lenVec(idxLong),  fs, N0);

b_s = sqrt(sum(dB_s.^2, 2));
b_l = sqrt(sum(dB_l.^2, 2));

X4 = [dB_s, b_s];
Y4 = [dB_l, b_l];

zX = dB_s(:,3);
zY = dB_l(:,3);

N = size(X4,1);
M = size(Y4,1);
w = max(floor(wR * max(N,M)), abs(N-M));

[path, ~] = dtw_path_4ch(X4, Y4, w, lambda);
X4_aligned = warp_to_ref_axis(X4, path, M);
zX_aligned = X4_aligned(:,3);

tRef = (0:M-1)'/fs;

fig = figure('Color','w','Position',[100 100 900 600]);
tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

ax1 = nexttile(tl,1);
plot(ax1, (0:N-1)'/fs, zX, 'LineWidth', 1.6); hold(ax1,'on');
plot(ax1, (0:M-1)'/fs, zY, 'LineWidth', 1.6);
grid(ax1,'on'); box(ax1,'on');
xlabel(ax1,'时间 / s');
ylabel(ax1,'\Delta B_z[n] / nT');
legend(ax1, {sprintf('样本A（N=%d）', N), sprintf('样本B（N=%d）', M)}, 'Location','best');
title(ax1, '对齐前（时间伸缩与局部错位）', 'FontWeight','normal');

ax2 = nexttile(tl,2);
plot(ax2, tRef, zY, 'LineWidth', 1.6); hold(ax2,'on');
plot(ax2, tRef, zX_aligned, 'LineWidth', 1.6);
grid(ax2,'on'); box(ax2,'on');
xlabel(ax2,'参考时间轴 / s');
ylabel(ax2,'\Delta B_z[n] / nT');
legend(ax2, {'参考样本B','对齐后的样本A'}, 'Location','best');
title(ax2, 'DTW 对齐后（映射到参考时间轴）', 'FontWeight','normal');

save_png(fig, fullfile(outDir, 'fig_motivation_dtw_align_z.png'), 300);
close(fig);

%% ========================================================================
%  4) 混淆矩阵（改布局：贴近 confusionchart 风格）
% ========================================================================
fprintf('[4/6] 生成混淆矩阵（CNN Baseline）...\n');
make_confusion_chart( ...
    fullfile(matlabDataDir,'cm_cnn_baseline_data.mat'), ...
    fullfile(outDir,'cm_cnn_baseline.png'), ...
    '离线混淆矩阵（CNN Baseline）', fontCN);

fprintf('[5/6] 生成混淆矩阵（DTW-MultiTemplate-CNN）...\n');
make_confusion_chart( ...
    fullfile(matlabDataDir,'cm_dtw_multi_cnn_data.mat'), ...
    fullfile(outDir,'cm_dtw_multi_cnn.png'), ...
    '离线混淆矩阵（DTW-MultiTemplate-CNN，K_{MT}^*=4）', fontCN);

%% ========================================================================
%  5) K_MT 取值消融（按 Python 风格：0-1，虚线网格；保留 K* 虚线）
% ========================================================================
fprintf('[6/6] 生成 K_{MT} 扫描曲线...\n');

D = load(fullfile(matlabDataDir, 'ablation_K_data.mat'));

% --- 兼容字段名：Python=K；你旧版=K_list ---
if isfield(D,'K')
    KMT_list = double(D.K(:));
elseif isfield(D,'K_list')
    KMT_list = double(D.K_list(:));
else
    error('ablation_K_data.mat 缺少 K / K_list 字段');
end

valF1  = double(D.val_f1(:));
testF1 = double(D.test_f1(:));

% --- 统一到 0~1（如果是百分制就除以 100）---
if max(valF1)  > 1.2, valF1  = valF1  / 100; end
if max(testF1) > 1.2, testF1 = testF1 / 100; end

% --- K*：优先读文件，否则按验证集最大值选 ---
if isfield(D,'K_best')
    KMT_best = double(D.K_best(1));
elseif isfield(D,'best_k')
    KMT_best = double(D.best_k(1));
else
    [~, idBest] = max(valF1);
    KMT_best = KMT_list(idBest);
end

fig = figure('Color','w','Position',[100 100 900 520]);

% 为了贴近你“第二个图”：蓝=Test，橙=Val
hTest = plot(KMT_list, testF1, '-o', 'LineWidth', 2.0, 'MarkerSize', 8, ...
    'MarkerFaceColor','auto'); hold on;
hVal  = plot(KMT_list, valF1,  '-s', 'LineWidth', 2.0, 'MarkerSize', 8, ...
    'MarkerFaceColor','auto');

% 保留你想要的 K* 竖直虚线
hBest = xline(KMT_best, '--', 'LineWidth', 1.6);

grid on; box on;
ax = gca;
ax.GridLineStyle = '--';
ax.GridAlpha     = 0.40;
ax.FontName      = fontCN;
ax.FontSize      = 14;

xticks(KMT_list.');
xlim([min(KMT_list)-0.2, max(KMT_list)+0.2]);

ylim([0.0, 1.0]);
yticks(0:0.2:1.0);

xlabel('每类模板数 K_{MT}');
ylabel('Macro-F1');
title('K_{MT} 取值消融', 'FontWeight','normal');

legend([hTest,hVal,hBest], ...
    {'测试集 Macro-F1','验证集 Macro-F1', sprintf('K_{MT}^*=%d', KMT_best)}, ...
    'Location','southwest');

save_png(fig, fullfile(outDir, 'ablation_K.png'), 300);
close(fig);

fprintf('\n=== 全部完成 ===\n');
fprintf('输出目录：%s\n', outDir);

%% =============================== 函数区 ================================

function fontCN = pick_chinese_font()
    cand = { ...
        'Microsoft YaHei','Microsoft YaHei UI','微软雅黑', ...
        'SimHei','黑体', ...
        'SimSun','宋体', ...
        'STSong','华文宋体', ...
        'Arial Unicode MS' ...
    };
    fs = listfonts;
    for i = 1:numel(cand)
        if any(strcmpi(fs, cand{i}))
            fontCN = cand{i};
            return;
        end
    end
    fsLower = lower(string(fs));
    idx = find(contains(fsLower, "yahei") | contains(string(fs), "微软雅黑"), 1);
    if ~isempty(idx), fontCN = fs{idx}; return; end
    idx = find(contains(string(fs), "宋") | contains(fsLower, "simsun"), 1);
    if ~isempty(idx), fontCN = fs{idx}; return; end
    idx = find(contains(string(fs), "黑") | contains(fsLower, "simhei"), 1);
    if ~isempty(idx), fontCN = fs{idx}; return; end
    fontCN = fs{1};
end

function set_plot_defaults(fontCN)
    set(groot, 'defaultFigureColor', 'w');
    set(groot, 'defaultAxesFontName', fontCN);
    set(groot, 'defaultTextFontName', fontCN);
    set(groot, 'defaultAxesFontSize', 12);
    set(groot, 'defaultAxesLineWidth', 1.0);
    set(groot, 'defaultLineLineWidth', 1.5);
    set(groot, 'defaultAxesBox', 'on');
    set(groot, 'defaultTextInterpreter', 'tex');
    set(groot, 'defaultAxesTickLabelInterpreter', 'tex');
    set(groot, 'defaultLegendInterpreter', 'tex');
end

function save_png(figHandle, filePath, dpi)
    if exist('exportgraphics','file') == 2
        exportgraphics(figHandle, filePath, 'Resolution', dpi);
    else
        print(figHandle, filePath, '-dpng', sprintf('-r%d', dpi));
    end
end

function [B, dB, b, t] = extract_event(Bpad, N, fs, N0)
    N = double(N);
    B = double(Bpad(1:N, :));
    n0 = min(N0, N);
    B0 = mean(B(1:n0, :), 1);
    dB = B - B0;
    b  = sqrt(sum(dB.^2, 2));
    t  = (0:N-1)' / fs;
end

function idxUse = crop_by_mag(b, frac, margin)
    if isempty(b), idxUse = []; return; end
    thr = frac * max(b);
    pos = find(b >= thr);
    if isempty(pos)
        idxUse = (1:numel(b)).';
        return;
    end
    s = max(1, pos(1) - margin);
    e = min(numel(b), pos(end) + margin);
    idxUse = (s:e).';
end

function y = resample_linear(x, L)
    x = x(:);
    N = numel(x);
    if N == L
        y = x; return;
    end
    t1 = linspace(0, 1, N);
    t2 = linspace(0, 1, L);
    y  = interp1(t1, x, t2, 'linear');
    y  = y(:);
end

function qv = pct(x, p)
    if exist('prctile','file') == 2
        qv = prctile(x, p);
        return;
    end
    x = sort(double(x(:)));
    if isempty(x), qv = NaN; return; end
    pos = 1 + (numel(x)-1) * (p/100);
    lo = floor(pos); hi = ceil(pos);
    if lo == hi
        qv = x(lo);
    else
        qv = x(lo) + (pos-lo)*(x(hi)-x(lo));
    end
end

function [repIdx, repLen, repScore] = select_representative_samples(ProcessedData, targetLength, fs, N0, L)
    nClass = numel(ProcessedData);
    repIdx   = zeros(1, nClass);
    repLen   = zeros(1, nClass);
    repScore = zeros(1, nClass);

    for c = 1:nClass
        lenVec = double(targetLength{c}(:));
        nSamp  = numel(lenVec);

        feat   = zeros(nSamp, 3*L);
        energy = zeros(nSamp, 1);

        for i = 1:nSamp
            [~, dB, b, ~] = extract_event(ProcessedData{c}{i}, lenVec(i), fs, N0);
            energy(i) = sum(b.^2);

            X = zeros(L, 3);
            for k = 1:3
                xk = resample_linear(dB(:,k), L);
                xk = (xk - mean(xk)) / (std(xk) + eps);
                X(:,k) = xk;
            end
            feat(i,:) = reshape(X, 1, []);
        end

        tmpl = mean(feat, 1);
        tmpl = (tmpl - mean(tmpl)) / (std(tmpl) + eps);

        corrScore = (feat * tmpl.') / (3*L);

        eThr  = pct(energy, 60);
        lenLo = pct(lenVec, 25);
        lenHi = pct(lenVec, 75);

        mask = (energy >= eThr) & (lenVec >= lenLo) & (lenVec <= lenHi);
        if sum(mask) < 5
            mask = (energy >= eThr);
        end

        corrScore(~mask) = -inf;
        [bestScore, bestIdx] = max(corrScore);

        repIdx(c)   = bestIdx;
        repLen(c)   = lenVec(bestIdx);
        repScore(c) = bestScore;
    end
end

function idx = pick_max_energy(classCell, lenVec, idxPool, fs, N0)
    bestE = -inf;
    idx = idxPool(1);
    for ii = idxPool(:)'
        [~, ~, b, ~] = extract_event(classCell{ii}, lenVec(ii), fs, N0);
        E = sum(b.^2);
        if E > bestE
            bestE = E;
            idx = ii;
        end
    end
end

%% ===================== 混淆矩阵：手动布局（贴近原 confusionchart） =====================

function make_confusion_chart(matFile, outPng, titleStr, fontCN)
    assert(exist(matFile,'file')==2, '缺少混淆矩阵数据：%s', matFile);
    D = load(matFile);

    cm = double(D.cm);
    labels = to_cellstr_row(D.labels);

    desired = {'小型车','中型车','大型车'};
    [cm, labels] = reorder_cm_labels(cm, labels, desired);

    n = size(cm,1);
    assert(n==3 && size(cm,2)==3, '当前绘制按三分类实现，但检测到 cm=%dx%d', n, size(cm,2));

    % 行/列汇总（整数百分比，0% 不留空）
    tp = diag(cm);
    rowSum = sum(cm,2);
    colSum = sum(cm,1).';

    rowCorrect = zeros(n,1);
    colCorrect = zeros(n,1);
    for i = 1:n
        if rowSum(i) > 0
            rowCorrect(i) = round(100 * tp(i) / rowSum(i));
        else
            rowCorrect(i) = 0;
        end
        if colSum(i) > 0
            colCorrect(i) = round(100 * tp(i) / colSum(i));
        else
            colCorrect(i) = 0;
        end
    end
    rowWrong = 100 - rowCorrect;
    colWrong = 100 - colCorrect;

    Prow = [rowCorrect, rowWrong];          % 3x2（右侧）
    Pcol = [colCorrect.'; colWrong.'];      % 2x3（底部）

    cmap = confusion_like_cmap(256);

    fig = figure('Color','w','Position',[100 100 950 720]);

    % ---- 手动布局：与 confusionchart 接近（关键）----
    posMain = [0.10 0.34 0.56 0.56];   % [x y w h]
    posRow  = [0.70 0.34 0.22 0.56];
    posCol  = [0.10 0.10 0.56 0.18];

    axMain = axes('Parent', fig, 'Position', posMain);
    axRow  = axes('Parent', fig, 'Position', posRow);
    axCol  = axes('Parent', fig, 'Position', posCol);

    % 主矩阵：保持方格观感
    cm_plot_matrix(axMain, cm, cmap, [0 max(cm(:))], 'count',   fontCN, true);
    axMain.XTick = [];                         % 主矩阵不显示 x 类别
    axMain.YTickLabel = labels;
    ylabel(axMain, '真实类');

    % 行汇总：允许拉伸填满（不强制方格，避免留白）
    cm_plot_matrix(axRow, Prow, cmap, [0 100], 'percent', fontCN, false);
    axRow.XTick = []; axRow.YTick = [];        % 不显示任何刻度

    % 列汇总：允许拉伸填满（不强制方格）
    cm_plot_matrix(axCol, Pcol, cmap, [0 100], 'percent', fontCN, false);
    axCol.YTick = [];
    axCol.XTickLabel = labels;
    xlabel(axCol, '预测类');

    sgtitle(titleStr, 'FontName', fontCN, 'FontWeight','normal', 'Interpreter','tex');

    save_png(fig, outPng, 300);
    close(fig);
end

function labels = to_cellstr_row(x)
    if iscell(x)
        labels = x(:).';
    elseif isstring(x)
        labels = cellstr(x(:)).';
    elseif ischar(x)
        labels = cellstr(x).';
    else
        labels = cellstr(string(x(:))).';
    end
end

function s = normlbl(s)
    s = string(s);
    s = regexprep(s, '\s+', '');
    s = strrep(s, char(160), '');
    s = strrep(s, char(12288), '');
end

function [cm2, labels2] = reorder_cm_labels(cm, labels, desired)
    lbl = normlbl(labels);
    des = normlbl(desired);

    perm = zeros(1, numel(desired));
    for k = 1:numel(desired)
        idx = find(lbl == des(k), 1);
        if isempty(idx)
            idx = find(contains(lbl, des(k)), 1);
        end
        if isempty(idx), perm(k) = 0; else, perm(k) = idx; end
    end

    if any(perm==0) || numel(unique(perm)) < numel(perm)
        warning('labels 无法稳定匹配到 {小型车,中型车,大型车}，将保持原顺序。labels=%s', strjoin(string(labels), ','));
        cm2 = cm;
        labels2 = labels;
        return;
    end

    cm2 = cm(perm, perm);
    labels2 = desired;
end

function cmap = confusion_like_cmap(n)
    cLow  = [0.9569 0.8353 0.8078]; % 浅红
    cHigh = [0.0000 0.4470 0.7410]; % 蓝
    cmap = [linspace(cLow(1), cHigh(1), n).', ...
            linspace(cLow(2), cHigh(2), n).', ...
            linspace(cLow(3), cHigh(3), n).'];
end

function cm_plot_matrix(ax, M, cmap, clim, mode, fontCN, squareCells)
    imagesc(ax, M);
    colormap(ax, cmap);
    caxis(ax, clim);

    [R,C] = size(M);
    set(ax, 'YDir','reverse');
    set(ax, 'XLim', [0.5 C+0.5], 'YLim', [0.5 R+0.5]);
    set(ax, 'FontName', fontCN, 'FontSize', 12);
    set(ax, 'TickLength', [0 0]);
    box(ax,'on');

    if squareCells
        axis(ax, 'image');
    else
        axis(ax, 'normal');
    end

    ax.XTick = 1:C;
    ax.YTick = 1:R;

    hold(ax,'on');
    for x = 0.5:1:(C+0.5)
        plot(ax, [x x], [0.5 R+0.5], 'k-', 'LineWidth', 0.8);
    end
    for y = 0.5:1:(R+0.5)
        plot(ax, [0.5 C+0.5], [y y], 'k-', 'LineWidth', 0.8);
    end

    vmax = clim(2);
    for i = 1:R
        for j = 1:C
            v = M(i,j);
            if strcmp(mode,'percent')
                txt = sprintf('%d%%', round(v));
                useWhite = (v >= 60);
            else
                txt = sprintf('%d', round(v));
                useWhite = (vmax > 0) && (v >= 0.65*vmax);
            end
            if useWhite, tcolor = 'w'; else, tcolor = 'k'; end
            text(ax, j, i, txt, 'HorizontalAlignment','center', ...
                'VerticalAlignment','middle', 'FontName', fontCN, ...
                'FontSize', 12, 'Color', tcolor);
        end
    end
    hold(ax,'off');
end

%% ===================== DTW 相关 =====================

function [path, D] = dtw_path_4ch(X, Y, w, lambda)
    N = size(X,1);
    M = size(Y,1);
    D = inf(N, M);

    D(1,1) = sum((X(1,:) - Y(1,:)).^2);

    for i = 2:N
        if abs(i-1) <= w
            d = sum((X(i,:) - Y(1,:)).^2);
            D(i,1) = d + D(i-1,1) + lambda;
        end
    end

    for j = 2:M
        if abs(1-j) <= w
            d = sum((X(1,:) - Y(j,:)).^2);
            D(1,j) = d + D(1,j-1) + lambda;
        end
    end

    for i = 2:N
        jStart = max(2, i - w);
        jEnd   = min(M, i + w);
        for j = jStart:jEnd
            d = sum((X(i,:) - Y(j,:)).^2);
            D(i,j) = d + min([ ...
                D(i-1,j-1), ...
                D(i-1,j) + lambda, ...
                D(i,  j-1) + lambda]);
        end
    end

    i = N; j = M;
    path = [i, j];
    while ~(i==1 && j==1)
        cand = [inf, inf, inf];
        if i>1 && j>1; cand(1) = D(i-1,j-1); end
        if i>1;        cand(2) = D(i-1,j) + lambda; end
        if j>1;        cand(3) = D(i,j-1) + lambda; end
        [~, k] = min(cand);
        if k==1
            i=i-1; j=j-1;
        elseif k==2
            i=i-1;
        else
            j=j-1;
        end
        path = [[i,j]; path]; %#ok<AGROW>
    end
end

function X_aligned = warp_to_ref_axis(X, path, M)
    C = size(X,2);
    X_aligned = zeros(M, C);
    for j = 1:M
        iList = path(path(:,2) == j, 1);
        if isempty(iList)
            [~, k] = min(abs(path(:,2) - j));
            iList = path(k,1);
        end
        X_aligned(j,:) = mean(X(iList,:), 1);
    end
end