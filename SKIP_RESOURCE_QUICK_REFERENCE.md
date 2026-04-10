# Skip Resource/Module from Specific Region - Quick Guide

## Your Question
**"If I want to skip one resource (or one complete module) from any region, how can I do that?"**

---

## Answer: Use `count` with Region Check

### Simplest Solution (1-2 Regions)

```hcl
# Skip S3 in ap-south-1 (deploy only in us-east-1)
resource "aws_s3_bucket" "logs" {
  count = var.region == "us-east-1" ? 1 : 0  # ← This line!
  
  bucket = "app-logs-${var.region}"
}

# Reference it:
output "bucket_id" {
  value = try(aws_s3_bucket.logs[0].id, "NOT DEPLOYED IN THIS REGION")
}
```

### Better Solution (Multiple Regions)

```hcl
# Deploy in specific regions
locals {
  allowed_regions = ["us-east-1", "eu-west-1"]
  deploy_storage  = contains(local.allowed_regions, var.region)
}

resource "aws_s3_bucket" "logs" {
  count = local.deploy_storage ? 1 : 0  # ← Cleaner!
  
  bucket = "app-logs-${var.region}"
}
```

### Skip Entire Module

```hcl
# Skip complete data pipeline module from ap-south-1
module "data_pipeline" {
  count = var.region == "us-east-1" ? 1 : 0  # ← Add count
  
  source = "../../modules/data-pipeline"
  region = var.region
}

# Access output:
output "pipeline_arn" {
  value = try(module.data_pipeline[0].arn, "NOT DEPLOYED")
}
```

---

## Real-World Examples

### Example 1: S3 Only in Primary Region

```hcl
resource "aws_s3_bucket" "data" {
  count = var.region == "us-east-1" ? 1 : 0
  bucket = "company-data-${var.region}"
}
```

**Result:**
- us-east-1 → S3 created ✅
- ap-south-1 → S3 skipped ✅

### Example 2: Database in 2 Regions Only

```hcl
locals {
  db_regions = ["us-east-1", "eu-west-1"]
  deploy_db  = contains(local.db_regions, var.region)
}

resource "aws_db_instance" "main" {
  count = local.deploy_db ? 1 : 0
  
  identifier = "app-db-${var.region}"
  engine     = "postgres"
}
```

**Result:**
- us-east-1 → RDS created ✅
- ap-south-1 → RDS skipped ✅
- eu-west-1 → RDS created ✅

### Example 3: Production-Only Resources

```hcl
variable "environment" { type = string }
variable "region" { type = string }

locals {
  is_production = var.environment == "prod"
  is_primary    = var.region == "us-east-1"
  
  deploy_redshift = local.is_production && local.is_primary
}

resource "aws_redshift_cluster" "analytics" {
  count = local.deploy_redshift ? 1 : 0
  
  cluster_identifier = "analytics"
  node_type          = "ra3.xlplus"
}
```

**Result:**
- prod + us-east-1 → Redshift created ✅
- prod + ap-south-1 → Skipped ✅
- dev + us-east-1 → Skipped ✅

### Example 4: Multiple Resources with Different Rules

```hcl
variable "region" { type = string }

locals {
  # Different deployment rules per resource
  deploy_storage   = var.region == "us-east-1"
  deploy_compute   = true  # Everywhere
  deploy_cache     = true  # Everywhere
  deploy_analytics = contains(["us-east-1", "eu-west-1"], var.region)
}

resource "aws_s3_bucket" "data" {
  count = local.deploy_storage ? 1 : 0
  bucket = "app-data-${var.region}"
}

resource "aws_instance" "app" {
  count = local.deploy_compute ? 1 : 0
  instance_type = "t2.micro"
}

resource "aws_elasticache_cluster" "cache" {
  count = local.deploy_cache ? 1 : 0
  cluster_id = "cache-${var.region}"
}

resource "aws_redshift_cluster" "analytics" {
  count = local.deploy_analytics ? 1 : 0
  cluster_identifier = "analytics-${var.region}"
}
```

**Deployment Pattern:**
| Resource | us-east-1 | ap-south-1 | eu-west-1 |
|----------|-----------|-----------|-----------|
| Storage | ✅ | ❌ | ❌ |
| Compute | ✅ | ✅ | ✅ |
| Cache | ✅ | ✅ | ✅ |
| Analytics | ✅ | ❌ | ✅ |

---

## Step-by-Step Implementation

### Step 1: Add count to Resource

