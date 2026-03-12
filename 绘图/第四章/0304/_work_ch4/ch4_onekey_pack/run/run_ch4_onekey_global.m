% %% run_ch4_onekey_global.m
% % One-click runner for Chapter 4 experiments (GLOBAL config).
% % 
% % Outputs (saved under p.out from core/ch4_local_paths.m):
% %   - E0_dataset_stats.csv
% %   - E1_per_file.csv
% %   - E1_by_group.csv
% %   - E1_timing_by_group.csv
% %   - E3_ablation_by_group.csv   (optional)
% %   - Figures: fig_case_*.png, fig_A_drift_mag.png, fig_B_dist.png, fig_C_seek_ratio.png
% %
% % Prerequisites:
% %   1) Put this file under the repo (recommended: under /run/).
% %   2) Update core/ch4_local_paths.m so that:
% %        p.root  = folder containing *_clean.csv (zhenzhi)
% %        p.synth = folder containing *_synth.csv (synth_out)
% %        p.gt    = GT CSV path (parking_groundtruth_filled_cleaned.csv)
% %        p.out   = output folder
% %   3) Run this script in MATLAB.
% %
% % Notes about reporting:
% %   - This script uses ONE global parameter set (deployment-like).
% %   - If you want "oracle per-group tuned" results, run separate scripts and clearly label as upper bound.
% 
% clear; clc; close all;
% 
% %% 0) Path setup
% thisFile = mfilename('fullpath');
% thisDir  = fileparts(thisFile);
% repoRoot = fileparts(thisDir);
% addpath(genpath(repoRoot));
% 
% p = ch4_local_paths();
% if ~exist(p.out, 'dir'); mkdir(p.out); end
% 
% %% 1) Load GT and append synth GT
% GT = readtable(p.gt);
% 
% % normalize string columns (important for == comparisons)
% GT.file = string(GT.file);
% if ismember("scenario_group", GT.Properties.VariableNames)
%     GT.scenario_group = string(GT.scenario_group);
% else
%     error("GT must contain column: scenario_group");
% end
% 
% GT = ch4_append_synth_gt_all_events(GT, p.synth);
% GT.file = string(GT.file);
% GT.scenario_group = string(GT.scenario_group);
% 
% files = unique(GT.file, 'stable');
% 
% %% 2) Global configuration (match your current E1 output)
% [cfg, post] = ch4_config_tuned_v2("GLOBAL");
% 
% % --- overrides (use your final global values) ---
% cfg.pk.D_th     = 36.0;
% cfg.pk.dist_th  = 4.0;
% cfg.ref.D_upd   = 30.0;
% % --- Figure/display options (visualization only) ---
% % 典型案例图（case）建议展示三轴扰动（相对参考点），以提高可读性与可解释性。
% % 可选：
% %   'dxyz' : 三轴扰动 Bx- Sref_x, By- Sref_y, Bz- Sref_z（推荐，用于 case 图）
% %   'rel'  : 标量残差 ||B-Sref||_2（更利于跨文件对比）
% %   'bx'   : 单轴扰动 Bx- Sref_x（更接近 wave 风格）
% cfg.fig.case_sigMode = 'dxyz';
% cfg.fig.wave_sigMode = 'xyz'; % reserved: waveform demo mode
% 
% 
% post.Tmin_sec      = 6.0;
% post.gap_merge_sec = 0.0;
% 
% IOU_TH = 0.50;
% 
% fprintf("=== E1 GLOBAL (all-events synth GT), IoU>=%.2f ===\n", IOU_TH);
% fprintf("Tmin=%.2f sec | gap_merge=%.2f sec\n", post.Tmin_sec, post.gap_merge_sec);
% fprintf("GLOBAL: D_th=%.2f, D_free=%.2f, dist_th=%.2f, D_upd=%.2f\n", ...
%     cfg.pk.D_th, cfg.pk.D_free, cfg.pk.dist_th, cfg.ref.D_upd);
% 
% %% 2.5) Figure options (PDF+PNG, Chinese labels, thesis placeholders)
% figOpt = struct();
% figOpt.strict = false;                   % true: rethrow figure errors (debug)
% % NOTE:
% %   If you previously ran this script when some figures were missing, it may have
% %   generated placeholder PDFs ("缺少图片占位...") with the same filenames used
% %   by your thesis LaTeX. In that case, you MUST overwrite them once, otherwise
% %   LaTeX will keep showing the placeholder.
% %   After you redraw pipeline/fsm by hand, set this back to false.
% figOpt.force_overwrite_schematics = true;  % overwrite ch4_pipeline/ch4_fsm_degrade
% figOpt.always_make_auto_schematics = true; % always output *_auto.* for selection
% figOpt.make_placeholders = true;         % create placeholder figures if missing
% figOpt.verbose = true;
% 
% % ---- extra figure pools (optional, for selection) ----
% figOpt.extra_pool = true;                % generate ch4_opt_* figures (statistics & distributions)
% % Copy ch4_opt_*.pdf to clean filenames (ch4_*.pdf) for LaTeX convenience
% figOpt.make_alias_without_opt = true;
% 
% % --- Export a curated "paper figure" folder (only the figures that appear in Ch4 LaTeX) ---
% % This does NOT affect normal outputs under p.images_dir; it only copies selected figures
% % into a separate folder for easy inclusion in LaTeX.
% figOpt.export_paper_figs = true;                % set false to disable
% figOpt.paper_fig_dir     = fullfile(p.out, 'paper_figs');
% figOpt.paper_copy_png    = true;                % also copy .png (preview); LaTeX typically uses .pdf
% 
% % List of figure basenames to export (no extension). Keep this aligned with your Ch4 LaTeX.
% % NOTE: D类建议用更长窗口（pad60s），所以这里默认使用 mid_pad60s。
% figOpt.paper_bases = { ...
%     'ch4_pass_vs_park_sim', ...   % 仿真/示意（可替换为 ch4_pass_vs_park）
%     'ch4_pipeline', ...
%     'ch4_stability_demo', ...
%     'ch4_fsm_degrade', ...
%     'ch4_scene_photo', ...
%     'ch4_setup_schematic', ...
%     'ch4_param_scan_Dth', ...
%     'ch4_param_scan_dist', ...
%     'ch4_opt_prf_by_group', ...
%     'ch4_opt_errors_by_group', ...
%     'ch4_opt_timing_tau_box', ...
%     'ch4_opt_timing_dt_cdf', ...
%     'ch4_C_seek_ratio', ...
%     'ch4_opt_ablation_by_group', ...
%     'ch4_sensitivity', ...
%     'ch4_case_A_mid_pad20s', ...
%     'ch4_case_B_mid_pad20s', ...
%     'ch4_case_C_mid_pad20s', ...
%     'ch4_case_D_mid_pad60s' ...
% };
% 
% figOpt.force_overwrite_alias  = true;
% 
% figOpt.extra_examples = true;
% figOpt.make_wave_groups = false; % 不建议作为“四类对比主图”，默认关闭
%             % generate extra case/wave examples (best/mid/worst + random)
% figOpt.extra_random_per_group = 2;       % number of random extra files per group
% figOpt.extra_case_pads_sec = [8, 20];    % context padding (seconds) for extra examples
% figOpt.extra_case_padSec_D = 30;          % D类慢漂移：建议更长窗口（秒）
% figOpt.extra_case_tCenter_by_group = struct('A',[], 'B',[], 'C',[], 'D',[]); % 可手工指定中心时刻（秒）
% figOpt.max_extra_cases_total = 60;       % hard cap to avoid generating too many figures
% % 例如你要把 D 类中心锁在 185s：
% figOpt.extra_case_tCenter_by_group.D = 185;
% %% 3) Run all files (cache minimal info for later plots)
% T_file = table('Size',[0 11], ...
%     'VariableTypes',{'string','string','double','double','double','double','double','double','double','double','double'}, ...
%     'VariableNames',{'file','group','TP','FP','FN','P','R','F1','events','pred','gt'});
% 
% % For E2 distributions
% A_drift_mag = []; A_is_park = [];
% B_dist      = []; B_is_leave = [];
% C_stable_found = []; C_used_degrade = [];
% % For C-group per-file ratios (optional plots)
% C_file = table('Size',[0 4], ...
%     'VariableTypes',{'string','string','double','double'}, ...
%     'VariableNames',{'file','group','stable_found_ratio','used_degrade_ratio'});
% 
% 
% % For timing stats (store per-TP match rows)
% tim_rows = table('Size',[0 8], ...
%     'VariableTypes',{'string','string','double','double','double','double','double','double'}, ...
%     'VariableNames',{'file','group','dt_in','dt_out','tau_in','tau_out','iou','gt_dur'});
% 
% % Case plots: auto-pick first file in each group
% casePick = struct();
% 
% % ===== 手动指定论文 case（覆盖自动挑选，避免挑错事件）=====
% casePick.A = "20240723_停车检测_sheet2_clean.csv";
% casePick.B = "20240723_停车检测_sheet2_e4_B_synth.csv";
% casePick.C = "20240723_停车检测_sheet2_e4_C_synth.csv";
% casePick.D = "20240723_停车检测_sheet2_e1_D_synth.csv";
% 
% % 每类窗口（秒）
% caseWin.padSec  = struct('A',15,'B',30,'C',30,'D',60);
% caseWin.tCenter = struct('A',102,'B',248,'C',248,'D',270);
% for i = 1:numel(files)
%     f = string(files(i));
%     g = string(GT.scenario_group(find(GT.file==f,1,'first')));
%     if isfield(casePick, char(g)) && casePick.(char(g)) == ""
%         casePick.(char(g)) = f;
%     end
% end
% 
% % Cache representative file outputs for thesis figures
% rep = struct('A',[] ,'B',[] ,'C',[] ,'D',[]);
% 
% for i = 1:numel(files)
%     fileName = string(files(i));
%     gt_f = GT(GT.file == fileName, :);
%     group = string(gt_f.scenario_group(1));
% 
%     csvPath = ch4_find_csv(fileName, p.root, p.synth);
% 
%     data = ch4_load_csv(csvPath, cfg.fs);
%     out  = ch4_run_parking_fsm(data, cfg);
% 
%     % Postprocess pred/conf together (keep alignment)
%     [pred_k, conf_k] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);
% 
%     gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
% 
%     res = ch4_eval(pred_k, gt_idx, IOU_TH);
% 
%     % Save per-file
%     rowTable = table(fileName, group, res.TP, res.FP, res.FN, res.P, res.R, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), ...
%         'VariableNames', T_file.Properties.VariableNames);
%     T_file = [T_file; rowTable]; %#ok<AGROW>
% 
%     fprintf("File=%s | Group=%s | TP=%d FP=%d FN=%d | F1=%.3f | events=%d pred=%d gt=%d | Tmin=%.2f\n", ...
%         fileName, group, res.TP, res.FP, res.FN, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), post.Tmin_sec);
% 
%     % -------- E2(A): collect drift_mag for A group --------
%     if group == "A"
%         [arrIdx, ~] = match_events_to_gt(out.events, gt_idx, round(2.0*cfg.fs));
%         for m = 1:numel(out.events)
%             dmag = out.dbg.drift_mag(m);
%             if ~isnan(dmag)
%                 A_drift_mag(end+1,1) = dmag; %#ok<SAGROW>
%                 A_is_park(end+1,1)   = ismember(m, arrIdx); %#ok<SAGROW>
%             end
%         end
%     end
% 
%     % -------- E2(B): collect dist for B group --------
%     if group == "B"
%         [~, leaveIdx] = match_events_to_gt(out.events, gt_idx, round(2.0*cfg.fs));
%         for m = 1:numel(out.events)
%             dd = out.dbg.dist(m);
%             if ~isnan(dd)
%                 B_dist(end+1,1) = dd; %#ok<SAGROW>
%                 B_is_leave(end+1,1) = ismember(m, leaveIdx); %#ok<SAGROW>
%             end
%         end
%     end
% 
%     % -------- E2(C): stable_found ratio / degrade usage --------
%     if group == "C"
%         C_stable_found = [C_stable_found; out.dbg.stable_found(:)]; %#ok<AGROW>
%         C_used_degrade = [C_used_degrade; out.dbg.used_degrade(:)]; %#ok<AGROW>
%         % per-file ratios (for optional plots)
%         try
%             rf = mean(out.dbg.stable_found(:));
%             rd = mean(out.dbg.used_degrade(:));
%             if isfinite(rf) && isfinite(rd)
%                 C_file = [C_file; {fileName, group, rf, rd}]; %#ok<AGROW>
%             end
%         catch
%         end
%     end
% 
%     % -------- Timing stats on matched TP --------
%     if ~isempty(res.match)
%         for r = 1:size(res.match,1)
%             ip = res.match(r,1);
%             ig = res.match(r,2);
%             iou = res.match(r,3);
% 
%             pseg = pred_k(ip,:);
%             cseg = conf_k(ip,:);
%             gseg = gt_idx(ig,:);
% 
%             dt_in  = (pseg(1) - gseg(1)) / cfg.fs;
%             dt_out = (pseg(2) - gseg(2)) / cfg.fs;
%             tau_in  = (cseg(1) - gseg(1)) / cfg.fs;
%             tau_out = (cseg(2) - gseg(2)) / cfg.fs;
% 
%             gt_dur = (gseg(2) - gseg(1)) / cfg.fs;
% 
%             tim_rows = [tim_rows; {fileName, group, dt_in, dt_out, tau_in, tau_out, iou, gt_dur}]; %#ok<AGROW>
%         end
%     end
% 
%     % -------- Plot representative cases --------
%     if isfield(casePick, char(group)) && fileName == casePick.(char(group))
%         % cache representative example for later wave/stability figures
%         rep.(char(group)) = struct('data',data,'out',out,'pred_k',pred_k,'gt_idx',gt_idx,'file',fileName,'group',group);
% 
%         figName = fullfile(p.images_dir, "ch4_case_" + group + ".pdf");
%         % plot_case_one(data, out, pred_k, gt_idx, figName, "工况" + group + "：" + fileName, cfg);
%         padSec = 30;  tC = [];
% try, padSec = caseWin.padSec.(char(group)); end
% try, tC     = caseWin.tCenter.(char(group)); end
% 
% plot_case_one(data, out, pred_k, gt_idx, figName, "工况" + group + "：" + fileName, cfg, ...
%     'padSec', padSec, 'tCenter', tC);
%     end
% end
% 
% %% 3.5) Extra figures for thesis placeholders (auto-generated)
% % These figures are referenced by the Chapter-4 LaTeX placeholders under images/.
% try
%     make_thesis_figures(rep, cfg, p, figOpt);
% catch ME
%     disp(getReport(ME,'extended','hyperlinks','off'));
%     warning('[Fig] make_thesis_figures failed: %s', ME.message);
%     if figOpt.strict
%         rethrow(ME);
%     end
% end
% 
% %% 4) Save E1 tables
% writetable(T_file, fullfile(p.out, "E1_per_file.csv"));
% 
% T_group = summarize_by_group(T_file);
% writetable(T_group, fullfile(p.out, "E1_by_group.csv"));
% 
% % ---- LaTeX table row files for direct \input{} in thesis ----
% write_tex_bycase_rows(T_group, fullfile(p.tables_dir, 'ch4_bycase_global_rows.tex'));
% 
% 
% disp("=== By Group (IoU>=0.50) ===");
% disp(T_group);
% 
% %% 5) Dataset statistics (E0)
% T_ds = dataset_stats_from_outputs(GT, T_file);
% writetable(T_ds, fullfile(p.out, "E0_dataset_stats.csv"));
% write_tex_dataset_rows(T_ds, fullfile(p.tables_dir, 'ch4_dataset_rows.tex'));
% 
% 
% %% 6) Timing statistics (E1 timing)
% T_timing = timing_stats_by_group(tim_rows);
% writetable(T_timing, fullfile(p.out, "E1_timing_by_group.csv"));
% write_tex_timing_rows(T_timing, fullfile(p.tables_dir, 'ch4_timing_global_rows.tex'));
% 
% 
% %% 7) E2 plots (A/B/C) -> mapped to thesis placeholders
% %  - D_th distribution  -> images/ch4_param_scan_Dth.pdf
% %  - dist_th distribution -> images/ch4_param_scan_dist.pdf
% %  - C-group seek/degrade ratio -> images/ch4_C_seek_ratio.pdf (optional)
% 
% if ~isempty(A_drift_mag)
%     fig = ch4_newfig(16, 8);
%     ax = axes(fig); hold(ax,'on'); grid(ax,'on');
% 
%     v0 = A_drift_mag(A_is_park==0);
%     v1 = A_drift_mag(A_is_park==1);
% 
%     edges = ch4_hist_edges(A_drift_mag, 30);
%     cc = (edges(1:end-1) + edges(2:end)) / 2;
%     p0 = histcounts(v0, edges, 'Normalization','probability');
%     p1 = histcounts(v1, edges, 'Normalization','probability');
% 
%     plot(ax, cc, p0, '-',  'LineWidth', 1.4);
%     plot(ax, cc, p1, '--', 'LineWidth', 1.4);
% 
%     yl = ylim(ax);
%     plot(ax, [cfg.pk.D_th cfg.pk.D_th], yl, ':', 'LineWidth', 1.2);
%     ylim(ax, yl);
%     text(ax, cfg.pk.D_th, yl(2), sprintf('  D_{th}=%.1f', cfg.pk.D_th), ...
%         'VerticalAlignment','top', 'HorizontalAlignment','left', 'FontSize', 9);
% 
%     xlabel(ax, '漂移幅值 ||\Delta B||_2'); ylabel(ax, '概率');
%     legend(ax, {'通过/干扰', '停车到达'}, 'Location','best');
%     title(ax, 'A类：漂移幅值分布');
% 
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, fullfile(p.images_dir, 'ch4_param_scan_Dth.pdf'));
%     close(fig);
% end
% 
% if ~isempty(B_dist)
%     fig = ch4_newfig(10, 6);
%     ax = axes(fig); hold(ax,'on'); grid(ax,'on');
% 
%     d_keep  = B_dist((~B_is_leave) & ~isnan(B_dist));
%     d_leave = B_dist(( B_is_leave) & ~isnan(B_dist));
% 
%     edges = ch4_hist_edges(d_keep, 25);
%     p_keep = histcounts(d_keep, edges, 'Normalization','probability');
%     x = edges(1:end-1);
%     plot(ax, x, p_keep, 'LineWidth', 1.8);
% 
%     leg = {'仍占用扰动事件'};
%     if numel(d_leave) >= 5
%         p_leave = histcounts(d_leave, edges, 'Normalization','probability');
%         plot(ax, x, p_leave, '--', 'LineWidth', 1.8);
%         leg = {'仍占用扰动事件', '驶离事件（若dist有效）'};
%     else
%         text(ax, 0.02, 0.10, '注：驶离多由 D_{free}(back2env) 判决，dist样本可能缺失', ...
%             'Units','normalized', 'FontSize', 10, 'Color', [0.3 0.3 0.3]);
%     end
% 
%     xline(ax, cfg.pk.dist_th, ':', sprintf('dist_{th}=%.1f', cfg.pk.dist_th), 'LineWidth', 1.2);
% 
%     if ~isempty(d_keep)
%         acc = mean(d_keep < cfg.pk.dist_th);
%         text(ax, 0.02, 0.90, sprintf('Acc@dist_{th}=%.1f%%', 100*acc), ...
%             'Units','normalized', 'FontSize', 11, 'Color', [0.1 0.1 0.1]);
%     end
% 
%     xlabel(ax, 'dist');
%     ylabel(ax, '概率');
%     legend(ax, leg, 'Location', 'best');
%     title(ax, '验证集：dist 分布与 dist_{th}（占用稳态门控）');
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, fullfile(p.images_dir, 'ch4_param_scan_dist.pdf'));
%     close(fig);
% end
% 
% if ~isempty(C_stable_found)
%     r_found = mean(C_stable_found);
%     r_deg   = mean(C_used_degrade);
% 
%     fig = ch4_newfig(10, 6);
%     ax = axes(fig);
%     bar(ax, [r_found, r_deg]);
%     set(ax, 'XTickLabel', {'稳定点可得','退化分支'});
%     ylim(ax, [0 1]);
%     ylabel(ax, '比例');
%     title(ax, 'C类：稳定点可得率与退化分支使用率');
% 
%     % annotate
%     for i = 1:2
%         val = [r_found, r_deg];
%         text(ax, i, val(i)+0.03, sprintf('%.2f', val(i)), 'HorizontalAlignment','center', 'FontSize',9);
%     end
% 
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, fullfile(p.images_dir, 'ch4_C_seek_ratio.pdf'));
%     close(fig);
% end
% 
% % ---- Sensitivity / threshold sweep figure (optional but recommended) ----
% % This figure is referenced by the LaTeX placeholder: images/ch4_sensitivity.pdf
% try
%     plot_sensitivity_fig(A_drift_mag, A_is_park, B_dist, B_is_leave, cfg, p);
% catch ME
%     disp(getReport(ME,'extended','hyperlinks','off'));
%     warning('[Fig] plot_sensitivity_fig failed: %s', ME.message);
%     if figOpt.strict
%         rethrow(ME);
%     end
% end
% 
% %% 8) E3 Ablation study (optional, but recommended)
% DO_ABLATION = true;
% if DO_ABLATION
%     variants = {
%         "Ours",            struct();
%         "Abl_noMeanDiff",  struct('use_mean_diff', false);
%         "Abl_noSimilarity",struct('use_similarity', false);
%         "Abl_noDegrade",   struct('use_degrade', false);
%         "Abl_noUpdateGate",struct('use_update_gate', false);
%     };
% 
%     T_ab = table('Size',[0 7], ...
%         'VariableTypes',{'string','double','double','double','double','double','double'}, ...
%         'VariableNames',{'variant','F1_all','F1_A','F1_B','F1_C','F1_D','TP_all'});
% 
%     for v = 1:size(variants,1)
%         name = variants{v,1};
%         mod  = variants{v,2};
% 
%         cfgv = cfg;
%         if isfield(mod,'use_mean_diff');   cfgv.v.use_mean_diff   = mod.use_mean_diff; end
%         if isfield(mod,'use_similarity');  cfgv.v.use_similarity  = mod.use_similarity; end
%         if isfield(mod,'use_degrade');     cfgv.v.use_degrade     = mod.use_degrade; end
%         if isfield(mod,'use_update_gate'); cfgv.v.use_update_gate = mod.use_update_gate; end
% 
%         Tv = run_eval_only(files, GT, p, cfgv, post, IOU_TH);
%         Tg = summarize_by_group(Tv);
% 
%         f1_all = Tg.F1(Tg.group=="ALL");
%         f1A = Tg.F1(Tg.group=="A");
%         f1B = Tg.F1(Tg.group=="B");
%         f1C = Tg.F1(Tg.group=="C");
%         f1D = Tg.F1(Tg.group=="D");
%         TPall = Tg.TP(Tg.group=="ALL");
% 
%         T_ab = [T_ab; {name, f1_all, f1A, f1B, f1C, f1D, TPall}]; %#ok<AGROW>
%     end
% 
%     writetable(T_ab, fullfile(p.out, "E3_ablation_by_group.csv"));
%     write_tex_ablation_rows(T_ab, fullfile(p.tables_dir, 'ch4_ablation_global_rows.tex'));
% 
%     disp("=== Ablation (GLOBAL) ==="); disp(T_ab);
% end
% 
% %% 8.5) Optional figure pool and extra examples (for selection)
% % These figures are NOT referenced by the LaTeX placeholders by default.
% % They are generated as "ch4_opt_*" and "ch4_case_*_{best/mid/worst/rand}_padXs" for you to choose.
% 
% if isfield(figOpt,'extra_pool') && figOpt.extra_pool
%     try
%         if exist('T_ab','var')
%             Tab = T_ab;
%         else
%             Tab = table();
%         end
%         make_optional_fig_pool(T_file, T_group, T_ds, T_timing, tim_rows, ...
%             A_drift_mag, A_is_park, B_dist, B_is_leave, C_file, Tab, cfg, p, figOpt);
%     catch ME
%         disp(getReport(ME,'extended','hyperlinks','off'));
%         warning('[Fig] make_optional_fig_pool failed: %s', ME.message);
%         if figOpt.strict
%             rethrow(ME);
%         end
%     end
% end
% 
% % Optional: create alias copies without the opt_ prefix so LaTeX can use clean filenames
% if isfield(figOpt,'make_alias_without_opt') && figOpt.make_alias_without_opt
%     try
%         ch4_make_aliases_without_opt(p, figOpt);
%     catch ME
%         disp(getReport(ME,'extended','hyperlinks','off'));
%         warning('[Fig] ch4_make_aliases_without_opt failed: %s', ME.message);
%         if figOpt.strict
%             rethrow(ME);
%         end
%     end
% end
% 
% if isfield(figOpt,'extra_examples') && figOpt.extra_examples
%     try
%         make_extra_examples(T_file, GT, p, cfg, post, IOU_TH, figOpt);
%     catch ME
%         disp(getReport(ME,'extended','hyperlinks','off'));
%         warning('[Fig] make_extra_examples failed: %s', ME.message);
%         if figOpt.strict
%             rethrow(ME);
%         end
%     end
% end
% 
% %% 9) Report figure outputs and (optionally) generate placeholders
% expectedFigs = {
%     % --- Figures referenced by the Chapter-4 LaTeX (recommended set) ---
%     'ch4_pass_vs_park'
%     'ch4_pipeline_auto'
%     'ch4_fsm_degrade_auto'
%     'ch4_stability_demo'
%     'ch4_param_scan_Dth'
%     'ch4_param_scan_dist'
%     'ch4_scene_photo'          % placeholder (replace by real photo)
%     'ch4_setup_schematic'      % placeholder (redraw for publication)
%     'ch4_opt_dataset_stats'
%     'ch4_opt_prf_by_group'
%     'ch4_opt_timing_tau_box'
%     'ch4_opt_timing_tau_cdf'
%     'ch4_C_seek_ratio'
%     'ch4_opt_ablation_by_group'
%     'ch4_sensitivity'
%     'ch4_case_A_mid_pad20s'
%     'ch4_case_B_mid_pad20s'
%     'ch4_case_C_mid_pad20s'
%     'ch4_case_D_mid_pad20s'
% 
%     % --- Compatibility aliases (clean names without opt_/auto) ---
%     'ch4_pipeline'
%     'ch4_fsm_degrade'
%     'ch4_dataset_stats'
%     'ch4_prf_by_group'
%     'ch4_timing_tau_box'
%     'ch4_timing_tau_cdf'
%     'ch4_ablation_by_group'
%     'ch4_ablation_fig'
% };
% 
% ch4_report_fig_status(p, expectedFigs, figOpt);
% 
% % Export curated paper figures to a separate folder (optional)
% if isfield(figOpt,'export_paper_figs') && figOpt.export_paper_figs
%     ch4_export_paper_figs(p, figOpt);
% end
% 
% disp("Done. All outputs saved under: " + string(p.out));
% 
% %% ================= Local helper functions =================
% 
% function [pred2, conf2] = postprocess_pred_conf(pred_k, conf_k, fs, Tmin_sec, gap_merge_sec)
%     if isempty(pred_k)
%         pred2 = pred_k; conf2 = conf_k; return;
%     end
%     dur_sec = (pred_k(:,2) - pred_k(:,1)) / fs;
%     keep = dur_sec >= Tmin_sec;
%     pred_k = pred_k(keep,:);
%     conf_k = conf_k(keep,:);
% 
%     if isempty(pred_k) || gap_merge_sec <= 0 || size(pred_k,1) <= 1
%         pred2 = pred_k; conf2 = conf_k; return;
%     end
% 
%     [~,ord] = sort(pred_k(:,1));
%     pred_k = pred_k(ord,:);
%     conf_k = conf_k(ord,:);
% 
%     gap_k = round(gap_merge_sec * fs);
% 
%     pred2 = pred_k(1,:);
%     conf2 = conf_k(1,:);
%     for i = 2:size(pred_k,1)
%         if pred_k(i,1) - pred2(end,2) <= gap_k
%             pred2(end,2) = max(pred2(end,2), pred_k(i,2));
%             conf2(end,2) = conf_k(i,2); % take the latest confirmation out
%         else
%             pred2 = [pred2; pred_k(i,:)]; %#ok<AGROW>
%             conf2 = [conf2; conf_k(i,:)]; %#ok<AGROW>
%         end
%     end
% end
% 
% function [arrIdx, leaveIdx] = match_events_to_gt(events, gt_idx, tol_k)
%     arrIdx = [];
%     leaveIdx = [];
%     if isempty(events) || isempty(gt_idx); return; end
%     kout = zeros(numel(events),1);
%     for i = 1:numel(events); kout(i) = events(i).k_out; end
% 
%     for j = 1:size(gt_idx,1)
%         kin  = gt_idx(j,1);
%         kout_gt = gt_idx(j,2);
% 
%         [d1, i1] = min(abs(kout - kin));
%         if d1 <= tol_k; arrIdx(end+1) = i1; end %#ok<AGROW>
% 
%         [d2, i2] = min(abs(kout - kout_gt));
%         if d2 <= tol_k; leaveIdx(end+1) = i2; end %#ok<AGROW>
%     end
%     arrIdx   = unique(arrIdx);
%     leaveIdx = unique(leaveIdx);
% end
% 
% function T_group = summarize_by_group(T_file)
%     groups = ["A","B","C","D"];
%     rows = {};
%     for g = groups
%         Tf = T_file(T_file.group == g, :);
%         TP = sum(Tf.TP); FP = sum(Tf.FP); FN = sum(Tf.FN);
%         [P,R,F1] = prf(TP,FP,FN);
%         Ngt = TP + FN;
%         Rf = FP / max(Ngt,1);
%         Rm = FN / max(Ngt,1);
%         rows(end+1,:) = {g, TP, FP, FN, P, R, F1, Rf, Rm}; %#ok<AGROW>
%     end
%     TP = sum(T_file.TP); FP = sum(T_file.FP); FN = sum(T_file.FN);
%     [P,R,F1] = prf(TP,FP,FN);
%     Ngt = TP + FN;
%     Rf = FP / max(Ngt,1);
%     Rm = FN / max(Ngt,1);
%     rows(end+1,:) = {"ALL", TP, FP, FN, P, R, F1, Rf, Rm}; %#ok<AGROW>
% 
%     T_group = cell2table(rows, ...
%         'VariableNames',{'group','TP','FP','FN','P','R','F1','Rf','Rm'});
% end
% 
% function [P,R,F1] = prf(TP,FP,FN)
%     P = TP / max(TP+FP, 1);
%     R = TP / max(TP+FN, 1);
%     F1 = 2*P*R / max(P+R, eps);
% end
% 
% function T_ds = dataset_stats_from_outputs(GT, T_file)
%     groups = ["A","B","C","D"];
%     rows = {};
%     for g = groups
%         files_g = unique(GT.file(GT.scenario_group==g), 'stable');
%         Tf = T_file(T_file.group==g,:);
%         nFiles = numel(files_g);
%         Ngt = sum(Tf.gt);
%         Nevents = sum(Tf.events);
%         Npass = max(Nevents - 2*Ngt, 0);
%         rows(end+1,:) = {g, nFiles, Ngt, Nevents, Npass}; %#ok<AGROW>
%     end
%     T_ds = cell2table(rows, 'VariableNames',{'group','num_files','num_parking_gt','num_vehicle_events','num_pass_est'});
% end
% 
% function T_timing = timing_stats_by_group(tim_rows)
%     groups = ["A","B","C","D","ALL"];
%     rows = {};
%     for g = groups
%         if g == "ALL"
%             Tr = tim_rows;
%         else
%             Tr = tim_rows(tim_rows.group==g,:);
%         end
%         if isempty(Tr)
%             rows(end+1,:) = {g, 0, NaN, NaN, NaN, NaN, NaN, NaN}; %#ok<AGROW>
%             continue;
%         end
%         med_abs_dt_in  = median(abs(Tr.dt_in));
%         med_abs_dt_out = median(abs(Tr.dt_out));
%         med_tau_in  = median(Tr.tau_in);
%         med_tau_out = median(Tr.tau_out);
%         p95_tau_in  = prctile(Tr.tau_in, 95);
%         p95_tau_out = prctile(Tr.tau_out, 95);
%         rows(end+1,:) = {g, height(Tr), med_abs_dt_in, med_abs_dt_out, med_tau_in, med_tau_out, p95_tau_in, p95_tau_out}; %#ok<AGROW>
%     end
%     T_timing = cell2table(rows, 'VariableNames', ...
%         {'group','N_TP','med_abs_dt_in','med_abs_dt_out','med_tau_in','med_tau_out','p95_tau_in','p95_tau_out'});
% end
% 
% % function plot_case_one(data, out, pred_k, gt_idx, figPath, figTitle, cfg, varargin)
% % %PLOT_CASE_ONE Event-level case visualization (compact, thesis-friendly).
% % %
% % % 目标：避免整段文件绘制导致四宫格缩放后不可读。默认以“代表性事件中心”
% % % 截取 t0±padSec 的窗口，并在图中叠加 GT 与算法输出区间。
% % %
% % % 子图（自上而下）：
% % % 1) 相对幅值 ||B - S_{pre}(0)||_2（S_{pre}(0) 为文件起始参考均值）
% % % 2) stable flag（稳定判据是否满足）
% % % 3) GT vs Pred 占用区间（条带显示，便于答辩解释）
% % 
% % % Backward compatibility: allow a positional numeric padSec as the first varargin element
% % posPadSec = [];
% % if ~isempty(varargin) && isnumeric(varargin{1})
% %     posPadSec = varargin{1};
% %     varargin = varargin(2:end);
% % end
% % 
% % defaultSigMode = 'rel';
% % if isfield(cfg,'fig') && isfield(cfg.fig,'case_sigMode')
% %     defaultSigMode = cfg.fig.case_sigMode;
% % end
% % 
% % ip = inputParser;
% % addParameter(ip, 'padSec', 30, @(x)isnumeric(x)&&isscalar(x)&&x>0);
% % addParameter(ip, 'tCenter', [], @(x)isempty(x)||(isnumeric(x)&&isscalar(x)));
% % addParameter(ip, 'centerMode', 'auto', @(s)ischar(s)||isstring(s));
% % addParameter(ip, 'sigMode', defaultSigMode, @(s) ischar(s) || isstring(s));
% % parse(ip, varargin{:});
% % padSec    = ip.Results.padSec;
% % if ~isempty(posPadSec); padSec = posPadSec; end
% % tCenter   = ip.Results.tCenter;
% % centerMode = char(ip.Results.centerMode);
% % sigMode   = lower(strtrim(char(ip.Results.sigMode)));
% % 
% % t = data.t(:);
% % n = numel(t);
% % 
% % % Reference baseline (initial)
% % k_ref = 1 : min(n, max(1, round(2*cfg.fs)));
% % S_ref = mean(data.B(k_ref,:), 1);
% % relB = vecnorm(data.B - S_ref, 2, 2);
% % % --- display mode (signal shown in subplot-1) ---
% % % case 图（证据链闭环）推荐三轴扰动；wave 图可用单轴增强直观性。
% % needLegend = false;
% % legLabels  = {};
% % if any(strcmp(sigMode, {'dxyz','xyz','3axis','tri','three'}))
% %     % 三轴扰动（相对参考点 S_ref），更贴合“输入→判据→输出”的可解释链条
% %     showSig = data.B - S_ref;            % N×3
% %     ylab1   = '$\Delta B\ (nT)$';
% %     drawDth = false;
% %     needLegend = true;
% %     legLabels  = {'$\Delta B_x$','$\Delta B_y$','$\Delta B_z$'};
% % elseif any(strcmp(sigMode, {'bx','x'}))
% %     showSig = data.B(:,1) - S_ref(1);
% %     ylab1   = '$\Delta B_x\ (nT)$';
% %     drawDth = false;
% % elseif any(strcmp(sigMode, {'norm','mag'}))
% %     showSig = vecnorm(data.B, 2, 2);
% %     ylab1   = '$\|B\|_2$';
% %     drawDth = false;
% % else
% %     % 标量残差（更利于跨文件对比/对齐阈值含义）
% %     showSig = relB;
% %     ylab1   = '$\|B-S_{ref}\|_2$';
% %     drawDth = true;
% % end
% % 
% % % Choose center index k0
% % if ~isempty(tCenter)
% %     [~, k0] = min(abs(t - tCenter));
% % else
% %     k0 = pick_case_center_k(figTitle, relB, out, pred_k, gt_idx, cfg, centerMode);
% % end
% % 
% % pad = round(padSec * cfg.fs);
% % k1 = max(1, k0 - pad);
% % k2 = min(n, k0 + pad);
% % 
% % fig = figure('Visible','off','Color','w','Position',[80 80 1200 720]);
% % tl = tiledlayout(fig, 3, 1, 'Padding','compact', 'TileSpacing','compact');
% % 
% % % ---------- (1) Relative magnitude ----------
% % ax1 = nexttile(tl, 1); hold(ax1,'on'); box(ax1,'on'); grid(ax1,'on');
% % plot(ax1, t(k1:k2), showSig(k1:k2,:), 'LineWidth', 1.3);
% % ylabel(ax1, ylab1, 'Interpreter','latex');
% % if drawDth
% %     yline(ax1, cfg.D_th, '--', 'LineWidth', 1.0);
% % end
% % title(ax1, figTitle, 'Interpreter','none');
% % 
% % % Legend for 3-axis display
% % if needLegend
% %     lg = legend(ax1, legLabels, 'Location','northeast');
% %     set(lg, 'Interpreter','latex', 'FontSize', 8, 'Box', 'off');
% % end
% % 
% % % Overlay GT / Pred occupancy (full-height shading)
% % if ~isempty(pred_k)
% %     add_interval_patches(ax1, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.22);
% % end
% % if ~isempty(gt_idx)
% %     add_interval_patches(ax1, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.18);
% % end
% % xline(ax1, t(k0), ':', 'LineWidth', 1.0);
% % 
% % % ---------- (2) Stability flag ----------
% % ax2 = nexttile(tl, 2); hold(ax2,'on'); box(ax2,'on'); grid(ax2,'on');
% % if isfield(out,'stable') && ~isempty(out.stable)
% %     st = out.stable(:);
% %     if numel(st) >= n
% %         st = st(1:n);
% %     else
% %         st = [st; zeros(n-numel(st),1)];
% %     end
% % else
% %     st = zeros(n,1);
% % end
% % plot(ax2, t(k1:k2), st(k1:k2), 'LineWidth', 1.2);
% % ylim(ax2, [-0.1 1.1]);
% % ylabel(ax2, 'stable');
% % xline(ax2, t(k0), ':', 'LineWidth', 1.0);
% % 
% % % ---------- (3) GT vs Pred bars ----------
% % ax3 = nexttile(tl, 3); hold(ax3,'on'); box(ax3,'on');
% % xlim(ax3, [t(k1) t(k2)]);
% % ylim(ax3, [0 1]);
% % yticks(ax3, [0.25 0.75]);
% % yticklabels(ax3, {'Pred','GT'});
% % xlabel(ax3, '时间/s');
% % 
% % if ~isempty(pred_k)
% %     add_interval_bars(ax3, t, pred_k, k1, k2, 0.10, 0.40, [0.80 0.90 1.00], 0.85);
% % end
% % if ~isempty(gt_idx)
% %     add_interval_bars(ax3, t, gt_idx,  k1, k2, 0.60, 0.90, [0.86 0.86 0.86], 0.85);
% % end
% % xline(ax3, t(k0), ':', 'LineWidth', 1.0);
% % 
% % linkaxes([ax1 ax2 ax3], 'x');
% % 
% % ch4_export_fig(fig, figPath);
% % close(fig);
% % end
% 
% 
% function plot_case_one(data, out, pred_k, gt_idx, figPath, figTitle, cfg, varargin)
% %PLOT_CASE_ONE  Thesis-ready case visualization (4 rows).
% %
% % Row-1: 三轴扰动 ΔB = B - S_ref,   S_ref = 事件前(文件起始) 2s 均值
% % Row-2: 主判据曲线 D(t)=||B - S_pre(t)||_2 + 阈值线（D_th / D_free）
% %        可选：叠加 dist 事件点 + dist_th（若 out.dbg.dist 存在）
% % Row-3: 内部逻辑条带：stableState / degrade / dist_gate / update_gate(限幅)
% % Row-4: GT vs Pred 占用条带（结论图层）
% %
% % Optional name-value:
% %   'padSec'    : window half width in seconds
% %   'tCenter'   : manual center time (sec)
% %   'centerMode': 'auto' (default) | 'midfile'
% 
% % --- backward compatibility: allow positional numeric padSec ---
% posPadSec = [];
% if ~isempty(varargin) && isnumeric(varargin{1})
%     posPadSec = varargin{1};
%     varargin = varargin(2:end);
% end
% 
% % --- defaults ---
% defaultSigMode = 'dxyz';
% if isfield(cfg,'fig') && isfield(cfg.fig,'case_sigMode')
%     defaultSigMode = cfg.fig.case_sigMode;
% end
% 
% ip = inputParser;
% addParameter(ip, 'padSec', 30, @(x)isnumeric(x)&&isscalar(x)&&x>0);
% addParameter(ip, 'tCenter', [], @(x)isempty(x)||(isnumeric(x)&&isscalar(x)));
% addParameter(ip, 'centerMode', 'auto', @(s)ischar(s)||isstring(s));
% addParameter(ip, 'sigMode', defaultSigMode, @(s)ischar(s)||isstring(s));
% parse(ip, varargin{:});
% 
% padSec     = ip.Results.padSec;
% if ~isempty(posPadSec); padSec = posPadSec; end
% tCenter    = ip.Results.tCenter;
% centerMode = char(ip.Results.centerMode);
% sigMode    = lower(strtrim(char(ip.Results.sigMode)));
% 
% t = data.t(:);
% B = data.B;
% n = numel(t);
% 
% % ---------- S_ref: file-begin 2s mean ----------
% k_ref = 1 : min(n, max(1, round(2*cfg.fs)));
% S_ref = mean(B(k_ref,:), 1);
% 
% % ---------- choose k0 ----------
% relB0 = vecnorm(B - S_ref, 2, 2); % for center picking heuristic
% if ~isempty(tCenter)
%     [~, k0] = min(abs(t - tCenter));
% else
%     k0 = pick_case_center_k(figTitle, relB0, out, pred_k, gt_idx, cfg, centerMode);
% end
% 
% pad = round(padSec * cfg.fs);
% k1 = max(1, k0 - pad);
% k2 = min(n, k0 + pad);
% 
% % ---------- signals for plotting ----------
% % Row-1 signal: default use dxyz (ΔB)
% if any(strcmp(sigMode, {'dxyz','xyz','3axis','tri','three'}))
%     sig1 = B - S_ref;          % Nx3
%     ylab1 = 'ΔB / nT';
%     showLegend1 = true;
% else
%     sig1 = relB0;              % Nx1
%     ylab1 = '||B-S_{ref}||_2 / nT';
%     showLegend1 = false;
% end
% 
% % stableState (fix: prefer out.st.stableState)
% stable = ch4_get_stable_vec(out, n);
% 
% % Baseline trace (S_pre(t)) reconstructed for visualization
% [S_pre_tr, updLimited] = ch4_build_Spre_trace(data, out, pred_k, cfg, S_ref, stable);
% 
% % Row-2 main criterion: D(t)=||B-S_pre(t)||_2
% D = vecnorm(B - S_pre_tr, 2, 2);
% 
% % dist (event-level) -> scatter series at event k_out
% distSeries = ch4_event_value_series(n, out, "dist");
% 
% % Row-3 internal flags -> segments (bars)
% fs = cfg.fs;
% stableSeg  = ch4_binary_to_segments(stable);
% degradeSeg = ch4_eventflag_to_segments(n, out, "used_degrade", round(0.6*fs)); % ±0.6s
% distKeepSeg = ch4_event_distkeep_segments(n, out, cfg, round(0.6*fs));         % ±0.6s
% updLimSeg  = ch4_binary_to_segments(updLimited);
% 
% % ---------- figure ----------
% fig = figure('Visible','off','Color','w','Position',[80 80 1200 900]);
% tl = tiledlayout(fig, 4, 1, 'Padding','compact', 'TileSpacing','compact');
% 
% % ===== Row 1: ΔB three-axis =====
% ax1 = nexttile(tl, 1); hold(ax1,'on'); box(ax1,'on'); grid(ax1,'on');
% % shaded GT/Pred first (keep curves on top)
% if ~isempty(pred_k), add_interval_patches(ax1, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.18); end
% if ~isempty(gt_idx), add_interval_patches(ax1, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.16); end
% 
% plot(ax1, t(k1:k2), sig1(k1:k2,:), 'LineWidth', 1.2);
% if showLegend1
%     yline(ax1, 0, 'r--', 'LineWidth', 1.0); % baseline y=0 (ΔB)
%     lg = legend(ax1, {'ΔB_x','ΔB_y','ΔB_z'}, 'Location','northeast');
%     lg.Box = 'off';
% end
% ylabel(ax1, ylab1);
% title(ax1, figTitle, 'Interpreter','none');
% xline(ax1, t(k0), ':', 'LineWidth', 1.0);
% 
% % ===== Row 2: main criterion D(t) + thresholds (and optional dist) =====
% ax2 = nexttile(tl, 2); hold(ax2,'on'); box(ax2,'on'); grid(ax2,'on');
% if ~isempty(pred_k), add_interval_patches(ax2, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.12); end
% if ~isempty(gt_idx), add_interval_patches(ax2, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.10); end
% 
% yyaxis(ax2, 'left');
% plot(ax2, t(k1:k2), D(k1:k2), 'LineWidth', 1.2);
% ylabel(ax2, 'D(t)=||B-S_{pre}(t)||_2 / nT');
% 
% % thresholds (if fields exist)
% if isfield(cfg,'pk') && isfield(cfg.pk,'D_th')
%     yline_if(ax2, cfg.pk.D_th, '--', sprintf('D_{th}=%.1f', cfg.pk.D_th));
% end
% if isfield(cfg,'pk') && isfield(cfg.pk,'D_free')
%     yline_if(ax2, cfg.pk.D_free, ':', sprintf('D_{free}=%.1f', cfg.pk.D_free));
% end
% 
% % optional dist on right axis
% hasDist = any(isfinite(distSeries(k1:k2)));
% if hasDist
%     yyaxis(ax2, 'right');
%     idx = find(isfinite(distSeries));
%     idx = idx(idx>=k1 & idx<=k2);
%     plot(ax2, t(idx), distSeries(idx), 'o', 'MarkerSize', 4, 'LineWidth', 1.0);
%     ylabel(ax2, 'dist（事件点）');
%     if isfield(cfg,'pk') && isfield(cfg.pk,'dist_th')
%         yline_if(ax2, cfg.pk.dist_th, '--', sprintf('dist_{th}=%.1f', cfg.pk.dist_th));
%     end
% end
% xline(ax2, t(k0), ':', 'LineWidth', 1.0);
% 
% % ===== Row 3: internal logic bars =====
% ax3 = nexttile(tl, 3); hold(ax3,'on'); box(ax3,'on');
% xlim(ax3, [t(k1) t(k2)]);
% ylim(ax3, [0 1]);
% grid(ax3,'on');
% 
% % optionally shade GT/Pred to align reading
% if ~isempty(pred_k), add_interval_patches(ax3, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.08); end
% if ~isempty(gt_idx), add_interval_patches(ax3, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.06); end
% 
% % bars at different y-levels to avoid overlap
% % stable
% add_interval_bars(ax3, t, stableSeg,   k1, k2, 0.78, 0.95, [0.70 0.90 0.70], 0.85);
% % degrade
% add_interval_bars(ax3, t, degradeSeg,  k1, k2, 0.56, 0.72, [1.00 0.86 0.65], 0.85);
% % dist gate (keep occ)
% add_interval_bars(ax3, t, distKeepSeg, k1, k2, 0.34, 0.50, [0.80 0.90 1.00], 0.85);
% % update gate limited
% add_interval_bars(ax3, t, updLimSeg,   k1, k2, 0.12, 0.28, [1.00 0.75 0.75], 0.85);
% 
% yticks(ax3, [0.20 0.42 0.64 0.865]);
% yticklabels(ax3, {'upd\_limit','dist\_gate','degrade','stable'});
% 
% ylabel(ax3, '内部逻辑');
% xline(ax3, t(k0), ':', 'LineWidth', 1.0);
% 
% % ===== Row 4: GT vs Pred occupancy bars =====
% ax4 = nexttile(tl, 4); hold(ax4,'on'); box(ax4,'on');
% xlim(ax4, [t(k1) t(k2)]);
% ylim(ax4, [0 1]);
% yticks(ax4, [0.25 0.75]);
% yticklabels(ax4, {'Pred','GT'});
% xlabel(ax4, '时间 / s');
% 
% if ~isempty(pred_k)
%     add_interval_bars(ax4, t, pred_k, k1, k2, 0.10, 0.40, [0.80 0.90 1.00], 0.85);
% end
% if ~isempty(gt_idx)
%     add_interval_bars(ax4, t, gt_idx,  k1, k2, 0.60, 0.90, [0.86 0.86 0.86], 0.85);
% end
% xline(ax4, t(k0), ':', 'LineWidth', 1.0);
% 
% linkaxes([ax1 ax2 ax3 ax4], 'x');
% 
% % style + export
% try
%     ch4_apply_style(fig);
% catch
% end
% ch4_export_fig(fig, figPath);
% close(fig);
% end
% 
% %% ===================== helpers for case plot =====================
% 
% function stable = ch4_get_stable_vec(out, n)
% % robust stableState extraction (avoid all-zeros)
% stable = [];
% if isfield(out,'st') && isfield(out.st,'stableState')
%     stable = out.st.stableState;
% elseif isfield(out,'stable')
%     stable = out.stable;
% elseif isfield(out,'flags') && isfield(out.flags,'stable')
%     stable = out.flags.stable;
% end
% if isempty(stable)
%     stable = zeros(n,1);
% else
%     stable = double(stable(:));
%     if numel(stable) < n
%         stable = [stable; zeros(n-numel(stable),1)];
%     else
%         stable = stable(1:n);
%     end
% end
% end
% 
% function [S_pre_tr, updLimited] = ch4_build_Spre_trace(data, out, pred_k, cfg, S_ref, stable)
% % Reconstruct a visualization-only baseline S_pre(t) (piecewise updates at stable points).
% B = data.B;
% n = size(B,1);
% S_pre_tr = zeros(n,3);
% updLimited = zeros(n,1);
% 
% % if no ref config -> constant
% if ~isfield(cfg,'ref') || ~isfield(cfg.ref,'enable') || ~cfg.ref.enable
%     for k = 1:n
%         S_pre_tr(k,:) = S_ref;
%     end
%     return;
% end
% 
% alpha = cfg.ref.alpha_free;
% useGate = isfield(cfg,'v') && isfield(cfg.v,'use_update_gate') && cfg.v.use_update_gate ...
%           && isfield(cfg.ref,'D_upd');
% 
% % occupancy mask from pred (avoid updating during occupied)
% occ = false(n,1);
% if ~isempty(pred_k)
%     for i = 1:size(pred_k,1)
%         a = max(1, round(pred_k(i,1)));
%         b = min(n, round(pred_k(i,2)));
%         if b >= a
%             occ(a:b) = true;
%         end
%     end
% end
% 
% % need meanVec
% meanVec = [];
% if isfield(out,'st') && isfield(out.st,'meanVec')
%     meanVec = out.st.meanVec;
% end
% 
% S_pre = S_ref;
% for k = 1:n
%     S_pre_tr(k,:) = S_pre;
% 
%     if occ(k), continue; end
%     if stable(k) <= 0.5, continue; end
% 
%     if ~isempty(meanVec) && k <= size(meanVec,1)
%         S_cand = meanVec(k,:);
%     else
%         % fallback: local mean over 0.5s
%         L = max(1, round(0.5*cfg.fs));
%         a = max(1, k-L+1);
%         S_cand = mean(B(a:k,:), 1);
%     end
% 
%     if any(~isfinite(S_cand)), continue; end
% 
%     d = S_cand - S_pre;
%     nd = norm(d,2);
% 
%     if useGate && nd > cfg.ref.D_upd
%         updLimited(k) = 1;
%         S_pre = S_pre + alpha * (cfg.ref.D_upd / max(nd, eps)) * d;
%     else
%         S_pre = (1-alpha)*S_pre + alpha*S_cand;
%     end
% end
% end
% 
% function segs = ch4_binary_to_segments(sig)
% sig = sig(:) > 0.5;
% d = diff([false; sig; false]);
% st = find(d==1);
% ed = find(d==-1) - 1;
% segs = [st ed];
% end
% 
% function segs = ch4_eventflag_to_segments(n, out, fieldName, halfWin)
% segs = zeros(0,2);
% if ~isfield(out,'events') || isempty(out.events), return; end
% if ~isfield(out,'dbg') || ~isfield(out.dbg, fieldName), return; end
% flag = out.dbg.(fieldName);
% mmax = min(numel(out.events), numel(flag));
% for m = 1:mmax
%     if ~flag(m), continue; end
%     k = round(out.events(m).k_out);
%     a = max(1, k-halfWin);
%     b = min(n, k+halfWin);
%     segs(end+1,:) = [a b]; %#ok<AGROW>
% end
% end
% 
% function segs = ch4_event_distkeep_segments(n, out, cfg, halfWin)
% % dist gate: dist < dist_th  (keep occupied)
% segs = zeros(0,2);
% if ~isfield(out,'events') || isempty(out.events), return; end
% if ~isfield(out,'dbg') || ~isfield(out.dbg,'dist'), return; end
% if ~isfield(cfg,'pk') || ~isfield(cfg.pk,'dist_th'), return; end
% 
% dist = out.dbg.dist(:);
% mmax = min(numel(out.events), numel(dist));
% for m = 1:mmax
%     if ~isfinite(dist(m)), continue; end
%     if dist(m) >= cfg.pk.dist_th, continue; end
%     k = round(out.events(m).k_out);
%     a = max(1, k-halfWin);
%     b = min(n, k+halfWin);
%     segs(end+1,:) = [a b]; %#ok<AGROW>
% end
% end
% 
% function vSeries = ch4_event_value_series(n, out, which)
% vSeries = nan(n,1);
% if ~isfield(out,'events') || isempty(out.events), return; end
% if ~isfield(out,'dbg') || ~isfield(out.dbg, which), return; end
% v = out.dbg.(which)(:);
% mmax = min(numel(out.events), numel(v));
% for m = 1:mmax
%     k = round(out.events(m).k_out);
%     if k>=1 && k<=n
%         vSeries(k) = v(m);
%     end
% end
% end
% 
% 
% 
% function k0 = pick_case_center_k(figTitle, relB, out, pred_k, gt_idx, cfg, centerMode)
% %PICK_CASE_CENTER_K Heuristic event-level window center selection.
% %
% % - A: center at GT arrival (occ_in)
% % - B: center at strongest internal disturbance event within GT occupancy
% % - C: center at first degrade/no-stable event (if available)
% % - D: center at max baseline drift (smoothed relB)
% % - otherwise: center at GT segment center (or mid-file)
% 
% n = numel(relB);
% k0 = round(n/2);
% 
% % Mode override
% if strcmpi(centerMode, 'midfile')
%     return;
% end
% 
% % Parse group tag from title
% groupTag = '';
% s = char(figTitle);
% tok = regexp(s, '([ABCD])类', 'tokens', 'once');
% if ~isempty(tok)
%     groupTag = tok{1};
% else
%     tok = regexp(s, '工况([ABCD])', 'tokens', 'once');
%     if ~isempty(tok)
%         groupTag = tok{1};
%     end
% end
% 
% % Select a representative GT segment (prefer max overlap with pred)
% occ_in = [];
% occ_out = [];
% if ~isempty(gt_idx)
%     if isempty(pred_k)
%         [~, jj] = max(gt_idx(:,2) - gt_idx(:,1));
%     else
%         ov = zeros(size(gt_idx,1),1);
%         for j = 1:size(gt_idx,1)
%             a = gt_idx(j,1); b = gt_idx(j,2);
%             for i = 1:size(pred_k,1)
%                 c = pred_k(i,1); d = pred_k(i,2);
%                 ov(j) = ov(j) + max(0, min(b,d) - max(a,c));
%             end
%         end
%         [~, jj] = max(ov);
%     end
%     occ_in  = gt_idx(jj,1);
%     occ_out = gt_idx(jj,2);
%     k0 = round((occ_in + occ_out)/2);
% end
% 
% % Heuristic per group
% switch upper(groupTag)
%     case 'A'
%         if ~isempty(occ_in)
%             k0 = occ_in;
%         end
% 
%     case 'B'
%         % strongest internal disturbance within occupancy (exclude near boundaries)
%         k0_best = k0;
%         bestScore = -inf;
%         if ~isempty(occ_in) && isfield(out,'events') && ~isempty(out.events) && isfield(out,'pr') && ~isempty(out.pr)
%             fs = cfg.fs;
%             guard = round(2*fs);
%             for m = 1:numel(out.events)
%                 c = round(0.5*(out.events(m).k_in + out.events(m).k_out));
%                 if c <= occ_in + guard || c >= occ_out - guard
%                     continue;
%                 end
%                 k1e = max(1, out.events(m).k_in);
%                 k2e = min(numel(out.pr), out.events(m).k_out);
%                 if k2e <= k1e, continue; end
%                 sc = max(out.pr(k1e:k2e));
%                 if sc > bestScore
%                     bestScore = sc;
%                     k0_best = c;
%                 end
%             end
%         end
%         k0 = k0_best;
% 
%     case 'C'
%         % first degrade / no-stable event if available
%         if isfield(out,'dbg') && ~isempty(out.dbg) && isfield(out.dbg,'used_degrade') && isfield(out.dbg,'stable_found') ...
%                 && isfield(out,'events') && ~isempty(out.events)
%             idx = find(out.dbg.used_degrade(:) | (~out.dbg.stable_found(:)), 1, 'first');
%             if ~isempty(idx) && idx <= numel(out.events)
%                 k0 = round(0.5*(out.events(idx).k_in + out.events(idx).k_out));
%             end
%         end
% 
%     case 'D'
%         % pick time where smoothed baseline deviation is largest (to highlight drift)
%         win = max(3, round(5*cfg.fs));
%         rel_s = movmean(relB, win, 'Endpoints','shrink');
%         [~, k0] = max(rel_s);
% 
%     otherwise
%         % keep default
% end
% 
% % Safety clamp
% k0 = max(1, min(n, k0));
% end
% 
% function add_interval_bars(ax, t, segs_k, k1, k2, y0, y1, faceColor, alpha)
% %ADD_INTERVAL_BARS Draw occupancy intervals as horizontal bars between y0..y1.
% 
% for ii = 1:size(segs_k,1)
%     a = segs_k(ii,1);
%     b = segs_k(ii,2);
%     if b < k1 || a > k2
%         continue;
%     end
%     aa = max(a, k1);
%     bb = min(b, k2);
%     x1 = t(aa);
%     x2 = t(bb);
%     patch(ax, [x1 x2 x2 x1], [y0 y0 y1 y1], faceColor, ...
%         'FaceAlpha', alpha, 'EdgeColor', 'none');
% end
% end
% 
% 
% function Tv = run_eval_only(files, GT, p, cfg, post, IOU_TH)
%     Tv = table('Size',[0 11], ...
%         'VariableTypes',{'string','string','double','double','double','double','double','double','double','double','double'}, ...
%         'VariableNames',{'file','group','TP','FP','FN','P','R','F1','events','pred','gt'});
% 
%     for i = 1:numel(files)
%         fileName = string(files(i));
%         gt_f = GT(GT.file == fileName, :);
%         group = string(gt_f.scenario_group(1));
%         csvPath = ch4_find_csv(fileName, p.root, p.synth);
% 
%         data = ch4_load_csv(csvPath, cfg.fs);
%         out  = ch4_run_parking_fsm(data, cfg);
% 
%         [pred_k, ~] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);
%         gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
%         res = ch4_eval(pred_k, gt_idx, IOU_TH);
% 
%         rowTable = table(fileName, group, res.TP, res.FP, res.FN, res.P, res.R, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), ...
%             'VariableNames', Tv.Properties.VariableNames);
%         Tv = [Tv; rowTable]; %#ok<AGROW>
%     end
% end
% 
% %% ================= LaTeX row writers =================
% 
% function write_tex_dataset_rows(T_ds, outPath)
% % T_ds: group, num_files, num_parking_gt, num_vehicle_events, num_pass_est
% descA = "正常车流单车停靠，稳定窗可得";
% descB = "占用伴随过车扰动（实测为主，含叠加增强）";
% descC = "连续车流或拥堵（稳定窗缺失，含拼接/增强）";
% descD = "慢漂移背景（实测为主，含漂移注入增强）";
% descALL = "全部数据";
% 
% % add ALL row
% nFiles = sum(T_ds.num_files);
% Ngt    = sum(T_ds.num_parking_gt);
% Npass  = sum(T_ds.num_pass_est);
% T_all = table("ALL", nFiles, Ngt, NaN, Npass, 'VariableNames', T_ds.Properties.VariableNames); %#ok<NASGU>
% 
% fid = fopen(outPath, 'w');
% assert(fid>0, "Cannot write %s", outPath);
% 
% for i = 1:height(T_ds)
%     g = string(T_ds.group(i));
%     switch g
%         case "A", desc = descA;
%         case "B", desc = descB;
%         case "C", desc = descC;
%         case "D", desc = descD;
%         otherwise, desc = "";
%     end
%     fprintf(fid, "%s & %d & %d & %d & %s \\\\\n", g, T_ds.num_files(i), T_ds.num_parking_gt(i), T_ds.num_pass_est(i), desc);
% end
% fprintf(fid, "ALL & %d & %d & %d & %s \\\\\n", nFiles, Ngt, Npass, descALL);
% 
% fclose(fid);
% end
% 
% function write_tex_bycase_rows(T_group, outPath)
% % Expected columns: group, TP, FP, FN, P, R, F1, Rf, Rm
% fid = fopen(outPath, 'w');
% assert(fid>0, "Cannot write %s", outPath);
% 
% for i = 1:height(T_group)
%     g = string(T_group.group(i));
%     P = T_group.P(i);
%     R = T_group.R(i);
%     F1 = T_group.F1(i);
%     Rf = 100 * T_group.Rf(i);
%     Rm = 100 * T_group.Rm(i);
%     FP = T_group.FP(i);
%     FN = T_group.FN(i);
%     fprintf(fid, "%s & %.3f & %.3f & %.3f & %.1f & %.1f & (%d,%d) \\\\\n", g, P, R, F1, Rf, Rm, FP, FN);
% end
% 
% fclose(fid);
% end
% 
% function write_tex_timing_rows(T_timing, outPath)
% % Columns: group, N_TP, med_abs_dt_in, med_abs_dt_out, med_tau_in, med_tau_out, p95_tau_in, p95_tau_out
% fid = fopen(outPath, 'w');
% assert(fid>0, "Cannot write %s", outPath);
% 
% for i = 1:height(T_timing)
%     g = string(T_timing.group(i));
%     N = T_timing.N_TP(i);
%     a = T_timing.med_abs_dt_in(i);
%     b = T_timing.med_abs_dt_out(i);
%     c = T_timing.med_tau_in(i);
%     d = T_timing.med_tau_out(i);
%     p95 = T_timing.p95_tau_in(i);
%     fprintf(fid, "%s & %d & %.2f & %.2f & %.2f & %.2f & %.2f \\\\\n", g, N, a, b, c, d, p95);
% end
% 
% fclose(fid);
% end
% 
% function write_tex_ablation_rows(T_ab, outPath)
% % T_ab: variant, F1_all, F1_A, F1_B, F1_C, F1_D, TP_all
% % We also add a brief "phenomenon" column.
% fid = fopen(outPath, 'w');
% assert(fid>0, "Cannot write %s", outPath);
% 
% for i = 1:height(T_ab)
%     v = string(T_ab.variant(i));
%     switch v
%         case "Ours"
%             label = "Ours-full";
%             phen  = "完整模型";
%         case "Abl_noMeanDiff"
%             label = "Abl-1（去除$M$）";
%             phen  = "伪稳态误触发增多，误检上升";
%         case "Abl_noSimilarity"
%             label = "Abl-2（去除$\mathrm{dist}$）";
%             phen  = "占用态过车后误释放或重复占用";
%         case "Abl_noDegrade"
%             label = "Abl-3（去除退化分支）";
%             phen  = "拥堵下寻稳失败导致漏检与延迟增大";
%         case "Abl_noUpdateGate"
%             label = "Abl-4（去除更新门控）";
%             phen  = "慢漂移背景下参考误更新，产生连锁误判";
%         otherwise
%             label = v;
%             phen  = "";
%     end
%     fprintf(fid, "%s & %.3f & %.3f & %.3f & %.3f & %.3f & %s \\\\\n", ...
%         label, T_ab.F1_all(i), T_ab.F1_A(i), T_ab.F1_B(i), T_ab.F1_C(i), T_ab.F1_D(i), phen);
% end
% 
% fclose(fid);
% end
% 
% %% ================= Figure utilities (thesis-ready) =================
% 
% function make_thesis_figures(rep, cfg, p, figOpt)
% %MAKE_THESIS_FIGURES Generate figures that match Chapter-4 LaTeX placeholders.
% % Figures are written into p.images_dir.
% %
% % This function is intentionally conservative:
% %   - Data-driven figures (wave/case/stability/param) are overwritten.
% %   - Conceptual schematics (pipeline/FSM) are only created if missing,
% %     so manual replacement will not be overwritten by reruns.
% 
%     % ---- Waveform examples for four groups ----
%     groups = {'A','B','C','D'};
% 
%     % 说明：原始三轴波形不适合做“四类横向对比主图”（偏置/尺度差导致差异不显著）。
%     % 若需要示例，可打开该开关生成备用图；正文建议仅挑 1 张最能支撑论证的样例即可。
%     if isfield(figOpt, 'make_wave_groups') && figOpt.make_wave_groups
%         for ii = 1:numel(groups)
%             g = groups{ii};
%             if ~isempty(rep.(g))
%                 figPath = fullfile(p.images_dir, ['ch4_wave_' g '.pdf']);
%                 plot_wave_group(rep.(g).data, rep.(g).out, rep.(g).pred_k, rep.(g).gt_idx, g, figPath, cfg);
%             end
%         end
%     end
% 
%     % ---- Stability demo (use group A if available, else first available group) ----
%     g0 = '';
%     for ii = 1:numel(groups)
%         if ~isempty(rep.(groups{ii}))
%             g0 = groups{ii};
%             break;
%         end
%     end
%     if ~isempty(g0)
%         figPath = fullfile(p.images_dir, 'ch4_stability_demo.pdf');
%         plot_stability_demo(rep.(g0).data, rep.(g0).out, rep.(g0).gt_idx, g0, figPath, cfg);
%     end
% 
%     % ---- Pass vs Park example (use group A if possible) ----
%     if ~isempty(rep.A)
%         figPath = fullfile(p.images_dir, 'ch4_pass_vs_park.pdf');
%         plot_pass_vs_park(rep.A.data, rep.A.out, rep.A.gt_idx, figPath, cfg);
%     end
% 
%     % ---- Conceptual schematics ----
%     % Always create *_auto.* for selection (won't conflict with manual diagrams).
%     figPipe = fullfile(p.images_dir, 'ch4_pipeline.pdf');
%     figPipeAuto = fullfile(p.images_dir, 'ch4_pipeline_auto.pdf');
%     if figOpt.always_make_auto_schematics
%         plot_pipeline_schematic(figPipeAuto);
%         if (exist(figPipe,'file') ~= 2) || figOpt.force_overwrite_schematics
%             ch4_copy_figpair(figPipeAuto, figPipe);
%         end
%     else
%         if exist(figPipe,'file') ~= 2
%             plot_pipeline_schematic(figPipe);
%         end
%     end
% 
%     figFsm = fullfile(p.images_dir, 'ch4_fsm_degrade.pdf');
%     figFsmAuto = fullfile(p.images_dir, 'ch4_fsm_degrade_auto.pdf');
%     if figOpt.always_make_auto_schematics
%         plot_fsm_schematic(figFsmAuto);
%         if (exist(figFsm,'file') ~= 2) || figOpt.force_overwrite_schematics
%             ch4_copy_figpair(figFsmAuto, figFsm);
%         end
%     else
%         if exist(figFsm,'file') ~= 2
%             plot_fsm_schematic(figFsm);
%         end
%     end
% 
%     % ---- Manual figures (optional placeholders) ----
%     if isfield(figOpt,'make_placeholders') && figOpt.make_placeholders
%         figScene = fullfile(p.images_dir, 'ch4_scene_photo.pdf');
%         if exist(figScene,'file') ~= 2
%             ch4_make_placeholder(figScene, '现场照片占位', {'请替换为：道路监测场景照片', '（应急车道/路肩 + 邻道车流）'});
%         end
%         figSetup = fullfile(p.images_dir, 'ch4_setup_schematic.pdf');
%         if exist(figSetup,'file') ~= 2
%             ch4_make_placeholder(figSetup, '布设示意占位', {'请替换为：传感器布设与坐标定义示意图', '（含 x/y/z 方向与车道关系）'});
%         end
%     end
% end
% 
% function plot_wave_group(data, out, pred_k, gt_idx, groupName, figPath, cfg, varargin)
% %PLOT_WAVE_GROUP  Plot representative waveform for a scenario group
% %
% % Changes vs v5:
% %   1) Automatically select a more representative GT interval (not always gt_idx(1,:)).
% %   2) Use group-specific default padding (B/C larger, D much larger).
% %   3) Add an extra panel for disturbance score pr(k) to make B/C differences visible.
% %
% % Optional:
% %   'pad' : padding seconds (override defaults)
% 
% % --- parse optional padding ---
% padSec = [];
% if ~isempty(varargin)
%     if isnumeric(varargin{1})
%         padSec = varargin{1};
%         varargin = varargin(2:end);
%     end
% end
% 
% p = inputParser;
% addParameter(p, 'pad', [], @(x) isempty(x) || (isscalar(x) && x >= 0));
% parse(p, varargin{:});
% 
% if isempty(padSec)
%     padSec = p.Results.pad;
% end
% 
% % --- default padding by group ---
% if isempty(padSec)
%     switch upper(string(groupName))
%         case "A"
%             padSec = 8;
%         case "B"
%             padSec = 20;
%         case "C"
%             padSec = 20;
%         case "D"
%             padSec = 90;  % drift needs longer horizon
%         otherwise
%             padSec = 8;
%     end
% end
% 
% % --- select GT interval (row) for this figure ---
% gtSel = [];
% gtSelIdx = 1;
% gtStat = struct('nEv', NaN, 'stableRatio', NaN, 'prMean', NaN, 'driftScore', NaN);
% if ~isempty(gt_idx)
%     [gtSel, gtSelIdx, gtStat] = ch4_select_gt_for_wave(data, out, gt_idx, groupName, cfg);
% end
% 
% % --- determine plotting window ---
% n = numel(data.k);
% if ~isempty(gtSel)
%     k_center_1 = gtSel(1);
%     k_center_2 = gtSel(2);
% elseif ~isempty(pred_k)
%     % fallback: first predicted interval
%     k_center_1 = pred_k(1,1);
%     k_center_2 = pred_k(1,2);
% else
%     k_center_1 = 1;
%     k_center_2 = n;
% end
% 
% pad = max(0, round(padSec * cfg.fs));
% k1 = max(1, k_center_1 - pad);
% k2 = min(n, k_center_2 + pad);
% 
% t = data.t(k1:k2);
% B = data.B(k1:k2, :);
% 
% % stability flag and disturbance score
% stable = out.st.stableState(k1:k2);
% pr = out.pr(k1:k2);
% 
% % --- prepare event markers in this window ---
% ev_out = [];
% ev_in = [];
% if ~isempty(out.events)
%     ev_in = [out.events.k_in]';
%     ev_out = [out.events.k_out]';
%     keep = (ev_out >= k1) & (ev_in <= k2);
%     ev_in = ev_in(keep);
%     ev_out = ev_out(keep);
% end
% 
% % --- figure ---
% fig = ch4_newfig(16, 14);
% tl = tiledlayout(5, 1, 'TileSpacing','compact','Padding','compact');
% 
% % --- 1) Bx ---
% ax1 = nexttile;
% plot(t, B(:,1), 'LineWidth', 1);
% ylabel('$B_x$', 'Interpreter','latex');
% hold on; grid on;
% 
% % --- 2) By ---
% ax2 = nexttile;
% plot(t, B(:,2), 'LineWidth', 1);
% ylabel('$B_y$', 'Interpreter','latex');
% hold on; grid on;
% 
% % --- 3) Bz ---
% ax3 = nexttile;
% plot(t, B(:,3), 'LineWidth', 1);
% ylabel('$B_z$', 'Interpreter','latex');
% hold on; grid on;
% 
% % --- 4) pr(k) (disturbance score) ---
% ax4 = nexttile;
% plot(t, pr, 'LineWidth', 1);
% ylim([0, 1]);
% ylabel('扰动得分');
% hold on; grid on;
% 
% % thresholds used by event detector (optional reference)
% try
%     yline(cfg.ev.theta_arrive, '--', 'arrive', 'LabelHorizontalAlignment','left', 'LabelVerticalAlignment','bottom');
%     yline(cfg.ev.theta_leave,  '--', 'leave',  'LabelHorizontalAlignment','left', 'LabelVerticalAlignment','top');
% catch
% end
% 
% % --- 5) stable flag ---
% ax5 = nexttile;
% plot(t, stable, 'LineWidth', 1);
% ylim([-0.05, 1.05]);
% ylabel('稳定标志');
% xlabel('时间/s');
% hold on; grid on;
% 
% % --- patches (predicted & selected GT) ---
% axs = [ax1 ax2 ax3 ax4 ax5];
% 
% for i = 1:numel(axs)
%     ax = axs(i);
% 
%     % predicted occupied intervals
%     if ~isempty(pred_k)
%         for j = 1:size(pred_k,1)
%             kk = pred_k(j,:);
%             if kk(2) < k1 || kk(1) > k2
%                 continue;
%             end
%             kk2 = [max(k1,kk(1)) min(k2,kk(2))];
%             tt2 = data.t(kk2);
%             ch4_patch_interval_time(ax, tt2, [0.0 0.6 0.0], 0.08);
%         end
%     end
% 
%     % selected GT interval (for this figure)
%     if ~isempty(gtSel)
%         kk = gtSel;
%         kk2 = [max(k1,kk(1)) min(k2,kk(2))];
%         tt2 = data.t(kk2);
%         ch4_patch_interval_time(ax, tt2, [0.2 0.2 1.0], 0.10);
%     end
% end
% 
% % --- event markers: draw on pr/stable panels (avoid clutter on B axes) ---
% if ~isempty(ev_out)
%     for i = 1:numel(ev_out)
%         tt_in = data.t(ev_in(i));
%         tt_out = data.t(ev_out(i));
%         xline(ax4, tt_in, ':', 'Color', [0.85 0.33 0.10], 'LineWidth', 0.8);
%         xline(ax4, tt_out, ':', 'Color', [0.85 0.33 0.10], 'LineWidth', 0.8);
%         xline(ax5, tt_out, ':', 'Color', [0.85 0.33 0.10], 'LineWidth', 0.8);
%     end
% end
% 
% % --- title with stats (helps distinguish groups visually) ---
% if ~isempty(gtSel)
%     ttl = sprintf('%s类波形示例（GT#%d，N_{ev}=%d，stable=%.2f，pr=%.3f）', ...
%         upper(char(groupName)), gtSelIdx, gtStat.nEv, gtStat.stableRatio, gtStat.prMean);
%     if upper(string(groupName)) == "D"
%         ttl = sprintf('%s，drift=%.2f', ttl, gtStat.driftScore);
%     end
% else
%     ttl = sprintf('%s类波形示例', upper(char(groupName)));
% end
% title(tl, ttl, 'FontWeight','normal');
% 
% ch4_apply_style(fig);
% 
% ch4_export_fig(fig, figPath);
% close(fig);
% end
% 
% function [gtSel, idxSel, statSel] = ch4_select_gt_for_wave(data, out, gt_idx, groupName, cfg)
% %CH4_SELECT_GT_FOR_WAVE  Pick a more representative GT interval for plotting.
% %
% % gt_idx : [N x 2] (sample indices, inclusive)
% % Strategy:
% %   A: prefer stable, few disturbances
% %   B: prefer more disturbances during occupied interval
% %   C: prefer unstable / high disturbance density
% %   D: prefer larger baseline drift around the interval (long window)
% 
% nGT = size(gt_idx, 1);
% n = numel(data.k);
% 
% % event list
% ev_in = [];
% ev_out = [];
% if ~isempty(out.events)
%     ev_in = [out.events.k_in]';
%     ev_out = [out.events.k_out]';
% end
% 
% nEv = zeros(nGT,1);
% stableRatio = zeros(nGT,1);
% prMean = zeros(nGT,1);
% driftScore = zeros(nGT,1);
% 
% % drift estimation window (seconds)
% winSec = 30;
% win = max(1, round(winSec * cfg.fs));
% 
% for i = 1:nGT
%     g1 = max(1, gt_idx(i,1));
%     g2 = min(n, gt_idx(i,2));
%     if g2 < g1
%         continue;
%     end
% 
%     % count events overlapping this GT interval
%     if ~isempty(ev_in)
%         overlap = ~(ev_out < g1 | ev_in > g2);
%         nEv(i) = sum(overlap);
%     else
%         nEv(i) = 0;
%     end
% 
%     % stable ratio inside GT
%     stableRatio(i) = mean(out.st.stableState(g1:g2));
% 
%     % average disturbance score inside GT
%     prMean(i) = mean(out.pr(g1:g2));
% 
%     % drift score (difference of mean baseline before/after GT)
%     pre1 = max(1, g1 - win);
%     pre2 = max(1, g1 - 1);
%     post1 = min(n, g2 + 1);
%     post2 = min(n, g2 + win);
%     if pre2 >= pre1 && post2 >= post1
%         preMu = mean(data.B(pre1:pre2, :), 1);
%         postMu = mean(data.B(post1:post2, :), 1);
%         driftScore(i) = norm(postMu - preMu);
%     else
%         driftScore(i) = 0;
%     end
% end
% 
% % scoring
% g = upper(string(groupName));
% switch g
%     case "A"
%         % stable and clean
%         score = 2.0*stableRatio - 0.6*nEv - 0.5*prMean;
%     case "B"
%         % occupied with pass disturbances
%         score = 1.2*nEv + 1.0*prMean + 0.3*stableRatio;
%     case "C"
%         % continuous traffic: unstable + many disturbances
%         score = 1.5*nEv + 1.2*prMean + 2.0*(1.0 - stableRatio);
%     case "D"
%         % drift background: choose interval with larger baseline drift
%         score = 2.0*driftScore + 0.2*nEv;
%     otherwise
%         score = nEv + prMean;
% end
% 
% [~, idxSel] = max(score);
% gtSel = gt_idx(idxSel, :);
% 
% statSel = struct();
% statSel.nEv = nEv(idxSel);
% statSel.stableRatio = stableRatio(idxSel);
% statSel.prMean = prMean(idxSel);
% statSel.driftScore = driftScore(idxSel);
% end
% 
% 
% function ch4_patch_interval_time(ax, t12, rgb, alphaVal)
% %CH4_PATCH_INTERVAL_TIME  Draw a vertical patch between t12(1)~t12(2) on axes ax.
% % Note: ylim(ax) is used as patch vertical span.
% 
% if isempty(t12) || numel(t12) < 2
%     return;
% end
% 
% y = ylim(ax);
% h = patch(ax, [t12(1) t12(2) t12(2) t12(1)], [y(1) y(1) y(2) y(2)], rgb, ...
%     'FaceAlpha', alphaVal, 'EdgeColor','none');
% try
%     uistack(h, 'bottom');
% catch
% end
% end
% 
% 
% function plot_stability_demo(data, out, gt_idx, groupName, figPath, cfg)
% %PLOT_STABILITY_DEMO R/M curves and thresholds + stable flag (for the thesis figure).
% 
%     t = data.t(:);
%     n = numel(t);
%     fs = cfg.fs;
% 
%     pad = round(8*fs);
%     if ~isempty(gt_idx)
%         k1 = max(1, gt_idx(1,1) - pad);
%         k2 = min(n, gt_idx(1,2) + pad);
%     else
%         k1 = 1; k2 = min(n, 25*fs);
%     end
%     idx = k1:k2;
% 
%     R = out.st.R(:);
%     M = out.st.M(:);
%     st = out.st.stableState(:);
% 
%     fig = ch4_newfig(16, 10);
%     tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
% 
%     ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
%     plot(ax1, t(idx), R(idx), 'LineWidth', 1.0);
%     yline_if(ax1, cfg.st.R_th, '--', sprintf('R_{th}=%.1f', cfg.st.R_th));
%     add_mask_shading(ax1, t, st, k1, k2, [0.85 0.85 0.85], 0.15);
%     ylabel(ax1, '窗内波动 R(k)');
%     title(ax1, sprintf('稳定判据示意（%s类）', groupName), 'FontWeight','normal');
% 
%     ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
%     plot(ax2, t(idx), M(idx), 'LineWidth', 1.0);
%     yline_if(ax2, cfg.st.M_th, '--', sprintf('M_{th}=%.1f', cfg.st.M_th));
%     add_mask_shading(ax2, t, st, k1, k2, [0.85 0.85 0.85], 0.15);
%     xlabel(ax2, '时间/s'); ylabel(ax2, '窗间水平差 M(k)');
% 
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, figPath);
%     close(fig);
% end
% 
% function plot_pass_vs_park(data, out, gt_idx, figPath, cfg)
% %PLOT_PASS_VS_PARK Side-by-side comparison: a pass event vs a parking-arrival event.
% 
%     if isempty(out.events)
%         return;
%     end
% 
%     fs = cfg.fs;
%     t = data.t(:);
%     B = data.B;
%     F = sqrt(sum(B.^2,2));
%     dB = [0; sqrt(sum(diff(B,1,1).^2,2))];
% 
%     % match event indices to GT arrival/leave (by k_out proximity)
%     [arrIdx, leaveIdx] = match_events_to_gt(out.events, gt_idx, round(2.0*fs));
%     if isempty(arrIdx)
%         return;
%     end
%     park_m = arrIdx(1);
% 
%     allIdx = 1:numel(out.events);
%     passCand = setdiff(allIdx, unique([arrIdx(:); leaveIdx(:)]));
%     if isempty(passCand)
%         pass_m = park_m; % fallback
%     else
%         pass_m = passCand(1);
%     end
% 
%     [k1p, k2p] = event_window(out.events(pass_m), numel(t), round(3*fs));
%     [k1k, k2k] = event_window(out.events(park_m), numel(t), round(3*fs));
% 
%     fig = ch4_newfig(16, 10);
%     tl = tiledlayout(fig, 2, 2, 'TileSpacing','compact', 'Padding','compact');
% 
%     % ---- Pass: magnitude ----
%     ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
%     plot(ax1, t(k1p:k2p), F(k1p:k2p), 'LineWidth', 1.0);
%     add_interval_patches(ax1, t, [out.events(pass_m).k_in, out.events(pass_m).k_out], k1p, k2p, [0.85 0.85 0.85], 0.35);
%     title(ax1, '通过事件：||B||_2', 'FontWeight','normal');
%     ylabel(ax1, '磁场幅值 ||B||_2');
% 
%     % ---- Park: magnitude ----
%     ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
%     plot(ax2, t(k1k:k2k), F(k1k:k2k), 'LineWidth', 1.0);
%     add_interval_patches(ax2, t, [out.events(park_m).k_in, out.events(park_m).k_out], k1k, k2k, [0.75 0.85 1.00], 0.30);
%     title(ax2, '停车到达事件：||B||_2', 'FontWeight','normal');
% 
%     % ---- Pass: diff magnitude ----
%     ax3 = nexttile(tl, 3); hold(ax3,'on'); grid(ax3,'on');
%     plot(ax3, t(k1p:k2p), dB(k1p:k2p), 'LineWidth', 1.0);
%     add_interval_patches(ax3, t, [out.events(pass_m).k_in, out.events(pass_m).k_out], k1p, k2p, [0.85 0.85 0.85], 0.35);
%     xlabel(ax3, '时间/s'); ylabel(ax3, '差分幅值 ||\Delta B||_2');
% 
%     % ---- Park: diff magnitude ----
%     ax4 = nexttile(tl, 4); hold(ax4,'on'); grid(ax4,'on');
%     plot(ax4, t(k1k:k2k), dB(k1k:k2k), 'LineWidth', 1.0);
%     add_interval_patches(ax4, t, [out.events(park_m).k_in, out.events(park_m).k_out], k1k, k2k, [0.75 0.85 1.00], 0.30);
%     xlabel(ax4, '时间/s');
% 
%     title(tl, '通过 vs 停靠对比', 'FontWeight','normal');
% 
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, figPath);
%     close(fig);
% end
% 
% 
% function plot_pipeline_schematic(figPath)
% %PLOT_PIPELINE_SCHEMATIC  Chapter-4 method pipeline schematic (for thesis figures).
% %
% %  说明：该图尽量避免把文本/箭头画到画布边缘之外，否则 exportgraphics 的裁剪会截断文字。
% %  如需进一步美化，建议最终版本改用 TikZ/draw.io 手工重画。
% 
%     fig = ch4_newfig(18, 4.8);
%     ax = axes(fig); %#ok<NASGU>
%     axis([0 1 0 1]); axis off; hold on;
% 
%     % Layout parameters (normalized figure coordinates)
%     margin = 0.05;
%     gap = 0.02;
%     n = 5;
%     w = (1 - 2*margin - (n-1)*gap) / n;
%     y = 0.22;
%     h = 0.56;
% 
%     xs = margin + (0:n-1) * (w + gap);
% 
%     % Box + text style
%     boxStyle = {'LineWidth', 1.0, 'EdgeColor', [0.15 0.15 0.15], 'FaceColor', [1 1 1]};
%     txtStyle = {'LineStyle','none', 'HorizontalAlignment','center', 'VerticalAlignment','middle', ...
%         'FontSize', 11, 'FontName', 'Microsoft YaHei', 'Interpreter','tex'};
% 
%     labels = { ...
%         {'输入：事件片段', '(diff\_on / diff\_off)'}; ...
%         {'预处理与稳定窗判定', 'R(k), M(k), f\_st(k)'}; ...
%         {'稳定点提取 / 动态参考', 'S\_pre, S\_post'}; ...
%         {'漂移 / 相似性判定', 'ΔB, dist'}; ...
%         {'输出：停车/占用语义', 'park\_flag, occ\_flag'} ...
%     };
% 
%     boxes = zeros(n,4);
%     for i = 1:n
%         boxes(i,:) = [xs(i) y w h];
%         annotation(fig,'rectangle', boxes(i,:), boxStyle{:});
%         annotation(fig,'textbox', boxes(i,:), 'String', labels{i}, txtStyle{:});
%     end
% 
%     % Arrows between boxes (centerline)
%     for i = 1:n-1
%         x1 = boxes(i,1) + boxes(i,3);
%         x2 = boxes(i+1,1);
%         yc = y + h/2;
%         annotation(fig,'arrow', [x1 x2], [yc yc], 'LineWidth', 1.0, ...
%             'HeadLength', 6, 'HeadWidth', 6);
%     end
% 
%     % Small notes (keep inside canvas)
%     annotation(fig,'textbox', [margin 0.06 1-2*margin 0.12], 'LineStyle','none', ...
%         'HorizontalAlignment','center', 'VerticalAlignment','middle', 'FontSize', 9, ...
%         'FontName', 'Microsoft YaHei', 'Interpreter','tex', ...
%         'String', '注：diff\_off 后在 T\_seek 内寻稳；稳定窗不可得时进入固定窗+一致性计数退化分支。');
% 
%     ch4_apply_style(fig);
%     ch4_save_pdf_png(fig, figPath);
%     close(fig);
% end
% 
% 
% function plot_fsm_schematic(figPath)
% %PLOT_FSM_SCHEMATIC  Clean FSM + degrade schematic for Chapter-4.
% %
% %  说明：优先保证图面“可读”和“不裁剪”。若需要更高的出版级质量，建议用 TikZ 重画。
% 
%     fig = ch4_newfig(16, 7.6);
%     ax = axes(fig); %#ok<NASGU>
%     axis([0 1 0 1]); axis off; hold on;
% 
%     boxStyle = {'LineWidth', 1.0, 'EdgeColor', [0.15 0.15 0.15], 'FaceColor', [1 1 1]};
%     txtStyle = {'LineStyle','none', 'HorizontalAlignment','center', 'VerticalAlignment','middle', ...
%         'FontSize', 10, 'FontName', 'Microsoft YaHei', 'Interpreter','tex'};
% 
%     % 2×2 layout avoids long diagonal arrows and reduces clutter
%     w = 0.34; h = 0.20;
%     P.FREE  = [0.10 0.70 w h];
%     P.CPARK = [0.56 0.70 w h];
%     P.OCC   = [0.56 0.30 w h];
%     P.CREL  = [0.10 0.30 w h];
% 
%     % Draw state boxes
%     annotation(fig,'rectangle', P.FREE,  boxStyle{:});
%     annotation(fig,'textbox',   P.FREE,  'String', {'FREE 空闲','更新环境参考 S\_pre'}, txtStyle{:});
% 
%     annotation(fig,'rectangle', P.CPARK, boxStyle{:});
%     annotation(fig,'textbox',   P.CPARK, 'String', {'CAND\_PARK 候选停车','寻稳/退化确认'}, txtStyle{:});
% 
%     annotation(fig,'rectangle', P.OCC,   boxStyle{:});
%     annotation(fig,'textbox',   P.OCC,   'String', {'OCCUPIED 占用','冻结占用参考 S\_post'}, txtStyle{:});
% 
%     annotation(fig,'rectangle', P.CREL,  boxStyle{:});
%     annotation(fig,'textbox',   P.CREL,  'String', {'CAND\_RELEASE 候选释放','回归/退化确认'}, txtStyle{:});
% 
%     % Main cycle arrows: FREE -> CPARK -> OCC -> CREL -> FREE
%     yTop = P.FREE(2) + P.FREE(4)/2;
%     annotation(fig,'arrow', [P.FREE(1)+P.FREE(3) P.CPARK(1)], [yTop yTop], ...
%         'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
%     annotation(fig,'textbox', [0.30 0.88 0.40 0.08], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
%         'HorizontalAlignment','center', 'FontSize', 9, 'Interpreter','tex', ...
%         'String', 'diff\_off 触发 → 进入候选停车');
% 
%     xR = P.CPARK(1) + P.CPARK(3)/2;
%     annotation(fig,'arrow', [xR xR], [P.CPARK(2) P.OCC(2)+P.OCC(4)], ...
%         'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
%     annotation(fig,'textbox', [0.74 0.56 0.24 0.12], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
%         'HorizontalAlignment','left', 'FontSize', 9, 'Interpreter','tex', ...
%         'String', {'确认停车：','ΔB > D\_th','或退化计数'} );
% 
%     yBot = P.OCC(2) + P.OCC(4)/2;
%     annotation(fig,'arrow', [P.OCC(1) P.CREL(1)+P.CREL(3)], [yBot yBot], ...
%         'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
%     annotation(fig,'textbox', [0.18 0.22 0.46 0.10], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
%         'HorizontalAlignment','left', 'FontSize', 9, 'Interpreter','tex', ...
%         'String', {'占用内干扰：dist < dist\_th ⇒ 仍占用'} );
% 
%     xL = P.CREL(1) + P.CREL(3)/2;
%     annotation(fig,'arrow', [xL xL], [P.CREL(2)+P.CREL(4) P.FREE(2)], ...
%         'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
%     annotation(fig,'textbox', [0.00 0.48 0.28 0.14], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
%         'HorizontalAlignment','left', 'FontSize', 9, 'Interpreter','tex', ...
%         'String', {'确认释放：','||S\_new-S\_pre|| < D\_free','或退化计数'} );
% 
%     % Fail-back arrow: CPARK -> FREE (timeout / drift too small)
%     yFB = P.FREE(2) + P.FREE(4)*0.85;
%     annotation(fig,'arrow', [P.CPARK(1) P.FREE(1)+P.FREE(3)], [yFB yFB], ...
%         'LineWidth', 1.0, 'LineStyle','--', 'HeadLength', 6, 'HeadWidth', 6);
%     annotation(fig,'textbox', [0.30 0.80 0.40 0.08], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
%         'HorizontalAlignment','center', 'FontSize', 9, 'Interpreter','tex', ...
%         'String', '寻稳超时 / 漂移不足 → 回到 FREE');
% 
%     % Degrade note (keep short)
%     annotation(fig,'textbox', [0.18 0.06 0.64 0.10], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
%         'HorizontalAlignment','center', 'FontSize', 9, 'Interpreter','tex', ...
%         'String', '退化分支：稳定窗不可得时，使用固定窗均值 + 一致性计数器完成确认。');
% 
%     ch4_apply_style(fig);
%     ch4_save_pdf_png(fig, figPath);
%     close(fig);
% end
% 
% function ch4_apply_style(fig)
% %CH4_APPLY_STYLE Apply a consistent academic style to a MATLAB figure.
%     set(fig, 'Color','w');
% 
%     axs = findall(fig, 'Type','axes');
%     for i = 1:numel(axs)
%         ax = axs(i);
%         ax.Box = 'on';
%         ax.LineWidth = 0.8;
%         ax.FontName = 'Microsoft YaHei';
%         ax.FontSize = 10;
%         ax.GridAlpha = 0.15;
%         ax.MinorGridAlpha = 0.08;
%     end
% 
%     lgs = findall(fig, 'Type','legend');
%     for i = 1:numel(lgs)
%         lg = lgs(i);
%         lg.Box = 'off';
%         lg.FontName = 'Microsoft YaHei';
%         lg.FontSize = 9;
%     end
% end
% 
% function ch4_save_pdf_png(fig, figPath)
% %CH4_SAVE_PDF_PNG Backward-compatible wrapper (older helper name).
% % Some schematic plotters call this function; we route to ch4_export_fig.
%     ch4_export_fig(fig, figPath);
% end
% 
% function ch4_export_fig(h, outPath)
% %CH4_EXPORT_FIG Export figure: if you pass a .pdf path, also export a same-name .png.
% %  - h can be an axes or figure handle; this function always exports the whole figure
% %    to preserve titles/labels/colorbars (avoid over-tight cropping).
% %  - PDF: vector (preferred for LaTeX)
% %  - PNG: 300 dpi (convenient for Word / quick insertion)
% 
% if isstring(outPath)
%     outPath = char(outPath);
% end
% 
% [p, name, ext] = fileparts(outPath);
% if isempty(ext)
%     ext = '.pdf';
%     outPath = fullfile(p, [name ext]);
% end
% 
% if ~isempty(p) && ~exist(p, 'dir')
%     mkdir(p);
% end
% 
% pdfPath = '';
% pngPath = '';
% 
% if strcmpi(ext, '.pdf')
%     pdfPath = outPath;
%     pngPath = fullfile(p, [name '.png']);
% elseif strcmpi(ext, '.png')
%     pngPath = outPath;
%     pdfPath = fullfile(p, [name '.pdf']); % symmetric: also save pdf
% else
%     % unknown extension -> treat as png
%     pngPath = outPath;
% end
% 
% % Always export the whole figure (avoid axis-only tight crop)
% if isgraphics(h, 'figure')
%     fig = h;
% else
%     fig = ancestor(h, 'figure');
%     if isempty(fig)
%         fig = gcf;
%     end
% end
% 
% try
%     set(fig, 'InvertHardcopy', 'off');
% catch
% end
% 
% % --- Ensure paper size matches figure size (prevents PDF clipping when using print) ---
% try
%     oldUnits = get(fig, 'Units');
%     set(fig, 'Units', 'inches');
%     pos = get(fig, 'Position');  % [left bottom width height] in inches
%     set(fig, 'PaperUnits', 'inches');
%     set(fig, 'PaperSize', [pos(3) pos(4)]);
%     set(fig, 'PaperPosition', [0 0 pos(3) pos(4)]);
%     set(fig, 'PaperPositionMode', 'manual');
%     set(fig, 'Units', oldUnits);
% catch
% end
% 
% try
%     set(fig, 'InvertHardcopy', 'off');
% catch
% end
% 
% hasExport = (exist('exportgraphics', 'file') == 2);
% 
% % 1) PDF (vector)
% if ~isempty(pdfPath)
%     if hasExport
%         try
%             exportgraphics(fig, pdfPath, 'ContentType', 'vector', 'BackgroundColor', 'white');
%         catch
%             try
%                 print(fig, pdfPath, '-dpdf', '-painters');
%             catch
%                 print(fig, pdfPath, '-dpdf');
%             end
%         end
%     else
%         try
%                 print(fig, pdfPath, '-dpdf', '-painters');
%             catch
%                 print(fig, pdfPath, '-dpdf');
%             end
%     end
% end
% 
% % 2) PNG (raster, keep full figure canvas; do not use getframe/axis crop)
% if ~isempty(pngPath)
%     if hasExport
%         try
%             exportgraphics(fig, pngPath, 'Resolution', 300, 'BackgroundColor', 'white');
%             return;
%         catch
%             % fall back to print
%         end
%     end
% 
%     oldRenderer = '';
%     try
%         oldRenderer = get(fig, 'Renderer');
%         set(fig, 'Renderer', 'opengl');
%     catch
%     end
%     try
%         print(fig, pngPath, '-dpng', '-r300');
%     catch
%     end
%     try
%         if ~isempty(oldRenderer)
%             set(fig, 'Renderer', oldRenderer);
%         end
%     catch
%     end
% end
% end
% 
% 
% function edges = ch4_hist_edges(v, nBins)
% %CH4_HIST_EDGES Robust histogram edges for degenerate distributions.
%     v = v(:);
%     v = v(isfinite(v));
%     if isempty(v)
%         edges = linspace(0, 1, nBins+1);
%         return;
%     end
%     vmin = min(v);
%     vmax = max(v);
%     if vmax <= vmin
%         vmin = vmin - 0.5;
%         vmax = vmax + 0.5;
%     end
%     edges = linspace(vmin, vmax, nBins+1);
% end
% 
% function yline_if(ax, y, style, labelStr)
% %YLINE_IF Use yline if available, otherwise plot a horizontal line.
%     if exist('yline','file') == 2
%         h = yline(ax, y, style, labelStr);
%         h.LineWidth = 1.0;
%     else
%         xl = xlim(ax);
%         plot(ax, xl, [y y], style, 'LineWidth', 1.0);
%         xlim(ax, xl);
%     end
% end
% 
% function add_interval_patches(ax, t, segs_k, k1, k2, faceColor, alpha)
% %ADD_INTERVAL_PATCHES Draw shaded intervals on an axis.
% % segs_k: Nx2 [k_in, k_out] (sample indices)
% 
%     if isempty(segs_k)
%         return;
%     end
%     if size(segs_k,2) ~= 2
%         return;
%     end
% 
%     yl = ylim(ax);
% 
%     for j = 1:size(segs_k,1)
%         a = max(k1, segs_k(j,1));
%         b = min(k2, segs_k(j,2));
%         if ~isfinite(a) || ~isfinite(b) || b <= a
%             continue;
%         end
%         a = max(1, min(a, numel(t)));
%         b = max(1, min(b, numel(t)));
%         x1 = t(a); x2 = t(b);
%         p = patch(ax, [x1 x2 x2 x1], [yl(1) yl(1) yl(2) yl(2)], faceColor, ...
%             'FaceAlpha', alpha, 'EdgeColor', 'none');
%         uistack(p, 'bottom');
%     end
% 
%     ylim(ax, yl);
% end
% 
% function add_mask_shading(ax, t, mask, k1, k2, faceColor, alpha)
% %ADD_MASK_SHADING Shade regions where mask==true within [k1,k2].
% 
%     if isempty(mask)
%         return;
%     end
%     mask = mask(:);
%     n = numel(mask);
%     k1 = max(1, min(k1, n));
%     k2 = max(1, min(k2, n));
% 
%     m = mask(k1:k2);
%     dm = diff([false; m; false]);
%     s = find(dm == 1) + k1 - 1;
%     e = find(dm == -1) - 1 + k1 - 1;
% 
%     segs = [s(:), e(:)];
%     add_interval_patches(ax, t, segs, k1, k2, faceColor, alpha);
% end
% 
% function [k1, k2] = event_window(ev, n, pad)
% %EVENT_WINDOW Safe [k1,k2] around an event
%     k1 = max(1, ev.k_in - pad);
%     k2 = min(n, ev.k_out + pad);
% end
% 
% 
% function plot_sensitivity_fig(A_drift_mag, A_is_park, B_dist, B_is_leave, cfg, p)
% % 参数敏感性（可视化）：
% % 左：A类 D_th（停车漂移阈值）对事件级TPR/FPR的影响
% % 右：B类 dist_th（相似性门控阈值）对“占用保持扰动事件”的接受率/更新触发率
% 
%     fig = ch4_newfig(12, 5.6);
%     tlo = tiledlayout(fig, 1, 2, 'Padding','compact', 'TileSpacing','compact');
% 
%     %% (Left) A类：D_th 事件级 TPR/FPR
%     ax1 = nexttile(tlo, 1);
%     hold(ax1, 'on'); grid(ax1, 'on'); box(ax1, 'on');
%     A_drift_mag = A_drift_mag(:);
%     A_is_park   = logical(A_is_park(:));
%     maskA = ~isnan(A_drift_mag);
%     A_drift_mag = A_drift_mag(maskA);
%     A_is_park   = A_is_park(maskA);
% 
%     if ~isempty(A_drift_mag)
%         Dgrid = linspace(min(A_drift_mag), max(A_drift_mag), 40);
%         [tprA, fprA] = binary_sweep_rates(A_drift_mag, A_is_park, Dgrid);
%         plot(ax1, Dgrid, tprA, 'LineWidth', 2.0);
%         plot(ax1, Dgrid, fprA, '--', 'LineWidth', 2.0);
%         xline(ax1, cfg.D_th, ':', sprintf('D_{th}=%.1f', cfg.D_th), 'LineWidth', 2.0);
%         legend(ax1, {'召回率(TPR)','误报率(FPR)'}, 'Location','best');
%     else
%         text(ax1, 0.5, 0.5, 'A类样本不足', 'HorizontalAlignment','center');
%     end
%     xlabel(ax1, '停车漂移阈值 $D_{\mathrm{th}}$', 'Interpreter','latex');
%     ylabel(ax1, '比例');
%     title(ax1, 'A类：$D_{\mathrm{th}}$敏感性（事件级）', 'Interpreter','latex');
% 
%     %% (Right) B类：dist_th 占用稳态接受率/更新触发率
%     ax2 = nexttile(tlo, 2);
%     hold(ax2, 'on'); grid(ax2, 'on'); box(ax2, 'on');
% 
%     B_dist = B_dist(:);
%     B_is_leave = logical(B_is_leave(:));
%     keep = ~B_is_leave & ~isnan(B_dist);
%     d_keep = B_dist(keep);
% 
%     if ~isempty(d_keep)
%         dgrid = linspace(0, max(d_keep)*1.05, 40);
%         acc = arrayfun(@(d) mean(d_keep < d), dgrid);       % 接受率：dist<d
%         upd = 1 - acc;                                      % 触发更新率：dist>=d
%         plot(ax2, dgrid, acc, 'LineWidth', 2.0);
%         plot(ax2, dgrid, upd, '--', 'LineWidth', 2.0);
%         xline(ax2, cfg.dist_th, ':', sprintf('dist_{th}=%.1f', cfg.dist_th), 'LineWidth', 2.0);
%         legend(ax2, {'接受率 $Acc(d)$','更新触发率 $1-Acc(d)$'}, 'Location','best', 'Interpreter','latex');
%     else
%         text(ax2, 0.5, 0.5, 'B类保持样本不足', 'HorizontalAlignment','center');
%     end
% 
%     xlabel(ax2, '相似性阈值 $\mathrm{dist}_{\mathrm{th}}$', 'Interpreter','latex');
%     ylabel(ax2, '比例');
%     title(ax2, 'B类：$\mathrm{dist}_{\mathrm{th}}$敏感性（占用保持事件）', 'Interpreter','latex');
% 
%     % Export (PDF+PNG) into thesis images_dir
%     figPath = fullfile(p.images_dir, 'ch4_sensitivity.pdf');
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, figPath);
%     close(fig);
% end
% 
% function [tpr, fpr] = binary_sweep_rates(x, y, th, greaterIsPositive)
% %BINARY_SWEEP_RATES Compute TPR/FPR for thresholds.
% %  - x: score
% %  - y: logical ground-truth positive
% %  - th: thresholds
% %  - greaterIsPositive: if true, pred = x>th else pred=x<th
% 
%     if nargin < 4 || isempty(greaterIsPositive)
%         greaterIsPositive = true;
%     end
% 
%     x = x(:); y = logical(y(:));
%     tpr = zeros(numel(th),1);
%     fpr = zeros(numel(th),1);
%     for i = 1:numel(th)
%         if greaterIsPositive
%             yp = x > th(i);
%         else
%             yp = x < th(i);
%         end
%         TP = sum( yp &  y);
%         FN = sum(~yp &  y);
%         FP = sum( yp & ~y);
%         TN = sum(~yp & ~y);
%         tpr(i) = TP / max(TP+FN, 1);
%         fpr(i) = FP / max(FP+TN, 1);
%     end
% end
% 
% function ch4_report_fig_status(p, expectedBases, figOpt)
% %CH4_REPORT_FIG_STATUS Print where images are written and which ones exist.
% 
%     fprintf('\n=== 输出目录 ===\n');
%     fprintf('thesis_dir : %s\n', string(p.thesis));
%     fprintf('images_dir : %s\n', string(p.images_dir));
%     fprintf('tables_dir : %s\n', string(p.tables_dir));
%     fprintf('csv(out)   : %s\n', string(p.out));
% 
%     d = dir(fullfile(p.images_dir, 'ch4_*.pdf'));
%     fprintf('\n=== images_dir 下已有 ch4_*.pdf：%d 个 ===\n', numel(d));
%     if figOpt.verbose
%         for i = 1:numel(d)
%             fprintf('  - %s\n', d(i).name);
%         end
%     end
% 
%     missing = {};
%     for i = 1:numel(expectedBases)
%         base = expectedBases{i};
%         pdfPath = fullfile(p.images_dir, [base '.pdf']);
%         if exist(pdfPath,'file') ~= 2
%             missing{end+1} = base; %#ok<AGROW>
%             if isfield(figOpt,'make_placeholders') && figOpt.make_placeholders
%                 ch4_make_placeholder(pdfPath, '缺少图片占位', {['文件名：' base '.pdf'], '请根据章节内容替换为真实图片。'});
%             end
%         end
%     end
% 
%     if ~isempty(missing)
%         fprintf('\n[Warn] 以下预期图片缺失（已按需生成占位图）：\n');
%         for i = 1:numel(missing)
%             fprintf('  - %s\n', missing{i});
%         end
%     else
%         fprintf('\n[OK] 预期图片均存在。\n');
%     end
% end
% 
% function ch4_make_placeholder(pdfPath, titleText, lines)
% %CH4_MAKE_PLACEHOLDER Create a simple placeholder figure (PDF+PNG).
% 
%     fig = ch4_newfig(16, 6);
%     axis off;
% 
%     if isstring(lines); lines = cellstr(lines); end
%     if ~iscell(lines); lines = {char(lines)}; end
% 
%     msg = [{titleText}; lines(:)];
% 
%     annotation(fig, 'rectangle', [0.05 0.15 0.90 0.75], 'LineWidth', 1.2);
%     annotation(fig, 'textbox', [0.06 0.16 0.88 0.73], 'String', msg, ...
%         'LineStyle','none', 'FontName','Microsoft YaHei', 'FontSize', 12, ...
%         'HorizontalAlignment','left', 'VerticalAlignment','top');
% 
%     ch4_apply_style(fig);
%     ch4_export_fig(fig, pdfPath);
%     close(fig);
% end
% 
% function ch4_copy_figpair(srcPdf, dstPdf)
% %CH4_COPY_FIGPAIR Copy PDF and its paired PNG (if exists).
%     try
%         copyfile(srcPdf, dstPdf, 'f');
%     catch
%     end
%     srcPng = regexprep(srcPdf, '\.pdf$', '.png', 'ignorecase');
%     dstPng = regexprep(dstPdf, '\.pdf$', '.png', 'ignorecase');
%     if exist(srcPng,'file') == 2
%         try
%             copyfile(srcPng, dstPng, 'f');
%         catch
%         end
%     end
% end
% 
% 
% function ch4_make_aliases_without_opt(p, figOpt)
% %CH4_MAKE_ALIASES_WITHOUT_OPT
% % Create alias copies so LaTeX can use clean filenames without the opt_/auto prefix.
% % This is purely a convenience layer and does not change any evaluation result.
% 
%     if ~isfield(figOpt,'force_overwrite_alias')
%         figOpt.force_overwrite_alias = false;
%     end
% 
%     % src (opt) -> dst (clean)
%     pairs = {
%         {'ch4_opt_dataset_stats',    'ch4_dataset_stats'}
%         {'ch4_opt_prf_by_group',     'ch4_prf_by_group'}
%         {'ch4_opt_timing_tau_box',   'ch4_timing_tau_box'}
%         {'ch4_opt_timing_tau_cdf',   'ch4_timing_tau_cdf'}
%         {'ch4_opt_ablation_by_group','ch4_ablation_by_group'}
%         {'ch4_opt_ablation_by_group','ch4_ablation_fig'}   % LaTeX label uses fig:ch4_ablation_fig
%     };
% 
%     for i = 1:numel(pairs)
%         srcBase = pairs{i}{1};
%         dstBase = pairs{i}{2};
%         srcPdf = fullfile(p.images_dir, [srcBase '.pdf']);
%         dstPdf = fullfile(p.images_dir, [dstBase '.pdf']);
% 
%         if isfile(srcPdf)
%             if (~isfile(dstPdf)) || figOpt.force_overwrite_alias
%                 ch4_copy_figpair(srcPdf, dstPdf);
%             end
%         end
%     end
% end
% 
% 
% %% ================= Extra figure pools (optional) =================
% 
% function make_optional_fig_pool(T_file, T_group, T_ds, T_timing, tim_rows, ...
%     A_drift_mag, A_is_park, B_dist, B_is_leave, C_file, T_ab, cfg, p, figOpt)
% %MAKE_OPTIONAL_FIG_POOL Generate additional figures for selection (ch4_opt_*).
% % These figures are not required by the LaTeX placeholders; they help you pick
% % better illustrations or provide supplementary analysis.
% 
%     if nargin < 13
%         figOpt = struct();
%     end
% 
%     outDir = p.images_dir;
%     if ~exist(outDir,'dir'); mkdir(outDir); end
% 
%     % ---------- 1) PRF by group ----------
%     try
%         if ~isempty(T_group)
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             M = [T_group.P, T_group.R, T_group.F1];
%             bar(ax, M);
%             ylim(ax, [0 1]);
%             xticks(ax, 1:height(T_group));
%             xticklabels(ax, cellstr(T_group.group));
%             ylabel(ax, '指标值');
%             legend(ax, {'精确率 P','召回率 R','F1'}, 'Location','northoutside','Orientation','horizontal');
%             title(ax, '分工况检测性能（GLOBAL）', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_prf_by_group.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 2) Errors by group: counts + rates ----------
%     try
%         if ~isempty(T_group)
%             fig = ch4_newfig(16, 10);
%             tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
% 
%             ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
%             C = [T_group.TP, T_group.FP, T_group.FN];
%             bar(ax1, C);
%             xticks(ax1, 1:height(T_group));
%             xticklabels(ax1, cellstr(T_group.group));
%             ylabel(ax1, '次数');
%             legend(ax1, {'TP','FP','FN'}, 'Location','northoutside','Orientation','horizontal');
%             title(ax1, 'TP/FP/FN 统计', 'FontWeight','normal');
% 
%             ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
%             plot(ax2, 1:height(T_group), 100*T_group.Rf, '-o', 'LineWidth', 1.2);
%             plot(ax2, 1:height(T_group), 100*T_group.Rm, '--s', 'LineWidth', 1.2);
%             xticks(ax2, 1:height(T_group));
%             xticklabels(ax2, cellstr(T_group.group));
%             ylabel(ax2, '比例/%');
%             legend(ax2, {'误检率 R_f','漏检率 R_m'}, 'Location','northoutside','Orientation','horizontal');
%             title(ax2, '误检率/漏检率（按 GT 事件数归一）', 'FontWeight','normal');
% 
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_errors_by_group.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 3) Dataset stats ----------
%     try
%         if ~isempty(T_ds)
%             fig = ch4_newfig(16, 10);
%             tl = tiledlayout(fig, 2, 2, 'TileSpacing','compact', 'Padding','compact');
% 
%             ax = nexttile(tl, 1); bar(ax, T_ds.num_files); grid(ax,'on');
%             title(ax, '文件数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));
% 
%             ax = nexttile(tl, 2); bar(ax, T_ds.num_parking_gt); grid(ax,'on');
%             title(ax, '真值占用事件数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));
% 
%             ax = nexttile(tl, 3); bar(ax, T_ds.num_vehicle_events); grid(ax,'on');
%             title(ax, '车辆扰动事件数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));
%             xlabel(ax, '工况组');
% 
%             ax = nexttile(tl, 4); bar(ax, T_ds.num_pass_est); grid(ax,'on');
%             title(ax, '通过事件估计数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));
%             xlabel(ax, '工况组');
% 
%             title(tl, '数据集统计（估计口径）', 'FontWeight','normal');
% 
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_dataset_stats.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 4) Per-file F1 distribution ----------
%     try
%         if ~isempty(T_file)
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             if exist('boxplot','file') == 2
%                 boxplot(ax, T_file.F1, T_file.group);
%             else
%                 % fallback: jittered scatter
%                 groups = unique(T_file.group,'stable');
%                 for i = 1:numel(groups)
%                     g = groups(i);
%                     y = T_file.F1(T_file.group==g);
%                     x = i + 0.12*(rand(size(y))-0.5);
%                     scatter(ax, x, y, 18, 'filled');
%                 end
%                 xticks(ax, 1:numel(groups));
%                 xticklabels(ax, cellstr(groups));
%             end
%             ylim(ax, [0 1]);
%             ylabel(ax, 'F1');
%             title(ax, '单文件 F1 分布（按工况组）', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_f1_box_by_group.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 5) Per-file F1 vs events ----------
%     try
%         if ~isempty(T_file)
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             groups = unique(T_file.group,'stable');
%             mk = {'o','s','^','d','x','+'};
%             for i = 1:numel(groups)
%                 g = groups(i);
%                 idx = T_file.group==g;
%                 scatter(ax, T_file.events(idx), T_file.F1(idx), 26, mk{1+mod(i-1,numel(mk))}, 'filled');
%             end
%             xlabel(ax, '车辆扰动事件数');
%             ylabel(ax, 'F1');
%             ylim(ax, [0 1]);
%             legend(ax, cellstr(groups), 'Location','northoutside','Orientation','horizontal');
%             title(ax, '单文件 F1 vs 车流扰动强度（事件数）', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_f1_vs_events.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 6) Top/Bottom per-file ranking ----------
%     try
%         if ~isempty(T_file)
%             Tf = sortrows(T_file, 'F1', 'descend');
%             k = min(10, height(Tf));
%             top = Tf(1:k, {'file','group','F1'});
%             bot = Tf(max(height(Tf)-k+1,1):height(Tf), {'file','group','F1'});
% 
%             fig = ch4_newfig(16, 10);
%             tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
% 
%             ax1 = nexttile(tl, 1); barh(ax1, top.F1); grid(ax1,'on');
%             xlim(ax1, [0 1]);
%             yticklabels(ax1, cellstr(top.group + " | " + top.file));
%             title(ax1, 'Top 文件（按 F1 降序）', 'FontWeight','normal');
% 
%             ax2 = nexttile(tl, 2); barh(ax2, flipud(bot.F1)); grid(ax2,'on');
%             xlim(ax2, [0 1]);
%             yticklabels(ax2, cellstr(flipud(bot.group + " | " + bot.file)));
%             title(ax2, 'Bottom 文件（按 F1 升序）', 'FontWeight','normal');
% 
%             title(tl, '单文件 F1 排名（用于挑选典型样例）', 'FontWeight','normal');
% 
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_per_file_rank.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 7) Timing boxplots ----------
%     try
%         if ~isempty(tim_rows)
%             fig = ch4_newfig(16, 10);
%             tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
% 
%             ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
%             if exist('boxplot','file') == 2
%                 boxplot(ax1, tim_rows.tau_in, tim_rows.group);
%             else
%                 scatter(ax1, double(categorical(tim_rows.group)), tim_rows.tau_in, 10, 'filled');
%             end
%             ylabel(ax1, '\tau_{in} / s');
%             title(ax1, '停车确认上报延迟 \tau_{in}', 'FontWeight','normal');
% 
%             ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
%             if exist('boxplot','file') == 2
%                 boxplot(ax2, tim_rows.tau_out, tim_rows.group);
%             else
%                 scatter(ax2, double(categorical(tim_rows.group)), tim_rows.tau_out, 10, 'filled');
%             end
%             ylabel(ax2, '\tau_{out} / s'); xlabel(ax2, '工况组');
%             title(ax2, '释放确认上报延迟 \tau_{out}', 'FontWeight','normal');
% 
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_timing_tau_box.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 8) Timing CDFs ----------
%     try
%         if ~isempty(tim_rows)
%             fig = ch4_newfig(16, 10);
%             tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
% 
%             ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
%             plot_cdf_by_group(ax1, tim_rows, 'tau_in', '\tau_{in} / s');
%             title(ax1, '\tau_{in} 的经验分布（CDF）', 'FontWeight','normal');
% 
%             ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
%             plot_cdf_by_group(ax2, tim_rows, 'tau_out', '\tau_{out} / s');
%             title(ax2, '\tau_{out} 的经验分布（CDF）', 'FontWeight','normal');
% 
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_timing_tau_cdf.pdf'));
%             close(fig);
% 
%             fig = ch4_newfig(16, 10);
%             tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
% 
%             ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
%             tmp = tim_rows; tmp.abs_dt_in = abs(tmp.dt_in);
%             plot_cdf_by_group(ax1, tmp, 'abs_dt_in', '|\\Delta t_{in}| / s');
%             title(ax1, '|\Delta t_{in}| 的经验分布（CDF）', 'FontWeight','normal');
% 
%             ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
%             tmp = tim_rows; tmp.abs_dt_out = abs(tmp.dt_out);
%             plot_cdf_by_group(ax2, tmp, 'abs_dt_out', '|\\Delta t_{out}| / s');
%             title(ax2, '|\Delta t_{out}| 的经验分布（CDF）', 'FontWeight','normal');
% 
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_timing_dt_cdf.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 9) A drift CDF ----------
%     try
%         if ~isempty(A_drift_mag)
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             v0 = A_drift_mag(A_is_park==0);
%             v1 = A_drift_mag(A_is_park==1);
%             plot_emp_cdf(ax, v0, '-', 1.2);
%             plot_emp_cdf(ax, v1, '--', 1.2);
%             xlabel(ax, '漂移幅值 ||\Delta B||_2'); ylabel(ax, 'CDF');
%             legend(ax, {'通过/干扰','停车到达'}, 'Location','best');
%             title(ax, 'A类：漂移幅值的经验分布', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_A_drift_cdf.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 10) B dist CDF ----------
% try
%     if ~isempty(B_dist)
%         fig = ch4_newfig(16, 8);
%         ax = axes(fig); hold(ax,'on'); grid(ax,'on');
% 
%         v_keep  = B_dist((B_is_leave==0) & ~isnan(B_dist));
%         v_leave = B_dist((B_is_leave==1) & ~isnan(B_dist));
% 
%         plot_emp_cdf(ax, v_keep, '-', 1.2);
% 
%         leg = {'仍占用扰动事件（保持门控）'};
%         if numel(v_leave) >= 5
%             plot_emp_cdf(ax, v_leave, '--', 1.2);
%             leg = {'仍占用扰动事件（保持门控）', '驶离事件（若dist有效）'};
%         else
%             text(ax, 0.02, 0.10, '注：驶离多由 D_{free}(back2env) 判决，dist样本可能缺失', ...
%                 'Units','normalized', 'FontSize', 10, 'Color', [0.3 0.3 0.3]);
%         end
% 
%         xline(ax, cfg.pk.dist_th, ':', sprintf('dist_{th}=%.1f', cfg.pk.dist_th), 'LineWidth', 1.2);
% 
%         if ~isempty(v_keep)
%             acc = mean(v_keep < cfg.pk.dist_th);
%             text(ax, 0.02, 0.90, sprintf('Acc@dist_{th}=%.1f%%', 100*acc), ...
%                 'Units','normalized', 'FontSize', 11, 'Color', [0.1 0.1 0.1]);
%         end
% 
%         xlabel(ax, '相似距离 dist');
%         ylabel(ax, 'CDF');
%         legend(ax, leg, 'Location', 'best');
%         title(ax, 'B类：相似性门控阈值 dist_{th} 的经验分布', 'FontWeight', 'normal');
%         ch4_apply_style(fig);
%         ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_B_dist_cdf.pdf'));
%         close(fig);
%     end
% catch
% end
% 
% % ---------- 11) C per-file ratios ----------
% 
%     try
%         if ~isempty(C_file)
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             M = [C_file.stable_found_ratio, C_file.used_degrade_ratio];
%             if exist('boxplot','file') == 2
%                 boxplot(ax, M, 'Labels', {'稳定点可得率','退化分支使用率'});
%             else
%                 scatter(ax, ones(size(M,1),1), M(:,1), 18, 'filled'); hold(ax,'on');
%                 scatter(ax, 2*ones(size(M,1),1), M(:,2), 18, 'filled');
%                 xlim(ax, [0.5 2.5]);
%                 set(ax,'XTick',[1 2],'XTickLabel',{'稳定点可得率','退化分支使用率'});
%             end
%             ylim(ax, [0 1]);
%             ylabel(ax, '比例');
%             title(ax, 'C类：按文件统计的稳定点可得率与退化分支使用率', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_C_file_ratios.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
%     % ---------- 12) Ablation plots ----------
%     try
%         if exist('T_ab','var') && ~isempty(T_ab) && height(T_ab) > 0
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             bar(ax, T_ab.F1_all);
%             ylim(ax, [0 1]);
%             xticks(ax, 1:height(T_ab));
%             xticklabels(ax, cellstr(T_ab.variant));
%             ylabel(ax, 'F1');
%             title(ax, '消融实验：总体 F1（GLOBAL）', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_ablation_all.pdf'));
%             close(fig);
% 
%             fig = ch4_newfig(16, 8);
%             ax = axes(fig); hold(ax,'on'); grid(ax,'on');
%             M = [T_ab.F1_A, T_ab.F1_B, T_ab.F1_C, T_ab.F1_D];
%             bar(ax, M);
%             ylim(ax, [0 1]);
%             xticks(ax, 1:height(T_ab));
%             xticklabels(ax, cellstr(T_ab.variant));
%             ylabel(ax, 'F1');
%             legend(ax, {'A','B','C','D'}, 'Location','best');
%             title(ax, '消融实验：分工况 F1（GLOBAL）', 'FontWeight','normal');
%             ch4_apply_style(fig);
%             ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_ablation_by_group.pdf'));
%             close(fig);
%         end
%     catch
%     end
% 
% end
% 
% 
% function make_extra_examples(T_file, GT, p, cfg, post, IOU_TH, figOpt)
% %MAKE_EXTRA_EXAMPLES Generate additional case/wave figures for selection.
% % Output naming:
% %   ch4_case_<G>_<tag>_padXXs.pdf/.png
% %   ch4_wave_<G>_<tag>_padXXs.pdf/.png
% 
%     if isempty(T_file) || isempty(GT)
%         return;
%     end
% 
%     groups = ["A","B","C","D"];
%     pads = figOpt.extra_case_pads_sec;
%     if isempty(pads); pads = [8 20]; end
% 
%     rng(0); % deterministic
% 
%     sel = table('Size',[0 4], ...
%         'VariableTypes',{'string','string','string','double'}, ...
%         'VariableNames',{'file','group','tag','F1'});
% 
%     for gg = 1:numel(groups)
%         g = groups(gg);
%         Tf = T_file(T_file.group==g,:);
%         if isempty(Tf); continue; end
% 
%         % sort by F1
%         Tf = sortrows(Tf, 'F1', 'descend');
%         best = Tf(1,:);
%         worst = Tf(end,:);
%         mid = Tf(round((height(Tf)+1)/2),:);
% 
%         sel = [sel; {best.file, g, "best", best.F1}]; %#ok<AGROW>
%         sel = [sel; {mid.file,  g, "mid",  mid.F1}]; %#ok<AGROW>
%         sel = [sel; {worst.file,g, "worst",worst.F1}]; %#ok<AGROW>
% 
%         % random picks (exclude already selected)
%         k = figOpt.extra_random_per_group;
%         if isempty(k) || k <= 0; continue; end
% 
%         allFiles = unique(Tf.file, 'stable');
%         picked = unique([best.file; mid.file; worst.file], 'stable');
%         cand = setdiff(allFiles, picked, 'stable');
%         if isempty(cand); continue; end
%         rp = randperm(numel(cand), min(k, numel(cand)));
%         for j = 1:numel(rp)
%             sel = [sel; {cand(rp(j)), g, "rand" + string(j), NaN}]; %#ok<AGROW>
%         end
%     end
% 
%     % de-duplicate
%     [~, ia] = unique(sel(:,{'file','group','tag'}), 'rows', 'stable');
%     sel = sel(ia,:);
% 
%     if height(sel) > figOpt.max_extra_cases_total
%         sel = sel(1:figOpt.max_extra_cases_total,:);
%     end
% 
%     fprintf("[Extra] will generate %d extra example(s) ...\n", height(sel));
% 
%     for i = 1:height(sel)
%         fileName = sel.file(i);
%         g = sel.group(i);
%         tag = sel.tag(i);
% 
%         gt_f = GT(GT.file == fileName, :);
%         if isempty(gt_f)
%             continue;
%         end
% 
%         csvPath = ch4_find_csv(fileName, p.root, p.synth);
%         data = ch4_load_csv(csvPath, cfg.fs);
%         out  = ch4_run_parking_fsm(data, cfg);
% 
%         [pred_k, conf_k] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec); %#ok<NASGU>
%         gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
% 
%         % Titles in Chinese (file names may contain underscores)
%         f1v = sel.F1(i);
%         if isfinite(f1v)
%             titleBase = sprintf('%s类-%s（F1=%.3f）：%s', char(g), char(tag_to_cn(tag)), f1v, char(fileName));
%         else
%             titleBase = sprintf('%s类-%s：%s', char(g), char(tag_to_cn(tag)), char(fileName));
%         end
% 
%             for pp = 1:numel(pads)
%                 padSec = pads(pp);
% 
%                 % D类慢漂移：窗口过短不易观察基线变化，允许对D类强制放大padSec
%                 if isfield(figOpt,'extra_case_padSec_D') && strcmpi(char(g),'D') && padSec < figOpt.extra_case_padSec_D
%                     padSec = figOpt.extra_case_padSec_D;
%                 end
% 
%                 % 可选：手工指定中心时刻（秒），用于挑选最能体现漂移/退化的窗口
%                 tCenterManual = [];
%                 if isfield(figOpt,'extra_case_tCenter_by_group')
%                     try
%                         tCenterManual = figOpt.extra_case_tCenter_by_group.(char(g));
%                     catch
%                         tCenterManual = [];
%                     end
%                 end
%             padTag = sprintf('pad%ds', round(padSec));
% 
%             figCase = fullfile(p.images_dir, "ch4_case_" + g + "_" + tag + "_" + padTag + ".pdf");
%             figWave = fullfile(p.images_dir, "ch4_wave_" + g + "_" + tag + "_" + padTag + ".pdf");
% 
%             % Case: ||B|| + R/M
%             if ~isempty(tCenterManual)
%     plot_case_one(data, out, pred_k, gt_idx, figCase, titleBase, cfg, 'padSec', padSec, 'tCenter', tCenterManual);
% else
%     plot_case_one(data, out, pred_k, gt_idx, figCase, titleBase, cfg, 'padSec', padSec);
% end
% 
%             % Wave: 3-axis + stable flag
%             plot_wave_group(data, out, pred_k, gt_idx, g, figWave, cfg, padSec);
%         end
%     end
% 
% end
% 
% 
% function s = tag_to_cn(tag)
%     tag = string(tag);
%     if startsWith(tag, "best"); s = "最佳";
%     elseif startsWith(tag, "mid"); s = "中位";
%     elseif startsWith(tag, "worst"); s = "最差";
%     elseif startsWith(tag, "rand"); s = "随机" + extractAfter(tag, "rand");
%     else; s = tag;
%     end
% end
% 
% 
% function plot_cdf_by_group(ax, T, fieldName, xlab)
%     groups = unique(T.group, 'stable');
%     for i = 1:numel(groups)
%         g = groups(i);
%         v = T.(fieldName)(T.group==g);
%         plot_emp_cdf(ax, v, '-', 1.0);
%     end
%     xlabel(ax, xlab);
%     ylabel(ax, 'CDF');
%     legend(ax, cellstr(groups), 'Location','northoutside','Orientation','horizontal');
% end
% 
% 
% function plot_emp_cdf(ax, v, style, lw)
%     v = v(:);
%     v = v(isfinite(v));
%     if isempty(v)
%         return;
%     end
%     v = sort(v);
%     n = numel(v);
%     y = (1:n) / n;
%     plot(ax, v, y, style, 'LineWidth', lw);
% end
% 
% function fig = ch4_newfig(w_cm, h_cm)
% %CH4_NEWFIG Create a white, off-screen figure with fixed size (cm)
%     fig = figure('Visible','off', 'Color','w');
%     set(fig, 'Units','centimeters', 'Position',[2 2 w_cm h_cm]);
%     set(fig, 'PaperPositionMode','auto');
% end
% 
% function ch4_export_paper_figs(p, figOpt)
% %CH4_EXPORT_PAPER_FIGS Copy selected figures (pdf/png) to a separate folder for thesis inclusion.
% %   This keeps your normal output under p.images_dir untouched, and provides a clean folder
% %   (figOpt.paper_fig_dir) that only contains the figures you actually reference in Ch4 LaTeX.
% 
% % destination folder
% dstDir = fullfile(p.out, 'paper_figs');
% if isfield(figOpt,'paper_fig_dir') && ~isempty(figOpt.paper_fig_dir)
%     dstDir = figOpt.paper_fig_dir;
% end
% if ~exist(dstDir,'dir')
%     mkdir(dstDir);
% end
% 
% % whether also copy png
% copyPng = true;
% if isfield(figOpt,'paper_copy_png')
%     copyPng = figOpt.paper_copy_png;
% end
% 
% % figure basenames to export
% if isfield(figOpt,'paper_bases') && ~isempty(figOpt.paper_bases)
%     bases = figOpt.paper_bases;
% else
%     bases = { 'ch4_pass_vs_park_sim', 'ch4_pipeline', 'ch4_stability_demo', 'ch4_fsm_degrade' };
% end
% 
% % D类默认更长窗口：如果 pad60s 的图不存在，则回退到 pad20s（避免导出失败）
% idxD = strcmp(bases, 'ch4_case_D_mid_pad60s');
% if any(idxD) && ~exist(fullfile(p.images_dir, 'ch4_case_D_mid_pad60s.pdf'), 'file')
%     bases{find(idxD,1)} = 'ch4_case_D_mid_pad20s';
% end
% 
% copiedPdf = {};
% missingPdf = {};
% 
% for i = 1:numel(bases)
%     base = bases{i};
% 
%     % pdf
%     srcPdf = fullfile(p.images_dir, [base '.pdf']);
%     if exist(srcPdf,'file')
%         dstPdf = fullfile(dstDir, [base '.pdf']);
%         copyfile(srcPdf, dstPdf);
%         copiedPdf{end+1} = [base '.pdf']; %#ok<AGROW>
%     else
%         missingPdf{end+1} = [base '.pdf']; %#ok<AGROW>
%     end
% 
%     % png (optional)
%     if copyPng
%         srcPng = fullfile(p.images_dir, [base '.png']);
%         if exist(srcPng,'file')
%             dstPng = fullfile(dstDir, [base '.png']);
%             copyfile(srcPng, dstPng);
%         end
%     end
% end
% 
% % manifest for quick check
% manifest = fullfile(dstDir, 'manifest_ch4_paper_figs.txt');
% fid = fopen(manifest, 'w');
% if fid > 0
%     fprintf(fid, '# Ch4 paper figures exported from: %s\n', p.images_dir);
%     fprintf(fid, '# Export time: %s\n\n', datestr(now, 31));
% 
%     fprintf(fid, '[COPIED_PDF]\n');
%     for i = 1:numel(copiedPdf)
%         fprintf(fid, '%s\n', copiedPdf{i});
%     end
% 
%     if ~isempty(missingPdf)
%         fprintf(fid, '\n[MISSING_PDF]\n');
%         for i = 1:numel(missingPdf)
%             fprintf(fid, '%s\n', missingPdf{i});
%         end
%     end
%     fclose(fid);
% end
% 
% fprintf('=== 已导出论文用图到: %s (%d/%d pdf found) ===\n', dstDir, numel(copiedPdf), numel(bases));
% end
% 
% 
% 
% 
% 
% 
% 
% % 1) 看 B/C/D meta 里到底记录了什么
% Tb = readtable('...\synth_out\4_16_停车检测_e1_B_meta.csv','VariableNamingRule','preserve');
% Tc = readtable('...\synth_out\4_16_停车检测_e1_C_meta.csv','VariableNamingRule','preserve');
% Td = readtable('...\synth_out\4_16_停车检测_e1_D_meta.csv','VariableNamingRule','preserve');
% 
% disp(Tb.Properties.VariableNames); disp(Tb);
% disp(Tc.Properties.VariableNames); disp(Tc);
% disp(Td.Properties.VariableNames); disp(Td);
% 
% % 2) 看 lib.mat 里有哪些变量（脉冲库/模板一般在这里）
% whos('-file','...\synth_out\4_16_停车检测_e1_lib.mat');
% S = load('...\synth_out\4_16_停车检测_e1_lib.mat');




