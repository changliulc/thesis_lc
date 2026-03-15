clc;clear;
close all;
[data_left_num,~,data_left]=xlsread('data0526.xlsx',1,'A1:L187');

arrive_point=2;
leave_point=78;
data_x=smooth(data_left_num(arrive_point:leave_point,4));
data_y=smooth(data_left_num(arrive_point:leave_point,5));
data_z=smooth(data_left_num(arrive_point:leave_point,6));
data_x=data_x';data_y=data_y';data_z=data_z';
data=[data_x(:,1),data_y(:,1),data_z(:,1)];
L=length(data_x);
v=15;
u=4*pi*10^(-7);%H/m
w=u*10^9/4/pi/13;
T=0.01;%采样周期 0.01s

%%
%GS算法的结果
%-52.3590, 230.0560, 80.7581
%-34.6610, 160.0867, -240.7006
%-1.1356, 2.0768, -0.1637, -0.2793
% th=[141.27,50.03,-375.78,269.29,8.67,-96.06,-1.11,2,-0.2,0.3];
th=[-52.3590, 230.0560, 80.7581,-34.6610, 160.0867, -240.7006,-1.1356, 2.0768, -0.1637, -0.2793];

m=[th(1:3);th(4:6);];%给定初始值 单位是Am² 需要迭代计算的值
[n,c]=size(m);
x10=-v*T*L/2;y0=-1.8;z0=th(7);
dx=th(8);dy=th(9);dz=th(10);
k=1:1:L;
x1=x10+v*k*T;%第一个磁偶极子的x，其他磁偶极子的可由这个表示出来
r1=sqrt(x1.^2+y0^2+z0^2);
r2=sqrt((x1+dx).^2+(y0+dy).^2+(z0+dz).^2);
r_r=[r1;r2];
r_x=[x1;x1+dx];
r_y=[y0,y0+dy];
r_z=[z0,z0+dz];
%预测值的计算
GSBxpre=0;GSBypre=0;GSBzpre=0;
for i=1:n
    x=r_x(i,:);y=r_y(1,i);z=r_z(1,i);r=r_r(i,:);
    Bx=w*((3*x.^2-r.^2)*m(i,1)+3*x*y*m(i,2)+3*x*z*m(i,3))./r.^5;
    By=w*(3*x*y*m(i,1)+(3*y^2-r.^2)*m(i,2)+3*y*z*m(i,3))./r.^5;
    Bz=w*(3*x*z*m(i,1)+3*y*z*m(i,2)+(3*z^2-r.^2)*m(i,3))./r.^5;
    GSBxpre=GSBxpre+Bx';
    GSBypre=GSBypre+By';
    GSBzpre=GSBzpre+Bz';
end
%误差
resGS=(data(:,1)-GSBxpre).^2+(data(:,2)-GSBypre).^2+(data(:,3)-GSBzpre).^2;
resGS=sum(resGS.^0.5)/L/3;
plot(GSBzpre,'b','LineWidth',1.3);hold on;

%%
%DE算法的结果
th=[100,100,-100,100,100,-100,-1,2,-0.3,0.3];

m=[th(1:3);th(4:6);];%给定初始值 单位是Am² 需要迭代计算的值
[n,c]=size(m);
x10=-20;y0=-1.5;z0=th(7);
dx=th(8);dy=th(9);dz=th(10);
k=1:1:300;
x1=x10+v*k*T;%第一个磁偶极子的x，其他磁偶极子的可由这个表示出来
r1=sqrt(x1.^2+y0^2+z0^2);
r2=sqrt((x1+dx).^2+(y0+dy).^2+(z0+dz).^2);
r_r=[r1;r2];
r_x=[x1;x1+dx];
r_y=[y0,y0+dy];
r_z=[z0,z0+dz];
%预测值的计算
DEBxpre=0;DEBypre=0;DEBzpre=0;
for i=1:n
    x=r_x(i,:);y=r_y(1,i);z=r_z(1,i);r=r_r(i,:);
    Bx=w*((3*x.^2-r.^2)*m(i,1)+3*x*y*m(i,2)+3*x*z*m(i,3))./r.^5;
    By=w*(3*x*y*m(i,1)+(3*y^2-r.^2)*m(i,2)+3*y*z*m(i,3))./r.^5;
    Bz=w*(3*x*z*m(i,1)+3*y*z*m(i,2)+(3*z^2-r.^2)*m(i,3))./r.^5;
    DEBxpre=DEBxpre+Bx';
    DEBypre=DEBypre+By';
    DEBzpre=DEBzpre+Bz';
end
%误差
resDE=(data(:,1)-DEBxpre).^2+(data(:,2)-DEBypre).^2+(data(:,3)-DEBzpre).^2;
resDE=sum(resDE.^0.5)/L/3;
figure('Name','三轴波形')
plot(DEBxpre,'LineWidth',1);hold on;
plot(DEBzpre,'LineWidth',1);hold on;
plot(DEBypre,'LineWidth',1);hold on;

% %%
% %和真实结果比较
% plot(data(:,3),'k','LineWidth',1.3);hold on;
% legend('GS算法拟合波形','DE算法拟合波形','Z轴实际波形');
% ylabel('磁场强度','FontSize',15);
% xlabel('时间(单位：10ms)','FontSize',15);
% hold on;
% %%
% figure('Name','各参数迭代情况')
% subplot(1,1,1);
% [param,~,data_left]=xlsread('DE算法迭代结果.xlsx',1,'A3:K502');
% [m,n]=size(param);
% x=1:1:m;
% plot(x,param(:,1),'k','LineWidth',1.5);hold on;
% plot(x,param(:,2),'r','LineWidth',1.5);hold on;
% plot(x,param(:,3),'b','LineWidth',1.5);hold on;
% plot(x,param(:,4),'g','LineWidth',1.5);hold on;
% plot(x,param(:,5),'m','LineWidth',1.5);hold on;
% plot(x,param(:,6),'c','LineWidth',1.5);hold on;
% 
% ylabel('参数值','FontSize',15);
% xlabel('迭代次数','FontSize',15);
% hold on;
% figure('Name','各参数迭代情况')
% subplot(1,1,1);
% plot(x,param(:,7),'r','LineWidth',1.5);hold on;
% plot(x,param(:,8),'g','LineWidth',1.5);hold on;
% plot(x,param(:,9),'b','LineWidth',1.5);hold on;
% plot(x,param(:,10),'c','LineWidth',1.5);hold on;
% ylabel('参数值','FontSize',15);
% xlabel('迭代次数','FontSize',15);
% hold on;
% figure('Name','Score迭代情况')
% subplot(1,1,1);
% plot(x,param(:,11),'b','LineWidth',1.5);hold on;
% ylabel('平均误差','FontSize',15);
% xlabel('迭代次数','FontSize',15);
% hold on;

