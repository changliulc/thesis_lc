clc; clear; close all;

%% =============== 0) 读数据（Sheet1，取前三列为Bx By Bz） ===============
file  = "G:\地磁组路段数据\路段统计\20240506南三环\20240506南三环.xlsx";
sheet = 1;   % Sheet1 -> 1；如果你的表名就是"Sheet1"，也可以写 sheet="Sheet1";

data = readmatrix(file, "Sheet", sheet);

% 只取前三列（Bx,By,Bz），并去掉非数值行
B = data(:,1:3);
B = B(all(isfinite(B),2), :);

if size(B,1) < 2000
    error("数据点太少（%d），不适合做统计图。建议用更长片段（至少几万点）。", size(B,1));
end

%% =============== 1) 黄研参数（按论文表3.5/表3.6） ===============
fs = 50;  %#ok<NASGU>  % 黄研按 50Hz 连续点数口径（这里主要用于说明口径）

% 表3.5：无车差分分布标准差（加入一定比例邻道数据后的σ0）
sigma0 = [1.0235, 1.0176, 0.8763];  % [σx, σy, σz]

% 先验
Pveh = 0.25;
Penv = 1 - Pveh;

% 表3.6：状态机参数（50Hz）
theta_arr = 0.90;
theta_lea = 0.50;
Narr = 10;
Nlea = 10;
Td   = 8;

%% =============== 2) 一阶差分 + FIR 平滑得到 Dbar ===============
Dx = diff(B(:,1));
Dy = diff(B(:,2));
Dz = diff(B(:,3));

% 优先使用你工程里同名 FIR（如果你已放在路径里）
useMyFIR = true;

if useMyFIR
    try
        Hd5 = FIRN11Fc5Beta05();  % 你的函数返回 dfilt 对象
        Hd6 = FIRN11Fc6Beta05();
        Dx_bar = filter(Hd5, Dx);
        Dy_bar = filter(Hd5, Dy);
        Dz_bar = filter(Hd6, Dz);
    catch
        warning("没找到 FIRN11Fc*Beta05() 或调用失败，改用 fir1(11) Kaiser(beta=0.5) 设计。");
        % fallback：线性相位 FIR（与之前Python一致口径）
        N = 11; beta = 0.5;
        b5 = fir1(N, 5/(fs/2), kaiser(N+1, beta));  % 5Hz
        b6 = fir1(N, 6/(fs/2), kaiser(N+1, beta));  % 6Hz
        Dx_bar = filter(b5, 1, Dx);
        Dy_bar = filter(b5, 1, Dy);
        Dz_bar = filter(b6, 1, Dz);
    end
else
    % 直接用 fir1 设计
    N = 11; beta = 0.5;
    b5 = fir1(N, 5/(fs/2), kaiser(N+1, beta));
    b6 = fir1(N, 6/(fs/2), kaiser(N+1, beta));
    Dx_bar = filter(b5, 1, Dx);
    Dy_bar = filter(b5, 1, Dy);
    Dz_bar = filter(b6, 1, Dz);
end

Dbar = [Dx_bar(:), Dy_bar(:), Dz_bar(:)];
N = size(Dbar,1);

%% =============== 3) 用黄研公式计算 Pcar(k)（对应p0/p1 + 三轴融合） ===============
% Φ(z) = 0.5*(1+erf(z/sqrt(2)))，避免依赖 Statistics Toolbox 的 normcdf
Phi = @(z) 0.5*(1 + erf(z./sqrt(2)));

% p1_l(k) = 2*Φ(|Dbar|/σ) - 1
zx = abs(Dbar(:,1)) / sigma0(1);
zy = abs(Dbar(:,2)) / sigma0(2);
zz = abs(Dbar(:,3)) / sigma0(3);

x1 = 2*Phi(zx) - 1;   x0 = 1 - x1;
y1 = 2*Phi(zy) - 1;   y0 = 1 - y1;
z1 = 2*Phi(zz) - 1;   z0 = 1 - z1;

% 复刻你工程 PgetMerge 的融合形式
pr_env = (x0 .* y0 .* z0) / (Penv^2);
pr_veh = (x1 .* y1 .* z1) / (Pveh^2);
Pcar = pr_veh ./ (pr_env + pr_veh + 1e-12);

%% =============== 4) 状态机分割事件区间 [tin,tout]（按你截图(2-16)~(2-19)口径） ===============
S1=1; S2=2; S3=3; S4=4; S5=5;
state = S1;
n_arr = 0; n_lea = 0; td = 0;
tin = NaN;

events = zeros(0,2);