%% run_ch4_onekey_global.m
% One-click runner for Chapter 4 experiments (GLOBAL config).
% 
% Outputs (saved under p.out from core/ch4_local_paths.m):
%   - E0_dataset_stats.csv
%   - E1_per_file.csv
%   - E1_by_group.csv
%   - E1_timing_by_group.csv
%   - E3_ablation_by_group.csv   (optional)
%   - Figures: fig_case_*.png, fig_A_drift_mag.png, fig_B_dist.png, fig_C_seek_ratio.png
%
% Prerequisites:
%   1) Put this file under the repo (recommended: under /run/).
%   2) Update core/ch4_local_paths.m so that:
%        p.root  = folder containing *_clean.csv (zhenzhi)
%        p.synth = folder containing *_synth.csv (synth_out)
%        p.gt    = GT CSV path (parking_groundtruth_filled_cleaned.csv)
%        p.out   = output folder
%   3) Run this script in MATLAB.
%
% Notes about reporting:
%   - This script uses ONE global parameter set (deployment-like).
%   - If you want "oracle per-group tuned" results, run separate scripts and clearly label as upper bound.

clear; clc; close all;

%% 0) Path setup
thisFile = mfilename('fullpath');
thisDir  = fileparts(thisFile);
repoRoot = fileparts(thisDir);
addpath(genpath(repoRoot));

