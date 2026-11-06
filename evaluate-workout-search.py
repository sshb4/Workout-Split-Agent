"""Repeatable checks and retained evidence for the Week 1 search planner.

Run: python3 evaluate-workout-search.py
"""
import csv
import json
from pathlib import Path

from workout_planner import plan_workout

BASE = Path(__file__).parent


def main():
    with (BASE / 'ai-project-workout-split-exercises.csv').open(newline='') as f:
        exercises = list(csv.DictReader(f))
    cases = [
        dict(name='dumbbells_30_minutes', equipment=['dumbbell'], minutes=30,
             required=['chest', 'back', 'shoulders'], disliked=['Dumbbell Fly'],
             avoided=['Dumbbell Shoulder Press'], preferred=['Dumbbell Row'],
             expected='feasible'),
        dict(name='insufficient_time', equipment=['dumbbell'], minutes=15,
             required=['chest', 'back', 'shoulders'], expected='infeasible'),
        dict(name='missing_equipment_for_primary_coverage', equipment=['bodyweight'],
             minutes=45, required=['chest', 'back', 'shoulders'], expected='infeasible'),
    ]
    evidence = []
    for case in cases:
        result = plan_workout(exercises, case['required'], case['equipment'],
                              case['minutes'], 90, case.get('disliked', []),
                              case.get('avoided', []), case.get('preferred', []))
        assert result['status'] == case['expected'], case['name']
        if result['status'] == 'feasible':
            selected = [ex for ex in exercises if ex['name'] in result['selected_exercises']]
            assert set(case['required']) <= {ex['primary_muscle'] for ex in selected}
            assert all(ex['equipment'] in case['equipment'] for ex in selected)
            assert not set(result['selected_exercises']) & set(case['disliked'] + case['avoided'])
            assert result['estimated_minutes'] <= case['minutes']
            assert 'Dumbbell Row' in result['selected_exercises']
            assert len(selected) == 3  # Primary-only coverage has a lower bound of three.
            assert result == plan_workout(list(reversed(exercises)), case['required'],
                                          case['equipment'], case['minutes'], 90,
                                          case['disliked'], case['avoided'], case['preferred'])
        else:
            assert result['selected_exercises'] == []
            assert result['reason']
        evidence.append(dict(input=case, result=result, checks='passed'))
        print(f"PASS {case['name']}: {result['status']}")

    # Tiny independent search oracle: preference outranks compound count.
    toy = [dict(name=name, primary_muscle=muscle, equipment='dumbbell', type=kind)
           for name, muscle, kind in [('A', 'chest', 'compound'),
                                      ('B', 'chest', 'isolation'),
                                      ('C', 'back', 'compound')]]
    result = plan_workout(toy, ['chest', 'back'], ['dumbbell'], 15, 90, preferred=['B'])
    assert result['selected_exercises'] == ['B', 'C']
    assert result['combinations_evaluated'] == 3
    assert result['feasible_combinations_at_minimum_size'] == 2
    evidence.append(dict(input=dict(name='objective_oracle', exercises=toy,
                                    required=['chest', 'back'], equipment=['dumbbell'],
                                    minutes=15, rest_sec=90, preferred=['B']),
                         result=result, checks='passed'))
    print('PASS objective_oracle: preferred feasible combination selected')
    path = BASE / 'ai-project-workout-split-search-evidence.json'
    path.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'Wrote {path.name}')


if __name__ == '__main__':
    main()
