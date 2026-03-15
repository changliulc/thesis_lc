function f=Optimfun1(t1,t2,t3,t4)
%%
%数据读取
[data_left_num,~,~]=xlsread('data0526.xlsx',3,'A1:L187');
%%
%考虑两个磁偶极子,且从三轴角度分别求解并对比
i=2;
aorder_num_arrive_leave=[2,76;78,187];
arrive_point=aorder_num_arrive_leave(i,1);%读取到达的行序号
leave_point=aorder_num_arrive_leave(i,2);%读取离开的行序号
data_x=smooth(data_left_num(arrive_point:leave_point,4));%只对车辆数据进行平滑滤波,N=10
data_y=smooth(data_left_num(arrive_point:leave_point,5));%由于滤波的原因，车辆数据长度会减少（N-1）个,数据转变成行向量
data_z=smooth(data_left_num(arrive_point:leave_point,6));
data_x=data_x';data_y=data_y';data_z=data_z';

% theta=[t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11];
theta=[t1,t2,t3,t4];
data=[data_x(:,1),data_y(:,1),data_z(:,1)];
L=length(data_x);
v=data_left_num(arrive_point-1,8)/3.6;%从数据表中获取速度
u=4*pi*10^(-7);%H/m
w=u*10^9/4/pi/13;
T=0.01;%采样周期 0.01s

%定义车辆初始值（磁偶极子的磁矩和初始位置、车辆速度）,可以进行初始化然后进行迭代修改
%需要迭代计算的值：mx1 my1 mz1  mx2 my2 mz2  z0 dx dy dz 
m=theta(1:3);%给定初始值 单位是Am² 需要迭代计算的值

x0=-v*T*L/2;y0=-1.8;z0=theta(4);%给定的y0从视频中观察得到
k=1:1:L;
x1=x0+v*k*T;%第一个磁偶极子的x，其他磁偶极子的可由这个表示出来

r1=sqrt(x1.^2+y0^2+z0^2);
r_r=r1;
r_x=x1;
r_y=y0;
r_z=z0;
%预测值的计算
Bxpre=0;Bypre=0;Bzpre=0;
    x=r_x;y=r_y;z=r_z;r=r_r;
    Bx=w*((3*x.^2-r.^2)*m(1)+3*x*y*m(2)+3*x*z*m(3))./r.^5;
    By=w*(3*x*y*m(1)+(3*y^2-r.^2)*m(2)+3*y*z*m(3))./r.^5;
    Bz=w*(3*x*z*m(1)+3*y*z*m(2)+(3*z^2-r.^2)*m(3))./r.^5;
    Bxpre=Bxpre+Bx';
    Bypre=Bypre+By';
    Bzpre=Bzpre+Bz';

%误差
res=(data(:,1)-Bxpre).^2+(data(:,2)-Bypre).^2+(data(:,3)-Bzpre).^2;
f=sum(res.^0.5)/L;
end