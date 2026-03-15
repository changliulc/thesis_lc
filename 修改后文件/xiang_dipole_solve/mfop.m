function f=mfop(m)
% data1_pre = xlsread('大中小模型',1,'A1:M88');%%%1车道
data1_pre = xlsread('D:\a研究资料\车型分类工作记录\0505-0507工作\ori_data(speed).xlsx',1,'A520:L605');%%%1车道

data1x1 = data1_pre(:,4)';
data1y1 = data1_pre(:,5)'; 
data1z1 = data1_pre(:,6)';
%离差标准化
data1x1=(data1x1-min(data1x1))/(max(data1x1)-min(data1x1));
data1y1=(data1y1-min(data1y1))/(max(data1y1)-min(data1y1));
data1z1=(data1z1-min(data1z1))/(max(data1z1)-min(data1z1));
[a,n]=size(data1x1);
u0=4*pi*10^(-7);
x0=-5;y0=0.9;z0=-0.6;%箱式货车
k1=1.7;k2=0.83;k3=-0.44;k4=-1.7;%箱式货车
%k1=1.7;k2=-1.7;%箱式货车
% x0=-5;y0=0.6;z0=-0.4;%轿车
% k1=2.023;k2=1.2;k3=0.377;k4=-1.2;%轿车
% x0=-5;y0=0.8;z0=-0.5;%平板载货车
% k1=1.925;k2=0.605;k3=-0.92;k4=-1.525;%平板载货车
t=0:0.005:0.7;
v=14;%单位m/s
x=x0+v*t;%10m/s=36km/h
r1=sqrt((x+k1).^2+y0^2+z0^2);
r2=sqrt((x+k2).^2+y0^2+z0^2);
r3=sqrt((x+k3).^2+y0^2+z0^2);
r4=sqrt((x+k4).^2+y0^2+z0^2);
r=[r1;r2;r3;r4];
x=[x+k1;x+k2;x+k3;x+k4];
% r=[r1;r2];
% x=[x+k1;x+k2];
[l,g]=size(r);
B_x=0;B_y=0;B_z=0;
for i=1:l
Bx=10.^9*((3*x(i,:).^2-r(i,:).^2)*m(i,1)+3*x(i,:).*y0*m(i,2)+3*x(i,:).*z0*m(i,3))*u0./(4*pi*r(i,:).^5)/13;
By=10.^9*(3*x(i,:)*y0*m(i,1)+(3*y0^2-r(i,:).^2)*m(i,2)+3*y0*z0*m(i,3))*u0./(4*pi*r(i,:).^5)/13;
Bz=10.^9*(3*x(i,:)*z0*m(i,1)+3*y0*z0*m(i,2)+(3*z0^2-r(i,:).^2)*m(i,3))*u0./(4*pi*r(i,:).^5)/13;
B_x=B_x+Bx;
B_y=B_y+By;
B_z=B_z+Bz;
end
[b,k]=size(B_x);
B_x=resample(B_x,n,k);
B_y=resample(B_y,n,k);
B_z=resample(B_z,n,k);
f=(B_x-data1x1).^2+(B_y-data1y1).^2+(B_z-data1z1).^2;
f=sum(f.^0.5)/n;
end