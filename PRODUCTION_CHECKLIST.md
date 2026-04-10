# Production Readiness Checklist

**Project:** Terraform Deployment Pipeline  
**Current Score:** 4.8/10 ⚠️  
**Target Score:** 8.0+/10 ✅  
**Time to Production:** 4-6 hours

---

## PHASE 1: CRITICAL FIXES (Do Today - 30 min)

These are BLOCKING issues. Pipeline won't work without these fixes.

### [ ] 1.1 - Fix Backend Configuration

**Status:** 🔴 BLOCKING  
**Risk:** Pipeline fails at terraform init  
**Files:** `.github/workflows/reusable.yml`, `stacks/*/backend.tf`

**Checklist:**
- [ ] Remove `key = "..."` from backend.tf
- [ ] Add `-backend-config` flags to terraform init
- [ ] Test locally: `terraform init -backend-config="key=..."`
- [ ] Verify: No error about variables in backend
- [ ] Push to feature branch
- [ ] Trigger workflow and check logs

**Reference:** IMPLEMENTATION_FIXES.md → Issue #1

---

### [ ] 1.2 - Fix Plan Artifact Handling

**Status:** 🔴 BLOCKING  
**Risk:** Apply step uses different plan than reviewed in PR  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Add `actions/upload-artifact@v4` after plan step
- [ ] Add `actions/download-artifact@v4` before apply step
- [ ] Verify artifact name is consistent: `tfplan-STACK-REGION`
- [ ] Test locally with act tool (if available)
- [ ] Push to feature branch
- [ ] Create PR and watch plan job
- [ ] Watch apply job and verify it uses artifact

**Reference:** IMPLEMENTATION_FIXES.md → Issue #2

---

### [ ] 1.3 - Add Manual Approval Gate

**Status:** 🔴 CRITICAL  
**Risk:** Anyone can auto-deploy to production  
**Files:** `.github/workflows/apply.yml`, GitHub Settings

**Checklist:**
- [ ] Add `approval` job to apply.yml
- [ ] Set environment: `name: production`
- [ ] Add approval job as dependency to stage-1
- [ ] Go to GitHub: Settings → Environments
- [ ] Create "production" environment
- [ ] Enable: "Require reviewers for deployments"
- [ ] Add team reviewers (minimum 1)
- [ ] Test: Push to main, watch workflow pause at approval

**Reference:** IMPLEMENTATION_FIXES.md → Issue #3

---

### [ ] 1.4 - Add Error Handling to Python Script

**Status:** 🔴 MEDIUM  
**Risk:** Silent failures, unclear error messages  
**Files:** `scripts/generate_matrix.py`

**Checklist:**
- [ ] Add try/except wrapper to main()
- [ ] Add file existence checks (include.txt, regions.txt, dependencies.json)
- [ ] Add validation for SHA arguments
- [ ] Add validation for loaded stacks/regions
- [ ] Output errors to stderr in JSON format
- [ ] Test invalid inputs: `python3 generate_matrix.py "" ""`
- [ ] Test missing files: remove include.txt and run
- [ ] Verify error messages are helpful

**Reference:** IMPLEMENTATION_FIXES.md → Issue #4

---

## PHASE 2: IMPORTANT FIXES (Do This Week - 2-3 hours)

These are important for reliability and safety. Do before deploying to production.

### [ ] 2.1 - Fix Terraform Format Check

**Status:** 🟠 HIGH  
**Risk:** Code quality not enforced  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Change format check to: `terraform fmt -check -recursive -diff`
- [ ] Add explicit exit on failure
- [ ] Test locally: `terraform fmt -check` in a stack
- [ ] Test failure case: Run fmt without changes, verify error
- [ ] Push changes

**Reference:** IMPLEMENTATION_FIXES.md → Issue #5

---

### [ ] 2.2 - Add Variable Validation

**Status:** 🟠 HIGH  
**Risk:** Invalid configurations reach production  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Add step: "Terraform Validate & Check Variables"
- [ ] Run: `terraform validate`
- [ ] Run: `terraform plan -var="region=..." -out=/dev/null`
- [ ] Set: `-input=false` to prevent interactive input
- [ ] Test locally: Try with invalid region
- [ ] Verify: Error message is clear

**Reference:** IMPLEMENTATION_FIXES.md → Issue #6

---

### [ ] 2.3 - Verify State Lock Table Exists

**Status:** 🟠 HIGH  
**Risk:** State file corruption in concurrent applies  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Add step: "Verify DynamoDB Lock Table"
- [ ] Command: `aws dynamodb describe-table --table-name terraform-locks`
- [ ] Set region: us-east-1 (where backend is)
- [ ] Test: Remove DynamoDB table and verify check fails
- [ ] Restore table

**Reference:** IMPLEMENTATION_FIXES.md → Issue #7

---

### [ ] 2.4 - Add Deployment Logging

**Status:** 🟠 MEDIUM  
**Risk:** No audit trail, no deployment history  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Add step: "Log Deployment" (only on apply)
- [ ] Log: timestamp, actor, stack, region, commit
- [ ] Optionally: Send to CloudWatch Logs
- [ ] Test: Run apply and check logs
- [ ] Archive logs for audit

