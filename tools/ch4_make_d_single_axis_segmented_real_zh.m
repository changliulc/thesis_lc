function ch4_make_d_single_axis_segmented_real()
% Figure 4.8 single-axis plotting script (point-index unified version)
%
% A/B/C: 横轴统一改为点数
% D    : 基于一个真实停车事件，按“点数分段展示”

%% -------------------- CONFIG --------------------
cfg.repoRoot = fileparts(fileparts(mfilename('fullpath')));

% Sampling rate
cfg.fs = 50;   % Hz

% ===== A/B/C input =====
cfg.waveDataDir = 'D:\xidian_Master\研究生论文\毕业论文\实验数据\第四章\数据';

cfg.aCsv = fullfile(cfg.waveDataDir, 'fig_a_win.csv');
cfg.bCsv = fullfile(cfg.waveDataDir, 'fig_b_win.csv');
cfg.cCsv = fullfile(cfg.waveDataDir, 'fig_c_win.csv');

cfg.outA = fullfile(cfg.repoRoot, 'images', 'ch4_wave_A_single_axis_points_matlab.png');
cfg.outB = fullfile(cfg.repoRoot, 'images', 'ch4_wave_B_single_axis_points_matlab.png');
cfg.outC = fullfile(cfg.repoRoot, 'images', 'ch4_wave_C_single_axis_points_matlab.png');

cfg.outAPreview = fullfile(cfg.repoRoot, 'tmp', 'ch4_wave_refresh', 'ch4_wave_A_single_axis_points_matlab.png');
cfg.outBPreview = fullfile(cfg.repoRoot, 'tmp', 'ch4_wave_refresh', 'ch4_wave_B_single_axis_points_matlab.png');
cfg.outCPreview = fullfile(cfg.repoRoot, 'tmp', 'ch4_wave_refresh', 'ch4_wave_C_single_axis_points_matlab.png');

% ===== D source =====
cfg.srcCsv = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi\20240726_停车检测_sheet1_clean.csv';

% 固定真实事件锚点
cfg.eventStartSec = 100.50;
cfg.eventEndSec   = 106.34;

% 左右真实局部窗口（秒）
cfg.leftPreSec   = 10.0;
cfg.leftPostSec  = 4.0;
cfg.rightPreSec  = 4.0;
cfg.rightPostSec = 10.0;

% D 类总占用时长（映射用）
cfg.actualOccHours = 7.0;

% 中段展示
cfg.midStartOccSec = 1.0 * 3600;
cfg.midHours       = 2.0;
cfg.midNumPts      = 420;

% 漂移量
cfg.targetDriftDelta = 65.0;

% 平台模板
cfg.midTemplateStartOffsetSec   = 2.0;
cfg.midTemplateEndBeforeExitSec = 2.0;

% 中段扰动强度
cfg.midTextureAmp = 2.4;
cfg.midNoiseAmp   = 0.7;
cfg.midNoiseSeed  = 0;

% 平滑
cfg.localSmoothSec = 0.12;

% Style - 统一放大字体
cfg.lineWidth = 1.8;
cfg.refLineWidth = 1.2;
cfg.fontSizeAxis = 16;     % 坐标轴标签字号 (原13)
cfg.fontSizeTick = 13;     % 刻度字号 (原11)
cfg.fontSizeTitle = 18;    % 标题字号 (原16)
cfg.fontSizeSubTitle = 15; % D类子标题字号 (原12)
cfg.fontSizeText = 17;     % 图内文字字号 (原15)

% D图布局比例
cfg.widthRatios = [2.5, 1.0, 2.5]; 
cfg.keepFiguresOpen = true;
cfg.drawABC = true;

cfg.sigColor   = [0.12, 0.47, 0.71];
cfg.baseColor  = [0.85, 0.20, 0.20];
cfg.base1Color = [0.55, 0.55, 0.55];

% D类图片尺寸统一为 700x360，与ABC一致
cfg.figPos = [80, 80, 700, 360]; 

cfg.outPreview = fullfile(cfg.repoRoot, 'tmp', 'ch4_wave_refresh', 'ch4_wave_D_single_axis_segmented_real_points_matlab.png');
cfg.outImage   = fullfile(cfg.repoRoot, 'images', 'ch4_wave_D_single_axis_segmented_real_points_matlab.png');

