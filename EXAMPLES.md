# Real-World Examples

## Scenario 1: Skip Compute - Only Deploy Network & IAM

**Use Case**: Development environment, only need networking and identity.

### Steps

1. **Update `include.txt`**:
   ```
   stacks/network/**
   stacks/iam/**
   # stacks/compute/**    ← Compute is skipped
   ```

2. **Keep `regions.txt` as is**:
   ```
   us-east-1
   ap-south-1
   ```

3. **Commit and push**:
   ```bash
   git add include.txt
   git commit -m "Skip compute stack"
   git push origin main
   ```

4. **Result**: 4 parallel jobs
   - network + us-east-1
   - network + ap-south-1
   - iam + us-east-1
   - iam + ap-south-1

Compute will NOT be deployed.

---

## Scenario 2: Multi-Region S3 - Same Stack, Different Regions

**Use Case**: Deploy S3 buckets to both us-east-1 and ap-south-1 with unique names.

### Problem
```hcl
# ❌ This fails on second region
resource "aws_s3_bucket" "app_data" {
  bucket = "my-company-data"  # ERROR: Already exists in us-east-1!
}
```

### Solution

1. **Update `stacks/storage/main.tf`**:
   ```hcl
   variable "region" {
     type = string
   }

   variable "environment" {
     type    = string
     default = "prod"
   }

   resource "aws_s3_bucket" "app_data" {
     bucket = "my-company-${var.environment}-${var.region}"
     # Creates: my-company-prod-us-east-1, my-company-prod-ap-south-1
   }

   resource "aws_s3_bucket_versioning" "app_data" {
     bucket = aws_s3_bucket.app_data.id
     versioning_configuration {
       status = "Enabled"
     }
   }

   resource "aws_s3_bucket_server_side_encryption_configuration" "app_data" {
     bucket = aws_s3_bucket.app_data.id
     rule {
       apply_server_side_encryption_by_default {
         sse_algorithm = "AES256"
       }
     }
   }
   ```

2. **Update `include.txt`** (add storage):
   ```
   stacks/network/**
   stacks/iam/**
   stacks/storage/**
   ```

3. **Keep `regions.txt`**:
   ```
   us-east-1
   ap-south-1
   ```

4. **Result**: 6 parallel jobs
   - network + us-east-1 → VPC created
   - network + ap-south-1 → VPC created
   - iam + us-east-1 → IAM roles created
   - iam + ap-south-1 → IAM roles created
   - storage + us-east-1 → Bucket `my-company-prod-us-east-1` created
   - storage + ap-south-1 → Bucket `my-company-prod-ap-south-1` created

Each bucket has a unique name, no conflicts!

---

## Scenario 3: Skip Second Region - Only Deploy to us-east-1

**Use Case**: Cost saving, only deploy to primary region.

### Steps

1. **Update `regions.txt`**:
   ```
   us-east-1
   # ap-south-1   ← Second region skipped
   ```

2. **Keep `include.txt` as is**:
   ```
   stacks/network/**
   stacks/iam/**
   stacks/compute/**
   ```

3. **Commit and push**:
   ```bash
   git add regions.txt
   git commit -m "Deploy to us-east-1 only"
   git push origin main
   ```

4. **Result**: 3 parallel jobs (instead of 6)
   - network + us-east-1
   - iam + us-east-1
   - compute + us-east-1 (depends on network)

ap-south-1 deployments are skipped.

---

## Scenario 4: Complex Dependencies - Deploy in Order

**Use Case**: Production environment with complex dependencies.

### Setup

**`include.txt`**:
```
stacks/network/**
stacks/compute/**
stacks/storage/**
stacks/iam/**
stacks/app/**
```

**`dependencies.json`**:
```json
{
  "network": [],
  "compute": ["network"],
  "storage": ["network"],
  "iam": [],
  "app": ["network", "compute", "storage", "iam"]
}
```

### Execution Flow

**Stage 1** (parallel):
- network
- iam

**Stage 2** (parallel, after stage 1):
- compute (needs network from stage 1)
- storage (needs network from stage 1)

**Stage 3** (after stage 2):
- app (needs all resources from stages 1 & 2)

This ensures resources are created in correct order despite parallel execution.

---

## Scenario 5: Temporary Development - Skip Everything Except Network

