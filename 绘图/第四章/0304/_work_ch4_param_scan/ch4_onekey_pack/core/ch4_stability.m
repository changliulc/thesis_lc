function st = ch4_stability(B, cfg)
%CH4_STABILITY Compute stability indicators and stable-point candidates

n = size(B,1);
L = cfg.st.L;
s = cfg.st.s;

% weights (use first 10 seconds)
n0 = min(n, cfg.fs * 10);
sig = std(B(1:n0,:), 0, 1);
w = [sig(2)*sig(3), sig(1)*sig(3), sig(1)*sig(2)];
if sum(w) == 0
    w = [1,1,1];
end
w = w / sum(w);

meanVec = nan(n,3);
R = nan(n,1);
M = nan(n,1);

for k = L:n
    win = B(k-L+1:k, :);
    meanVec(k,:) = mean(win, 1);
    rvec = max(win,[],1) - min(win,[],1);
    R(k) = w * rvec';
    if (k - s) >= L
        M(k) = w * abs(meanVec(k,:) - meanVec(k-s,:))';
    end
end

if cfg.v.use_mean_diff
    stable0 = (R <= cfg.st.R_th) & (M <= cfg.st.M_th);
else
    stable0 = (R <= cfg.st.R_th);
end

Nst = cfg.st.N_stable;
stableState = false(n,1);
cnt = 0;
for k = 1:n
    if stable0(k)
        cnt = min(cnt + 1, Nst);
    else
        cnt = 0;
    end
    stableState(k) = (cnt == Nst);
end

st.w = w;
st.meanVec = meanVec;
st.R = R;
st.M = M;
st.stableState = stableState;
end