%% -------------------- DRAW A/B/C FIRST --------------------
if cfg.drawABC
    % ABC图位置保持原设，但函数内部会使用新的字号配置
    draw_single_axis_case_points(cfg.aCsv, '', ...
        cfg.outAPreview, cfg.outA, cfg.keepFiguresOpen, [80, 560, 700, 360], cfg.fs, cfg);
    draw_single_axis_case_points(cfg.bCsv, '', ...
        cfg.outBPreview, cfg.outB, cfg.keepFiguresOpen, [820, 560, 700, 360], cfg.fs, cfg);
    draw_single_axis_case_points(cfg.cCsv, '', ...
        cfg.outCPreview, cfg.outC, cfg.keepFiguresOpen, [80, 120, 700, 360], cfg.fs, cfg);
end

%% -------------------- LOAD D DATA --------------------
srcT = readtable(cfg.srcCsv);
srcT = normalize_table_vars(srcT);

assert(any(strcmp(srcT.Properties.VariableNames, 't')) || any(strcmp(srcT.Properties.VariableNames, 'time')), ...
    'srcCsv 缺少时间列 t 或 time');
assert(any(strcmp(srcT.Properties.VariableNames, 'x')) || any(strcmp(srcT.Properties.VariableNames, 'bx')), ...
    'srcCsv 缺少 X 轴列 x 或 bx');

if any(strcmp(srcT.Properties.VariableNames, 't'))
    t = double(srcT.t(:));
else
    t = double(srcT.time(:));
end

if any(strcmp(srcT.Properties.VariableNames, 'x'))
    x = double(srcT.x(:));
else
    x = double(srcT.bx(:));
end

[t, ord] = sort(t);
x = x(ord);

dt = median(diff(t));
assert(isfinite(dt) && dt > 0, '时间列异常');

xSm = movmean(x, sec2win(cfg.localSmoothSec, dt), 'Endpoints', 'shrink');

entrySec = cfg.eventStartSec;
exitSec  = cfg.eventEndSec;
assert(exitSec > entrySec, 'eventStartSec / eventEndSec 设置有误');

%% -------------------- LEFT SEGMENT --------------------
preMask = (t >= entrySec - 4.0) & (t <= entrySec - 0.25);
if nnz(preMask) < 5
    preMask = t < entrySec;
end
B0 = median(xSm(preMask));

leftRawStart = entrySec - cfg.leftPreSec;
leftRawEnd   = entrySec + cfg.leftPostSec;
leftMask = (t >= leftRawStart) & (t <= leftRawEnd);

tLeftRaw = t(leftMask);
xLeftRaw = xSm(leftMask);
assert(numel(tLeftRaw) > 10, '左段窗口数据不足');

leftPreMask = tLeftRaw <= (entrySec - 0.20);
if nnz(leftPreMask) < 5
    leftPreMask = tLeftRaw < entrySec;
end
rawLeftPre = median(xLeftRaw(leftPreMask));

leftShift = B0 - rawLeftPre;
xLeft = xLeftRaw + leftShift;

p0Mask = (t >= entrySec + 1.8) & (t <= exitSec - 1.8);
if nnz(p0Mask) < 10
    p0Mask = (t >= entrySec + 1.6) & (t <= exitSec - 1.6);
end
assert(nnz(p0Mask) >= 10, 'P0 平台窗口太短');
P0 = median(xSm(p0Mask)) + leftShift;

%% -------------------- RIGHT SEGMENT --------------------
rightRawStart = exitSec - cfg.rightPreSec;
rightRawEnd   = exitSec + cfg.rightPostSec;
rightMask = (t >= rightRawStart) & (t <= rightRawEnd);

tRightRaw = t(rightMask);
xRightRaw = xSm(rightMask);
assert(numel(tRightRaw) > 10, '右段窗口数据不足');

rightOccMask = (tRightRaw >= exitSec - 1.60) & (tRightRaw <= exitSec - 0.25);
if nnz(rightOccMask) < 5
    rightOccMask = tRightRaw < exitSec;
end

rightPostMask = (tRightRaw >= exitSec + 0.60) & ...
                (tRightRaw <= min(exitSec + 6.0, tRightRaw(end)));
if nnz(rightPostMask) < 5
    rightPostMask = tRightRaw >= exitSec;
end

rawRightPost = median(xRightRaw(rightPostMask));

B1 = B0 + cfg.targetDriftDelta;

rightShift = B1 - rawRightPost;
xRight = xRightRaw + rightShift;
P1 = median(xRight(rightOccMask));