**Reference:** IMPLEMENTATION_FIXES.md → Issue #8

---

### [ ] 2.5 - Add Plan Comment to PR

**Status:** 🟠 MEDIUM  
**Risk:** Reviewers can't see what will change  
**Files:** `.github/workflows/plan.yml`

**Checklist:**
- [ ] Add step: "Comment Plan to PR"
- [ ] Use: `actions/github-script@v7`
- [ ] Show: terraform plan output in comment
- [ ] Include: Stack name, region, changes summary
- [ ] Test: Create PR and check for comment

**Reference:** IMPLEMENTATION_FIXES.md → Issue #9

---

### [ ] 2.6 - Add Cost Estimation

**Status:** 🟠 MEDIUM  
**Risk:** Accidental expensive deployments  
**Files:** `.github/workflows/plan.yml`

**Checklist:**
- [ ] Add Infracost integration
- [ ] Show cost changes in PR comment
- [ ] Set warning threshold (e.g., warn if >$100/month increase)
- [ ] Document cost optimization tips
- [ ] Test: Create PR and verify cost appears

**Reference:** IMPLEMENTATION_FIXES.md → Issue #10

---

### [ ] 2.7 - Add Dependency Validation

**Status:** 🟠 MEDIUM  
**Risk:** Invalid dependency configurations  
**Files:** `scripts/generate_matrix.py`

**Checklist:**
- [ ] Add function: `validate_dependencies()`
- [ ] Check: All deps in dependencies.json exist in include.txt
- [ ] Show helpful error if missing
- [ ] Test: Add invalid dependency to dependencies.json
- [ ] Verify: Script exits with clear error

**Reference:** IMPLEMENTATION_FIXES.md → Issue #11

---

### [ ] 2.8 - Add Pre-Flight Checks

**Status:** 🟠 MEDIUM  
**Risk:** Configuration errors discovered mid-deployment  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Add step: "Pre-Flight Checks"
- [ ] Check AWS credentials: `aws sts get-caller-identity`
- [ ] Check S3 backend: `aws s3 ls s3://bucket`
- [ ] Check region available: `aws ec2 describe-availability-zones`
- [ ] Test: Run and verify all checks pass
- [ ] Test: Disable AWS credentials and verify fails early

**Reference:** IMPLEMENTATION_FIXES.md → Issue #12

---

## PHASE 3: RECOMMENDED ADDITIONS (Before Month 1 - 2-3 hours)

These improve production reliability significantly.

### [ ] 3.1 - Add Environment-Specific Configuration

**Status:** 🟢 MEDIUM  
**Risk:** Can't differentiate dev vs prod  
**Files:** `stacks/*/variables.tf`, `stacks/*/main.tf`

**Checklist:**
- [ ] Add variable: `environment` (dev, staging, prod)
- [ ] Create locals: environment-specific config
- [ ] Pass environment from workflow
- [ ] Use in resources: instance types, backup retention, etc.
- [ ] Test: Deploy different environments with different configs
- [ ] Document: Environment configuration matrix

**Reference:** IMPLEMENTATION_FIXES.md → Issue #13

---

### [ ] 3.2 - Enable State Backups

**Status:** 🟢 MEDIUM  
**Risk:** State file loss = infrastructure unmanageable  
**Files:** `.github/workflows/apply.yml`, AWS S3

**Checklist:**
- [ ] Enable S3 versioning on backend bucket
- [ ] Enable S3 MFA Delete (optional, stronger)
- [ ] Create backup bucket: `terraform-state-backups`
- [ ] Add step: Copy state before apply
- [ ] Add step: Copy state after apply success
- [ ] Set retention: Keep backups for 90 days
- [ ] Document: Restore procedure

**Reference:** IMPLEMENTATION_FIXES.md → Issue #14

---

### [ ] 3.3 - Add Drift Detection Alerts

**Status:** 🟢 MEDIUM  
**Risk:** Infrastructure changes go unnoticed  
**Files:** `.github/workflows/drift.yml`

**Checklist:**
- [ ] Capture drift detection exit code
- [ ] If drift found: Send Slack notification
- [ ] Include: Stack, region, change summary
- [ ] Add: Link to full drift report
- [ ] Test: Manually change infrastructure in AWS
- [ ] Run drift workflow and verify alert

**Reference:** IMPLEMENTATION_FIXES.md → Issue #15

---

### [ ] 3.4 - Add Resource Tagging Standards

**Status:** 🟢 LOW  
**Risk:** Cost allocation unclear, compliance issues  
**Files:** `stacks/*/main.tf`, `modules/*/main.tf`

**Checklist:**
- [ ] Create locals: `common_tags`
- [ ] Include: Environment, Stack, Region, ManagedBy, etc.
- [ ] Apply to all resources: `tags = merge(local.common_tags, {...})`
- [ ] Document: Tag naming conventions
- [ ] Test: Deploy and verify tags in AWS console