for k = 1:N
    p = Pcar(k);

    switch state
        case S1  % 无车
            if p >= theta_arr
                state = S2;
                n_arr = 1;
            end

        case S2  % 到达检测
            if p >= theta_arr
                n_arr = n_arr + 1;
                if n_arr >= Narr
                    tin = k - Narr + 1;
                    state = S3;
                    td = 0;
                end
            else
                state = S1;
                n_arr = 0;
            end

        case S3  % 延时
            td = td + 1;
            if td >= Td
                state = S4;
            end

        case S4  % 车内
            if p <= theta_lea
                state = S5;
                n_lea = 1;
            end

        case S5  % 离开检测
            if p <= theta_lea
                n_lea = n_lea + 1;
                if n_lea >= Nlea
                    tout = k - Nlea + 1;
                    if ~isnan(tin) && tout > tin
                        events(end+1,:) = [tin, tout]; %#ok<SAGROW>
                    end
                    state = S1;
                    n_arr = 0; n_lea = 0; td = 0;
                    tin = NaN;
                end
            else
                state = S4;
                n_lea = 0;
            end
    end
end

fprintf("[INFO] 检测事件数 = %d\n", size(events,1));

carMask = false(N,1);
for i = 1:size(events,1)
    carMask(events(i,1):events(i,2)) = true;
end
envMask = ~carMask;

%% =============== 5) 统计 (b) 无车误触发连续长度：Iarr=1 且无车段 ===============
Iarr_false = (Pcar >= theta_arr) & envMask;

falseLens = run_lengths(Iarr_false);

%% =============== 6) 统计 (c) 事件内回落长度：Pcar <= theta_lea（剔除事件末尾离开段） ===============
dropLens = [];

for i = 1:size(events,1)
    a = events(i,1); b = events(i,2);
    seg = Pcar(a:b);
    m = seg <= theta_lea;

    % 计算m中True的run-length，但剔除“触到末尾”的那段（它是真离开）
    [sIdx, eIdx] = run_segments(m);
    for r = 1:numel(sIdx)
        if eIdx(r) < numel(m)  % 不触到末尾才算“事件内回落”
            dropLens(end+1,1) = eIdx(r) - sIdx(r) + 1; %#ok<SAGROW>
        end
    end
end

%% =============== 7) 画“图2.6 三联统计依据图” ===============
figure('Color','w','Units','centimeters','Position',[2 2 22 6.5]);
tiledlayout(1,3,'TileSpacing','compact','Padding','compact');

% (a) Pcar分布对比
nexttile;
edges = linspace(0,1,41);
h1 = histogram(Pcar(envMask), edges, 'Normalization','pdf'); hold on;
h2 = histogram(Pcar(carMask), edges, 'Normalization','pdf');
h1.FaceAlpha = 0.55; h2.FaceAlpha = 0.55;
xline(theta_arr,'--','\theta_{arr}','LabelVerticalAlignment','bottom');
xline(theta_lea,'--','\theta_{lea}','LabelVerticalAlignment','bottom');
grid on; box on;
title('(a) P_{car}(k) 分布对比','Interpreter','tex');
xlabel('P_{car}'); ylabel('概率密度');
legend({'无车段','有车段'},'Location','best');

% (b) 无车误触发连续长度
nexttile;
if isempty(falseLens)
    text(0.5,0.5,"无车误触发为0（建议用更长数据段）",'HorizontalAlignment','center');
    axis off;
else
    edgesL = 0.5:1:(max(falseLens)+1.5);
    histogram(falseLens, edgesL);
    xline(Narr,'--',sprintf('N_{arr}=%d',Narr),'LabelVerticalAlignment','bottom');
    grid on; box on;
    title('(b) 无车连续触发长度统计','Interpreter','tex');
    xlabel('连续点数'); ylabel('次数');
end

% (c) 事件内回落长度
nexttile;
if isempty(dropLens)
    text(0.5,0.5,"事件内回落统计为空（事件数少或阈值偏低）",'HorizontalAlignment','center');
    axis off;
else
    edgesD = 0.5:1:(max(dropLens)+1.5);
    histogram(dropLens, edgesD);
    xline(Td,'--',sprintf('T_d=%d',Td),'LabelVerticalAlignment','bottom');
    grid on; box on;
    title('(c) 事件内回落长度统计','Interpreter','tex');
    xlabel('连续点数'); ylabel('次数');
end

sgtitle('图2.6 关键参数取值的统计依据示意（参考黄研，50 Hz）','FontWeight','bold');

exportgraphics(gcf, "Fig2_6_param_stats.png", "Resolution", 600);
disp("已导出：Fig2_6_param_stats.png");

%% ====== 辅助函数：连续段长度统计 ======
function lens = run_lengths(mask)
    [sIdx, eIdx] = run_segments(mask);
    lens = eIdx - sIdx + 1;
end

function [sIdx, eIdx] = run_segments(mask)
    mask = mask(:);
    d = diff([false; mask; false]);
    sIdx = find(d == 1);
    eIdx = find(d == -1) - 1;
end