%% -------------------- POINT AXIS MAPPING --------------------
entryAbsPt = round(cfg.leftPreSec * cfg.fs);
exitAbsPt  = round((cfg.leftPreSec + cfg.actualOccHours * 3600) * cfg.fs);

midStartAbsPt = round(cfg.midStartOccSec * cfg.fs);
midEndAbsPt   = round((cfg.midStartOccSec + cfg.midHours * 3600) * cfg.fs);

tauLeftPt  = entryAbsPt + round((tLeftRaw  - entrySec) * cfg.fs);
tauRightPt = exitAbsPt  + round((tRightRaw - exitSec)  * cfg.fs);

%% -------------------- MIDDLE SEGMENT --------------------
midFrac0 = cfg.midStartOccSec / (cfg.actualOccHours * 3600);
midFrac1 = (cfg.midStartOccSec + cfg.midHours * 3600) / (cfg.actualOccHours * 3600);

Pmid0 = P0 + (P1 - P0) * midFrac0;
Pmid1 = P0 + (P1 - P0) * midFrac1;

tauMidPt = linspace(midStartAbsPt, midEndAbsPt, cfg.midNumPts).';
baseRamp = linspace(Pmid0, Pmid1, cfg.midNumPts).';

occTexMask = (t >= entrySec + cfg.midTemplateStartOffsetSec) & ...
             (t <= exitSec  - cfg.midTemplateEndBeforeExitSec);
assert(nnz(occTexMask) >= 20, '真实平台模板太短');

xOcc = xSm(occTexMask);
xOcc = movmean(xOcc, 3, 'Endpoints', 'shrink');

nOcc = numel(xOcc);
nEdge = max(3, round(0.18 * nOcc));

occLow = movmean(xOcc, min(31, 2*floor(nOcc/4)+1), 'Endpoints', 'shrink');
lowTrend = linspace(median(occLow(1:nEdge)), median(occLow(end-nEdge+1:end)), nOcc).';
lowShape = occLow(:) - lowTrend;
lowShape = lowShape - linspace(lowShape(1), lowShape(end), nOcc).';
ampLow = prctile(abs(lowShape), 95);
if ampLow < eps, lowShape = zeros(size(lowShape)); else lowShape = lowShape / ampLow; end

occNoise = xOcc(:) - movmean(xOcc(:), min(11, 2*floor(nOcc/6)+1), 'Endpoints', 'shrink');
occNoise = occNoise - mean(occNoise);
ampNoise = prctile(abs(occNoise), 95);
if ampNoise < eps, occNoise = zeros(size(occNoise)); else occNoise = occNoise / ampNoise; end

textureLow = interp1(linspace(0,1,nOcc).', lowShape, linspace(0,1,cfg.midNumPts).', 'pchip');
textureLow = textureLow - linspace(textureLow(1), textureLow(end), numel(textureLow)).';

rng(cfg.midNoiseSeed);
blockLen = min(12, max(6, floor(nOcc/8)));
noiseBlocks = [];
while numel(noiseBlocks) < cfg.midNumPts
    startIdx = randi(max(1, nOcc - blockLen + 1));
    block = occNoise(startIdx:min(startIdx + blockLen - 1, nOcc));
    noiseBlocks = [noiseBlocks; block(:)]; %#ok<AGROW>
end
textureNoise = noiseBlocks(1:cfg.midNumPts);
textureNoise = movmean(textureNoise, 3, 'Endpoints', 'shrink');
textureNoise = textureNoise - mean(textureNoise);
ampNoiseMid = prctile(abs(textureNoise), 95);
if ampNoiseMid < eps, textureNoise = zeros(size(textureNoise)); else textureNoise = textureNoise / ampNoiseMid; end

xMid = baseRamp + cfg.midTextureAmp * textureLow + cfg.midNoiseAmp * textureNoise;

%% -------------------- SHARED Y SCALE --------------------
yAll = [xLeft; xMid; xRight; B0; P0; P1; B1];
ySpan = max(yAll) - min(yAll);
if ySpan < eps, ySpan = 1; end
yPad = 0.08 * ySpan;
yMin = min(yAll) - yPad;
yMax = max(yAll) + yPad;

yTickStart = 50 * floor(yMin / 50);
yTickEnd   = 50 * ceil(yMax / 50);
yTicks = yTickStart : 50 : yTickEnd;

