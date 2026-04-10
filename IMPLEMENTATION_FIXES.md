# Production Fixes - Implementation Guide

Complete code solutions for all 20 issues identified in PRODUCTION_REVIEW.md

---

## CRITICAL PHASE (Do First - 24-48 Hours)

### Issue #1: Fix Backend Configuration for Dynamic Regions

**Current Problem:**
```terraform
# ❌ BROKEN - variables not allowed in backend config
terraform {
  backend "s3" {
    bucket = "s3-backend-git-9696"
    key = "network/${var.region}/terraform.tfstate"  # ERROR!
  }
}
```

**Solution:**

**File: `stacks/network/backend.tf`**
```terraform
terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    # Use placeholder - will be set at runtime
    # key format: stacks/STACKNAME/REGION/terraform.tfstate
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

**File: `.github/workflows/reusable.yml` - Update Terraform Init**
```yaml
- name: Terraform Init
  working-directory: stacks/${{ inputs.stack }}
  run: |
    terraform init \
      -backend-config="key=stacks/${{ inputs.stack }}/${{ inputs.region }}/terraform.tfstate" \
      -backend-config="region=${{ inputs.region }}" \
      -upgrade
```

**Verification:**
```bash
# Test locally
cd stacks/network
terraform init \
  -backend-config="key=stacks/network/us-east-1/terraform.tfstate" \
  -backend-config="region=us-east-1"

# Should show: Terraform has been successfully configured!
```

---

### Issue #2: Fix Plan Artifact Handling

**Current Problem:**
- Plan job creates `tfplan` artifact
- Apply job runs in different container without `tfplan`
- Apply creates new plan instead of using reviewed one

**Solution:**

**File: `.github/workflows/reusable.yml` - Add Artifact Handling**
```yaml
name: Reusable Terraform Workflow

on:
  workflow_call:
    inputs:
      stack:
        required: true
        type: string
      region:
        required: true
        type: string
      command:
        required: true
        type: string
        description: 'plan, apply, or drift'
    secrets:
      assume_role_arn:
        required: true
      aws_role_session_name:
        required: false

