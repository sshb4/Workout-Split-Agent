#!/usr/bin/env python3
"""
Workout split + weights agent — POC, Week 1.

What this POC proves, on a limited version:
  profile.json -> Epley 1RM estimate (or known 1RM if given)
               -> goal -> %1RM / rep range / rest
               -> split structure that fits days_per_week
               -> exercises filtered by equipment + muscle + dislikes
               -> sets / reps / starting weights, rounded to loadable plates
               -> time estimate + muscle coverage check
               -> trace log showing every decision

What it does NOT do yet (Weeks 2-3):
  feedback adaptation loop, secondary-goal blending, full wger/ExerciseDB
  pull, UI / login / database. Those are extensions, not POC claims.

POC limits:
  - Load calculations use heuristic reference-lift fractions and rounding;
    they do not establish individual safety or enforce goal-band validation.
  - Out-of-range Epley inputs are warned about, not rejected.
  - Accessory starters require calibration; feedback is not implemented.
  - Constraint search uses primary muscles and estimated time only.
"""
import csv, json, sys
from workout_planner import plan_workout
from pathlib import Path

BASE = Path(__file__).parent
TRACE = []

def log(msg):
    TRACE.append(msg)
    print(msg)

def round_to_plate(lb, increment=2.5):
    """Round to nearest loadable increment. Dumbbells are per-hand."""
    if lb is None:
        return None
    return round(lb / increment) * increment

def epley_1rm(weight, reps):
    """Epley (1985): 1RM = weight * (1 + reps/30). Best for 2-10 reps."""
    if reps < 2 or reps > 12:
        log(f"  [Epley WARNING] reps={reps} outside 2-12, estimate is low confidence")
    return weight * (1 + reps / 30.0)

GOALS = {
    # goal: (pct_low, pct_high, reps, rest_sec, tempo_note, exercise_style)
    "strength": (0.85, 0.95, "3-6", 180, "controlled, full rest for max force", "compound-first"),
    "hypertrophy": (0.67, 0.85, "8-12", 90, "controlled, moderate rest", "compound + isolation"),
    "endurance": (0.50, 0.67, "15-20", 45, "controlled, short rest", "compound + isolation, higher reps"),
    "power": (0.30, 0.60, "3-5", 180, "move as fast as possible, long rest for velocity", "power variations + plyometrics"),
    "injury_prevention": (0.50, 0.67, "15-20", 60, "slow controlled tempo, stability / unilateral focus", "stability + unilateral, no max grinding"),
    "fat_loss_muscle": (0.67, 0.85, "8-12", 90, "controlled, moderate rest, plus conditioning", "compound + isolation"),
}
# alias used in sample profile
GOALS["fat_loss"] = GOALS["fat_loss_muscle"]

# Movement-pattern map for avoid_movements (POC subset).
# "avoid overhead" must remove more than one exercise name — it removes
# every exercise tagged with that pattern. New patterns can be added
# without changing the core agent logic.
AVOID_MOVEMENT_MAP = {
    "overhead": ["Overhead Press", "Dumbbell Shoulder Press", "Incline Bench Press",
                 "Incline Dumbbell Press", "Overhead Tricep Extension", "Machine Shoulder Press"],
    "jumping": ["Box Jump"],
    "deep_knee_flexion": ["Front Squat"],
    "twisting": ["Russian Twist"],
    "spinal_loading": ["Conventional Deadlift", "Good Morning"],
}

SPLITS = {
    2: ["Full Body A", "Full Body B"],
    3: ["Full Body A", "Upper", "Lower"],
    4: ["Upper", "Lower", "Upper", "Lower"],
    5: ["Push", "Pull", "Legs", "Upper", "Lower"],
    6: ["Push", "Pull", "Legs", "Push", "Pull", "Legs"],
}

# Day -> primary muscles the day must cover (POC version, simplified)
DAY_MUSCLES = {
    "Upper": ["chest", "back", "shoulders", "biceps", "triceps"],
    "Lower": ["quads", "hamstrings", "glutes", "calves"],
    "Full Body A": ["chest", "back", "quads", "glutes"],
    "Full Body B": ["shoulders", "back", "hamstrings", "glutes"],
    "Push": ["chest", "shoulders", "triceps"],
    "Pull": ["back", "biceps"],
    "Legs": ["quads", "hamstrings", "glutes", "calves"],
}

