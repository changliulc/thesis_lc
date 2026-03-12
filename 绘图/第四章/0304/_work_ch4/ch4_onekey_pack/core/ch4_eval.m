% function res = ch4_eval(pred_k, gt_k, fs, iou_th)
% %CH4_EVAL IoU matching + Precision/Recall/F1 + timing stats
% % Robust to empty pred or empty gt.
% 
% if isempty(pred_k), pred_k = zeros(0,2); end
% if isempty(gt_k),   gt_k   = zeros(0,2); end
% 
% Np = size(pred_k,1);
% Ng = size(gt_k,1);
% 
% % ===== handle empty cases first (avoid sortrows error) =====
% if Np == 0 && Ng == 0
%     TP = 0; FP = 0; FN = 0;
%     match = zeros(0,3);
% 
% elseif Np == 0 && Ng > 0
%     TP = 0; FP = 0; FN = Ng;
%     match = zeros(0,3);
% 
% elseif Np > 0 && Ng == 0
%     TP = 0; FP = Np; FN = 0;
%     match = zeros(0,3);
% 
% else
%     % ===== IoU matrix =====
%     IoU = zeros(Np, Ng);
%     for i = 1:Np
%         for j = 1:Ng
%             inter = max(0, min(pred_k(i,2), gt_k(j,2)) - max(pred_k(i,1), gt_k(j,1)));
%             uni   = max(pred_k(i,2), gt_k(j,2)) - min(pred_k(i,1), gt_k(j,1));
%             if uni > 0
%                 IoU(i,j) = inter / uni;
%             end
%         end
%     end
% 
%     % ===== greedy match by IoU =====
%     pairs = zeros(Np*Ng, 3);
%     t = 0;
%     for i = 1:Np
%         for j = 1:Ng
%             t = t + 1;
%             pairs(t,:) = [i, j, IoU(i,j)];
%         end
%     end
% 
%     pairs = sortrows(pairs, -3);
% 
%     matched_p = false(Np,1);
%     matched_g = false(Ng,1);
%     match = zeros(0,3);
% 
%     for r = 1:size(pairs,1)
%         i = pairs(r,1); j = pairs(r,2); v = pairs(r,3);
%         if v < iou_th
%             break;
%         end
%         if ~matched_p(i) && ~matched_g(j)
%             matched_p(i) = true;
%             matched_g(j) = true;
%             match(end+1,:) = [i, j, v]; %#ok<AGROW>
%         end
%     end
% 
%     TP = size(match,1);
%     FP = sum(~matched_p);
%     FN = sum(~matched_g);
% end
% 
% Precision = TP / max(TP + FP, 1);
% Recall    = TP / max(TP + FN, 1);
% F1        = 2 * Precision * Recall / max(Precision + Recall, eps);
% 
% res.TP = TP; res.FP = FP; res.FN = FN;
% res.Precision = Precision;
% res.Recall = Recall;
% res.F1 = F1;
% 
% % event-level false/miss rate aligned to gt count
% res.Rf = FP / max(Ng, 1);
% res.Rm = FN / max(Ng, 1);
% 
% res.match = match;
% 
% res.pred_k = pred_k;
% res.gt_k = gt_k;
% res.fs = fs;
% end


% function res = ch4_eval(pred_k, gt_k, iou_th)
% %CH4_EVAL Greedy IoU matching for interval detection.
% %
% %   res = ch4_eval(pred_k, gt_k, iou_th)
% %
% % Inputs
% %   pred_k : Np x 2, predicted intervals in local 1-based sample index
% %   gt_k   : Ng x 2, ground-truth intervals in local 1-based sample index
% %   iou_th : scalar, IoU threshold (default 0.5)
% %
% % Output (struct)
% %   TP, FP, FN, Precision, Recall, F1, Rf, Rm, match
% %
% % Notes
% %   - Handles empty pred/gt safely.
% %   - Uses inclusive interval length ( +1 ) consistent with sample indexing.
% 
%     if nargin < 3 || isempty(iou_th)
%         iou_th = 0.5;
%     end
% 
%     if isempty(pred_k)
%         pred_k = zeros(0,2);
%     end
%     if isempty(gt_k)
%         gt_k = zeros(0,2);
%     end
% 
%     pred_k = double(pred_k);
%     gt_k   = double(gt_k);
% 
%     % Ensure k_in <= k_out
%     if ~isempty(pred_k)
%         pred_k = sort(pred_k, 2);
%     end
%     if ~isempty(gt_k)
%         gt_k = sort(gt_k, 2);
%     end
% 
%     Np = size(pred_k,1);
%     Ng = size(gt_k,1);
% 
%     % Build candidate pairs
%     if Np == 0 && Ng == 0
%         matches = zeros(0,3);
%         TP = 0; FP = 0; FN = 0;
%     elseif Np == 0
%         matches = zeros(0,3);
%         TP = 0; FP = 0; FN = Ng;
%     elseif Ng == 0
%         matches = zeros(0,3);
%         TP = 0; FP = Np; FN = 0;
%     else
%         pairs = zeros(Np*Ng, 3);
%         idx = 0;
%         for i = 1:Np
%             a = pred_k(i,:);
%             for j = 1:Ng
%                 b = gt_k(j,:);
%                 idx = idx + 1;
%                 pairs(idx,:) = [i, j, interval_iou(a,b)];
%             end
%         end
%         pairs = pairs(1:idx,:);
% 
%         % Sort by IoU descending
%         pairs = sortrows(pairs, -3);
% 
%         pred_used = false(Np,1);
%         gt_used   = false(Ng,1);
%         matches = zeros(0,3);
% 
%         for r = 1:size(pairs,1)
%             i = pairs(r,1);
%             j = pairs(r,2);
%             v = pairs(r,3);
% 
%             if v < iou_th
%                 break;
%             end
%             if pred_used(i) || gt_used(j)
%                 continue;
%             end
% 
%             pred_used(i) = true;
%             gt_used(j) = true;
%             matches = [matches; i, j, v]; %#ok<AGROW>
%         end
% 
%         TP = size(matches,1);
%         FP = sum(~pred_used);
%         FN = sum(~gt_used);
%     end
% 
%     Precision = TP / max(TP + FP, 1);
%     Recall    = TP / max(TP + FN, 1);
%     F1        = 2 * Precision * Recall / max(Precision + Recall, eps);
% 
%     % Event-level rates (%), normalized by number of GT events
%     Rf = FP / max(Ng,1) * 100;
%     Rm = FN / max(Ng,1) * 100;
% 
%     res = struct();
%     res.TP = TP;
%     res.FP = FP;
%     res.FN = FN;
%     res.Precision = Precision;
%     res.Recall = Recall;
%     res.F1 = F1;
%     res.Rf = Rf;
%     res.Rm = Rm;
%     res.match = matches;
%     res.pred_k = pred_k;
%     res.gt_k = gt_k;
% end
% 
% function iou = interval_iou(a,b)
% % a,b: [k_in, k_out] inclusive
%     inter = max(0, min(a(2), b(2)) - max(a(1), b(1)) + 1);
%     uni = (a(2) - a(1) + 1) + (b(2) - b(1) + 1) - inter;
%     if uni <= 0
%         iou = 0;
%     else
%         iou = inter / uni;
%     end
% end


