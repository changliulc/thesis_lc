function [pr_vehicle_norm] = Pget(num, mu, sigma)
    pr_vehicle_norm = 1 - (1 - normcdf(abs(num), mu, sigma)) * 2;
end