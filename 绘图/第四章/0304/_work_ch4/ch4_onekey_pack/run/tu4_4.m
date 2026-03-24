% clc; clear; close all;
% 
% %% ====== 1) 读 Excel：第2个sheet，只取前三列 ======
% xlsxFile = 'G:\地磁组\lab_office\路段统计\20240723校园测试数据\校园测试20240723.xlsx';
% sheetId  = 2;              % 第二个sheet（你说的那个）
% fs       = 50;             % 采样率(Hz)，你这份数据基本是 50Hz
% 
% M = readmatrix(xlsxFile, 'Sheet', sheetId);
% M = M(:, 1:3);             % 只要前三列
% M = M(all(~isnan(M),2),:); % 去掉空行/NaN
% 
% Bx = double(M(:,1));
% By = double(M(:,2));
% Bz = double(M(:,3));
% 
% N = size(M,1);
% t = (0:N-1)'/fs;
% 
% %% ====== 2) 滤波：优先用 FIR 低通；没有工具箱就退化为 movmean ======
% % 低通截止频率（Hz），你可以按需要调
% fcX = 5; fcY = 5; fcZ = 6;
% beta = 0.5;   % Kaiser 窗参数
% ord  = 11;    % FIR 阶数（越大越平滑，但群延迟也越大）
% 
% useZeroPhase = true; % true 用 filtfilt（相位不延迟）；false 用 filter
% 
% try
%     % 需要 Signal Processing Toolbox: fir1/kaiser/filtfilt
%     bX = fir1(ord, fcX/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
%     bY = fir1(ord, fcY/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
%     bZ = fir1(ord, fcZ/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
% 
%     if useZeroPhase
%         Bx_f = filtfilt(bX, 1, Bx);
%         By_f = filtfilt(bY, 1, By);
%         Bz_f = filtfilt(bZ, 1, Bz);
%     else
%         Bx_f = filter(bX, 1, Bx);
%         By_f = filter(bY, 1, By);
%         Bz_f = filter(bZ, 1, Bz);
%     end
% 
% catch
%     % 没有工具箱：用移动平均（不依赖工具箱）
%     winSec = 0.20;                   % 平滑窗口时长（秒）
%     win    = max(5, round(winSec*fs));
%     if mod(win,2)==0, win = win+1; end
% 
%     Bx_f = movmean(Bx, win);
%     By_f = movmean(By, win);
%     Bz_f = movmean(Bz, win);
% end
% 
% %% ====== 6) 稳定窗双判据示意图（终稿版）======
% % 片段选择：你可以保持当前这段，或换成你认为更典型的一段
% idx0 = 25009; idx1 = 25591;   % 示例：驶入→稳定确认（按你的清洗后行号）
% Bx_s = Bx_f(idx0:idx1);
% By_s = By_f(idx0:idx1);
% Bz_s = Bz_f(idx0:idx1);
% t_s  = (0:numel(Bz_s)-1)'/fs;
% 
% % -------- 参数（与正文口径一致即可）--------
% L_sec = 1.0;                       % 稳定窗长度（秒）
% L     = max(5, round(L_sec*fs));   % 点数
% s     = L;                          % 窗间差的步长（相邻窗）
% w     = [1/3, 1/3, 1/3];            % 三轴权重（示意图可先用均匀）
% 
% R_th_q = 90;                        % 阈值的分位数（示意图用；若有固定阈值可替换为常数）
% M_th_q = 90;
% 
% N_stable_sec = 0.30;                % 连续门控时长（秒）
% N_stable     = max(1, round(N_stable_sec*fs));
% 
% % -------- 构造 R(k)：窗内波动（极差）--------
% rx = movmax(Bx_s, [L-1 0]) - movmin(Bx_s, [L-1 0]);
% ry = movmax(By_s, [L-1 0]) - movmin(By_s, [L-1 0]);
% rz = movmax(Bz_s, [L-1 0]) - movmin(Bz_s, [L-1 0]);
% R  = w(1)*rx + w(2)*ry + w(3)*rz;
% 
% % -------- 构造 M(k)：窗间水平差（相邻窗均值差）--------
% mux = movmean(Bx_s, [L-1 0]);
% muy = movmean(By_s, [L-1 0]);
% muz = movmean(Bz_s, [L-1 0]);
% 
% mx = mux - [nan(s,1); mux(1:end-s)];
% my = muy - [nan(s,1); muy(1:end-s)];
% mz = muz - [nan(s,1); muz(1:end-s)];
% M  = w(1)*abs(mx) + w(2)*abs(my) + w(3)*abs(mz);
% 
% % -------- 阈值（示意图：分位数；若你论文里阈值固定，直接赋常数即可）--------
% R_th = prctile(R(isfinite(R)), R_th_q);
% M_th = prctile(M(isfinite(M)), M_th_q);
% 
% stable_raw  = (R <= R_th) & (M <= M_th);
% stable_gate = movsum(double(stable_raw), [N_stable-1 0]) >= N_stable;
% 
% % -------- 处理“滑窗初始化不可用区间”--------
% idx_valid0 = find(isfinite(R) & isfinite(M), 1, 'first');
% if isempty(idx_valid0), idx_valid0 = 1; end
% t_init0 = t_s(1);
% t_init1 = t_s(idx_valid0);
% 
% % 为了避免 stable 开头出现“伪 0 平台”，用 NaN 断开曲线（不改变判定本身）
% raw_plot  = double(stable_raw);
% gate_plot = double(stable_gate);
% raw_plot(1:idx_valid0-1)  = nan;
% gate_plot(1:idx_valid0-1) = nan;
% 
% % -------- 自动给出 k_out 与 k_st（用于图中标注）--------
% % 这里将“阈值超限区间的最后一点”作为 k_out（不想自动就手动指定）
% idx_unstable = find((R > R_th) | (M > M_th));
% if ~isempty(idx_unstable)
%     k_out = idx_unstable(end);
% else
%     k_out = idx_valid0;
% end
% 
% k_st = find(stable_gate & ((1:numel(stable_gate))' >= k_out), 1, 'first');
% if isempty(k_st), k_st = nan; end
% 
% % -------- 绘图：去工具栏 + 统一版式 --------
% fig = figure('Color','w','MenuBar','none','ToolBar','none',...
%              'Position',[100 100 980 720]);
% 
% tl = tiledlayout(4,1,'Padding','compact','TileSpacing','compact');
% 
% % 1) Bz
% ax1 = nexttile; hold(ax1,'on'); grid(ax1,'on');
% plot(ax1, t_s, Bz_s, 'LineWidth', 1.2);
% ylabel(ax1, 'B_z / nT');
% title(ax1, '稳定窗双判据示意（数据片段）');
% local_shade(ax1, t_init0, t_init1);              % 初始化遮罩
% local_shade_segments(ax1, t_s, stable_gate);     % 稳定窗阴影（门控后）
% xline(ax1, t_s(k_out), '--', 'k_{out}', 'LabelHorizontalAlignment','left');
% if isfinite(k_st)
%     xline(ax1, t_s(k_st), '-',  'k_{st}',  'LabelHorizontalAlignment','left');
%     plot(ax1, t_s(k_st), Bz_s(k_st), 'ko', 'MarkerFaceColor','k', 'MarkerSize',4);
% end
% 
% % 2) R(k)
% ax2 = nexttile; hold(ax2,'on'); grid(ax2,'on');
% plot(ax2, t_s, R, 'LineWidth', 1.2);
% yline(ax2, R_th, '--', 'R_{th}', 'LabelHorizontalAlignment','right');
% ylabel(ax2, 'R(k)');
% local_shade(ax2, t_init0, t_init1);
% 
% % 3) M(k)
% ax3 = nexttile; hold(ax3,'on'); grid(ax3,'on');
% plot(ax3, t_s, M, 'LineWidth', 1.2);
% yline(ax3, M_th, '--', 'M_{th}', 'LabelHorizontalAlignment','right');
% ylabel(ax3, 'M(k)');
% local_shade(ax3, t_init0, t_init1);
% 
% % 4) stable：同时画 raw 与 gate
% ax4 = nexttile; hold(ax4,'on'); grid(ax4,'on');
% stairs(ax4, t_s, raw_plot,  'LineWidth', 0.9);
% stairs(ax4, t_s, gate_plot, 'LineWidth', 1.4);
% ylim(ax4, [-0.1 1.1]);
% ylabel(ax4, 'stable');
% xlabel(ax4, '时间 / s');
% legend(ax4, {'stable\_raw','stable\_gate'}, 'Location','northeast');
% 
% linkaxes([ax1 ax2 ax3 ax4], 'x');
% 
% % -------- 导出：矢量 PDF + 高分辨 PNG --------
% outDir = fullfile(pwd, 'figures');
% if ~exist(outDir,'dir'); mkdir(outDir); end
% 
% outPdf = fullfile(outDir, 'ch4_stability_demo.pdf');
% outPng = fullfile(outDir, 'ch4_stability_demo.png');
% 
% exportgraphics(fig, outPdf, 'ContentType','vector');   % 矢量 PDF（论文推荐）:contentReference[oaicite:1]{index=1}
% exportgraphics(fig, outPng, 'Resolution', 300);
% 
% %% ====== 脚本局部函数（放在文件末尾即可）======
% function local_shade(ax, x0, x1)
%     yl = ylim(ax);
%     p = patch(ax, [x0 x1 x1 x0], [yl(1) yl(1) yl(2) yl(2)], ...
%               [0 0 0], 'EdgeColor','none', 'FaceAlpha',0.06, 'HandleVisibility','off');
%     uistack(p,'bottom');
% end
% 
% function local_shade_segments(ax, t, mask)
%     mask = mask(:) > 0.5;
%     d = diff([false; mask; false]);
%     st = find(d==1);
%     ed = find(d==-1) - 1;
%     yl = ylim(ax);
%     for i = 1:numel(st)
%         x0 = t(st(i)); x1 = t(ed(i));
%         p = patch(ax, [x0 x1 x1 x0], [yl(1) yl(1) yl(2) yl(2)], ...
%                   [0 0 0], 'EdgeColor','none', 'FaceAlpha',0.05, 'HandleVisibility','off');
%         uistack(p,'bottom');
%     end
% end
% 
% %% ====== 3) 基线估计（慢变项）+ 基线扣除 + 三轴融合 ======
% % 基线窗口建议取“明显大于车辆扰动持续时间”的尺度（比如 6~15 秒）
% baseWinSec = 10;                     % 你可调：越大越“慢变”
% baseWin    = max(21, round(baseWinSec*fs));
% if mod(baseWin,2)==0, baseWin = baseWin+1; end
% 
% % 用 movmedian 更稳健（不容易被车辆扰动拉偏）
% Bx_base = movmedian(Bx_f, baseWin);
% By_base = movmedian(By_f, baseWin);
% Bz_base = movmedian(Bz_f, baseWin);
% 
% dBx = Bx_f - Bx_base;
% dBy = By_f - By_base;
% dBz = Bz_f - Bz_base;
% 
% F_merge = sqrt(dBx.^2 + dBy.^2 + dBz.^2);
% 
% %% ====== 4) 画图：4 张图（3轴滤波后原始 + 1张融合） ======
% % 1) Bx 滤波后原始
% figure('Name','Bx 滤波后原始','Color','w');
% plot(t, Bx_f, 'LineWidth', 1); grid on;
% xlabel('时间 / s'); ylabel('B_x / nT');
% title('B_x：滤波后原始波形');
% 
% % 2) By 滤波后原始
% figure('Name','By 滤波后原始','Color','w');
% plot(t, By_f, 'LineWidth', 1); grid on;
% xlabel('时间 / s'); ylabel('B_y / nT');
% title('B_y：滤波后原始波形');
% 
% % 3) Bz 滤波后原始
% figure('Name','Bz 滤波后原始','Color','w');
% plot(t, Bz_f, 'LineWidth', 1); grid on;
% xlabel('时间 / s'); ylabel('B_z / nT');
% title('B_z：滤波后原始波形');
% 
% % 4) 三轴“滤波后减基线”融合
% figure('Name','三轴融合（滤波+减基线）','Color','w');
% plot(t, F_merge, 'LineWidth', 1); grid on;
% xlabel('时间 / s'); ylabel('||\Delta \bf{B}||_2 / nT');
% title('三轴融合：滤波后减基线再融合');
% 
% %% ====== 5) （可选）保存图片 ======
% % outDir = fullfile(pwd, 'fig_wave');
% % if ~exist(outDir,'dir'); mkdir(outDir); end
% % saveas(figure(1), fullfile(outDir,'Bx_filtered.png'));
% % saveas(figure(2), fullfile(outDir,'By_filtered.png'));
% % saveas(figure(3), fullfile(outDir,'Bz_filtered.png'));
% % saveas(figure(4), fullfile(outDir,'Fusion_baselineRemoved.png'));