def main(profile_path, exercises_path):
    TRACE.clear()
    profile = json.loads(Path(profile_path).read_text())
    log(f"=== Workout split agent — POC ===")
    log(f"Profile: {profile['name']}")
    log(f"Level: {profile['level']}, sex: {profile['sex']}, age: {profile['age']}, "
        f"bodyweight: {profile['bodyweight_lb']} lb, height: {profile['height_in']} in")
    log(f"Body fat %: {profile.get('body_fat_pct') or 'not given — optional, agent works without it'}")
    log(f"Primary goal: {profile['primary_goal']}, secondary: {profile.get('secondary_goal') or 'none'}")
    log(f"Days/week: {profile['days_per_week']}, minutes/session: {profile['minutes_per_session']}, "
        f"equipment: {', '.join(profile['equipment'])}")
    # --- Tailoring / user control (structured + open) ---
    log(f"Active rest: at least {profile.get('min_active_rest_days', 0)} days, "
        f"preferred: {', '.join(profile.get('active_rest_days_preferred', [])) or 'none given'}")
    log(f"Include list: {profile.get('include_list') or 'none'} | "
        f"Disliked: {profile.get('disliked_exercises') or 'none'} | "
        f"Avoid movements: {profile.get('avoid_movements') or 'none'} | "
        f"Injuries: {profile.get('injuries') or 'none'}")
    cp = profile.get("cardio_preference") or {}
    if cp:
        log(f"Cardio substitution: disliked {cp.get('disliked')} -> preferred {cp.get('preferred')} "
            f"(same duration / intensity zone, trace shows the swap)")
    if profile.get("free_text_preferences"):
        log(f"Free-text preferences (open, not on the fixed list): {profile['free_text_preferences']}")
        log("  Unhandled preference: free text is retained but not parsed or enforced in Week 1.")
    if profile.get("injuries"):
        log("  WARNING: injuries are not interpreted; use explicit supported movement restrictions.")
    log("")

    # --- 1RM: known, else Epley from recent set ---
    one_rm = dict(profile.get("known_1rm_lb") or {})
    for s in profile.get("recent_sets", []):
        lift = s["lift"]
        if lift in one_rm:
            log(f"1RM {lift}: known directly = {one_rm[lift]} lb (no Epley needed)")
            continue
        est = epley_1rm(s["weight_lb"], s["reps"])
        one_rm[lift] = round(est, 1)
        log(f"1RM {lift}: Epley from {s['weight_lb']} lb x {s['reps']} reps "
            f"= {s['weight_lb']} * (1 + {s['reps']}/30) = {est:.1f} lb")
    if not one_rm:
        # Fallback: user does not know their starting lifts.
        # Use conservative beginner female standards as a *calibration*
        # estimate only, flagged low confidence. First week is RPE check,
        # feedback corrects it fast. Ratios are 1RM / bodyweight.
        bw = profile["bodyweight_lb"]
        fallback = {"squat": 0.50, "bench": 0.30, "deadlift": 0.65,
                    "ohp": 0.25, "row": 0.40, "hip_thrust": 0.75}
        log("No known 1RM and no recent sets given — using conservative beginner")
        log("standards as a CALIBRATION estimate only (low confidence, first week is RPE check):")
        for lift, ratio in fallback.items():
            one_rm[lift] = round(bw * ratio, 1)
            log(f"  1RM {lift}: estimated {bw} lb bodyweight x {ratio} = {one_rm[lift]} lb (beginner standard, NOT your actual lift)")
        log("  -> Agent must NOT present these as your real lifts. Feedback after week 1 replaces them.")
    log(f"Estimated 1RMs: {one_rm}")
    log("")

    # --- Goal mapping ---
    goal_key = profile["primary_goal"]
    if goal_key not in GOALS:
        log(f"ERROR: unknown goal '{goal_key}', known goals: {sorted(GOALS)}")
        sys.exit(1)
    pct_low, pct_high, reps, rest, tempo, style = GOALS[goal_key]
    pct_mid = (pct_low + pct_high) / 2
    log(f"Goal mapping [{goal_key}]: {pct_low*100:.0f}-{pct_high*100:.0f}% of 1RM, "
        f"{reps} reps, {rest}s rest, tempo: {tempo}, style: {style}")
    log(f"Using midpoint {pct_mid*100:.1f}% for starting weights (inside the band, not at the top).")
    log("")

    # --- Exercise DB ---
    exercises = {}
    with open(exercises_path, newline="") as f:
        for row in csv.DictReader(f):
            exercises[row["name"]] = row
    log(f"Exercise DB loaded: {len(exercises)} exercises (curated POC subset)")

    # --- Split ---
    days = profile["days_per_week"]
    split = SPLITS.get(days)
    if not split:
        log(f"ERROR: no POC split template for {days} days/week")
        sys.exit(1)
    log(f"Split for {days} days/week: {' / '.join(split)}")
    log("")

    # --- Search each workout within the selected weekly split ---
    unknown_movements = set(profile.get("avoid_movements", [])) - set(AVOID_MOVEMENT_MAP)
    if unknown_movements:
        raise ValueError(f"Unsupported movement restrictions: {sorted(unknown_movements)}")
    avoided = {name for movement in profile.get("avoid_movements", [])
               for name in AVOID_MOVEMENT_MAP[movement]}

    out_days = []
    covered = set()
    total_minutes_est = 0
    for day_name in split:
        log(f"--- {day_name} ---")
        day_out = {"day": day_name, "exercises": []}
        search = plan_workout(
            exercises.values(), DAY_MUSCLES[day_name], profile["equipment"],
            profile["minutes_per_session"], rest,
            disliked=profile.get("disliked_exercises", []), avoided=avoided,
            preferred=profile.get("include_list", []),
        )
        day_out["search"] = search
        log(f"  SEARCH: {search['candidate_count']} eligible candidates; "
            f"required primary muscles: {search['required_muscles']}; "
            f"time limit: {search['time_limit_minutes']} min")
        log(f"  Objective: {search['objective']}")
        log(f"  Evaluated {search['combinations_evaluated']} combinations; "
            f"{search['feasible_combinations_at_minimum_size']} feasible at minimum size")
        log(f"  Search status: {search['status']}")
        if search["status"] == "infeasible":
            day_out["estimated_minutes"] = None
            log(f"  INFEASIBLE: {search['reason']}")
            out_days.append(day_out)
            continue
        plan = search["selected_exercises"]
        log(f"  Selected: {', '.join(plan)}")
        for ex_name in plan:
            ex = exercises.get(ex_name)
            if not ex:
                log(f"  SKIP {ex_name}: not in POC DB")
                continue
            if ex_name in profile.get("disliked_exercises", []):
                log(f"  SKIP {ex_name}: user disliked")
                continue
            avoided = set()
            for mv in profile.get("avoid_movements", []):
                avoided.update(AVOID_MOVEMENT_MAP.get(mv, []))
            if ex_name in avoided:
                log(f"  SKIP {ex_name}: avoid movement pattern {profile.get('avoid_movements')}")
                continue
            if ex["equipment"] not in profile["equipment"]:
                log(f"  SKIP {ex_name}: equipment {ex['equipment']} not available")
                continue
            covered.add(ex["primary_muscle"])
            sets = 3
            ref = ex.get("reference_lift", "")
            frac = ex.get("weight_fraction", "")
            if ref and frac and ref in one_rm:
                base = one_rm[ref] * float(frac)
                working = base * pct_mid
                # Dumbbell fractions in CSV are per-hand, so working is per-hand
                working_r = round_to_plate(working)
                unit = "lb per hand" if ex["equipment"] == "dumbbell" else "lb"
                log(f"  {ex_name}: {sets}x{reps}, {working_r} {unit} "
                    f"= {one_rm[ref]} lb {ref} 1RM x {frac} x {pct_mid:.2f} goal% -> rounded to {working_r}")
                weight_out = working_r
                weight_note = f"{one_rm[ref]} 1RM x {frac} x {pct_mid:.2f}"
            elif ex.get("level_starter_lb"):
                weight_out = float(ex["level_starter_lb"])
                weight_note = "level starter — first-session RPE check, adjust by feedback"
                log(f"  {ex_name}: {sets}x{reps}, {weight_out} lb (level starter, RPE check)")
            else:
                weight_out = None
                weight_note = "bodyweight — no added load in POC"
                log(f"  {ex_name}: {sets}x{reps}, bodyweight")
            day_out["exercises"].append({
                "name": ex_name, "primary_muscle": ex["primary_muscle"],
                "equipment": ex["equipment"], "type": ex["type"],
                "sets": sets, "reps": reps, "rest_sec": rest,
                "weight_lb": weight_out, "weight_basis": weight_note,
            })
        day_out["estimated_minutes"] = search["estimated_minutes"]
        total_minutes_est += day_out["estimated_minutes"]
        log(f"  Estimated session time: ~{day_out['estimated_minutes']} min "
            f"(target {profile['minutes_per_session']} min)")
        out_days.append(day_out)
        log("")

    # Include-list check
    all_ex = [e["name"] for d in out_days for e in d["exercises"]]
    for inc in profile.get("include_list", []):
        log(f"Include check: {inc} present in split? {inc in all_ex}")
    log(f"Muscle coverage in POC split: {sorted(covered)}")
    log(f"All major muscles covered? chest/back/shoulders/quads/hamstrings/glutes in set: "
        f"{set(['chest','back','shoulders','quads','hamstrings','glutes']).issubset(covered)}")
    feasible_days = [d for d in out_days if d["search"]["status"] == "feasible"]
    plan_status = "feasible" if len(feasible_days) == len(out_days) else "infeasible"
    log(f"Overall plan status: {plan_status}")
    if feasible_days:
        log(f"Average feasible-session time: ~{total_minutes_est / len(feasible_days):.1f} min "
            f"vs target {profile['minutes_per_session']} min")
    # Weekly calendar with active rest days, if given
    if profile.get("active_rest_days_preferred"):
        log("")
        log("Weekly calendar (illustrative placement; recovery is not validated):")
        # Map training split in order onto non-rest days, Mon-Sat + Sun rest example
        week_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        rest_days = set(profile["active_rest_days_preferred"])
        ti = 0
        for wd in week_order:
            if wd in rest_days:
                if wd == "Sunday":
                    log(f"  {wd}: ACTIVE REST — HOME ONLY, do not leave house. "
                        f"Light: mobility / yoga / light dumbbell circuit / stretching, "
                        f"20-45 min, low intensity. NO stairmaster (stairmaster is at gym). "
                        f"Home equipment only: basic dumbbells + bodyweight, RPE starters.")
                else:
                    log(f"  {wd}: ACTIVE REST — stairmaster preferred, light intensity, "
                        f"20-30 min (not a hard workout), plus mobility. Gym day, not home.")
            else:
                if ti >= len(out_days):
                    log(f"  {wd}: UNASSIGNED")
                    continue
                planned_day = out_days[ti]
                ti += 1
                log(f"  {wd}: {planned_day['day']} — {planned_day['search']['status']}, "
                    f"estimated minutes: {planned_day['estimated_minutes']}")
    log("")
    log("Progression note (Week 2, not applied in POC): if all reps completed with RPE <=8, "
        "+2.5-5 lb next week; if failed last set, -10% and re-estimate 1RM; if pain reported, "
        "stop that exercise and flag — agent does not diagnose.")
    log("=== POC complete ===")

    out = {
        "profile_name": profile["name"],
        "plan_status": plan_status,
        "estimated_1rm_lb": one_rm,
        "goal": goal_key,
        "goal_band_pct": [pct_low, pct_high],
        "reps": reps, "rest_sec": rest,
        "split": split,
        "days": out_days,
        "muscle_coverage": sorted(covered),
        "trace": TRACE,
    }
    out_path = BASE / "ai-project-workout-split-output.json"
    out_path.write_text(json.dumps(out, indent=2))
    (BASE / "ai-project-workout-split-trace.log").write_text("\n".join(TRACE))
    log(f"\nWrote {out_path} and ai-project-workout-split-trace.log")

if __name__ == "__main__":
    import sys as _sys
    prof = BASE / "ai-project-workout-split-profile.json"
    if len(_sys.argv) > 1:
        prof = Path(_sys.argv[1])
    main(prof, BASE / "ai-project-workout-split-exercises.csv")