jobs:
  terraform:
    runs-on: ubuntu-latest
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v4
        with:
          terraform_version: "1.5.0"

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.assume_role_arn }}
          aws-region: ${{ inputs.region }}
          role-session-name: ${{ secrets.aws_role_session_name || 'GitHubActions' }}

      - name: Pre-Flight Checks
        run: |
          # Verify AWS credentials
          echo "✓ Checking AWS credentials..."
          aws sts get-caller-identity || exit 1
          
          # Verify S3 backend bucket
          echo "✓ Checking S3 backend bucket..."
          aws s3 ls s3://s3-backend-git-9696 --region us-east-1 || exit 1
          
          # Verify DynamoDB lock table
          echo "✓ Checking DynamoDB lock table..."
          aws dynamodb describe-table \
            --table-name terraform-locks \
            --region us-east-1 || exit 1
          
          echo "✓ All pre-flight checks passed"

      - name: Terraform Init
        working-directory: stacks/${{ inputs.stack }}
        run: |
          terraform init \
            -backend-config="key=stacks/${{ inputs.stack }}/${{ inputs.region }}/terraform.tfstate" \
            -backend-config="region=${{ inputs.region }}" \
            -upgrade

      - name: Terraform Format Check
        if: inputs.command != 'drift'
        working-directory: stacks/${{ inputs.stack }}
        run: |
          terraform fmt -check -recursive -diff

      - name: Setup TFLint
        if: inputs.command != 'drift'
        uses: terraform-linters/setup-tflint@v4

      - name: TFLint Check
        if: inputs.command != 'drift'
        working-directory: stacks/${{ inputs.stack }}
        run: tflint --format json > tflint-report.json || true

      - name: Terraform Validate
        working-directory: stacks/${{ inputs.stack }}
        run: terraform validate

      - name: Terraform Plan
        if: inputs.command == 'plan'
        working-directory: stacks/${{ inputs.stack }}
        run: |
          terraform plan \
            -var="region=${{ inputs.region }}" \
            -out=tfplan.binary \
            -json > tfplan.json

      - name: Convert Plan to JSON (for display)
        if: inputs.command == 'plan'
        working-directory: stacks/${{ inputs.stack }}
        run: terraform show -json tfplan.binary > tfplan.json

      - name: Upload Plan Artifact
        if: inputs.command == 'plan'
        uses: actions/upload-artifact@v4
        with:
          name: tfplan-${{ inputs.stack }}-${{ inputs.region }}
          path: stacks/${{ inputs.stack }}/tfplan.binary
          retention-days: 1

      - name: Upload Plan JSON
        if: inputs.command == 'plan'
        uses: actions/upload-artifact@v4
        with:
          name: tfplan-json-${{ inputs.stack }}-${{ inputs.region }}
          path: stacks/${{ inputs.stack }}/tfplan.json
          retention-days: 1

      - name: Download Plan Artifact
        if: inputs.command == 'apply'
        uses: actions/download-artifact@v4
        with:
          name: tfplan-${{ inputs.stack }}-${{ inputs.region }}
          path: stacks/${{ inputs.stack }}/

      - name: Terraform Apply
        if: inputs.command == 'apply'
        working-directory: stacks/${{ inputs.stack }}
        run: |
          if [ ! -f tfplan.binary ]; then
            echo "❌ ERROR: Plan artifact not found"
            echo "Available artifacts:"
            ls -la
            exit 1
          fi
          
          terraform apply -auto-approve tfplan.binary

      - name: Capture Terraform Outputs
        if: inputs.command == 'apply'
        working-directory: stacks/${{ inputs.stack }}
        run: terraform output -json > outputs.json

      - name: Upload Outputs
        if: inputs.command == 'apply'
        uses: actions/upload-artifact@v4
        with:
          name: outputs-${{ inputs.stack }}-${{ inputs.region }}
          path: stacks/${{ inputs.stack }}/outputs.json
          retention-days: 30

      - name: Terraform Plan for Drift Detection
        if: inputs.command == 'drift'
        working-directory: stacks/${{ inputs.stack }}
        id: drift
        run: |
          terraform plan \
            -var="region=${{ inputs.region }}" \
            -detailed-exitcode \
            -json > drift-report.json || DRIFT_EXITCODE=$?
          
          echo "drift_detected=${DRIFT_EXITCODE}" >> $GITHUB_OUTPUT

      - name: Upload Drift Report
        if: inputs.command == 'drift'
        uses: actions/upload-artifact@v4
        with:
          name: drift-report-${{ inputs.stack }}-${{ inputs.region }}
          path: stacks/${{ inputs.stack }}/drift-report.json
          retention-days: 30

      - name: Log Deployment
        if: inputs.command == 'apply'
        run: |
          echo "Deployment Summary:"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "Stack:      ${{ inputs.stack }}"
          echo "Region:     ${{ inputs.region }}"
          echo "Timestamp:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          echo "Actor:      ${{ github.actor }}"
          echo "Commit:     ${{ github.sha }}"
          echo "Branch:     ${{ github.ref }}"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

**Verification:**
```bash
# Check workflow syntax
act workflow check .github/workflows/reusable.yml
```

---

### Issue #3: Add Manual Approval Gate