%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

clc; clear; close all;

%% ============================================================
%  稳定窗双判据示意图（R2024b 终稿版：中文不方块）
%  - 第一行可选显示：Bx / By / Bz / norm（开关 show_axis）
%  - 强制 OpenGL 渲染（避免 painters 中文变方块）
%  - 导出：print -opengl（位图PDF/PNG，论文插图可直接用）
%% ============================================================

%% ===== 0) 用户可配置区 =====
% 第一行显示：'x' | 'y' | 'z' | 'norm'
show_axis = 'z';

% 数据路径（按需修改）
xlsxFile = 'G:\地磁组\lab_office\路段统计\20240723校园测试数据\校园测试20240723.xlsx';
sheetId  = 2;        % 第二个 sheet
fs       = 50;       % 采样率 Hz

% 片段（清洗后 1-based 行号）
idx0 = 25009;
idx1 = 25591;

% 稳定窗参数（与你论文全局参数表对齐）
L        = 25;     % 稳定窗长度（点）
s        = 25;     % 相邻窗步长（点）
N_stable = 5;      % 连续门控窗口数
R_th     = 5.44;   % 波动阈值（nT）
M_th     = 3.50;   % 水平差阈值（nT）

% 字号（可再调大）
FS_AX   = 18;   % 坐标刻度
FS_LAB  = 20;   % 坐标轴标签
FS_TIT  = 18;   % 标题
FS_LEG  = 18;   % 图例
FS_ANN  = 24;   % t_out / t_st 标注
LW_MAIN = 1.6;
LW_AUX  = 1.2;