p = ch4_local_paths();
if ~exist(p.out, 'dir'); mkdir(p.out); end

%% 1) Load GT and append synth GT
GT = readtable(p.gt);

% normalize string columns (important for == comparisons)
GT.file = string(GT.file);
if ismember("scenario_group", GT.Properties.VariableNames)
    GT.scenario_group = string(GT.scenario_group);
else
    error("GT must contain column: scenario_group");
end

GT = ch4_append_synth_gt_all_events(GT, p.synth);
GT.file = string(GT.file);
GT.scenario_group = string(GT.scenario_group);

files = unique(GT.file, 'stable');

%% 2) Global configuration (match your current E1 output)
[cfg, post] = ch4_config_tuned_v2("GLOBAL");

% --- overrides (use your final global values) ---
cfg.pk.D_th     = 36.0;
cfg.pk.dist_th  = 4.0;
cfg.ref.D_upd   = 30.0;
% --- Figure/display options (visualization only) ---
% 典型案例图（case）建议展示三轴扰动（相对参考点），以提高可读性与可解释性。
% 可选：
%   'dxyz' : 三轴扰动 Bx- Sref_x, By- Sref_y, Bz- Sref_z（推荐，用于 case 图）
%   'rel'  : 标量残差 ||B-Sref||_2（更利于跨文件对比）
%   'bx'   : 单轴扰动 Bx- Sref_x（更接近 wave 风格）
cfg.fig.case_sigMode = 'dxyz';
cfg.fig.wave_sigMode = 'xyz'; % reserved: waveform demo mode


