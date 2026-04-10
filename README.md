# Terraform Deployment Pipeline with GitHub Actions

Production-ready multi-stack, multi-region Terraform CI/CD pipeline using GitHub Actions with:
- ✅ Dependency-aware execution
- ✅ Parallel deployments
- ✅ Change detection (only deploy affected stacks)
- ✅ Drift detection (scheduled)
- ✅ AWS OIDC authentication
- ✅ Remote state with S3 + DynamoDB locking
- ✅ Quality checks (fmt, validate)
- ✅ Global service support (IAM, Route53, CloudFront)
- ✅ Easy stack/region management

---

## 📁 Repository Structure

```
.github/workflows/
  ├── plan.yml          # PR planning
  ├── apply.yml         # Push to main
  ├── drift.yml         # Scheduled drift detection
  └── reusable.yml      # Shared workflow logic
scripts/
  └── generate_matrix.py  # Dynamic matrix generation
stacks/
  ├── network/          # VPC and networking
  ├── iam/              # IAM roles and policies
  ├── compute/          # EC2 instances
  └── storage/          # S3 buckets
modules/
  ├── vpc/              # VPC module
  └── s3/               # S3 bucket module
include.txt             # Stacks to deploy (comment out to skip)
regions.txt             # Regions to deploy to
dependencies.json       # Stack dependency ordering
global_stacks.json      # Per-stack region overrides (global AWS services)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- AWS Account with OIDC configured
- GitHub Repository
- `ASSUME_ROLE_ARN` secret configured

### 2. Configure Stacks
Edit `include.txt` — comment out any stack to skip it:
```
stacks/network/**
stacks/iam/**
# stacks/compute/**   ← commented = skipped
# stacks/storage/**   ← commented = skipped
```

### 3. Configure Regions
Edit `regions.txt`:
```
us-east-1
ap-south-1
```

### 4. Set Dependencies
Edit `dependencies.json`:
```json
{
  "network": [],
  "iam": [],
  "compute": ["network"],
  "storage": ["network", "iam"]
}
```

### 5. Configure Global Services
Edit `global_stacks.json` for stacks that should only deploy to one region:
```json
{
  "iam": ["us-east-1"]
}
```

### 6. Add GitHub Secret
Go to **Settings → Secrets and variables → Actions** and add:
- `ASSUME_ROLE_ARN`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-terraform-role`

---

## 🎯 How It Works

### Workflow Triggers

| Workflow | Trigger | Action |
|----------|---------|--------|
| `plan.yml` | PR to main | Runs `terraform plan` on affected stacks |
| `apply.yml` | Push to main | Runs `terraform apply` with dependency ordering |
| `drift.yml` | Daily at 6 AM UTC | Detects infrastructure drift |

### Change Detection
1. Compare git SHAs (base vs head)
2. Detect changed files
3. Identify affected stacks from file paths
4. Include dependent stacks
5. Filter against `include.txt` (respects comments)
6. Generate parallel execution matrix

### Dependency Handling
```json
{
  "network": [],
  "compute": ["network"]
}
```
- Stage 1: `network` + `iam` run in parallel
- Stage 2: `compute` runs after stage 1 completes

### Multi-Region Execution
Each stack deploys to all regions in `regions.txt` unless overridden in `global_stacks.json`.

### Global Services
Services like IAM, Route53, and CloudFront are global — deploying them to multiple regions causes `EntityAlreadyExists` errors. Pin them to one region in `global_stacks.json`:
```json
{
  "_comment": "Global AWS services — deploy to one region only",
  "iam": ["us-east-1"],
  "route53": ["us-east-1"],
  "cloudfront": ["us-east-1"]
}
```

---

## 🔐 Security
- **No static credentials** — AWS OIDC federation
- **State locking** — DynamoDB prevents concurrent modifications
- **State encryption** — S3 with encryption enabled
- **Audit trail** — all changes in git history

---

## 🛠️ Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `EntityAlreadyExists` | Global service deployed to multiple regions | Add stack to `global_stacks.json` |
| `Matrix empty` | All stacks skipped | Check `include.txt` |
| `Dependency error` | Wrong `dependencies.json` | Review dependency order |
| `Credentials failed` | Secret not set | Add `ASSUME_ROLE_ARN` secret |
| `fmt check failed` | Unformatted `.tf` files | Run `terraform fmt` locally |

---

## 📝 File Reference

### `include.txt`
Controls which stacks deploy. Comment out to skip:
```
stacks/network/**
stacks/iam/**
# stacks/compute/**
```

### `regions.txt`
Default regions for all stacks:
```
us-east-1
ap-south-1
```

### `dependencies.json`
Stack execution order:
```json
{
  "network": [],
  "iam": [],
  "compute": ["network"],
  "storage": ["network", "iam"]
}
```

### `global_stacks.json`
Override regions for global AWS services:
```json
{
  "iam": ["us-east-1"]
}
```
Keys starting with `_` are treated as comments and ignored.