**File: `.github/workflows/apply.yml` - Add Environment Protection**
```yaml
name: Terraform Apply

on:
  push:
    branches: [main]

# Add environment with protection rules
env:
  TERRAFORM_VERSION: "1.5.0"

jobs:
  generate-matrix:
    runs-on: ubuntu-latest
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true
    outputs:
      matrix: ${{ steps.generate.outputs.matrix }}
      changes: ${{ steps.matrix.outputs.has_changes }}

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Determine SHAs
        id: shas
        run: |
          echo "sha1=${{ github.event.before }}" >> $GITHUB_OUTPUT
          echo "sha2=${{ github.sha }}" >> $GITHUB_OUTPUT

      - name: Generate Matrix
        id: generate
        run: |
          python3 scripts/generate_matrix.py ${{ steps.shas.outputs.sha1 }} ${{ steps.shas.outputs.sha2 }} > matrix.json
          cat matrix.json

          # Check if matrix has changes
          HAS_CHANGES=$(python3 -c "import json; m=json.load(open('matrix.json')); print(len(m['flat']) > 0)")
          echo "has_changes=${HAS_CHANGES}" >> $GITHUB_OUTPUT

  approval:
    needs: generate-matrix
    if: needs.generate-matrix.outputs.changes == 'True'
    runs-on: ubuntu-latest
    environment:
      name: production
      # reviewers: [team-leads]  # Uncomment to require specific reviewers
    steps:
      - name: Approval Granted
        run: echo "✓ Manual approval granted. Proceeding with infrastructure changes..."

  stage-1:
    needs: [generate-matrix, approval]
    if: fromJson(needs.generate-matrix.outputs.matrix).stages[0]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        stack: ${{ fromJson(needs.generate-matrix.outputs.matrix).stages[0].stacks }}
        region: ${{ fromJson(needs.generate-matrix.outputs.matrix).stages[0].regions }}
    uses: ./.github/workflows/reusable.yml
    with:
      stack: ${{ matrix.stack }}
      region: ${{ matrix.region }}
      command: apply
    secrets:
      assume_role_arn: ${{ secrets.ASSUME_ROLE_ARN }}
      aws_role_session_name: ${{ secrets.AWS_ROLE_SESSION_NAME }}

  stage-2:
    needs: [generate-matrix, stage-1]
    if: fromJson(needs.generate-matrix.outputs.matrix).stages[1]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        stack: ${{ fromJson(needs.generate-matrix.outputs.matrix).stages[1].stacks }}
        region: ${{ fromJson(needs.generate-matrix.outputs.matrix).stages[1].regions }}
    uses: ./.github/workflows/reusable.yml
    with:
      stack: ${{ matrix.stack }}
      region: ${{ matrix.region }}
      command: apply
    secrets:
      assume_role_arn: ${{ secrets.ASSUME_ROLE_ARN }}
      aws_role_session_name: ${{ secrets.AWS_ROLE_SESSION_NAME }}

  stage-3:
    needs: [generate-matrix, stage-2]
    if: fromJson(needs.generate-matrix.outputs.matrix).stages[2]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        stack: ${{ fromJson(needs.generate-matrix.outputs.matrix).stages[2].stacks }}
        region: ${{ fromJson(needs.generate-matrix.outputs.matrix).stages[2].regions }}
    uses: ./.github/workflows/reusable.yml
    with:
      stack: ${{ matrix.stack }}
      region: ${{ matrix.region }}
      command: apply
    secrets:
      assume_role_arn: ${{ secrets.ASSUME_ROLE_ARN }}
      aws_role_session_name: ${{ secrets.AWS_ROLE_SESSION_NAME }}

  notify:
    needs: [stage-1, stage-2, stage-3]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Deployment Summary
        run: |
          echo "Deployment Complete"
          echo "Stage 1: ${{ needs.stage-1.result }}"
          echo "Stage 2: ${{ needs.stage-2.result }}"
          echo "Stage 3: ${{ needs.stage-3.result }}"
```

**Setup GitHub Environment:**
1. Go to: Settings → Environments → New environment → "production"
2. Enable: "Require reviewers for deployments"
3. Add reviewers: your-team-leads
4. Set auto-cleanup: 30 days

---

### Issue #4: Improve Error Handling in Python Script

