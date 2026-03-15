function [T1] = smooth(T)
L = length(T);
N=10;  % ´°¿Ú´óĞ¡ 
k = 0;
m =0 ;
for i = 1:L
    m = m+1;
    if i+N-1 > L
        break;
    else
        for j = i:N+i-1
            k = k+1;
            W(k) = T(j) ;
        end
        T1(m) = mean(W);
        k = 0;
    end
end
