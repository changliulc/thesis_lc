clc;close all;clear;
%数据读取
file_path = 'D:\Document\lab_office\差分-车型分类\磁偶极子原始车辆数据\2024.6.11车辆数据.xls';
sheet_index = 7; % 指定工作表
range = 'A1:J662';
magDipNum=2;%模型的磁偶极子数量
y_begin=2.2;
param_num = 6*magDipNum-2;%迭代求的向量theta里的参数个数
data_left_num=readmatrix(file_path,'Sheet',sheet_index,'Range',range);
arrive_status=2;
leave_status=4;

%下面计算车辆个数
status_column = data_left_num(:,7);
arrive_row = find(isnan(status_column))+1;
leave_row = find(status_column==4);
vehicle_num = length(leave_row);

choose_vehicle_index=2;%每次需要选择第几个车
data_choose = data_left_num(arrive_row(choose_vehicle_index)-1:leave_row(choose_vehicle_index),:);


%考虑两个磁偶极子,且从三轴角度分别求解并对比
arrive_point=arrive_row(choose_vehicle_index);%读取到达的行序号
leave_point=leave_row(choose_vehicle_index);%读取离开的行序号
data_x=smooth(data_left_num(arrive_point:leave_point,4));%只对车辆数据进行平滑滤波,N=10
data_y=smooth(data_left_num(arrive_point:leave_point,5));%由于滤波的原因，车辆数据长度会减少（N-1）个,数据转变成行向量
data_z=smooth(data_left_num(arrive_point:leave_point,6));
data_x=data_x';data_y=data_y';data_z=data_z';

data=[data_x(:,1),data_y(:,1),data_z(:,1)];%得到下面处理的数据data
L=length(data_x);
v=data_left_num(arrive_point-1,8)/3.6;
u=4*pi*10^(-7);%H/m
w=u*10^9/4/pi/13;
T=0.02;%采样周期 0.01s


% 上下界（根据需要调整）
lower_bound = zeros(1,param_num);
upper_bound = zeros(1,param_num);
%尝试x、y、z轴的边界分开设置
% for i_temp=1:3*magDipNum
%     lower_bound(i_temp) = -3000;%原本是-500
%     upper_bound(i_temp) =  3000;%原本是500
% end
for i_temp=1:magDipNum
    lower_bound((i_temp-1)*3+1) = -3000;%原本是-500
    upper_bound((i_temp-1)*3+1) =  3000;%原本是500
    lower_bound((i_temp-1)*3+2) = -1500;%原本是-500
    upper_bound((i_temp-1)*3+2) =  1500;%原本是500
    lower_bound((i_temp-1)*3+3) = -1500;%原本是-500
    upper_bound((i_temp-1)*3+4) =  1500;%原本是500
end

lower_bound(3*magDipNum+1) = -5.3;%原本是-1.3
upper_bound(3*magDipNum+1) = 5.2;%原本是-0.2  %Z轴初始位置
for i_temp=3*magDipNum+2:magDipNum * 6 - 2
    if mod(i_temp-2,3)==0
        lower_bound(i_temp) = -5.9;%原本是0.1
        upper_bound(i_temp) = 5.9;%原本是5.9  % dx的范围
    else
        lower_bound(i_temp) = -2.31;%原本是-0.31
        upper_bound(i_temp) =  2.31;%原本是0.31      %dy、dz的范围
    end
end
%%
% 定义代价函数 F
F = @(t) cost_function(t, data_choose, y_begin); % y0已知

% 初始参数 theta
theta=[-246.829309540046 358.948220935425 -22.1844831863747 149.621794157071 -500 -241.53491331406 -1.284723064022 0.1 0.262948516380235 0.293112328621707];

% 下界和上界 (lb 和 ub) 分别是约束的下界和上界
lb = lower_bound; % 未知数的约束下界
ub = upper_bound; % 未知数的约束上界

% 模拟退火算法的选项
opts = optimoptions('simulannealbnd', ...
                    'MaxIterations', 200, ... % 最大迭代次数
                    'InitialTemperature', 1000, ... % 初始温度（可根据具体问题调整）
                    'ReannealInterval', 100, ... % 重复退火间隔
                    'TemperatureFcn','temperaturefast',...%温度下降函数
                    'MaxStallIterations',100,...%最大持续的的长度，超过这个就会终止
                    'MaxFunctionEvaluations',100,...%最大函数评价次数
                    'AnnealingFcn','annealingfast',...%生成新的点的方式
                    'PlotFcn', {@saplotbestf,@saplottemperature}); % 绘制优化过程的图

% 使用模拟退火算法进行优化
[theta_opt, fval,exitflag,output] = simulannealbnd(F, theta, lb, ub, opts);

% 输出结果
th = theta_opt;
f = fval;

% 显示优化结果
disp('优化后的参数:');
disp(th);
disp('优化后的函数值:');
disp(f);