```hcl
# BEFORE
resource "aws_s3_bucket" "logs" {
  bucket = "app-logs"
}

# AFTER - Add count condition
resource "aws_s3_bucket" "logs" {
  count = var.region == "us-east-1" ? 1 : 0
  
  bucket = "app-logs-${var.region}"
}
```

### Step 2: Update All References

```hcl
# References to the resource must use [0] when using count

# OLD (without count):
output "bucket_arn" {
  value = aws_s3_bucket.logs.arn
}

# NEW (with count):
output "bucket_arn" {
  value = try(aws_s3_bucket.logs[0].arn, "NOT DEPLOYED IN THIS REGION")
}
```

### Step 3: Dependent Resources Must Also Skip

```hcl
# If S3 bucket is skipped, bucket versioning must also skip!

resource "aws_s3_bucket_versioning" "logs" {
  count = var.region == "us-east-1" ? 1 : 0  # ← Same condition!
  
  bucket = aws_s3_bucket.logs[0].id
}
```

### Step 4: Test Both Scenarios

```bash
# Test in us-east-1 (should create)
terraform plan -var="region=us-east-1"

# Should show: Plan: X to add

# Test in ap-south-1 (should skip)
terraform plan -var="region=ap-south-1"

# Should show: No changes
```

---

## Important: Use `try()` for Outputs

When resource is skipped with `count = 0`, accessing it causes error.

```hcl
# ❌ WRONG - Will error if count = 0
output "bucket_id" {
  value = aws_s3_bucket.logs[0].id
}

# ✅ RIGHT - Uses try() for safety
output "bucket_id" {
  value = try(aws_s3_bucket.logs[0].id, "NOT DEPLOYED IN THIS REGION")
}

# ✅ ALSO RIGHT - Conditional check
output "bucket_id" {
  value = var.region == "us-east-1" ? aws_s3_bucket.logs[0].id : "NOT DEPLOYED"
}
```

---

## Common Patterns

### Pattern 1: Skip in All Regions Except One

```hcl
locals {
  deploy = var.region == "us-east-1"
}

resource "aws_resource" "example" {
  count = local.deploy ? 1 : 0
}
```

### Pattern 2: Skip in All Regions Except Multiple

```hcl
locals {
  deploy = contains(["us-east-1", "eu-west-1"], var.region)
}

resource "aws_resource" "example" {
  count = local.deploy ? 1 : 0
}
```

### Pattern 3: Skip Based on Environment

```hcl
variable "environment" { type = string }

locals {
  deploy = var.environment == "prod"
}

resource "expensive_resource" "example" {
  count = local.deploy ? 1 : 0
}
```

### Pattern 4: Skip Based on Region AND Environment

```hcl
variable "region" { type = string }
variable "environment" { type = string }

locals {
  is_primary      = var.region == "us-east-1"
  is_production   = var.environment == "prod"
  deploy          = local.is_primary && local.is_production
}

resource "premium_resource" "example" {
  count = local.deploy ? 1 : 0
}
```

---

## Skip Entire Module

Same technique, but apply to module:

```hcl
module "analytics" {
  count = var.region == "us-east-1" ? 1 : 0  # ← Add count
  
  source = "../../modules/analytics"
  region = var.region
}

# Access output with try()
output "analytics_endpoint" {
  value = try(module.analytics[0].endpoint, "NOT DEPLOYED")
}
```

---

## Verification Checklist

Before pushing:
- [ ] `count` added to resource
- [ ] All dependent resources also have `count`
- [ ] Outputs use `try()` for safety
- [ ] Tested with both regions
- [ ] Git status clean
- [ ] Ready to commit

---

## Example File Structure

```
stacks/app/
├── main.tf              ← Add count conditions here
├── variables.tf         ← var.region required
├── outputs.tf           ← Use try() here
├── providers.tf
└── backend.tf
```

---

## Deploy with Your Config

Your `regions.txt`:
```
us-east-1
ap-south-1
```

Your `include.txt`:
```
stacks/app/**
```

Your Terraform (with skip logic):
```hcl
resource "aws_s3_bucket" "logs" {
  count = var.region == "us-east-1" ? 1 : 0
  bucket = "app-logs"
}
```

**Result:**
```
Pipeline creates 2 jobs:
  app + us-east-1   → S3 CREATED ✅
  app + ap-south-1  → S3 SKIPPED ✅
```

---

## For Detailed Guide
See: [SKIP_RESOURCE_BY_REGION.md](SKIP_RESOURCE_BY_REGION.md)

Covers:
- 5 different solutions
- 8 real-world examples
- Combining region + environment
- Gotchas & tips
- Decision tree
