%% ch2_make_p_car_example_from_excel.m
% Rebuild Fig. 2.4 from raw Excel data using the original MATLAB pipeline.
% This script exports preview files only and does NOT overwrite thesis images.

clc; clear; close all;

%% ============ 1) Paths / Config ============
THIS_FILE = mfilename('fullpath');
TOOLS_DIR = fileparts(THIS_FILE);
REPO_ROOT = fileparts(TOOLS_DIR);

PREVIEW_DIR = fullfile(REPO_ROOT, '绘图', '图片新修', '第二章', 'fig_p_car_example_matlab_preview');
if exist(PREVIEW_DIR, 'dir') ~= 7
    mkdir(PREVIEW_DIR);
end

FILE = "G:\地磁组路段数据\路段统计\20240730白沙路数据采集\20240730白沙路车型分类数据采集.xlsx";
SHEET = 2;                  % Python sheet_index=1 -> Excel第2个sheet
ROW_START = 1;              % MATLAB从1开始
ROW_END   = 32740;
RANGE = "A" + ROW_START + ":C" + ROW_END;

FS = 50;                    % 采样率
NTAP = 11;                  % taps数
BETA = 5;                   % Kaiser beta
FC_XY = 5;
FC_Z  = 6;

P_VEH = 0.25;
THETA_ARR = 0.90;
THETA_LEA = 0.50;

BG_QUANTILE = 0.30;         % 取能量低的30%作为背景集合
KAPPA = 3.0;                % sigma放大系数
SIGMA_FLOOR = [0.8, 0.8, 0.8];

TL = 324.0;
TR = 327.0;
X1 = 324.5;
X2 = 326.5;

FONT_CN = 'SimSun';
FONT_EN = 'Times New Roman';
FS_AX   = 12;
FS_LAB  = 14;
FS_LEG  = 12;
FS_THETA = 14;
LW_SIG  = 2.0;
LW_P    = 2.2;
LW_THR  = 1.8;

COLOR_X = [0.0000, 0.4470, 0.7410];
COLOR_Y = [0.8500, 0.3250, 0.0980];
COLOR_Z = [0.9290, 0.6940, 0.1250];

add_ch2_probability_core(REPO_ROOT);

if exist(FILE, 'file') ~= 2
    error('未找到原始数据文件：%s', FILE);
end

%% ============ 2) Read B ============
B = readmatrix(FILE, "Sheet", SHEET, "Range", RANGE);
B = B(:, 1:3);
if any(isnan(B(:)))
    warning('B 中存在 NaN，请检查 Excel 区间或空行。');
end

%% ============ 3) First diff + FIR zero-phase smoothing ============
D = diff(B, 1, 1);
N = size(D, 1);

hXY = fir1(NTAP - 1, FC_XY / (FS / 2), kaiser(NTAP, BETA));
hZ  = fir1(NTAP - 1, FC_Z  / (FS / 2), kaiser(NTAP, BETA));

Dbar = zeros(size(D));
Dbar(:, 1) = filtfilt(hXY, 1, D(:, 1));
Dbar(:, 2) = filtfilt(hXY, 1, D(:, 2));
Dbar(:, 3) = filtfilt(hZ,  1, D(:, 3));

%% ============ 4) Auto-detect main event window ============
E = vecnorm(Dbar, 2, 2);
thr = median(E) + 3 * 1.4826 * mad(E, 1);

idx_evt = find(E > thr);
if ~isempty(idx_evt)
    padL = round(0.4 * FS);
    padR = round(0.6 * FS);
    k1 = max(1, idx_evt(1) - padL);
    k2 = min(N, idx_evt(end) + padR);
    Dbar_use = Dbar(k1:k2, :);
    E_use = E(k1:k2);
else
    Dbar_use = Dbar;
    E_use = E;
    k1 = 1;
    k2 = N;
end

%% ============ 5) Background sigma estimate ============
q = quantile(E_use, BG_QUANTILE);
bgMask = (E_use <= q);

mu0 = [0, 0, 0];
sigma0 = std(Dbar_use(bgMask, :), 0, 1);
sigma0 = max(sigma0, SIGMA_FLOOR);
sigma0 = KAPPA * sigma0;

%% ============ 6) Compute Pcar ============
M = size(Dbar_use, 1);
Pcar = zeros(M, 1);
for i = 1:M
    Pcar(i) = PgetMerge( ...
        Dbar_use(i, 1), Dbar_use(i, 2), Dbar_use(i, 3), ...
        mu0(1), sigma0(1), mu0(2), sigma0(2), mu0(3), sigma0(3), ...
        P_VEH);
end

%% ============ 7) Absolute time ============
idx_use = (k1:k2)';
n_abs   = (ROW_START + idx_use);
t_abs   = (n_abs - 1) / FS;

win = (t_abs >= TL) & (t_abs <= TR);
if ~any(win)
    error(['窗口 [%.2f, %.2f] s 内没有数据。当前 t_abs 范围 = [%.2f, %.2f] s，', ...
           '请检查 ROW_END / FS 或事件裁剪区间。'], ...
          TL, TR, min(t_abs), max(t_abs));
end

t_plot = t_abs(win);
Dbar_plot = Dbar_use(win, :);
Pcar_plot = Pcar(win);

%% ============ 8) Plot ============
fig = figure('Color', 'w', 'Units', 'centimeters', 'Position', [2 2 18 11]);
tl = tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

