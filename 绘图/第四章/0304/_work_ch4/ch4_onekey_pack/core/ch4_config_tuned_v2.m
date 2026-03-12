function [cfg, post] = ch4_config_tuned_v2(scenario_group)
%CH4_CONFIG_TUNED_V2  Tuned parameter sets (v2).
%   [cfg, post] = ch4_config_tuned_v2("A"|"B"|"C"|"D"|"GLOBAL")
%   Unknown group uses GLOBAL fallback.

cfg = ch4_config();

if nargin < 1 || scenario_group == ""
    scenario_group = "GLOBAL";
end
scenario_group = string(scenario_group);

switch scenario_group
    case "A"
        cfg.fs = 50;
        cfg.ev.theta_arrive = 0.9;
        cfg.ev.theta_leave  = 0.3;
        cfg.ev.arriveLen = 8;
        cfg.ev.arriveWin = 6;
        cfg.ev.leaveLen  = 5;
        cfg.ev.leaveWin  = 6;
        cfg.ev.Td = 4;
        cfg.pr.P_vehicle = 0.25;
        cfg.pr.muX = 0;
        cfg.pr.muY = 0;
        cfg.pr.muZ = 0;
        cfg.pr.sigmaX = 1.5716;
        cfg.pr.sigmaY = 1.8608;
        cfg.pr.sigmaZ = 0.8196;
        cfg.pr.ema_alpha = 0.1;
        cfg.pr.fir_order = 11;
        cfg.pr.fir_beta = 0.5;
        cfg.pr.fir_fc_xy = 5;
        cfg.pr.fir_fc_z = 6;
        cfg.pr.use_legacy_fir = false;
        cfg.pr.use_legacy_smooth = false;
        cfg.st.L = 25;
        cfg.st.s = 25;
        cfg.st.N_stable = 4;
        cfg.st.R_th = 2.09646286934612;
        cfg.st.M_th = 11.5205848812515;
        cfg.pk.T_seek_sec = 2.63771209670334;
        cfg.pk.D_th = 24.2212649975444;
        cfg.pk.D_free = 18.2911814135066;
        cfg.pk.dist_th = 8.41923495743084;
        cfg.pk.lambda_occ = 0.159161327481618;
        cfg.dg.enable = true;
        cfg.dg.L_fix = 50;
        cfg.dg.c_th  = 1;
        cfg.ref.enable = true;
        cfg.ref.alpha_free = 0.0536588290750576;
        cfg.ref.D_upd = 68.8028657490795;
        cfg.v.use_mean_diff = true;
        cfg.v.use_similarity = true;
        cfg.v.use_degrade = true;
        cfg.v.use_update_gate = true;
        cfg.pk.Tmin_sec = 5;

    case "B"
        cfg.fs = 50;
        cfg.ev.theta_arrive = 0.9;
        cfg.ev.theta_leave  = 0.3;
        cfg.ev.arriveLen = 8;
        cfg.ev.arriveWin = 6;
        cfg.ev.leaveLen  = 5;
        cfg.ev.leaveWin  = 6;
        cfg.ev.Td = 4;
        cfg.pr.P_vehicle = 0.25;
        cfg.pr.muX = 0;
        cfg.pr.muY = 0;
        cfg.pr.muZ = 0;
        cfg.pr.sigmaX = 1.5716;
        cfg.pr.sigmaY = 1.8608;
        cfg.pr.sigmaZ = 0.8196;
        cfg.pr.ema_alpha = 0.1;
        cfg.pr.fir_order = 11;
        cfg.pr.fir_beta = 0.5;
        cfg.pr.fir_fc_xy = 5;
        cfg.pr.fir_fc_z = 6;
        cfg.pr.use_legacy_fir = false;
        cfg.pr.use_legacy_smooth = false;
        cfg.st.L = 25;
        cfg.st.s = 25;
        cfg.st.N_stable = 3;
        cfg.st.R_th = 10.5336594928956;
        cfg.st.M_th = 3.33790652154534;
        cfg.pk.T_seek_sec = 2.74240984467191;
        cfg.pk.D_th = 18.6932099478109;
        cfg.pk.D_free = 25.2423674246356;
        cfg.pk.dist_th = 13.8099411645666;
        cfg.pk.lambda_occ = 0.121310059530146;
        cfg.dg.enable = true;
        cfg.dg.L_fix = 50;
        cfg.dg.c_th  = 2;
        cfg.ref.enable = true;
        cfg.ref.alpha_free = 0.0736454631320762;
        cfg.ref.D_upd = 240.200541838379;
        cfg.v.use_mean_diff = true;
        cfg.v.use_similarity = true;
        cfg.v.use_degrade = true;
        cfg.v.use_update_gate = true;
        cfg.pk.Tmin_sec = 20;

    case "C"
        cfg.fs = 50;
        cfg.ev.theta_arrive = 0.9;
        cfg.ev.theta_leave  = 0.3;
        cfg.ev.arriveLen = 8;
        cfg.ev.arriveWin = 6;
        cfg.ev.leaveLen  = 5;
        cfg.ev.leaveWin  = 6;
        cfg.ev.Td = 4;
        cfg.pr.P_vehicle = 0.25;
        cfg.pr.muX = 0;
        cfg.pr.muY = 0;
        cfg.pr.muZ = 0;
        cfg.pr.sigmaX = 1.5716;
        cfg.pr.sigmaY = 1.8608;
        cfg.pr.sigmaZ = 0.8196;
        cfg.pr.ema_alpha = 0.1;
        cfg.pr.fir_order = 11;
        cfg.pr.fir_beta = 0.5;
        cfg.pr.fir_fc_xy = 5;
        cfg.pr.fir_fc_z = 6;
        cfg.pr.use_legacy_fir = false;
        cfg.pr.use_legacy_smooth = false;
        cfg.st.L = 25;
        cfg.st.s = 25;
        cfg.st.N_stable = 3;
        cfg.st.R_th = 2.49131184396187;
        cfg.st.M_th = 7.16172575769657;
        cfg.pk.T_seek_sec = 2.69745742394637;
        cfg.pk.D_th = 22.1272735033529;
        cfg.pk.D_free = 11.6804753709003;
        cfg.pk.dist_th = 18.665956068495;
        cfg.pk.lambda_occ = 0.125534337084302;
        cfg.dg.enable = true;
        cfg.dg.L_fix = 100;
        cfg.dg.c_th  = 2;
        cfg.ref.enable = true;
        cfg.ref.alpha_free = 0.198217754943599;
        cfg.ref.D_upd = 94.1657881805025;
        cfg.v.use_mean_diff = true;
        cfg.v.use_similarity = true;
        cfg.v.use_degrade = true;
        cfg.v.use_update_gate = true;
        cfg.pk.Tmin_sec = 20;

    case "D"
        cfg.fs = 50;
        cfg.ev.theta_arrive = 0.9;
        cfg.ev.theta_leave  = 0.3;
        cfg.ev.arriveLen = 8;
        cfg.ev.arriveWin = 6;
        cfg.ev.leaveLen  = 5;
        cfg.ev.leaveWin  = 6;
        cfg.ev.Td = 4;
        cfg.pr.P_vehicle = 0.25;
        cfg.pr.muX = 0;
        cfg.pr.muY = 0;
        cfg.pr.muZ = 0;
        cfg.pr.sigmaX = 1.5716;
        cfg.pr.sigmaY = 1.8608;
        cfg.pr.sigmaZ = 0.8196;
        cfg.pr.ema_alpha = 0.1;
        cfg.pr.fir_order = 11;
        cfg.pr.fir_beta = 0.5;
        cfg.pr.fir_fc_xy = 5;
        cfg.pr.fir_fc_z = 6;
        cfg.pr.use_legacy_fir = false;
        cfg.pr.use_legacy_smooth = false;
        cfg.st.L = 25;
        cfg.st.s = 25;
        cfg.st.N_stable = 4;
        cfg.st.R_th = 5.05246711922956;
        cfg.st.M_th = 2.81116568559298;
        cfg.pk.T_seek_sec = 2.48533355928558;
        cfg.pk.D_th = 20.3186174093772;
        cfg.pk.D_free = 21.0191604632368;
        cfg.pk.dist_th = 15.1292673490806;
        cfg.pk.lambda_occ = 0.288644706048997;
        cfg.dg.enable = true;
        cfg.dg.L_fix = 75;
        cfg.dg.c_th  = 3;
        cfg.ref.enable = true;
        cfg.ref.alpha_free = 0.0914952055190651;
        cfg.ref.D_upd = 129.625766833171;
        cfg.v.use_mean_diff = true;
        cfg.v.use_similarity = true;
        cfg.v.use_degrade = true;
        cfg.v.use_update_gate = true;
        cfg.pk.Tmin_sec = 5;

    otherwise  % GLOBAL fallback
        cfg.fs = 50;
        cfg.ev.theta_arrive = 0.88;
        cfg.ev.theta_leave  = 0.25;
        cfg.ev.arriveLen = 6;
        cfg.ev.arriveWin = 4;
        cfg.ev.leaveLen  = 5;
        cfg.ev.leaveWin  = 6;
        cfg.ev.Td = 4;
        cfg.pr.P_vehicle = 0.25;
        cfg.pr.muX = 0;
        cfg.pr.muY = 0;
        cfg.pr.muZ = 0;
        cfg.pr.sigmaX = 1.5716;
        cfg.pr.sigmaY = 1.8608;
        cfg.pr.sigmaZ = 0.8196;
        cfg.pr.ema_alpha = 0.1;
        cfg.pr.fir_order = 11;
        cfg.pr.fir_beta = 0.5;
        cfg.pr.fir_fc_xy = 5;
        cfg.pr.fir_fc_z = 6;
        cfg.pr.use_legacy_fir = false;
        cfg.pr.use_legacy_smooth = false;
        cfg.st.L = 25;
        cfg.st.s = 25;
        cfg.st.N_stable = 5;
        cfg.st.R_th = 5.43595814555724;
        cfg.st.M_th = 3.50467962447916;
        cfg.pk.T_seek_sec = 2.130189771;
        cfg.pk.D_th = 19.520168822607;
        cfg.pk.D_free = 27.1166224036963;
        cfg.pk.dist_th = 20.1886907302364;
        cfg.pk.lambda_occ = 0.224628215628187;
        cfg.dg.enable = true;
        cfg.dg.L_fix = 75;
        cfg.dg.c_th  = 3;
        cfg.ref.enable = true;
        cfg.ref.alpha_free = 0.162018584491401;
        cfg.ref.D_upd = 383.829166434513;
        cfg.v.use_mean_diff = true;
        cfg.v.use_similarity = true;
        cfg.v.use_degrade = true;
        cfg.v.use_update_gate = true;
        if scenario_group == "B" || scenario_group == "C"
            cfg.pk.Tmin_sec = 18;
        else
            cfg.pk.Tmin_sec = 5;
        end
end

% Ensure legacy filters disabled (recommended for 50 Hz data)
cfg.pr.use_legacy_fir = false;
cfg.pr.use_legacy_smooth = false;

% Postprocess parameters (interval-level)
% Tmin_sec: remove predicted intervals shorter than this
% gap_merge_sec: merge adjacent intervals if gap <= gap_merge_sec
post = struct();
post.Tmin_sec = cfg.pk.Tmin_sec;
post.gap_merge_sec = 0; % default, can be overridden in run scripts

end