% 输出退出标志和详细信息
disp('详细信息:');
disp(output);
%%
%th = [1357.87627899859	-1366.93022607094	-351.643128858895	706.314887838247	449.022151873674	749.872045257412	-5.12867994218825	-5.71159907572754	1.88973171582842	-2.22142162282643];

m=zeros(magDipNum,3);
for i_temp=1:magDipNum
    m(i_temp,:)=[th((i_temp-1)*3+1),th((i_temp-1)*3+2),th((i_temp-1)*3+3)];
end
[n,c]=size(m);
x10=-v*T*L/2;
y0=y_begin; %这里可能需要修改，原来是-1.8，这里应该和java代码里设置的初始值一样
z0=th(magDipNum*3+1);%给定的y0从视频中观察得到
dx=zeros(magDipNum-1);dy=zeros(magDipNum-1);dz=zeros(magDipNum-1);
for i_temp=1:magDipNum-1
    dx(i_temp)=th(magDipNum*3+1 + (i_temp-1)*3 +1);
    dy(i_temp)=th(magDipNum*3+1 + (i_temp-1)*3 +2);
    dz(i_temp)=th(magDipNum*3+1 + (i_temp-1)*3 +3);
end

k=1:1:L;
x1=x10+v*k*T;%第一个磁偶极子的x，其他磁偶极子的可由这个表示出来,这是一个向量,因为k是一个向量，不是一个值
r_vector=zeros(magDipNum,L);
r_vector(1,:)=sqrt(x1.^2+y0^2+z0^2);
for i_temp=2:magDipNum
    r_vector(i_temp,:)=sqrt((x1+dx(i_temp-1)).^2+(y0+dy(i_temp-1)).^2+(z0+dz(i_temp-1)).^2);
end
r_r=r_vector;
%下面的r_x r_y r_z里面，只有r_x是矩阵，其它是向量
r_x=zeros(magDipNum,L);r_y=zeros(magDipNum,1);r_z=zeros(magDipNum,1);
r_x(1,:)=x1;r_y(1)=y0;r_z(1)=z0;
for i_temp=2:magDipNum
    r_x(i_temp,:)=r_x(1,:)+dx(i_temp-1);
    r_y(i_temp)=r_y(1)+dy(i_temp-1);
    r_z(i_temp)=r_z(1)+dz(i_temp-1);
end
%预测值的计算
Bxpre=0;Bypre=0;Bzpre=0;
for i=1:n
    x=r_x(i,:);y=r_y(i);z=r_z(i);r=r_r(i,:);
    Bx=w*((3*x.^2-r.^2)*m(i,1)+3*x*y*m(i,2)+3*x*z*m(i,3))./r.^5;
    By=w*(3*x*y*m(i,1)+(3*y^2-r.^2)*m(i,2)+3*y*z*m(i,3))./r.^5;
    Bz=w*(3*x*z*m(i,1)+3*y*z*m(i,2)+(3*z^2-r.^2)*m(i,3))./r.^5;
    Bxpre=Bxpre+Bx';
    Bypre=Bypre+By';
    Bzpre=Bzpre+Bz';
end

%误差
res=(data(:,1)-Bxpre).^2+(data(:,2)-Bypre).^2+(data(:,3)-Bzpre).^2;
res=sum(res.^0.5)/L;

%%
figure('Name','磁偶极子近似波形');
subplot(1,1,1);
plot(Bxpre,'b');hold on;
plot(data(:,1),'k');hold on;
legend('X轴理论','X轴实际');
ylabel('磁场强度','FontSize',15);
xlabel('时间(单位：10ms)','FontSize',15);
hold on;

figure('Name','磁偶极子近似波形');
subplot(1,1,1);
plot(Bypre,'b');hold on;
plot(data(:,2),'k');hold on;
legend('Y轴理论','Y轴实际');
ylabel('磁场强度','FontSize',15);
xlabel('时间(单位：10ms)','FontSize',15);
hold on;

figure('Name','磁偶极子近似波形');
subplot(1,1,1);
plot(Bzpre,'b');hold on;
plot(data(:,3),'k');hold on;
legend('Z轴理论','Z轴实际');
ylabel('磁场强度','FontSize',15);
xlabel('时间(单位：10ms)','FontSize',15);
hold on;



%%
% figure('Name','X轴原始波形');
% subplot(1,1,1);
% plot(data(:,1),'k');
% legend('X轴原始波形');
% ylabel('磁场强度','FontSize',15);
% xlabel('时间(单位：10ms)','FontSize',15);
% hold on;
% 
% figure('Name','Y轴原始波形');
% subplot(1,1,1);
% plot(data(:,2),'k');
% legend('Y轴原始波形');
% ylabel('磁场强度','FontSize',15);
% xlabel('时间(单位：10ms)','FontSize',15);
% hold on;
% 
% figure('Name','Z轴原始波形');
% subplot(1,1,1);
% plot(data(:,3),'k');
% legend('Z轴原始波形');
% ylabel('磁场强度','FontSize',15);
% xlabel('时间(单位：10ms)','FontSize',15);
% hold on;