post.Tmin_sec      = 6.0;
post.gap_merge_sec = 0.0;

IOU_TH = 0.50;

fprintf("=== E1 GLOBAL (all-events synth GT), IoU>=%.2f ===\n", IOU_TH);
fprintf("Tmin=%.2f sec | gap_merge=%.2f sec\n", post.Tmin_sec, post.gap_merge_sec);
fprintf("GLOBAL: D_th=%.2f, D_free=%.2f, dist_th=%.2f, D_upd=%.2f\n", ...
    cfg.pk.D_th, cfg.pk.D_free, cfg.pk.dist_th, cfg.ref.D_upd);

%% 2.5) Figure options (PDF+PNG, Chinese labels, thesis placeholders)
figOpt = struct();
figOpt.strict = false;                   % true: rethrow figure errors (debug)
% NOTE:
%   If you previously ran this script when some figures were missing, it may have
%   generated placeholder PDFs ("缺少图片占位...") with the same filenames used
%   by your thesis LaTeX. In that case, you MUST overwrite them once, otherwise
%   LaTeX will keep showing the placeholder.
%   After you redraw pipeline/fsm by hand, set this back to false.
figOpt.force_overwrite_schematics = true;  % overwrite ch4_pipeline/ch4_fsm_degrade
figOpt.always_make_auto_schematics = true; % always output *_auto.* for selection
figOpt.make_placeholders = true;         % create placeholder figures if missing
figOpt.verbose = true;

