# Terraform Deployment Pipeline with GitHub Actions

Production-ready multi-stack, multi-region Terraform CI/CD pipeline using GitHub Actions with:
- ✅ Dependency-aware execution
- ✅ Parallel deployments
- ✅ Change detection (only deploy affected stacks)
- ✅ Drift detection (scheduled)
- ✅ AWS OIDC authentication
- ✅ Remote state with S3 + DynamoDB locking
- ✅ Quality checks (fmt, validate)
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
  └── generate_matrix.py # Dynamic matrix generation
stacks/
  ├── network/          # VPC and networking
  ├── iam/              # IAM roles and policies
  ├── compute/          # EC2 instances (example)
  └── storage/          # S3 buckets (example)
modules/
  ├── vpc/              # VPC module
  └── s3/               # S3 bucket module
include.txt             # Stacks to deploy
regions.txt             # Regions to deploy to
dependencies.json       # Stack dependencies
SETUP_GUIDE.md          # Complete setup instructions
GITHUB_SECRETS.md       # Secrets configuration
QUICK_REFERENCE.md      # Quick lookup guide
SKIPPING_STACKS_AND_REGIONS.md  # Advanced: Skip stacks/regions
```

---

## 🚀 Quick Start (5 Minutes)

### 1. Prerequisites
- AWS Account
- GitHub Repository
- `ASSUME_ROLE_ARN` secret configured (see [GITHUB_SECRETS.md](GITHUB_SECRETS.md))

### 2. Configure Stacks
Edit `include.txt` to control which stacks deploy:
```
stacks/network/**
stacks/iam/**
```

### 3. Configure Regions
Edit `regions.txt` for multi-region deployment:
```
us-east-1
ap-south-1
```

### 4. Set Dependencies
Edit `dependencies.json` to control deployment order:
```json
{
  "network": [],
  "compute": ["network"],
  "iam": []
}
```

### 5. Create Stack
```bash
mkdir -p stacks/my-stack
cat > stacks/my-stack/main.tf << 'EOF'
resource "aws_example_resource" "example" {
  # Your resource definition
}
EOF
```

### 6. Add GitHub Secret
Go to **Settings → Secrets and variables → Actions** and add:
- `ASSUME_ROLE_ARN`: `arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-terraform-role`

### 7. Push & Watch
```bash
git add .
git commit -m "Add my-stack"
git push
```

---

## 🎯 How It Works

### Workflow Triggers

| Workflow | Trigger | Action |
|----------|---------|--------|
| **plan.yml** | PR to main | Runs `terraform plan` on affected stacks |
| **apply.yml** | Push to main | Runs `terraform apply` with dependency ordering |
| **drift.yml** | Daily at 6 AM UTC | Detects infrastructure drift |

### Change Detection

1. Compare git SHAs (base vs head)
2. Detect changed files
3. Identify affected stacks from file paths
4. Include dependent stacks
5. Generate parallel execution matrix

### Dependency Handling

Given `dependencies.json`:
```json
{
  "network": [],
  "compute": ["network"]
}
```

Pipeline ensures:
- **Stage 1**: network runs in parallel with iam
- **Stage 2**: compute runs after stage 1 completes

### Multi-Region Execution

With `regions.txt`:
```
us-east-1
ap-south-1
```

Each stack deploys to ALL regions in parallel. E.g., for 3 stacks × 2 regions = 6 parallel jobs.

---

## ❓ Common Questions

### Q: How do I skip the Compute stack?
A: Edit `include.txt` and remove `stacks/compute/**`:
```
stacks/network/**
stacks/iam/**
# stacks/compute/**  ← Commented = skipped
```

### Q: What if my S3 bucket name is the same in both regions?
A: **It will fail!** S3 bucket names are globally unique. Use region in the name:
```hcl
resource "aws_s3_bucket" "app" {
  bucket = "my-app-${var.region}"  # ✅ Unique per region
}
```

See [SKIPPING_STACKS_AND_REGIONS.md](SKIPPING_STACKS_AND_REGIONS.md) for details.

### Q: How do I deploy only to one region?
A: Edit `regions.txt` to have one region:
```
us-east-1
```

### Q: Can I manually skip a stage in pipeline?
A: Not without modifying workflow. Best practice: use `include.txt` for permanent changes.

### Q: How do I add a new stack?
A:
1. Create `stacks/my-stack/main.tf`
2. Add to `include.txt`: `stacks/my-stack/**`
3. Add to `dependencies.json` (if has dependencies)
4. Commit and push

### Q: How often does drift detection run?
A: Daily at 6 AM UTC. Edit `drift.yml` to change schedule.

### Q: What if credentials fail?
A: Check [GITHUB_SECRETS.md](GITHUB_SECRETS.md) → Troubleshooting section.

---

## 📚 Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup from scratch (AWS + GitHub)
- **[GITHUB_SECRETS.md](GITHUB_SECRETS.md)** - Secrets configuration and troubleshooting
- **[SKIPPING_STACKS_AND_REGIONS.md](SKIPPING_STACKS_AND_REGIONS.md)** - Skip stacks/regions, multi-region S3
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick lookup guide

---

## 🔄 Workflow Examples

### Example 1: Deploy Network + IAM to 2 regions

**Files**:
- `include.txt`: network + iam
- `regions.txt`: us-east-1, ap-south-1
- `dependencies.json`: network has no deps, iam has no deps

**Result**: 4 parallel jobs
- network + us-east-1
- network + ap-south-1
- iam + us-east-1
- iam + ap-south-1

### Example 2: Deploy with dependencies

**Files**:
- `include.txt`: network, compute, iam
- `dependencies.json`: compute depends on network
- `regions.txt`: us-east-1

**Result**: 3 jobs in 2 stages
- **Stage 1** (parallel): network + iam
- **Stage 2** (after stage 1): compute

---

## 🔐 Security

- **No static credentials**: Uses AWS OIDC federation
- **IAM role**: Configurable via secret
- **State locking**: DynamoDB prevents concurrent modifications
- **State encryption**: S3 versioning and encryption enabled
- **Audit trail**: All changes in git history

---

## 🛠️ Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Credentials failed | Secret not set | Add `ASSUME_ROLE_ARN` secret |
| S3 bucket already exists | Same name in 2 regions | Add `${var.region}` to bucket name |
| Matrix empty | All stacks skipped | Check `include.txt` |
| Dependency error | Wrong `dependencies.json` | Review dependency order |
| No plan output | Changes not detected | Push to trigger workflow |

See [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting) for detailed solutions.

---

## 📝 File Reference

### `include.txt`
Controls which stacks are deployed. Remove stacks to skip them:
```
stacks/network/**
stacks/iam/**
stacks/compute/**
```

### `regions.txt`
Controls regions for multi-region deployment:
```
us-east-1
ap-south-1
eu-west-1
```

### `dependencies.json`
Defines stack execution order:
```json
{
  "network": [],
  "compute": ["network"],
  "iam": [],
  "storage": ["network", "iam"]
}
```

---

## ✨ Features

- ✅ **Change Detection**: Only deploy affected stacks
- ✅ **Dependency Ordering**: Stacks deploy in correct order
- ✅ **Parallel Execution**: Independent stacks deploy simultaneously
- ✅ **Multi-Region**: Deploy to multiple regions with one config
- ✅ **Drift Detection**: Scheduled drift detection with alerts
- ✅ **Quality Checks**: fmt, validate
- ✅ **State Locking**: Prevent concurrent modifications
- ✅ **OIDC Auth**: No static AWS credentials
- ✅ **Easy Scaling**: Add stacks without modifying workflows

---

## 🎓 Learn More

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

For quick lookups, see [QUICK_REFERENCE.md](QUICK_REFERENCE.md).

For advanced topics, see [SKIPPING_STACKS_AND_REGIONS.md](SKIPPING_STACKS_AND_REGIONS.md).