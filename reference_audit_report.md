# 参考文献真实性与贴合度审查报告

## 审查范围与方法

- 审查对象：当前主论文 [xdupgthesis_template_lc.tex](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex) 中实际被引用的 49 个唯一参考文献键。
- 审查原则：优先逐篇阅读你本地 `参考文献pdf` 中对应原文；对本地缺失或文件名不直观的条目，补查 DOI 页面、期刊官网、官方政策页、标准页或可访问的摘要页。
- 审查口径：
  - `匹配良好`：原文能够直接支撑正文中的说法。
  - `基本匹配`：原文总体能支撑，但我拿到的是摘要/标准页/二次线索，或正文写法略宽。
  - `存在问题`：要么引用语句写重了，要么本地 PDF 与条目不一致，要么该文献本身并不适合支撑当前这句话。

## 主要发现

### 一类问题：需要优先处理

- `R02`，对应正文 [xdupgthesis_template_lc.tex:248](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L248)。
  - `references.bib` 中的条目与网页 URL 指向的是“百度地图《2024年度中国城市交通报告》”。
  - 但你本地保存的 [R02.pdf](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/参考文献pdf/R02.pdf) 实际是“高德地图《2023年度中国主要城市交通分析报告》”。
  - 这说明当前“本地证据包”与 bib 条目不一致。也就是说，这条引用不是“文献不存在”，而是“你本地下载到的 PDF 不是你正文正在引用的那份报告”。
  - 结论：`R02` 的真实性没有问题，但本地 PDF 错配，导致我无法用你本地 PDF 直接核对“北京、上海等超大城市通勤时间仍位居全国前列”这一句的细节。

- `ch3_yang2011amrtraffic`，对应正文 [xdupgthesis_template_lc.tex:619](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L619)。
  - 该文献题名为“异向性磁阻传感器检测车流量的新方法”，主题明显更接近“车流量检测方法”。
  - 你正文这里写的是“单地磁传感器具有成本低、功耗低、易于地埋部署以及适合长期在线运行等优势”。
  - 我没拿到该文的原文全文，也没有找到可核实摘要；从题名和可查到的信息看，它并不是支撑这句“工程优势总述”的理想来源。
  - 结论：这条最像“引文没错，但放错地方”。建议后续改引为更直接谈低成本、低功耗、易部署、长期运行的文献，如 `R09`、`ch2_sifuentes2011wakeup`、`wang2018roadside`。

- `ch4_lin2017surveyparking`，对应正文 [xdupgthesis_template_lc.tex:289](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L289)。
  - 这篇综述确实是智慧停车领域的重要总述。
  - 但你现在写成“Lin 等总结的智能停车方案主要面向封闭停车位或边界明确的停车区域”，这个判断偏强。
  - 原文综述其实覆盖了更广的 smart parking ecosystem，包括 on-street parking，并不只是在讲封闭车位。
  - 结论：文献真实，方向相关，但这句对原文的概括偏窄，建议改写而不是删引。

- `R43`，对应正文 [xdupgthesis_template_lc.tex:1344](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L1344)。
  - 这篇 GLOBECOM 2023 论文确实是“开放道路异常停车检测”，这点没有问题。
  - 但它重点讨论的是“太阳能板电流变化引起的局部电磁场变化”和“光照变化导致的误检”。
  - 你正文这里把它拿来一口气支撑“环境慢漂移、连续车流打断稳态证据、邻道车辆与低速停走引起伪稳态”三类困难，这就超出了原文直接论述范围。
  - 结论：`R43` 放在 [xdupgthesis_template_lc.tex:295](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L295) 那句“研究已扩展到开放道路异常停车场景”是合适的；放在 [xdupgthesis_template_lc.tex:1344](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L1344) 这句支撑三类一般性困难，则写重了。

### 二类问题：基本匹配，但证据强度略弱

- `ch3_mps_ga8022019`，对应正文 [xdupgthesis_template_lc.tex:639](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L639)。
  - 我核到了标准条目、适用范围和部分分类口径，能确认它是道路交通管理中的机动车分类标准。
  - 你正文是“参考该标准并归并为小、中、大三类”，这个用法是合理的。
  - 但我拿到的主要是标准页和标准全文转录页，不是你本地的官方 PDF。

- `ch4_wu2023iotparking`，对应正文 [xdupgthesis_template_lc.tex:1342](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L1342)。
  - 我核到了期刊条目和摘要。摘要明确写到“多个地磁传感器 + WiFi 模块 + 云平台 + 实时交互”。
  - 用它来支撑“围绕智慧停车系统的节点布设、数据汇聚与平台接入，相关工作也对停车网络的系统组织进行了研究”是基本匹配的。
  - 但这篇文章更偏系统实现与实验验证，不是高层系统综述。