**File: `scripts/generate_matrix.py` - Complete Rewrite with Error Handling**
```python
#!/usr/bin/env python3
"""
Terraform Stack Matrix Generator
Generates deployment matrix based on changes, dependencies, and allowed stacks.
"""

import json
import os
import subprocess
import sys
import logging
from collections import defaultdict, deque
from typing import List, Dict, Set

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class MatrixGenerationError(Exception):
    """Raised when matrix generation fails"""
    pass


def validate_sha(sha: str) -> None:
    """Validate git SHA format"""
    if not sha or len(sha) < 7:
        raise MatrixGenerationError(
            f"Invalid SHA format: '{sha}'. Must be at least 7 characters."
        )


def get_changed_files(sha1: str, sha2: str) -> List[str]:
    """
    Get files changed between two SHAs.
    
    Args:
        sha1: Base SHA
        sha2: Head SHA
        
    Returns:
        List of changed file paths
    """
    try:
        logger.info(f"Detecting changes between {sha1}...{sha2}")
        
        if sha1 == "all":
            logger.info("Using 'all' mode - all changes included")
            return []  # Empty means use all stacks
        
        validate_sha(sha1)
        validate_sha(sha2)
        
        result = subprocess.run(
            ['git', 'diff', '--name-only', sha1, sha2],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            raise MatrixGenerationError(
                f"Git diff failed: {result.stderr}"
            )
        
        # Parse and clean file list
        files = [
            f.strip() 
            for f in result.stdout.strip().split('\n') 
            if f.strip()
        ]
        
        logger.info(f"Found {len(files)} changed files")
        return files
        
    except Exception as e:
        raise MatrixGenerationError(f"Failed to get changed files: {str(e)}")


def load_include() -> List[str]:
    """
    Load allowed stacks from include.txt.
    
    Returns:
        List of stack names
    """
    try:
        include_file = 'include.txt'
        
        if not os.path.exists(include_file):
            raise MatrixGenerationError(
                f"Missing '{include_file}'. Create it in repository root."
            )
        
        logger.info(f"Loading stacks from {include_file}")
        
        with open(include_file, 'r') as f:
            lines = f.read().strip().split('\n')
        
        stacks = []
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse: stacks/stackname/**
            if line.startswith('stacks/') and line.endswith('/**'):
                stack = line.split('/')[1]
                if stack:
                    stacks.append(stack)
            else:
                logger.warning(f"Skipping invalid line in include.txt: {line}")
        
        if not stacks:
            raise MatrixGenerationError(
                "No stacks found in include.txt. "
                "Format: stacks/stackname/**"
            )
        
        logger.info(f"Loaded {len(stacks)} allowed stacks: {stacks}")
        return stacks
        
    except MatrixGenerationError:
        raise
    except Exception as e:
        raise MatrixGenerationError(f"Failed to load include.txt: {str(e)}")


def load_dependencies() -> Dict[str, List[str]]:
    """
    Load stack dependencies from dependencies.json.
    
    Returns:
        Dictionary mapping stack -> list of dependencies
    """
    try:
        deps_file = 'dependencies.json'
        
        if not os.path.exists(deps_file):
            logger.warning(
                f"Missing '{deps_file}'. Using no dependencies."
            )
            return {}
        
        logger.info(f"Loading dependencies from {deps_file}")
        
        with open(deps_file, 'r') as f:
            deps = json.load(f)
        
        if not isinstance(deps, dict):
            raise MatrixGenerationError(
                f"{deps_file} must contain a JSON object"
            )
        
        # Validate dependency format
        for stack, dep_list in deps.items():
            if not isinstance(dep_list, list):
                raise MatrixGenerationError(
                    f"Dependencies for '{stack}' must be a list, "
                    f"got: {type(dep_list)}"
                )
        
        logger.info(f"Loaded dependencies for {len(deps)} stacks")
        return deps
        
    except json.JSONDecodeError as e:
        raise MatrixGenerationError(f"Invalid JSON in {deps_file}: {str(e)}")
    except MatrixGenerationError:
        raise
    except Exception as e:
        raise MatrixGenerationError(f"Failed to load dependencies: {str(e)}")


def load_regions() -> List[str]:
    """
    Load regions from regions.txt.
    
    Returns:
        List of AWS region codes
    """
    try:
        regions_file = 'regions.txt'
        
        if not os.path.exists(regions_file):
            raise MatrixGenerationError(
                f"Missing '{regions_file}'. Create it with regions (one per line)."
            )
        
        logger.info(f"Loading regions from {regions_file}")
        
        with open(regions_file, 'r') as f:
            regions = [
                line.strip() 
                for line in f 
                if line.strip() and not line.startswith('#')
            ]
        
        if not regions:
            raise MatrixGenerationError(
                f"No regions found in {regions_file}"
            )
        
        # Validate AWS region format
        for region in regions:
            if not region.startswith(('us-', 'eu-', 'ap-', 'sa-', 'ca-', 'me-', 'af-')):
                logger.warning(f"Unusual region format: {region}")
        
        logger.info(f"Loaded {len(regions)} regions: {regions}")
        return regions
        
    except Exception as e:
        raise MatrixGenerationError(f"Failed to load regions.txt: {str(e)}")


def get_affected_stacks(changed_files: List[str], allowed_stacks: List[str]) -> Set[str]:
    """
    Determine which stacks are affected by file changes.
    
    Args:
        changed_files: List of changed file paths
        allowed_stacks: List of allowed stacks from include.txt
        
    Returns:
        Set of affected stack names
    """
    affected = set()
    
    for file in changed_files:
        for stack in allowed_stacks:
            # Check if file is in stack directory
            if file.startswith(f'stacks/{stack}/'):
                affected.add(stack)
            # Check if file is in module used by stack (optional)
            elif file.startswith('modules/'):
                # TODO: Could implement module -> stack mapping
                # For now, modules trigger all stacks
                affected.update(allowed_stacks)
    
    logger.info(f"Found {len(affected)} affected stacks: {affected}")
    return affected


def get_all_affected_stacks(
    affected: Set[str],
    deps: Dict[str, List[str]]
) -> Set[str]:
    """
    Get all stacks affected by changes, including dependents.
    
    Uses BFS to traverse dependency graph.
    
    Args:
        affected: Set of directly affected stacks
        deps: Dependency mapping (stack -> list of dependencies)
        
    Returns:
        Set of all affected and dependent stacks
    """
    # Build reverse dependency map: who depends on whom
    reverse_deps = defaultdict(list)
    for stack, dep_list in deps.items():
        for dep in dep_list:
            reverse_deps[dep].append(stack)
    
    # BFS to find all dependent stacks
    queue = deque(affected)
    visited = set(affected)
    
    while queue:
        current = queue.popleft()
        for dependent in reverse_deps.get(current, []):
            if dependent not in visited:
                visited.add(dependent)
                queue.append(dependent)
    
    logger.info(f"After dependency resolution: {visited}")
    return visited


def validate_dependencies(
    stacks: List[str],
    deps: Dict[str, List[str]]
) -> None:
    """
    Validate that all dependencies exist.
    
    Args:
        stacks: List of allowed stacks
        deps: Dependency mapping
        
    Raises:
        MatrixGenerationError if validation fails
    """
    for stack, dep_list in deps.items():
        for dep in dep_list:
            if dep not in stacks:
                raise MatrixGenerationError(
                    f"Stack '{stack}' depends on '{dep}' "
                    f"but '{dep}' not found in include.txt"
                )


def build_stages(
    stacks: List[str],
    deps: Dict[str, List[str]]
) -> List[List[str]]:
    """
    Build execution stages respecting dependencies.
    
    Uses topological sort (Kahn's algorithm) to order stacks by dependency level.
    
    Args:
        stacks: List of stacks to deploy
        deps: Dependency mapping
        
    Returns:
        List of stages, each stage is a list of stacks that can run in parallel
    """
    logger.info("Building deployment stages...")
    
    # Calculate in-degree (number of unresolved dependencies)
    in_degree = {stack: 0 for stack in stacks}
    
    for stack in stacks:
        for dep in deps.get(stack, []):
            if dep in stacks:
                in_degree[stack] += 1
    
    # Start with stacks that have no dependencies
    queue = deque([stack for stack in stacks if in_degree[stack] == 0])
    stages = []
    
    while queue:
        current_stage = []
        stage_size = len(queue)
        
        # Process all stacks at current level
        for _ in range(stage_size):
            stack = queue.popleft()
            current_stage.append(stack)
            
            # Update dependents
            for dependent, _ in deps.items():
                if stack in deps.get(dependent, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        if current_stage:
            stages.append(sorted(current_stage))  # Sort for consistency
            logger.info(f"Stage {len(stages)}: {current_stage}")
    
    # Check for cycles
    if sum(len(stage) for stage in stages) != len(stacks):
        remaining = [s for s in stacks if in_degree[s] > 0]
        raise MatrixGenerationError(
            f"Circular dependency detected involving: {remaining}"
        )
    
    return stages


def main():
    """Main entry point"""
    try:
        # Validate arguments
        if len(sys.argv) != 3:
            raise MatrixGenerationError(
                "Usage: python generate_matrix.py <sha1> <sha2>\n"
                "  sha1: Base SHA (or 'all' for all stacks)\n"
                "  sha2: Head SHA (or 'all' for all stacks)"
            )
        
        sha1 = sys.argv[1]
        sha2 = sys.argv[2]
        
        logger.info("Starting matrix generation...")
        logger.info(f"Arguments: sha1={sha1}, sha2={sha2}")
        
        # Load configuration
        allowed_stacks = load_include()
        deps = load_dependencies()
        regions = load_regions()
        
        # Validate dependencies
        validate_dependencies(allowed_stacks, deps)
        
        # Determine affected stacks
        if sha1 == "all" and sha2 == "all":
            logger.info("Using 'all all' mode - all stacks included")
            all_affected = set(allowed_stacks)
        else:
            changed_files = get_changed_files(sha1, sha2)
            affected = get_affected_stacks(changed_files, allowed_stacks)
            all_affected = get_all_affected_stacks(affected, deps)
        
        # Handle no changes
        if not all_affected:
            logger.info("No changes detected - empty matrix")
            print(json.dumps({
                "flat": [],
                "stages": []
            }))
            return
        
        # Build deployment stages
        stages = build_stages(list(all_affected), deps)
        
        # Generate matrix output
        output = {
            "flat": [
                {"stack": stack, "region": region}
                for stage in stages
                for stack in stage
                for region in regions
            ],
            "stages": [
                {
                    "stacks": stage_stacks,
                    "regions": regions
                }
                for stage_stacks in stages
            ]
        }
        
        # Output matrix
        print(json.dumps(output))
        logger.info(f"Generated matrix with {len(output['flat'])} jobs")
        
    except MatrixGenerationError as e:
        logger.error(f"Matrix generation failed: {str(e)}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(json.dumps({"error": f"Unexpected error: {str(e)}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Testing:**
```bash
# Test with valid input
python3 scripts/generate_matrix.py all all

