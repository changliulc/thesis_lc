% function pr = ch4_pr_vehicle(B, cfg)
% %CH4_PR_VEHICLE Probability of vehicle presence based on filtered diff
% % Priority:
% %   FIR:   legacy FIRN11Fc5Beta05 / FIRN11Fc6Beta05 (dfilt) if enabled,
% %          fallback to fir1+kaiser designed with cfg.fs
% %   Smooth: legacy smooth.m if enabled, fallback to EMA
% %
% % Output:
% %   pr: n×1 vehicle presence probability
% 
% n = size(B,1);
% x = B(:,1); y = B(:,2); z = B(:,3);
% 
% dx = [0; diff(x)];
% dy = [0; diff(y)];
% dz = [0; diff(z)];
% 
% useLegacyFir = isfield(cfg, "pr") && isfield(cfg.pr, "use_legacy_fir") && cfg.pr.use_legacy_fir;
% useLegacySmooth = isfield(cfg, "pr") && isfield(cfg.pr, "use_legacy_smooth") && cfg.pr.use_legacy_smooth;
% 
% % ===== 1) FIR lowpass =====
% dx_lp = ch4_lowpass_any(dx, cfg, useLegacyFir, "FIRN11Fc5Beta05", cfg.pr.fir_fc_xy);
% dy_lp = ch4_lowpass_any(dy, cfg, useLegacyFir, "FIRN11Fc5Beta05", cfg.pr.fir_fc_xy);
% dz_lp = ch4_lowpass_any(dz, cfg, useLegacyFir, "FIRN11Fc6Beta05", cfg.pr.fir_fc_z);
% 
% % ===== 2) Smooth =====
% dx_f = ch4_smooth_any(dx_lp, cfg.pr.ema_alpha, useLegacySmooth);
% dy_f = ch4_smooth_any(dy_lp, cfg.pr.ema_alpha, useLegacySmooth);
% dz_f = ch4_smooth_any(dz_lp, cfg.pr.ema_alpha, useLegacySmooth);
% 
% % ===== 3) Merge to pr_vehicle =====
% pr = zeros(n,1);
% for i = 1:n
%     pr(i) = PgetMerge(dx_f(i), dy_f(i), dz_f(i), ...
%         cfg.pr.muX, cfg.pr.sigmaX, cfg.pr.muY, cfg.pr.sigmaY, cfg.pr.muZ, cfg.pr.sigmaZ, cfg.pr.P_vehicle);
% end
% 
% end
% 
% % ======================================================================
% % Helpers
% % ======================================================================
% 
% function y = ch4_lowpass_any(x, cfg, useLegacyFir, legacyName, FcFallback)
% x = x(:);
% 
% % 兼容：legacyName 可能是 string，也可能是 char
% if isstring(legacyName)
%     legacyNameChar = char(legacyName);
% else
%     legacyNameChar = legacyName;
% end
% 
% % 关键修复点：exist 的第一个输入必须是 char 或 string 标量
% % 这里直接用函数名查找即可，不要拼 ".m"
% if useLegacyFir && exist(legacyNameChar, "file") == 2
%     % 1) dfilt 风格：Hd = FIRN...(); y = filter(Hd, x)
%     try
%         Hd = feval(legacyNameChar);
%         y = ch4_apply_filter_object(Hd, x);
%         y = y(:);
%         if numel(y) == numel(x)
%             return;
%         end
%     catch
%         % fallback below
%     end
% 
%     % 2) 直接对信号滤波风格：y = FIRN...(x)
%     try
%         y = feval(legacyNameChar, x);
%         y = y(:);
%         if numel(y) == numel(x)
%             return;
%         end
%     catch
%         % fallback below
%     end
% end
% 
% % Fallback: fir1 + kaiser, designed at cfg.fs with cutoff FcFallback (Hz)
% y = ch4_fir_lowpass_fallback(x, FcFallback, cfg.fs, cfg.pr.fir_order, cfg.pr.fir_beta);
% end
% 
% function y = ch4_apply_filter_object(Hd, x)
% if isnumeric(Hd)
%     y = filter(Hd, 1, x);
%     return;
% end
% 
% % dfilt 对象支持 filter(Hd, x)
% try
%     y = filter(Hd, x);
%     return;
% catch
% end
% 
% % Try extracting Numerator
% try
%     if isprop(Hd, "Numerator")
%         b = Hd.Numerator;
%         y = filter(b, 1, x);
%         return;
%     end
% catch
% end
% 
% error("Legacy filter object cannot be applied.");
% end
% 
% function y = ch4_smooth_any(x, alpha, tryLegacy)
% x = x(:);
% n = numel(x);
% 
% % 这里的 exist 写法是安全的（string 标量），也可以改成 'smooth.m'
% if tryLegacy && exist("smooth.m","file")==2
%     try
%         y0 = feval("smooth", x);  % your smooth.m
%         y0 = y0(:);
% 
%         % your smooth returns length n-N+1, pad to n
%         if isempty(y0)
%             % do nothing
%         elseif numel(y0) < n
%             y = [y0; repmat(y0(end), n - numel(y0), 1)];
%             return;
%         elseif numel(y0) > n
%             y = y0(1:n);
%             return;
%         else
%             y = y0;
%             return;
%         end
%     catch
%         % fallback below
%     end
% end
% 
% y = ch4_ema_fallback(x, alpha);
% end
% 
% function y = ch4_ema_fallback(x, alpha)
% y = zeros(size(x));
% y(1) = x(1);
% for i = 2:numel(x)
%     y(i) = alpha * x(i) + (1 - alpha) * y(i-1);
% end
% end
% 
% function y = ch4_fir_lowpass_fallback(x, Fc, Fs, N, Beta)
% win = kaiser(N+1, Beta);
% b = fir1(N, Fc/(Fs/2), "low", win, "scale");
% y = filter(b, 1, x(:));
% end
function pr = ch4_pr_vehicle(B, cfg)
%CH4_PR_VEHICLE Probability of vehicle presence based on filtered diff
% Priority:
%   FIR:   legacy FIRN11Fc5Beta05 / FIRN11Fc6Beta05 (dfilt) if enabled,
%          fallback to fir1+kaiser designed with cfg.fs
%   Smooth: legacy smooth.m if enabled, fallback to EMA
%
% Output:
%   pr: n×1 vehicle presence probability

