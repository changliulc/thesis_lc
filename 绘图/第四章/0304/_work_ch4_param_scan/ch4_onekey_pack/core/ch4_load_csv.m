function data = ch4_load_csv(csvFile, fs)
%CH4_LOAD_CSV Load clean csv to a unified struct
% Compatible:
%   data = ch4_load_csv(csvFile)        % fs auto infer / default
%   data = ch4_load_csv(csvFile, fs)    % user specified fs

T = readtable(csvFile, "VariableNamingRule","preserve");
vnames = string(T.Properties.VariableNames);

% Required columns: x,y,z
if ~all(ismember(["x","y","z"], vnames))
    error("CSV missing x/y/z: %s", csvFile);
end

% Optional: k
if ~ismember("k", vnames)
    T.k = (0:height(T)-1)';
end

% Optional: t
if ~ismember("t", vnames)
    % if fs not provided, try default 50
    if nargin < 2 || isempty(fs)
        fs = 50;
    end
    T.t = double(T.k) / fs;
else
    % if fs not provided, infer from t
    if nargin < 2 || isempty(fs)
        tt = double(T.t(:));
        if numel(tt) >= 3
            dt = diff(tt);
            fs_est = 1/median(dt);
            if isfinite(fs_est) && fs_est > 1
                fs = fs_est;
            else
                fs = 50;
            end
        else
            fs = 50;
        end
    end
end

data.k = double(T.k(:));
data.t = double(T.t(:));
data.B = [double(T.x), double(T.y), double(T.z)];
data.n = size(data.B,1);
data.file = csvFile;
data.fs = fs;
end
