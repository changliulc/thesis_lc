clc; clear; close all;

%% =======================
%  ch4_pass_vs_park (reference layout + correct waveforms)
%  目标：对齐你给的“第二张参考图”的右侧波形形态（包含到达峰+驶离峰）
%
%  核心做法：
%   - 通过段：以 dp 峰值为中心，截取 10 s（峰值约落在 5 s）
%   - 停车段：在 dk 中找“较晚的主峰”（驶离），把它对齐到 20 s，截取 25 s
%   - 布局：2x2，上行统一y轴，下行统一y轴；右列不放y标签；左上图例带框
%   - 导出：print + PaperSize=FigureSize（兼容旧版本）
%% =======================

%% ====== 0) 配置区 ======
xlsxFile  = 'G:\地磁组\lab_office\路段统计\20240723校园测试数据\校园测试20240723.xlsx';
sheetSel  = '下午';
fs = 50;

% 取窗（确保窗口足够长，能包含停车“到达+驶离”）
passWinSec = [406, 443];
parkWinSec = [70, 115];

useRelativeTime = true;
preSec = 1.0;

% 显示长度（秒）
L_pass_show = 10;      % 左列显示 0~10 s
L_park_show = 25;      % 右列显示 0~25 s

% 停车：把“驶离峰”对齐到 20 s（与你参考图一致）
t_depart_target = 20;  % s

% 低通滤波参数
fcX = 5; fcY = 5; fcZ = 6;
beta = 0.5;
ord  = 11;
useZeroPhase = true;

outPdf = fullfile(pwd, 'ch4_pass_vs_park.pdf');
outPng = fullfile(pwd, 'ch4_pass_vs_park.png');

%% ====== 1) 读Excel：只取前三列 ======
M = readmatrix(xlsxFile, 'Sheet', sheetSel);
M = M(:, 1:3);
M = M(all(~isnan(M),2),:);

Bx = double(M(:,1));
By = double(M(:,2));
Bz = double(M(:,3));

N = size(M,1);
t = (0:N-1)'/fs;

%% ====== 2) 滤波 ======
try
    bX = fir1(ord, fcX/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
    bY = fir1(ord, fcY/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
    bZ = fir1(ord, fcZ/(fs/2), 'low', kaiser(ord+1, beta), 'scale');

    if useZeroPhase
        Bx_f = filtfilt(bX, 1, Bx);
        By_f = filtfilt(bY, 1, By);
        Bz_f = filtfilt(bZ, 1, Bz);
    else
        Bx_f = filter(bX, 1, Bx);
        By_f = filter(bY, 1, By);
        Bz_f = filter(bZ, 1, Bz);
    end
catch
    winSec = 0.20;
    win = max(5, round(winSec*fs));
    if mod(win,2)==0, win=win+1; end
    Bx_f = movmean(Bx, win);
    By_f = movmean(By, win);
    Bz_f = movmean(Bz, win);
end

%% ====== 3) 取窗 + 去基线（三轴） + 差分幅值 ======
sec2idx = @(tw) [max(1, floor(tw(1)*fs)+1), min(N, floor(tw(2)*fs)+1)];

kp = sec2idx(passWinSec);  k1p = kp(1); k2p = kp(2);
kk = sec2idx(parkWinSec);  k1k = kk(1); k2k = kk(2);

preN = max(1, round(preSec*fs));

B0p = mean([Bx_f(k1p:min(N,k1p+preN-1)), By_f(k1p:min(N,k1p+preN-1)), Bz_f(k1p:min(N,k1p+preN-1))], 1);
B0k = mean([Bx_f(k1k:min(N,k1k+preN-1)), By_f(k1k:min(N,k1k+preN-1)), Bz_f(k1k:min(N,k1k+preN-1))], 1);

Bp = [Bx_f(k1p:k2p), By_f(k1p:k2p), Bz_f(k1p:k2p)] - B0p;
Bk = [Bx_f(k1k:k2k), By_f(k1k:k2k), Bz_f(k1k:k2k)] - B0k;

Bf = [Bx_f, By_f, Bz_f];
dBmag = [0; sqrt(sum(diff(Bf,1,1).^2, 2))];

if useRelativeTime
    tp = t(k1p:k2p) - t(k1p);
    tk = t(k1k:k2k) - t(k1k);
else
    tp = t(k1p:k2p);
    tk = t(k1k:k2k);
end

dp = dBmag(k1p:k2p);
dk = dBmag(k1k:k2k);

Tp = tp(end);
Tk = tk(end);

%% ====== 4) 通过段：以 dp 峰值居中截取 10 s（峰值落在约5 s）=====
[~, iPeakP] = max(dp);
tPeakP = tp(iPeakP);
t0p = tPeakP - 0.5*L_pass_show;
t0p = clamp(t0p, 0, max(0, Tp - L_pass_show));
t1p = t0p + L_pass_show;

