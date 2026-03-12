% % =========================================================================
% % 论文专供：生成“完美”的 C 类和 D 类数据
% % =========================================================================
% clear; clc;
% 
% % 1. 定义数据路径 (请确保路径正确)
% dir_synth = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\synth_out';
% dir_clean = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi';
% 
% % -------------------------------------------------------------------------
% % 2. 改造 C 类: 复制前半段拥堵，填补驶离后的空白
% % -------------------------------------------------------------------------
% c_file_in  = fullfile(dir_synth, '20240723_停车检测_sheet2_e1_C_synth.csv');
% c_file_out = fullfile(dir_synth, '20240723_停车检测_sheet2_e2_C_synth.csv'); % 保存为新文件
% 
% fprintf('正在生成完美 C 类数据...\n');
% Tc = readtable(c_file_in, 'VariableNamingRule', 'preserve');
% t_c = Tc{:, 2};
% Bx_c = Tc{:, 3}; By_c = Tc{:, 4}; Bz_c = Tc{:, 5};
% 
% % 提取 152s 到 168s 之间的拥堵杂波 (减去中位数得到纯波动)
% idx_src = find(t_c >= 152 & t_c <= 168);
% noise_x = Bx_c(idx_src) - median(Bx_c(idx_src));
% noise_y = By_c(idx_src) - median(By_c(idx_src));
% noise_z = Bz_c(idx_src) - median(Bz_c(idx_src));
% 
% % 准备把这段杂波无缝注入到 182s (车辆驶离后)
% idx_dst = find(t_c >= 182);
% L = min(length(noise_x), length(idx_dst));
% 
% % 制作淡入淡出窗口，防止波形出现“断崖式”跳变
% fade_len = 50; % 1秒(50个点)的平滑过渡
% win = ones(L, 1);
% win(1:fade_len) = linspace(0, 1, fade_len)';
% win(end-fade_len+1:end) = linspace(1, 0, fade_len)';
% 
% % 叠加扰动
% Bx_c(idx_dst(1:L)) = Bx_c(idx_dst(1:L)) + noise_x(1:L) .* win;
% By_c(idx_dst(1:L)) = By_c(idx_dst(1:L)) + noise_y(1:L) .* win;
% Bz_c(idx_dst(1:L)) = Bz_c(idx_dst(1:L)) + noise_z(1:L) .* win;
% 
% % 保存 C 类
% Tc{:, 3} = Bx_c; Tc{:, 4} = By_c; Tc{:, 5} = Bz_c;
% writetable(Tc, c_file_out);
% fprintf('--> C类已保存: %s\n', '20240723_停车检测_sheet2_e2_C_synth.csv');
% 
% % -------------------------------------------------------------------------
% % 3. 改造 D 类: 注入全局明显的连续慢漂移
% % -------------------------------------------------------------------------
% d_file_in  = fullfile(dir_clean, '20240723_停车检测_sheet1_clean.csv');
% d_file_out = fullfile(dir_synth, '20240723_停车检测_sheet1_e1_D_synth.csv'); % 保存为D类合成命名格式
% 
% fprintf('正在生成完美 D 类数据...\n');
% Td = readtable(d_file_in, 'VariableNamingRule', 'preserve');
% t_d = Td{:, 2};
% Bx_d = Td{:, 3}; By_d = Td{:, 4}; Bz_d = Td{:, 5};
% 
% % 注入 1.0~1.5 nT/s 的连续倾斜，这样在图表的 60 秒内会有明显的基线爬升/下降
% drift_x =  1.0 * t_d + 0.002 * t_d.^2; 
% drift_y = -1.2 * t_d - 0.001 * t_d.^2;
% drift_z =  1.5 * t_d + 0.003 * t_d.^2;
% 
% Bx_d = Bx_d + drift_x;
% By_d = By_d + drift_y;
% Bz_d = Bz_d + drift_z;
% 
% % 保存 D 类
% Td{:, 3} = Bx_d; Td{:, 4} = By_d; Td{:, 5} = Bz_d;
% writetable(Td, d_file_out);
% fprintf('--> D类已保存: %s\n', '20240723_停车检测_sheet1_e1_D_synth.csv');
% disp('全部完成！');
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% 
% %%
% % =========================================================================
% % 绘制 A, B, C, D 四类典型工况的原始三轴波形图 (已修正列序号)
% % =========================================================================
% clear; clc; close all;
% 
% % 1. 定义你的本地数据文件夹路径
% dir_clean = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi';
% dir_synth = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\synth_out';
% 
% % 2. 定义你要画的文件列表
% % 格式: {'工况类别', '文件名', 所在文件夹, X轴起始时间(s), X轴结束时间(s)}
% % 如果你想看整段全长波形，就把起止时间写成 []
% file_list = {
%     'A', '20240723_停车检测_sheet2_clean.csv',        dir_clean, [], []; 
%     'A', '20240726_停车检测_sheet1_clean.csv',        dir_clean, 14.6, 84.8;  % 根据你提供的数据截取
%     'B', '20240726_停车检测_sheet1_e3_B_synth.csv',   dir_synth, 14.6, 102.1; % 根据你提供的数据截取
%     'C', '20240723_停车检测_sheet2_e1_C_synth.csv',   dir_synth, 29.1, 50.6;  % 根据你提供的数据截取
%     'D', '4_16_停车检测_e1_D_synth.csv',              dir_synth, 82.2, 156.0; % 根据你提供的数据截取
%     % C 类改成我们刚生成的 e2_C_synth，时间锁定在拥堵段 150s 到 205s
%     'C', '20240723_停车检测_sheet2_e2_C_synth.csv',   dir_synth, 150, 205;  
% 
%     % D 类改成我们刚注入漂移的文件，时间锁定在单次停车 0s 到 60s
%     'D', '20240723_停车检测_sheet1_e1_D_synth.csv',   dir_synth, 0, 60;
% };
% 
% % 3. 循环读取并画图
% for i = 1:size(file_list, 1)
%     group   = file_list{i, 1};
%     fname   = file_list{i, 2};
%     folder  = file_list{i, 3};
%     t_start = file_list{i, 4};
%     t_end   = file_list{i, 5};
% 
%     filepath = fullfile(folder, fname);
% 
%     % --- 读取数据 ---
%     try
%         % 读取 CSV，保留原始列名
%         T = readtable(filepath, 'VariableNamingRule', 'preserve');
%     catch
%         warning('文件读取失败，请检查路径是否正确: %s', filepath);
%         continue;
%     end
% 
%     % --- 提取正确的时间 t 和 三轴 Bx, By, Bz ---
%     % 针对 5 列格式: [序号(k), 时间(t), Bx, By, Bz]
%     try
%         t  = T{:, 2}; % 第2列是时间
%         Bx = T{:, 3}; % 第3列是Bx
%         By = T{:, 4}; % 第4列是By
%         Bz = T{:, 5}; % 第5列是Bz
%     catch
%         warning('文件 %s 列数不足 5 列，请检查 CSV 格式！', fname);
%         continue;
%     end
% 
%     % --- 画图 ---
%     fig = figure('Name', sprintf('%s类工况 - %s', group, fname), 'Color', 'w', 'Position', [100, 100, 1000, 700]);
%     tlo = tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
% 
%     % 画 Bx
%     ax1 = nexttile;
%     plot(t, Bx, 'LineWidth', 1.2, 'Color', [0 0.4470 0.7410]);
%     ylabel('B_x', 'FontWeight', 'bold'); 
%     grid on; set(gca, 'GridAlpha', 0.15);
% 
%     % 画 By
%     ax2 = nexttile;
%     plot(t, By, 'LineWidth', 1.2, 'Color', [0 0.4470 0.7410]);
%     ylabel('B_y', 'FontWeight', 'bold'); 
%     grid on; set(gca, 'GridAlpha', 0.15);
% 
%     % 画 Bz
%     ax3 = nexttile;
%     plot(t, Bz, 'LineWidth', 1.2, 'Color', [0 0.4470 0.7410]);
%     ylabel('B_z', 'FontWeight', 'bold'); 
%     xlabel('Time / s', 'FontWeight', 'bold'); 
%     grid on; set(gca, 'GridAlpha', 0.15);
% 
%     % 联动三个子图的 X 轴缩放
%     linkaxes([ax1, ax2, ax3], 'x');
% 
%     % 如果你在上面配置了 t_start 和 t_end，就会自动放大到那个区间
%     if ~isempty(t_start) && ~isempty(t_end)
%         % 确保 t_start < t_end，防止数组写反报错
%         xlim(ax1, [min(t_start, t_end), max(t_start, t_end)]);
%     end
% 
%     % 添加总标题 (strrep 用于防止下划线 _ 把后续字符变成下标)
%     title(tlo, sprintf('%s类工况波形展示: %s', group, strrep(fname, '_', '\_')), 'FontSize', 14);
% end




