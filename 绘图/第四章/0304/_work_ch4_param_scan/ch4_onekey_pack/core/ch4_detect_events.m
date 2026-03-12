function events = ch4_detect_events(pr, cfg)
%CH4_DETECT_EVENTS Detect vehicle events (arrive/leave) from pr_vehicle
% Output: struct array with fields k_in, k_out

n = numel(pr);
ev = cfg.ev;

state = 1;
i = 1;

arriveCount = 0; arriveNum = 0; arriveleft = 1; arriveright = 1;
leaveCount  = 0; leaveNum  = 0; left = 1; right = 1;
td = 0;

events = [];
k_in = NaN;

while i <= n
    Pr_i = pr(i);

    switch state
        case 1  % FREE
            if Pr_i >= ev.theta_arrive
                state = 2;
                arriveNum = 1;
                arriveCount = 1;
                arriveleft = i;
                arriveright = min(n, i + ev.arriveLen);
            end

        case 2  % arrive detect
            if arriveNum < ev.arriveLen
                arriveNum = arriveNum + 1;
            end
            if Pr_i >= ev.theta_arrive
                arriveCount = arriveCount + 1;
            end

            if arriveNum >= ev.arriveLen && arriveCount < ev.arriveWin
                arriveleft = arriveleft + 1;
                if arriveright < n
                    arriveright = arriveright + 1;
                end
                arriveCount = sum(pr(arriveleft:arriveright) >= ev.theta_arrive);
            end

            if arriveCount == 0
                state = 1;
            end

            if arriveCount >= ev.arriveWin
                k_in = i;
                td = 0;
                arriveCount = 0;
                state = 3;
            end

        case 3  % delay
            td = td + 1;
            if td >= ev.Td
                state = 4;
            end

        case 4  % passing
            if Pr_i < ev.theta_leave
                state = 5;
                leaveCount = 1;
                leaveNum = 1;
                left = i;
                right = min(n, i + ev.leaveLen);
            end

        case 5  % leave detect
            if leaveNum < ev.leaveLen
                leaveNum = leaveNum + 1;
            end
            if Pr_i < ev.theta_leave
                leaveCount = leaveCount + 1;
            end

            if leaveNum >= ev.leaveLen && leaveCount < ev.leaveWin
                left = left + 1;
                if right < n
                    right = right + 1;
                end
                leaveCount = sum(pr(left:right) < ev.theta_leave);
            end

            if leaveCount >= ev.leaveWin
                k_out = i;
                e.k_in = k_in;
                e.k_out = k_out;
                events = [events; e]; %#ok<AGROW>
                state = 1;
                leaveCount = 0;
            end
    end

    i = i + 1;
end
end