% 字体（你 listfonts 里确实存在）
FONT_CN = 'SimSun';
FONT_EN = 'Times New Roman';

% 导出分辨率
DPI = 600;

%% ===== 1) 强制 OpenGL（避免 painters）=====
set(groot,'defaultFigureRenderer','opengl');
set(groot,'defaultFigureRendererMode','manual');

% 关闭全局默认解释器，避免中文被 TeX/LaTeX 通道吞掉
set(groot,'defaultTextInterpreter','none');
set(groot,'defaultLegendInterpreter','none');
set(groot,'defaultAxesTickLabelInterpreter','none');

%% ===== 2) 读取 Excel（只取前三列，去 NaN 行） =====
assert(isfile(xlsxFile), 'Excel 文件不存在：%s', xlsxFile);
M = readmatrix(xlsxFile, 'Sheet', sheetId);
M = M(:,1:3);
M = M(all(~isnan(M),2),:);

Bx = double(M(:,1));
By = double(M(:,2));
Bz = double(M(:,3));
N  = size(M,1);
assert(idx0>=1 && idx1<=N && idx1>idx0, 'idx0/idx1 不合法。');

%% ===== 3) 低通滤波（无工具箱则退化 movmean）=====
fcX = 5; fcY = 5; fcZ = 6;   % 截止频率（Hz）
beta = 0.5;
ord  = 11;

