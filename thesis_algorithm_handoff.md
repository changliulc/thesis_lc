# Thesis Algorithm Handoff

## Purpose

This file is a handoff summary for future chats.

If a new conversation needs to understand the thesis algorithm quickly, read this file first instead of re-reading the whole codebase.

The main historical engineering reference discussed here is:

`D:\xidian_Master\研究生论文\20241028_diff_modify_add_vehicle_9600\DS3110H&DS3110E&DS3205_2024-01-25-V373-369W（兼容版本）同0119优化浮点运算\Apps\src\mc\mag_proc.c`

The current thesis draft reference is:

`xdupgthesis_template_lc.tex`

## Core Conclusion

The thesis is not three unrelated topics placed side by side.

The real chain is:

`continuous triaxial geomagnetic stream -> vehicle event extraction base -> two upper-layer task branches`

The two branches are:

1. event-level vehicle type classification in Chapter 3
2. state-level parking / occupancy inference in Chapter 4

So the correct understanding is:

`Chapter 2 provides the shared interface`

Then:

`Chapter 3 consumes event segments`

`Chapter 4 consumes event triggers and event-neighbor signals`

It is not:

`event detection -> vehicle classification -> parking detection`

Chapter 3 and Chapter 4 are parallel upper tasks built on the same event base.

## One-Sentence Thesis Story

Under a single roadside triaxial geomagnetic sensor, the thesis first converts continuous observations into a stable and unified event-level interface, then uses that interface to support vehicle type recognition and parking/occupancy state inference.

## Full Pipeline

### Layer 1: Continuous Observation

Input:

- roadside single-node triaxial geomagnetic signal
- sampling rate: `50 Hz`
- continuous stream `B(k)`

Goal:

- continuously observe disturbances caused by vehicles
- keep the method compatible with low-power roadside deployment

### Layer 2: Vehicle Event Extraction Base (Chapter 2)

This is the common foundation of the whole thesis.

Main logic:

1. read continuous triaxial signal
2. compute first-order differences on three axes
3. smooth the difference signals
4. evaluate per-axis disturbance evidence against background statistics
5. fuse three-axis evidence into a real-time vehicle probability
6. use a finite-state machine plus consecutive-count confirmation to stabilize boundaries
7. output the event interface

Output interface:

- vehicle event start boundary
- vehicle event end boundary
- standardized event segment
- event trigger metadata

In thesis language, this is the shared event-level input base.

In old engineering code, this is the logic around:

- difference features
- `Pdetect`
- `detectVehicleDif`
- `MAGStateDif`
- arrival / leave confirmation

### Layer 3A: Vehicle Type Classification Branch (Chapter 3)

This branch treats one detected vehicle event as one sample.

Main logic:

1. use Chapter 2 boundaries to cut out a single vehicle event
2. build event-level representation
3. classify the event into `small / medium / large`

The thesis uses two paths here.

#### Path A: Edge-Side Lightweight Classification

Purpose:

- fit roadside node constraints
- low computation
- low storage
- low communication overhead

Main idea:

1. represent each event with baseline-removed triaxial disturbance and magnitude sequence
2. extract low-cost statistical features
3. rank and de-redundancy features
4. keep a small Top-K feature subset
5. use Softmax as the edge-side main classifier

This path is conceptually close to the old embedded classification logic:

- accumulate event statistics during the event
- classify after event termination

#### Path B: Offline Enhanced Classification

Purpose:

- not for direct edge deployment
- used to study performance ceiling and the value of time alignment

Main idea:

1. map variable-length events to a unified length
2. build a 1D CNN baseline on fixed-length inputs
3. add DTW alignment to compensate for speed-induced temporal stretching
4. use single-template and multi-template DTW enhancement
5. feed aligned sequences to the same CNN backbone

This branch is new in the thesis and is not present as a complete counterpart in the old `mag_proc.c`.

### Layer 3B: Parking / Occupancy Branch (Chapter 4)

This branch does not use the event segment as the final answer.

Instead, it uses the Chapter 2 event as a trigger entry.

That distinction is essential.

Chapter 2 gives:

- disturbance event boundaries

Chapter 4 wants:

- parking confirmation
- occupancy maintenance
- occupancy release
- occupancy state interval

So Chapter 4 is a state inference problem built on top of event triggers.

Main logic:

1. after an event, search for stable windows in the event neighborhood
2. extract stable points rather than relying only on event-ending instant values
3. maintain two dynamic references
4. compare new stable evidence with those references
5. use an outer state logic to decide whether occupancy is established, maintained, or released
6. if no stable point can be found in time, fall back to a degraded branch for continuous traffic

The two core references are:

- environment reference stable point `Spre`
- occupancy reference stable point `Spost`

The key judgment pieces are:

- stable-window dual criteria
- drift magnitude
- similarity gating
- outer state machine
- degraded branch under missing stable windows

This branch is strongly related to the old engineering parking logic, but the thesis expresses it more clearly and more academically.

## Old `mag_proc.c` vs Thesis: Structural Mapping

| Old code concept | Thesis concept | Meaning |
| --- | --- | --- |
| `xdiff / ydiff / zdiff` | triaxial first-order difference | disturbance enhancement |
| smoothed difference update | difference smoothing | suppress noise and spikes |
| `Pdetect` | fused vehicle probability `Pcar(k)` | real-time vehicle evidence |
| `detectVehicleDif` | consecutive-count event confirmation | stabilize arrival / leave detection |
| `MAGStateDif` | finite-state machine for event extraction | event boundary control |
| event arrival / leave timestamps | `k_in / k_out` style event boundaries | event interface output |
| `VehicleSort(...)` | event-level feature accumulation | build classification evidence during the event |
| `get_Vehicle_type_basis(...)` | edge-side lightweight classification | classify one event |
| `JudgeStability(...)` | stable-window judgment | identify post-event stable evidence |
| `ParkDetect_basis(...)` | dynamic-reference parking / occupancy inference | decide parking / release around stable points |
| parking status transitions | outer state logic | maintain state across events |

## Main Similarities

The old algorithm and the thesis are similar in the following structural sense.

1. Both start from continuous triaxial geomagnetic signals.
2. Both use difference-based disturbance enhancement.
3. Both use probability-style or threshold-style evidence fusion.
4. Both use a finite-state-machine-like logic to stabilize vehicle event detection.
5. Both do edge-side vehicle-type reasoning after a vehicle event has been identified.
6. Both treat parking inference as something that cannot be solved by a single disturbance boundary alone.
7. Both rely on stable-region evidence and drift comparison in parking logic.

## Main Differences

The thesis is not a direct code dump of the old algorithm.

The main differences are:

1. The old code is a tightly coupled engineering implementation in one file, while the thesis turns the logic into a clearer research chain with a shared Chapter 2 interface.
2. The thesis explicitly defines the event-level interface and uses it as a formal common input to later chapters.
3. The thesis adds the offline DTW + CNN classification branch, which is not a complete part of the old embedded implementation.
4. The thesis formalizes parking logic into a more explicit framework: stable-point extraction, environment reference, occupancy reference, outer state logic, and degraded branch.
5. The thesis separates "disturbance event boundary" from "occupancy state interval", which is a very important conceptual cleanup.

## Important Reading Rule

When reading the thesis, always keep the following distinction in mind:

1. Chapter 2 answers: how does continuous signal become a reliable vehicle event interface?
2. Chapter 3 answers: given one event, what type of vehicle is it?
3. Chapter 4 answers: after an event happens, does the road position enter, keep, or release occupancy?

This distinction avoids a common misunderstanding:

- vehicle event boundary is not equal to occupancy interval

Chapter 4 goes beyond event detection and performs state-level inference.

## Practical Interpretation of Each Chapter

### Chapter 2

Role:

- shared bottom interface

Do not describe it as:

- just a simple vehicle counter

Better description:

- a unified event extraction base for later multi-task sensing

### Chapter 3

Role:

- event-level recognition branch

Do not describe it as:

- directly working on the whole continuous signal

Better description:

- classification on top of event-segment organization

### Chapter 4

Role:

- state-level inference branch

Do not describe it as:

- simply using the same event boundary as the parking interval

Better description:

- using event-triggered stable evidence and dynamic references to infer occupancy state segments

## Current Best High-Level Summary for Future Chats

Use the following summary sentence by default:

`The thesis studies roadside sensing with a single triaxial geomagnetic node. It first converts continuous 50 Hz magnetic observations into a stable event-level interface, then uses that interface in two upper-layer branches: event-level vehicle type classification and state-level parking/occupancy inference.`

## Warning About the Old Code Snapshot

The old `mag_proc.c` is useful as structural evidence, but not every line should be treated as the final clean thesis algorithm.

One notable issue in the inspected snapshot is that `get_Vehicle_type_basis(...)` contains a forced assignment:

- `type_value = VEHICLE_BIG;`

So this snapshot is reliable for understanding the overall structure, but not ideal as the final source of classification-result correctness.

## Recommended Workflow for Future Chats

If a future chat needs context, use this order:

1. read `thesis_algorithm_handoff.md`
2. if needed, read the corresponding thesis chapter in `xdupgthesis_template_lc.tex`
3. only inspect old `mag_proc.c` when a very specific implementation detail is needed

## Suggested Prompt for a New Chat

Use this directly in a future conversation:

`Please read thesis_algorithm_handoff.md first and use it as the primary summary of the thesis algorithm. Only inspect thesis TeX or old code if a specific detail is still unclear.`