% ---- extra figure pools (optional, for selection) ----
figOpt.extra_pool = true;                % generate ch4_opt_* figures (statistics & distributions)
% Copy ch4_opt_*.pdf to clean filenames (ch4_*.pdf) for LaTeX convenience
figOpt.make_alias_without_opt = true;

% --- Export a curated "paper figure" folder (only the figures that appear in Ch4 LaTeX) ---
% This does NOT affect normal outputs under p.images_dir; it only copies selected figures
% into a separate folder for easy inclusion in LaTeX.
figOpt.export_paper_figs = true;                % set false to disable
figOpt.paper_fig_dir     = fullfile(p.out, 'paper_figs');
figOpt.paper_copy_png    = true;                % also copy .png (preview); LaTeX typically uses .pdf

% List of figure basenames to export (no extension). Keep this aligned with your Ch4 LaTeX.
% NOTE: D类建议用更长窗口（pad60s），所以这里默认使用 mid_pad60s。
figOpt.paper_bases = { ...
    'ch4_pass_vs_park_sim', ...   % 仿真/示意（可替换为 ch4_pass_vs_park）
    'ch4_pipeline', ...
    'ch4_stability_demo', ...
    'ch4_fsm_degrade', ...
    'ch4_scene_photo', ...
    'ch4_setup_schematic', ...
    'ch4_param_scan_Dth', ...
    'ch4_param_scan_dist', ...
    'ch4_opt_prf_by_group', ...
    'ch4_opt_errors_by_group', ...
    'ch4_opt_timing_tau_box', ...
    'ch4_opt_timing_dt_cdf', ...
    'ch4_C_seek_ratio', ...
    'ch4_opt_ablation_by_group', ...
    'ch4_sensitivity', ...
    'ch4_case_A', ...
    'ch4_case_B', ...
    'ch4_case_C', ...
    'ch4_case_D' ...
};

figOpt.force_overwrite_alias  = true;

figOpt.extra_examples = true;
figOpt.make_wave_groups = false; % 不建议作为“四类对比主图”，默认关闭
            % generate extra case/wave examples (best/mid/worst + random)
figOpt.extra_random_per_group = 2;       % number of random extra files per group
figOpt.extra_case_pads_sec = [8, 20];    % context padding (seconds) for extra examples
figOpt.extra_case_padSec_D = 60;          % D类慢漂移：建议更长窗口（秒）
figOpt.extra_case_tCenter_by_group = struct('A',[], 'B',[], 'C',[], 'D',[]); % 可手工指定中心时刻（秒）
figOpt.max_extra_cases_total = 60;       % hard cap to avoid generating too many figures
% 可选：手工指定 D 类中心（秒），便于突出“驶离后慢漂移”
figOpt.extra_case_tCenter_by_group.D = 270;
%% 3) Run all files (cache minimal info for later plots)
T_file = table('Size',[0 11], ...
    'VariableTypes',{'string','string','double','double','double','double','double','double','double','double','double'}, ...
    'VariableNames',{'file','group','TP','FP','FN','P','R','F1','events','pred','gt'});

% For E2 distributions
A_drift_mag = []; A_is_park = [];
B_dist      = []; B_is_leave = [];
C_stable_found = []; C_used_degrade = [];
% For C-group per-file ratios (optional plots)
C_file = table('Size',[0 4], ...
    'VariableTypes',{'string','string','double','double'}, ...
    'VariableNames',{'file','group','stable_found_ratio','used_degrade_ratio'});


% For timing stats (store per-TP match rows)
tim_rows = table('Size',[0 8], ...
    'VariableTypes',{'string','string','double','double','double','double','double','double'}, ...
    'VariableNames',{'file','group','dt_in','dt_out','tau_in','tau_out','iou','gt_dur'});

% Case plots: auto-pick first file in each group
casePick = struct();

% ===== 手动指定论文 case（覆盖自动挑选，避免挑错事件）=====
casePick.A = "20240723_停车检测_sheet2_clean.csv";
casePick.B = "20240723_停车检测_sheet2_e4_B_synth.csv";
casePick.C = "20240723_停车检测_sheet2_e4_C_synth.csv";
casePick.D = "20240723_停车检测_sheet2_e1_D_synth.csv";

% 每类窗口（秒）
caseWin.padSec  = struct('A',15,'B',30,'C',30,'D',60);
caseWin.tCenter = struct('A',102,'B',248,'C',248,'D',270);
for i = 1:numel(files)
    f = string(files(i));
    g = string(GT.scenario_group(find(GT.file==f,1,'first')));
    if isfield(casePick, char(g)) && casePick.(char(g)) == ""
        casePick.(char(g)) = f;
    end
end

% Cache representative file outputs for thesis figures
rep = struct('A',[] ,'B',[] ,'C',[] ,'D',[]);

for i = 1:numel(files)
    fileName = string(files(i));
    gt_f = GT(GT.file == fileName, :);
    group = string(gt_f.scenario_group(1));

    csvPath = ch4_find_csv(fileName, p.root, p.synth);

    data = ch4_load_csv(csvPath, cfg.fs);
    out  = ch4_run_parking_fsm(data, cfg);

    % Postprocess pred/conf together (keep alignment)
    [pred_k, conf_k] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);

    gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));

    res = ch4_eval(pred_k, gt_idx, IOU_TH);

    % Save per-file
    rowTable = table(fileName, group, res.TP, res.FP, res.FN, res.P, res.R, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), ...
        'VariableNames', T_file.Properties.VariableNames);
    T_file = [T_file; rowTable]; %#ok<AGROW>

    fprintf("File=%s | Group=%s | TP=%d FP=%d FN=%d | F1=%.3f | events=%d pred=%d gt=%d | Tmin=%.2f\n", ...
        fileName, group, res.TP, res.FP, res.FN, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), post.Tmin_sec);

    % -------- E2(A): collect drift_mag for A group --------
    if group == "A"
        [arrIdx, ~] = match_events_to_gt(out.events, gt_idx, round(2.0*cfg.fs));
        for m = 1:numel(out.events)
            dmag = out.dbg.drift_mag(m);
            if ~isnan(dmag)
                A_drift_mag(end+1,1) = dmag; %#ok<SAGROW>
                A_is_park(end+1,1)   = ismember(m, arrIdx); %#ok<SAGROW>
            end
        end
    end

    % -------- E2(B): collect dist for B group --------
    if group == "B"
        [~, leaveIdx] = match_events_to_gt(out.events, gt_idx, round(2.0*cfg.fs));
        for m = 1:numel(out.events)
            dd = out.dbg.dist(m);
            if ~isnan(dd)
                B_dist(end+1,1) = dd; %#ok<SAGROW>
                B_is_leave(end+1,1) = ismember(m, leaveIdx); %#ok<SAGROW>
            end
        end
    end

    % -------- E2(C): stable_found ratio / degrade usage --------
    if group == "C"
        C_stable_found = [C_stable_found; out.dbg.stable_found(:)]; %#ok<AGROW>
        C_used_degrade = [C_used_degrade; out.dbg.used_degrade(:)]; %#ok<AGROW>
        % per-file ratios (for optional plots)
        try
            rf = mean(out.dbg.stable_found(:));
            rd = mean(out.dbg.used_degrade(:));
            if isfinite(rf) && isfinite(rd)
                C_file = [C_file; {fileName, group, rf, rd}]; %#ok<AGROW>
            end
        catch
        end
    end

    % -------- Timing stats on matched TP --------
    if ~isempty(res.match)
        for r = 1:size(res.match,1)
            ip = res.match(r,1);
            ig = res.match(r,2);
            iou = res.match(r,3);

            pseg = pred_k(ip,:);
            cseg = conf_k(ip,:);
            gseg = gt_idx(ig,:);

            dt_in  = (pseg(1) - gseg(1)) / cfg.fs;
            dt_out = (pseg(2) - gseg(2)) / cfg.fs;
            tau_in  = (cseg(1) - gseg(1)) / cfg.fs;
            tau_out = (cseg(2) - gseg(2)) / cfg.fs;

            gt_dur = (gseg(2) - gseg(1)) / cfg.fs;

            tim_rows = [tim_rows; {fileName, group, dt_in, dt_out, tau_in, tau_out, iou, gt_dur}]; %#ok<AGROW>
        end
    end

    % -------- Plot representative cases --------
    if isfield(casePick, char(group)) && fileName == casePick.(char(group))
        % cache representative example for later wave/stability figures
        rep.(char(group)) = struct('data',data,'out',out,'pred_k',pred_k,'gt_idx',gt_idx,'file',fileName,'group',group);

        figName = fullfile(p.images_dir, "ch4_case_" + group + ".pdf");
        % plot_case_one(data, out, pred_k, gt_idx, figName, "工况" + group + "：" + fileName, cfg);
        padSec = 30;  tC = [];
try, padSec = caseWin.padSec.(char(group)); end
try, tC     = caseWin.tCenter.(char(group)); end

plot_case_one(data, out, pred_k, gt_idx, figName, "工况" + group + "：" + fileName, cfg, ...
    'padSec', padSec, 'tCenter', tC);
    end
end

%% 3.5) Extra figures for thesis placeholders (auto-generated)
% These figures are referenced by the Chapter-4 LaTeX placeholders under images/.
try
    make_thesis_figures(rep, cfg, p, figOpt);
catch ME
    disp(getReport(ME,'extended','hyperlinks','off'));
    warning('[Fig] make_thesis_figures failed: %s', ME.message);
    if figOpt.strict
        rethrow(ME);
    end
end

%% 4) Save E1 tables
writetable(T_file, fullfile(p.out, "E1_per_file.csv"));

T_group = summarize_by_group(T_file);
writetable(T_group, fullfile(p.out, "E1_by_group.csv"));

% ---- LaTeX table row files for direct \input{} in thesis ----
write_tex_bycase_rows(T_group, fullfile(p.tables_dir, 'ch4_bycase_global_rows.tex'));


disp("=== By Group (IoU>=0.50) ===");
disp(T_group);

%% 5) Dataset statistics (E0)
T_ds = dataset_stats_from_outputs(GT, T_file);
writetable(T_ds, fullfile(p.out, "E0_dataset_stats.csv"));
write_tex_dataset_rows(T_ds, fullfile(p.tables_dir, 'ch4_dataset_rows.tex'));


%% 6) Timing statistics (E1 timing)
T_timing = timing_stats_by_group(tim_rows);
writetable(T_timing, fullfile(p.out, "E1_timing_by_group.csv"));
write_tex_timing_rows(T_timing, fullfile(p.tables_dir, 'ch4_timing_global_rows.tex'));


%% 7) E2 plots (A/B/C) -> mapped to thesis placeholders
%  - D_th distribution  -> images/ch4_param_scan_Dth.pdf
%  - dist_th distribution -> images/ch4_param_scan_dist.pdf
%  - C-group seek/degrade ratio -> images/ch4_C_seek_ratio.pdf (optional)

if ~isempty(A_drift_mag)
    fig = ch4_newfig(16, 8);
    ax = axes(fig); hold(ax,'on'); grid(ax,'on');

    v0 = A_drift_mag(A_is_park==0);
    v1 = A_drift_mag(A_is_park==1);

    edges = ch4_hist_edges(A_drift_mag, 30);
    cc = (edges(1:end-1) + edges(2:end)) / 2;
    p0 = histcounts(v0, edges, 'Normalization','probability');
    p1 = histcounts(v1, edges, 'Normalization','probability');

    plot(ax, cc, p0, '-',  'LineWidth', 1.4);
    plot(ax, cc, p1, '--', 'LineWidth', 1.4);

    yl = ylim(ax);
    plot(ax, [cfg.pk.D_th cfg.pk.D_th], yl, ':', 'LineWidth', 1.2);
    ylim(ax, yl);
    text(ax, cfg.pk.D_th, yl(2), sprintf('  D_{th}=%.1f', cfg.pk.D_th), ...
        'VerticalAlignment','top', 'HorizontalAlignment','left', 'FontSize', 9);

    xlabel(ax, '漂移幅值 ||\Delta B||_2'); ylabel(ax, '概率');
    legend(ax, {'通过/干扰', '停车到达'}, 'Location','best');
    title(ax, 'A类：漂移幅值分布');

    ch4_apply_style(fig);
    ch4_export_fig(fig, fullfile(p.images_dir, 'ch4_param_scan_Dth.pdf'));
    close(fig);
end

if ~isempty(B_dist)
    fig = ch4_newfig(10, 6);
    ax = axes(fig); hold(ax,'on'); grid(ax,'on');

    d_keep  = B_dist((~B_is_leave) & ~isnan(B_dist));
    d_leave = B_dist(( B_is_leave) & ~isnan(B_dist));

    edges = ch4_hist_edges(d_keep, 25);
    p_keep = histcounts(d_keep, edges, 'Normalization','probability');
    x = edges(1:end-1);
    plot(ax, x, p_keep, 'LineWidth', 1.8);

    leg = {'仍占用扰动事件'};
    if numel(d_leave) >= 5
        p_leave = histcounts(d_leave, edges, 'Normalization','probability');
        plot(ax, x, p_leave, '--', 'LineWidth', 1.8);
        leg = {'仍占用扰动事件', '驶离事件（若dist有效）'};
    else
        text(ax, 0.02, 0.10, '注：驶离多由 D_{free}(back2env) 判决，dist样本可能缺失', ...
            'Units','normalized', 'FontSize', 10, 'Color', [0.3 0.3 0.3]);
    end

    xline(ax, cfg.pk.dist_th, ':', sprintf('dist_{th}=%.1f', cfg.pk.dist_th), 'LineWidth', 1.2);

    if ~isempty(d_keep)
        acc = mean(d_keep < cfg.pk.dist_th);
        text(ax, 0.02, 0.90, sprintf('Acc@dist_{th}=%.1f%%', 100*acc), ...
            'Units','normalized', 'FontSize', 11, 'Color', [0.1 0.1 0.1]);
    end

    xlabel(ax, 'dist');
    ylabel(ax, '概率');
    legend(ax, leg, 'Location', 'best');
    title(ax, '验证集：dist 分布与 dist_{th}（占用稳态门控）');
    ch4_apply_style(fig);
    ch4_export_fig(fig, fullfile(p.images_dir, 'ch4_param_scan_dist.pdf'));
    close(fig);
end

if ~isempty(C_stable_found)
    r_found = mean(C_stable_found);
    r_deg   = mean(C_used_degrade);

    fig = ch4_newfig(10, 6);
    ax = axes(fig);
    bar(ax, [r_found, r_deg]);
    set(ax, 'XTickLabel', {'稳定点可得','退化分支'});
    ylim(ax, [0 1]);
    ylabel(ax, '比例');
    title(ax, 'C类：稳定点可得率与退化分支使用率');

    % annotate
    for i = 1:2
        val = [r_found, r_deg];
        text(ax, i, val(i)+0.03, sprintf('%.2f', val(i)), 'HorizontalAlignment','center', 'FontSize',9);
    end

    ch4_apply_style(fig);
    ch4_export_fig(fig, fullfile(p.images_dir, 'ch4_C_seek_ratio.pdf'));
    close(fig);
end

% ---- Sensitivity / threshold sweep figure (optional but recommended) ----
% This figure is referenced by the LaTeX placeholder: images/ch4_sensitivity.pdf
try
    plot_sensitivity_fig(A_drift_mag, A_is_park, B_dist, B_is_leave, cfg, p);
catch ME
    disp(getReport(ME,'extended','hyperlinks','off'));
    warning('[Fig] plot_sensitivity_fig failed: %s', ME.message);
    if figOpt.strict
        rethrow(ME);
    end
end

%% 8) E3 Ablation study (optional, but recommended)
DO_ABLATION = true;
if DO_ABLATION
    variants = {
        "Ours",            struct();
        "Abl_noMeanDiff",  struct('use_mean_diff', false);
        "Abl_noSimilarity",struct('use_similarity', false);
        "Abl_noDegrade",   struct('use_degrade', false);
        "Abl_noUpdateGate",struct('use_update_gate', false);
    };

    T_ab = table('Size',[0 7], ...
        'VariableTypes',{'string','double','double','double','double','double','double'}, ...
        'VariableNames',{'variant','F1_all','F1_A','F1_B','F1_C','F1_D','TP_all'});

    for v = 1:size(variants,1)
        name = variants{v,1};
        mod  = variants{v,2};

        cfgv = cfg;
        if isfield(mod,'use_mean_diff');   cfgv.v.use_mean_diff   = mod.use_mean_diff; end
        if isfield(mod,'use_similarity');  cfgv.v.use_similarity  = mod.use_similarity; end
        if isfield(mod,'use_degrade');     cfgv.v.use_degrade     = mod.use_degrade; end
        if isfield(mod,'use_update_gate'); cfgv.v.use_update_gate = mod.use_update_gate; end

        Tv = run_eval_only(files, GT, p, cfgv, post, IOU_TH);
        Tg = summarize_by_group(Tv);

        f1_all = Tg.F1(Tg.group=="ALL");
        f1A = Tg.F1(Tg.group=="A");
        f1B = Tg.F1(Tg.group=="B");
        f1C = Tg.F1(Tg.group=="C");
        f1D = Tg.F1(Tg.group=="D");
        TPall = Tg.TP(Tg.group=="ALL");

        T_ab = [T_ab; {name, f1_all, f1A, f1B, f1C, f1D, TPall}]; %#ok<AGROW>
    end

    writetable(T_ab, fullfile(p.out, "E3_ablation_by_group.csv"));
    write_tex_ablation_rows(T_ab, fullfile(p.tables_dir, 'ch4_ablation_global_rows.tex'));

    disp("=== Ablation (GLOBAL) ==="); disp(T_ab);
end

%% 8.5) Optional figure pool and extra examples (for selection)
% These figures are NOT referenced by the LaTeX placeholders by default.
% They are generated as "ch4_opt_*" and "ch4_case_*_{best/mid/worst/rand}_padXs" for you to choose.

if isfield(figOpt,'extra_pool') && figOpt.extra_pool
    try
        if exist('T_ab','var')
            Tab = T_ab;
        else
            Tab = table();
        end
        make_optional_fig_pool(T_file, T_group, T_ds, T_timing, tim_rows, ...
            A_drift_mag, A_is_park, B_dist, B_is_leave, C_file, Tab, cfg, p, figOpt);
    catch ME
        disp(getReport(ME,'extended','hyperlinks','off'));
        warning('[Fig] make_optional_fig_pool failed: %s', ME.message);
        if figOpt.strict
            rethrow(ME);
        end
    end
end

% Optional: create alias copies without the opt_ prefix so LaTeX can use clean filenames
if isfield(figOpt,'make_alias_without_opt') && figOpt.make_alias_without_opt
    try
        ch4_make_aliases_without_opt(p, figOpt);
    catch ME
        disp(getReport(ME,'extended','hyperlinks','off'));
        warning('[Fig] ch4_make_aliases_without_opt failed: %s', ME.message);
        if figOpt.strict
            rethrow(ME);
        end
    end
end

if isfield(figOpt,'extra_examples') && figOpt.extra_examples
    try
        make_extra_examples(T_file, GT, p, cfg, post, IOU_TH, figOpt);
    catch ME
        disp(getReport(ME,'extended','hyperlinks','off'));
        warning('[Fig] make_extra_examples failed: %s', ME.message);
        if figOpt.strict
            rethrow(ME);
        end
    end
end

%% 9) Report figure outputs and (optionally) generate placeholders
expectedFigs = {
    % --- Figures referenced by the Chapter-4 LaTeX (recommended set) ---
    'ch4_pass_vs_park'
    'ch4_pipeline_auto'
    'ch4_fsm_degrade_auto'
    'ch4_stability_demo'
    'ch4_param_scan_Dth'
    'ch4_param_scan_dist'
    'ch4_scene_photo'          % placeholder (replace by real photo)
    'ch4_setup_schematic'      % placeholder (redraw for publication)
    'ch4_opt_dataset_stats'
    'ch4_opt_prf_by_group'
    'ch4_opt_timing_tau_box'
    'ch4_opt_timing_tau_cdf'
    'ch4_C_seek_ratio'
    'ch4_opt_ablation_by_group'
    'ch4_sensitivity'
    'ch4_case_A'
    'ch4_case_B'
    'ch4_case_C'
    'ch4_case_D'

    % --- Compatibility aliases (clean names without opt_/auto) ---
    'ch4_pipeline'
    'ch4_fsm_degrade'
    'ch4_dataset_stats'
    'ch4_prf_by_group'
    'ch4_timing_tau_box'
    'ch4_timing_tau_cdf'
    'ch4_ablation_by_group'
    'ch4_ablation_fig'
};

ch4_report_fig_status(p, expectedFigs, figOpt);

% Export curated paper figures to a separate folder (optional)
if isfield(figOpt,'export_paper_figs') && figOpt.export_paper_figs
    ch4_export_paper_figs(p, figOpt);
end

disp("Done. All outputs saved under: " + string(p.out));

%% ================= Local helper functions =================

function [pred2, conf2] = postprocess_pred_conf(pred_k, conf_k, fs, Tmin_sec, gap_merge_sec)
    if isempty(pred_k)
        pred2 = pred_k; conf2 = conf_k; return;
    end
    dur_sec = (pred_k(:,2) - pred_k(:,1)) / fs;
    keep = dur_sec >= Tmin_sec;
    pred_k = pred_k(keep,:);
    conf_k = conf_k(keep,:);

    if isempty(pred_k) || gap_merge_sec <= 0 || size(pred_k,1) <= 1
        pred2 = pred_k; conf2 = conf_k; return;
    end

    [~,ord] = sort(pred_k(:,1));
    pred_k = pred_k(ord,:);
    conf_k = conf_k(ord,:);

    gap_k = round(gap_merge_sec * fs);

    pred2 = pred_k(1,:);
    conf2 = conf_k(1,:);
    for i = 2:size(pred_k,1)
        if pred_k(i,1) - pred2(end,2) <= gap_k
            pred2(end,2) = max(pred2(end,2), pred_k(i,2));
            conf2(end,2) = conf_k(i,2); % take the latest confirmation out
        else
            pred2 = [pred2; pred_k(i,:)]; %#ok<AGROW>
            conf2 = [conf2; conf_k(i,:)]; %#ok<AGROW>
        end
    end
end

function [arrIdx, leaveIdx] = match_events_to_gt(events, gt_idx, tol_k)
    arrIdx = [];
    leaveIdx = [];
    if isempty(events) || isempty(gt_idx); return; end
    kout = zeros(numel(events),1);
    for i = 1:numel(events); kout(i) = events(i).k_out; end

    for j = 1:size(gt_idx,1)
        kin  = gt_idx(j,1);
        kout_gt = gt_idx(j,2);

        [d1, i1] = min(abs(kout - kin));
        if d1 <= tol_k; arrIdx(end+1) = i1; end %#ok<AGROW>

        [d2, i2] = min(abs(kout - kout_gt));
        if d2 <= tol_k; leaveIdx(end+1) = i2; end %#ok<AGROW>
    end
    arrIdx   = unique(arrIdx);
    leaveIdx = unique(leaveIdx);
end

function T_group = summarize_by_group(T_file)
    groups = ["A","B","C","D"];
    rows = {};
    for g = groups
        Tf = T_file(T_file.group == g, :);
        TP = sum(Tf.TP); FP = sum(Tf.FP); FN = sum(Tf.FN);
        [P,R,F1] = prf(TP,FP,FN);
        Ngt = TP + FN;
        Rf = FP / max(Ngt,1);
        Rm = FN / max(Ngt,1);
        rows(end+1,:) = {g, TP, FP, FN, P, R, F1, Rf, Rm}; %#ok<AGROW>
    end
    TP = sum(T_file.TP); FP = sum(T_file.FP); FN = sum(T_file.FN);
    [P,R,F1] = prf(TP,FP,FN);
    Ngt = TP + FN;
    Rf = FP / max(Ngt,1);
    Rm = FN / max(Ngt,1);
    rows(end+1,:) = {"ALL", TP, FP, FN, P, R, F1, Rf, Rm}; %#ok<AGROW>

    T_group = cell2table(rows, ...
        'VariableNames',{'group','TP','FP','FN','P','R','F1','Rf','Rm'});
end