try
    bX = fir1(ord, fcX/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
    bY = fir1(ord, fcY/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
    bZ = fir1(ord, fcZ/(fs/2), 'low', kaiser(ord+1, beta), 'scale');
    Bx_f = filtfilt(bX, 1, Bx);
    By_f = filtfilt(bY, 1, By);
    Bz_f = filtfilt(bZ, 1, Bz);
catch
    win = max(5, round(0.20*fs));
    if mod(win,2)==0, win = win+1; end
    Bx_f = movmean(Bx, win);
    By_f = movmean(By, win);
    Bz_f = movmean(Bz, win);
end

%% ===== 4) 基线估计 + 融合（用于 norm）=====
baseWin = max(21, round(10*fs));
if mod(baseWin,2)==0, baseWin = baseWin+1; end

Bx_base = movmedian(Bx_f, baseWin);
By_base = movmedian(By_f, baseWin);
Bz_base = movmedian(Bz_f, baseWin);

dBx = Bx_f - Bx_base;
dBy = By_f - By_base;
dBz = Bz_f - Bz_base;
F_merge = sqrt(dBx.^2 + dBy.^2 + dBz.^2);

%% ===== 5) 截取片段 =====
Bx_s = Bx_f(idx0:idx1);
By_s = By_f(idx0:idx1);
Bz_s = Bz_f(idx0:idx1);
F_s  = F_merge(idx0:idx1);