% =========================================================================
% 论文出图终极版：物理事件触发型热漂移 (从 70s 开始平滑漂移)
% =========================================================================
clear; clc; close all;

% 1. 定义数据路径
dir_synth = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\synth_out';
dir_clean = 'D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi';

% -------------------------------------------------------------------------
% 2. 改造 C 类与 D 类
% -------------------------------------------------------------------------
c_file_in  = fullfile(dir_synth, '20240723_停车检测_sheet2_e1_C_synth.csv');
c_file_out = fullfile(dir_synth, '20240723_停车检测_sheet2_e2_C_synth.csv');
d_file_in  = fullfile(dir_clean, '20240723_停车检测_sheet1_clean.csv');
d_file_out = fullfile(dir_synth, '20240723_停车检测_sheet1_e1_D_synth.csv');

fprintf('正在生成物理事件触发型漂移数据...\n');
try
    % 生成 C 类 (拥堵后置)
    Tc = readtable(c_file_in, 'VariableNamingRule', 'preserve');
    t_c = Tc{:, 2}; Bx_c = Tc{:, 3}; By_c = Tc{:, 4}; Bz_c = Tc{:, 5};
    dt_c = diff(t_c); fs_c = round(1/median(dt_c(isfinite(dt_c) & dt_c>0)));
    idx_src = find(t_c >= 152 & t_c <= 168);
    nx = Bx_c(idx_src) - median(Bx_c(idx_src));
    ny = By_c(idx_src) - median(By_c(idx_src));
    nz = Bz_c(idx_src) - median(Bz_c(idx_src));
    [Bx_c, By_c, Bz_c] = inject_after_time(Bx_c, By_c, Bz_c, t_c, 182, nx, ny, nz, fs_c, 1.0, 1.0);
    Tc{:, 3} = Bx_c; Tc{:, 4} = By_c; Tc{:, 5} = Bz_c; writetable(Tc, c_file_out);

    % 生成 D 类 (从 70s 提前开始触发热漂移)
    Td = readtable(d_file_in, 'VariableNamingRule', 'preserve');
    t_d = Td{:, 2}; Bx_d = Td{:, 3}; By_d = Td{:, 4}; Bz_d = Td{:, 5};
    dt_d = diff(t_d); fs_d = round(1/median(dt_d(isfinite(dt_d) & dt_d>0)));
    rng(42); 
    
    % 【关键修改】：将触发时间从 85s 改为 70s
    [dx, dy, dz] = make_event_triggered_drift(t_d, fs_d, [150, -180, 140], 35, 70);
    Td{:, 3} = Bx_d + dx; Td{:, 4} = By_d + dy; Td{:, 5} = Bz_d + dz; writetable(Td, d_file_out);