ax1 = nexttile(tl, 1);
plot(ax1, t_plot, Dbar_plot(:, 1), 'LineWidth', LW_SIG, 'Color', COLOR_X); hold(ax1, 'on');
plot(ax1, t_plot, Dbar_plot(:, 2), 'LineWidth', LW_SIG, 'Color', COLOR_Y);
plot(ax1, t_plot, Dbar_plot(:, 3), 'LineWidth', LW_SIG, 'Color', COLOR_Z);
grid(ax1, 'on'); box(ax1, 'on');
xlim(ax1, [X1 X2]);
set(ax1, 'FontName', FONT_EN, 'FontSize', FS_AX, 'LineWidth', 1.0);
ylabel(ax1, mix_cn_en('磁场差分值', ''), 'FontSize', FS_LAB, 'Interpreter', 'tex');
leg = legend(ax1, ...
    {legend_axis('X'), legend_axis('Y'), legend_axis('Z')}, ...
    'Location', 'northeast', ...
    'FontSize', FS_LEG, ...
    'Interpreter', 'tex', ...
    'Box', 'on');
set(leg, 'FontName', FONT_CN);

ax2 = nexttile(tl, 2);
plot(ax2, t_plot, Pcar_plot, 'LineWidth', LW_P, 'Color', COLOR_X); hold(ax2, 'on');
grid(ax2, 'on'); box(ax2, 'on');
xlim(ax2, [X1 X2]);
ylim(ax2, [-0.02 1.02]);
set(ax2, 'FontName', FONT_EN, 'FontSize', FS_AX, 'LineWidth', 1.0);
xlabel(ax2, mix_cn_en('时间', '(s)'), 'FontSize', FS_LAB, 'Interpreter', 'tex');
ylabel(ax2, '\fontname{SimSun}有车概率 \fontname{Times New Roman}P_{car}', ...
    'Interpreter', 'tex', 'FontSize', FS_LAB);

hArr = yline(ax2, THETA_ARR, '--', 'LineWidth', LW_THR, 'Color', [0.35 0.35 0.35]);
hArr.Label = '\theta_{arr}';
hArr.Interpreter = 'tex';
hArr.FontSize = FS_THETA;
hArr.FontName = FONT_EN;
hArr.LabelHorizontalAlignment = 'left';
hArr.LabelVerticalAlignment = 'middle';

hLea = yline(ax2, THETA_LEA, '--', 'LineWidth', LW_THR, 'Color', [0.35 0.35 0.35]);
hLea.Label = '\theta_{lea}';
hLea.Interpreter = 'tex';
hLea.FontSize = FS_THETA;
hLea.FontName = FONT_EN;
hLea.LabelHorizontalAlignment = 'left';
hLea.LabelVerticalAlignment = 'middle';

%% ============ 9) Export preview only ============
pngOut = fullfile(PREVIEW_DIR, 'Fig_Pcar_matlab_preview.png');
pdfOut = fullfile(PREVIEW_DIR, 'Fig_Pcar_matlab_preview.pdf');
metaOut = fullfile(PREVIEW_DIR, 'Fig_Pcar_matlab_preview_meta.txt');

exportgraphics(fig, pngOut, 'Resolution', 600);
exportgraphics(fig, pdfOut, 'ContentType', 'vector');

fid = fopen(metaOut, 'w');
fprintf(fid, 'Source Excel: %s\n', FILE);
fprintf(fid, 'Sheet: %d\n', SHEET);
fprintf(fid, 'Range: %s\n', RANGE);
fprintf(fid, 'Window: [%.3f, %.3f] s\n', X1, X2);
fprintf(fid, 'Detected event crop in Dbar index: [%d, %d]\n', k1, k2);
fprintf(fid, 'sigma0 = [%.6f, %.6f, %.6f]\n', sigma0(1), sigma0(2), sigma0(3));
fprintf(fid, 'Preview PNG: %s\n', pngOut);
fprintf(fid, 'Preview PDF: %s\n', pdfOut);
fprintf(fid, 'Note: preview only, thesis image not overwritten.\n');
fclose(fid);

disp(['[OK] Saved preview PNG: ' pngOut]);
disp(['[OK] Saved preview PDF: ' pdfOut]);
disp(['[OK] Saved meta TXT: ' metaOut]);


function add_ch2_probability_core(repoRoot)
    candidates = {
        fullfile(repoRoot, '绘图', '第四章', '0304', '_work_ch4', 'ch4_onekey_pack', 'core')
        fullfile(repoRoot, '绘图', '第四章', '0304', '_work_ch4_param_scan', 'ch4_onekey_pack', 'core')
    };
    found = false;
    for i = 1:numel(candidates)
        coreDir = candidates{i};
        if exist(fullfile(coreDir, 'PgetMerge.m'), 'file') == 2
            addpath(coreDir);
            found = true;
            break;
        end
    end
    if ~found
        error('未找到 PgetMerge.m，请检查仓库中的 core 路径。');
    end
end


function s = mix_cn_en(cnText, enText)
    if isempty(enText)
        s = ['\fontname{SimSun}' cnText];
    else
        s = ['\fontname{SimSun}' cnText ' ' '\fontname{Times New Roman}' enText];
    end
end


function s = legend_axis(axisLetter)
    s = ['\fontname{Times New Roman}' axisLetter '\fontname{SimSun}轴差分'];
end
