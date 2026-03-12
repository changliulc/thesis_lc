function cfg = ch4_config()
%CH4_CONFIG  Chapter-4 parking/occupancy experiment config

cfg.fs = 50;  % Hz

% ===== Vehicle event detector (probability-based) =====
cfg.ev.theta_arrive = 0.90;
cfg.ev.theta_leave  = 0.30;
cfg.ev.arriveLen = 8;
cfg.ev.arriveWin = 6;
cfg.ev.leaveLen  = 5;
cfg.ev.leaveWin  = 6;
cfg.ev.Td = 4;

% ===== Probability model for pr_vehicle =====
cfg.pr.P_vehicle = 0.25;
cfg.pr.muX = 0; cfg.pr.muY = 0; cfg.pr.muZ = 0;
cfg.pr.sigmaX = 1.5716;
cfg.pr.sigmaY = 1.8608;
cfg.pr.sigmaZ = 0.8196;

cfg.pr.ema_alpha = 0.10;      % fallback smoothing
cfg.pr.fir_order = 11;
cfg.pr.fir_beta  = 0.5;
cfg.pr.fir_fc_xy = 5;         % Hz (fallback)
cfg.pr.fir_fc_z  = 6;         % Hz (fallback)

% ===== Use your legacy filters if available =====
% 注意：你上传的 FIRN11Fc5/Fc6 内部写的 Fs=100，若你希望严格按 50Hz 重新设计，
% 可将 use_legacy_fir=false，使用 fallback 的 fir1(按 cfg.fs=50 设计)。
cfg.pr.use_legacy_fir = true;
cfg.pr.use_legacy_smooth = true;

% ===== Stable window =====
cfg.st.L = 25;                  % 0.5 s
cfg.st.s = cfg.st.L;
cfg.st.N_stable = 3;
cfg.st.R_th = 4.5;
cfg.st.M_th = 5.5;

% ===== Parking / occupancy thresholds =====
cfg.pk.T_seek_sec = 2.0;
% cfg.pk.D_th   = 10.13;
cfg.pk.D_th    = 36.0;
cfg.pk.D_free = 16;

% cfg.pk.dist_th = 15;
cfg.pk.dist_th = 6;
cfg.pk.lambda_occ = 0.10;

% ===== Script-level postprocess (min duration) =====
cfg.pk.Tmin_sec = 0;   % seconds, set by tuned config / scripts

% ===== Degrade branch =====
cfg.dg.enable = true;
cfg.dg.L_fix = 50;              % 1 s
cfg.dg.c_th  = 5;

% ===== Reference update in FREE =====
cfg.ref.enable = true;
% cfg.ref.D_upd = 200;   
cfg.ref.D_upd  = 30.0;% 原来 20 太严/太小
cfg.ref.alpha_free = 0.10;  % 原来 0.05 更新太慢（可选但建议）

% ===== Variant switches (for baselines/ablations) =====
cfg.v.use_mean_diff = true;     % Abl-1: false
cfg.v.use_similarity = true;    % Abl-2: false
cfg.v.use_degrade = true;       % Abl-3: false
cfg.v.use_update_gate = true;   % Abl-4: false

end