function run_E1_global_best()
%RUN_E1_GLOBAL_BEST One-click E1 evaluation with GLOBAL best params (Tmin=4)
% Output: per-file TP/FP/FN/F1 and by-group + overall summary.

clear; clc;

CODE_DIR = fileparts(mfilename('fullpath'));
addpath(fullfile(CODE_DIR, "..", "core"));
addpath(fullfile(CODE_DIR, "..", "configs"));

p = ch4_local_paths();

DATA_DIR = p.root;
SYN_DIR  = p.synth;
GT_FILE  = p.gt;

IOU_TH = 0.50;

fprintf("=== E1 GLOBAL BEST (Tmin=4, all-events synth GT), IoU>=%.2f ===\n", IOU_TH);

gt = readtable(GT_FILE, "VariableNamingRule","preserve");
gt = ch4_append_synth_gt_all_events(gt, SYN_DIR);

[cfg, post] = cfg_global_best();

files = unique(string(gt.file));
groups = unique(string(gt.scenario_group));
groups = groups(groups~="");

sumByGroup = struct();
for g = 1:numel(groups)
    sumByGroup(g).name = groups(g);
    sumByGroup(g).TP = 0; sumByGroup(g).FP = 0; sumByGroup(g).FN = 0;
end
sumAll.TP = 0; sumAll.FP = 0; sumAll.FN = 0;

files_cnt = 0; events_cnt = 0; pred_cnt = 0; gt_cnt = 0;

for f = 1:numel(files)
    fileName = files(f);

    csvPath = ch4_find_csv(fileName, DATA_DIR, SYN_DIR);
    if csvPath == ""
        fprintf("[Skip] missing file: %s\n", fileName);
        continue;
    end

    gt_f = gt(string(gt.file)==fileName, :);
    if isempty(gt_f)
        fprintf("[Skip] no gt rows: %s\n", fileName);
        continue;
    end

    gname = string(gt_f.scenario_group(1));

    data = ch4_load_csv(csvPath, cfg.fs);
    out  = ch4_run_parking_fsm(data, cfg);

    pred = ch4_pred_postprocess(out.pred_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);

    k0 = data.k(1);
    gt_idx = ch4_gt_k_to_idx([gt_f.k_star_in, gt_f.k_star_out], k0);

    res = ch4_eval(pred, gt_idx, cfg.fs, IOU_TH);

    files_cnt = files_cnt + 1;
    events_cnt = events_cnt + numel(out.events);
    pred_cnt = pred_cnt + size(pred,1);
    gt_cnt = gt_cnt + size(gt_idx,1);

    gi = find(string({sumByGroup.name})==gname, 1);
    if ~isempty(gi)
        sumByGroup(gi).TP = sumByGroup(gi).TP + res.TP;
        sumByGroup(gi).FP = sumByGroup(gi).FP + res.FP;
        sumByGroup(gi).FN = sumByGroup(gi).FN + res.FN;
    end
    sumAll.TP = sumAll.TP + res.TP;
    sumAll.FP = sumAll.FP + res.FP;
    sumAll.FN = sumAll.FN + res.FN;

    fprintf("File=%s | Group=%s | TP=%d FP=%d FN=%d | F1=%.3f | events=%d pred=%d gt=%d\n", ...
        fileName, gname, res.TP, res.FP, res.FN, res.F1, numel(out.events), size(pred,1), size(gt_idx,1));
end

fprintf("\n=== By Group (IoU>=%.2f) ===\n", IOU_TH);
for g = 1:numel(sumByGroup)
    TP = sumByGroup(g).TP; FP = sumByGroup(g).FP; FN = sumByGroup(g).FN;
    P = TP/max(TP+FP,1);
    R = TP/max(TP+FN,1);
    F1 = 2*P*R/max(P+R, eps);
    fprintf("Group=%s | P=%.3f R=%.3f F1=%.3f | FP=%d FN=%d\n", sumByGroup(g).name, P, R, F1, FP, FN);
end

P = sumAll.TP/max(sumAll.TP+sumAll.FP,1);
R = sumAll.TP/max(sumAll.TP+sumAll.FN,1);
F1 = 2*P*R/max(P+R, eps);
fprintf("\nAll | P=%.3f R=%.3f F1=%.3f | FP=%d FN=%d\n", P, R, F1, sumAll.FP, sumAll.FN);
fprintf("files=%d, events=%d, pred=%d, gt=%d\n", files_cnt, events_cnt, pred_cnt, gt_cnt);

end