**Use Case**: Testing network configuration in isolation.

### Steps

1. **Temporarily update `include.txt`**:
   ```
   stacks/network/**
   # stacks/compute/**
   # stacks/storage/**
   # stacks/iam/**
   ```

2. **Push to feature branch**:
   ```bash
   git checkout -b feature/test-network
   git add include.txt
   git commit -m "Test network stack only"
   git push origin feature/test-network
   ```

3. **Create PR and test**

4. **When done, revert before merging**:
   ```bash
   git checkout main
   git pull
   # Restore original include.txt
   git add include.txt
   git commit -m "Restore all stacks"
   ```

---

## Scenario 6: Staging vs Production - Different Configurations

**Use Case**: Deploy same stacks but different configurations per environment.

### Approach: Use terraform.tfvars

Create separate variable files (NOT in git):

1. **Create local vars files**:
   ```bash
   # Development
   echo 'environment = "dev"' > terraform.dev.tfvars
   echo 'instance_type = "t2.micro"' >> terraform.dev.tfvars

   # Production  
   echo 'environment = "prod"' > terraform.prod.tfvars
   echo 'instance_type = "t2.large"' >> terraform.prod.tfvars
   ```

2. **In `stacks/compute/main.tf`**:
   ```hcl
   variable "environment" {
     type = string
   }

   variable "instance_type" {
     type = string
   }

   resource "aws_instance" "app" {
     ami           = "ami-0c55b159cbfafe1d0"
     instance_type = var.instance_type

     tags = {
       Environment = var.environment
       Region      = var.region
     }
   }
   ```

3. **Update workflow to pass vars**:
   ```yaml
   - name: Terraform Plan
     run: |
       terraform plan \
         -var="region=${{ matrix.region }}" \
         -var-file="terraform.prod.tfvars"
   ```

Or use separate branches for dev/prod, each with different vars.

---

## Scenario 7: Blue-Green Deployment - Parallel Stacks

**Use Case**: Run old and new versions simultaneously for zero downtime.

### Approach: Create Stack Variants

```
stacks/
  compute-blue/   # Current production
    main.tf
  compute-green/  # New version
    main.tf
```

**`include.txt`**:
```
stacks/network/**
stacks/compute-blue/**
stacks/compute-green/**
```

**`dependencies.json`**:
```json
{
  "network": [],
  "compute-blue": ["network"],
  "compute-green": ["network"]
}
```

Both deploy in parallel to network. When green is ready, flip traffic and delete blue.

---

## Scenario 8: Hotfix - Skip Non-Critical Stacks

**Use Case**: Emergency fix to IAM only, skip compute/storage.

### Steps

1. **Quickly update `include.txt`**:
   ```
   stacks/iam/**
   # Everything else commented out
   ```

2. **Fix and push**:
   ```bash
   git checkout -b hotfix/iam-fix
   # Make IAM fix
   git add stacks/iam/
   git add include.txt
   git commit -m "Hotfix: IAM permission issue"
   git push origin hotfix/iam-fix
   ```

3. **Create and merge PR**

4. **Revert `include.txt`** for next deployment

Only IAM stack is deployed, reducing risk.

---

## Quick Commands

```bash
# See what will be deployed
python scripts/generate_matrix.py all all

# Preview before commit
cat include.txt
cat regions.txt
cat dependencies.json

# Test locally (if Terraform installed)
cd stacks/network
terraform init -backend=false
terraform plan -var="region=us-east-1"

# Check git diff before pushing
git diff include.txt
git diff regions.txt
```

---

## Common Patterns

| Pattern | Use Case | How |
|---------|----------|-----|
| Skip stack | Don't deploy compute | Remove from `include.txt` |
| Single region | Cost saving | Keep 1 region in `regions.txt` |
| Multi-region | Global deployment | Add regions to `regions.txt` |
| Unique names | S3, global resources | Add `${var.region}` |
| Dependencies | Complex infra | Update `dependencies.json` |
| Staged rollout | Gradual deployment | Multiple stacks with dependencies |
| Hotfix | Emergency fix | Temporarily modify `include.txt` |
| Blue-green | Zero-downtime deploy | Create parallel stacks |

---

For more info, see [QUICK_REFERENCE.md](QUICK_REFERENCE.md) or [SETUP_GUIDE.md](SETUP_GUIDE.md).