function res = ch4_eval(pred_k, gt_k, iou_th)
%CH4_EVAL Greedy IoU matching for interval detection.
%
%   res = ch4_eval(pred_k, gt_k, iou_th)
%
% Inputs
%   pred_k : Np x 2, predicted intervals in local 1-based sample index
%   gt_k   : Ng x 2, ground-truth intervals in local 1-based sample index
%   iou_th : scalar, IoU threshold (default 0.5)
%
% Output (struct)
%   TP, FP, FN, Precision, Recall, F1, Rf, Rm, match
%
% Notes
%   - Handles empty pred/gt safely.
%   - Uses inclusive interval length ( +1 ) consistent with sample indexing.

    if nargin < 3 || isempty(iou_th)
        iou_th = 0.5;
    end

    if isempty(pred_k)
        pred_k = zeros(0,2);
    end
    if isempty(gt_k)
        gt_k = zeros(0,2);
    end

    pred_k = double(pred_k);
    gt_k   = double(gt_k);

    % Ensure k_in <= k_out
    if ~isempty(pred_k)
        pred_k = sort(pred_k, 2);
    end
    if ~isempty(gt_k)
        gt_k = sort(gt_k, 2);
    end

    Np = size(pred_k,1);
    Ng = size(gt_k,1);

    % Build candidate pairs
    if Np == 0 && Ng == 0
        matches = zeros(0,3);
        TP = 0; FP = 0; FN = 0;
    elseif Np == 0
        matches = zeros(0,3);
        TP = 0; FP = 0; FN = Ng;
    elseif Ng == 0
        matches = zeros(0,3);
        TP = 0; FP = Np; FN = 0;
    else
        pairs = zeros(Np*Ng, 3);
        idx = 0;
        for i = 1:Np
            a = pred_k(i,:);
            for j = 1:Ng
                b = gt_k(j,:);
                idx = idx + 1;
                pairs(idx,:) = [i, j, interval_iou(a,b)];
            end
        end
        pairs = pairs(1:idx,:);

        % Sort by IoU descending
        pairs = sortrows(pairs, -3);

        pred_used = false(Np,1);
        gt_used   = false(Ng,1);
        matches = zeros(0,3);

        for r = 1:size(pairs,1)
            i = pairs(r,1);
            j = pairs(r,2);
            v = pairs(r,3);

            if v < iou_th
                break;
            end
            if pred_used(i) || gt_used(j)
                continue;
            end

            pred_used(i) = true;
            gt_used(j) = true;
            matches = [matches; i, j, v]; %#ok<AGROW>
        end

        TP = size(matches,1);
        FP = sum(~pred_used);
        FN = sum(~gt_used);
    end

    Precision = TP / max(TP + FP, 1);
    Recall    = TP / max(TP + FN, 1);
    F1        = 2 * Precision * Recall / max(Precision + Recall, eps);

    % Event-level rates (%), normalized by number of GT events
    Rf = FP / max(Ng,1) * 100;
    Rm = FN / max(Ng,1) * 100;

    res = struct();
    res.TP = TP;
    res.FP = FP;
    res.FN = FN;
    res.Precision = Precision;
    res.Recall = Recall;
    % Backward-compatible aliases (older scripts expect P/R)
    res.P = Precision;
    res.R = Recall;
    res.F1 = F1;
    res.Rf = Rf;
    res.Rm = Rm;
    res.match = matches;
    res.pred_k = pred_k;
    res.gt_k = gt_k;
end

function iou = interval_iou(a,b)
% a,b: [k_in, k_out] inclusive
    inter = max(0, min(a(2), b(2)) - max(a(1), b(1)) + 1);
    uni = (a(2) - a(1) + 1) + (b(2) - b(1) + 1) - inter;
    if uni <= 0
        iou = 0;
    else
        iou = inter / uni;
    end
end
