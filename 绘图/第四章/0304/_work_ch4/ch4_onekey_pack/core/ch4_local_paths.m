function p = ch4_local_paths()
%CH4_LOCAL_PATHS  Path configuration for Chapter-4 one-key experiments.
%
% This version is tailored for the XDU thesis template structure:
%   <THESIS_ROOT>/
%     chapters/
%     images/
%     tables/
%     ch4_onekey_pack/
%
% Data folder convention (recommended):
%   <THESIS_ROOT>/data/zhenzhi/     (clean csv + GT)
%   <THESIS_ROOT>/data/synth_out/   (synth csv)
%
% Fallback conventions also supported:
%   <THESIS_ROOT>/zhenzhi/
%   <THESIS_ROOT>/synth_out/

core_dir = fileparts(mfilename('fullpath'));
pack_dir = fileparts(core_dir);

% Try to locate thesis root by searching upward for the thesis structure.
% This makes the script robust even if the pack is nested under
%   <THESIS_ROOT>/.../ch4_onekey_pack/
thesis_dir = fileparts(pack_dir);
found = false;
cur = thesis_dir;
for k = 1:8
    if exist(fullfile(cur, 'chapters'), 'dir') && exist(fullfile(cur, 'images'), 'dir')
        thesis_dir = cur;
        found = true;
        break;
    end
    parent = fileparts(cur);
    if isempty(parent) || strcmp(parent, cur)
        break;
    end
    cur = parent;
end
if ~found
    % If not found, fall back to pack_dir (standalone usage).
    thesis_dir = pack_dir;
end

p = struct();
p.core   = core_dir;
p.pack   = pack_dir;
p.thesis = thesis_dir;

% ---------- data dir auto-detect ----------
cand_data = { ...
    fullfile(thesis_dir, 'data', 'zhenzhi'), ...
    fullfile(thesis_dir, 'zhenzhi'), ...
    fullfile(pack_dir,   'data', 'zhenzhi'), ...
    fullfile(pack_dir,   'zhenzhi') ...
};
p.root = cand_data{1};
for i = 1:numel(cand_data)
    if exist(cand_data{i}, 'dir')
        p.root = cand_data{i};
        break;
    end
end

cand_syn = { ...
    fullfile(thesis_dir, 'data', 'synth_out'), ...
    fullfile(thesis_dir, 'synth_out'), ...
    fullfile(pack_dir,   'data', 'synth_out'), ...
    fullfile(pack_dir,   'synth_out') ...
};
p.synth = cand_syn{1};
for i = 1:numel(cand_syn)
    if exist(cand_syn{i}, 'dir')
        p.synth = cand_syn{i};
        break;
    end
end

% ---------- GT file ----------
p.gt = fullfile(p.root, 'parking_groundtruth_filled_cleaned.csv');

% ---------- output dirs (for LaTeX integration) ----------
p.images_dir = fullfile(thesis_dir, 'images');
p.tables_dir = fullfile(thesis_dir, 'tables');
p.csv_dir    = fullfile(thesis_dir, 'tables', 'ch4_csv');

if ~exist(p.images_dir, 'dir'); mkdir(p.images_dir); end
if ~exist(p.tables_dir, 'dir'); mkdir(p.tables_dir); end
if ~exist(p.csv_dir,    'dir'); mkdir(p.csv_dir);    end

% For backward-compatibility with older scripts:
p.out = p.csv_dir;

end