%% -------------------- FIGURE LAYOUT (D 类) --------------------
fig = figure('Color', 'w', 'Position', cfg.figPos);

leftMargin  = 0.11;
rightMargin = 0.06;
bottom      = 0.18;
top         = 0.18;  % 顶部空间留给子标题
gap         = 0.032;

ratios = cfg.widthRatios / sum(cfg.widthRatios);
usableW = 1 - leftMargin - rightMargin - 2 * gap;
w1 = usableW * ratios(1);
w2 = usableW * ratios(2);
w3 = usableW * ratios(3);
h = 1 - bottom - top;

ax1 = axes('Parent', fig, 'Position', [leftMargin, bottom, w1, h]);
ax2 = axes('Parent', fig, 'Position', [leftMargin + w1 + gap, bottom, w2, h]);
ax3 = axes('Parent', fig, 'Position', [leftMargin + w1 + gap + w2 + gap, bottom, w3, h]);

axesAll = [ax1, ax2, ax3];
for k = 1:numel(axesAll)
    ax = axesAll(k);
    hold(ax, 'on');
    grid(ax, 'on');
    box(ax, 'on');
    ax.GridAlpha = 0.18;
    ax.LineWidth = 1.0;
    ax.FontSize = cfg.fontSizeTick;
    ax.YLim = [yTicks(1), yTicks(end)];
    ax.YTick = yTicks;
    ax.Layer = 'top';
    ax.YAxis.Exponent = 0;
    yline(ax, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);
end
linkaxes(axesAll, 'y');

