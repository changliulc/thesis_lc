% function ch4_make_d_single_axis_segmented_absolute_selected_event()
% % D类慢漂移背景场景（X轴，分段展示）
% %
% % 说明：
% % 1) 只用 20240726 数据中的一个真实停车事件作为原型；
% % 2) 事件固定为 [102.56 s, 109.94 s]；
% % 3) 左/右两段使用该真实事件的进入/驶离局部形状；
% % 4) 中间只展示代表性 2 h 占用漂移片段；
% % 5) 整体时间采用统一“绝对经过时间轴”，原点从 0 开始；
% % 6) 停车占用总时长按约 7 h 映射，驶离时刻约为 07:00:10。
% %
% % 目标层级关系：
% %   B0：原始背景基线
% %   P0：刚停车后的初始平台
% %   P1：7 h 后漂移后的平台
% %   B1：7 h 后漂移后的新背景基线
% 
% %% ==================== CONFIG ====================
% cfg.repoRoot = fileparts(mfilename('fullpath'));
% 
% cfg.srcCsv = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi\20240726_停车检测_sheet1_clean.csv';
% 
% % 固定真实事件，不再自动检测
% cfg.forceEntrySec = 102.56;
% cfg.forceExitSec  = 109.94;
% 
% % 全局绝对经过时间轴设置
% cfg.leftPreSec  = 10.0;    % 左段：停车前保留 10 s 环境基线
% cfg.leftPostSec = 4.0;     % 左段：停车后再保留 4 s
% cfg.actualOccHours = 7.0;  % 停车占用总时长映射为 7 h
% cfg.rightPreSec  = 4.0;    % 右段：驶离前保留 4 s
% cfg.rightPostSec = 10.0;   % 右段：驶离后保留 10 s 环境基线
% 
% % 中间只展示代表性 2 h
% cfg.midStartAbsSec = 10 * 60;  % 中段从 00:10:00 开始
% cfg.midShowHours   = 2.0;      % 展示 2 h，即到 02:10:00
% cfg.midNumPts      = 420;
% 
% % 总漂移量（背景基线）
% cfg.driftDelta = 65.0;         % 60~70 nT，这里取 65 nT
% 
% % 中段平台纹理只从真实平台段截取
% cfg.midTemplateStartOffsetSec   = 1.20;   % 进入后 1.2 s 开始
% cfg.midTemplateEndBeforeExitSec = 2.20;   % 离开前 2.2 s 截断
% cfg.midTextureAmp = 0.8;                  % 中段平台纹理幅值（nT）
% 
% % 平滑（尽量轻）
% cfg.localSmoothSec = 0.12;
% 
% % 作图样式（保持你之前那种 MATLAB 风格）
% cfg.figPos = [120, 80, 1380, 610];
% cfg.widthRatios = [2.15, 1.05, 2.15];
% cfg.lineWidth = 2.0;
% cfg.refLineWidth = 1.25;
% cfg.fontSizeAxis = 13;
% cfg.fontSizeTick = 11;
% cfg.fontSizeTitle = 16;
% 
% cfg.sigColor   = [0.00, 0.447, 0.741];   % MATLAB 默认蓝
% cfg.baseColor  = [0.90, 0.25, 0.25];     % 红虚线：B0
% cfg.base1Color = [0.55, 0.55, 0.55];     % 灰虚线：B1
% cfg.showB1 = true;
% 
% cfg.outImage = fullfile(cfg.repoRoot, 'ch4_wave_D_selected_event_absolute_time_20240726.png');
% cfg.keepFigureOpen = true;
% 
% %% ==================== READ DATA ====================
% T = readtable(cfg.srcCsv);
% T = normalize_table_vars(T);
% 
% assert(any(strcmp(T.Properties.VariableNames, 't')) || any(strcmp(T.Properties.VariableNames, 'time')), ...
%     'CSV 中缺少时间列 t 或 time。');
% assert(any(strcmp(T.Properties.VariableNames, 'x')) || any(strcmp(T.Properties.VariableNames, 'bx')), ...
%     'CSV 中缺少 X 轴列 x 或 bx。');
% 
% if any(strcmp(T.Properties.VariableNames, 't'))
%     t = double(T.t(:));
% else
%     t = double(T.time(:));
% end
% 
% if any(strcmp(T.Properties.VariableNames, 'x'))
%     x = double(T.x(:));
% else
%     x = double(T.bx(:));
% end
% 
% [t, ord] = sort(t);
% x = x(ord);
% 
% dt = median(diff(t));
% assert(isfinite(dt) && dt > 0, '时间列异常。');
% 
% xSm = movmean(x, sec2win(cfg.localSmoothSec, dt), 'Endpoints', 'shrink');
% 
% %% ==================== FIXED EVENT ====================
% entrySec = cfg.forceEntrySec;
% exitSec  = cfg.forceExitSec;
% assert(exitSec > entrySec, '进入/驶离时刻设置有误。');
% 
% %% ==================== ESTIMATE B0 / P0 ====================
% % B0：进入前背景基线
% preMask = (t >= entrySec - 4.0) & (t <= entrySec - 0.25);
% if nnz(preMask) < 5
%     preMask = t < entrySec;
% end
% B0 = median(xSm(preMask));
% 
% % 左段真实窗口
% leftRawStart = entrySec - cfg.leftPreSec;
% leftRawEnd   = entrySec + cfg.leftPostSec;
% 
% leftMask = (t >= leftRawStart) & (t <= leftRawEnd);
% tLeftRaw = t(leftMask);
% xLeftRaw = xSm(leftMask);
% assert(numel(tLeftRaw) > 10, '左段窗口数据不足。');
% 
% % 左段内真实进入前 / 进入后平台
% leftPreMask = tLeftRaw <= (entrySec - 0.20);
% if nnz(leftPreMask) < 5
%     leftPreMask = tLeftRaw < entrySec;
% end
% 
% leftOccMask = (tLeftRaw >= (entrySec + 0.80)) & ...
%               (tLeftRaw <= min(entrySec + 2.20, tLeftRaw(end)));
% if nnz(leftOccMask) < 5
%     leftOccMask = tLeftRaw > (entrySec + 0.40);
% end
% 
% rawLeftPre = median(xLeftRaw(leftPreMask));
% rawLeftOcc = median(xLeftRaw(leftOccMask));
% 
% % 左段只做平移，保持真实进入形状
% leftShift = B0 - rawLeftPre;
% xLeft = xLeftRaw + leftShift;
% P0 = rawLeftOcc + leftShift;
% 
% %% ==================== ESTIMATE B1 / P1 FROM REAL EXIT WAVEFORM ====================
% % 右段真实窗口
% rightRawStart = exitSec - cfg.rightPreSec;
% rightRawEnd   = exitSec + cfg.rightPostSec;
% 
% rightMask = (t >= rightRawStart) & (t <= rightRawEnd);
% tRightRaw = t(rightMask);
% xRightRaw = xSm(rightMask);
% assert(numel(tRightRaw) > 10, '右段窗口数据不足。');
% 
% rightOccMask = (tRightRaw >= max(rightRawStart, exitSec - 1.60)) & ...
%                (tRightRaw <= (exitSec - 0.25));
% if nnz(rightOccMask) < 5
%     rightOccMask = tRightRaw < exitSec;
% end
% 
% rightPostMask = (tRightRaw >= (exitSec + 0.60)) & ...
%                 (tRightRaw <= min(exitSec + 6.0, tRightRaw(end)));
% if nnz(rightPostMask) < 5
%     rightPostMask = tRightRaw >= exitSec;
% end
% 
% rawRightOcc  = median(xRightRaw(rightOccMask));
% rawRightPost = median(xRightRaw(rightPostMask));
% 
% % 背景漂移后新基线固定上移 65 nT
% B1 = B0 + cfg.driftDelta;
% 
% % 右段只做平移，保持真实离开形状
% rightShift = B1 - rawRightPost;
% xRight = xRightRaw + rightShift;
% P1 = rawRightOcc + rightShift;
% 
% %% ==================== GLOBAL ABSOLUTE ELAPSED TIME MAPPING ====================
% % 左段最左端 = 00:00:00
% % 进入时刻   = 00:00:10
% % 驶离时刻   = 07:00:10
% 
% entryAbs = cfg.leftPreSec;
% exitAbs  = cfg.leftPreSec + cfg.actualOccHours * 3600;
% 
% % 中段绝对时间窗：00:10:00 ~ 02:10:00
% midStartAbs = cfg.midStartAbsSec;
% midEndAbs   = cfg.midStartAbsSec + cfg.midShowHours * 3600;
% 
% assert(midStartAbs > entryAbs, 'midStartAbsSec 必须晚于进入时刻。');
% assert(midEndAbs < exitAbs, '中段展示结束时间必须早于驶离时刻。');
% 
% % 左右段映射到绝对经过时间轴
% tauLeft  = entryAbs + (tLeftRaw  - entrySec);
% tauRight = exitAbs  + (tRightRaw - exitSec);
% 
% %% ==================== MIDDLE SEGMENT: REAL PLATFORM TEXTURE ONLY ====================
% % 中段高度：按 7 h 总过程，从 P0 漂到 P1 的对应 2 h 片段
% midFrac0 = (midStartAbs - entryAbs) / (cfg.actualOccHours * 3600);
% midFrac1 = (midEndAbs   - entryAbs) / (cfg.actualOccHours * 3600);
% 
% Pmid0 = P0 + (P1 - P0) * midFrac0;
% Pmid1 = P0 + (P1 - P0) * midFrac1;
% 
% tauMid = linspace(midStartAbs, midEndAbs, cfg.midNumPts).';
% baseRamp = linspace(Pmid0, Pmid1, cfg.midNumPts).';
% 
% % 只从“真实平台段”提取模板，不允许混入进入/离开边缘
% occTexMask = (t >= entrySec + cfg.midTemplateStartOffsetSec) & ...
%              (t <= exitSec  - cfg.midTemplateEndBeforeExitSec);
% 
% if nnz(occTexMask) < 10
%     occTexMask = (t >= entrySec + 1.0) & (t <= exitSec - 2.0);
% end
% if nnz(occTexMask) < 10
%     error('中段真实平台模板太短，请调整模板截取窗口。');
% end
% 
% xOcc = xSm(occTexMask);
% xOcc = movmean(xOcc, 3, 'Endpoints', 'shrink');
% 
% nOcc = numel(xOcc);
% nEdge = max(3, round(0.18 * nOcc));
% 
% occStartBase = median(xOcc(1:nEdge));
% occEndBase   = median(xOcc(end-nEdge+1:end));
% 
% % 去掉整体趋势，只保留真实平台纹理
% trendTex = linspace(occStartBase, occEndBase, nOcc).';
% texture = xOcc(:) - trendTex;
% 
% % 再把首尾压回 0，避免拉伸后鼓包
% texture = texture - linspace(texture(1), texture(end), nOcc).';
% 
% amp95 = prctile(abs(texture), 95);
% if amp95 < eps
%     texture = zeros(size(texture));
% else
%     texture = texture / amp95;
% end
% 
% texture = texture * cfg.midTextureAmp;
% 
% textureMid = interp1( ...
%     linspace(0,1,nOcc).', ...
%     texture, ...
%     linspace(0,1,cfg.midNumPts).', ...
%     'pchip');
% 
% % 再次校正两端为 0
% textureMid = textureMid - linspace(textureMid(1), textureMid(end), numel(textureMid)).';
% 
% xMid = baseRamp + textureMid;
% 
% %% ==================== Y LIMITS ====================
% yAll = [xLeft; xMid; xRight; B0; P0; P1; B1];
% ySpan = max(yAll) - min(yAll);
% if ySpan < eps
%     ySpan = 1;
% end
% yPad = 0.08 * ySpan;
% yMin = min(yAll) - yPad;
% yMax = max(yAll) + yPad;
% 
% %% ==================== FIGURE LAYOUT ====================
% fig = figure('Color', 'w', 'Position', cfg.figPos);
% 
% leftMargin  = 0.07;
% rightMargin = 0.03;
% bottom      = 0.14;
% top         = 0.12;
% gap         = 0.055;
% 
% ratios = cfg.widthRatios / sum(cfg.widthRatios);
% usableW = 1 - leftMargin - rightMargin - 2*gap;
% w1 = usableW * ratios(1);
% w2 = usableW * ratios(2);
% w3 = usableW * ratios(3);
% h  = 1 - bottom - top;
% 
% ax1 = axes('Parent', fig, 'Position', [leftMargin, bottom, w1, h]);
% ax2 = axes('Parent', fig, 'Position', [leftMargin + w1 + gap, bottom, w2, h]);
% ax3 = axes('Parent', fig, 'Position', [leftMargin + w1 + gap + w2 + gap, bottom, w3, h]);
% 
% axesAll = [ax1, ax2, ax3];
% for k = 1:numel(axesAll)
%     ax = axesAll(k);
%     hold(ax, 'on');
%     grid(ax, 'on');
%     box(ax, 'on');
%     ax.GridAlpha = 0.18;
%     ax.LineWidth = 1.0;
%     ax.FontSize = cfg.fontSizeTick;
%     ax.YLim = [yMin, yMax];
%     ax.Layer = 'top';
%     ax.XAxis.Exponent = 0;
%     ax.YAxis.Exponent = 0;
% end
% 
% %% -------------------- LEFT PANEL --------------------
% plot(ax1, tauLeft, xLeft, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
% yline(ax1, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);
% 
% xlim(ax1, [0, entryAbs + cfg.leftPostSec]);
% xlabel(ax1, 'Elapsed time', 'FontSize', cfg.fontSizeAxis);
% ylabel(ax1, '$B_x$ (nT)', 'Interpreter', 'latex', 'FontSize', 20);
% title(ax1, 'D类慢漂移背景场景（X轴，分段展示）', ...
%     'FontSize', cfg.fontSizeTitle, 'FontWeight', 'normal');
% 
% leftTicks = [0, 5, entryAbs, entryAbs + cfg.leftPostSec];
% leftTicks = unique(leftTicks(leftTicks >= 0 & leftTicks <= (entryAbs + cfg.leftPostSec)));
% xticks(ax1, leftTicks);
% xticklabels(ax1, sec_to_hms_labels(leftTicks));
% 
% %% -------------------- MIDDLE PANEL --------------------
% plot(ax2, tauMid, xMid, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
% yline(ax2, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);
% 
% xlim(ax2, [midStartAbs, midEndAbs]);
% xlabel(ax2, 'Elapsed time', 'FontSize', cfg.fontSizeAxis);
% ax2.YTickLabel = [];
% 
% midTicks = [midStartAbs, midStartAbs + 3600, midEndAbs];
% xticks(ax2, midTicks);
% xticklabels(ax2, sec_to_hms_labels(midTicks));
% 
% text(ax2, midStartAbs + 0.58*(midEndAbs - midStartAbs), ...
%     Pmid0 + 0.65*(Pmid1 - Pmid0), ...
%     {'停车占用平台', '缓慢漂移'}, ...
%     'HorizontalAlignment', 'center', ...
%     'FontSize', 12, 'Color', [0.35, 0.35, 0.35]);
% 
% %% -------------------- RIGHT PANEL --------------------
% plot(ax3, tauRight, xRight, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
% yline(ax3, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);
% 
% if cfg.showB1
%     yline(ax3, B1, '--', 'Color', cfg.base1Color, 'LineWidth', 1.0);
% end
% 
% xlim(ax3, [exitAbs - cfg.rightPreSec, exitAbs + cfg.rightPostSec]);
% xlabel(ax3, 'Elapsed time', 'FontSize', cfg.fontSizeAxis);
% ax3.YTickLabel = [];
% 
% rightTicks = [exitAbs - cfg.rightPreSec, exitAbs, exitAbs + 5, exitAbs + cfg.rightPostSec];
% rightTicks = unique(rightTicks(rightTicks >= (exitAbs - cfg.rightPreSec) & ...
%                                rightTicks <= (exitAbs + cfg.rightPostSec)));
% xticks(ax3, rightTicks);
% xticklabels(ax3, sec_to_hms_labels(rightTicks));
% 
% %% -------------------- BREAK MARKS --------------------
% add_break_marks(ax1, 'right');
% add_break_marks(ax2, 'left');
% add_break_marks(ax2, 'right');
% add_break_marks(ax3, 'left');
% 
% text(ax1, 1.03, 0.48, '...', 'Units', 'normalized', ...
%     'FontSize', 20, 'Color', [0.40, 0.40, 0.40], ...
%     'VerticalAlignment', 'middle');
% 
% text(ax2, 1.03, 0.48, '...', 'Units', 'normalized', ...
%     'FontSize', 20, 'Color', [0.40, 0.40, 0.40], ...
%     'VerticalAlignment', 'middle');
% 
% %% ==================== SAVE ====================
% outDir = fileparts(cfg.outImage);
% if ~isempty(outDir) && ~exist(outDir, 'dir')
%     mkdir(outDir);
% end
% 
% exportgraphics(fig, cfg.outImage, 'Resolution', 220);
% fprintf('Saved image to: %s\n', cfg.outImage);
% 
% fprintf('\n========= D FIGURE LEVELS =========\n');
% fprintf('Fixed entry time           : %.3f s\n', entrySec);
% fprintf('Fixed leaving time         : %.3f s\n', exitSec);
% fprintf('Global displayed entry     : %s\n', sec_to_hms_labels_scalar(entryAbs));
% fprintf('Global displayed leaving   : %s\n', sec_to_hms_labels_scalar(exitAbs));
% fprintf('B0 (old baseline)          : %.3f nT\n', B0);
% fprintf('P0 (initial platform)      : %.3f nT\n', P0);
% fprintf('P1 (drifted platform)      : %.3f nT\n', P1);
% fprintf('B1 (new baseline)          : %.3f nT\n', B1);
% fprintf('Applied baseline drift     : %.3f nT\n', cfg.driftDelta);
% 
% if ~cfg.keepFigureOpen
%     close(fig);
% end
% 
% end
% 
% %% ========================================================================
% function T = normalize_table_vars(T)
% vars = string(T.Properties.VariableNames);
% vars = lower(strtrim(vars));
% vars = regexprep(vars, '[^a-z0-9_]', '');
% T.Properties.VariableNames = cellstr(vars);
% end
% 
% function w = sec2win(sec, dt)
% w = round(sec / dt);
% w = max(w, 3);
% if mod(w, 2) == 0
%     w = w + 1;
% end
% end
% 
% function add_break_marks(ax, side)
% xL = xlim(ax);
% yL = ylim(ax);
% 
% dx = 0.018 * (xL(2) - xL(1));
% dy = 0.025 * (yL(2) - yL(1));
% 
% switch lower(side)
%     case 'right'
%         x0 = xL(2);
%         line(ax, [x0 - dx, x0 + dx], [yL(1) - dy, yL(1) + dy], ...
%             'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
%         line(ax, [x0 - dx, x0 + dx], [yL(2) - dy, yL(2) + dy], ...
%             'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
% 
%     case 'left'
%         x0 = xL(1);
%         line(ax, [x0 - dx, x0 + dx], [yL(1) - dy, yL(1) + dy], ...
%             'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
%         line(ax, [x0 - dx, x0 + dx], [yL(2) - dy, yL(2) + dy], ...
%             'Color', [0.35, 0.35, 0.35], 'Clipping', 'off', 'LineWidth', 1.0);
% end
% end
% 
% function labs = sec_to_hms_labels(v)
% v = round(v(:));
% h = floor(v / 3600);
% m = floor(mod(v, 3600) / 60);
% s = mod(v, 60);
% labs = arrayfun(@(hh,mm,ss) sprintf('%02d:%02d:%02d', hh, mm, ss), ...
%     h, m, s, 'UniformOutput', false);
% end
% 
% function lab = sec_to_hms_labels_scalar(v)
% c = sec_to_hms_labels(v);
% lab = c{1};
% end
function ch4_make_d_single_axis_segmented_absolute_selected_event()
% D类慢漂移背景场景（X轴，分段展示）
%
% v4 修订说明：
%   横轴统一改为 0-base 点数索引（Sample index），去掉 HH:MM:SS 时间标签。
%   左段第 500 点 = 入停时刻（@50Hz, leftPreSec=10s → 10/0.02=500点）
%   右段第 200 点 = 驶离时刻（@50Hz, rightPreSec=4s  →  4/0.02=200点）
%   漂移量计算逻辑不变，仅影响显示轴。

%% ==================== CONFIG ====================
cfg.repoRoot = fileparts(mfilename('fullpath'));

cfg.srcCsv = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi\20240726_停车检测_sheet1_clean.csv';

cfg.eventDetectWinSec = [100.00, 112.00];

cfg.forceEntrySec = [];   % 留空则自动识别
cfg.forceExitSec  = [];

% 原始数据截取窗口（秒），仍用于从 CSV 中截取左/右段波形
cfg.leftPreSec   = 10.0;
cfg.leftPostSec  = 4.0;
cfg.rightPreSec  = 4.0;
cfg.rightPostSec = 10.0;

% 停车总时长映射（用于漂移量内部计算，不出现在轴标签上）
cfg.actualOccHours = 7.0;

% 中段仅用于漂移量计算（确定 Pmid0/Pmid1 高度）
cfg.midStartAbsSec = 10 * 60;   % 漂移起始参考：距入停 10 min
cfg.midShowHours   = 2.0;       % 漂移显示跨度：2 h
cfg.midNumPts      = 420;       % 中段绘制点数（合成）

% 总漂移量
cfg.driftDelta   = 65.0;        % nT
cfg.midTextureNT = 1.2;         % 中段纹理目标峰值幅值（nT）

% 检测参数
cfg.localSmoothSec = 0.12;
cfg.detectThrRatio = 0.35;
cfg.edgeRefineSec  = 0.70;

% 作图样式
cfg.figPos       = [120, 80, 1380, 610];
cfg.widthRatios  = [2.15, 1.05, 2.15];
cfg.lineWidth    = 2.0;
cfg.refLineWidth = 1.25;
cfg.fontSizeAxis  = 13;
cfg.fontSizeTick  = 11;
cfg.fontSizeTitle = 16;

cfg.sigColor   = [0.00, 0.447, 0.741];
cfg.baseColor  = [0.90, 0.25, 0.25];
cfg.base1Color = [0.55, 0.55, 0.55];
cfg.showB1     = true;

cfg.outImage = fullfile(cfg.repoRoot, 'ch4_wave_D_selected_event_sampleidx_20240726.png');
cfg.keepFigureOpen = true;

%% ==================== READ DATA ====================
T = readtable(cfg.srcCsv);
T = normalize_table_vars(T);

if any(strcmp(T.Properties.VariableNames, 't'))
    t = double(T.t(:));
else
    t = double(T.time(:));
end
if any(strcmp(T.Properties.VariableNames, 'x'))
    x = double(T.x(:));
else
    x = double(T.bx(:));
end

[t, ord] = sort(t);
x = x(ord);

dt = median(diff(t));
assert(isfinite(dt) && dt > 0, '时间列异常。');

xSm = movmean(x, sec2win(cfg.localSmoothSec, dt), 'Endpoints', 'shrink');

%% ==================== EVENT DETECTION ====================
evtMask = (t >= cfg.eventDetectWinSec(1)) & (t <= cfg.eventDetectWinSec(2));
tEvt = t(evtMask);
xEvt = xSm(evtMask);
assert(numel(tEvt) > 20, '识别窗口内点数过少。');

B0guess  = median(xEvt(1:max(5, round(0.15*numel(xEvt)))));
peakHigh = prctile(xEvt, 92);
thr      = B0guess + cfg.detectThrRatio * (peakHigh - B0guess);

idx1 = find(xEvt >= thr, 1, 'first');
idx2 = find(xEvt >= thr, 1, 'last');
assert(~isempty(idx1) && ~isempty(idx2) && idx2 > idx1, '未识别到有效事件。');

gEvt    = gradient(xEvt) ./ max(gradient(tEvt), eps);
halfWin = max(3, round(cfg.edgeRefineSec / dt));

i1a = max(1, idx1-halfWin); i1b = min(numel(gEvt), idx1+halfWin);
[~,k1] = max(gEvt(i1a:i1b));  entryIdxEvt = i1a+k1-1;

i2a = max(1, idx2-halfWin); i2b = min(numel(gEvt), idx2+halfWin);
[~,k2] = min(gEvt(i2a:i2b));  exitIdxEvt  = i2a+k2-1;

entrySec = tEvt(entryIdxEvt);
exitSec  = tEvt(exitIdxEvt);

if ~isempty(cfg.forceEntrySec), entrySec = cfg.forceEntrySec; end
if ~isempty(cfg.forceExitSec),  exitSec  = cfg.forceExitSec;  end
assert(exitSec > entrySec, '进入/驶离时刻识别失败。');

%% ==================== MAGNETIC LEVELS ====================
preMask = (t >= entrySec-4.0) & (t <= entrySec-0.25);
if nnz(preMask) < 5, preMask = t < entrySec; end
B0 = median(xSm(preMask));

p0Mask = (t >= entrySec+0.90) & (t <= min(entrySec+2.80, exitSec-1.60));
if nnz(p0Mask) < 5, p0Mask = (t >= entrySec+0.60) & (t <= min(entrySec+1.80, exitSec-1.00)); end
if nnz(p0Mask) < 5, p0Mask = (t > entrySec) & (t < exitSec); end
P0 = median(xSm(p0Mask));

P1 = P0 + cfg.driftDelta;
B1 = B0 + cfg.driftDelta;

%% ==================== 漂移量内部计算（秒时间轴，不显示）====================
% 这一节仅用于确定中段折线的起止高度 Pmid0/Pmid1，不影响显示轴
entryAbs    = cfg.leftPreSec;                               % 入停绝对秒数
midStartAbs = cfg.midStartAbsSec;                           % 中段起始（距入停 10min）
midEndAbs   = cfg.midStartAbsSec + cfg.midShowHours*3600;   % 中段终止
driftRate   = cfg.driftDelta / (cfg.actualOccHours * 3600); % nT/s

Pmid0 = P0 + driftRate * (midStartAbs - entryAbs);   % 中段起始平台高度
Pmid1 = P0 + driftRate * (midEndAbs   - entryAbs);   % 中段终止平台高度

%% ==================== LEFT SEGMENT ====================
leftMask = (t >= entrySec - cfg.leftPreSec) & (t <= entrySec + cfg.leftPostSec);
tLeftRaw = t(leftMask);
xLeftRaw = xSm(leftMask);
assert(numel(tLeftRaw) > 10, '左段窗口数据不足。');

leftPreMask = tLeftRaw <= (entrySec - 0.20);
if nnz(leftPreMask) < 5, leftPreMask = tLeftRaw < entrySec; end
leftOccMask = (tLeftRaw >= entrySec+0.80) & (tLeftRaw <= min(entrySec+2.20, tLeftRaw(end)));
if nnz(leftOccMask) < 5, leftOccMask = tLeftRaw > (entrySec+0.40); end

leftLowRef  = median(xLeftRaw(leftPreMask));
leftHighRef = median(xLeftRaw(leftOccMask));

alphaLeft = map_segment_to_levels(xLeftRaw, leftLowRef, leftHighRef, -0.02, 1.02);
xLeft = B0 + alphaLeft .* (P0 - B0);

% 横轴：0-base 点数索引
kLeft = (0 : numel(xLeft)-1)';

%% ==================== MIDDLE SEGMENT ====================
baseRamp = linspace(Pmid0, Pmid1, cfg.midNumPts)';

occTexMask = (t >= entrySec+0.80) & (t <= exitSec-0.80);
occTex = xSm(occTexMask);

if numel(occTex) >= 8
    trendTex = linspace(occTex(1), occTex(end), numel(occTex))';
    texture  = occTex(:) - trendTex;
    texture  = texture - mean(texture);
    texPeak  = max(abs(texture));
    if texPeak > eps
        texture = texture / texPeak * cfg.midTextureNT;  % 幅值缩放到 ±1.2 nT
    end
    nTile      = ceil(cfg.midNumPts / numel(texture)) + 1;
    texTiled   = repmat(texture, nTile, 1);
    textureMid = texTiled(1:cfg.midNumPts);
    textureMid = movmean(textureMid, 5, 'Endpoints', 'shrink');
else
    rng(7);
    z = cumsum(randn(cfg.midNumPts, 1));
    z = movmean(z, 31, 'Endpoints', 'shrink');
    z = z - linspace(z(1), z(end), numel(z))';
    z = z ./ max(abs(z), eps);
    textureMid = cfg.midTextureNT * z;
end

xMid = baseRamp + textureMid;
kMid = (0 : cfg.midNumPts-1)';   % 0-base 点数

%% ==================== RIGHT SEGMENT ====================
rightMask = (t >= exitSec - cfg.rightPreSec) & (t <= exitSec + cfg.rightPostSec);
tRightRaw = t(rightMask);
xRightRaw = xSm(rightMask);
assert(numel(tRightRaw) > 10, '右段窗口数据不足。');

% 参考平台：避开下降沿（从 exitSec-1s 开始变陡），取 exitSec-3.5 ~ exitSec-1.5
rightOccMask = (tRightRaw >= max(exitSec - cfg.rightPreSec, exitSec-3.5)) & ...
               (tRightRaw <= exitSec - 1.5);
if nnz(rightOccMask) < 5
    rightOccMask = (tRightRaw >= exitSec-2.0) & (tRightRaw <= exitSec-0.8);
end
if nnz(rightOccMask) < 5, rightOccMask = tRightRaw < exitSec; end

% 驶离后背景：信号完全恢复后取
rightPostMask = (tRightRaw >= exitSec+1.5) & (tRightRaw <= min(exitSec+8.0, tRightRaw(end)));
if nnz(rightPostMask) < 5
    rightPostMask = (tRightRaw >= exitSec+0.60) & (tRightRaw <= min(exitSec+6.0, tRightRaw(end)));
end
if nnz(rightPostMask) < 5, rightPostMask = tRightRaw >= exitSec; end

rightHighRef = median(xRightRaw(rightOccMask));
rightLowRef  = median(xRightRaw(rightPostMask));

% 右段 alpha clip 放宽，保留驶离后真实下冲（实测 alpha ≈ -0.114）
alphaRight = map_segment_to_levels(xRightRaw, rightLowRef, rightHighRef, -0.13, 1.05);
xRight = B1 + alphaRight .* (P1 - B1);

kRight = (0 : numel(xRight)-1)';   % 0-base 点数

%% ==================== Y LIMITS ====================
yAll  = [xLeft; xMid; xRight; B0; P0; P1; B1];
ySpan = max(yAll) - min(yAll);
if ySpan < eps, ySpan = 1; end
yPad = 0.08 * ySpan;
yMin = min(yAll) - yPad;
yMax = max(yAll) + yPad;

%% ==================== FIGURE LAYOUT ====================
fig = figure('Color', 'w', 'Position', cfg.figPos, ...
    'MenuBar', 'none', 'ToolBar', 'none');

leftMargin  = 0.07;
rightMargin = 0.03;
bottom      = 0.14;
top         = 0.12;
gap         = 0.055;

ratios  = cfg.widthRatios / sum(cfg.widthRatios);
usableW = 1 - leftMargin - rightMargin - 2*gap;
w1 = usableW * ratios(1);
w2 = usableW * ratios(2);
w3 = usableW * ratios(3);
h  = 1 - bottom - top;

ax1 = axes('Parent', fig, 'Position', [leftMargin,                        bottom, w1, h]);
ax2 = axes('Parent', fig, 'Position', [leftMargin+w1+gap,                 bottom, w2, h]);
ax3 = axes('Parent', fig, 'Position', [leftMargin+w1+gap+w2+gap,          bottom, w3, h]);

for ax = [ax1, ax2, ax3]
    hold(ax, 'on');  grid(ax, 'on');  box(ax, 'on');
    ax.GridAlpha = 0.18;  ax.LineWidth = 1.0;
    ax.FontSize  = cfg.fontSizeTick;
    ax.YLim      = [yMin, yMax];
    ax.Layer     = 'top';
end

%% -------------------- LEFT PANEL --------------------
plot(ax1, kLeft, xLeft, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
yline(ax1, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);

xlim(ax1, [kLeft(1), kLeft(end)]);
xlabel(ax1, 'Sample index', 'FontSize', cfg.fontSizeAxis);
ylabel(ax1, '$B_x$ (nT)', 'Interpreter', 'latex', 'FontSize', 20);
title(ax1, 'D类慢漂移背景场景（X轴，分段展示）', ...
    'FontSize', cfg.fontSizeTitle, 'FontWeight', 'normal');

% 关键刻度：起点、入停点（leftPreSec/dt）、终点
entryKLeft = round(cfg.leftPreSec / dt);   % = 500 @ 50 Hz
xticks(ax1, unique([0, entryKLeft, kLeft(end)]));

%% -------------------- MIDDLE PANEL --------------------
plot(ax2, kMid, xMid, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
yline(ax2, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);

xlim(ax2, [kMid(1), kMid(end)]);
xlabel(ax2, 'Sample index', 'FontSize', cfg.fontSizeAxis);
ax2.YTickLabel = [];

xticks(ax2, [0, round(cfg.midNumPts/2), cfg.midNumPts-1]);

text(ax2, cfg.midNumPts * 0.58, Pmid0 + 0.68*(Pmid1-Pmid0), ...
    {'停车占用平台', '缓慢漂移'}, ...
    'HorizontalAlignment', 'center', ...
    'FontSize', 12, 'Color', [0.35, 0.35, 0.35]);

%% -------------------- RIGHT PANEL --------------------
plot(ax3, kRight, xRight, 'Color', cfg.sigColor, 'LineWidth', cfg.lineWidth);
yline(ax3, B0, '--', 'Color', cfg.baseColor, 'LineWidth', cfg.refLineWidth);

if cfg.showB1
    yline(ax3, B1, '--', 'Color', cfg.base1Color, 'LineWidth', 1.0);
end

xlim(ax3, [kRight(1), kRight(end)]);
xlabel(ax3, 'Sample index', 'FontSize', cfg.fontSizeAxis);
ax3.YTickLabel = [];

% 关键刻度：起点、驶离点（rightPreSec/dt）、终点
exitKRight = round(cfg.rightPreSec / dt);  % = 200 @ 50 Hz
xticks(ax3, unique([0, exitKRight, kRight(end)]));

%% -------------------- BREAK MARKS --------------------
add_break_marks(ax1, 'right');
add_break_marks(ax2, 'left');
add_break_marks(ax2, 'right');
add_break_marks(ax3, 'left');

text(ax1, 1.03, 0.48, '...', 'Units', 'normalized', ...
    'FontSize', 20, 'Color', [0.40,0.40,0.40], 'VerticalAlignment', 'middle');
text(ax2, 1.03, 0.48, '...', 'Units', 'normalized', ...
    'FontSize', 20, 'Color', [0.40,0.40,0.40], 'VerticalAlignment', 'middle');

%% ==================== SAVE ====================
outDir = fileparts(cfg.outImage);
if ~isempty(outDir) && ~exist(outDir, 'dir'), mkdir(outDir); end

exportgraphics(fig, cfg.outImage, 'Resolution', 220);
fprintf('Saved → %s\n', cfg.outImage);

fprintf('\n========= LEVELS =========\n');
fprintf('Entry t = %.3f s  |  Exit t = %.3f s\n', entrySec, exitSec);
fprintf('B0 = %.1f nT,  P0 = %.1f nT\n', B0, P0);
fprintf('B1 = %.1f nT,  P1 = %.1f nT  (drift = %.1f nT)\n', B1, P1, cfg.driftDelta);
fprintf('Left  panel: %d pts  (entry @ k=%d)\n', numel(kLeft),  entryKLeft);
fprintf('Middle panel: %d pts (synthetic)\n', cfg.midNumPts);
fprintf('Right panel: %d pts  (exit  @ k=%d)\n', numel(kRight), exitKRight);
fprintf('rightHighRef = %.1f nT,  rightLowRef = %.1f nT\n', rightHighRef, rightLowRef);

if ~cfg.keepFigureOpen, close(fig); end
end

%% ========================================================================
function T = normalize_table_vars(T)
vars = string(T.Properties.VariableNames);
vars = lower(strtrim(vars));
vars = regexprep(vars, '[^a-z0-9_]', '');
T.Properties.VariableNames = cellstr(vars);
end

function alpha = map_segment_to_levels(xRaw, lowRef, highRef, alphaMin, alphaMax)
den = highRef - lowRef;
if abs(den) < 1e-6
    alpha = zeros(size(xRaw));
else
    alpha = (xRaw - lowRef) ./ den;
end
alpha = movmean(alpha, 3, 'Endpoints', 'shrink');
alpha = min(max(alpha, alphaMin), alphaMax);
end

function w = sec2win(sec, dt)
w = round(sec / dt);
w = max(w, 3);
if mod(w,2) == 0, w = w+1; end
end

function add_break_marks(ax, side)
xL = xlim(ax);  yL = ylim(ax);
dx = 0.018*(xL(2)-xL(1));  dy = 0.025*(yL(2)-yL(1));
switch lower(side)
    case 'right', x0 = xL(2);
    case 'left',  x0 = xL(1);
end
line(ax, [x0-dx,x0+dx], [yL(1)-dy,yL(1)+dy], ...
    'Color',[0.35,0.35,0.35], 'Clipping','off', 'LineWidth',1.0);
line(ax, [x0-dx,x0+dx], [yL(2)-dy,yL(2)+dy], ...
    'Color',[0.35,0.35,0.35], 'Clipping','off', 'LineWidth',1.0);
end