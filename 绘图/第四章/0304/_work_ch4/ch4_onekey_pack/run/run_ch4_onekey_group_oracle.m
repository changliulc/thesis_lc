%RUN_CH4_ONEKEY_GROUP_ORACLE
% 
% Oracle evaluation: use different parameter sets for A/B/C/D.
% This is useful as an upper bound analysis, but NOT recommended as the
% headline deployment result.
%
% Outputs (to out/):
%   - E1_per_file_oracle.csv
%   - E1_by_group_oracle.csv
%
% NOTE:
%   Replace the parameter blocks below with your final tuned values if needed.

clear; clc;

thisDir = fileparts(mfilename('fullpath'));
repoRoot = fileparts(thisDir);
addpath(genpath(repoRoot));

p = ch4_local_paths();

IOU_TH = 0.50;

GT = readtable(p.gt);
GT = ch4_append_synth_gt_all_events(GT, p.synth);

files = unique(GT.file, 'stable');

T_file = table('Size',[0 11], ...
    'VariableTypes',{'string','string','double','double','double','double','double','double','double','double','double'}, ...
    'VariableNames',{'file','group','TP','FP','FN','P','R','F1','events','pred','gt'});

for i = 1:numel(files)
    fileName = string(files(i));
    gt_f = GT(GT.file == fileName, :);
    group = string(gt_f.scenario_group(1));

    % ---- choose config by group ----
    [cfg, post] = ch4_config_tuned_v2(group);

    % ---- overwrite with your "best" per-group params (from your search logs) ----
    switch group
        case "A"
            cfg.pk.D_th        = 38.8685;
            cfg.pk.D_free      = 30.2050;
            cfg.pk.dist_th     = 19.6747;
            cfg.pk.lambda_occ  = 0.0880490;
            cfg.pk.T_seek_sec  = 4.26863;
            cfg.ref.alpha_free = 0.383171;
            cfg.ref.D_upd      = 455.299;
            cfg.dg.L_fix       = 150;
            cfg.dg.c_th        = 1;
            cfg.v.use_update_gate = false;
            post.Tmin_sec      = 6.88229;
            post.gap_merge_sec = 5.0;

        case "B"
            cfg.pk.D_th        = 166.322;
            cfg.pk.D_free      = 75.3887;
            cfg.pk.dist_th     = 17.7643;
            cfg.pk.lambda_occ  = 0.293800;
            cfg.pk.T_seek_sec  = 1.91304;
            cfg.ref.alpha_free = 0.155243;
            cfg.ref.D_upd      = 375.109;
            cfg.dg.L_fix       = 75;
            cfg.dg.c_th        = 3;
            cfg.v.use_update_gate = false;
            post.Tmin_sec      = 12.4313;
            post.gap_merge_sec = 0.0;

        case "C"
            cfg.pk.D_th        = 76.5562;
            cfg.pk.D_free      = 42.2718;
            cfg.pk.dist_th     = 6.86006;
            cfg.pk.lambda_occ  = 0.223358;
            cfg.pk.T_seek_sec  = 2.44967;
            cfg.ref.alpha_free = 0.101780;
            cfg.ref.D_upd      = 43.3444;
            cfg.dg.L_fix       = 25;
            cfg.dg.c_th        = 1;
            cfg.v.use_update_gate = true;
            post.Tmin_sec      = 8.45421;
            post.gap_merge_sec = 2.0;

        case "D"
            % D is usually robust; you can keep GLOBAL defaults, or overwrite here.
            % Example: keep as-is.
            % post.gap_merge_sec = 0.0;

        otherwise
            % keep defaults
    end

    csvPath = ch4_find_csv(fileName, p.root, p.synth);
    data = ch4_load_csv(csvPath, cfg.fs);
    out  = ch4_run_parking_fsm(data, cfg);

    [pred_k, ~] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);
    gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
    res = ch4_eval(pred_k, gt_idx, IOU_TH);

    rowTable = table(fileName, group, res.TP, res.FP, res.FN, res.P, res.R, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), ...
        'VariableNames', T_file.Properties.VariableNames);
    T_file = [T_file; rowTable]; %#ok<AGROW>

    fprintf("File=%s | Group=%s | TP=%d FP=%d FN=%d | F1=%.3f\n", fileName, group, res.TP, res.FP, res.FN, res.F1);
end

writetable(T_file, fullfile(p.out, "E1_per_file_oracle.csv"));
T_group = summarize_by_group(T_file);
writetable(T_group, fullfile(p.out, "E1_by_group_oracle.csv"));

disp("=== Oracle By Group (IoU>=0.50) ===");
disp(T_group);

%% ---------------- local helpers (same as global script) ----------------
function [pred_k2, conf_k2] = postprocess_pred_conf(pred_k, conf_k, fs, Tmin_sec, gap_merge_sec)
    if isempty(pred_k)
        pred_k2 = pred_k; conf_k2 = conf_k; return;
    end

    % Filter by minimum duration
    dur = (pred_k(:,2) - pred_k(:,1)) / fs;
    keep = dur >= Tmin_sec;
    pred_k = pred_k(keep,:);
    conf_k = conf_k(keep,:);

    if isempty(pred_k)
        pred_k2 = pred_k; conf_k2 = conf_k; return;
    end

    % Merge by gap
    pred_k2 = []; conf_k2 = [];
    cur = pred_k(1,:); curc = conf_k(1,:);
    for i = 2:size(pred_k,1)
        gap = (pred_k(i,1) - cur(2)) / fs;
        if gap <= gap_merge_sec
            cur(2) = pred_k(i,2);
            curc(2) = conf_k(i,2);
        else
            pred_k2 = [pred_k2; cur]; %#ok<AGROW>
            conf_k2 = [conf_k2; curc]; %#ok<AGROW>
            cur = pred_k(i,:); curc = conf_k(i,:);
        end
    end
    pred_k2 = [pred_k2; cur];
    conf_k2 = [conf_k2; curc];
end

function T_group = summarize_by_group(T_file)
    groups = ["A","B","C","D","ALL"];
    rows = {};
    for g = groups
        if g == "ALL"
            Tf = T_file;
        else
            Tf = T_file(T_file.group == g,:);
        end
        TP = sum(Tf.TP); FP = sum(Tf.FP); FN = sum(Tf.FN);
        P = TP / max(TP + FP, eps);
        R = TP / max(TP + FN, eps);
        F1 = 2*P*R / max(P+R, eps);
        rows(end+1,:) = {g, TP, FP, FN, P, R, F1}; %#ok<AGROW>
    end
    T_group = cell2table(rows, 'VariableNames',{'group','TP','FP','FN','P','R','F1'});
end