selP = (tp >= t0p) & (tp <= t1p);
tpS  = tp(selP) - t0p;
BpS  = Bp(selP,:);
dpS  = dp(selP);

%% ====== 5) 停车段：对齐“驶离峰”到 20 s，截取 25 s ======
% 取 dk 的两个“相距足够远”的主峰，选时间更晚的作为驶离峰
[idxA, idxD] = pick_two_peaks(dk, fs);   % idxD 更晚
tDepart = tk(idxD);

t0k = tDepart - t_depart_target;        % 让驶离峰出现在 20 s
t0k = clamp(t0k, 0, max(0, Tk - L_park_show));
t1k = t0k + L_park_show;

selK = (tk >= t0k) & (tk <= t1k);
tkS  = tk(selK) - t0k;
BkS  = Bk(selK,:);
dkS  = dk(selK);

%% ====== 6) 作图（参考图布局）=====
co = [0.0000 0.4470 0.7410;
      0.8500 0.3250 0.0980;
      0.9290 0.6940 0.1250];

FONT_CN = pick_cn_font();
FONT_EN = 'Times New Roman';

FS_AX  = 10.5;
FS_LAB = 12;
FS_TIT = 13;

fig = figure('Color','w', 'Units','centimeters', 'Position',[2 2 20 11.5]);
movegui(fig,'center');

tl = tiledlayout(fig, 2, 2, 'TileSpacing','compact', 'Padding','compact');

% --- 上左：通过三轴扰动 ---
ax1 = nexttile(tl,1); hold(ax1,'on'); grid(ax1,'on');
set(ax1,'FontName',FONT_EN,'FontSize',FS_AX,'ColorOrder',co,'Box','off');
plot(ax1, tpS, BpS, 'LineWidth', 1.2);
yline(ax1, 0, '--', 'LineWidth', 0.9);
xlim(ax1, [0, L_pass_show]);
title(ax1, '通过事件：三轴扰动', 'FontWeight','normal', 'FontName',FONT_CN,'FontSize',FS_TIT,'Interpreter','none');
yl1 = ylabel(ax1, '磁场扰动 / nT', 'FontName',FONT_CN,'FontSize',FS_LAB,'Interpreter','none');

lg1 = legend(ax1, {'X轴','Y轴','Z轴'}, 'Location','northwest');
set(lg1,'FontName',FONT_CN,'FontSize',FS_AX,'Interpreter','none');
lg1.Box = 'on';

% --- 上右：停车三轴扰动 ---
ax2 = nexttile(tl,2); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'FontName',FONT_EN,'FontSize',FS_AX,'ColorOrder',co,'Box','off');
plot(ax2, tkS, BkS, 'LineWidth', 1.2);
yline(ax2, 0, '--', 'LineWidth', 0.9);
xlim(ax2, [0, L_park_show]);
title(ax2, '停车事件：三轴扰动', 'FontWeight','normal', 'FontName',FONT_CN,'FontSize',FS_TIT,'Interpreter','none');
ylabel(ax2, '');

% --- 下左：通过差分幅值 ---
ax3 = nexttile(tl,3); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'FontName',FONT_EN,'FontSize',FS_AX,'Box','off');
plot(ax3, tpS, dpS, 'LineWidth', 1.2);
xlim(ax3, [0, L_pass_show]);
xlabel(ax3, '时间 / s', 'FontName',FONT_CN,'FontSize',FS_LAB,'Interpreter','none');
yl3 = ylabel(ax3, '差分幅值 ||\Delta_1\bf{B}||_2', 'FontName',FONT_CN,'FontSize',FS_LAB,'Interpreter','tex');

