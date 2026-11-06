"""Exhaustive constraint search for a small, curated exercise database."""

from itertools import combinations


def plan_workout(exercises, required_muscles, equipment, minutes, rest_sec,
                 disliked=(), avoided=(), preferred=()):
    """Minimize exercise count, then favor preferences and compound exercises.

    Coverage counts primary muscles only. Each exercise has three sets and
    costs 3 * (one minute of work + goal-specific rest). This is a planning
    estimate, excluding warm-up, transitions, and differences in rep duration.
    Exhaust all combinations at the smallest feasible size; names break ties.
    """
    required = set(required_muscles)
    available = set(equipment)
    excluded = set(disliked) | set(avoided)
    preferred = set(preferred)
    candidates = sorted(
        (ex for ex in exercises
         if ex['equipment'] in available
         and ex['name'] not in excluded
         and ex['primary_muscle'] in required),
        key=lambda ex: ex['name'],
    )
    exercise_minutes = 3 * (1 + rest_sec / 60)
    result = {
        'strategy': 'exhaustive constraint search',
        'required_muscles': sorted(required),
        'coverage_rule': 'at least one exercise per required primary muscle',
        'time_limit_minutes': minutes,
        'minutes_per_exercise': exercise_minutes,
        'candidate_count': len(candidates),
        'combinations_evaluated': 0,
        'feasible_combinations_at_minimum_size': 0,
        'objective': 'minimize exercise count; maximize preferred exercises; '
                     'maximize compound exercises; break ties by exercise names',
        'selected_exercises': [],
    }
    missing = required - {ex['primary_muscle'] for ex in candidates}
    if missing:
        return dict(result, status='infeasible',
                    reason='No eligible exercise for: ' + ', '.join(sorted(missing)))
    # Primary-only coverage needs at least one exercise per required muscle.
    max_count = min(len(candidates), int(minutes // exercise_minutes))
    if max_count < len(required):
        return dict(result, status='infeasible',
                    reason=f'Coverage requires at least {len(required)} exercises '
                           f'({len(required) * exercise_minutes:g} estimated minutes); '
                           f'time limit is {minutes:g} minutes.')
    for count in range(len(required), max_count + 1):
        best = None
        best_key = None
        for choice in combinations(candidates, count):
            result['combinations_evaluated'] += 1
            if not required.issubset({ex['primary_muscle'] for ex in choice}):
                continue
            result['feasible_combinations_at_minimum_size'] += 1
            key = (
                -sum(ex['name'] in preferred for ex in choice),
                -sum(ex['type'] == 'compound' for ex in choice),
                tuple(ex['name'] for ex in choice),
            )
            if best_key is None or key < best_key:
                best, best_key = choice, key
        if best is not None:
            return dict(result, status='feasible',
                        selected_exercises=[ex['name'] for ex in best],
                        estimated_minutes=count * exercise_minutes,
                        preferred_exercises_selected=-best_key[0],
                        compound_exercises_selected=-best_key[1])
    return dict(result, status='infeasible', reason='No feasible combination found.')