**Reference:** IMPLEMENTATION_FIXES.md → Issue #16

---

### [ ] 3.5 - Add Output Capture

**Status:** 🟢 LOW  
**Risk:** Outputs not available for dependent systems  
**Files:** `.github/workflows/reusable.yml`

**Checklist:**
- [ ] Add step: `terraform output -json > outputs.json`
- [ ] Upload artifact with outputs
- [ ] Make available for 30 days
- [ ] Document: How to retrieve outputs
- [ ] Test: Download outputs from completed apply

**Reference:** IMPLEMENTATION_FIXES.md → Issue #17

---

### [ ] 3.6 - Add Resource Tagging Standards

**Status:** 🟢 LOW  
**Risk:** Resource tracking and cost allocation unclear  
**Files:** `stacks/*/locals.tf` (create if not exists)

**Checklist:**
- [ ] Create `locals.tf` with common_tags
- [ ] Add tags: Environment, Stack, Region, GitCommit, etc.
- [ ] Apply to all resources
- [ ] Use in cost allocation queries
- [ ] Document tag strategy

**Reference:** IMPLEMENTATION_FIXES.md → Issue #18

---

## PHASE 4: NICE-TO-HAVE (After Month 1)

### [ ] 4.1 - Enable Terraform Cloud for State Visualization
### [ ] 4.2 - Add Automated Rollback on Apply Failure
### [ ] 4.3 - Add Policy as Code (Sentinel)
### [ ] 4.4 - Add Resource Compliance Checks
### [ ] 4.5 - Add Automated Scaling Policies

---

## Daily Workflow Checklist

Before pushing code:
- [ ] Run terraform validate locally
- [ ] Run terraform fmt locally
- [ ] Check for hardcoded values
- [ ] Review plan output
- [ ] Verify all required variables present

Before merging to main:
- [ ] Code review completed
- [ ] Plan looks correct
- [ ] No unintended changes
- [ ] Tags applied correctly
- [ ] Outputs documented

After deployment:
- [ ] Verify resources created
- [ ] Check resource outputs
- [ ] Verify tags applied
- [ ] Confirm monitoring active
- [ ] Document changes in runbook

---

## Success Criteria

Your pipeline is production-ready when:

✅ **Phase 1 Complete (Must Have)**
- [ ] Backend configuration supports all regions
- [ ] Plan artifacts verified between jobs
- [ ] Manual approval required for deployments
- [ ] Clear error messages on failures
- [ ] No format check warnings

✅ **Phase 2 Complete (Should Have)**
- [ ] All variable validation passes
- [ ] State locking verified before apply
- [ ] Full audit trail logged
- [ ] Cost estimation visible in PR
- [ ] Drift detection alerts working

✅ **Phase 3 Complete (Nice to Have)**
- [ ] Environment-specific config works
- [ ] Automated state backups running
- [ ] Resource tagging standards enforced
- [ ] Output artifacts captured
- [ ] Team runbook updated

---

## Progress Tracker

```
Phase 1 (Critical): [0/4]   0%
  1.1 Backend config:        [ ]
  1.2 Plan artifacts:        [ ]
  1.3 Approval gate:         [ ]
  1.4 Error handling:        [ ]

Phase 2 (Important): [0/8]   0%
  2.1 Format check:          [ ]
  2.2 Variable validation:   [ ]
  2.3 State lock verify:     [ ]
  2.4 Deployment logging:    [ ]
  2.5 Plan PR comment:       [ ]
  2.6 Cost estimation:       [ ]
  2.7 Dependency validation: [ ]
  2.8 Pre-flight checks:     [ ]

Phase 3 (Recommended): [0/6] 0%
  3.1 Environment config:    [ ]
  3.2 State backups:         [ ]
  3.3 Drift alerts:          [ ]
  3.4 Resource tagging:      [ ]
  3.5 Output capture:        [ ]
  3.6 Rollback procedure:    [ ]

OVERALL: [0/18] 0%
```

---

## Support Resources

- **Full Review:** [PRODUCTION_REVIEW.md](PRODUCTION_REVIEW.md)
- **Code Examples:** [IMPLEMENTATION_FIXES.md](IMPLEMENTATION_FIXES.md)
- **Quick Guide:** [QUICK_ACTION_GUIDE.md](QUICK_ACTION_GUIDE.md)
- **Documentation:** [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

---

## Questions?

| Question | Answer | Document |
|----------|--------|----------|
| What's the priority? | Phase 1 first, then Phase 2 | QUICK_ACTION_GUIDE.md |
| How long will it take? | Phase 1: 30 min, Phase 2: 2-3 hrs | QUICK_ACTION_GUIDE.md |
| How do I implement? | Copy code from IMPLEMENTATION_FIXES.md | IMPLEMENTATION_FIXES.md |
| What happens if I skip a fix? | Risk of production failure | PRODUCTION_REVIEW.md |
| How do I test? | Run locally, test in GitHub Actions | Each section |

---

**Remember:** Your architecture is solid, but execution needs hardening. 4-6 hours of focused work = production-ready system. 🚀