t_s = (0:numel(Bz_s)-1)'/fs;  % 片段内时间（0 起算）

%% ===== 6) 权重 w（按初始空车段噪声估计）=====
Ns0 = min(N, max(10, round(5*fs)));
sgx = std(Bx_f(1:Ns0));
sgy = std(By_f(1:Ns0));
sgz = std(Bz_f(1:Ns0));
den = sgy*sgz + sgx*sgz + sgx*sgy;
if den < 1e-12
    w = [1/3, 1/3, 1/3];
else
    w = [sgy*sgz, sgx*sgz, sgx*sgy] / den;
end

%% ===== 7) 计算 R(k), M(k) =====
rx = movmax(Bx_s,[L-1 0]) - movmin(Bx_s,[L-1 0]);
ry = movmax(By_s,[L-1 0]) - movmin(By_s,[L-1 0]);
rz = movmax(Bz_s,[L-1 0]) - movmin(Bz_s,[L-1 0]);
R  = w(1)*rx + w(2)*ry + w(3)*rz;

mux = movmean(Bx_s,[L-1 0]);
muy = movmean(By_s,[L-1 0]);
muz = movmean(Bz_s,[L-1 0]);

mx = mux - [nan(s,1); mux(1:end-s)];
my = muy - [nan(s,1); muy(1:end-s)];
mz = muz - [nan(s,1); muz(1:end-s)];
M  = w(1)*abs(mx) + w(2)*abs(my) + w(3)*abs(mz);

stable_raw  = (R <= R_th) & (M <= M_th);
stable_gate = movsum(double(stable_raw), [N_stable-1 0]) >= N_stable;

% 初始化不可用段（NaN）不画，避免“伪 0 平台”
idx_valid0 = find(isfinite(R) & isfinite(M), 1, 'first');
if isempty(idx_valid0), idx_valid0 = 1; end
raw_plot  = double(stable_raw);
gate_plot = double(stable_gate);
raw_plot(1:idx_valid0-1)  = nan;
gate_plot(1:idx_valid0-1) = nan;

%% ===== 8) 第一行信号选择 =====
switch lower(show_axis)
    case 'x'
        S_show = Bx_s; ylab = '$\tilde{B}_x$ / nT'; tag = 'Bx';
    case 'y'
        S_show = By_s; ylab = '$\tilde{B}_y$ / nT'; tag = 'By';
    case 'z'
        S_show = Bz_s; ylab = '$\tilde{B}_z$ / nT'; tag = 'Bz';
    case 'norm'
        S_show = F_s;  ylab = '$\|\Delta\mathbf{B}\|_2$ / nT'; tag = 'norm';
    otherwise
        error('show_axis 只能是 x/y/z/norm');
