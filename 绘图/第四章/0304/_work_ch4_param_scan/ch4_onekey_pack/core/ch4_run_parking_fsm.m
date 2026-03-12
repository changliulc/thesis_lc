function out = ch4_run_parking_fsm(data, cfg)
%CH4_RUN_PARKING_FSM Run chapter-4 parking/occupancy FSM

B = data.B;
n = data.n;

pr = ch4_pr_vehicle(B, cfg);
events = ch4_detect_events(pr, cfg);
st = ch4_stability(B, cfg);

seekN = round(cfg.pk.T_seek_sec * cfg.fs);

FREE = 0; OCC = 1;
state = FREE;

S_pre = [];
S_post = [];
dB = [];

c_park = 0;
c_free = 0;
% candidate buffer for consecutive parking-confirm (stable_found branch)


pred_k = [];
conf_k = [];

dbg = struct();
dbg.event_k_in  = zeros(numel(events),1);
dbg.event_k_out = zeros(numel(events),1);
dbg.stable_found = false(numel(events),1);
dbg.drift_mag = nan(numel(events),1);
dbg.back2env = nan(numel(events),1);
dbg.dist = nan(numel(events),1);
dbg.used_degrade = false(numel(events),1);

k0 = find(st.stableState, 1, "first");
if ~isempty(k0)
    S_pre = st.meanVec(k0,:);
else
    S_pre = B(1,:);
end

open_k_in = NaN;
open_k_conf_in = NaN;

for m = 1:numel(events)
    k_out = events(m).k_out;
    dbg.event_k_in(m) = events(m).k_in;
    dbg.event_k_out(m) = k_out;

    % Update S_pre in FREE
    if state == FREE && cfg.ref.enable
        k_last = find(st.stableState(1:k_out), 1, "last");
        if ~isempty(k_last)
            S_cand = st.meanVec(k_last,:);
           alpha = cfg.ref.alpha_free;
d = S_cand - S_pre;
nd = norm(d, 2);

if ~cfg.v.use_update_gate
    S_pre = (1 - alpha) * S_pre + alpha * S_cand;
else
    if nd <= cfg.ref.D_upd
        % 正常 EMA 更新
        S_pre = (1 - alpha) * S_pre + alpha * S_cand;
    else
        % 限幅更新：朝 S_cand 方向走，但单次步长受 D_upd 限制，避免大跳变
        S_pre = S_pre + alpha * (cfg.ref.D_upd / nd) * d;
    end
end

        end
    end

    % stable after event end
    k_seek_end = min(n, k_out + seekN);
    k_st = find(st.stableState(k_out:k_seek_end), 1, "first");
    if ~isempty(k_st)
        k_st = k_out + k_st - 1;
        S_new = st.meanVec(k_st,:);
        dbg.stable_found(m) = true;
    else
        S_new = [];
        dbg.stable_found(m) = false;
    end

    if state == FREE
        if dbg.stable_found(m)
            dB_cand = S_new - S_pre;
            drift_mag = norm(dB_cand, 2);
            dbg.drift_mag(m) = drift_mag;

            % ===== 连续证据停车确认（用于 stable_found 分支）=====
% persistent cand_k_in cand_k_conf_in cand_S_post cand_dB
% if isempty(cand_k_in)
%     cand_k_in = NaN; cand_k_conf_in = NaN;
%     cand_S_post = []; cand_dB = [];
% end

if drift_mag > cfg.pk.D_th
    % confirm parking (stable_found branch: one-shot)
    state = OCC;
    S_post = S_new;
    dB = dB_cand;

    open_k_in = k_out;
    open_k_conf_in = k_st;

    c_park = 0;
    c_free = 0;