function [P,R,F1] = prf(TP,FP,FN)
    P = TP / max(TP+FP, 1);
    R = TP / max(TP+FN, 1);
    F1 = 2*P*R / max(P+R, eps);
end

function T_ds = dataset_stats_from_outputs(GT, T_file)
    groups = ["A","B","C","D"];
    rows = {};
    for g = groups
        files_g = unique(GT.file(GT.scenario_group==g), 'stable');
        Tf = T_file(T_file.group==g,:);
        nFiles = numel(files_g);
        Ngt = sum(Tf.gt);
        Nevents = sum(Tf.events);
        Npass = max(Nevents - 2*Ngt, 0);
        rows(end+1,:) = {g, nFiles, Ngt, Nevents, Npass}; %#ok<AGROW>
    end
    T_ds = cell2table(rows, 'VariableNames',{'group','num_files','num_parking_gt','num_vehicle_events','num_pass_est'});
end

function T_timing = timing_stats_by_group(tim_rows)
    groups = ["A","B","C","D","ALL"];
    rows = {};
    for g = groups
        if g == "ALL"
            Tr = tim_rows;
        else
            Tr = tim_rows(tim_rows.group==g,:);
        end
        if isempty(Tr)
            rows(end+1,:) = {g, 0, NaN, NaN, NaN, NaN, NaN, NaN}; %#ok<AGROW>
            continue;
        end
        med_abs_dt_in  = median(abs(Tr.dt_in));
        med_abs_dt_out = median(abs(Tr.dt_out));
        med_tau_in  = median(Tr.tau_in);
        med_tau_out = median(Tr.tau_out);
        p95_tau_in  = prctile(Tr.tau_in, 95);
        p95_tau_out = prctile(Tr.tau_out, 95);
        rows(end+1,:) = {g, height(Tr), med_abs_dt_in, med_abs_dt_out, med_tau_in, med_tau_out, p95_tau_in, p95_tau_out}; %#ok<AGROW>
    end
    T_timing = cell2table(rows, 'VariableNames', ...
        {'group','N_TP','med_abs_dt_in','med_abs_dt_out','med_tau_in','med_tau_out','p95_tau_in','p95_tau_out'});
end

% function plot_case_one(data, out, pred_k, gt_idx, figPath, figTitle, cfg, varargin)
% %PLOT_CASE_ONE Event-level case visualization (compact, thesis-friendly).
% %
% % 目标：避免整段文件绘制导致四宫格缩放后不可读。默认以“代表性事件中心”
% % 截取 t0±padSec 的窗口，并在图中叠加 GT 与算法输出区间。
% %
% % 子图（自上而下）：
% % 1) 相对幅值 ||B - S_{pre}(0)||_2（S_{pre}(0) 为文件起始参考均值）
% % 2) stable flag（稳定判据是否满足）
% % 3) GT vs Pred 占用区间（条带显示，便于答辩解释）
% 
% % Backward compatibility: allow a positional numeric padSec as the first varargin element
% posPadSec = [];
% if ~isempty(varargin) && isnumeric(varargin{1})
%     posPadSec = varargin{1};
%     varargin = varargin(2:end);
% end
% 
% defaultSigMode = 'rel';
% if isfield(cfg,'fig') && isfield(cfg.fig,'case_sigMode')
%     defaultSigMode = cfg.fig.case_sigMode;
% end
% 
% ip = inputParser;
% addParameter(ip, 'padSec', 30, @(x)isnumeric(x)&&isscalar(x)&&x>0);
% addParameter(ip, 'tCenter', [], @(x)isempty(x)||(isnumeric(x)&&isscalar(x)));
% addParameter(ip, 'centerMode', 'auto', @(s)ischar(s)||isstring(s));
% addParameter(ip, 'sigMode', defaultSigMode, @(s) ischar(s) || isstring(s));
% parse(ip, varargin{:});
% padSec    = ip.Results.padSec;
% if ~isempty(posPadSec); padSec = posPadSec; end
% tCenter   = ip.Results.tCenter;
% centerMode = char(ip.Results.centerMode);
% sigMode   = lower(strtrim(char(ip.Results.sigMode)));
% 
% t = data.t(:);
% n = numel(t);
% 
% % Reference baseline (initial)
% k_ref = 1 : min(n, max(1, round(2*cfg.fs)));
% S_ref = mean(data.B(k_ref,:), 1);
% relB = vecnorm(data.B - S_ref, 2, 2);
% % --- display mode (signal shown in subplot-1) ---
% % case 图（证据链闭环）推荐三轴扰动；wave 图可用单轴增强直观性。
% needLegend = false;
% legLabels  = {};
% if any(strcmp(sigMode, {'dxyz','xyz','3axis','tri','three'}))
%     % 三轴扰动（相对参考点 S_ref），更贴合“输入→判据→输出”的可解释链条
%     showSig = data.B - S_ref;            % N×3
%     ylab1   = '$\Delta B\ (nT)$';
%     drawDth = false;
%     needLegend = true;
%     legLabels  = {'$\Delta B_x$','$\Delta B_y$','$\Delta B_z$'};
% elseif any(strcmp(sigMode, {'bx','x'}))
%     showSig = data.B(:,1) - S_ref(1);
%     ylab1   = '$\Delta B_x\ (nT)$';
%     drawDth = false;
% elseif any(strcmp(sigMode, {'norm','mag'}))
%     showSig = vecnorm(data.B, 2, 2);
%     ylab1   = '$\|B\|_2$';
%     drawDth = false;
% else
%     % 标量残差（更利于跨文件对比/对齐阈值含义）
%     showSig = relB;
%     ylab1   = '$\|B-S_{ref}\|_2$';
%     drawDth = true;
% end
% 
% % Choose center index k0
% if ~isempty(tCenter)
%     [~, k0] = min(abs(t - tCenter));
% else
%     k0 = pick_case_center_k(figTitle, relB, out, pred_k, gt_idx, cfg, centerMode);
% end
% 
% pad = round(padSec * cfg.fs);
% k1 = max(1, k0 - pad);
% k2 = min(n, k0 + pad);
% 
% fig = figure('Visible','off','Color','w','Position',[80 80 1200 720]);
% tl = tiledlayout(fig, 3, 1, 'Padding','compact', 'TileSpacing','compact');
% 
% % ---------- (1) Relative magnitude ----------
% ax1 = nexttile(tl, 1); hold(ax1,'on'); box(ax1,'on'); grid(ax1,'on');
% plot(ax1, t(k1:k2), showSig(k1:k2,:), 'LineWidth', 1.3);
% ylabel(ax1, ylab1, 'Interpreter','latex');
% if drawDth
%     yline(ax1, cfg.D_th, '--', 'LineWidth', 1.0);
% end
% title(ax1, figTitle, 'Interpreter','none');
% 
% % Legend for 3-axis display
% if needLegend
%     lg = legend(ax1, legLabels, 'Location','northeast');
%     set(lg, 'Interpreter','latex', 'FontSize', 8, 'Box', 'off');
% end
% 
% % Overlay GT / Pred occupancy (full-height shading)
% if ~isempty(pred_k)
%     add_interval_patches(ax1, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.22);
% end
% if ~isempty(gt_idx)
%     add_interval_patches(ax1, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.18);
% end
% xline(ax1, t(k0), ':', 'LineWidth', 1.0);
% 
% % ---------- (2) Stability flag ----------
% ax2 = nexttile(tl, 2); hold(ax2,'on'); box(ax2,'on'); grid(ax2,'on');
% if isfield(out,'stable') && ~isempty(out.stable)
%     st = out.stable(:);
%     if numel(st) >= n
%         st = st(1:n);
%     else
%         st = [st; zeros(n-numel(st),1)];
%     end
% else
%     st = zeros(n,1);
% end
% plot(ax2, t(k1:k2), st(k1:k2), 'LineWidth', 1.2);
% ylim(ax2, [-0.1 1.1]);
% ylabel(ax2, 'stable');
% xline(ax2, t(k0), ':', 'LineWidth', 1.0);
% 
% % ---------- (3) GT vs Pred bars ----------
% ax3 = nexttile(tl, 3); hold(ax3,'on'); box(ax3,'on');
% xlim(ax3, [t(k1) t(k2)]);
% ylim(ax3, [0 1]);
% yticks(ax3, [0.25 0.75]);
% yticklabels(ax3, {'Pred','GT'});
% xlabel(ax3, '时间/s');
% 
% if ~isempty(pred_k)
%     add_interval_bars(ax3, t, pred_k, k1, k2, 0.10, 0.40, [0.80 0.90 1.00], 0.85);
% end
% if ~isempty(gt_idx)
%     add_interval_bars(ax3, t, gt_idx,  k1, k2, 0.60, 0.90, [0.86 0.86 0.86], 0.85);
% end
% xline(ax3, t(k0), ':', 'LineWidth', 1.0);
% 
% linkaxes([ax1 ax2 ax3], 'x');
% 
% ch4_export_fig(fig, figPath);
% close(fig);
% end


function plot_case_one(data, out, pred_k, gt_idx, figPath, figTitle, cfg, varargin)
%PLOT_CASE_ONE  Thesis-ready case visualization (4 rows).
%
% Row-1: 三轴扰动 ΔB = B - S_ref,   S_ref = 事件前(文件起始) 2s 均值
% Row-2: 主判据曲线 D(t)=||B - S_pre(t)||_2 + 阈值线（D_th / D_free）
%        可选：叠加 dist 事件点 + dist_th（若 out.dbg.dist 存在）
% Row-3: 内部逻辑条带：stableState / degrade / dist_gate / update_gate(限幅)
% Row-4: GT vs Pred 占用条带（结论图层）
%
% Optional name-value:
%   'padSec'    : window half width in seconds
%   'tCenter'   : manual center time (sec)
%   'centerMode': 'auto' (default) | 'midfile'

% --- backward compatibility: allow positional numeric padSec ---
posPadSec = [];
if ~isempty(varargin) && isnumeric(varargin{1})
    posPadSec = varargin{1};
    varargin = varargin(2:end);
end

% --- defaults ---
defaultSigMode = 'dxyz';
if isfield(cfg,'fig') && isfield(cfg.fig,'case_sigMode')
    defaultSigMode = cfg.fig.case_sigMode;
end

ip = inputParser;
addParameter(ip, 'padSec', 30, @(x)isnumeric(x)&&isscalar(x)&&x>0);
addParameter(ip, 'tCenter', [], @(x)isempty(x)||(isnumeric(x)&&isscalar(x)));
addParameter(ip, 'centerMode', 'auto', @(s)ischar(s)||isstring(s));
addParameter(ip, 'sigMode', defaultSigMode, @(s)ischar(s)||isstring(s));
parse(ip, varargin{:});

padSec     = ip.Results.padSec;
if ~isempty(posPadSec); padSec = posPadSec; end
tCenter    = ip.Results.tCenter;
centerMode = char(ip.Results.centerMode);
sigMode    = lower(strtrim(char(ip.Results.sigMode)));

t = data.t(:);
B = data.B;
n = numel(t);

% ---------- S_ref: file-begin 2s mean ----------
k_ref = 1 : min(n, max(1, round(2*cfg.fs)));
S_ref = mean(B(k_ref,:), 1);

% ---------- choose k0 ----------
relB0 = vecnorm(B - S_ref, 2, 2); % for center picking heuristic
if ~isempty(tCenter)
    [~, k0] = min(abs(t - tCenter));
else
    k0 = pick_case_center_k(figTitle, relB0, out, pred_k, gt_idx, cfg, centerMode);
end

pad = round(padSec * cfg.fs);
k1 = max(1, k0 - pad);
k2 = min(n, k0 + pad);

% ---------- signals for plotting ----------
% Row-1 signal: default use dxyz (ΔB)
if any(strcmp(sigMode, {'dxyz','xyz','3axis','tri','three'}))
    sig1 = B - S_ref;          % Nx3
    ylab1 = 'ΔB / nT';
    showLegend1 = true;
else
    sig1 = relB0;              % Nx1
    ylab1 = '||B-S_{ref}||_2 / nT';
    showLegend1 = false;
end

% stableState (fix: prefer out.st.stableState)
stable = ch4_get_stable_vec(out, n);

% Baseline trace (S_pre(t)) reconstructed for visualization
[S_pre_tr, updLimited] = ch4_build_Spre_trace(data, out, pred_k, cfg, S_ref, stable);

% Row-2 main criterion: D(t)=||B-S_pre(t)||_2
D = vecnorm(B - S_pre_tr, 2, 2);

% dist (event-level) -> scatter series at event k_out
distSeries = ch4_event_value_series(n, out, "dist");

% Row-3 internal flags -> segments (bars)
fs = cfg.fs;
stableSeg  = ch4_binary_to_segments(stable);
degradeSeg = ch4_eventflag_to_segments(n, out, "used_degrade", round(0.6*fs)); % ±0.6s
distKeepSeg = ch4_event_distkeep_segments(n, out, cfg, round(0.6*fs));         % ±0.6s
updLimSeg  = ch4_binary_to_segments(updLimited);

% ---------- figure ----------
fig = figure('Visible','off','Color','w','Position',[80 80 1200 900]);
tl = tiledlayout(fig, 4, 1, 'Padding','compact', 'TileSpacing','compact');

% ===== Row 1: ΔB three-axis =====
ax1 = nexttile(tl, 1); hold(ax1,'on'); box(ax1,'on'); grid(ax1,'on');

% 先画曲线，让坐标轴根据数据自动缩放（避免被背景patch锁死在[0,1]）
plot(ax1, t(k1:k2), sig1(k1:k2,:), 'LineWidth', 1.2);

if showLegend1
    h0 = yline(ax1, 0, 'r--', 'LineWidth', 1.0); % baseline y=0 (ΔB)
    try, h0.HandleVisibility = 'off'; catch, end
    lg = legend(ax1, {'ΔB_x','ΔB_y','ΔB_z'}, 'Location','northeast');
    lg.Box = 'off';
    try, lg.AutoUpdate = 'off'; catch, end
end
ylabel(ax1, ylab1);
title(ax1, figTitle, 'Interpreter','none');

% 再加 GT/Pred 背景遮罩（patch 会固定当前 ylim，必须放在曲线之后）
if ~isempty(pred_k), add_interval_patches(ax1, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.18); end
if ~isempty(gt_idx), add_interval_patches(ax1, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.16); end

hx = xline(ax1, t(k0), ':', 'LineWidth', 1.0);
try, hx.HandleVisibility = 'off'; catch, end

% ===== Row 2: main criterion D(t) + thresholds (and optional dist) =====
ax2 = nexttile(tl, 2); hold(ax2,'on'); box(ax2,'on'); grid(ax2,'on');

yyaxis(ax2, 'left');
plot(ax2, t(k1:k2), D(k1:k2), 'LineWidth', 1.2);
ylabel(ax2, 'D(t)=||B-S_{pre}(t)||_2 / nT');

% thresholds (if fields exist) + 强制把阈值纳入 ylim，避免阈值线被裁掉
thVals = [];
if isfield(cfg,'pk') && isfield(cfg.pk,'D_th')
    yline_if(ax2, cfg.pk.D_th, '--', sprintf('D_{th}=%.1f', cfg.pk.D_th));
    thVals(end+1,1) = cfg.pk.D_th; %#ok<AGROW>
end
if isfield(cfg,'pk') && isfield(cfg.pk,'D_free')
    yline_if(ax2, cfg.pk.D_free, ':', sprintf('D_{free}=%.1f', cfg.pk.D_free));
    thVals(end+1,1) = cfg.pk.D_free; %#ok<AGROW>
end

dseg = D(k1:k2);
dseg = dseg(isfinite(dseg));
if isempty(dseg)
    dseg = 0;
end
allv = [dseg(:); thVals(:)];
lo = min(allv);
hi = max(allv);
if ~isfinite(lo) || ~isfinite(hi) || lo == hi
    lo = 0; hi = lo + 1;
end
marg = 0.05 * (hi - lo);
ylim(ax2, [lo - marg, hi + marg]);

% 背景遮罩必须放在曲线之后（add_interval_patches 会固定当前 ylim）
if ~isempty(pred_k), add_interval_patches(ax2, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.12); end
if ~isempty(gt_idx), add_interval_patches(ax2, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.10); end

% optional dist on right axis
hasDist = any(isfinite(distSeries(k1:k2)));
if hasDist
    yyaxis(ax2, 'right');
    idx = find(isfinite(distSeries));
    idx = idx(idx>=k1 & idx<=k2);
    plot(ax2, t(idx), distSeries(idx), 'o', 'MarkerSize', 4, 'LineWidth', 1.0);
    ylabel(ax2, 'dist（事件点）');
    if isfield(cfg,'pk') && isfield(cfg.pk,'dist_th')
        yline_if(ax2, cfg.pk.dist_th, '--', sprintf('dist_{th}=%.1f', cfg.pk.dist_th));
    end
end

hx = xline(ax2, t(k0), ':', 'LineWidth', 1.0);
try, hx.HandleVisibility = 'off'; catch, end

% ===== Row 3: internal logic bars =====
ax3 = nexttile(tl, 3); hold(ax3,'on'); box(ax3,'on');
xlim(ax3, [t(k1) t(k2)]);
ylim(ax3, [0 1]);
grid(ax3,'on');

% optionally shade GT/Pred to align reading
if ~isempty(pred_k), add_interval_patches(ax3, t, pred_k, k1, k2, [0.80 0.90 1.00], 0.08); end
if ~isempty(gt_idx), add_interval_patches(ax3, t, gt_idx,  k1, k2, [0.86 0.86 0.86], 0.06); end

% bars at different y-levels to avoid overlap
% stable
add_interval_bars(ax3, t, stableSeg,   k1, k2, 0.78, 0.95, [0.70 0.90 0.70], 0.85);
% degrade
add_interval_bars(ax3, t, degradeSeg,  k1, k2, 0.56, 0.72, [1.00 0.86 0.65], 0.85);
% dist gate (keep occ)
add_interval_bars(ax3, t, distKeepSeg, k1, k2, 0.34, 0.50, [0.80 0.90 1.00], 0.85);
% update gate limited
add_interval_bars(ax3, t, updLimSeg,   k1, k2, 0.12, 0.28, [1.00 0.75 0.75], 0.85);

yticks(ax3, [0.20 0.42 0.64 0.865]);
yticklabels(ax3, {'upd\_limit','dist\_gate','degrade','stable'});

ylabel(ax3, '内部逻辑');
xline(ax3, t(k0), ':', 'LineWidth', 1.0);

% ===== Row 4: GT vs Pred occupancy bars =====
ax4 = nexttile(tl, 4); hold(ax4,'on'); box(ax4,'on');
xlim(ax4, [t(k1) t(k2)]);
ylim(ax4, [0 1]);
yticks(ax4, [0.25 0.75]);
yticklabels(ax4, {'Pred','GT'});
xlabel(ax4, '时间 / s');

if ~isempty(pred_k)
    add_interval_bars(ax4, t, pred_k, k1, k2, 0.10, 0.40, [0.80 0.90 1.00], 0.85);
end
if ~isempty(gt_idx)
    add_interval_bars(ax4, t, gt_idx,  k1, k2, 0.60, 0.90, [0.86 0.86 0.86], 0.85);
end
xline(ax4, t(k0), ':', 'LineWidth', 1.0);

linkaxes([ax1 ax2 ax3 ax4], 'x');

% style + export
try
    ch4_apply_style(fig);
catch
end
ch4_export_fig(fig, figPath);
close(fig);
end

%% ===================== helpers for case plot =====================

function stable = ch4_get_stable_vec(out, n)
% robust stableState extraction (avoid all-zeros)
stable = [];
if isfield(out,'st') && isfield(out.st,'stableState')
    stable = out.st.stableState;
elseif isfield(out,'stable')
    stable = out.stable;
elseif isfield(out,'flags') && isfield(out.flags,'stable')
    stable = out.flags.stable;
end
if isempty(stable)
    stable = zeros(n,1);
else
    stable = double(stable(:));
    if numel(stable) < n
        stable = [stable; zeros(n-numel(stable),1)];
    else
        stable = stable(1:n);
    end
end
end

function [S_pre_tr, updLimited] = ch4_build_Spre_trace(data, out, pred_k, cfg, S_ref, stable)
% Reconstruct a visualization-only baseline S_pre(t) (piecewise updates at stable points).
B = data.B;
n = size(B,1);
S_pre_tr = zeros(n,3);
updLimited = zeros(n,1);

% if no ref config -> constant
if ~isfield(cfg,'ref') || ~isfield(cfg.ref,'enable') || ~cfg.ref.enable
    for k = 1:n
        S_pre_tr(k,:) = S_ref;
    end
    return;
end

alpha = cfg.ref.alpha_free;
useGate = isfield(cfg,'v') && isfield(cfg.v,'use_update_gate') && cfg.v.use_update_gate ...
          && isfield(cfg.ref,'D_upd');

% occupancy mask from pred (avoid updating during occupied)
occ = false(n,1);
if ~isempty(pred_k)
    for i = 1:size(pred_k,1)
        a = max(1, round(pred_k(i,1)));
        b = min(n, round(pred_k(i,2)));
        if b >= a
            occ(a:b) = true;
        end
    end
end

% need meanVec
meanVec = [];
if isfield(out,'st') && isfield(out.st,'meanVec')
    meanVec = out.st.meanVec;
end

S_pre = S_ref;
for k = 1:n
    S_pre_tr(k,:) = S_pre;

    if occ(k), continue; end
    if stable(k) <= 0.5, continue; end

    if ~isempty(meanVec) && k <= size(meanVec,1)
        S_cand = meanVec(k,:);
    else
        % fallback: local mean over 0.5s
        L = max(1, round(0.5*cfg.fs));
        a = max(1, k-L+1);
        S_cand = mean(B(a:k,:), 1);
    end

    if any(~isfinite(S_cand)), continue; end

    d = S_cand - S_pre;
    nd = norm(d,2);

    if useGate && nd > cfg.ref.D_upd
        updLimited(k) = 1;
        S_pre = S_pre + alpha * (cfg.ref.D_upd / max(nd, eps)) * d;
    else
        S_pre = (1-alpha)*S_pre + alpha*S_cand;
    end
end
end

function segs = ch4_binary_to_segments(sig)
sig = sig(:) > 0.5;
d = diff([false; sig; false]);
st = find(d==1);
ed = find(d==-1) - 1;
segs = [st ed];
end

function segs = ch4_eventflag_to_segments(n, out, fieldName, halfWin)
segs = zeros(0,2);
if ~isfield(out,'events') || isempty(out.events), return; end
if ~isfield(out,'dbg') || ~isfield(out.dbg, fieldName), return; end
flag = out.dbg.(fieldName);
mmax = min(numel(out.events), numel(flag));
for m = 1:mmax
    if ~flag(m), continue; end
    k = round(out.events(m).k_out);
    a = max(1, k-halfWin);
    b = min(n, k+halfWin);
    segs(end+1,:) = [a b]; %#ok<AGROW>
end
end

function segs = ch4_event_distkeep_segments(n, out, cfg, halfWin)
% dist gate: dist < dist_th  (keep occupied)
segs = zeros(0,2);
if ~isfield(out,'events') || isempty(out.events), return; end
if ~isfield(out,'dbg') || ~isfield(out.dbg,'dist'), return; end
if ~isfield(cfg,'pk') || ~isfield(cfg.pk,'dist_th'), return; end

dist = out.dbg.dist(:);
mmax = min(numel(out.events), numel(dist));
for m = 1:mmax
    if ~isfinite(dist(m)), continue; end
    if dist(m) >= cfg.pk.dist_th, continue; end
    k = round(out.events(m).k_out);
    a = max(1, k-halfWin);
    b = min(n, k+halfWin);
    segs(end+1,:) = [a b]; %#ok<AGROW>
end
end

function vSeries = ch4_event_value_series(n, out, which)
vSeries = nan(n,1);
if ~isfield(out,'events') || isempty(out.events), return; end
if ~isfield(out,'dbg') || ~isfield(out.dbg, which), return; end
v = out.dbg.(which)(:);
mmax = min(numel(out.events), numel(v));
for m = 1:mmax
    k = round(out.events(m).k_out);
    if k>=1 && k<=n
        vSeries(k) = v(m);
    end
end
end



function k0 = pick_case_center_k(figTitle, relB, out, pred_k, gt_idx, cfg, centerMode)
%PICK_CASE_CENTER_K Heuristic event-level window center selection.
%
% - A: center at GT arrival (occ_in)
% - B: center at strongest internal disturbance event within GT occupancy
% - C: center at first degrade/no-stable event (if available)
% - D: center at max baseline drift (smoothed relB)
% - otherwise: center at GT segment center (or mid-file)

n = numel(relB);
k0 = round(n/2);

% Mode override
if strcmpi(centerMode, 'midfile')
    return;
end

% Parse group tag from title
groupTag = '';
s = char(figTitle);
tok = regexp(s, '([ABCD])类', 'tokens', 'once');
if ~isempty(tok)
    groupTag = tok{1};
else
    tok = regexp(s, '工况([ABCD])', 'tokens', 'once');
    if ~isempty(tok)
        groupTag = tok{1};
    end
end

% Select a representative GT segment (prefer max overlap with pred)
occ_in = [];
occ_out = [];
if ~isempty(gt_idx)
    if isempty(pred_k)
        [~, jj] = max(gt_idx(:,2) - gt_idx(:,1));
    else
        ov = zeros(size(gt_idx,1),1);
        for j = 1:size(gt_idx,1)
            a = gt_idx(j,1); b = gt_idx(j,2);
            for i = 1:size(pred_k,1)
                c = pred_k(i,1); d = pred_k(i,2);
                ov(j) = ov(j) + max(0, min(b,d) - max(a,c));
            end
        end
        [~, jj] = max(ov);
    end
    occ_in  = gt_idx(jj,1);
    occ_out = gt_idx(jj,2);
    k0 = round((occ_in + occ_out)/2);
end

% Heuristic per group
switch upper(groupTag)
    case 'A'
        if ~isempty(occ_in)
            k0 = occ_in;
        end

    case 'B'
        % strongest internal disturbance within occupancy (exclude near boundaries)
        k0_best = k0;
        bestScore = -inf;
        if ~isempty(occ_in) && isfield(out,'events') && ~isempty(out.events) && isfield(out,'pr') && ~isempty(out.pr)
            fs = cfg.fs;
            guard = round(2*fs);
            for m = 1:numel(out.events)
                c = round(0.5*(out.events(m).k_in + out.events(m).k_out));
                if c <= occ_in + guard || c >= occ_out - guard
                    continue;
                end
                k1e = max(1, out.events(m).k_in);
                k2e = min(numel(out.pr), out.events(m).k_out);
                if k2e <= k1e, continue; end
                sc = max(out.pr(k1e:k2e));
                if sc > bestScore
                    bestScore = sc;
                    k0_best = c;
                end
            end
        end
        k0 = k0_best;

    case 'C'
        % first degrade / no-stable event if available
        if isfield(out,'dbg') && ~isempty(out.dbg) && isfield(out.dbg,'used_degrade') && isfield(out.dbg,'stable_found') ...
                && isfield(out,'events') && ~isempty(out.events)
            idx = find(out.dbg.used_degrade(:) | (~out.dbg.stable_found(:)), 1, 'first');
            if ~isempty(idx) && idx <= numel(out.events)
                k0 = round(0.5*(out.events(idx).k_in + out.events(idx).k_out));
            end
        end

    case 'D'
        % pick time where smoothed baseline deviation is largest (to highlight drift)
        win = max(3, round(5*cfg.fs));
        rel_s = movmean(relB, win, 'Endpoints','shrink');
        [~, k0] = max(rel_s);

    otherwise
        % keep default
end

% Safety clamp
k0 = max(1, min(n, k0));
end

function add_interval_bars(ax, t, segs_k, k1, k2, y0, y1, faceColor, alpha)
%ADD_INTERVAL_BARS Draw occupancy intervals as horizontal bars between y0..y1.

for ii = 1:size(segs_k,1)
    a = segs_k(ii,1);
    b = segs_k(ii,2);
    if b < k1 || a > k2
        continue;
    end
    aa = max(a, k1);
    bb = min(b, k2);
    x1 = t(aa);
    x2 = t(bb);
    patch(ax, [x1 x2 x2 x1], [y0 y0 y1 y1], faceColor, ...
        'FaceAlpha', alpha, 'EdgeColor', 'none');
end
end


function Tv = run_eval_only(files, GT, p, cfg, post, IOU_TH)
    Tv = table('Size',[0 11], ...
        'VariableTypes',{'string','string','double','double','double','double','double','double','double','double','double'}, ...
        'VariableNames',{'file','group','TP','FP','FN','P','R','F1','events','pred','gt'});

    for i = 1:numel(files)
        fileName = string(files(i));
        gt_f = GT(GT.file == fileName, :);
        group = string(gt_f.scenario_group(1));
        csvPath = ch4_find_csv(fileName, p.root, p.synth);

        data = ch4_load_csv(csvPath, cfg.fs);
        out  = ch4_run_parking_fsm(data, cfg);

        [pred_k, ~] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);
        gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
        res = ch4_eval(pred_k, gt_idx, IOU_TH);

        rowTable = table(fileName, group, res.TP, res.FP, res.FN, res.P, res.R, res.F1, numel(out.events), size(pred_k,1), size(gt_idx,1), ...
            'VariableNames', Tv.Properties.VariableNames);
        Tv = [Tv; rowTable]; %#ok<AGROW>
    end
end

%% ================= LaTeX row writers =================

function write_tex_dataset_rows(T_ds, outPath)
% T_ds: group, num_files, num_parking_gt, num_vehicle_events, num_pass_est
descA = "正常车流单车停靠，稳定窗可得";
descB = "占用伴随过车扰动（实测为主，含叠加增强）";
descC = "连续车流或拥堵（稳定窗缺失，含拼接/增强）";
descD = "慢漂移背景（实测为主，含漂移注入增强）";
descALL = "全部数据";

% add ALL row
nFiles = sum(T_ds.num_files);
Ngt    = sum(T_ds.num_parking_gt);
Npass  = sum(T_ds.num_pass_est);
T_all = table("ALL", nFiles, Ngt, NaN, Npass, 'VariableNames', T_ds.Properties.VariableNames); %#ok<NASGU>

fid = fopen(outPath, 'w');
assert(fid>0, "Cannot write %s", outPath);

for i = 1:height(T_ds)
    g = string(T_ds.group(i));
    switch g
        case "A", desc = descA;
        case "B", desc = descB;
        case "C", desc = descC;
        case "D", desc = descD;
        otherwise, desc = "";
    end
    fprintf(fid, "%s & %d & %d & %d & %s \\\\\n", g, T_ds.num_files(i), T_ds.num_parking_gt(i), T_ds.num_pass_est(i), desc);
end
fprintf(fid, "ALL & %d & %d & %d & %s \\\\\n", nFiles, Ngt, Npass, descALL);

fclose(fid);
end

function write_tex_bycase_rows(T_group, outPath)
% Expected columns: group, TP, FP, FN, P, R, F1, Rf, Rm
fid = fopen(outPath, 'w');
assert(fid>0, "Cannot write %s", outPath);

for i = 1:height(T_group)
    g = string(T_group.group(i));
    P = T_group.P(i);
    R = T_group.R(i);
    F1 = T_group.F1(i);
    Rf = 100 * T_group.Rf(i);
    Rm = 100 * T_group.Rm(i);
    FP = T_group.FP(i);
    FN = T_group.FN(i);
    fprintf(fid, "%s & %.3f & %.3f & %.3f & %.1f & %.1f & (%d,%d) \\\\\n", g, P, R, F1, Rf, Rm, FP, FN);
end

fclose(fid);
end

function write_tex_timing_rows(T_timing, outPath)
% Columns: group, N_TP, med_abs_dt_in, med_abs_dt_out, med_tau_in, med_tau_out, p95_tau_in, p95_tau_out
fid = fopen(outPath, 'w');
assert(fid>0, "Cannot write %s", outPath);

for i = 1:height(T_timing)
    g = string(T_timing.group(i));
    N = T_timing.N_TP(i);
    a = T_timing.med_abs_dt_in(i);
    b = T_timing.med_abs_dt_out(i);
    c = T_timing.med_tau_in(i);
    d = T_timing.med_tau_out(i);
    p95 = T_timing.p95_tau_in(i);
    fprintf(fid, "%s & %d & %.2f & %.2f & %.2f & %.2f & %.2f \\\\\n", g, N, a, b, c, d, p95);
end

fclose(fid);
end

function write_tex_ablation_rows(T_ab, outPath)
% T_ab: variant, F1_all, F1_A, F1_B, F1_C, F1_D, TP_all
% We also add a brief "phenomenon" column.
fid = fopen(outPath, 'w');
assert(fid>0, "Cannot write %s", outPath);