% --- 下右：停车差分幅值 ---
ax4 = nexttile(tl,4); hold(ax4,'on'); grid(ax4,'on');
set(ax4,'FontName',FONT_EN,'FontSize',FS_AX,'Box','off');
plot(ax4, tkS, dkS, 'LineWidth', 1.2);
xlim(ax4, [0, L_park_show]);
xlabel(ax4, '时间 / s', 'FontName',FONT_CN,'FontSize',FS_LAB,'Interpreter','none');
ylabel(ax4, '');

% ===== 上行统一 y 轴 =====
yTopAll = [BpS(:); BkS(:)];
yTopMin = min(yTopAll);  yTopMax = max(yTopAll);
padTop  = 0.06 * max(1, (yTopMax - yTopMin));
ylim(ax1, [yTopMin-padTop, yTopMax+padTop]);
ylim(ax2, [yTopMin-padTop, yTopMax+padTop]);

% ===== 下行统一 y 轴（从0开始）=====
yBotMax = max([dpS(:); dkS(:)]);
padBot  = 0.06 * max(1, yBotMax);
ylim(ax3, [0, yBotMax+padBot]);
ylim(ax4, [0, yBotMax+padBot]);

title(tl, '车辆通过与停靠对比', 'FontWeight','normal', 'FontName',FONT_CN,'FontSize',FS_TIT+1,'Interpreter','none');

% 左列两行 ylabel 同列对齐
set([yl1 yl3], 'Units','normalized');
xAlign = max([yl1.Position(1), yl3.Position(1)]);
p = yl1.Position; p(1) = xAlign; yl1.Position = p;
p = yl3.Position; p(1) = xAlign; yl3.Position = p;

% 收紧留白
axs = [ax1 ax2 ax3 ax4];
for i = 1:numel(axs)
    ti = get(axs(i),'TightInset');
    set(axs(i),'LooseInset', ti + [0.002 0.002 0.002 0.002]);
end

%% ====== 7) 导出（兼容旧版本；避免旋转中文在矢量PDF里出问题）=====
set(fig, 'PaperUnits','centimeters');
pos = get(fig,'Position');   % [left bottom width height] in cm
w = pos(3); h = pos(4);
set(fig, 'PaperSize',[w h]);
set(fig, 'PaperPosition',[0 0 w h]);
set(fig, 'PaperPositionMode','manual');

print(fig, outPdf, '-dpdf', '-opengl', '-r600');
print(fig, outPng, '-dpng', '-r600');

fprintf('Saved: %s\nSaved: %s\n', outPdf, outPng);

%% ====== 工具函数 ======
function y = clamp(x, lo, hi)
    y = min(max(x, lo), hi);
end

function [idxA, idxD] = pick_two_peaks(sig, fs)
% 不依赖 findpeaks：用平滑+排除窗口选两个主峰（相距>=2s）
    sig = sig(:);
    w = max(3, round(0.20*fs));            % 0.2 s 平滑
    sigS = movmean(sig, w);

    [~, ord] = sort(sigS, 'descend');
    idx1 = ord(1);

    minGap = max(1, round(2.0*fs));        % 两峰最小间隔 2 s
    idx2 = idx1;
    for k = 2:numel(ord)
        if abs(ord(k) - idx1) >= minGap
            idx2 = ord(k);
            break;
        end
    end

    idxA = min(idx1, idx2);   % 更早的峰（到达）
    idxD = max(idx1, idx2);   % 更晚的峰（驶离）
end

function f = pick_cn_font()
    cand = {'Microsoft YaHei','Microsoft YaHei UI','SimHei','SimSun','Arial Unicode MS'};
    fonts = listfonts;
    f = cand{end};
    for k = 1:numel(cand)
        if any(strcmpi(fonts, cand{k}))
            f = cand{k};
            return;
        end
    end
end