Chapter 4 Figure 4.8 discussion package

Current focus:
- A/B/C already adjusted in preview.
- D is being redesigned.
- Current D preview uses:
  1) candidate parking event source: D:\download\lunwen\ch4_auto_picks_out\data_extracted\data\zhenzhi\20240726_停车检测_sheet1_clean.csv
  2) long drift source: D:\xidian_Master\研究生论文\毕业论文\实验数据\2026-03-18 091512.XDat
  3) target duration: 7 h
  4) target drift amplitude: about 65 / 65 / 70
  5) display-priority entry/exit currently exaggerated to 25 s each

Key files:
- scripts\ch4_wave_preview_and_prepare.py : current Python preview script
- scripts\ch4_make_wave_abcd_unified.m    : current MATLAB script snapshot
- data\fig_a_win.csv / fig_b_win.csv / fig_c_win.csv / fig_d_win.csv : current thesis window data
- data\20240726_停车检测_sheet1_clean.csv : D candidate parking source
- data\fig_d_win_new.csv                  : latest generated D preview data
- data\drift_template_norm.csv            : normalized drift template derived from long XDat
- previews\ch4_wave_D_preview.png         : latest D preview
- previews\ch4_wave_abcd_preview.png      : latest A/B/C/D preview

Current discussion point:
- On a 7 h linear axis, even 20~30 s entry/exit still appears very steep.
- The next decision is whether to:
  a) keep strict linear axis and accept steep entry/exit,
  b) exaggerate entry/exit much more for display,
  c) use broken axis / inset.
