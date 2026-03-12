function [cfg, post] = cfg_global_best()
%CFG_GLOBAL_BEST Global best configuration (new data, Tmin=4)
% This file only sets parameters; core functions remain unchanged.

cfg = ch4_config_tuned_v2("GLOBAL");

% ---- Global overrides (fixed best) ----
cfg.pk.D_th    = 36.0;
cfg.pk.dist_th = 4.5;
cfg.ref.D_upd  = 30.0;

% If you want to lock other parameters, set them here as well.

% ---- Postprocess (script-level) ----
post.Tmin_sec = 4.0;
post.gap_merge_sec = 0.0;
end