catch ME
    warning('数据处理出错: %s', ME.message);
end
disp('数据生成完毕，开始绘图...');

% -------------------------------------------------------------------------
% 3. 精选 4 张图的配置列表
% -------------------------------------------------------------------------
file_list = {
    'A', '20240723_停车检测_sheet2_clean.csv',        dir_clean, 210, 290; 
    'B', '20240726_停车检测_sheet1_e3_B_synth.csv',   dir_synth, 155, 195; 
    'C', '20240723_停车检测_sheet2_e2_C_synth.csv',   dir_synth, 150, 205; 
    'D', '20240723_停车检测_sheet1_e1_D_synth.csv',   dir_synth,  60, 120; 
};

% -------------------------------------------------------------------------
% 4. 循环画图
% -------------------------------------------------------------------------
for i = 1:size(file_list, 1)
    group   = file_list{i, 1};
    fname   = file_list{i, 2};
    folder  = file_list{i, 3};
    t_start = file_list{i, 4};
    t_end   = file_list{i, 5};
    
    filepath = fullfile(folder, fname);
    try
        T = readtable(filepath, 'VariableNamingRule', 'preserve');
        t = T{:, 2}; Bx = T{:, 3}; By = T{:, 4}; Bz = T{:, 5};
    catch
        continue;
    end
    
    % 寻找当前画面的起点，用来画红色水平基准线
    if ~isempty(t_start)
        idx0 = find(t >= min(t_start, t_end), 1, 'first');
    else
        idx0 = 1;
    end
    if isempty(idx0), idx0 = 1; end
    ref_x = Bx(idx0); ref_y = By(idx0); ref_z = Bz(idx0);
    
    fig = figure('Name', sprintf('%s类 - %s', group, fname), 'Color', 'w', 'Position', [100+i*30, 100+i*30, 1000, 700]);
    tlo = tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
    
    ax1 = nexttile; plot(t, Bx, 'LineWidth', 1.2, 'Color', [0 0.4470 0.7410]); hold on;
    yline(ref_x, '--r', 'LineWidth', 1.5, 'Alpha', 0.8); hold off; 
    ylabel('B_x (nT)', 'FontWeight', 'bold'); grid on; set(gca, 'GridAlpha', 0.15);
    
    ax2 = nexttile; plot(t, By, 'LineWidth', 1.2, 'Color', [0 0.4470 0.7410]); hold on;
    yline(ref_y, '--r', 'LineWidth', 1.5, 'Alpha', 0.8); hold off; 
    ylabel('B_y (nT)', 'FontWeight', 'bold'); grid on; set(gca, 'GridAlpha', 0.15);
    
    ax3 = nexttile; plot(t, Bz, 'LineWidth', 1.2, 'Color', [0 0.4470 0.7410]); hold on;
    yline(ref_z, '--r', 'LineWidth', 1.5, 'Alpha', 0.8); hold off; 
    ylabel('B_z (nT)', 'FontWeight', 'bold'); xlabel('时间 / s', 'FontWeight', 'bold'); grid on; set(gca, 'GridAlpha', 0.15);
    
    linkaxes([ax1, ax2, ax3], 'x');
    if ~isempty(t_start) && ~isempty(t_end)
        xlim(ax1, [min(t_start, t_end), max(t_start, t_end)]);
    end
    title(tlo, sprintf('%s类工况: %s', group, strrep(fname, '_', '\_')), 'FontSize', 14, 'FontWeight', 'bold');
