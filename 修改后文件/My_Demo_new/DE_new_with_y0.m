%这个文件是20240616写的，把y轴的初始距离y0加入到参数theta中
clc;close all;clear;
% 差分进化（DE）算法的MATLAB实现
% 参数
population_size = 500;
iter_num = 100;
magDipNum = 2; % 磁偶极子的数量
param_num = magDipNum * 6 - 1; % 根据需要调整
%y_begin=2.2;%y轴距离初始位置
F = 0.5; % 变异因子
CR = 0.5; % 交叉率

% 读取Excel文件
file_path = 'D:\Document\lab_office\差分-车型分类\磁偶极子原始车辆数据\2024.6.11车辆数据.xls';
sheet_index = 4; % 指定工作表
range = 'A1:J111';
data = readmatrix(file_path, 'Sheet', sheet_index,'Range',range);


% 上下界（根据需要调整）
lower_bound = zeros(1,param_num);
upper_bound = zeros(1,param_num);
for i_temp=1:3*magDipNum
    lower_bound(i_temp) = -1500;%原本是-500
    upper_bound(i_temp) =  1500;%原本是500
end
%尝试x、y、z轴的边界分开设置
% for i_temp=1:magDipNum
%     lower_bound((i_temp-1)*3+1) = -1000;%原本是-500
%     upper_bound((i_temp-1)*3+1) =  1000;%原本是500
%     lower_bound((i_temp-1)*3+2) = -500;%原本是-500
%     upper_bound((i_temp-1)*3+2) =  500;%原本是500
%     lower_bound((i_temp-1)*3+3) = -500;%原本是-500
%     upper_bound((i_temp-1)*3+4) =  500;%原本是500
% end
lower_bound(3*magDipNum+1) = -1.3;%原本是-1.3  %Z轴初始位置
upper_bound(3*magDipNum+1) = -0.2;%原本是-0.2
for i_temp=3*magDipNum+2:magDipNum * 6 - 2
    if mod(i_temp-2,3)==0
        lower_bound(i_temp) = 0.1;%原本是0.1
        upper_bound(i_temp) = 5.9;%原本是5.9   % dx的范围
    else
        lower_bound(i_temp) = -1.31;%原本是-0.31
        upper_bound(i_temp) =  5.31;%原本是0.31      %dy、dz的范围
    end
end
lower_bound(magDipNum * 6 - 1) = 1.5;%新增加的y轴初始位置y0的范围
upper_bound(magDipNum * 6 - 1) = 2.5;
%下面计算车辆个数
status_column = data(:,7);
arrive_row = find(isnan(status_column))+1;
leave_row = find(status_column==4);
vehicle_num = length(leave_row);

choose_vehicle_index=1;
data_choose = data(arrive_row(choose_vehicle_index)-1:leave_row(choose_vehicle_index),:);
%data_choose是要仿真的车辆数据，第一行是状态，剩下的才是磁场数据

% 初始化种群
population = lower_bound + (upper_bound - lower_bound) .* rand(population_size, param_num);
scores = zeros(population_size, 1);

% 适应度函数（示例，根据实际适应度函数替换）
%这里新建了一个文件 cost_function_with_y0

% 评估初始种群
for i = 1:population_size
    scores(i) = cost_function_with_y0(population(i, :),data_choose);
end

% 差分进化主循环
for iter = 1:iter_num
    for i = 1:population_size
        % 随机选择三个个体
        indices = randperm(population_size, 3);
        x1 = population(indices(1), :);
        x2 = population(indices(2), :);
        x3 = population(indices(3), :);
        
        % 变异
        mutant = x1 + F * (x2 - x3);
        
        % 确保变异向量在边界内
        mutant = max(min(mutant, upper_bound), lower_bound);
        
        % 交叉
        trial = population(i, :);
        for j = 1:param_num
            if rand <= CR
                trial(j) = mutant(j);
            end
        end
        
        % 确保试验向量在边界内
        trial = max(min(trial, upper_bound), lower_bound);
        
        % 选择
        trial_score = cost_function_with_y0(trial,data_choose);
        if trial_score < scores(i)
            population(i, :) = trial;
            scores(i) = trial_score;
        end
    end
    
    % 可选：记录最佳解
    [best_score, best_idx] = min(scores);
    best_solution = population(best_idx, :);
    
    % 显示迭代进度
    fprintf('Iteration %d, Best Score: %.4f\n', iter, best_score);
end

% 输出最佳解
fprintf('Best Solution: %s\n', mat2str(best_solution));
fprintf('Best Score: %.4f\n', best_score);
