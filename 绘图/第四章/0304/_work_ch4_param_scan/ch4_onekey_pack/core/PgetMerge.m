function [pr_vehicle_norm] = PgetMerge(numX, numY, numZ, muX, sigmaX, muY, sigmaY, muZ, sigmaZ, P_vehicle)
P_environment = 1 - P_vehicle;
%关于X轴
xValue_e1 = Pget(numX, muX, sigmaX);
xValue_e0 = 1 - xValue_e1;
%关于Y轴
yValue_e1 = Pget(numY, muY, sigmaY);
yValue_e0 = 1 - yValue_e1;

%关于Z轴
zValue_e1 = Pget(numZ, muZ, sigmaZ);
zValue_e0 = 1 - zValue_e1;

pr_environment = xValue_e0 * yValue_e0 * zValue_e0 / (P_environment * P_environment);
pr_vehicle = xValue_e1 * yValue_e1 * zValue_e1 / (P_vehicle * P_vehicle);
pr_vehicle_norm = pr_vehicle / (pr_environment + pr_vehicle);
end