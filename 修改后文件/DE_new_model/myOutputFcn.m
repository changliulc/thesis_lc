function stop = myOutputFcn(optimValues, state)
%optimValues, state, min_value 这个函数用来输出globalsearch迭代过程中的一些信息
%   20240617写的

%初始化停止标志为false
stop=false;
%只在每次迭代结束时输出目标函数值和迭代次数
if strcmp(state,'iter')
    %获取当前的输出目标函数值、迭代次数
    currentFval = optimValues.localsolution.Fval;
    global iteration_count;
    iteration_count=iteration_count+1;
    iteration = iteration_count;
    % disp(optimValues);
    %打印目标函数值和迭代次数
    fprintf('Iteration: %d, Function Value: %.6f\n', iteration, currentFval);
    % fprintf(' Function Value: %.6f\n',  currentFval);
end

end