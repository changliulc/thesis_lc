% plot_ch4_ABCD_from_win_csv.m
% 读取 fig_a_win.csv / fig_b_win.csv / fig_c_win.csv / fig_d_win.csv
% 画四张图：A类/B类/C类/D类（红色虚线=窗口起点值）
clear; clc; close all;

% ========= 0) 字体（可选）=========
try
    set(groot,'defaultAxesFontName','Microsoft YaHei');
    set(groot,'defaultTextFontName','Microsoft YaHei');
end

% ========= 1) 数据目录（你按实际改）=========
baseDir = 'D:\xidian_Master\研究生论文\毕业论文\实验数据\第四章\数据';

% ========= 2) 是否保存（可选）=========
doSave = true;                      % true=保存 png/pdf，false=只显示
outDir = fullfile(baseDir,'figs');  % 输出目录
if doSave && ~isfolder(outDir), mkdir(outDir); end

% ========= 3) 四个窗口数据文件 =========
items = { ...
    'A', 'A类', fullfile(baseDir,'fig_a_win.csv');
    'B', 'B类', fullfile(baseDir,'fig_b_win.csv');
    'C', 'C类', fullfile(baseDir,'fig_c_win.csv');
    'D', 'D类', fullfile(baseDir,'fig_d_win.csv');
};

% ========= 4) 逐类画图 =========
for i = 1:size(items,1)
    tag   = items{i,1};   % A/B/C/D（用于文件名）
    label = items{i,2};   % A类/B类/C类/D类（用于标题）
    fpath = items{i,3};

    assert(isfile(fpath), "找不到文件：%s", fpath);

    [t,Bx,By,Bz] = read_mag_csv_auto(fpath);

    % 若 t 非升序，按时间排序（防御）
    if any(diff(t) < 0)
        [t,ord] = sort(t);
        Bx = Bx(ord); By = By(ord); Bz = Bz(ord);
    end

    % 红色基准线：取窗口起点值
    refx = Bx(1); refy = By(1); refz = Bz(1);

    fig = figure('Color','w', 'Name', label, 'Position', [120+30*i, 80+30*i, 1200, 720]);
    tlo = tiledlayout(fig, 3, 1, 'TileSpacing','compact', 'Padding','compact');

    ax1 = nexttile(tlo);
    plot(ax1, t, Bx, 'LineWidth', 1.2); hold(ax1,'on');
    yline(ax1, refx, '--r', 'LineWidth', 1.2, 'Alpha', 0.8); hold(ax1,'off');
    ylabel(ax1, 'B_x (nT)'); grid(ax1,'on'); set(ax1,'GridAlpha',0.15);

    ax2 = nexttile(tlo);
    plot(ax2, t, By, 'LineWidth', 1.2); hold(ax2,'on');
    yline(ax2, refy, '--r', 'LineWidth', 1.2, 'Alpha', 0.8); hold(ax2,'off');
    ylabel(ax2, 'B_y (nT)'); grid(ax2,'on'); set(ax2,'GridAlpha',0.15);

    ax3 = nexttile(tlo);
    plot(ax3, t, Bz, 'LineWidth', 1.2); hold(ax3,'on');
    yline(ax3, refz, '--r', 'LineWidth', 1.2, 'Alpha', 0.8); hold(ax3,'off');
    ylabel(ax3, 'B_z (nT)'); xlabel(ax3, '时间 / s');
    grid(ax3,'on'); set(ax3,'GridAlpha',0.15);

    linkaxes([ax1 ax2 ax3],'x');
    xlim(ax1, [t(1), t(end)]);
    title(tlo, label, 'FontSize', 16, 'FontWeight','bold');

    if doSave
        pngPath = fullfile(outDir, sprintf('Fig_%s.png', tag));
        pdfPath = fullfile(outDir, sprintf('Fig_%s.pdf', tag));
        export_fig_safe(fig, pngPath, pdfPath);
    end
end

disp('完成：已生成 A/B/C/D 四张图。');

% ===== 导出（兼容老版本MATLAB）=====
function export_fig_safe(fig, pngPath, pdfPath)
    try
        exportgraphics(fig, pngPath, 'Resolution', 220);
        exportgraphics(fig, pdfPath, 'ContentType','vector');
    catch
        set(fig, 'PaperPositionMode','auto');
        print(fig, pngPath, '-dpng', '-r220');
        print(fig, pdfPath, '-dpdf');
    end
end

% ===== 读取CSV（兼容两种列格式）=====
function [t,Bx,By,Bz] = read_mag_csv_auto(fpath)
    T = readtable(fpath, 'VariableNamingRule','preserve');
    vars = T.Properties.VariableNames;

    % 情况1：t,Bx,By,Bz
    if all(ismember({'t','Bx','By','Bz'}, vars))
        t  = T{:,'t'};
        Bx = T{:,'Bx'}; By = T{:,'By'}; Bz = T{:,'Bz'};
        t = double(t(:)); Bx = double(Bx(:)); By = double(By(:)); Bz = double(Bz(:));
        return;
    end

    % 情况2：k,t,x,y,z（把 x/y/z 当 Bx/By/Bz）
    if all(ismember({'t','x','y','z'}, vars))
        t  = T{:,'t'};
        Bx = T{:,'x'}; By = T{:,'y'}; Bz = T{:,'z'};
        t = double(t(:)); Bx = double(Bx(:)); By = double(By(:)); Bz = double(Bz(:));
        return;
    end

    % 兜底：按列数猜（尽量不让你卡住）
    ncol = width(T);
    A = table2array(T);
    if ncol >= 5
        t  = double(A(:,2)); Bx = double(A(:,3)); By = double(A(:,4)); Bz = double(A(:,5));
    elseif ncol >= 4
        t  = double(A(:,1)); Bx = double(A(:,2)); By = double(A(:,3)); Bz = double(A(:,4));
    else
        error("CSV列数不足：%s", fpath);
    end
end