for i = 1:height(T_ab)
    v = string(T_ab.variant(i));
    switch v
        case "Ours"
            label = "Ours-full";
            phen  = "完整模型";
        case "Abl_noMeanDiff"
            label = "Abl-1（去除$M$）";
            phen  = "伪稳态误触发增多，误检上升";
        case "Abl_noSimilarity"
            label = "Abl-2（去除$\mathrm{dist}$）";
            phen  = "占用态过车后误释放或重复占用";
        case "Abl_noDegrade"
            label = "Abl-3（去除退化分支）";
            phen  = "拥堵下寻稳失败导致漏检与延迟增大";
        case "Abl_noUpdateGate"
            label = "Abl-4（去除更新门控）";
            phen  = "慢漂移背景下参考误更新，产生连锁误判";
        otherwise
            label = v;
            phen  = "";
    end
    fprintf(fid, "%s & %.3f & %.3f & %.3f & %.3f & %.3f & %s \\\\\n", ...
        label, T_ab.F1_all(i), T_ab.F1_A(i), T_ab.F1_B(i), T_ab.F1_C(i), T_ab.F1_D(i), phen);
end

fclose(fid);
end

%% ================= Figure utilities (thesis-ready) =================

function make_thesis_figures(rep, cfg, p, figOpt)
%MAKE_THESIS_FIGURES Generate figures that match Chapter-4 LaTeX placeholders.
% Figures are written into p.images_dir.
%
% This function is intentionally conservative:
%   - Data-driven figures (wave/case/stability/param) are overwritten.
%   - Conceptual schematics (pipeline/FSM) are only created if missing,
%     so manual replacement will not be overwritten by reruns.

    % ---- Waveform examples for four groups ----
    groups = {'A','B','C','D'};

    % 说明：原始三轴波形不适合做“四类横向对比主图”（偏置/尺度差导致差异不显著）。
    % 若需要示例，可打开该开关生成备用图；正文建议仅挑 1 张最能支撑论证的样例即可。
    if isfield(figOpt, 'make_wave_groups') && figOpt.make_wave_groups
        for ii = 1:numel(groups)
            g = groups{ii};
            if ~isempty(rep.(g))
                figPath = fullfile(p.images_dir, ['ch4_wave_' g '.pdf']);
                plot_wave_group(rep.(g).data, rep.(g).out, rep.(g).pred_k, rep.(g).gt_idx, g, figPath, cfg);
            end
        end
    end

    % ---- Stability demo (use group A if available, else first available group) ----
    g0 = '';
    for ii = 1:numel(groups)
        if ~isempty(rep.(groups{ii}))
            g0 = groups{ii};
            break;
        end
    end
    if ~isempty(g0)
        figPath = fullfile(p.images_dir, 'ch4_stability_demo.pdf');
        plot_stability_demo(rep.(g0).data, rep.(g0).out, rep.(g0).gt_idx, g0, figPath, cfg);
    end

    % ---- Pass vs Park example (use group A if possible) ----
    if ~isempty(rep.A)
        figPath = fullfile(p.images_dir, 'ch4_pass_vs_park.pdf');
        plot_pass_vs_park(rep.A.data, rep.A.out, rep.A.gt_idx, figPath, cfg);
    end

    % ---- Conceptual schematics ----
    % Always create *_auto.* for selection (won't conflict with manual diagrams).
    figPipe = fullfile(p.images_dir, 'ch4_pipeline.pdf');
    figPipeAuto = fullfile(p.images_dir, 'ch4_pipeline_auto.pdf');
    if figOpt.always_make_auto_schematics
        plot_pipeline_schematic(figPipeAuto);
        if (exist(figPipe,'file') ~= 2) || figOpt.force_overwrite_schematics
            ch4_copy_figpair(figPipeAuto, figPipe);
        end
    else
        if exist(figPipe,'file') ~= 2
            plot_pipeline_schematic(figPipe);
        end
    end

    figFsm = fullfile(p.images_dir, 'ch4_fsm_degrade.pdf');
    figFsmAuto = fullfile(p.images_dir, 'ch4_fsm_degrade_auto.pdf');
    if figOpt.always_make_auto_schematics
        plot_fsm_schematic(figFsmAuto);
        if (exist(figFsm,'file') ~= 2) || figOpt.force_overwrite_schematics
            ch4_copy_figpair(figFsmAuto, figFsm);
        end
    else
        if exist(figFsm,'file') ~= 2
            plot_fsm_schematic(figFsm);
        end
    end

    % ---- Manual figures (optional placeholders) ----
    if isfield(figOpt,'make_placeholders') && figOpt.make_placeholders
        figScene = fullfile(p.images_dir, 'ch4_scene_photo.pdf');
        if exist(figScene,'file') ~= 2
            ch4_make_placeholder(figScene, '现场照片占位', {'请替换为：道路监测场景照片', '（应急车道/路肩 + 邻道车流）'});
        end
        figSetup = fullfile(p.images_dir, 'ch4_setup_schematic.pdf');
        if exist(figSetup,'file') ~= 2
            ch4_make_placeholder(figSetup, '布设示意占位', {'请替换为：传感器布设与坐标定义示意图', '（含 x/y/z 方向与车道关系）'});
        end
    end
end

function plot_wave_group(data, out, pred_k, gt_idx, groupName, figPath, cfg, varargin)
%PLOT_WAVE_GROUP  Plot representative waveform for a scenario group
%
% Changes vs v5:
%   1) Automatically select a more representative GT interval (not always gt_idx(1,:)).
%   2) Use group-specific default padding (B/C larger, D much larger).
%   3) Add an extra panel for disturbance score pr(k) to make B/C differences visible.
%
% Optional:
%   'pad' : padding seconds (override defaults)

% --- parse optional padding ---
padSec = [];
if ~isempty(varargin)
    if isnumeric(varargin{1})
        padSec = varargin{1};
        varargin = varargin(2:end);
    end
end

p = inputParser;
addParameter(p, 'pad', [], @(x) isempty(x) || (isscalar(x) && x >= 0));
parse(p, varargin{:});

if isempty(padSec)
    padSec = p.Results.pad;
end

% --- default padding by group ---
if isempty(padSec)
    switch upper(string(groupName))
        case "A"
            padSec = 8;
        case "B"
            padSec = 20;
        case "C"
            padSec = 20;
        case "D"
            padSec = 90;  % drift needs longer horizon
        otherwise
            padSec = 8;
    end
end

% --- select GT interval (row) for this figure ---
gtSel = [];
gtSelIdx = 1;
gtStat = struct('nEv', NaN, 'stableRatio', NaN, 'prMean', NaN, 'driftScore', NaN);
if ~isempty(gt_idx)
    [gtSel, gtSelIdx, gtStat] = ch4_select_gt_for_wave(data, out, gt_idx, groupName, cfg);
end

% --- determine plotting window ---
n = numel(data.k);
if ~isempty(gtSel)
    k_center_1 = gtSel(1);
    k_center_2 = gtSel(2);
elseif ~isempty(pred_k)
    % fallback: first predicted interval
    k_center_1 = pred_k(1,1);
    k_center_2 = pred_k(1,2);
else
    k_center_1 = 1;
    k_center_2 = n;
end

pad = max(0, round(padSec * cfg.fs));
k1 = max(1, k_center_1 - pad);
k2 = min(n, k_center_2 + pad);

t = data.t(k1:k2);
B = data.B(k1:k2, :);

% stability flag and disturbance score
stable = out.st.stableState(k1:k2);
pr = out.pr(k1:k2);

% --- prepare event markers in this window ---
ev_out = [];
ev_in = [];
if ~isempty(out.events)
    ev_in = [out.events.k_in]';
    ev_out = [out.events.k_out]';
    keep = (ev_out >= k1) & (ev_in <= k2);
    ev_in = ev_in(keep);
    ev_out = ev_out(keep);
end

% --- figure ---
fig = ch4_newfig(16, 14);
tl = tiledlayout(5, 1, 'TileSpacing','compact','Padding','compact');

% --- 1) Bx ---
ax1 = nexttile;
plot(t, B(:,1), 'LineWidth', 1);
ylabel('$B_x$', 'Interpreter','latex');
hold on; grid on;

% --- 2) By ---
ax2 = nexttile;
plot(t, B(:,2), 'LineWidth', 1);
ylabel('$B_y$', 'Interpreter','latex');
hold on; grid on;

% --- 3) Bz ---
ax3 = nexttile;
plot(t, B(:,3), 'LineWidth', 1);
ylabel('$B_z$', 'Interpreter','latex');
hold on; grid on;

% --- 4) pr(k) (disturbance score) ---
ax4 = nexttile;
plot(t, pr, 'LineWidth', 1);
ylim([0, 1]);
ylabel('扰动得分');
hold on; grid on;

% thresholds used by event detector (optional reference)
try
    yline(cfg.ev.theta_arrive, '--', 'arrive', 'LabelHorizontalAlignment','left', 'LabelVerticalAlignment','bottom');
    yline(cfg.ev.theta_leave,  '--', 'leave',  'LabelHorizontalAlignment','left', 'LabelVerticalAlignment','top');
catch
end

% --- 5) stable flag ---
ax5 = nexttile;
plot(t, stable, 'LineWidth', 1);
ylim([-0.05, 1.05]);
ylabel('稳定标志');
xlabel('时间/s');
hold on; grid on;

% --- patches (predicted & selected GT) ---
axs = [ax1 ax2 ax3 ax4 ax5];

for i = 1:numel(axs)
    ax = axs(i);

    % predicted occupied intervals
    if ~isempty(pred_k)
        for j = 1:size(pred_k,1)
            kk = pred_k(j,:);
            if kk(2) < k1 || kk(1) > k2
                continue;
            end
            kk2 = [max(k1,kk(1)) min(k2,kk(2))];
            tt2 = data.t(kk2);
            ch4_patch_interval_time(ax, tt2, [0.0 0.6 0.0], 0.08);
        end
    end

    % selected GT interval (for this figure)
    if ~isempty(gtSel)
        kk = gtSel;
        kk2 = [max(k1,kk(1)) min(k2,kk(2))];
        tt2 = data.t(kk2);
        ch4_patch_interval_time(ax, tt2, [0.2 0.2 1.0], 0.10);
    end
end

% --- event markers: draw on pr/stable panels (avoid clutter on B axes) ---
if ~isempty(ev_out)
    for i = 1:numel(ev_out)
        tt_in = data.t(ev_in(i));
        tt_out = data.t(ev_out(i));
        xline(ax4, tt_in, ':', 'Color', [0.85 0.33 0.10], 'LineWidth', 0.8);
        xline(ax4, tt_out, ':', 'Color', [0.85 0.33 0.10], 'LineWidth', 0.8);
        xline(ax5, tt_out, ':', 'Color', [0.85 0.33 0.10], 'LineWidth', 0.8);
    end
end

% --- title with stats (helps distinguish groups visually) ---
if ~isempty(gtSel)
    ttl = sprintf('%s类波形示例（GT#%d，N_{ev}=%d，stable=%.2f，pr=%.3f）', ...
        upper(char(groupName)), gtSelIdx, gtStat.nEv, gtStat.stableRatio, gtStat.prMean);
    if upper(string(groupName)) == "D"
        ttl = sprintf('%s，drift=%.2f', ttl, gtStat.driftScore);
    end
else
    ttl = sprintf('%s类波形示例', upper(char(groupName)));
end
title(tl, ttl, 'FontWeight','normal');

ch4_apply_style(fig);

ch4_export_fig(fig, figPath);
close(fig);
end

function [gtSel, idxSel, statSel] = ch4_select_gt_for_wave(data, out, gt_idx, groupName, cfg)
%CH4_SELECT_GT_FOR_WAVE  Pick a more representative GT interval for plotting.
%
% gt_idx : [N x 2] (sample indices, inclusive)
% Strategy:
%   A: prefer stable, few disturbances
%   B: prefer more disturbances during occupied interval
%   C: prefer unstable / high disturbance density
%   D: prefer larger baseline drift around the interval (long window)

nGT = size(gt_idx, 1);
n = numel(data.k);

% event list
ev_in = [];
ev_out = [];
if ~isempty(out.events)
    ev_in = [out.events.k_in]';
    ev_out = [out.events.k_out]';
end

nEv = zeros(nGT,1);
stableRatio = zeros(nGT,1);
prMean = zeros(nGT,1);
driftScore = zeros(nGT,1);

% drift estimation window (seconds)
winSec = 30;
win = max(1, round(winSec * cfg.fs));

for i = 1:nGT
    g1 = max(1, gt_idx(i,1));
    g2 = min(n, gt_idx(i,2));
    if g2 < g1
        continue;
    end

    % count events overlapping this GT interval
    if ~isempty(ev_in)
        overlap = ~(ev_out < g1 | ev_in > g2);
        nEv(i) = sum(overlap);
    else
        nEv(i) = 0;
    end

    % stable ratio inside GT
    stableRatio(i) = mean(out.st.stableState(g1:g2));

    % average disturbance score inside GT
    prMean(i) = mean(out.pr(g1:g2));

    % drift score (difference of mean baseline before/after GT)
    pre1 = max(1, g1 - win);
    pre2 = max(1, g1 - 1);
    post1 = min(n, g2 + 1);
    post2 = min(n, g2 + win);
    if pre2 >= pre1 && post2 >= post1
        preMu = mean(data.B(pre1:pre2, :), 1);
        postMu = mean(data.B(post1:post2, :), 1);
        driftScore(i) = norm(postMu - preMu);
    else
        driftScore(i) = 0;
    end
end

% scoring
g = upper(string(groupName));
switch g
    case "A"
        % stable and clean
        score = 2.0*stableRatio - 0.6*nEv - 0.5*prMean;
    case "B"
        % occupied with pass disturbances
        score = 1.2*nEv + 1.0*prMean + 0.3*stableRatio;
    case "C"
        % continuous traffic: unstable + many disturbances
        score = 1.5*nEv + 1.2*prMean + 2.0*(1.0 - stableRatio);
    case "D"
        % drift background: choose interval with larger baseline drift
        score = 2.0*driftScore + 0.2*nEv;
    otherwise
        score = nEv + prMean;
end

[~, idxSel] = max(score);
gtSel = gt_idx(idxSel, :);

statSel = struct();
statSel.nEv = nEv(idxSel);
statSel.stableRatio = stableRatio(idxSel);
statSel.prMean = prMean(idxSel);
statSel.driftScore = driftScore(idxSel);
end


function ch4_patch_interval_time(ax, t12, rgb, alphaVal)
%CH4_PATCH_INTERVAL_TIME  Draw a vertical patch between t12(1)~t12(2) on axes ax.
% Note: ylim(ax) is used as patch vertical span.

if isempty(t12) || numel(t12) < 2
    return;
end

y = ylim(ax);
h = patch(ax, [t12(1) t12(2) t12(2) t12(1)], [y(1) y(1) y(2) y(2)], rgb, ...
    'FaceAlpha', alphaVal, 'EdgeColor','none');
try
    uistack(h, 'bottom');
catch
end
end


function plot_stability_demo(data, out, gt_idx, groupName, figPath, cfg)
%PLOT_STABILITY_DEMO R/M curves and thresholds + stable flag (for the thesis figure).

    t = data.t(:);
    n = numel(t);
    fs = cfg.fs;

    pad = round(8*fs);
    if ~isempty(gt_idx)
        k1 = max(1, gt_idx(1,1) - pad);
        k2 = min(n, gt_idx(1,2) + pad);
    else
        k1 = 1; k2 = min(n, 25*fs);
    end
    idx = k1:k2;

    R = out.st.R(:);
    M = out.st.M(:);
    st = out.st.stableState(:);

    fig = ch4_newfig(16, 10);
    tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

    ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
    plot(ax1, t(idx), R(idx), 'LineWidth', 1.0);
    yline_if(ax1, cfg.st.R_th, '--', sprintf('R_{th}=%.1f', cfg.st.R_th));
    add_mask_shading(ax1, t, st, k1, k2, [0.85 0.85 0.85], 0.15);
    ylabel(ax1, '窗内波动 R(k)');
    title(ax1, sprintf('稳定判据示意（%s类）', groupName), 'FontWeight','normal');

    ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
    plot(ax2, t(idx), M(idx), 'LineWidth', 1.0);
    yline_if(ax2, cfg.st.M_th, '--', sprintf('M_{th}=%.1f', cfg.st.M_th));
    add_mask_shading(ax2, t, st, k1, k2, [0.85 0.85 0.85], 0.15);
    xlabel(ax2, '时间/s'); ylabel(ax2, '窗间水平差 M(k)');

    ch4_apply_style(fig);
    ch4_export_fig(fig, figPath);
    close(fig);
end

function plot_pass_vs_park(data, out, gt_idx, figPath, cfg)
%PLOT_PASS_VS_PARK Side-by-side comparison: a pass event vs a parking-arrival event.

    if isempty(out.events)
        return;
    end

    fs = cfg.fs;
    t = data.t(:);
    B = data.B;
    F = sqrt(sum(B.^2,2));
    dB = [0; sqrt(sum(diff(B,1,1).^2,2))];

    % match event indices to GT arrival/leave (by k_out proximity)
    [arrIdx, leaveIdx] = match_events_to_gt(out.events, gt_idx, round(2.0*fs));
    if isempty(arrIdx)
        return;
    end
    park_m = arrIdx(1);

    allIdx = 1:numel(out.events);
    passCand = setdiff(allIdx, unique([arrIdx(:); leaveIdx(:)]));
    if isempty(passCand)
        pass_m = park_m; % fallback
    else
        pass_m = passCand(1);
    end

    [k1p, k2p] = event_window(out.events(pass_m), numel(t), round(3*fs));
    [k1k, k2k] = event_window(out.events(park_m), numel(t), round(3*fs));

    fig = ch4_newfig(16, 10);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing','compact', 'Padding','compact');

    % ---- Pass: magnitude ----
    ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
    plot(ax1, t(k1p:k2p), F(k1p:k2p), 'LineWidth', 1.0);
    add_interval_patches(ax1, t, [out.events(pass_m).k_in, out.events(pass_m).k_out], k1p, k2p, [0.85 0.85 0.85], 0.35);
    title(ax1, '通过事件：||B||_2', 'FontWeight','normal');
    ylabel(ax1, '磁场幅值 ||B||_2');

    % ---- Park: magnitude ----
    ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
    plot(ax2, t(k1k:k2k), F(k1k:k2k), 'LineWidth', 1.0);
    add_interval_patches(ax2, t, [out.events(park_m).k_in, out.events(park_m).k_out], k1k, k2k, [0.75 0.85 1.00], 0.30);
    title(ax2, '停车到达事件：||B||_2', 'FontWeight','normal');

    % ---- Pass: diff magnitude ----
    ax3 = nexttile(tl, 3); hold(ax3,'on'); grid(ax3,'on');
    plot(ax3, t(k1p:k2p), dB(k1p:k2p), 'LineWidth', 1.0);
    add_interval_patches(ax3, t, [out.events(pass_m).k_in, out.events(pass_m).k_out], k1p, k2p, [0.85 0.85 0.85], 0.35);
    xlabel(ax3, '时间/s'); ylabel(ax3, '差分幅值 ||\Delta B||_2');

    % ---- Park: diff magnitude ----
    ax4 = nexttile(tl, 4); hold(ax4,'on'); grid(ax4,'on');
    plot(ax4, t(k1k:k2k), dB(k1k:k2k), 'LineWidth', 1.0);
    add_interval_patches(ax4, t, [out.events(park_m).k_in, out.events(park_m).k_out], k1k, k2k, [0.75 0.85 1.00], 0.30);
    xlabel(ax4, '时间/s');

    title(tl, '通过 vs 停靠对比', 'FontWeight','normal');

    ch4_apply_style(fig);
    ch4_export_fig(fig, figPath);
    close(fig);
end


function plot_pipeline_schematic(figPath)
%PLOT_PIPELINE_SCHEMATIC  Chapter-4 method pipeline schematic (for thesis figures).
%
%  说明：该图尽量避免把文本/箭头画到画布边缘之外，否则 exportgraphics 的裁剪会截断文字。
%  如需进一步美化，建议最终版本改用 TikZ/draw.io 手工重画。

    fig = ch4_newfig(18, 4.8);
    ax = axes(fig); %#ok<NASGU>
    axis([0 1 0 1]); axis off; hold on;

    % Layout parameters (normalized figure coordinates)
    margin = 0.05;
    gap = 0.02;
    n = 5;
    w = (1 - 2*margin - (n-1)*gap) / n;
    y = 0.22;
    h = 0.56;

    xs = margin + (0:n-1) * (w + gap);

    % Box + text style
    boxStyle = {'LineWidth', 1.0, 'EdgeColor', [0.15 0.15 0.15], 'FaceColor', [1 1 1]};
    txtStyle = {'LineStyle','none', 'HorizontalAlignment','center', 'VerticalAlignment','middle', ...
        'FontSize', 11, 'FontName', 'Microsoft YaHei', 'Interpreter','tex'};

    labels = { ...
        {'输入：事件片段', '(diff\_on / diff\_off)'}; ...
        {'预处理与稳定窗判定', 'R(k), M(k), f\_st(k)'}; ...
        {'稳定点提取 / 动态参考', 'S\_pre, S\_post'}; ...
        {'漂移 / 相似性判定', 'ΔB, dist'}; ...
        {'输出：停车/占用语义', 'park\_flag, occ\_flag'} ...
    };

    boxes = zeros(n,4);
    for i = 1:n
        boxes(i,:) = [xs(i) y w h];
        annotation(fig,'rectangle', boxes(i,:), boxStyle{:});
        annotation(fig,'textbox', boxes(i,:), 'String', labels{i}, txtStyle{:});
    end

    % Arrows between boxes (centerline)
    for i = 1:n-1
        x1 = boxes(i,1) + boxes(i,3);
        x2 = boxes(i+1,1);
        yc = y + h/2;
        annotation(fig,'arrow', [x1 x2], [yc yc], 'LineWidth', 1.0, ...
            'HeadLength', 6, 'HeadWidth', 6);
    end

    % Small notes (keep inside canvas)
    annotation(fig,'textbox', [margin 0.06 1-2*margin 0.12], 'LineStyle','none', ...
        'HorizontalAlignment','center', 'VerticalAlignment','middle', 'FontSize', 9, ...
        'FontName', 'Microsoft YaHei', 'Interpreter','tex', ...
        'String', '注：diff\_off 后在 T\_seek 内寻稳；稳定窗不可得时进入固定窗+一致性计数退化分支。');

    ch4_apply_style(fig);
    ch4_save_pdf_png(fig, figPath);
    close(fig);
end


