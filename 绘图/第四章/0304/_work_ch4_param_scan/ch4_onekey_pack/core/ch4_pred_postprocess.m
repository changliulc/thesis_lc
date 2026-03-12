function pred2 = ch4_pred_postprocess(pred, fs, Tmin_sec, gap_merge_sec)
%CH4_PRED_POSTPROCESS  Script-level postprocess for predicted occupancy intervals.
%   1) Remove intervals shorter than Tmin_sec.
%   2) Optionally merge adjacent intervals if gap <= gap_merge_sec.
%
% pred: Nx2 [k_in, k_out] in MATLAB indices (1-based)
if nargin < 3 || isempty(Tmin_sec), Tmin_sec = 0; end
if nargin < 4 || isempty(gap_merge_sec), gap_merge_sec = 0; end

pred2 = pred;
if isempty(pred2)
    return;
end

% 1) remove short
dur_sec = (pred2(:,2) - pred2(:,1)) / fs;
pred2 = pred2(dur_sec >= Tmin_sec, :);

if isempty(pred2) || gap_merge_sec <= 0
    return;
end

% 2) merge small gaps
pred2 = sortrows(pred2, 1);
gap_k = round(gap_merge_sec * fs);

merged = pred2(1,:);
for i = 2:size(pred2,1)
    if pred2(i,1) - merged(end,2) <= gap_k
        merged(end,2) = max(merged(end,2), pred2(i,2));
    else
        merged = [merged; pred2(i,:)]; %#ok<AGROW>
    end
end
pred2 = merged;
end
