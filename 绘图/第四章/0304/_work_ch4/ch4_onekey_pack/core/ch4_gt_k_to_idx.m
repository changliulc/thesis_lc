% function gt_idx = ch4_gt_k_to_idx(gt_k_abs, data_k0)
% %CH4_GT_K_TO_IDX  Convert absolute k (from groundtruth) to MATLAB indices (1-based).
% %   index = (k - k0) + 1
% %
% % Inputs:
% %   gt_k_abs: Nx2 [k_star_in, k_star_out] in absolute k domain
% %   data_k0 : the first k value in the corresponding CSV (absolute k)
% %
% % Output:
% %   gt_idx : Nx2 indices aligned to MATLAB vectors (1-based)
% gt_idx = gt_k_abs;
% gt_idx(:,1) = gt_k_abs(:,1) - data_k0 + 1;
% gt_idx(:,2) = gt_k_abs(:,2) - data_k0 + 1;
% end
function gt_idx = ch4_gt_k_to_idx(gt_f, data_k0)
%CH4_GT_K_TO_IDX Convert GT absolute k to local sample index
% gt_f: table rows for one file (contains k_star_in/k_star_out or t_star_in_sec/t_star_out_sec)
% data_k0: first sample absolute k in this csv (usually 0 or 1)
%
% output gt_idx: [k_in_idx, k_out_idx] in 1-based local indexing

    if isempty(gt_f)
        gt_idx = zeros(0,2);
        return;
    end

    % -------- 1) pick columns safely --------
    if istable(gt_f)
        vars = string(gt_f.Properties.VariableNames);

        % prefer absolute k columns
        if any(vars=="k_star_in") && any(vars=="k_star_out")
            k_abs = gt_f{:, ["k_star_in","k_star_out"]};  % NOTE: {} -> array
        elseif any(vars=="k_in") && any(vars=="k_out")
            k_abs = gt_f{:, ["k_in","k_out"]};
        elseif any(vars=="t_star_in_sec") && any(vars=="t_star_out_sec")
            % if only time exists, try to use it (need fs; fall back to rounding seconds*50)
            t_abs = gt_f{:, ["t_star_in_sec","t_star_out_sec"]};
            t_abs = toDouble(t_abs);
            fs = 50; % default, consistent with your chapter
            k_abs = round(t_abs * fs);
        else
            error("GT table does not contain k_star_in/k_star_out (or t_star_in_sec/t_star_out_sec). Please check column names.");
        end
    else
        % allow numeric input directly
        k_abs = gt_f;
    end

    % -------- 2) force numeric --------
    k_abs = toDouble(k_abs);

    % -------- 3) abs-k -> local 1-based index --------
    gt_idx = round(k_abs - double(data_k0) + 1);

end

% ================= helper =================
function x = toDouble(x)
    % table{} may still return cell/string; normalize to double
    if iscell(x)
        x = cellfun(@(v) str2double(string(v)), x);
    elseif isstring(x)
        x = str2double(x);
    else
        x = double(x);
    end
end
