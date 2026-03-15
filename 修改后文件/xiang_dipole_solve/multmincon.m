clear;
close all;
clc;
data1_pre = xlsread('D:\a研究资料\车型分类工作记录\0505-0507工作\ori_data(speed).xlsx',1,'A520:L605');%%%1车道
data1x1 = data1_pre(:,4)';
data1y1 = data1_pre(:,5)'; 
data1z1 = data1_pre(:,6)';

[a,n]=size(data1x1);
u0=4*pi*10^(-7);
% x0=-5;y0=0.6;z0=-2;       
% t=0:0.005:0.7;    
% v=14;%单位m/s
% x=x0+v*t;%10m/s=36km/h
% r=sqrt(x.^2+y0^2+z0^2);
% a1=10.^9*(3*x.^2-r.^2)*u0./(4*pi*r.^5);a2=10.^9*3*x.*y0*u0./(4*pi*r.^5);a3=10.^9*3*x.*z0*u0./(4*pi*r.^5);
% b1=10.^9*3*x*y0*u0./(4*pi*r.^5);b2=10.^9*3*y0*z0*u0./(4*pi*r.^5);b3=10.^9*3*y0*z0*u0./(4*pi*r.^5);
% c1=10.^9*3*x*z0*u0./(4*pi*r.^5);c2=10.^9*3*x*z0*u0./(4*pi*r.^5);c3=10.^9*(3*z0^2-r.^2)*u0./(4*pi*r.^5);
% A=[a1(ceil(n/2)),a2(ceil(n/2)),a3(ceil(n/2));b1(ceil(n/2)),b2(ceil(n/2)),b3(ceil(n/2));c1(ceil(n/2)),c2(ceil(n/2)),c3(ceil(n/2))];
% B=[max(data1x1);max(data1y1);max(data1z1)];
m0=[0.5,0.5,0.5;0.5,0.5,0.5;0.5,0.5,0.5;0.5,0.5,0.5];
%m0=[0.5,0.5,0.5;0.5,0.5,0.5];

option=optimset; option.LargeScale='off';option.Display='off';
 
[m,f]=fmincon('mfop',m0,[],[],[],[],[],[],[],option);

data1x1=(data1x1-min(data1x1))/(max(data1x1)-min(data1x1));
data1y1=(data1y1-min(data1y1))/(max(data1y1)-min(data1y1));
data1z1=(data1z1-min(data1z1))/(max(data1z1)-min(data1z1));
data1 = sqrt(data1x1.^2+data1y1.^2+data1z1.^2);

[a,n]=size(data1x1);
x0=-5;y0=0.9;z0=-0.6;%箱式货车
k1=1.7;k2=0.83;k3=-0.44;k4=-1.7;%箱式货车
% x0=-5;y0=0.6;z0=-0.4;%轿车
% k1=2.023;k2=1.2;k3=0.377;k4=-1.2;%轿车
% x0=-5;y0=0.8;z0=-0.5;%平板载货车
% k1=1.925;k2=0.605;k3=-0.92;k4=-1.525;%平板载货车
t=0:0.005:0.7;
v=14;%单位m/s
x=x0+v*t;%10m/s=36km/h
% m=xlsread('大中小模型',8,'A1:C100');
% [r,t]=size(m);
% r=r/5;
u0=4*pi*10^(-7);
%x0=-5;y0=0.9;z0=-0.6;%箱式货车
%k1=1.7;k2=-1.7;%箱式货车
m_x=m(:,1);
m_y=m(:,2);
m_z=m(:,3);%箱式货车，4
r1=sqrt((x+k1).^2+y0^2+z0^2);
r2=sqrt((x+k2).^2+y0^2+z0^2);
r3=sqrt((x+k3).^2+y0^2+z0^2);
r4=sqrt((x+k4).^2+y0^2+z0^2);
r=[r1;r2;r3;r4];
x=[x+k1;x+k2;x+k3;x+k4];
% r=[r1;r2];
% x=[x+k1;x+k2];
B_x4=0;B_y4=0;B_z4=0;
[l,g]=size(r);
i=1;
for i=1:l
Bx4=10.^9.*((3.*x(i,:).^2-r(i,:).^2).*m_x(i,:)+3.*x(i,:).*y0.*m_y(i,:)+3.*x(i,:).*z0.*m_z(i,:)).*u0./(4*pi.*r(i,:).^5);
By4=10.^9.*(3.*x(i,:).*y0.*m_x(i,:)+(3.*y0^2-r(i,:).^2).*m_y(i,:)+3.*y0.*z0.*m_z(i,:)).*u0./(4*pi.*r(i,:).^5);
Bz4=10.^9.*(3.*x(i,:).*z0.*m_x(i,:)+3.*y0.*z0.*m_y(i,:)+(3.*z0^2-r(i,:).^2).*m_z(i,:)).*u0./(4*pi.*r(i,:).^5);
B_x4=B_x4+Bx4;
B_y4=B_y4+By4;
B_z4=B_z4+Bz4;
end
[b,k]=size(B_x4);
B_x4=resample(B_x4,n,k);
B_y4=resample(B_y4,n,k);
B_z4=resample(B_z4,n,k);
B_x4=(B_x4-min(B_x4))/(max(B_x4)-min(B_x4));
B_y4=(B_y4-min(B_y4))/(max(B_y4)-min(B_y4));
B_z4=(B_z4-min(B_z4))/(max(B_z4)-min(B_z4));
B_R4=sqrt(B_x4.^2+B_y4.^2+B_z4.^2);
%figure('Name','三轴原始波形及融合后波形');%原始波形
    subplot(4,1,1);
    plot(B_x4);%X
    hold on;
  
    %subplot(4,1,1);
    plot(data1x1);%X轴
    ylabel('X轴磁场强度','FontSize',15);
    hold on;
%figure('Name','三轴原始波形及融合后波形');%原始波形
   subplot(4,1,2);
    plot(B_y4);%Y轴
    hold on;
    
   % subplot(4,1,2);
    plot(data1y1);%Y轴
    ylabel('Y轴磁场强度','FontSize',15);
    hold on;
%figure('Name','三轴原始波形及融合后波形');%原始波形
   subplot(4,1,3);
    plot(B_z4);%Z轴
    hold on;
    
    %subplot(4,1,3);
    plot(data1z1);%Y轴
    ylabel('Z轴磁场强度','FontSize',15);
    hold on;
%figure('Name','三轴原始波形及融合后波形');%原始波形
    subplot(4,1,4);
    plot(B_R4);%融合后波形
    hold on;
    
   % subplot(4,1,4);
    plot(data1);%融合后波形
    ylabel('融合磁场强度','FontSize',15);
    %xlabel('采样点数','FontSize',15);
    hold on;