%% -------------------- LEFT PANEL --------------------
plot(ax1, tauLeftPt, xLeft, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
xlim(ax1, [0, round((cfg.leftPreSec + cfg.leftPostSec) * cfg.fs)]);
xticks(ax1, [0, 200, 400, 600]);

ax1.XAxis.Exponent = 0;
xlabel(ax1, '点数', 'FontSize', cfg.fontSizeAxis);
ylabel(ax1, '$B_x$', 'Interpreter', 'latex', 'FontSize', 20);

% 左段子标题
title(ax1, '进入局部', 'FontSize', cfg.fontSizeSubTitle, 'FontWeight', 'normal');

%% -------------------- MIDDLE PANEL --------------------
plot(ax2, tauMidPt, xMid, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
xlim(ax2, [midStartAbsPt, midEndAbsPt]);

xticks(ax2, [200000, 300000, 400000, 500000]);
ax2.XAxis.Exponent = 4;
xlabel(ax2, '点数', 'FontSize', cfg.fontSizeAxis);
ax2.YTickLabel = [];

% 中段子标题
title(ax2, '占用中段漂移', 'FontSize', cfg.fontSizeSubTitle, 'FontWeight', 'normal');

% 图内文字
text(ax2, 0.5 * (midStartAbsPt + midEndAbsPt), ...
    Pmid0 + 0.55 * (Pmid1 - Pmid0), ...
    {'停车占用波形', '缓慢漂移'}, ...
    'HorizontalAlignment', 'center', ...
    'FontSize', cfg.fontSizeText, 'Color', [0.35, 0.35, 0.35]);

%% -------------------- RIGHT PANEL --------------------
plot(ax3, tauRightPt, xRight, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
if true
    yline(ax3, B1, '--', 'Color', cfg.base1Color, 'LineWidth', 1.0);
end

xlim(ax3, [exitAbsPt - round(cfg.rightPreSec * cfg.fs), ...
           exitAbsPt + round(cfg.rightPostSec * cfg.fs)]);

xticks(ax3, [1260400, 1260600, 1260800, 1261000]);
ax3.XAxis.Exponent = 4;
xlabel(ax3, '点数', 'FontSize', cfg.fontSizeAxis);
ax3.YTickLabel = [];

% 右段子标题
title(ax3, '驶离局部', 'FontSize', cfg.fontSizeSubTitle, 'FontWeight', 'normal');

%% -------------------- BREAK MARKS --------------------
add_break_marks(ax1, 'right');
add_break_marks(ax2, 'left');
add_break_marks(ax2, 'right');
add_break_marks(ax3, 'left');

% 省略号
text(ax1, 1.018, 0.50, '...', 'Units', 'normalized', ...
    'FontSize', 18, 'Color', [0.4, 0.4, 0.4], 'VerticalAlignment', 'middle');
text(ax2, 1.018, 0.50, '...', 'Units', 'normalized', ...
    'FontSize', 18, 'Color', [0.4, 0.4, 0.4], 'VerticalAlignment', 'middle');

%% -------------------- SAVE --------------------
save_figure(fig, cfg.outPreview, cfg.outImage, cfg.keepFiguresOpen);

fprintf('D 类源文件                      = %s\n', cfg.srcCsv);
fprintf('D 类图片尺寸已调整为 ABC 一致     = [%d, %d]\n', cfg.figPos(3), cfg.figPos(4));

end

%% -------------------- DRAW A/B/C FUNCTION --------------------
function draw_single_axis_case_points(csvPath, titleText, outPreview, outImage, keepOpen, figPos, fs, cfg)
T = readtable(csvPath);
T = normalize_table_vars(T);

vars = T.Properties.VariableNames;
if all(ismember({'k', 'x'}, vars))
    p = double(T.k(:)); p = p - p(1); x = double(T.x(:));
elseif all(ismember({'k', 'bx'}, vars))
    p = double(T.k(:)); p = p - p(1); x = double(T.bx(:));
elseif all(ismember({'t', 'x'}, vars))
    p = round((double(T.t(:)) - double(T.t(1))) * fs); x = double(T.x(:));
elseif all(ismember({'t', 'bx'}, vars))
    p = round((double(T.t(:)) - double(T.t(1))) * fs); x = double(T.bx(:));
else
    error('文件 %s 缺少可识别的列', csvPath);
end

ref = x(1);
yPad = 0.08 * max(max(x) - min(x), eps);
yMin = min([x; ref]) - yPad;
yMax = max([x; ref]) + yPad;

fig = figure('Color', 'w', 'Position', figPos);
ax = axes('Parent', fig);
hold(ax, 'on');
grid(ax, 'on');
box(ax, 'on');
ax.GridAlpha = 0.18;
ax.LineWidth = 1.0;
ax.FontSize = cfg.fontSizeTick;   % 使用统一配置的字号
ax.XAxis.Exponent = 0;
ax.YAxis.Exponent = 0;

plot(ax, p, x, 'Color', [0.12, 0.47, 0.71], 'LineWidth', 1.8);
yline(ax, ref, '--', 'Color', [0.85, 0.2, 0.2], 'LineWidth', 1.2);

% 使用统一配置的字号
xlabel(ax, '点数', 'FontSize', cfg.fontSizeAxis);
ylabel(ax, '$B_x$', 'Interpreter', 'latex', 'FontSize', 20);
title(ax, titleText, 'FontSize', cfg.fontSizeTitle, 'FontWeight', 'normal');

ax.YLim = [yMin, yMax];

save_figure(fig, outPreview, outImage, keepOpen);
end

function save_figure(fig, outPreview, outImage, keepOpen)
outDir1 = fileparts(outPreview);
outDir2 = fileparts(outImage);
if ~exist(outDir1, 'dir'), mkdir(outDir1); end
if ~exist(outDir2, 'dir'), mkdir(outDir2); end

exportgraphics(fig, outPreview, 'Resolution', 220);
exportgraphics(fig, outImage, 'Resolution', 220);

fprintf('预览图已保存到：%s\n', outPreview);
fprintf('图像已保存到：%s\n', outImage);

if ~keepOpen
    close(fig);
end
end

function T = normalize_table_vars(T)
vars = string(T.Properties.VariableNames);
vars = lower(strtrim(vars));
vars = regexprep(vars, '[^a-z0-9_]', '');
T.Properties.VariableNames = cellstr(vars);
end

function w = sec2win(sec, dt)
w = round(sec / dt);
w = max(w, 3);
if mod(w, 2) == 0, w = w + 1; end
end

function add_break_marks(ax, side)
xL = xlim(ax);
yL = ylim(ax);
dx = 0.012 * (xL(2) - xL(1));
dy = 0.020 * (yL(2) - yL(1));

switch lower(side)
    case 'right'
        x0 = xL(2);
        line(ax, [x0 - dx, x0 + dx], [yL(1) - dy, yL(1) + dy], ...
            'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
        line(ax, [x0 - dx, x0 + dx], [yL(2) - dy, yL(2) + dy], ...
            'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
    case 'left'
        x0 = xL(1);
        line(ax, [x0 - dx, x0 + dx], [yL(1) - dy, yL(1) + dy], ...
            'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
        line(ax, [x0 - dx, x0 + dx], [yL(2) - dy, yL(2) + dy], ...
            'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
end
end