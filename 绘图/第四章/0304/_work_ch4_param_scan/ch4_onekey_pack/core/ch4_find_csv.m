function csvPath = ch4_find_csv(fileName, DATA_DIR, SYN_DIR)
%CH4_FIND_CSV  Resolve CSV path from clean and synth folders.
%
% This helper is robust to:
% 1) Data unzipped with an extra subfolder (e.g., SYN_DIR/synth_out/ ...)
% 2) Filenames where Chinese characters are encoded as "#UXXXX" (zip tools)
%
% Priority:
%   - If *_synth.csv, search SYN_DIR first
%   - Otherwise search DATA_DIR first
%
% Returns "" if not found.

fileName = string(fileName);

if strlength(fileName) == 0
    csvPath = "";
    return;
end

% Already an existing path
if exist(fileName, 'file') == 2
    csvPath = fileName;
    return;
end

% candidate names (plain + #U encoded)
name_plain = fileName;
name_hashU = encode_hashU(fileName);

% candidate directories (also try extra-layer folders)
DATA_CANDS = [
    string(DATA_DIR), ...
    fullfile(string(DATA_DIR), "zhenzhi") ...
];
SYN_CANDS = [
    string(SYN_DIR), ...
    fullfile(string(SYN_DIR), "synth_out") ...
];

% build candidate path list
paths = strings(0,1);
if endsWith(fileName, "_synth.csv")
    % synth first
    for d = SYN_CANDS
        paths(end+1,1) = fullfile(d, name_plain); %#ok<AGROW>
        paths(end+1,1) = fullfile(d, name_hashU); %#ok<AGROW>
    end
    for d = DATA_CANDS
        paths(end+1,1) = fullfile(d, name_plain); %#ok<AGROW>
        paths(end+1,1) = fullfile(d, name_hashU); %#ok<AGROW>
    end
else
    % clean first
    for d = DATA_CANDS
        paths(end+1,1) = fullfile(d, name_plain); %#ok<AGROW>
        paths(end+1,1) = fullfile(d, name_hashU); %#ok<AGROW>
    end
    for d = SYN_CANDS
        paths(end+1,1) = fullfile(d, name_plain); %#ok<AGROW>
        paths(end+1,1) = fullfile(d, name_hashU); %#ok<AGROW>
    end
end

csvPath = "";
for i = 1:numel(paths)
    if exist(paths(i), 'file') == 2
        csvPath = string(paths(i));
        return;
    end
end

end

%% --- local helper: encode non-ascii characters into #UXXXX ---
function out = encode_hashU(in)
in = char(in);
out = "";
for i = 1:numel(in)
    c = in(i);
    if c <= 127
        out = out + string(c);
    else
        out = out + sprintf("#U%04X", uint16(c));
    end
end
out = string(out);
end
