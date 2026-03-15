function [score] = cost_function_with_y0(population,data_raw)
%cost_function计算真实数据与模拟数据之间的差距res
%   输入population与需要仿真的数据 data_choose
%   输出计算的分数score，也就是差距
%%
%考虑两个磁偶极子,且从三轴角度分别求解并对比
arrive_point=2;
leave_point=length(data_raw(:,1));
data_x=smooth(data_raw(arrive_point:leave_point,4));%只对车辆数据进行平滑滤波,N=10
data_y=smooth(data_raw(arrive_point:leave_point,5));%由于滤波的原因，车辆数据长度会减少（N-1）个,数据转变成行向量
data_z=smooth(data_raw(arrive_point:leave_point,6));
data_x=data_x';data_y=data_y';data_z=data_z';

theta=population;
y_begin=theta(length(theta));
data=[data_x(:,1),data_y(:,1),data_z(:,1)];
L=length(data_x);
v=data_raw(arrive_point-1,8)/3.6;%从数据表中获取速度
u=4*pi*10^(-7);%H/m
w=u*10^9/4/pi/13;
T=0.02;%采样周期 0.01s

%定义车辆初始值（磁偶极子的磁矩和初始位置、车辆速度）,可以进行初始化然后进行迭代修改
%需要迭代计算的值：mx1 my1 mz1  mx2 my2 mz2  z0 dx dy dz 
magDipNum = (length(theta)+1)/6;
m=[];
for i_temp=1:magDipNum
    m=[m;theta((i_temp-1)*3+1:(i_temp-1)*3+3)];
end
%给定初始值 单位是Am² 需要迭代计算的值
[n,~]=size(m);

x10=-v*T*L/2;
y0=y_begin; %这里可能需要修改，原来是-1.8，这里应该和java代码里设置的初始值一样
z0=theta(magDipNum*3+1);%给定的y0从视频中观察得到
dx=zeros(magDipNum-1);dy=zeros(magDipNum-1);dz=zeros(magDipNum-1);
for i_temp=1:magDipNum-1
    dx(i_temp)=theta(magDipNum*3+1 + (i_temp-1)*3 +1);
    dy(i_temp)=theta(magDipNum*3+1 + (i_temp-1)*3 +2);
    dz(i_temp)=theta(magDipNum*3+1 + (i_temp-1)*3 +3);
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
score=sum(res.^0.5)/L;
% res=max([sum((data(:,1)-Bxpre).^2),sum((data(:,2)-Bypre).^2),sum((data(:,3)-Bzpre).^2)]);
% score=res/L;

end