- `ch3_xu2017featuresets`，对应正文 [xdupgthesis_template_lc.tex:1825](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L1825)。
  - 我没有拿到这篇 2017 原文全文。
  - 但在 [ch3_xu2018imbalanced.pdf](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/参考文献pdf/ch3_xu2018imbalanced.pdf) 的正文里，作者明确把它作为自己的前作介绍，并说明该路线面向更细的车辆类别，且属于单 AMR 传感器分类研究。
  - 你把它放在“未来可扩展到更细粒度车型分类任务”这一句后面，方向上是合理的，但目前属于间接核实。

- `ch5_salvador2007fastdtw`，对应正文 [xdupgthesis_template_lc.tex:1825](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L1825)。
  - 这篇文献真实无误，核心主题就是以更低复杂度逼近 DTW。
  - 你在未来工作里把它用于“轻量化时间对齐、模板压缩与特征增强方法”的方向性支撑，是合理的。
  - 但我当前拿到的是公开可访问摘要/条目信息，不是你本地全文。

- `ch5_cao2020magcal`，对应正文 [xdupgthesis_template_lc.tex:1827](/d:/xidian_Master/研究生论文/毕业论文/xduts-main/xdupgthesis_template_lc.tex#L1827)。
  - 原文明确讨论 magnetometer 的 real-time calibration，并强调对环境磁扰和参数偏差的在线校正。
  - 你把它放在“参数自适应、在线校准和异常参考检测机制”的未来工作里，是可以成立的。
  - 但它是更通用的磁力计校准方法文献，不是停车检测专文，所以属于“方法论引入”，不是“场景同源引用”。

### 三类问题：小的元数据/书目卫生问题

- `R26` 的本地原文题名是 “Deep learning approaches for vehicle type classification with 3-D magnetic sensor”，而 `references.bib` 中写成了 “with a Single 3-D Magnetic Sensor Node”。主题和 DOI 是对的，但题名建议按原文统一。
- `references.bib` 中存在若干重复或近重复条目，例如 `R09` / `haoui2008wireless`、`taghvaeeyan2014portable` / `ch2_taghvaeeyan2014portable`、`marshall1978vehicle` / `marshall1978magnetic`。这不影响当前正文引用真假，但后面若继续改文献，容易混淆。

## 已核实且与正文使用贴合良好的条目

下面这些条目，我已经通过本地全文或官方页面核过，正文中的使用总体是成立的。

### 绪论与第二章相关

- `R01`
- `wang2023transportation5`
- `ch2_bernas2018lowcost`
- `R09`
- `taghvaeeyan2014portable`
- `R49`
- `R52`
- `ch2_ding2004signal`
- `R13`
- `wang2018roadside`
- `marshall1978vehicle`
- `liu2017threeaxis`
- `ch2_sifuentes2011wakeup`
- `ch2_wang2011easitia`

### 第三章车型分类相关

- `feng2022magmonitor`
- `ch3_sarcevic2022singlemag`
- `R17`
- `R21`
- `R22`
- `R18`
- `R19`
- `R20`
- `R23`
- `ch3_zhang2019featureselection`
- `ch3_li2020singlemag`
- `R26`
- `breiman2001randomforests`
- `ch3_xu2018imbalanced`
- `ch3_feng2019magspeed`
- `ch3_sakoe1978dtw`
- `ch3_petitjean2011dba`
- `wei2017adaptable`

### 第四章停车与占用检测相关

- `ch4_gu2013streetparking`
- `ch4_bagula2015networks`
- `ch4_zhang2015amr`
- `ch4_zhang2020railway`
- `R47`
- `R45`
- `ch4_zhang2020tracking`
- `ch4_huang2017easydeploy`

## 当前建议的处理顺序

1. 先处理 `R02`。
   先把正确的百度 2024 报告 PDF 下载或替换到本地，再核对正文那句“北京、上海等超大城市通勤时间仍位居全国前列”是否与报告表述完全一致。

2. 再处理 `ch3_yang2011amrtraffic`。
   这条我更建议直接换引，不建议继续硬保。

3. 再收 `ch4_lin2017surveyparking` 和 `R43`。
   这两条更像“正文概括写重了”，通常改句子比换文献更好。

4. 最后统一书目卫生。
   包括 `R26` 题名统一、重复 bib 条目清理、本地 PDF 与 bib 映射关系再整理一遍。

## 现阶段结论

- 49 个实际被引用的唯一文献键中：
  - `40` 个条目可判定为“匹配良好”；
  - `5` 个条目可判定为“基本匹配，但证据强度略弱”；
  - `4` 个条目存在明确问题，建议优先处理。
- 目前最需要你警惕的，不是“大量引用造假”，而是“少数条目引用位置不理想”与“个别本地 PDF 错配”。
- 整体上，这篇论文的大部分引用是真实、可核和基本贴合的，但确实有几处需要认真收口，否则盲审时容易被抓住。