end


        else
            if cfg.dg.enable && cfg.v.use_degrade
                dbg.used_degrade(m) = true;

                if (k_seek_end - cfg.dg.L_fix + 1) >= 1
                    S_hat = mean(B(k_seek_end - cfg.dg.L_fix + 1 : k_seek_end, :), 1);
                else
                    S_hat = mean(B(1:k_seek_end,:), 1);
                end

                dB_hat = S_hat - S_pre;
                drift_mag = norm(dB_hat, 2);
                dbg.drift_mag(m) = drift_mag;

                if drift_mag > cfg.pk.D_th
                    c_park = min(c_park + 1, cfg.dg.c_th);
                else
                    c_park = 0;
                end

                if c_park >= cfg.dg.c_th
                    state = OCC;
                    S_post = S_hat;
                    dB = dB_hat;

                    open_k_in = k_out;
                    open_k_conf_in = k_seek_end;

                    c_park = 0; c_free = 0;
                end
            end
        end

    else % OCCUPIED
        if dbg.stable_found(m)
            back2env = norm(S_new - S_pre, 2);
            dbg.back2env(m) = back2env;

            if back2env < cfg.pk.D_free
                state = FREE;

                pred_k = [pred_k; open_k_in, k_out]; %#ok<AGROW>
                conf_k = [conf_k; open_k_conf_in, k_st]; %#ok<AGROW>

                S_pre = S_new;

                open_k_in = NaN;
                open_k_conf_in = NaN;
                S_post = [];
                dB = [];
                c_free = 0;

           else
    % ---------- 1) 计算相似性距离 dist ----------
    dist = NaN;
    if cfg.v.use_similarity && ~isempty(dB)
        dist = norm((S_new - S_pre) - dB, 2);
        dbg.dist(m) = dist;
    end

    % ---------- 2) 若仍与占用漂移相似：保持占用，并清零释放计数 ----------
    if ~isnan(dist) && dist < cfg.pk.dist_th
        S_post = (1 - cfg.pk.lambda_occ) * S_post + cfg.pk.lambda_occ * S_new;
        dB = S_post - S_pre;
        c_free = 0;   % 关键：仍占用则清零“释放一致性计数”

    % ---------- 3) 若不相似：累积释放证据，达到 c_th 则释放 ----------
    else
        c_free = min(c_free + 1, cfg.dg.c_th);
        if c_free >= cfg.dg.c_th
            % release confirmed by dissimilarity
            state = FREE;

            pred_k = [pred_k; open_k_in, k_out]; %#ok<AGROW>
            conf_k = [conf_k; open_k_conf_in, k_st]; %#ok<AGROW>

            % 更新环境参考到新的自由稳定点
            S_pre = S_new;

            open_k_in = NaN;
            open_k_conf_in = NaN;
            S_post = [];
            dB = [];
            c_free = 0;
        end
    end
end


        else
            if cfg.dg.enable && cfg.v.use_degrade
                dbg.used_degrade(m) = true;

                if (k_seek_end - cfg.dg.L_fix + 1) >= 1
                    S_hat = mean(B(k_seek_end - cfg.dg.L_fix + 1 : k_seek_end, :), 1);
                else
                    S_hat = mean(B(1:k_seek_end,:), 1);
                end

                back2env = norm(S_hat - S_pre, 2);
                dbg.back2env(m) = back2env;

                if back2env < cfg.pk.D_free
                    c_free = min(c_free + 1, cfg.dg.c_th);
                else
                    c_free = 0;
                end

                if c_free >= cfg.dg.c_th
                    state = FREE;

                    pred_k = [pred_k; open_k_in, k_out]; %#ok<AGROW>
                    conf_k = [conf_k; open_k_conf_in, k_seek_end]; %#ok<AGROW>

                    S_pre = S_hat;
                    open_k_in = NaN;
                    open_k_conf_in = NaN;
                    S_post = [];
                    dB = [];
                    c_free = 0;
                end
            end
        end
    end
    
end

out.pred_k = pred_k;
out.conf_k = conf_k;
out.pr = pr;
out.events = events;
out.st = st;
out.dbg = dbg;

end

