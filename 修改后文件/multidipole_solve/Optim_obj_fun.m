%%
theta=[300,300,300,250,250,250,-1,1,0.1,0.1];
%参数值：mx1 my1 mz1  mx2 my2 mz2  z0 dx dy dz  1-3个参数是第一个磁偶极子的参数   4-6是第二个磁偶极子的参数  7是磁偶极子相对于地面的高度，即磁偶极子的Z坐标  8 - 10是两个磁偶极子在xyz三轴上的相对距离
%磁偶极子的X坐标随车辆移动而变化、Y轴坐标固定，基本是车道宽度的一半
L=100;%数据点数
v = 50;%速度 km/h
v=v/3.6;%获取速度 m/s
u=4*pi*10^(-7);%H/m 系数
w=u*10^9/4/pi/13; %系数
T=0.01;%采样周期 0.01s

 
m=[theta(1:3);theta(4:6);];
[n,~]=size(m);
x0=-v*T*L/2;y0=-1.8;z0=theta(7);%给定的y0从视频中观察得到
dx=theta(8);dy=theta(9);dz=theta(10);
k=1:1:L;
x1=x0+v*k*T;%第一个磁偶极子的x，其他磁偶极子的可由这个表示出来

r1=sqrt(x1.^2+y0^2+z0^2);
r2=sqrt((x1+dx).^2+(y0+dy).^2+(z0+dz).^2);
r_r=[r1;r2];
r_x=[x1;x1+dx];
r_y=[y0,y0+dy];
r_z=[z0,z0+dz];
%预测值的计算
Bxpre=0;Bypre=0;Bzpre=0;
for i=1:n
    x=r_x(i,:);y=r_y(1,i);z=r_z(1,i);r=r_r(i,:);
    Bx=w*((3*x.^2-r.^2)*m(i,1)+3*x*y*m(i,2)+3*x*z*m(i,3))./r.^5;
    By=w*(3*x*y*m(i,1)+(3*y^2-r.^2)*m(i,2)+3*y*z*m(i,3))./r.^5;
    Bz=w*(3*x*z*m(i,1)+3*y*z*m(i,2)+(3*z^2-r.^2)*m(i,3))./r.^5;
    Bxpre=Bxpre+Bx';%X轴的磁场值
    Bypre=Bypre+By';%Y轴的磁场值
    Bzpre=Bzpre+Bz';%Z轴的磁场值
end