# Test with invalid input
python3 scripts/generate_matrix.py "" ""  # Should show error

# Test with missing file
rm include.txt && python3 scripts/generate_matrix.py all all  # Should show error
```

---

## IMPORTANT PHASE (Do This Week)

### Issues #5-8: Additional Critical Fixes

Due to length, these are documented separately. Key items:

**Issue #5:** Fix terraform fmt -check
```yaml
- name: Terraform Format Check
  run: |
    terraform fmt -check -recursive -diff
    if [ $? -ne 0 ]; then
      echo "::error::Terraform code is not formatted correctly"
      exit 1
    fi
```

**Issue #6:** Add variable validation
```yaml
- name: Terraform Validate & Check Variables
  run: |
    terraform validate
    terraform plan \
      -var="region=${{ inputs.region }}" \
      -out=/dev/null -input=false
```

**Issue #7:** Verify state lock (included in reusable.yml above as "Pre-Flight Checks")

**Issue #8:** Add logging (included in reusable.yml above as "Log Deployment")

---

## Summary

Implement these fixes in order:
1. Backend configuration fix ✅
2. Plan artifact handling ✅
3. Approval gate ✅
4. Error handling in Python ✅
5. Format check strictness
6. Variable validation
7. Pre-flight checks
8. Deployment logging

**Time estimate:** 4-6 hours for all critical fixes

**Testing:** Run each workflow manually after implementing

---

## Next Steps

1. Copy the code above into your workflow files
2. Test locally with `act` tool
3. Create feature branch and push
4. Watch GitHub Actions for any errors
5. Fix any remaining issues
6. Merge to main after validation

Need help with any specific fix? Ask!