end

%% ===== 9) 估计 t_out 与 t_st（示意标注）=====
k_out = local_estimate_event_end(S_show, idx_valid0);
k_st  = find(stable_gate & ((1:numel(stable_gate))' >= k_out), 1, 'first');
if isempty(k_st), k_st = nan; end

t_out = t_s(k_out);
if isfinite(k_st)
    t_st = t_s(k_st);
else
    t_st = nan;
end

%% ===== 10) 输出目录 =====
outDir1 = fullfile(pwd, 'out_ch4_thesis', 'images');
outDir2 = fullfile(pwd, 'images');
if isfolder(outDir1)
    outDir = outDir1;
else
    outDir = outDir2;
    if ~isfolder(outDir), mkdir(outDir); end
end

%% ===== 11) 绘图（强制 OpenGL）=====
fig = figure('Color','w','MenuBar','none','ToolBar','none', ...
             'Position',[80 80 1100 780], 'Renderer','opengl');
set(fig,'RendererMode','manual');

% 本 figure 默认字体（保证中文文本继承中文字体）
set(fig,'DefaultTextFontName', FONT_CN);
set(fig,'DefaultAxesFontName', FONT_EN);

TL = tiledlayout(fig, 4, 1, 'Padding','compact', 'TileSpacing','compact');

% 1) 第一行
ax1 = nexttile(TL); hold(ax1,'on'); grid(ax1,'on');
plot(ax1, t_s, S_show, 'LineWidth', LW_MAIN);
ylabel(ax1, ylab, 'Interpreter','latex', 'FontSize', FS_LAB);

title(ax1, sprintf('', tag), ...
      'FontName', FONT_CN, 'FontSize', FS_TIT, 'Interpreter','none');

local_shade(ax1, t_s(1), t_s(idx_valid0));
local_shade_segments(ax1, t_s, stable_gate);

xline(ax1, t_out, '--', 'LineWidth', LW_AUX);
if isfinite(t_st)
    xline(ax1, t_st, '-', 'LineWidth', LW_AUX);
end

% 横向标注（更大、不竖）
% 横向标注（更大、不竖）
yl1   = ylim(ax1);
y_text = yl1(1) + 0.10*(yl1(2)-yl1(1));

% ---- 新增：向前（左）挪动量（秒），给一个自适应的偏移 ----
dx   = max(0.05, 0.02*(t_s(end)-t_s(1)));     % 0.05s 或 x-span 的 2%
xMin = t_s(1) + 0.01*(t_s(end)-t_s(1));       % 防止贴到最左边被裁剪

x_out_txt = max(xMin, t_out - dx);
text(ax1, x_out_txt, y_text, '$t_{out}$', 'Interpreter','latex', ...
     'FontSize', FS_ANN, 'HorizontalAlignment','right', 'VerticalAlignment','bottom', ...
     'Clipping','on');

if isfinite(t_st)
    x_st_txt = max(xMin, t_st - dx);
    text(ax1, x_st_txt, y_text, '$t_{st}$', 'Interpreter','latex', ...
         'FontSize', FS_ANN, 'HorizontalAlignment','right', 'VerticalAlignment','bottom', ...
         'Clipping','on');
end

% 2) R(k)
% 2) R(k)
ax2 = nexttile(TL); hold(ax2,'on'); grid(ax2,'on');
plot(ax2, t_s, R, 'LineWidth', LW_MAIN);
ylabel(ax2, '$R(k)$', 'Interpreter','latex', 'FontSize', FS_LAB);
local_shade(ax2, t_s(1), t_s(idx_valid0));

hR = yline(ax2, R_th, '--', 'LineWidth', LW_AUX);
set(hR,'Label','$R_{th}$', ...
       'Interpreter','latex', ...
       'LabelHorizontalAlignment','right', ...
       'FontSize', FS_ANN);     % ← 这里控制大小