end

% =========================================================================
% 助手函数
% =========================================================================
function [dx, dy, dz] = make_event_triggered_drift(t, fs, max_drift_xyz, tau, start_time)
    % 事件触发型漂移：在 start_time 之前无漂移，之后开始呈指数型热漂移
    N = numel(t);
    dx = zeros(N, 1); dy = zeros(N, 1); dz = zeros(N, 1);
    
    % 找到触发时刻对应的索引
    idx = find(t >= start_time);
    if isempty(idx), return; end
    
    % 漂移的时间轴只从触发时刻开始算
    tr = t(idx) - t(idx(1));
    
    % 1. 热冲击指数衰减曲线 (仅在触发后)
    drift_therm = 1 - exp(-tr / tau); 
    
    % 2. 极低频缓慢起伏 (确保在 0 点处平滑起步)
    M = numel(idx);
    rw = cumsum(randn(M, 3), 1);
    rw = movmean(rw, round(fs * 5), 1); 
    rw = rw - rw(1,:);
    rw = rw ./ max(1e-9, max(abs(rw), [], 1)); 
    
    % 3. 合成并赋值到对应区间
    dx(idx) = max_drift_xyz(1) * (0.90 * drift_therm + 0.10 * rw(:,1));
    dy(idx) = max_drift_xyz(2) * (0.90 * drift_therm + 0.10 * rw(:,2));
    dz(idx) = max_drift_xyz(3) * (0.90 * drift_therm + 0.10 * rw(:,3));
end

function [Bx,By,Bz] = inject_after_time(Bx,By,Bz, t, dstStart, nX,nY,nZ, fs, scale, fadeSec)
    idxDst = find(t>=dstStart); L = min([numel(idxDst), numel(nX), numel(nY), numel(nZ)]);
    if L<10; return; end
    fadeLen = max(1, round(fs*fadeSec)); w = ones(L,1); fade = linspace(0,1,fadeLen)';
    if L > 2*fadeLen, w(1:fadeLen) = fade; w(end-fadeLen+1:end) = flipud(fade); end
    ii = idxDst(1:L); Bx(ii) = Bx(ii) + scale*w.*nX(1:L); By(ii) = By(ii) + scale*w.*nY(1:L); Bz(ii) = Bz(ii) + scale*w.*nZ(1:L);
end