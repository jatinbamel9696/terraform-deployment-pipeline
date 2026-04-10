#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from collections import defaultdict, deque

SHA_RE = re.compile(r'^[0-9a-f]{7,40}$')


def validate_sha(sha):
    if sha != 'all' and not SHA_RE.match(sha):
        raise ValueError(f"Invalid SHA: {sha!r}")


def get_changed_files(sha1, sha2):
    result = subprocess.run(
        ['git', 'diff', '--name-only', sha1, sha2],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git diff failed: {result.stderr}")
    return result.stdout.strip().split('\n')


def load_include():
    with open('include.txt', 'r') as f:
        lines = f.read().strip().split('\n')
    return [
        line.split('/')[1]
        for line in lines
        if line.startswith('stacks/') and line.endswith('/**')
    ]


def load_dependencies():
    with open('dependencies.json', 'r') as f:
        return json.load(f)


def load_regions():
    with open('regions.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]


def get_affected_stacks(changed_files, allowed_stacks):
    affected = set()
    for file in changed_files:
        for stack in allowed_stacks:
            if file.startswith(f'stacks/{stack}/'):
                affected.add(stack)
    return affected


def get_all_affected_stacks(affected, deps):
    reverse_deps = defaultdict(list)
    for stack, deps_list in deps.items():
        for dep in deps_list:
            reverse_deps[dep].append(stack)

    queue = deque(affected)
    visited = set(affected)
    while queue:
        current = queue.popleft()
        for dependent in reverse_deps.get(current, []):
            if dependent not in visited:
                visited.add(dependent)
                queue.append(dependent)
    return visited


def build_stages(stacks, deps):
    in_degree = {stack: 0 for stack in stacks}
    for stack in stacks:
        for dep in deps.get(stack, []):
            if dep in stacks:
                in_degree[stack] += 1

    queue = deque([s for s in stacks if in_degree[s] == 0])
    stages = []
    while queue:
        current_stage = []
        for _ in range(len(queue)):
            stack = queue.popleft()
            current_stage.append(stack)
            for dependent in deps:
                if stack in deps[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        if current_stage:
            stages.append(current_stage)
    return stages


def main():
    if len(sys.argv) != 3:
        print("Usage: python generate_matrix.py <sha1> <sha2>", file=sys.stderr)
        sys.exit(1)

    sha1, sha2 = sys.argv[1], sys.argv[2]
    validate_sha(sha1)
    validate_sha(sha2)

    allowed_stacks = load_include()
    deps = load_dependencies()
    regions = load_regions()

    if sha1 == 'all':
        all_affected = set(allowed_stacks)
    else:
        changed_files = get_changed_files(sha1, sha2)
        affected = get_affected_stacks(changed_files, allowed_stacks)
        all_affected = get_all_affected_stacks(affected, deps)

    if not all_affected:
        print(json.dumps({"flat": [], "regions": [], "stages": []}))
        return

    stages = build_stages(list(all_affected), deps)

    print(json.dumps({
        "flat": [
            {"stack": stack, "region": region}
            for stage in stages
            for stack in stage
            for region in regions
        ],
        "regions": [
            {"region": region, "stacks": [s for stage in stages for s in stage]}
            for region in regions
        ],
        "stages": [
            {"region": region, "stacks": stage_stacks, "stage": i + 1}
            for region in regions
            for i, stage_stacks in enumerate(stages)
        ]
    }))


if __name__ == "__main__":
    main()