% 3) M(k)
% 3) M(k)
ax3 = nexttile(TL); hold(ax3,'on'); grid(ax3,'on');
plot(ax3, t_s, M, 'LineWidth', LW_MAIN);
ylabel(ax3, '$M(k)$', 'Interpreter','latex', 'FontSize', FS_LAB);
local_shade(ax3, t_s(1), t_s(idx_valid0));

hM = yline(ax3, M_th, '--', 'LineWidth', LW_AUX);
set(hM,'Label','$M_{th}$', ...
       'Interpreter','latex', ...
       'LabelHorizontalAlignment','right', ...
       'FontSize', FS_ANN);     % ← 这里控制大小
% 4) stable
ax4 = nexttile(TL); hold(ax4,'on'); grid(ax4,'on');
stairs(ax4, t_s, raw_plot,  'LineWidth', LW_AUX);
stairs(ax4, t_s, gate_plot, 'LineWidth', LW_MAIN);
ylim(ax4, [-0.1 1.1]);
ylabel(ax4, 'stable', 'FontName', FONT_EN, 'FontSize', FS_LAB);

lg = legend(ax4, {'双判据成立','连续门控后'}, 'Location','northeast');
set(lg, 'FontName', FONT_CN, 'FontSize', FS_LEG, 'Interpreter','none');

xlabel(TL, '时间 / s', 'FontName', FONT_CN, 'FontSize', FS_LAB, 'Interpreter','none');

% 统一刻度字号
axs = [ax1 ax2 ax3 ax4];
for a = axs
    set(a, 'FontSize', FS_AX, 'LineWidth', 0.9);
end
linkaxes(axs,'x');

%% ===== 12) 导出（关键：print -opengl，避免 painters）=====
outPng = fullfile(outDir, sprintf('ch4_stability_demo_%s.png', tag));
outPdf = fullfile(outDir, sprintf('ch4_stability_demo_%s.pdf', tag));

set(fig,'PaperPositionMode','auto');
print(fig, outPng, '-dpng', sprintf('-r%d',DPI), '-opengl');
print(fig, outPdf, '-dpdf', sprintf('-r%d',DPI), '-opengl');

fprintf('Renderer = %s\n', get(fig,'Renderer'));
disp(get(get(ax1,'Title'),'FontName'));
disp(get(get(ax1,'Title'),'Interpreter'));
fprintf('[OK] saved:\n  %s\n  %s\n', outPdf, outPng);

%% ===============================
%  局部函数（必须在文件末尾）
%% ===============================
function local_shade(ax, x0, x1)
    yl = ylim(ax);
    p = patch(ax, [x0 x1 x1 x0], [yl(1) yl(1) yl(2) yl(2)], ...
              [0 0 0], 'EdgeColor','none', 'FaceAlpha',0.06, 'HandleVisibility','off');
    uistack(p,'bottom');
end

function local_shade_segments(ax, t, mask)
    mask = mask(:) > 0.5;
    d = diff([false; mask; false]);
    st = find(d==1);
    ed = find(d==-1) - 1;
    yl = ylim(ax);
    for i = 1:numel(st)
        x0 = t(st(i)); x1 = t(ed(i));
        p = patch(ax, [x0 x1 x1 x0], [yl(1) yl(1) yl(2) yl(2)], ...
                  [0 0 0], 'EdgeColor','none', 'FaceAlpha',0.05, 'HandleVisibility','off');
        uistack(p,'bottom');
    end
end

function k_out = local_estimate_event_end(x, k_min)
    x = x(:);
    dx = abs([0; diff(x)]);
    med = median(dx);
    madv = median(abs(dx - med));
    sigma = 1.4826 * madv;
    thr = med + 6*sigma;
    if ~isfinite(thr) || thr <= 0
        thr = prctile(dx, 95);
    end
    idx = find(dx > thr);
    if isempty(idx)
        k_out = max(1, k_min);
    else
        k_out = max(idx(end), k_min);
    end
end