n = size(B,1);
x = B(:,1); y = B(:,2); z = B(:,3);

dx = [0; diff(x)];
dy = [0; diff(y)];
dz = [0; diff(z)];

useLegacyFir = isfield(cfg,'pr') && isfield(cfg.pr,'use_legacy_fir') && cfg.pr.use_legacy_fir;
useLegacySmooth = isfield(cfg,'pr') && isfield(cfg.pr,'use_legacy_smooth') && cfg.pr.use_legacy_smooth;

% ===== 1) FIR lowpass =====
dx_lp = ch4_lowpass_any(dx, cfg, useLegacyFir, 'FIRN11Fc5Beta05', cfg.pr.fir_fc_xy);
dy_lp = ch4_lowpass_any(dy, cfg, useLegacyFir, 'FIRN11Fc5Beta05', cfg.pr.fir_fc_xy);
dz_lp = ch4_lowpass_any(dz, cfg, useLegacyFir, 'FIRN11Fc6Beta05', cfg.pr.fir_fc_z);

% ===== 2) Smooth =====
dx_f = ch4_smooth_any(dx_lp, cfg.pr.ema_alpha, useLegacySmooth);
dy_f = ch4_smooth_any(dy_lp, cfg.pr.ema_alpha, useLegacySmooth);
dz_f = ch4_smooth_any(dz_lp, cfg.pr.ema_alpha, useLegacySmooth);

% ===== 3) Merge to pr_vehicle =====
pr = zeros(n,1);
for i = 1:n
    pr(i) = PgetMerge(dx_f(i), dy_f(i), dz_f(i), ...
        cfg.pr.muX, cfg.pr.sigmaX, cfg.pr.muY, cfg.pr.sigmaY, cfg.pr.muZ, cfg.pr.sigmaZ, cfg.pr.P_vehicle);
end

end

% ======================================================================
% Helpers
% ======================================================================

function y = ch4_lowpass_any(x, cfg, useLegacyFir, legacyName, FcFallback)
x = x(:);

% 关键修复：exist 的输入必须是 char 向量或 string 标量，这里统一用 char
if useLegacyFir && exist(legacyName, 'file') == 2

    % Try dfilt-based legacy function: Hd = FIRN...(); y = filter(Hd, x)
    try
        Hd = feval(legacyName);
        y = ch4_apply_filter_object(Hd, x);
        y = y(:);
        if numel(y) == numel(x)
            return;
        end
    catch
        % fallback below
    end

    % Try legacy function that directly accepts signal
    try
        y = feval(legacyName, x);
        y = y(:);
        if numel(y) == numel(x)
            return;
        end
    catch
        % fallback below
    end
end

% Fallback: fir1 + kaiser, designed at cfg.fs with cutoff FcFallback (Hz)
y = ch4_fir_lowpass_fallback(x, FcFallback, cfg.fs, cfg.pr.fir_order, cfg.pr.fir_beta);
end

function y = ch4_apply_filter_object(Hd, x)
% Apply dfilt or coefficient vector
if isnumeric(Hd)
    y = filter(Hd, 1, x);
    return;
end

% dfilt supports filter(Hd, x)
try
    y = filter(Hd, x);
    return;
catch
end

% Try extracting Numerator
try
    if isprop(Hd, 'Numerator')
        b = Hd.Numerator;
        y = filter(b, 1, x);
        return;
    end
catch
end

error('Legacy filter object cannot be applied.');
end

function y = ch4_smooth_any(x, alpha, tryLegacy)
x = x(:);
n = numel(x);

% 注意：你的 smooth.m 输出长度是 n-N+1，这里会自动补齐到 n
if tryLegacy && exist('smooth', 'file') == 2
    try
        y0 = smooth(x);
        y0 = y0(:);

        if isempty(y0)
            % fallback below
        elseif numel(y0) < n
            y = [y0; repmat(y0(end), n - numel(y0), 1)];
            return;
        elseif numel(y0) > n
            y = y0(1:n);
            return;
        else
            y = y0;
            return;
        end
    catch
        % fallback below
    end
end

% fallback EMA
y = ch4_ema_fallback(x, alpha);
end

function y = ch4_ema_fallback(x, alpha)
y = zeros(size(x));
y(1) = x(1);
for i = 2:numel(x)
    y(i) = alpha * x(i) + (1 - alpha) * y(i-1);
end
end

function y = ch4_fir_lowpass_fallback(x, Fc, Fs, N, Beta)
win = kaiser(N+1, Beta);
b = fir1(N, Fc/(Fs/2), 'low', win, 'scale');
y = filter(b, 1, x(:));
end
