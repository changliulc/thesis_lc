% function gt2 = ch4_append_synth_gt_all_events(gt, synthDir)
% %CH4_APPEND_SYNTH_GT_ALL_EVENTS Duplicate all base events to each synth file
% % 适用场景：synth_out 保留了整段录制（包含多个停车事件）
% %
% % 做法：
% % 1) base = 4_16_停车检测_clean.csv 的全部事件真值行
% % 2) 对 synthDir 下每个 *_synth.csv：
% %    - 删除 gt2 中该 synth 文件已有行（避免重复）
% %    - 复制 base 全部行，覆盖 file/dataset/scenario_group
% %
% gt2 = gt;
% 
% if nargin < 2 || isempty(synthDir)
%     synthDir = ".";
% end
% 
% vars = string(gt2.Properties.VariableNames);
% if ~ismember("file", vars)
%     error("groundtruth table must contain column: file");
% end
% 
% % --- 1) 取 base（全事件） ---
% if ismember("dataset", vars)
%     base = gt2(string(gt2.dataset)=="4_16_停车检测" & string(gt2.file)=="4_16_停车检测_clean.csv", :);
% else
%     base = gt2(string(gt2.file)=="4_16_停车检测_clean.csv", :);
% end
% 
% if isempty(base)
%     error("Cannot find base rows for 4_16_停车检测_clean.csv in groundtruth.");
% end
% 
% % --- 2) 扫描 synth 文件 ---
% dd = dir(fullfile(synthDir, "*_synth.csv"));
% 
% for i = 1:numel(dd)
%     fname = string(dd(i).name);
% 
%     % 推断分组
%     if contains(fname, "_B_synth")
%         g = "B";
%     elseif contains(fname, "_C_synth")
%         g = "C";
%     elseif contains(fname, "_D_synth")
%         g = "D";
%     else
%         continue;
%     end
% 
%     % --- 删除已有该 synth 文件行（避免重复） ---
%     gt2 = gt2(~(string(gt2.file) == fname), :);
% 
%     % --- 复制 base 并覆盖关键列（必须按行复制赋值） ---
%     r = base;
%     r = set_col_repeat(r, "file", fname);
% 
%     if ismember("dataset", vars)
%         r = set_col_repeat(r, "dataset", erase(fname, ".csv"));
%     end
%     if ismember("scenario_group", vars)
%         r = set_col_repeat(r, "scenario_group", g);
%     end
%     if ismember("notes", vars)
%         r = set_col_repeat(r, "notes", "synth_all_events");
%     end
% 
%     gt2 = [gt2; r]; %#ok<AGROW>
% end
% 
% end
% 
% % ===== helper: set a table column by repeating a scalar to match height =====
% function T = set_col_repeat(T, colName, val)
% if height(T) == 0
%     return;
% end
% colName = string(colName);
% v = string(T.Properties.VariableNames);
% if ~ismember(colName, v)
%     return;
% end
% 
% n = height(T);
% col = T.(colName);
% 
% if isstring(col)
%     T.(colName) = repmat(string(val), n, 1);
% elseif iscell(col)
%     T.(colName) = repmat({char(val)}, n, 1);
% elseif iscategorical(col)
%     T.(colName) = categorical(repmat(string(val), n, 1));
% elseif isnumeric(col)
%     x = str2double(string(val));
%     if ~isnan(x)
%         T.(colName) = repmat(x, n, 1);
%     else
%         % fallback：转 string（尽量不触发）
%         T.(colName) = repmat(string(val), n, 1);
%     end
% else
%     % 最后兜底：尝试 string
%     try
%         T.(colName) = repmat(string(val), n, 1);
%     catch
%         T.(colName) = repmat({char(val)}, n, 1);
%     end
% end
% end



function gt2 = ch4_append_synth_gt_all_events(gt, synthDir)
%CH4_APPEND_SYNTH_GT_ALL_EVENTS
% 对 synthDir 下每个 *_synth.csv：
%   - 从文件名解析 baseStem
%   - 在 GT 中优先找 baseStem_clean_crop.csv；找不到则找 baseStem_clean.csv
%   - 把该 base 的“全事件 GT 行”复制给该 synth 文件（覆盖 file/dataset/scenario_group/notes）

