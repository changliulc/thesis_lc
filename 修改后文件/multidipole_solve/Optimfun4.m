% function f=Optim_obj_fun(t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11)
function f=Optimfun4(t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,t14,t15,t16)
%%
%数据读取
[data_left_num,~,~]=xlsread('data0526.xlsx',2,'A1:L158');
% arrive_status=2;%注：所读取的数据表中，采样点取到前面几个状态为2和5的点
% leave_status=4;
% %先计算该表中有多少辆车
% col_status=7;%记录当前状态，用该列判断车辆的到达与离开
% data_status=data_left_num(:,col_status);%读取状态列数据,所有行的第col_status列
% data_length=length(data_status);%数据总行数
% arrive_mark=0;%检测到车辆到达，即遇到状态3时，arrive_mark置1；检测到车辆离开，即遇到状态4时，arrive_mark置0
% vehicle_num=0;%车辆数，检测到离开状态4，就+1
% for i=1:data_length
%     if data_status(i,1)==arrive_status && arrive_mark==0
%         arrive_mark=1;
%         continue;%往下走，跳出本if
%     end
%     if data_status(i,1)==leave_status && arrive_mark==1
%         arrive_mark=0;%还原mark
%         vehicle_num=vehicle_num+1;
%     end
% end
% %%提取车辆到达与离开的行号
% aorder_num_arrive_leave=zeros(vehicle_num,2);%存储每辆车的到达行与离开行
% amoment_arrive=cell(vehicle_num,1);%存储每辆车的到达时间
% order_count=1;
% arrive_mark=0;
% 
% for i=1:data_length
%     if data_status(i,1)==arrive_status && arrive_mark==0
%         arrive_mark=1;
%         %arrive_point=i;
%         aorder_num_arrive_leave(order_count,1)=i;
%         amoment_arrive(order_count,1)=data_left(i,11);
%         continue;
%     end
%     if data_status(i,1)==leave_status && arrive_mark==1%&& isequal(data_left(i,col_infomation),cell_leave) 
%         arrive_mark=0;
%         %leave_point=i;
%         aorder_num_arrive_leave(order_count,2)=i;
%         order_count=order_count+1;
%     end
% end
%%
%考虑两个磁偶极子,且从三轴角度分别求解并对比
% aorder_num_arrive_leave=[2,76;78,187];%框式货车
aorder_num_arrive_leave=[2,65;67,158];%商务客车
i=1;
arrive_point=aorder_num_arrive_leave(i,1);%读取到达的行序号
leave_point=aorder_num_arrive_leave(i,2);%读取离开的行序号
data_x=smooth(data_left_num(arrive_point:leave_point,4));%只对车辆数据进行平滑滤波,N=10
data_y=smooth(data_left_num(arrive_point:leave_point,5));%由于滤波的原因，车辆数据长度会减少（N-1）个,数据转变成行向量
data_z=smooth(data_left_num(arrive_point:leave_point,6));
data_x=data_x';data_y=data_y';data_z=data_z';

% theta=[t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11];
theta=[t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,t14,t15,t16];
data=[data_x(:,1),data_y(:,1),data_z(:,1)];
L=length(data_x);
v=data_left_num(arrive_point-1,8)/3.6;%从数据表中获取速度
u=4*pi*10^(-7);%H/m
w=u*10^9/4/pi/13;
T=0.01;%采样周期 0.01s

%定义车辆初始值（磁偶极子的磁矩和初始位置、车辆速度）,可以进行初始化然后进行迭代修改
%需要迭代计算的值：mx1 my1 mz1  mx2 my2 mz2  z0 dx dy dz 
m=[theta(1:3);theta(4:6);theta(7:9);theta(10:12)];%给定初始值 单位是Am² 需要迭代计算的值
[n,~]=size(m);
x0=-v*T*L/2;y0=-1.6;z0=theta(16);%给定的y0从视频中观察得到
dx1=theta(13);dx2=theta(14);dx3=theta(15);
k=1:1:L;
x1=x0+v*k*T;%第一个磁偶极子的x，其他磁偶极子的可由这个表示出来

r1=sqrt(x1.^2+y0^2+z0^2);
r2=sqrt((x1+dx1).^2+y0.^2+z0.^2);
r3=sqrt((x1+dx2).^2+y0.^2+z0.^2);
r4=sqrt((x1+dx3).^2+y0.^2+z0.^2);
r_r=[r1;r2;r3;r4];
r_x=[x1;x1+dx1;x1+dx2;x1+dx3];
r_y=y0*ones(1,n);
r_z=z0*ones(1,n);
%预测值的计算
Bxpre=0;Bypre=0;Bzpre=0;
for i=1:n
    x=r_x(i,:);y=r_y(1,i);z=r_z(1,i);r=r_r(i,:);
    Bx=w*((3*x.^2-r.^2)*m(i,1)+3*x*y*m(i,2)+3*x*z*m(i,3))./r.^5;
    By=w*(3*x*y*m(i,1)+(3*y^2-r.^2)*m(i,2)+3*y*z*m(i,3))./r.^5;
    Bz=w*(3*x*z*m(i,1)+3*y*z*m(i,2)+(3*z^2-r.^2)*m(i,3))./r.^5;
    Bxpre=Bxpre+Bx';
    Bypre=Bypre+By';
    Bzpre=Bzpre+Bz';
end

%误差
res=(data(:,1)-Bxpre).^2+(data(:,2)-Bypre).^2+(data(:,3)-Bzpre).^2;
f=sum(res.^0.5)/L;
end