% function ch4_make_thesis_4cases(varargin)
% %CH4_MAKE_THESIS_4CASES  生成论文用四张 case 图（A/B/C/D），对齐 fig_*_win.csv 窗口。
% % - 仅用于“机制/现象展示”（允许每类用各自更合适参数）。
% % - 输出：A类/B类/C类/D类.pdf + .png（默认到 ch4_local_paths().images_dir）
% %
% % 用法：
% %   ch4_make_thesis_4cases();
% %   ch4_make_thesis_4cases('winCsvDir', 'D:\...\tables\ch4_csv', 'outDir', 'D:\...\images');
% 
% %% ---- Path bootstrap ----
% thisDir = fileparts(mfilename('fullpath'));
% try
%     addpath(genpath(thisDir));
%     addpath(genpath(fileparts(thisDir)));
% catch
% end
% 
% p = ch4_local_paths();
% 
% ip = inputParser;
% addParameter(ip, 'winCsvDir', p.csv_dir, @(s)ischar(s)||isstring(s));
% addParameter(ip, 'outDir',    p.images_dir, @(s)ischar(s)||isstring(s));
% parse(ip, varargin{:});
% winCsvDir = string(ip.Results.winCsvDir);
% outDir    = string(ip.Results.outDir);
% if ~exist(outDir,'dir'); mkdir(outDir); end
% 
% %% ---- Config base (GLOBAL best) ----
% if exist('cfg_global_best','file') == 2
%     [cfg0, post0] = cfg_global_best();
% else
%     [cfg0, post0] = ch4_config_tuned_v2("GLOBAL");
%     cfg0.pk.D_th    = 36.0;
%     cfg0.pk.dist_th = 4.0;
%     cfg0.ref.D_upd  = 30.0;
%     post0.Tmin_sec      = 6.0;
%     post0.gap_merge_sec = 0.0;
% end
% cfg0.fs = round(cfg0.fs); % 防止 ch4_stability 里 1:n0 报“冒号需要整数”
% 
% %% ---- GT ----
% GT = readtable(p.gt, "VariableNamingRule","preserve");
% GT.file = string(GT.file);
% if exist('ch4_append_synth_gt_all_events','file') == 2
%     try
%         GT = ch4_append_synth_gt_all_events(GT, p.synth);
%         GT.file = string(GT.file);
%     catch
%     end
% end
% 
% %% ---- Four cases (wave windows) ----
% cases = struct([]);
% cases(1).g = "A"; cases(1).gtName = "20240723_停车检测_sheet2_clean.csv";      cases(1).winCsv="fig_a_win.csv";
% cases(2).g = "B"; cases(2).gtName = "20240723_停车检测_sheet2_e4_B_synth.csv"; cases(2).winCsv="fig_b_win.csv";
% cases(3).g = "C"; cases(3).gtName = "20240723_停车检测_sheet2_e4_C_synth.csv"; cases(3).winCsv="fig_c_win.csv";
% cases(4).g = "D"; cases(4).gtName = "20240723_停车检测_sheet1_clean.csv";      cases(4).winCsv="fig_d_win.csv";
% 
% for i = 1:numel(cases)
%     g = cases(i).g;
%     caseName = g + "类";
% 
%     winPath = fullfile(winCsvDir, cases(i).winCsv);
%     if exist(winPath,'file') ~= 2
%         % fallback: try current dir
%         winPath = fullfile(thisDir, cases(i).winCsv);
%     end
%     assert(exist(winPath,'file')==2, "找不到窗口文件: %s", cases(i).winCsv);
% 
%     % ---- load wave window as data ----
%     data = load_wave_window(winPath, cfg0.fs);
% 
%     % ---- per-case tuned (展示用) ----
%     cfg = cfg0; post = post0;
%     [cfg, post] = apply_case_params(cfg, post, g);
% 
%     % ---- run FSM ----
%     out = ch4_run_parking_fsm(data, cfg);
% 
%     % ---- postprocess pred ----
%     pred_k = ch4_pred_postprocess(out.pred_k, cfg.fs, post.Tmin_sec, post.gap_merge_sec);
% 
%     % ---- GT -> local idx ----
%     gt_f = GT(GT.file == string(cases(i).gtName), :);
%     gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
%     gt_idx = clip_to_window(gt_idx, data.n);
% 
%     % ---- export ----
%     figPdf = fullfile(outDir, caseName + ".pdf");
%     plot_case_one_thesis(data, out, pred_k, gt_idx, figPdf, caseName, cfg, g);
% 
%     fprintf("[%s] t=[%.2f, %.2f], n=%d -> %s\n", caseName, data.t(1), data.t(end), data.n, figPdf);
% end
% end
% 
% %% ======================================================================
% function [cfg, post] = apply_case_params(cfg, post, g)
% % per-case tuned params ONLY for mechanism display
% g = upper(string(g));
% switch g
%     case "A"
%         % keep GLOBAL best
%     case "B"
%         cfg.pk.dist_th = 25;   % B: 扰动多，适当放宽 dist 门控
%     case "C"
%         cfg.pk.D_free = 30;    % C: 回到环境更困难，放宽 free 判据
%     case "D"
%         cfg.pk.D_free = 65;    % D: 漂移明显，否则很难“回到环境”
%     otherwise
% end
% end
% 
% function data = load_wave_window(csvPath, fsDefault)
% T = readtable(csvPath, "VariableNamingRule","preserve");
% v = lower(string(T.Properties.VariableNames));
% 
% % time
% assert(any(v=="t"), "窗口CSV缺少 t 列: %s", csvPath);
% t = double(T{:, find(v=="t",1)});
% t = t(:);
% 
% % B columns
% if all(ismember(["x","y","z"], v))
%     bx = double(T{:, find(v=="x",1)});
%     by = double(T{:, find(v=="y",1)});
%     bz = double(T{:, find(v=="z",1)});
% elseif all(ismember(["bx","by","bz"], v))
%     bx = double(T{:, find(v=="bx",1)});
%     by = double(T{:, find(v=="by",1)});
%     bz = double(T{:, find(v=="bz",1)});
% else
%     error("窗口CSV缺少 (x,y,z) 或 (Bx,By,Bz): %s", csvPath);
% end
% B = [bx(:), by(:), bz(:)];
% 
% % fs infer
% fs = fsDefault;
% if numel(t) >= 3
%     dt = diff(t);
%     fs_est = 1/median(dt);
%     if isfinite(fs_est) && fs_est > 1
%         fs = round(fs_est);
%     end
% end
% 
% % absolute k
% if any(v=="k")
%     k = double(T{:, find(v=="k",1)});
% else
%     k = round(t * fs);
% end
% k = k(:);
% 
% data = struct();
% data.t = t;
% data.k = k;
% data.B = B;
% data.n = size(B,1);
% data.fs = fs;
% end
% 
% function seg2 = clip_to_window(seg, n)
% seg2 = zeros(0,2);
% if isempty(seg) || size(seg,2)~=2, return; end
% seg = round(seg);
% for i = 1:size(seg,1)
%     a = seg(i,1); b = seg(i,2);
%     if b < 1 || a > n, continue; end
%     a = max(1,a); b = min(n,b);
%     if b >= a
%         seg2(end+1,:) = [a b]; %#ok<AGROW>
%     end
% end
% end
% 
% %% ===================== plotting =====================
% function plot_case_one_thesis(data, out, pred_k, gt_idx, figPdf, figTitle, cfg, g)
% t = data.t(:); B = data.B; n = data.n; fs = cfg.fs;
% 
% % baseline for ΔB (window start 2s)
% k_ref = 1:min(n, max(1, round(2*fs)));
% S_ref = mean(B(k_ref,:), 1);
% dB = B - S_ref;
% 
% % stable
% stable = get_stable_vec(out, n);
% 
% % S_pre trace (visualization)
% [S_pre_tr, updLimited] = build_Spre_trace(data, out, pred_k, cfg);
% D = vecnorm(B - S_pre_tr, 2, 2);
% 
% distSeries = event_value_series(n, out, "dist");
% 
% stableSeg   = binary_to_segments(stable);
% degradeSeg  = eventflag_to_segments(n, out, "used_degrade", round(0.6*fs));
% distKeepSeg = event_distkeep_segments(n, out, cfg, round(0.6*fs));
% updLimSeg   = binary_to_segments(updLimited);
% 
% % center marker (use longest GT if exists)
% tC = 0.5*(t(1)+t(end));
% if ~isempty(gt_idx)
%     lens = gt_idx(:,2)-gt_idx(:,1);
%     [~,jj] = max(lens);
%     a = max(1,min(n,gt_idx(jj,1)));
%     b = max(1,min(n,gt_idx(jj,2)));
%     tC = 0.5*(t(a)+t(b));
% end
% 
% fig = figure('Visible','off','Color','w','Position',[80 80 1200 900]);
% tl = tiledlayout(fig, 4, 1, 'Padding','compact', 'TileSpacing','compact');
% 
% % Row1
% ax1 = nexttile(tl,1); hold(ax1,'on'); box(ax1,'on'); grid(ax1,'on');
% p1 = plot(ax1, t, dB(:,1), 'LineWidth',1.2);
% p2 = plot(ax1, t, dB(:,2), 'LineWidth',1.2);
% p3 = plot(ax1, t, dB(:,3), 'LineWidth',1.2);
% yline(ax1, 0, 'r--', 'LineWidth',1.0, 'HandleVisibility','off');
% xline(ax1, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');
% title(ax1, figTitle, 'Interpreter','none');
% ylabel(ax1, 'ΔB / nT');
% lg = legend(ax1,[p1 p2 p3],{'ΔB_x','ΔB_y','ΔB_z'},'Location','northeast');
% lg.Box='off'; lg.AutoUpdate='off';
% shade(ax1, t, gt_idx,  [0.86 0.86 0.86], 0.10);
% shade(ax1, t, pred_k, [0.80 0.90 1.00], 0.08);
% 
% % Row2
% ax2 = nexttile(tl,2); hold(ax2,'on'); box(ax2,'on'); grid(ax2,'on');
% yyaxis(ax2,'left');
% plot(ax2, t, D, 'LineWidth',1.2);
% ylabel(ax2, 'D(t) / nT');
% xline(ax2, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');
% 
% % threshold lines (no inline label)
% hasTh = isfield(cfg,'pk') && isfield(cfg.pk,'D_th')   && isfinite(cfg.pk.D_th);
% hasFr = isfield(cfg,'pk') && isfield(cfg.pk,'D_free') && isfinite(cfg.pk.D_free);
% hasDistTh = isfield(cfg,'pk') && isfield(cfg.pk,'dist_th') && isfinite(cfg.pk.dist_th);
% 
% if hasTh, yline(ax2, cfg.pk.D_th, '--', 'LineWidth',1.0, 'HandleVisibility','off'); end
% if hasFr, yline(ax2, cfg.pk.D_free, ':',  'LineWidth',1.0, 'HandleVisibility','off'); end
% 
% % always show right axis for consistency (even if no points)
% yyaxis(ax2,'right');
% idx = find(isfinite(distSeries));
% if ~isempty(idx)
%     plot(ax2, t(idx), distSeries(idx), 'o', 'MarkerSize',4, 'LineWidth',1.0);
%     maxDist = max(distSeries(idx));
% else
%     maxDist = 0;
% end
% ylabel(ax2, 'dist（事件点）');
% if hasDistTh
%     yline(ax2, cfg.pk.dist_th, '--', 'LineWidth',1.0, 'HandleVisibility','off');
% end
% % set right ylim to keep dist_th visible and avoid 0~1 default
% yMax = max([1, maxDist*1.05, (hasDistTh)*cfg.pk.dist_th*2 + (~hasDistTh)*1]);
% ylim(ax2, [0 yMax]);
% 
% % info box (top-right, never overlap/clip)
% yyaxis(ax2,'left');
% info = {};
% if hasTh, info{end+1} = sprintf('D_{th}=%.1f', cfg.pk.D_th); end
% if hasFr, info{end+1} = sprintf('D_{free}=%.1f', cfg.pk.D_free); end
% if hasDistTh, info{end+1} = sprintf('dist_{th}=%.1f', cfg.pk.dist_th); end
% if ~isempty(info)
%     txt = strjoin(info, newline);
%     text(ax2, 0.985, 0.92, txt, 'Units','normalized', ...
%         'HorizontalAlignment','right','VerticalAlignment','top', ...
%         'Interpreter','tex','BackgroundColor','w','Margin',3,'Clipping','off');
% end
% shade(ax2, t, gt_idx,  [0.86 0.86 0.86], 0.08);
% shade(ax2, t, pred_k, [0.80 0.90 1.00], 0.06);
% 
% % Row3
% ax3 = nexttile(tl,3); hold(ax3,'on'); box(ax3,'on'); grid(ax3,'on');
% xlim(ax3,[t(1) t(end)]); ylim(ax3,[0 1]);
% bars(ax3,t, stableSeg,   0.78,0.95,[0.70 0.90 0.70],0.85);
% bars(ax3,t, degradeSeg,  0.56,0.72,[1.00 0.86 0.65],0.85);
% bars(ax3,t, distKeepSeg, 0.34,0.50,[0.80 0.90 1.00],0.85);
% bars(ax3,t, updLimSeg,   0.12,0.28,[1.00 0.75 0.75],0.85);
% yticks(ax3,[0.20 0.42 0.64 0.865]);
% yticklabels(ax3,{'upd\_limit','dist\_gate','degrade','stable'});
% ylabel(ax3,'内部逻辑');
% xline(ax3, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');
% 
% % Row4
% ax4 = nexttile(tl,4); hold(ax4,'on'); box(ax4,'on'); grid(ax4,'on');
% xlim(ax4,[t(1) t(end)]); ylim(ax4,[0 1]);
% yticks(ax4,[0.25 0.75]); yticklabels(ax4,{'Pred','GT'});
% xlabel(ax4,'时间 / s');
% bars(ax4,t, pred_k, 0.10,0.40,[0.80 0.90 1.00],0.85);
% bars(ax4,t, gt_idx,  0.60,0.90,[0.86 0.86 0.86],0.85);
% xline(ax4, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');
% 
% linkaxes([ax1 ax2 ax3 ax4],'x');
% apply_style(fig);
% 
% export_fig(fig, figPdf);
% close(fig);
% end
% 
% function stable = get_stable_vec(out, n)
% stable = [];
% if isfield(out,'st') && isfield(out.st,'stableState')
%     stable = out.st.stableState;
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
% function [S_pre_tr, updLimited] = build_Spre_trace(data, out, pred_k, cfg)
% B=data.B; n=data.n; stable=get_stable_vec(out,n);
% 
% occ=false(n,1);
% if ~isempty(pred_k)
%     for i=1:size(pred_k,1)
%         a=max(1,round(pred_k(i,1))); b=min(n,round(pred_k(i,2)));
%         if b>=a, occ(a:b)=true; end
%     end
% end
% meanVec=[];
% if isfield(out,'st') && isfield(out.st,'meanVec')
%     meanVec=out.st.meanVec;
% end
% k0=find(stable,1,'first');
% if ~isempty(k0) && ~isempty(meanVec) && k0<=size(meanVec,1)
%     S_pre=meanVec(k0,:);
% else
%     S_pre=B(1,:);
% end
% 
% alpha=cfg.ref.alpha_free;
% useGate=isfield(cfg,'v') && isfield(cfg.v,'use_update_gate') && cfg.v.use_update_gate && isfield(cfg.ref,'D_upd');
% 
% S_pre_tr=zeros(n,3);
% updLimited=zeros(n,1);
% for k=1:n
%     S_pre_tr(k,:)=S_pre;
%     if occ(k), continue; end
%     if stable(k)<=0.5, continue; end
%     if ~isempty(meanVec) && k<=size(meanVec,1)
%         S_cand=meanVec(k,:);
%     else
%         L=max(1,round(0.5*cfg.fs));
%         a=max(1,k-L+1);
%         S_cand=mean(B(a:k,:),1);
%     end
%     d=S_cand-S_pre; nd=norm(d,2);
%     if ~useGate || nd<=cfg.ref.D_upd
%         S_pre=(1-alpha)*S_pre+alpha*S_cand;
%     else
%         updLimited(k)=1;
%         S_pre=S_pre+alpha*(cfg.ref.D_upd/max(nd,eps))*d;
%     end
% end
% end
% 
% function segs = binary_to_segments(sig)
% sig = sig(:) > 0.5;
% d = diff([false; sig; false]);
% st = find(d==1);
% ed = find(d==-1) - 1;
% segs = [st ed];
% end
% 
% function segs = eventflag_to_segments(n, out, fieldName, halfWin)
% segs=zeros(0,2);
% if ~isfield(out,'events')||isempty(out.events), return; end
% if ~isfield(out,'dbg')||~isfield(out.dbg,fieldName), return; end
% flag=out.dbg.(fieldName);
% mmax=min(numel(out.events),numel(flag));
% for m=1:mmax
%     if ~flag(m), continue; end
%     k=round(out.events(m).k_out);
%     a=max(1,k-halfWin); b=min(n,k+halfWin);
%     segs(end+1,:)=[a b]; %#ok<AGROW>
% end
% end
% 
% function segs = event_distkeep_segments(n, out, cfg, halfWin)
% segs=zeros(0,2);
% if ~isfield(out,'events')||isempty(out.events), return; end
% if ~isfield(out,'dbg')||~isfield(out.dbg,'dist'), return; end
% if ~isfield(cfg,'pk')||~isfield(cfg.pk,'dist_th'), return; end
% dist=out.dbg.dist(:);
% mmax=min(numel(out.events),numel(dist));
% for m=1:mmax
%     if ~isfinite(dist(m)), continue; end
%     if dist(m)>=cfg.pk.dist_th, continue; end
%     k=round(out.events(m).k_out);
%     a=max(1,k-halfWin); b=min(n,k+halfWin);
%     segs(end+1,:)=[a b]; %#ok<AGROW>
% end
% end
% 
% function vSeries = event_value_series(n, out, which)
% vSeries = nan(n,1);
% if ~isfield(out,'events')||isempty(out.events), return; end
% if ~isfield(out,'dbg')||~isfield(out.dbg,which), return; end
% v = out.dbg.(which)(:);
% mmax=min(numel(out.events),numel(v));
% for m=1:mmax
%     k=round(out.events(m).k_out);
%     if k>=1 && k<=n
%         vSeries(k)=v(m);
%     end
% end
% end
% 
% function shade(ax, t, segs, faceColor, alpha)
% if isempty(segs), return; end
% yyaxis(ax,'left');
% yl = ylim(ax);
% for i=1:size(segs,1)
%     a=max(1,segs(i,1)); b=min(numel(t),segs(i,2));
%     if b<=a, continue; end
%     x1=t(a); x2=t(b);
%     p=patch(ax,[x1 x2 x2 x1],[yl(1) yl(1) yl(2) yl(2)],faceColor,...
%         'FaceAlpha',alpha,'EdgeColor','none','HandleVisibility','off');
%     set(p,'HitTest','off');
% end
% end
% 
% function bars(ax, t, segs, y0, y1, faceColor, alpha)
% if isempty(segs), return; end
% for i=1:size(segs,1)
%     a=max(1,segs(i,1)); b=min(numel(t),segs(i,2));
%     if b<=a, continue; end
%     x1=t(a); x2=t(b);
%     p=patch(ax,[x1 x2 x2 x1],[y0 y0 y1 y1],faceColor,...
%         'FaceAlpha',alpha,'EdgeColor','none','HandleVisibility','off');
%     set(p,'HitTest','off');
% end
% end
% 
% function apply_style(fig)
% set(fig,'Color','w');
% axs=findall(fig,'Type','axes');
% for i=1:numel(axs)
%     ax=axs(i);
%     ax.Box='on';
%     ax.LineWidth=0.8;
%     ax.FontName='Microsoft YaHei';
%     ax.FontSize=11;
%     ax.GridAlpha=0.15;
%     ax.MinorGridAlpha=0.08;
% end
% lgs=findall(fig,'Type','legend');
% for i=1:numel(lgs)
%     lg=lgs(i);
%     lg.Box='off';
%     lg.FontName='Microsoft YaHei';
%     lg.FontSize=10;
% end
% end
% 
% function export_fig(fig, outPath)
% if isstring(outPath), outPath=char(outPath); end
% [p,name,ext]=fileparts(outPath);
% if isempty(ext), ext='.pdf'; outPath=fullfile(p,[name ext]); end
% if ~exist(p,'dir'); mkdir(p); end
% try
%     exportgraphics(fig, outPath, 'ContentType','vector');
% catch
%     print(fig, outPath, '-dpdf', '-painters');
% end
% pngPath=fullfile(p,[name '.png']);
% try
%     exportgraphics(fig, pngPath, 'Resolution', 300);
% catch
%     print(fig, pngPath, '-dpng', '-r300');
% end
% end

function ch4_make_thesis_4cases(varargin)
%CH4_MAKE_THESIS_4CASES  生成论文用四张 case 图（A/B/C/D）。
% - 逻辑：运算用各自 Case 调优参数；绘图（虚线、标注）统一用 Global 参数。
% - 排版：强制统一所有 Case 的 Y 轴量程（固定 ylim），确保论文排版完全对齐。
% - 输出：A类/B类/C类/D类.pdf + .png

%% ---- Path bootstrap ----
thisDir = fileparts(mfilename('fullpath'));
try
    addpath(genpath(thisDir));
    addpath(genpath(fileparts(thisDir)));
catch
end

p = ch4_local_paths();

ip = inputParser;
addParameter(ip, 'winCsvDir', p.csv_dir, @(s)ischar(s)||isstring(s));
addParameter(ip, 'outDir',    p.images_dir, @(s)ischar(s)||isstring(s));
parse(ip, varargin{:});
winCsvDir = string(ip.Results.winCsvDir);
outDir    = string(ip.Results.outDir);
if ~exist(outDir,'dir'); mkdir(outDir); end

%% ---- Config base (GLOBAL best) ----
if exist('cfg_global_best','file') == 2
    [cfg0, post0] = cfg_global_best();
else
    [cfg0, post0] = ch4_config_tuned_v2("GLOBAL");
    cfg0.pk.D_th    = 36.0;
    cfg0.pk.dist_th = 4.5;
    cfg0.ref.D_upd  = 30.0;
    cfg0.pk.D_free  = 27.1; % 确保有一个默认的 D_free
    post0.Tmin_sec      = 6.0;
    post0.gap_merge_sec = 0.0;
end
cfg0.fs = round(cfg0.fs); 

%% ---- GT ----
GT = readtable(p.gt, "VariableNamingRule","preserve");
GT.file = string(GT.file);
if exist('ch4_append_synth_gt_all_events','file') == 2
    try
        GT = ch4_append_synth_gt_all_events(GT, p.synth);
        GT.file = string(GT.file);
    catch
    end
end

%% ---- Four cases ----
cases = struct([]);
cases(1).g = "A"; cases(1).gtName = "20240723_停车检测_sheet2_clean.csv";      cases(1).winCsv="fig_a_win.csv";
cases(2).g = "B"; cases(2).gtName = "20240723_停车检测_sheet2_e4_B_synth.csv"; cases(2).winCsv="fig_b_win.csv";
cases(3).g = "C"; cases(3).gtName = "20240723_停车检测_sheet2_e4_C_synth.csv"; cases(3).winCsv="fig_c_win.csv";
cases(4).g = "D"; cases(4).gtName = "20240723_停车检测_sheet1_clean.csv";      cases(4).winCsv="fig_d_win.csv";

for i = 1:numel(cases)
    g = cases(i).g;
    caseName = g + "类";

    winPath = fullfile(winCsvDir, cases(i).winCsv);
    if exist(winPath,'file') ~= 2
        winPath = fullfile(thisDir, cases(i).winCsv);
    end
    assert(exist(winPath,'file')==2, "找不到窗口文件: %s", cases(i).winCsv);

    % ---- load wave window ----
    data = load_wave_window(winPath, cfg0.fs);

    % ---- 获取该 Case 特有的调优参数 ----
    [cfg_case, post_case] = apply_case_params(cfg0, post0, g);

    % ---- 1. 运算（使用 Case 参数 cfg_case） ----
    out = ch4_run_parking_fsm(data, cfg_case);

    % ---- 2. 后处理（使用 Case 参数 cfg_case） ----
    pred_k = ch4_pred_postprocess(out.pred_k, cfg_case.fs, post_case.Tmin_sec, post_case.gap_merge_sec);

    % ---- GT -> local idx ----
    gt_f = GT(GT.file == string(cases(i).gtName), :);
    gt_idx = ch4_gt_k_to_idx(gt_f, data.k(1));
    gt_idx = clip_to_window(gt_idx, data.n);

    % ---- 3. 绘图（传入 cfg_case 算轨迹，传入 cfg0 画基准线） ----
    figPdf = fullfile(outDir, caseName + ".pdf");
    plot_case_one_thesis(data, out, pred_k, gt_idx, figPdf, caseName, cfg_case, cfg0, g);

    fprintf("[%s] 逻辑/轨迹: %s类参数, 阈值虚线/标注/坐标轴: 强制统一对齐 -> %s\n", caseName, g, figPdf);
end
end

%% ===================== 辅助函数 =====================
function [cfg, post] = apply_case_params(cfgIn, postIn, g)
cfg = cfgIn; post = postIn;
g = upper(string(g));
switch g
    case "A"
        % keep GLOBAL
    case "B"
        cfg.pk.dist_th = 25;   % B类放宽门控
    case "C"
        cfg.pk.D_free = 30;    % C类放宽判据
    case "D"
        cfg.pk.D_free = 65;    % D类放宽判据
    otherwise
end
end

function data = load_wave_window(csvPath, fsDefault)
T = readtable(csvPath, "VariableNamingRule","preserve");
v = lower(string(T.Properties.VariableNames));
t = double(T{:, find(v=="t",1)}); t = t(:);
if all(ismember(["x","y","z"], v))
    bx = double(T{:, find(v=="x",1)}); by = double(T{:, find(v=="y",1)}); bz = double(T{:, find(v=="z",1)});
elseif all(ismember(["bx","by","bz"], v))
    bx = double(T{:, find(v=="bx",1)}); by = double(T{:, find(v=="by",1)}); bz = double(T{:, find(v=="bz",1)});
else
    error("窗口CSV缺少坐标轴数据");
end
B = [bx(:), by(:), bz(:)];
fs = fsDefault;
if numel(t) >= 3
    dt = diff(t); fs_est = 1/median(dt);
    if isfinite(fs_est) && fs_est > 1, fs = round(fs_est); end
end
if any(v=="k"), k = double(T{:, find(v=="k",1)}); else k = round(t * fs); end
data = struct('t',t,'k',k(:),'B',B,'n',size(B,1),'fs',fs);
end

function seg2 = clip_to_window(seg, n)
seg2 = zeros(0,2); if isempty(seg), return; end
seg = round(seg);
for i = 1:size(seg,1)
    a = max(1,seg(i,1)); b = min(n,seg(i,2));
    if b >= a, seg2(end+1,:) = [a b]; end
end
end

%% ===================== 绘图函数 (界面显示逻辑) =====================
function plot_case_one_thesis(data, out, pred_k, gt_idx, figPdf, figTitle, cfgCase, cfgGlobal, g)
t = data.t(:); B = data.B; n = data.n; fs = cfgCase.fs;

% 1. 计算 D(t) 轨迹：使用 Case 参数 (cfgCase) 保证逻辑正确
stable = get_stable_vec(out, n);
[S_pre_tr, updLimited] = build_Spre_trace(data, out, pred_k, cfgCase);
D = vecnorm(B - S_pre_tr, 2, 2);

% 2. 计算逻辑棒图：使用 Case 参数 (cfgCase) 保证内部逻辑与运算一致
distSeries = event_value_series(n, out, "dist");
stableSeg   = binary_to_segments(stable);
degradeSeg  = eventflag_to_segments(n, out, "used_degrade", round(0.6*fs));
distKeepSeg = event_distkeep_segments(n, out, cfgCase, round(0.6*fs)); % 反映 Case 的 gate
updLimSeg   = binary_to_segments(updLimited);

% --- 提取中心点 (为了画虚线对齐) ---
tC = 0.5*(t(1)+t(end));
if ~isempty(gt_idx)
    lens = gt_idx(:,2)-gt_idx(:,1);
    [~,jj] = max(lens);
    a = max(1,min(n,gt_idx(jj,1))); b = max(1,min(n,gt_idx(jj,2)));
    tC = 0.5*(t(a)+t(b));
end

fig = figure('Visible','off','Color','w', 'Position',[80 80 1200 900]);
tl = tiledlayout(fig, 4, 1, 'Padding','compact', 'TileSpacing','compact');

% ==================== Row 1: ΔB ====================
ax1 = nexttile(tl,1); hold(ax1,'on'); box(ax1,'on'); grid(ax1,'on');
k_ref = 1:min(n, max(1, round(2*fs))); S_ref = mean(B(k_ref,:), 1);
dB = B - S_ref;
p1 = plot(ax1, t, dB(:,1), 'LineWidth',1.2);
p2 = plot(ax1, t, dB(:,2), 'LineWidth',1.2);
p3 = plot(ax1, t, dB(:,3), 'LineWidth',1.2);
yline(ax1, 0, 'r--', 'LineWidth',1.0, 'HandleVisibility','off');
xline(ax1, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');

ylabel(ax1, 'ΔB / nT'); 
title(ax1, figTitle, 'Interpreter','none');
lg = legend(ax1,[p1 p2 p3],{'ΔB_x','ΔB_y','ΔB_z'},'Location','northeast');
lg.Box='off'; lg.AutoUpdate='off';

% 强制对齐 Row 1 坐标轴
ylim(ax1, [-200, 600]); 
yticks(ax1, -200:200:600);

shade(ax1, t, gt_idx, [0.86 0.86 0.86], 0.10);
shade(ax1, t, pred_k, [0.80 0.90 1.00], 0.08);


% ==================== Row 2: D(t) 与 阈值 ====================
ax2 = nexttile(tl,2); hold(ax2,'on'); box(ax2,'on'); grid(ax2,'on');
xline(ax2, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');

% --- 左侧轴：D(t) 轨迹与 GLOBAL 阈值线 ---
yyaxis(ax2,'left');
plot(ax2, t, D, 'LineWidth',1.2); 
ylabel(ax2, 'D(t) / nT');

% 强制对齐左侧坐标轴
ylim(ax2, [0, 600]); 
yticks(ax2, 0:200:600);

if isfield(cfgGlobal.pk,'D_th'),   yline(ax2, cfgGlobal.pk.D_th, '--', 'Color',[0.4 0.4 0.4], 'LineWidth',1.0); end
if isfield(cfgGlobal.pk,'D_free'), yline(ax2, cfgGlobal.pk.D_free, ':', 'Color',[0.4 0.4 0.4], 'LineWidth',1.0); end

% --- 右侧轴：dist 散点与 GLOBAL 阈值线 ---
yyaxis(ax2,'right');
idx = find(isfinite(distSeries));
if ~isempty(idx), plot(ax2, t(idx), distSeries(idx), 'o', 'MarkerSize',4, 'Color', [0.85 0.33 0.1]); end
ylabel(ax2, 'dist（事件点）');

% 强制对齐右侧坐标轴（设为固定50）
ylim(ax2, [0, 50]); 
yticks(ax2, 0:10:50);

if isfield(cfgGlobal.pk,'dist_th'), yline(ax2, cfgGlobal.pk.dist_th, '--', 'Color',[0.8 0.4 0.4], 'LineWidth',1.0); end

% --- 右上角标注：强制显示 GLOBAL 参数 ---
yyaxis(ax2,'left');
info = {};
if isfield(cfgGlobal.pk,'D_th'), info{end+1} = sprintf('D_{th}=%.1f', cfgGlobal.pk.D_th); end
if isfield(cfgGlobal.pk,'D_free'), info{end+1} = sprintf('D_{free}=%.1f', cfgGlobal.pk.D_free); end
if isfield(cfgGlobal.pk,'dist_th'), info{end+1} = sprintf('dist_{th}=%.1f', cfgGlobal.pk.dist_th); end
text(ax2, 0.985, 0.92, strjoin(info, newline), 'Units','normalized', 'HorizontalAlignment','right', ...
    'VerticalAlignment','top','BackgroundColor','w','Margin',3, 'Clipping','off');

shade(ax2, t, gt_idx, [0.86 0.86 0.86], 0.08);
shade(ax2, t, pred_k, [0.80 0.90 1.00], 0.06);


% ==================== Row 3: 内部逻辑 ====================
ax3 = nexttile(tl,3); hold(ax3,'on'); box(ax3,'on'); grid(ax3,'on');
xlim(ax3,[t(1) t(end)]); ylim(ax3,[0 1]);
xline(ax3, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');

bars(ax3,t, stableSeg,   0.78,0.95,[0.70 0.90 0.70],0.85);
bars(ax3,t, degradeSeg,  0.56,0.72,[1.00 0.86 0.65],0.85);
bars(ax3,t, distKeepSeg, 0.34,0.50,[0.80 0.90 1.00],0.85);
bars(ax3,t, updLimSeg,   0.12,0.28,[1.00 0.75 0.75],0.85);
yticks(ax3,[0.20 0.42 0.64 0.865]);
yticklabels(ax3,{'upd\_limit','dist\_gate','degrade','stable'});
ylabel(ax3,'内部逻辑');


% ==================== Row 4: 结果对比 ====================
ax4 = nexttile(tl,4); hold(ax4,'on'); box(ax4,'on'); grid(ax4,'on');
xlim(ax4,[t(1) t(end)]); ylim(ax4,[0 1]);
xline(ax4, tC, ':', 'LineWidth',1.0, 'HandleVisibility','off');

bars(ax4,t, pred_k, 0.10,0.40,[0.80 0.90 1.00],0.85);
bars(ax4,t, gt_idx,  0.60,0.90,[0.86 0.86 0.86],0.85);
yticks(ax4,[0.25 0.75]); yticklabels(ax4,{'Pred','GT'});
xlabel(ax4,'时间 / s');

linkaxes([ax1 ax2 ax3 ax4],'x');
apply_style(fig);
export_fig(fig, figPdf);
close(fig);
end

%% ===================== 核心支撑函数 =====================
function stable = get_stable_vec(out, n)
stable = zeros(n,1);
if isfield(out,'st') && isfield(out.st,'stableState')
    v = double(out.st.stableState(:));
    stable(1:min(n,numel(v))) = v(1:min(n,numel(v)));
end
end

function [S_pre_tr, updLimited] = build_Spre_trace(data, out, pred_k, cfg)
B=data.B; n=data.n; stable=get_stable_vec(out,n);
occ=false(n,1);
if ~isempty(pred_k)
    for i=1:size(pred_k,1)
        a=max(1,round(pred_k(i,1))); b=min(n,round(pred_k(i,2)));
        if b>=a, occ(a:b)=true; end
    end
end
meanVec=[]; if isfield(out,'st') && isfield(out.st,'meanVec'), meanVec=out.st.meanVec; end
k0=find(stable,1,'first');
if ~isempty(k0) && ~isempty(meanVec) && k0<=size(meanVec,1), S_pre=meanVec(k0,:); else S_pre=B(1,:); end
alpha=cfg.ref.alpha_free;
useGate=isfield(cfg,'v') && isfield(cfg.v,'use_update_gate') && cfg.v.use_update_gate && isfield(cfg.ref,'D_upd');
S_pre_tr=zeros(n,3); updLimited=zeros(n,1);
for k=1:n
    S_pre_tr(k,:)=S_pre;
    if occ(k), continue; end
    if stable(k)<=0.5, continue; end
    if ~isempty(meanVec) && k<=size(meanVec,1), S_cand=meanVec(k,:); 
    else L=max(1,round(0.5*cfg.fs)); a=max(1,k-L+1); S_cand=mean(B(a:k,:),1); end
    d=S_cand-S_pre; nd=norm(d,2);
    if ~useGate || nd<=cfg.ref.D_upd, S_pre=(1-alpha)*S_pre+alpha*S_cand; 
    else updLimited(k)=1; S_pre=S_pre+alpha*(cfg.ref.D_upd/max(nd,eps))*d; end
end
end

function segs = binary_to_segments(sig)
sig = sig(:) > 0.5; d = diff([false; sig; false]);
st = find(d==1); ed = find(d==-1) - 1; segs = [st ed];
end

function segs = eventflag_to_segments(n, out, fieldName, halfWin)
segs=zeros(0,2); if ~isfield(out,'events')||isempty(out.events), return; end
if ~isfield(out,'dbg')||~isfield(out.dbg,fieldName), return; end
flag=out.dbg.(fieldName); mmax=min(numel(out.events),numel(flag));
for m=1:mmax
    if ~flag(m), continue; end
    k=round(out.events(m).k_out); a=max(1,k-halfWin); b=min(n,k+halfWin);
    segs(end+1,:)=[a b];
end
end

function segs = event_distkeep_segments(n, out, cfg, halfWin)
segs=zeros(0,2); if ~isfield(out,'events')||isempty(out.events), return; end
if ~isfield(out,'dbg')||~isfield(out.dbg,'dist'), return; end
dist=out.dbg.dist(:); mmax=min(numel(out.events),numel(dist));
th = 4.0; if isfield(cfg,'pk') && isfield(cfg.pk,'dist_th'), th=cfg.pk.dist_th; end
for m=1:mmax
    if ~isfinite(dist(m)) || dist(m)>=th, continue; end
    k=round(out.events(m).k_out); a=max(1,k-halfWin); b=min(n,k+halfWin);
    segs(end+1,:)=[a b];
end
end

function vSeries = event_value_series(n, out, which)
vSeries = nan(n,1); if ~isfield(out,'events')||isempty(out.events), return; end
if ~isfield(out,'dbg')||~isfield(out.dbg,which), return; end
v = out.dbg.(which)(:); mmax=min(numel(out.events),numel(v));
for m=1:mmax
    k=round(out.events(m).k_out); if k>=1 && k<=n, vSeries(k)=v(m); end
end
end

function shade(ax, t, segs, faceColor, alpha)
if isempty(segs), return; end
yyaxis(ax,'left'); yl = ylim(ax);
for i=1:size(segs,1)
    a=max(1,segs(i,1)); b=min(numel(t),segs(i,2)); if b<=a, continue; end
    patch(ax,[t(a) t(b) t(b) t(a)],[yl(1) yl(1) yl(2) yl(2)],faceColor,'FaceAlpha',alpha,'EdgeColor','none','HandleVisibility','off','HitTest','off');
end
end

function bars(ax, t, segs, y0, y1, faceColor, alpha)
if isempty(segs), return; end
for i=1:size(segs,1)
    a=max(1,segs(i,1)); b=min(numel(t),segs(i,2)); if b<=a, continue; end
    patch(ax,[t(a) t(b) t(b) t(a)],[y0 y0 y1 y1],faceColor,'FaceAlpha',alpha,'EdgeColor','none','HandleVisibility','off','HitTest','off');
end
end

function apply_style(fig)
set(fig,'Color','w'); axs=findall(fig,'Type','axes');
for i=1:numel(axs)
    ax=axs(i); ax.Box='on'; ax.LineWidth=0.8; ax.FontName='Microsoft YaHei'; ax.FontSize=11; ax.GridAlpha=0.15; ax.MinorGridAlpha=0.08;
end
lgs=findall(fig,'Type','legend');
for i=1:numel(lgs), lg=lgs(i); lg.Box='off'; lg.FontName='Microsoft YaHei'; lg.FontSize=10; end
end

function export_fig(fig, outPath)
[p,name,ext]=fileparts(char(outPath));
if isempty(ext), ext='.pdf'; outPath=fullfile(p,[name ext]); end
if ~exist(p,'dir'); mkdir(p); end
try exportgraphics(fig, outPath, 'ContentType','vector'); catch, print(fig, outPath, '-dpdf', '-painters'); end
pngPath=fullfile(p,[name '.png']);
try exportgraphics(fig, pngPath, 'Resolution', 300); catch, print(fig, pngPath, '-dpng', '-r300'); end
end