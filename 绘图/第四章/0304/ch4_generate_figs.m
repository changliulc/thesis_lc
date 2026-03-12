function ch4_generate_figs()
%% 第四章实验结果图片生成脚本
% 生成以下图片:
%   - ch4_baseline_cmp_f1.png: 不同方法在各工况上的F1对比
%   - ch4_C_seek_ratio.png: C类数据稳定点可得率与退化分支使用率统计
%
% 使用方法: 在MATLAB中运行 ch4_generate_figs

%% 设置中文字体和图形样式
set(0, 'DefaultAxesFontSize', 11);
set(0, 'DefaultTextFontSize', 11);
set(0, 'DefaultAxesFontName', 'SimHei');
set(0, 'DefaultTextFontName', 'SimHei');

%% ========== 图1: 基线对比F1分数 ==========
% 数据说明: 4个工况(A/B/C/D) x 3种方法(SP-FSM, LWC+, ADTA-FSM)
% 请根据实际结果修改以下数据

% 示例数据 (请根据实际结果修改)
groups = {'A', 'B', 'C', 'D'};

% 本文方法
F1_ours = [1.000, 0.968, 0.903, 1.000];  % 从E1_baseline_cmp_by_group.csv读取

% 基线1 (LWC)
F1_baseline1 = [0.957, 0.951, 0.833, 0.985];  % 从E1_baseline_cmp_by_group.csv读取

% 基线2 (ADTA-FSM)
F1_baseline2 = [0.957, 0.912, 0.833, 0.862];  % 从E1_baseline_cmp_by_group.csv读取

% 绘制柱状图
fig1 = figure('Position', [100, 100, 800, 480]);
x = 1:length(groups);
width = 0.25;

bar1 = bar(x - width, F1_ours, width, 'DisplayName', '本文方法');
hold on;
bar2 = bar(x, F1_baseline1, width, 'DisplayName', '基线1');
bar3 = bar(x + width, F1_baseline2, width, 'DisplayName', '基线2');

% 设置坐标轴
xlabel('工况');
ylabel('F_1');
set(gca, 'XTick', x);
set(gca, 'XTickLabel', groups);
ylim([0, 1.15]);  % 增加顶部空间
grid on;
legend('Location', 'northoutside', 'NumColumns', 3, 'FontSize', 10);

% 添加数值标签
for i = 1:length(groups)
    text(i - width, F1_ours(i) + 0.025, sprintf('%.2f', F1_ours(i)), ...
        'HorizontalAlignment', 'center', 'FontSize', 10, 'FontWeight', 'bold');
    text(i, F1_baseline1(i) + 0.025, sprintf('%.2f', F1_baseline1(i)), ...
        'HorizontalAlignment', 'center', 'FontSize', 10, 'FontWeight', 'bold');
    text(i + width, F1_baseline2(i) + 0.025, sprintf('%.2f', F1_baseline2(i)), ...
        'HorizontalAlignment', 'center', 'FontSize', 10, 'FontWeight', 'bold');
end

title('不同方法在各工况上的 F_1 对比 (IoU≥0.5)');
hold off;

% 保存图片
saveas(fig1, 'images/ch4_baseline_cmp_f1.png');
fprintf('图1已保存: images/ch4_baseline_cmp_f1.png\n');


%% ========== 图2: C类数据稳定点可得率与退化触发率 ==========
% 数据说明: 从评估结果中统计C类数据的稳定点可得率和退化触发率

% 实际数据 (从generate_ch4_figs.py读取)
r_found = 0.34;  % 稳定点可得率
r_deg = 0.66;    % 退化触发率

fig2 = figure('Position', [100, 100, 480, 336]);
vals = [r_found, r_deg];

bar_vals = bar([0, 1], vals, 'FaceColor', [0.2, 0.5, 0.8]);
hold on;

% 设置坐标轴
set(gca, 'XTick', [0, 1]);
set(gca, 'XTickLabel', {'稳定点可得率', '退化触发率'});
ylabel('比例');
ylim([0, 1.15]);  % 增加顶部空间
grid on;

% 添加数值标签
for i = 1:length(vals)
    text(i - 1, vals(i) + 0.035, sprintf('%.2f', vals(i)), ...
        'HorizontalAlignment', 'center', 'FontSize', 12, 'FontWeight', 'bold');
end

title('C 类数据稳定点可得率与退化分支使用率统计');
hold off;

% 保存图片
saveas(fig2, 'images/ch4_C_seek_ratio.png');
fprintf('图2已保存: images/ch4_C_seek_ratio.png\n');


%% 关闭图形
close all;
fprintf('所有图片生成完成!\n');
end