gt2 = gt;

if nargin < 2 || isempty(synthDir)
    synthDir = ".";
end

vars = string(gt2.Properties.VariableNames);
needCols = ["file","k_star_in","k_star_out"]; % scenario_group/dataset/notes 可选
for c = needCols
    if ~ismember(c, vars)
        error("GT 缺少必要列：%s", c);
    end
end

% --- scan synth files (non-recursive) ---
dd = dir(fullfile(synthDir, "*_synth.csv"));

% 兜底：防止解压后多一层 synth_out/
if isempty(dd) && exist(fullfile(synthDir, "synth_out"), 'dir') == 7
    synthDir = fullfile(synthDir, "synth_out");
    dd = dir(fullfile(synthDir, "*_synth.csv"));
end

if isempty(dd)
    warning("No *_synth.csv found under: %s", synthDir);
    return;
end

for i = 1:numel(dd)
    fname = string(dd(i).name);

    % group from filename
    if contains(fname, "_B_synth")
        g = "B";
    elseif contains(fname, "_C_synth")
        g = "C";
    elseif contains(fname, "_D_synth")
        g = "D";
    else
        continue;
    end

    % parse baseStem: <baseStem>_e<d>_<G>_synth.csv
    tok = regexp(fname, "^(.*)_e\d+_[BCD]_synth\.csv$", "tokens", "once");
    if isempty(tok)
        warning("Skip synth name not match pattern: %s", fname);
        continue;
    end
    baseStem = string(tok{1});

    % ===== 最关键：自动选择存在的 baseFile（优先 clean_crop，其次 clean）=====
    cand = [baseStem + "_clean_crop.csv", baseStem + "_clean.csv"];
    baseFile = "";
    for k = 1:numel(cand)
        if any(string(gt2.file) == cand(k))
            baseFile = cand(k);
            break;
        end
    end
    if baseFile == ""
        warning("Skip %s: base GT not found for %s (tried clean_crop/clean)", fname, baseStem);
        continue;
    end

    base = gt2(string(gt2.file) == baseFile, :);
    if isempty(base)
        warning("Skip %s: base rows empty for %s", fname, baseFile);
        continue;
    end

    % 删除已有该 synth 文件行（避免重复）
    gt2 = gt2(~(string(gt2.file) == fname), :);

    % 复制 base 并覆盖关键列（用 set_col_repeat 保证类型兼容）
    r = base;
    r = set_col_repeat(r, "file", fname);

    if ismember("dataset", vars)
        r = set_col_repeat(r, "dataset", erase(fname, ".csv"));
    end
    if ismember("scenario_group", vars)
        r = set_col_repeat(r, "scenario_group", g);
    end
    if ismember("notes", vars)
        r = set_col_repeat(r, "notes", "synth_all_events");
    end

    gt2 = [gt2; r]; %#ok<AGROW>
end

end

% ===== helper: set a table column by repeating a scalar to match height =====
function T = set_col_repeat(T, colName, val)
if height(T) == 0
    return;
end
colName = string(colName);
v = string(T.Properties.VariableNames);
if ~ismember(colName, v)
    return;
end

n = height(T);
col = T.(colName);

if isstring(col)
    T.(colName) = repmat(string(val), n, 1);
elseif iscell(col)
    T.(colName) = repmat({char(val)}, n, 1);
elseif iscategorical(col)
    T.(colName) = categorical(repmat(string(val), n, 1));
elseif isnumeric(col)
    x = str2double(string(val));
    if ~isnan(x)
        T.(colName) = repmat(x, n, 1);
    else
        T.(colName) = repmat(string(val), n, 1);
    end
else
    try
        T.(colName) = repmat(string(val), n, 1);
    catch
        T.(colName) = repmat({char(val)}, n, 1);
    end
end
end
