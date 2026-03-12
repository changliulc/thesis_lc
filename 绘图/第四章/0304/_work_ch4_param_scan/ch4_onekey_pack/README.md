# Chapter-4 One-Key Experiment Pack (GLOBAL)

本目录用于**一键生成论文第4章所需的实验图与表格行（LaTeX 可直接 \input）**。

- 目标：让第4章的“现象 → 方法 → 参数 → 量化结果 → 典型案例”证据链闭环。
- 输出：
  - `images/` 下的 `ch4_*.pdf`（论文插图）
  - `tables/` 下的 `ch4_*_rows.tex`（表格行片段）
  - `tables/ch4_csv/` 下的中间 CSV（便于复核）

> 说明：pipeline/fsm/布设图等“概念图”本质更适合手工绘制（TikZ/draw.io）。本包会生成可用的**自动版本/占位版本**，确保 LaTeX 不缺图；最终你可以替换为手工高质量版本（保持同名文件即可）。

---

## 1. 目录结构与数据放置

推荐在论文工程根目录按如下放置（脚本会自动探测）：

```
<THESIS_ROOT>/
  chapters/
  images/
  tables/
  data/
    zhenzhi/                # 实测 clean CSV + GT
      *.csv
      parking_groundtruth_filled_cleaned.csv
    synth_out/              # 可选：合成/扩增 CSV（用于补充 B/C/D 类样例）
      *.csv
  ch4_onekey_pack/
```

若你没有 `data/` 目录，也可直接使用：

- `<THESIS_ROOT>/zhenzhi/`
- `<THESIS_ROOT>/synth_out/`

路径探测与默认文件名在：`core/ch4_local_paths.m`

---

## 2. 一键运行

在 MATLAB 中：

```matlab
cd('<THESIS_ROOT>/ch4_onekey_pack');
run('run/run_ch4_onekey_global.m');
```

成功后你会在：

- `<THESIS_ROOT>/images/` 看到 `ch4_*.pdf` 图
- `<THESIS_ROOT>/tables/` 看到 `ch4_*_rows.tex`（供 LaTeX \input）

---

## 3. 关键可调项（建议你只改这些）

所有可视化/案例选择相关的开关集中在：

- `run/run_ch4_onekey_global.m` 顶部的 `figOpt.*`

### 3.1 “典型案例”窗口（A/B/C/D）

- 默认每类取一个“中位”样例并按事件中心截窗。
- **D 类慢漂移**默认窗更长（`padSec=60`），避免“窗太短看不出漂移”。

你也可以手工指定中心时刻（秒）：

```matlab
figOpt.extra_case_tCenter_by_group.D = 185;  % 例：卡在漂移最明显时刻
```

并可按组配置窗长：

```matlab
figOpt.extra_case_padSec_by_group.D = 60;
```

### 3.2 case 图 vs wave 图（你当前采用的推荐策略）

- **wave 图**用于解释现象（可用单轴 Bx，前提是各点安装姿态/坐标系一致）。
- **case 图**用于证明算法闭环（输入→中间量→决策→输出），更抗答辩追问。

本包的“典型案例图”默认用三轴差分（`case_sigMode = 'dxyz'`），即：

- 上：\(\Delta B_x,\Delta B_y,\Delta B_z\)
- 中：稳定判据/稳定标志
- 下：GT vs 预测（条带叠加）

这对应“算法内部仍使用三轴特征”的事实；同时可读性比原始三轴 Bx/By/Bz 平台对比更强。

### 3.3 dist_th 的论证方式（已修复）

`dist_th` 在 FSM 中是**“占用稳态相似性门控阈值”**，不是“释放检测阈值”。

因此本包不再画“释放召回/误释放”那种会被追问的 TPR/FPR，而改为：

- **验证集扫参曲线：** B/D 组 F1 vs `dist_th`
- **门控敏感性：** \(Acc(d)=Pr(dist<d\mid\text{仍占用扰动})\)

对应图：

- `images/ch4_param_scan_dist.pdf`
- `images/ch4_sensitivity.pdf`（右子图）

---

## 4. 与 LaTeX 的衔接

第4章 LaTeX 通常会 \input 这些行文件（脚本自动生成）：

- `tables/ch4_dataset_rows.tex`
- `tables/ch4_bycase_global_rows.tex`
- `tables/ch4_timing_global_rows.tex`

如果你在 LaTeX 里看到 `--` 或缺行，说明脚本没有跑完或数据路径/GT 文件名不匹配。

---

## 5. Python 预览（不依赖数据，可用于快速调版式）

如果你想先看“图面布局”是否适合论文排版，可运行：

```bash
python3 python/ch4_wave_case_preview.py
```

它会在当前目录生成若干 `*_demo.png`，用于检查：

- 多行子图的字号/留白
- GT/预测条带的可读性
- 单轴 wave vs 三轴 case 的信息密度

---

## 6. 常见问题

1) **缺图**：先确认 `images/` 是否生成对应 `ch4_*.pdf`，再检查 `core/ch4_local_paths.m` 的数据路径与 GT 文件名。

2) **图中文字太挤**：优先调 `cfg.plot.*` 字号、`padSec`、以及案例截窗中心 `tCenter`，不要强行塞满一张图。

3) **你要替换手工图**：只要生成同名 PDF（例如 `ch4_pipeline.pdf`、`ch4_fsm_degrade.pdf`）覆盖即可，LaTeX 无需改动。
