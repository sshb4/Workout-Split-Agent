# Workout Split + Weights Agent
## Design + Proof of Concept (U0-HW-10)

**Name:** Sasha Bates
**Repository:** [Workout-Split-Agent](https://github.com/sshb4/Workout-Split-Agent)
**Submitted commit:** [commit hash]

## 1. Problem, user, intended use, target outcome

**Problem:** Planning a workout split becomes difficult when a person's schedule, available equipment, or performance changes. The user must decide which exercises to perform, how to distribute them across the week, and what starting weights to use.

**Intended user:** A gym-goer who wants a workout plan tailored to their goals, available training days, equipment, and exercise preferences.

**Intended use:** The user provides a structured profile and known lifts or recent sets. The system produces a weekly split with exercises, sets, repetitions, estimated starting weights, and a trace explaining its calculations.

**Target outcome:** A plan that meets defined muscle-coverage and session-time targets, respects supported constraints, and calculates starting loads using the configured goal-specific percentage ranges. These calculations do not establish that a load is safe or appropriate for an individual.

**Week 1 scope:** The POC selects a predefined weekly split, searches exercise combinations for each workout under equipment, exercise-restriction, primary-muscle coverage, and estimated-time constraints, calculates starting loads, and writes results and search evidence. It processes one profile per run.

**Planned agent behavior:** In Weeks 2–3, the system will improve exercise selection and substitutions, revise plans when equipment or schedules change, and adjust loads using workout feedback. A web interface is an optional extension after the main implementation and evaluation.

## 2. PEAS

- **Performance:** Muscle coverage, percentage of sessions within the time limit, compliance with equipment and exercise restrictions, and percentage of reference-based loads within the configured goal band. Later evaluation will measure adaptation accuracy and user ratings.
- **Environment:** A simulated workout-planning environment containing a user profile in JSON and a curated exercise database in CSV. Later versions will include workout history and feedback.
- **Actuators:** Write the proposed weekly split, exercises, sets, repetitions, starting loads, and decision trace to output files. Later versions will revise the plan after feedback.
- **Sensors / percepts:** Read training days, session duration, equipment, goal, disliked exercises, movement restrictions, and known 1RMs or recent sets. Later versions will read completed repetitions, RPE, failed sets, and pain flags.

## 3. Decision boundary, percepts, actions, state, goal / terminal

- **Decision boundary:** Select a predefined split based on training days; search exercise combinations that satisfy equipment, dislikes, supported movement restrictions, primary-muscle coverage, and estimated time; calculate starting loads using the selected goal. Day-of replanning and feedback-based adaptation are planned for Weeks 2–3.
- **Percepts:** The structured profile and exercise database described in PEAS. Free-text preferences and injuries are currently logged but do not automatically become restrictions.
- **Actions:** Estimate 1RMs, apply goal mappings, search and select exercise combinations, assign sets/repetitions/loads, estimate session duration, report muscle coverage, and write the plan and trace.
- **State:** During a run, retain the profile, exercise database, estimated 1RMs, selected split, generated workouts, coverage set, and trace. The POC does not load previous workout history.
- **Goal:** Produce a plan meeting the proposed coverage, time, equipment, and load-calculation criteria. The search enforces workout-level primary coverage, equipment and supported exclusions, and estimated time. Load-band validation and weekly recovery checks are not enforced. Include-list entries are soft preferences, not guaranteed requirements.
- **Terminal condition:** A completed run ends when the JSON plan and trace are written, including a feasible or infeasible status. An infeasible workout has no selected exercises and records the reason. An unsupported goal or training-day count ends the run with an error.
- **Environment interaction:** Read local input files and write local results. The user reviews the plan; the POC does not observe workout performance. Later versions will use logged feedback to revise plans.
- **Scope boundary:** Medical diagnosis is outside scope. Handling pain feedback by stopping or flagging an exercise is planned behavior and is not implemented in Week 1.

## 4. AI strategy and fit

**Selected AI strategy:** Constraint-based planning using exhaustive search, supported by deterministic calculation tools. No LLM is required or called in Week 1. An LLM is an optional later extension for free-text interpretation or explanations.

**Why it fits:** Equipment, movement restrictions, muscle coverage, and available time constrain which exercise combinations are acceptable. Searching alternatives allows the agent to select a feasible combination or explain why the requirements cannot be met.

**Implemented search:** A predefined weekly split supplies the required primary muscles for each workout. The planner filters the CSV to eligible exercises, then enumerates combinations by increasing exercise count within the estimated time budget. A feasible combination must contain at least one primary-muscle exercise for each required muscle. Among combinations at the smallest feasible size, it first maximizes include-list preferences, then compound-exercise count; alphabetical names break ties. The trace retains candidate counts, combinations evaluated, feasible counts, selected exercises, and failure reasons. Each exercise uses three sets; estimated duration is 3 × (1 minute of work + goal-specific rest in minutes).

**Principal technical uncertainty:** Can a small search planner construct a workout that satisfies coverage, equipment, restrictions, and estimated-time constraints, while detecting conflicting requirements instead of returning an incomplete plan?

**POC finding:** The supplied profile produces feasible searched workouts. A dumbbell-only case succeeds, while insufficient time and missing eligible exercises produce explicit infeasible results. This supports the feasibility of the constrained search pipeline, not individual load safety or training effectiveness. Weekly recovery, exercise ordering, richer quality scoring, and feedback adaptation remain future work.

## 5. Data sources

**Exercise database:** The POC reads a local CSV containing 55 exercises with primary and secondary muscles, equipment, exercise type, reference lifts, and load-calculation fields. Search coverage currently uses primary muscles only. External exercise APIs are possible future extensions.

**User profile:** A local JSON file supplies the training goal, days per week, session-time limit, equipment, exercise preferences, movement restrictions, and known lifts or recent sets. The submitted sample contains fictional data.

**Load calculations:** When recent sets are provided, the POC estimates 1RM using the Epley formula: `weight × (1 + repetitions / 30)`. Configured goal ranges determine the starting-load percentage. Exercise conversion fractions and fixed accessory starting loads are heuristic assumptions that require later validation.

**Fallback estimates:** When no lift data is available, the code uses fixed bodyweight ratios as rough calibration estimates. These ratios are not personalized by sex or training level.

**Supported preferences:** Equipment, disliked exercises, and supported movement restrictions constrain the search. Include-list exercises influence scoring. Free-text preferences, injury descriptions, and secondary goals are retained but do not change the generated plan.

**Model requirements:** The POC uses Python's standard library. It requires no trained model, LLM, API key, or network connection.

## 6. System diagram

```text
User profile JSON + Exercise CSV
                |
                v
Read goal, estimate 1RMs, select weekly split
                |
                v
Filter candidates for each workout
(equipment, dislikes, movement restrictions)
                |
                v
Search exercise combinations
(require primary-muscle coverage and time fit)
                |
         +------+------+
         |             |
      Feasible      Infeasible
         |             |
         v             v
Select best plan   Record reason;
and calculate      no exercises
starting loads     for that workout
         |             |
         +------+------+
                |
                v
Write JSON results and decision trace
```

## 7. Implementation and evaluation scope

- **Week 1 — ending November 5:** Complete the search POC, load calculations, JSON output, and trace. Retain the sample run and checks covering feasible selection, conflicting constraints, and selection scoring.
- **Week 2 — ending November 12:** Improve exercise ordering and scoring; add input validation, load-band checks, and weekly recovery checks. Demonstrate replanning after an equipment change with before/after evidence.
- **Week 3 — ending November 19:** Add feedback-based load adjustment. Evaluate at least six fixed profiles against a predefined template baseline. Retain successful and unsuccessful examples, numerical results, and a provisional deploy/revise/do-not-use recommendation.
- **Thanksgiving week:** No project submission scheduled.
- **Final week — ending December 3:** Limited fixes, documentation, final report, and presentation slides. A web interface remains optional if the core implementation and evaluation are complete.

## 8. Repeatable evaluation plan

**Procedure:** Save at least six fixed test profiles covering a full gym, dumbbells only, bodyweight only, limited time, movement restrictions, and conflicting requirements. Record the expected feasible/infeasible outcome before running each case. Run the planner and a fixed exercise-template baseline on the same inputs, using the same checks. Retain inputs, outputs, traces, and results.

| Measure | Target |
| --- | --- |
| Equipment and exercise restrictions | Zero violations in workouts reported as feasible |
| Required primary-muscle coverage | 100% for each feasible workout |
| Estimated session time | Every feasible workout within the input time limit |
| Failure detection | Correct feasible/infeasible classification for all test cases |
| Load calculation compliance | 100% of reference-based loads within the configured band after rounding; accessory starters reported separately |
| Repeatability | Identical selected exercises and statuses when rerunning the same inputs |
| Feedback adjustment, Week 3 | All predefined success/failure cases produce the expected adjustment direction and amount |

**Baseline comparison:** Report feasible-plan rate and constraint violations for both systems. A correct infeasible result is successful failure detection, rather than a usable plan.

**Week 1 evidence:** The sample profile and four retained search checks have passed. These are initial checks; the six-profile comparison, load validation, weekly recovery evaluation, and feedback evaluation remain planned work.

**Interpretation:** These measures evaluate planning behavior and calculation compliance. They do not establish muscle gain or individual exercise safety.

## 9. Limitations, failure conditions, and recommendation criteria

**Limitations:** The POC uses a small exercise database, predefined weekly splits, and primary-muscle coverage. It does not validate exercise order, weekly recovery, or effective training volume. Time estimates exclude warm-up and transitions. Load estimates, exercise-conversion fractions, and accessory starters require further validation. Free-text interpretation, injury handling, and feedback adaptation are not implemented. Exhaustive search may become costly with a larger database.

**Failure conditions:** A workout is reported as feasible despite violating equipment, supported restrictions, coverage, or estimated-time constraints; conflicting requirements produce an incomplete plan without an infeasible status; or load calculations fail the configured checks. Later versions must also detect failures in recovery rules and feedback adjustment.

**Deploy:** Recommend a limited, supervised pilot only after all required checks pass across the fixed evaluation cases, recovery and feedback handling are implemented, and a human review finds the plans usable. Passing software checks alone does not establish individual exercise safety.

**Revise:** The system reports its limitations and infeasible cases correctly, but plan quality, supported constraints, or evaluation coverage remain insufficient.

**Do not use:** The system silently violates required constraints, presents unsupported load estimates as validated recommendations, or ignores pain feedback while claiming to handle it.

**Current recommendation:** Revise and continue development. The Week 1 results support feasibility, but deployment criteria have not been met.

## 10. POC evidence — Week 1, actually run

Command:
```
python3 ai-project-workout-split-poc.py ai-project-workout-split-profile.json
```
Input: `ai-project-workout-split-profile.json`
Sample profile only, NOT real lifts: 24M, 185 lb, 6'0", hypertrophy, 5 days/week,
45 min, full gym, squat 185x8, bench 135x8, deadlift 225x5, OHP 95x8,
row 135x8, hip thrust 225x10.
Code: `ai-project-workout-split-poc.py`
Exercise DB: `ai-project-workout-split-exercises.csv`
Output: `ai-project-workout-split-output.json`
Trace: `ai-project-workout-split-trace.log`

Additional source: `workout_planner.py` (imported by the POC).
Requirements: Python 3, standard library only. Run commands from the project directory with all source and data files present.

Result: Epley 1RMs — squat 234.3, bench 171.0, deadlift 262.5, OHP 120.3,
row 171.0, hip thrust 300.0 lb. The configured hypertrophy midpoint is 76%.
Example reference-based loads: squat 177.5 lb, bench 130.0 lb, row 130.0 lb,
deadlift 200.0 lb, and hip thrust 227.5 lb.

| Workout | Combinations evaluated | Feasible at minimum size | Estimated minutes |
| --- | ---: | ---: | ---: |
| Push | 816 | 192 | 22.5 |
| Pull | 66 | 27 | 15.0 |
| Legs | 3,876 | 360 | 30.0 |
| Upper | 142,506 | 5,184 | 37.5 |
| Lower | 3,876 | 360 | 30.0 |

All five searched workouts are feasible under the implemented constraints.
Average estimated duration is 27.0 minutes against a 45-minute limit.
The split contains all nine primary muscle labels reported in the output;
this is not a validation of recovery or training effectiveness.

Repeatable search checks:

```sh
python3 evaluate-workout-search.py
```

Retained evidence: `ai-project-workout-split-search-evidence.json`.

- Dumbbells, chest/back/shoulders, 30 minutes, with exercise exclusions: feasible; three exercises, 22.5 estimated minutes.
- Same primary-muscle targets with only 15 minutes: infeasible; at least 22.5 estimated minutes required.
- Bodyweight-only chest/back/shoulders: infeasible because the CSV has no eligible shoulder-primary exercise.
- Three-exercise toy database: selects the preferred feasible pair; checks exact combination counts and objective ordering.

The evaluation script also checks selected equipment, exclusions, primary coverage,
time compliance, and stability when the database order is reversed.

**Feasibility assessment:** The POC demonstrates actual search over exercise combinations,
reproducible load calculations, and explicit failure reporting. This supports proceeding
with the project. Next work must improve plan quality, validate loads and inputs,
model weekly recovery, and add feedback-based replanning. The results do not establish
that the generated workouts or loads are appropriate for deployment.