function plot_fsm_schematic(figPath)
%PLOT_FSM_SCHEMATIC  Clean FSM + degrade schematic for Chapter-4.
%
%  说明：优先保证图面“可读”和“不裁剪”。若需要更高的出版级质量，建议用 TikZ 重画。

    fig = ch4_newfig(16, 7.6);
    ax = axes(fig); %#ok<NASGU>
    axis([0 1 0 1]); axis off; hold on;

    boxStyle = {'LineWidth', 1.0, 'EdgeColor', [0.15 0.15 0.15], 'FaceColor', [1 1 1]};
    txtStyle = {'LineStyle','none', 'HorizontalAlignment','center', 'VerticalAlignment','middle', ...
        'FontSize', 10, 'FontName', 'Microsoft YaHei', 'Interpreter','tex'};

    % 2×2 layout avoids long diagonal arrows and reduces clutter
    w = 0.34; h = 0.20;
    P.FREE  = [0.10 0.70 w h];
    P.CPARK = [0.56 0.70 w h];
    P.OCC   = [0.56 0.30 w h];
    P.CREL  = [0.10 0.30 w h];

    % Draw state boxes
    annotation(fig,'rectangle', P.FREE,  boxStyle{:});
    annotation(fig,'textbox',   P.FREE,  'String', {'FREE 空闲','更新环境参考 S\_pre'}, txtStyle{:});

    annotation(fig,'rectangle', P.CPARK, boxStyle{:});
    annotation(fig,'textbox',   P.CPARK, 'String', {'CAND\_PARK 候选停车','寻稳/退化确认'}, txtStyle{:});

    annotation(fig,'rectangle', P.OCC,   boxStyle{:});
    annotation(fig,'textbox',   P.OCC,   'String', {'OCCUPIED 占用','冻结占用参考 S\_post'}, txtStyle{:});

    annotation(fig,'rectangle', P.CREL,  boxStyle{:});
    annotation(fig,'textbox',   P.CREL,  'String', {'CAND\_RELEASE 候选释放','回归/退化确认'}, txtStyle{:});

    % Main cycle arrows: FREE -> CPARK -> OCC -> CREL -> FREE
    yTop = P.FREE(2) + P.FREE(4)/2;
    annotation(fig,'arrow', [P.FREE(1)+P.FREE(3) P.CPARK(1)], [yTop yTop], ...
        'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
    annotation(fig,'textbox', [0.30 0.88 0.40 0.08], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
        'HorizontalAlignment','center', 'FontSize', 9, 'Interpreter','tex', ...
        'String', 'diff\_off 触发 → 进入候选停车');

    xR = P.CPARK(1) + P.CPARK(3)/2;
    annotation(fig,'arrow', [xR xR], [P.CPARK(2) P.OCC(2)+P.OCC(4)], ...
        'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
    annotation(fig,'textbox', [0.74 0.56 0.24 0.12], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
        'HorizontalAlignment','left', 'FontSize', 9, 'Interpreter','tex', ...
        'String', {'确认停车：','ΔB > D\_th','或退化计数'} );

    yBot = P.OCC(2) + P.OCC(4)/2;
    annotation(fig,'arrow', [P.OCC(1) P.CREL(1)+P.CREL(3)], [yBot yBot], ...
        'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
    annotation(fig,'textbox', [0.18 0.22 0.46 0.10], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
        'HorizontalAlignment','left', 'FontSize', 9, 'Interpreter','tex', ...
        'String', {'占用内干扰：dist < dist\_th ⇒ 仍占用'} );

    xL = P.CREL(1) + P.CREL(3)/2;
    annotation(fig,'arrow', [xL xL], [P.CREL(2)+P.CREL(4) P.FREE(2)], ...
        'LineWidth', 1.0, 'HeadLength', 6, 'HeadWidth', 6);
    annotation(fig,'textbox', [0.00 0.48 0.28 0.14], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
        'HorizontalAlignment','left', 'FontSize', 9, 'Interpreter','tex', ...
        'String', {'确认释放：','||S\_new-S\_pre|| < D\_free','或退化计数'} );

    % Fail-back arrow: CPARK -> FREE (timeout / drift too small)
    yFB = P.FREE(2) + P.FREE(4)*0.85;
    annotation(fig,'arrow', [P.CPARK(1) P.FREE(1)+P.FREE(3)], [yFB yFB], ...
        'LineWidth', 1.0, 'LineStyle','--', 'HeadLength', 6, 'HeadWidth', 6);
    annotation(fig,'textbox', [0.30 0.80 0.40 0.08], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
        'HorizontalAlignment','center', 'FontSize', 9, 'Interpreter','tex', ...
        'String', '寻稳超时 / 漂移不足 → 回到 FREE');

    % Degrade note (keep short)
    annotation(fig,'textbox', [0.18 0.06 0.64 0.10], 'LineStyle','none', 'FontName','Microsoft YaHei', ...
        'HorizontalAlignment','center', 'FontSize', 9, 'Interpreter','tex', ...
        'String', '退化分支：稳定窗不可得时，使用固定窗均值 + 一致性计数器完成确认。');

    ch4_apply_style(fig);
    ch4_save_pdf_png(fig, figPath);
    close(fig);
end

function ch4_apply_style(fig)
%CH4_APPLY_STYLE Apply a consistent academic style to a MATLAB figure.
    set(fig, 'Color','w');

    axs = findall(fig, 'Type','axes');
    for i = 1:numel(axs)
        ax = axs(i);
        ax.Box = 'on';
        ax.LineWidth = 0.8;
        ax.FontName = 'Microsoft YaHei';
        ax.FontSize = 10;
        ax.GridAlpha = 0.15;
        ax.MinorGridAlpha = 0.08;
    end

    lgs = findall(fig, 'Type','legend');
    for i = 1:numel(lgs)
        lg = lgs(i);
        lg.Box = 'off';
        lg.FontName = 'Microsoft YaHei';
        lg.FontSize = 9;
    end
end

function ch4_save_pdf_png(fig, figPath)
%CH4_SAVE_PDF_PNG Backward-compatible wrapper (older helper name).
% Some schematic plotters call this function; we route to ch4_export_fig.
    ch4_export_fig(fig, figPath);
end

function ch4_export_fig(h, outPath)
%CH4_EXPORT_FIG Export figure: if you pass a .pdf path, also export a same-name .png.
%  - h can be an axes or figure handle; this function always exports the whole figure
%    to preserve titles/labels/colorbars (avoid over-tight cropping).
%  - PDF: vector (preferred for LaTeX)
%  - PNG: 300 dpi (convenient for Word / quick insertion)

if isstring(outPath)
    outPath = char(outPath);
end

[p, name, ext] = fileparts(outPath);
if isempty(ext)
    ext = '.pdf';
    outPath = fullfile(p, [name ext]);
end

if ~isempty(p) && ~exist(p, 'dir')
    mkdir(p);
end

pdfPath = '';
pngPath = '';

if strcmpi(ext, '.pdf')
    pdfPath = outPath;
    pngPath = fullfile(p, [name '.png']);
elseif strcmpi(ext, '.png')
    pngPath = outPath;
    pdfPath = fullfile(p, [name '.pdf']); % symmetric: also save pdf
else
    % unknown extension -> treat as png
    pngPath = outPath;
end

% Always export the whole figure (avoid axis-only tight crop)
if isgraphics(h, 'figure')
    fig = h;
else
    fig = ancestor(h, 'figure');
    if isempty(fig)
        fig = gcf;
    end
end

try
    set(fig, 'InvertHardcopy', 'off');
catch
end

% --- Ensure paper size matches figure size (prevents PDF clipping when using print) ---
try
    oldUnits = get(fig, 'Units');
    set(fig, 'Units', 'inches');
    pos = get(fig, 'Position');  % [left bottom width height] in inches
    set(fig, 'PaperUnits', 'inches');
    set(fig, 'PaperSize', [pos(3) pos(4)]);
    set(fig, 'PaperPosition', [0 0 pos(3) pos(4)]);
    set(fig, 'PaperPositionMode', 'manual');
    set(fig, 'Units', oldUnits);
catch
end

try
    set(fig, 'InvertHardcopy', 'off');
catch
end

hasExport = (exist('exportgraphics', 'file') == 2);

% 1) PDF (vector)
if ~isempty(pdfPath)
    if hasExport
        try
            exportgraphics(fig, pdfPath, 'ContentType', 'vector', 'BackgroundColor', 'white');
        catch
            try
                print(fig, pdfPath, '-dpdf', '-painters');
            catch
                print(fig, pdfPath, '-dpdf');
            end
        end
    else
        try
                print(fig, pdfPath, '-dpdf', '-painters');
            catch
                print(fig, pdfPath, '-dpdf');
            end
    end
end

% 2) PNG (raster, keep full figure canvas; do not use getframe/axis crop)
if ~isempty(pngPath)
    if hasExport
        try
            exportgraphics(fig, pngPath, 'Resolution', 300, 'BackgroundColor', 'white');
            return;
        catch
            % fall back to print
        end
    end

    oldRenderer = '';
    try
        oldRenderer = get(fig, 'Renderer');
        set(fig, 'Renderer', 'opengl');
    catch
    end
    try
        print(fig, pngPath, '-dpng', '-r300');
    catch
    end
    try
        if ~isempty(oldRenderer)
            set(fig, 'Renderer', oldRenderer);
        end
    catch
    end
end
end


function edges = ch4_hist_edges(v, nBins)
%CH4_HIST_EDGES Robust histogram edges for degenerate distributions.
    v = v(:);
    v = v(isfinite(v));
    if isempty(v)
        edges = linspace(0, 1, nBins+1);
        return;
    end
    vmin = min(v);
    vmax = max(v);
    if vmax <= vmin
        vmin = vmin - 0.5;
        vmax = vmax + 0.5;
    end
    edges = linspace(vmin, vmax, nBins+1);
end

function yline_if(ax, y, style, labelStr)
%YLINE_IF Use yline if available, otherwise plot a horizontal line.
    if exist('yline','file') == 2
        h = yline(ax, y, style, labelStr);
        h.LineWidth = 1.0;
    else
        xl = xlim(ax);
        plot(ax, xl, [y y], style, 'LineWidth', 1.0);
        xlim(ax, xl);
    end
end

function add_interval_patches(ax, t, segs_k, k1, k2, faceColor, alpha)
%ADD_INTERVAL_PATCHES Draw shaded intervals on an axis.
% segs_k: Nx2 [k_in, k_out] (sample indices)

    if isempty(segs_k)
        return;
    end
    if size(segs_k,2) ~= 2
        return;
    end

    yl = ylim(ax);

    for j = 1:size(segs_k,1)
        a = max(k1, segs_k(j,1));
        b = min(k2, segs_k(j,2));
        if ~isfinite(a) || ~isfinite(b) || b <= a
            continue;
        end
        a = max(1, min(a, numel(t)));
        b = max(1, min(b, numel(t)));
        x1 = t(a); x2 = t(b);
        p = patch(ax, [x1 x2 x2 x1], [yl(1) yl(1) yl(2) yl(2)], faceColor, ...
            'FaceAlpha', alpha, 'EdgeColor', 'none');
        uistack(p, 'bottom');
    end

    ylim(ax, yl);
end

function add_mask_shading(ax, t, mask, k1, k2, faceColor, alpha)
%ADD_MASK_SHADING Shade regions where mask==true within [k1,k2].

    if isempty(mask)
        return;
    end
    mask = mask(:);
    n = numel(mask);
    k1 = max(1, min(k1, n));
    k2 = max(1, min(k2, n));

    m = mask(k1:k2);
    dm = diff([false; m; false]);
    s = find(dm == 1) + k1 - 1;
    e = find(dm == -1) - 1 + k1 - 1;

    segs = [s(:), e(:)];
    add_interval_patches(ax, t, segs, k1, k2, faceColor, alpha);
end

function [k1, k2] = event_window(ev, n, pad)
%EVENT_WINDOW Safe [k1,k2] around an event
    k1 = max(1, ev.k_in - pad);
    k2 = min(n, ev.k_out + pad);
end


function plot_sensitivity_fig(A_drift_mag, A_is_park, B_dist, B_is_leave, cfg, p)
% 参数敏感性（可视化）：
% 左：A类 D_th（停车漂移阈值）对事件级TPR/FPR的影响
% 右：B类 dist_th（相似性门控阈值）对“占用保持扰动事件”的接受率/更新触发率

    fig = ch4_newfig(12, 5.6);
    tlo = tiledlayout(fig, 1, 2, 'Padding','compact', 'TileSpacing','compact');

    %% (Left) A类：D_th 事件级 TPR/FPR
    ax1 = nexttile(tlo, 1);
    hold(ax1, 'on'); grid(ax1, 'on'); box(ax1, 'on');
    A_drift_mag = A_drift_mag(:);
    A_is_park   = logical(A_is_park(:));
    maskA = ~isnan(A_drift_mag);
    A_drift_mag = A_drift_mag(maskA);
    A_is_park   = A_is_park(maskA);

    if ~isempty(A_drift_mag)
        Dgrid = linspace(min(A_drift_mag), max(A_drift_mag), 40);
        [tprA, fprA] = binary_sweep_rates(A_drift_mag, A_is_park, Dgrid);
        plot(ax1, Dgrid, tprA, 'LineWidth', 2.0);
        plot(ax1, Dgrid, fprA, '--', 'LineWidth', 2.0);
        xline(ax1, cfg.D_th, ':', sprintf('D_{th}=%.1f', cfg.D_th), 'LineWidth', 2.0);
        legend(ax1, {'召回率(TPR)','误报率(FPR)'}, 'Location','best');
    else
        text(ax1, 0.5, 0.5, 'A类样本不足', 'HorizontalAlignment','center');
    end
    xlabel(ax1, '停车漂移阈值 $D_{\mathrm{th}}$', 'Interpreter','latex');
    ylabel(ax1, '比例');
    title(ax1, 'A类：$D_{\mathrm{th}}$敏感性（事件级）', 'Interpreter','latex');

    %% (Right) B类：dist_th 占用稳态接受率/更新触发率
    ax2 = nexttile(tlo, 2);
    hold(ax2, 'on'); grid(ax2, 'on'); box(ax2, 'on');

    B_dist = B_dist(:);
    B_is_leave = logical(B_is_leave(:));
    keep = ~B_is_leave & ~isnan(B_dist);
    d_keep = B_dist(keep);

    if ~isempty(d_keep)
        dgrid = linspace(0, max(d_keep)*1.05, 40);
        acc = arrayfun(@(d) mean(d_keep < d), dgrid);       % 接受率：dist<d
        upd = 1 - acc;                                      % 触发更新率：dist>=d
        plot(ax2, dgrid, acc, 'LineWidth', 2.0);
        plot(ax2, dgrid, upd, '--', 'LineWidth', 2.0);
        xline(ax2, cfg.dist_th, ':', sprintf('dist_{th}=%.1f', cfg.dist_th), 'LineWidth', 2.0);
        legend(ax2, {'接受率 $Acc(d)$','更新触发率 $1-Acc(d)$'}, 'Location','best', 'Interpreter','latex');
    else
        text(ax2, 0.5, 0.5, 'B类保持样本不足', 'HorizontalAlignment','center');
    end

    xlabel(ax2, '相似性阈值 $\mathrm{dist}_{\mathrm{th}}$', 'Interpreter','latex');
    ylabel(ax2, '比例');
    title(ax2, 'B类：$\mathrm{dist}_{\mathrm{th}}$敏感性（占用保持事件）', 'Interpreter','latex');

    % Export (PDF+PNG) into thesis images_dir
    figPath = fullfile(p.images_dir, 'ch4_sensitivity.pdf');
    ch4_apply_style(fig);
    ch4_export_fig(fig, figPath);
    close(fig);
end

function [tpr, fpr] = binary_sweep_rates(x, y, th, greaterIsPositive)
%BINARY_SWEEP_RATES Compute TPR/FPR for thresholds.
%  - x: score
%  - y: logical ground-truth positive
%  - th: thresholds
%  - greaterIsPositive: if true, pred = x>th else pred=x<th

    if nargin < 4 || isempty(greaterIsPositive)
        greaterIsPositive = true;
    end

    x = x(:); y = logical(y(:));
    tpr = zeros(numel(th),1);
    fpr = zeros(numel(th),1);
    for i = 1:numel(th)
        if greaterIsPositive
            yp = x > th(i);
        else
            yp = x < th(i);
        end
        TP = sum( yp &  y);
        FN = sum(~yp &  y);
        FP = sum( yp & ~y);
        TN = sum(~yp & ~y);
        tpr(i) = TP / max(TP+FN, 1);
        fpr(i) = FP / max(FP+TN, 1);
    end
end

function ch4_report_fig_status(p, expectedBases, figOpt)
%CH4_REPORT_FIG_STATUS Print where images are written and which ones exist.

    fprintf('\n=== 输出目录 ===\n');
    fprintf('thesis_dir : %s\n', string(p.thesis));
    fprintf('images_dir : %s\n', string(p.images_dir));
    fprintf('tables_dir : %s\n', string(p.tables_dir));
    fprintf('csv(out)   : %s\n', string(p.out));

    d = dir(fullfile(p.images_dir, 'ch4_*.pdf'));
    fprintf('\n=== images_dir 下已有 ch4_*.pdf：%d 个 ===\n', numel(d));
    if figOpt.verbose
        for i = 1:numel(d)
            fprintf('  - %s\n', d(i).name);
        end
    end

    missing = {};
    for i = 1:numel(expectedBases)
        base = expectedBases{i};
        pdfPath = fullfile(p.images_dir, [base '.pdf']);
        if exist(pdfPath,'file') ~= 2
            missing{end+1} = base; %#ok<AGROW>
            if isfield(figOpt,'make_placeholders') && figOpt.make_placeholders
                ch4_make_placeholder(pdfPath, '缺少图片占位', {['文件名：' base '.pdf'], '请根据章节内容替换为真实图片。'});
            end
        end
    end

    if ~isempty(missing)
        fprintf('\n[Warn] 以下预期图片缺失（已按需生成占位图）：\n');
        for i = 1:numel(missing)
            fprintf('  - %s\n', missing{i});
        end
    else
        fprintf('\n[OK] 预期图片均存在。\n');
    end
end

function ch4_make_placeholder(pdfPath, titleText, lines)
%CH4_MAKE_PLACEHOLDER Create a simple placeholder figure (PDF+PNG).

    fig = ch4_newfig(16, 6);
    axis off;

    if isstring(lines); lines = cellstr(lines); end
    if ~iscell(lines); lines = {char(lines)}; end

    msg = [{titleText}; lines(:)];

    annotation(fig, 'rectangle', [0.05 0.15 0.90 0.75], 'LineWidth', 1.2);
    annotation(fig, 'textbox', [0.06 0.16 0.88 0.73], 'String', msg, ...
        'LineStyle','none', 'FontName','Microsoft YaHei', 'FontSize', 12, ...
        'HorizontalAlignment','left', 'VerticalAlignment','top');

    ch4_apply_style(fig);
    ch4_export_fig(fig, pdfPath);
    close(fig);
end

function ch4_copy_figpair(srcPdf, dstPdf)
%CH4_COPY_FIGPAIR Copy PDF and its paired PNG (if exists).
    try
        copyfile(srcPdf, dstPdf, 'f');
    catch
    end
    srcPng = regexprep(srcPdf, '\.pdf$', '.png', 'ignorecase');
    dstPng = regexprep(dstPdf, '\.pdf$', '.png', 'ignorecase');
    if exist(srcPng,'file') == 2
        try
            copyfile(srcPng, dstPng, 'f');
        catch
        end
    end
end


function ch4_make_aliases_without_opt(p, figOpt)
%CH4_MAKE_ALIASES_WITHOUT_OPT
% Create alias copies so LaTeX can use clean filenames without the opt_/auto prefix.
% This is purely a convenience layer and does not change any evaluation result.

    if ~isfield(figOpt,'force_overwrite_alias')
        figOpt.force_overwrite_alias = false;
    end

    % src (opt) -> dst (clean)
    pairs = {
        {'ch4_opt_dataset_stats',    'ch4_dataset_stats'}
        {'ch4_opt_prf_by_group',     'ch4_prf_by_group'}
        {'ch4_opt_timing_tau_box',   'ch4_timing_tau_box'}
        {'ch4_opt_timing_tau_cdf',   'ch4_timing_tau_cdf'}
        {'ch4_opt_ablation_by_group','ch4_ablation_by_group'}
        {'ch4_opt_ablation_by_group','ch4_ablation_fig'}   % LaTeX label uses fig:ch4_ablation_fig
    };

    for i = 1:numel(pairs)
        srcBase = pairs{i}{1};
        dstBase = pairs{i}{2};
        srcPdf = fullfile(p.images_dir, [srcBase '.pdf']);
        dstPdf = fullfile(p.images_dir, [dstBase '.pdf']);

        if isfile(srcPdf)
            if (~isfile(dstPdf)) || figOpt.force_overwrite_alias
                ch4_copy_figpair(srcPdf, dstPdf);
            end
        end
    end
end


%% ================= Extra figure pools (optional) =================

function make_optional_fig_pool(T_file, T_group, T_ds, T_timing, tim_rows, ...
    A_drift_mag, A_is_park, B_dist, B_is_leave, C_file, T_ab, cfg, p, figOpt)
%MAKE_OPTIONAL_FIG_POOL Generate additional figures for selection (ch4_opt_*).
% These figures are not required by the LaTeX placeholders; they help you pick
% better illustrations or provide supplementary analysis.

    if nargin < 13
        figOpt = struct();
    end

    outDir = p.images_dir;
    if ~exist(outDir,'dir'); mkdir(outDir); end

    % ---------- 1) PRF by group ----------
    try
        if ~isempty(T_group)
            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            M = [T_group.P, T_group.R, T_group.F1];
            bar(ax, M);
            ylim(ax, [0 1]);
            xticks(ax, 1:height(T_group));
            xticklabels(ax, cellstr(T_group.group));
            ylabel(ax, '指标值');
            legend(ax, {'精确率 P','召回率 R','F1'}, 'Location','northoutside','Orientation','horizontal');
            title(ax, '分工况检测性能（GLOBAL）', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_prf_by_group.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 2) Errors by group: counts + rates ----------
    try
        if ~isempty(T_group)
            fig = ch4_newfig(16, 10);
            tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

            ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
            C = [T_group.TP, T_group.FP, T_group.FN];
            bar(ax1, C);
            xticks(ax1, 1:height(T_group));
            xticklabels(ax1, cellstr(T_group.group));
            ylabel(ax1, '次数');
            legend(ax1, {'TP','FP','FN'}, 'Location','northoutside','Orientation','horizontal');
            title(ax1, 'TP/FP/FN 统计', 'FontWeight','normal');

            ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
            plot(ax2, 1:height(T_group), 100*T_group.Rf, '-o', 'LineWidth', 1.2);
            plot(ax2, 1:height(T_group), 100*T_group.Rm, '--s', 'LineWidth', 1.2);
            xticks(ax2, 1:height(T_group));
            xticklabels(ax2, cellstr(T_group.group));
            ylabel(ax2, '比例/%');
            legend(ax2, {'误检率 R_f','漏检率 R_m'}, 'Location','northoutside','Orientation','horizontal');
            title(ax2, '误检率/漏检率（按 GT 事件数归一）', 'FontWeight','normal');

            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_errors_by_group.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 3) Dataset stats ----------
    try
        if ~isempty(T_ds)
            fig = ch4_newfig(16, 10);
            tl = tiledlayout(fig, 2, 2, 'TileSpacing','compact', 'Padding','compact');

            ax = nexttile(tl, 1); bar(ax, T_ds.num_files); grid(ax,'on');
            title(ax, '文件数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));

            ax = nexttile(tl, 2); bar(ax, T_ds.num_parking_gt); grid(ax,'on');
            title(ax, '真值占用事件数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));

            ax = nexttile(tl, 3); bar(ax, T_ds.num_vehicle_events); grid(ax,'on');
            title(ax, '车辆扰动事件数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));
            xlabel(ax, '工况组');

            ax = nexttile(tl, 4); bar(ax, T_ds.num_pass_est); grid(ax,'on');
            title(ax, '通过事件估计数', 'FontWeight','normal'); xticks(ax,1:height(T_ds)); xticklabels(ax,cellstr(T_ds.group));
            xlabel(ax, '工况组');

            title(tl, '数据集统计（估计口径）', 'FontWeight','normal');

            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_dataset_stats.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 4) Per-file F1 distribution ----------
    try
        if ~isempty(T_file)
            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            if exist('boxplot','file') == 2
                boxplot(ax, T_file.F1, T_file.group);
            else
                % fallback: jittered scatter
                groups = unique(T_file.group,'stable');
                for i = 1:numel(groups)
                    g = groups(i);
                    y = T_file.F1(T_file.group==g);
                    x = i + 0.12*(rand(size(y))-0.5);
                    scatter(ax, x, y, 18, 'filled');
                end
                xticks(ax, 1:numel(groups));
                xticklabels(ax, cellstr(groups));
            end
            ylim(ax, [0 1]);
            ylabel(ax, 'F1');
            title(ax, '单文件 F1 分布（按工况组）', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_f1_box_by_group.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 5) Per-file F1 vs events ----------
    try
        if ~isempty(T_file)
            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            groups = unique(T_file.group,'stable');
            mk = {'o','s','^','d','x','+'};
            for i = 1:numel(groups)
                g = groups(i);
                idx = T_file.group==g;
                scatter(ax, T_file.events(idx), T_file.F1(idx), 26, mk{1+mod(i-1,numel(mk))}, 'filled');
            end
            xlabel(ax, '车辆扰动事件数');
            ylabel(ax, 'F1');
            ylim(ax, [0 1]);
            legend(ax, cellstr(groups), 'Location','northoutside','Orientation','horizontal');
            title(ax, '单文件 F1 vs 车流扰动强度（事件数）', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_f1_vs_events.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 6) Top/Bottom per-file ranking ----------
    try
        if ~isempty(T_file)
            Tf = sortrows(T_file, 'F1', 'descend');
            k = min(10, height(Tf));
            top = Tf(1:k, {'file','group','F1'});
            bot = Tf(max(height(Tf)-k+1,1):height(Tf), {'file','group','F1'});

            fig = ch4_newfig(16, 10);
            tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

            ax1 = nexttile(tl, 1); barh(ax1, top.F1); grid(ax1,'on');
            xlim(ax1, [0 1]);
            yticklabels(ax1, cellstr(top.group + " | " + top.file));
            title(ax1, 'Top 文件（按 F1 降序）', 'FontWeight','normal');

            ax2 = nexttile(tl, 2); barh(ax2, flipud(bot.F1)); grid(ax2,'on');
            xlim(ax2, [0 1]);
            yticklabels(ax2, cellstr(flipud(bot.group + " | " + bot.file)));
            title(ax2, 'Bottom 文件（按 F1 升序）', 'FontWeight','normal');

            title(tl, '单文件 F1 排名（用于挑选典型样例）', 'FontWeight','normal');

            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_per_file_rank.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 7) Timing boxplots ----------
    try
        if ~isempty(tim_rows)
            fig = ch4_newfig(16, 10);
            tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

            ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
            if exist('boxplot','file') == 2
                boxplot(ax1, tim_rows.tau_in, tim_rows.group);
            else
                scatter(ax1, double(categorical(tim_rows.group)), tim_rows.tau_in, 10, 'filled');
            end
            ylabel(ax1, '\tau_{in} / s');
            title(ax1, '停车确认上报延迟 \tau_{in}', 'FontWeight','normal');

            ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
            if exist('boxplot','file') == 2
                boxplot(ax2, tim_rows.tau_out, tim_rows.group);
            else
                scatter(ax2, double(categorical(tim_rows.group)), tim_rows.tau_out, 10, 'filled');
            end
            ylabel(ax2, '\tau_{out} / s'); xlabel(ax2, '工况组');
            title(ax2, '释放确认上报延迟 \tau_{out}', 'FontWeight','normal');

            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_timing_tau_box.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 8) Timing CDFs ----------
    try
        if ~isempty(tim_rows)
            fig = ch4_newfig(16, 10);
            tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

            ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
            plot_cdf_by_group(ax1, tim_rows, 'tau_in', '\tau_{in} / s');
            title(ax1, '\tau_{in} 的经验分布（CDF）', 'FontWeight','normal');

            ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
            plot_cdf_by_group(ax2, tim_rows, 'tau_out', '\tau_{out} / s');
            title(ax2, '\tau_{out} 的经验分布（CDF）', 'FontWeight','normal');

            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_timing_tau_cdf.pdf'));
            close(fig);

            fig = ch4_newfig(16, 10);
            tl = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');

            ax1 = nexttile(tl, 1); hold(ax1,'on'); grid(ax1,'on');
            tmp = tim_rows; tmp.abs_dt_in = abs(tmp.dt_in);
            plot_cdf_by_group(ax1, tmp, 'abs_dt_in', '|\\Delta t_{in}| / s');
            title(ax1, '|\Delta t_{in}| 的经验分布（CDF）', 'FontWeight','normal');

            ax2 = nexttile(tl, 2); hold(ax2,'on'); grid(ax2,'on');
            tmp = tim_rows; tmp.abs_dt_out = abs(tmp.dt_out);
            plot_cdf_by_group(ax2, tmp, 'abs_dt_out', '|\\Delta t_{out}| / s');
            title(ax2, '|\Delta t_{out}| 的经验分布（CDF）', 'FontWeight','normal');

            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_timing_dt_cdf.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 9) A drift CDF ----------
    try
        if ~isempty(A_drift_mag)
            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            v0 = A_drift_mag(A_is_park==0);
            v1 = A_drift_mag(A_is_park==1);
            plot_emp_cdf(ax, v0, '-', 1.2);
            plot_emp_cdf(ax, v1, '--', 1.2);
            xlabel(ax, '漂移幅值 ||\Delta B||_2'); ylabel(ax, 'CDF');
            legend(ax, {'通过/干扰','停车到达'}, 'Location','best');
            title(ax, 'A类：漂移幅值的经验分布', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_A_drift_cdf.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 10) B dist CDF ----------
try
    if ~isempty(B_dist)
        fig = ch4_newfig(16, 8);
        ax = axes(fig); hold(ax,'on'); grid(ax,'on');

        v_keep  = B_dist((B_is_leave==0) & ~isnan(B_dist));
        v_leave = B_dist((B_is_leave==1) & ~isnan(B_dist));

        plot_emp_cdf(ax, v_keep, '-', 1.2);

        leg = {'仍占用扰动事件（保持门控）'};
        if numel(v_leave) >= 5
            plot_emp_cdf(ax, v_leave, '--', 1.2);
            leg = {'仍占用扰动事件（保持门控）', '驶离事件（若dist有效）'};
        else
            text(ax, 0.02, 0.10, '注：驶离多由 D_{free}(back2env) 判决，dist样本可能缺失', ...
                'Units','normalized', 'FontSize', 10, 'Color', [0.3 0.3 0.3]);
        end

        xline(ax, cfg.pk.dist_th, ':', sprintf('dist_{th}=%.1f', cfg.pk.dist_th), 'LineWidth', 1.2);

        if ~isempty(v_keep)
            acc = mean(v_keep < cfg.pk.dist_th);
            text(ax, 0.02, 0.90, sprintf('Acc@dist_{th}=%.1f%%', 100*acc), ...
                'Units','normalized', 'FontSize', 11, 'Color', [0.1 0.1 0.1]);
        end

        xlabel(ax, '相似距离 dist');
        ylabel(ax, 'CDF');
        legend(ax, leg, 'Location', 'best');
        title(ax, 'B类：相似性门控阈值 dist_{th} 的经验分布', 'FontWeight', 'normal');
        ch4_apply_style(fig);
        ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_B_dist_cdf.pdf'));
        close(fig);
    end
catch
end

% ---------- 11) C per-file ratios ----------

    try
        if ~isempty(C_file)
            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            M = [C_file.stable_found_ratio, C_file.used_degrade_ratio];
            if exist('boxplot','file') == 2
                boxplot(ax, M, 'Labels', {'稳定点可得率','退化分支使用率'});
            else
                scatter(ax, ones(size(M,1),1), M(:,1), 18, 'filled'); hold(ax,'on');
                scatter(ax, 2*ones(size(M,1),1), M(:,2), 18, 'filled');
                xlim(ax, [0.5 2.5]);
                set(ax,'XTick',[1 2],'XTickLabel',{'稳定点可得率','退化分支使用率'});
            end
            ylim(ax, [0 1]);
            ylabel(ax, '比例');
            title(ax, 'C类：按文件统计的稳定点可得率与退化分支使用率', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_C_file_ratios.pdf'));
            close(fig);
        end
    catch
    end

    % ---------- 12) Ablation plots ----------
    try
        if exist('T_ab','var') && ~isempty(T_ab) && height(T_ab) > 0
            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            bar(ax, T_ab.F1_all);
            ylim(ax, [0 1]);
            xticks(ax, 1:height(T_ab));
            xticklabels(ax, cellstr(T_ab.variant));
            ylabel(ax, 'F1');
            title(ax, '消融实验：总体 F1（GLOBAL）', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_ablation_all.pdf'));
            close(fig);

            fig = ch4_newfig(16, 8);
            ax = axes(fig); hold(ax,'on'); grid(ax,'on');
            M = [T_ab.F1_A, T_ab.F1_B, T_ab.F1_C, T_ab.F1_D];
            bar(ax, M);
            ylim(ax, [0 1]);
            xticks(ax, 1:height(T_ab));
            xticklabels(ax, cellstr(T_ab.variant));
            ylabel(ax, 'F1');
            legend(ax, {'A','B','C','D'}, 'Location','best');
            title(ax, '消融实验：分工况 F1（GLOBAL）', 'FontWeight','normal');
            ch4_apply_style(fig);
            ch4_export_fig(fig, fullfile(outDir, 'ch4_opt_ablation_by_group.pdf'));
            close(fig);
        end
    catch
    end

end


function make_extra_examples(T_file, GT, p, cfg, post, IOU_TH, figOpt)
%MAKE_EXTRA_EXAMPLES Generate additional case/wave figures for selection.
% Output naming:
%   ch4_case_<G>_<tag>_padXXs.pdf/.png
%   ch4_wave_<G>_<tag>_padXXs.pdf/.png

    if isempty(T_file) || isempty(GT)
        return;
    end

    groups = ["A","B","C","D"];
    pads = figOpt.extra_case_pads_sec;
    if isempty(pads); pads = [8 20]; end

    rng(0); % deterministic

    sel = table('Size',[0 4], ...
        'VariableTypes',{'string','string','string','double'}, ...
        'VariableNames',{'file','group','tag','F1'});

    for gg = 1:numel(groups)
        g = groups(gg);
        Tf = T_file(T_file.group==g,:);
        if isempty(Tf); continue; end

        % sort by F1
        Tf = sortrows(Tf, 'F1', 'descend');
        best = Tf(1,:);
        worst = Tf(end,:);
        mid = Tf(round((height(Tf)+1)/2),:);

        sel = [sel; {best.file, g, "best", best.F1}]; %#ok<AGROW>
        sel = [sel; {mid.file,  g, "mid",  mid.F1}]; %#ok<AGROW>
        sel = [sel; {worst.file,g, "worst",worst.F1}]; %#ok<AGROW>

        % random picks (exclude already selected)
        k = figOpt.extra_random_per_group;
        if isempty(k) || k <= 0; continue; end

        allFiles = unique(Tf.file, 'stable');
        picked = unique([best.file; mid.file; worst.file], 'stable');
        cand = setdiff(allFiles, picked, 'stable');
        if isempty(cand); continue; end
        rp = randperm(numel(cand), min(k, numel(cand)));
        for j = 1:numel(rp)
            sel = [sel; {cand(rp(j)), g, "rand" + string(j), NaN}]; %#ok<AGROW>
        end
    end

    % de-duplicate
    [~, ia] = unique(sel(:,{'file','group','tag'}), 'rows', 'stable');
    sel = sel(ia,:);

    if height(sel) > figOpt.max_extra_cases_total
        sel = sel(1:figOpt.max_extra_cases_total,:);
    end

    fprintf("[Extra] will generate %d extra example(s) ...\n", height(sel));

    for i = 1:height(sel)
        fileName = sel.file(i);
        g = sel.group(i);
        tag = sel.tag(i);

        gt_f = GT(GT.file == fileName, :);
        if isempty(gt_f)
            continue;
        end

        csvPath = ch4_find_csv(fileName, p.root, p.synth);
        data = ch4_load_csv(csvPath, cfg.fs);
        out  = ch4_run_parking_fsm(data, cfg);

        [pred_k, conf_k] = postprocess_pred_conf(out.pred_k, out.conf_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec); %#ok<NASGU>
        gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));

        % Titles in Chinese (file names may contain underscores)
        f1v = sel.F1(i);
        if isfinite(f1v)
            titleBase = sprintf('%s类-%s（F1=%.3f）：%s', char(g), char(tag_to_cn(tag)), f1v, char(fileName));
        else
            titleBase = sprintf('%s类-%s：%s', char(g), char(tag_to_cn(tag)), char(fileName));
        end

            for pp = 1:numel(pads)
                padSec = pads(pp);

                % D类慢漂移：窗口过短不易观察基线变化，允许对D类强制放大padSec
                if isfield(figOpt,'extra_case_padSec_D') && strcmpi(char(g),'D') && padSec < figOpt.extra_case_padSec_D
                    padSec = figOpt.extra_case_padSec_D;
                end

                % 可选：手工指定中心时刻（秒），用于挑选最能体现漂移/退化的窗口
                tCenterManual = [];
                if isfield(figOpt,'extra_case_tCenter_by_group')
                    try
                        tCenterManual = figOpt.extra_case_tCenter_by_group.(char(g));
                    catch
                        tCenterManual = [];
                    end
                end
            padTag = sprintf('pad%ds', round(padSec));

            figCase = fullfile(p.images_dir, "ch4_case_" + g + "_" + tag + "_" + padTag + ".pdf");
            figWave = fullfile(p.images_dir, "ch4_wave_" + g + "_" + tag + "_" + padTag + ".pdf");

            % Case: ||B|| + R/M
            if ~isempty(tCenterManual)
    plot_case_one(data, out, pred_k, gt_idx, figCase, titleBase, cfg, 'padSec', padSec, 'tCenter', tCenterManual);
else
    plot_case_one(data, out, pred_k, gt_idx, figCase, titleBase, cfg, 'padSec', padSec);
end

            % Wave: 3-axis + stable flag
            plot_wave_group(data, out, pred_k, gt_idx, g, figWave, cfg, padSec);
        end
    end

end


function s = tag_to_cn(tag)
    tag = string(tag);
    if startsWith(tag, "best"); s = "最佳";
    elseif startsWith(tag, "mid"); s = "中位";
    elseif startsWith(tag, "worst"); s = "最差";
    elseif startsWith(tag, "rand"); s = "随机" + extractAfter(tag, "rand");
    else; s = tag;
    end
end


function plot_cdf_by_group(ax, T, fieldName, xlab)
    groups = unique(T.group, 'stable');
    for i = 1:numel(groups)
        g = groups(i);
        v = T.(fieldName)(T.group==g);
        plot_emp_cdf(ax, v, '-', 1.0);
    end
    xlabel(ax, xlab);
    ylabel(ax, 'CDF');
    legend(ax, cellstr(groups), 'Location','northoutside','Orientation','horizontal');
end


function plot_emp_cdf(ax, v, style, lw)
    v = v(:);
    v = v(isfinite(v));
    if isempty(v)
        return;
    end
    v = sort(v);
    n = numel(v);
    y = (1:n) / n;
    plot(ax, v, y, style, 'LineWidth', lw);
end

function fig = ch4_newfig(w_cm, h_cm)
%CH4_NEWFIG Create a white, off-screen figure with fixed size (cm)
    fig = figure('Visible','off', 'Color','w');
    set(fig, 'Units','centimeters', 'Position',[2 2 w_cm h_cm]);
    set(fig, 'PaperPositionMode','auto');
end

function ch4_export_paper_figs(p, figOpt)
%CH4_EXPORT_PAPER_FIGS Copy selected figures (pdf/png) to a separate folder for thesis inclusion.
%   This keeps your normal output under p.images_dir untouched, and provides a clean folder
%   (figOpt.paper_fig_dir) that only contains the figures you actually reference in Ch4 LaTeX.

% destination folder
dstDir = fullfile(p.out, 'paper_figs');
if isfield(figOpt,'paper_fig_dir') && ~isempty(figOpt.paper_fig_dir)
    dstDir = figOpt.paper_fig_dir;
end
if ~exist(dstDir,'dir')
    mkdir(dstDir);
end

% whether also copy png
copyPng = true;
if isfield(figOpt,'paper_copy_png')
    copyPng = figOpt.paper_copy_png;
end

% figure basenames to export
if isfield(figOpt,'paper_bases') && ~isempty(figOpt.paper_bases)
    bases = figOpt.paper_bases;
else
    bases = { 'ch4_pass_vs_park_sim', 'ch4_pipeline', 'ch4_stability_demo', 'ch4_fsm_degrade' };
end

% D类 case 由主脚本生成为 ch4_case_D.pdf；若缺失会在 manifest 中列出

copiedPdf = {};
missingPdf = {};

for i = 1:numel(bases)
    base = bases{i};

    % pdf
    srcPdf = fullfile(p.images_dir, [base '.pdf']);
    if exist(srcPdf,'file')
        dstPdf = fullfile(dstDir, [base '.pdf']);
        copyfile(srcPdf, dstPdf);
        copiedPdf{end+1} = [base '.pdf']; %#ok<AGROW>
    else
        missingPdf{end+1} = [base '.pdf']; %#ok<AGROW>
    end

    % png (optional)
    if copyPng
        srcPng = fullfile(p.images_dir, [base '.png']);
        if exist(srcPng,'file')
            dstPng = fullfile(dstDir, [base '.png']);
            copyfile(srcPng, dstPng);
        end
    end
end

% manifest for quick check
manifest = fullfile(dstDir, 'manifest_ch4_paper_figs.txt');
fid = fopen(manifest, 'w');
if fid > 0
    fprintf(fid, '# Ch4 paper figures exported from: %s\n', p.images_dir);
    fprintf(fid, '# Export time: %s\n\n', datestr(now, 31));

    fprintf(fid, '[COPIED_PDF]\n');
    for i = 1:numel(copiedPdf)
        fprintf(fid, '%s\n', copiedPdf{i});
    end

    if ~isempty(missingPdf)
        fprintf(fid, '\n[MISSING_PDF]\n');
        for i = 1:numel(missingPdf)
            fprintf(fid, '%s\n', missingPdf{i});
        end
    end
    fclose(fid);
end

fprintf('=== 已导出论文用图到: %s (%d/%d pdf found) ===\n', dstDir, numel(copiedPdf), numel(bases));
end

