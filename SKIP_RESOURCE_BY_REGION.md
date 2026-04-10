# Skip Resources/Modules from Specific Regions

Advanced guide for selectively deploying resources by region.

---

## Problem: Skip Resource in Specific Region

You want to deploy most resources everywhere, but skip certain resources in specific regions.

**Example Scenarios:**
- Deploy S3 only in us-east-1 (not in ap-south-1)
- Deploy compute only in certain regions
- Deploy expensive resources only in production region
- Skip RDS backup in staging region

---

## Solution 1: Use `count` with Region Variable (Easiest)

### Example: Deploy S3 Only in us-east-1

**File: `stacks/storage/main.tf`**

```hcl
variable "region" {
  type = string
}

# Deploy S3 only in us-east-1
resource "aws_s3_bucket" "app_data" {
  count = var.region == "us-east-1" ? 1 : 0
  
  bucket = "my-app-${var.region}"
  
  tags = {
    Region = var.region
  }
}

resource "aws_s3_bucket_versioning" "app_data" {
  count = var.region == "us-east-1" ? 1 : 0
  
  bucket = aws_s3_bucket.app_data[0].id
  
  versioning_configuration {
    status = "Enabled"
  }
}

output "bucket_name" {
  value = try(aws_s3_bucket.app_data[0].id, "NOT DEPLOYED IN THIS REGION")
}
```

### How It Works

```
count = var.region == "us-east-1" ? 1 : 0

Meaning:
  If region == us-east-1 → count = 1 (create resource)
  If region != us-east-1 → count = 0 (skip resource)
```

### Result

```
Deployment:
  storage + us-east-1   → S3 bucket CREATED ✅
  storage + ap-south-1  → S3 bucket SKIPPED ✅
```

---

## Solution 2: Use Variable List (More Flexible)

### Example: Deploy in Multiple Specific Regions

**File: `stacks/compute/main.tf`**

```hcl
variable "region" {
  type = string
}

# Allowed regions for compute
locals {
  compute_regions = ["us-east-1", "eu-west-1"]
  deploy_compute  = contains(local.compute_regions, var.region)
}

resource "aws_instance" "app_server" {
  count = local.deploy_compute ? 1 : 0
  
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
  
  tags = {
    Region = var.region
  }
}

output "instance_id" {
  value = try(aws_instance.app_server[0].id, "NOT DEPLOYED IN THIS REGION")
}
```

### Result

```
Deployment:
  compute + us-east-1   → EC2 CREATED ✅
  compute + ap-south-1  → EC2 SKIPPED ✅
  compute + eu-west-1   → EC2 CREATED ✅
```

### Easy to Modify

```hcl
# Deploy everywhere
locals {
  compute_regions = ["us-east-1", "ap-south-1", "eu-west-1"]
}

# Deploy only expensive regions
locals {
  compute_regions = ["us-east-1"]
}

# Deploy everywhere except one
locals {
  compute_regions = ["us-east-1", "ap-south-1", "eu-west-1"]
  # Exclude ap-south-1 for staging
  compute_regions = local.region_all
  deploy_compute  = contains(local.compute_regions, var.region)
}
```

---

## Solution 3: Use Variable Flag (Most Control)

### Example: Control Deployment via Variable

**File: `stacks/backup/main.tf`**

```hcl
variable "region" {
  type = string
}

variable "deploy_backup" {
  description = "Deploy backup resources in this region"
  type        = bool
  default     = true
}

resource "aws_backup_vault" "main" {
  count         = var.deploy_backup ? 1 : 0
  name          = "app-backup-${var.region}"
  force_destroy = true
  
  tags = {
    Region = var.region
  }
}

output "backup_vault_id" {
  value = try(aws_backup_vault.main[0].id, "BACKUP NOT DEPLOYED")
}
```

**File: `stacks/backup/terraform.tfvars` (for local testing)**

```hcl
region         = "us-east-1"
deploy_backup  = true
```

**File: `stacks/backup/terraform.tfvars.staging` (for staging)**

```hcl
region         = "ap-south-1"
deploy_backup  = false
```

---

## Solution 4: Skip Entire Module from Region

### Example: Module with Region Control

**File: `stacks/data-pipeline/main.tf`**

```hcl
variable "region" {
  type = string
}

variable "enable_data_pipeline" {
  description = "Enable data pipeline in this region"
  type        = bool
  default     = var.region == "us-east-1"  # Only in us-east-1
}

module "data_pipeline" {
  count = var.enable_data_pipeline ? 1 : 0
  
  source = "../../modules/data-pipeline"
  
  region = var.region
  
  # Other variables...
}

# Access module outputs conditionally
output "pipeline_arn" {
  value = try(module.data_pipeline[0].arn, "PIPELINE NOT DEPLOYED IN THIS REGION")
}
```

### Result

```
Deployment:
  data-pipeline + us-east-1   → Module deployed ✅
  data-pipeline + ap-south-1  → Module skipped ✅
```

---

## Solution 5: Modify Workflow Matrix (Advanced)

Skip entire stack from specific regions at the pipeline level.

### Before: Deploy All Stacks to All Regions

```
regions.txt:
  us-east-1
  ap-south-1

Pipeline creates matrix:
  storage + us-east-1
  storage + ap-south-1
  compute + us-east-1
  compute + ap-south-1
```

### After: Skip Storage from ap-south-1

**Modify: `scripts/generate_matrix.py`**

```python
def get_allowed_regions(stack):
    """Returns allowed regions for each stack"""
    region_overrides = {
        "storage": ["us-east-1"],           # Storage only in us-east-1
        "compute": ["us-east-1", "ap-south-1"],  # Compute everywhere
        "network": ["us-east-1", "ap-south-1"],  # Network everywhere
    }
    return region_overrides.get(stack, all_regions)

def main():
    # ... existing code ...
    
    for stage in stages:
        for stack in stage:
            allowed_regions = get_allowed_regions(stack)
            for region in allowed_regions:
                output["flat"].append({"stack": stack, "region": region})
    
    print(json.dumps(output))
```

### Result

```
Matrix now creates:
  storage + us-east-1      ✅
  storage + ap-south-1     ❌ Skipped
  compute + us-east-1      ✅
  compute + ap-south-1     ✅
  network + us-east-1      ✅
  network + ap-south-1     ✅
```

---

## Real-World Examples

### Example 1: Expensive Resource Only in Production

**File: `stacks/analytics/main.tf`**

```hcl
variable "region" {
  type = string
}

variable "environment" {
  type    = string
  default = "dev"
}

locals {
  is_production = var.environment == "prod"
  is_us_east    = var.region == "us-east-1"
  deploy_redshift = local.is_production && local.is_us_east
}

resource "aws_redshift_cluster" "analytics" {
  count = local.deploy_redshift ? 1 : 0
  
  cluster_identifier = "analytics-${var.region}"
  node_type          = "ra3.xlplus"
  number_of_nodes    = 3
  
  tags = {
    Environment = var.environment
    Region      = var.region
  }
}

output "redshift_cluster_id" {
  value = try(
    aws_redshift_cluster.analytics[0].id,
    "REDSHIFT NOT DEPLOYED (Not production or not us-east-1)"
  )
}
```

### Example 2: Database Only in Specific Regions

**File: `stacks/database/main.tf`**

```hcl
variable "region" {
  type = string
}

locals {
  # Deploy RDS in these regions
  rds_regions = ["us-east-1", "eu-west-1"]
  deploy_rds  = contains(local.rds_regions, var.region)
}

resource "aws_db_instance" "main" {
  count = local.deploy_rds ? 1 : 0
  
  identifier     = "app-db-${var.region}"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_encrypted = true
  
  tags = {
    Region = var.region
  }
}

output "db_endpoint" {
  value = try(
    aws_db_instance.main[0].endpoint,
    "DATABASE NOT DEPLOYED IN THIS REGION"
  )
}
```

### Example 3: Skip Multiple Resources Based on Region

**File: `stacks/hybrid/main.tf`**

```hcl
variable "region" {
  type = string
}

locals {
  deploy_in_all_regions = true
  
  # Deploy storage only in primary region
  deploy_storage     = var.region == "us-east-1"
  
  # Deploy compute everywhere
  deploy_compute     = true
  
  # Deploy database only in production regions
  deploy_database    = contains(["us-east-1", "eu-west-1"], var.region)
  
  # Deploy cache in all regions
  deploy_cache       = true
}

# Storage layer (primary region only)
resource "aws_s3_bucket" "data" {
  count  = local.deploy_storage ? 1 : 0
  bucket = "app-data-${var.region}"
}

# Compute layer (all regions)
resource "aws_instance" "app" {
  count             = local.deploy_compute ? 1 : 0
  ami               = "ami-0c55b159cbfafe1d0"
  instance_type     = "t2.micro"
  availability_zone = "${var.region}a"
}

# Database layer (specific regions)
resource "aws_db_instance" "main" {
  count      = local.deploy_database ? 1 : 0
  identifier = "app-db-${var.region}"
  engine     = "postgres"
  instance_class = "db.t3.micro"
}

# Cache layer (all regions)
resource "aws_elasticache_cluster" "cache" {
  count           = local.deploy_cache ? 1 : 0
  cluster_id      = "app-cache-${var.region}"
  engine          = "redis"
  node_type       = "cache.t3.micro"
  num_cache_nodes = 1
}

output "deployment_summary" {
  value = {
    region      = var.region
    storage     = local.deploy_storage ? "✅ Deployed" : "⏭️ Skipped"
    compute     = local.deploy_compute ? "✅ Deployed" : "⏭️ Skipped"
    database    = local.deploy_database ? "✅ Deployed" : "⏭️ Skipped"
    cache       = local.deploy_cache ? "✅ Deployed" : "⏭️ Skipped"
  }
}
```

---

## Configuration Methods Comparison

| Method | Use Case | Complexity | Flexibility |
|--------|----------|-----------|------------|
| **Solution 1: `count` with region check** | Skip in 1-2 regions | ⭐ Easy | ⭐ Low |
| **Solution 2: List of allowed regions** | Skip in multiple regions | ⭐⭐ Medium | ⭐⭐ Medium |
| **Solution 3: Variable flag** | Control via variables | ⭐⭐ Medium | ⭐⭐⭐ High |
| **Solution 4: Module with count** | Skip entire module | ⭐⭐ Medium | ⭐⭐⭐ High |
| **Solution 5: Workflow matrix filter** | Skip at pipeline level | ⭐⭐⭐ Advanced | ⭐⭐⭐ High |

---

## Combining with Environment Variables

### Example: Use Both Region AND Environment

**File: `stacks/app/main.tf`**

```hcl
variable "region" {
  type = string
}

variable "environment" {
  type = string
}

locals {
  # Expensive resources only in production + primary region
  is_production = var.environment == "prod"
  is_primary    = var.region == "us-east-1"
  
  deploy_multi_az   = local.is_production && local.is_primary
  deploy_monitoring = local.is_production
  deploy_app        = true
}

# Application (always)
resource "aws_instance" "app" {
  count      = local.deploy_app ? 1 : 0
  instance_type = "t2.micro"
  # ...
}

# Monitoring (production only)
resource "aws_cloudwatch_log_group" "app" {
  count = local.deploy_monitoring ? 1 : 0
  name  = "/aws/ec2/app-${var.environment}-${var.region}"
  # ...
}

# Multi-AZ (production + primary region only)
resource "aws_db_instance" "main" {
  count = local.deploy_multi_az ? 1 : 0
  multi_az = true
  # ... expensive multi-AZ config
}
```

---

## Quick Implementation Steps

### Step 1: Identify What to Skip

```hcl
# In your main.tf, identify the resource:
resource "aws_s3_bucket" "logs" {
  bucket = "app-logs-${var.region}"
}
```

### Step 2: Add Skip Logic

```hcl
resource "aws_s3_bucket" "logs" {
  count = var.region == "us-east-1" ? 1 : 0  # ← Add this line
  
  bucket = "app-logs-${var.region}"
}
```

### Step 3: Update References

```hcl
# If other resources reference this:
# OLD: aws_s3_bucket.logs.id
# NEW: aws_s3_bucket.logs[0].id

# Or use try() for safety:
output "bucket_id" {
  value = try(aws_s3_bucket.logs[0].id, "NOT DEPLOYED")
}
```

### Step 4: Test

```bash
# Test in us-east-1 (should create)
terraform init
terraform plan -var="region=us-east-1"

# Test in ap-south-1 (should NOT create)
terraform plan -var="region=ap-south-1"
```

---

## Common Patterns

### Pattern 1: Region-Specific Deployments

```hcl
locals {
  # Availability by region
  services = {
    storage  = ["us-east-1"]
    compute  = ["us-east-1", "ap-south-1"]
    database = ["us-east-1", "eu-west-1"]
  }
}

# Use it:
resource "aws_s3_bucket" "storage" {
  count = contains(local.services.storage, var.region) ? 1 : 0
}
```

### Pattern 2: Environment-Based Deployment

```hcl
variable "environment" {
  type = string
}

locals {
  # Production gets everything, dev/staging gets limited
  deploy_premium = var.environment == "prod"
}

resource "aws_rds_cluster" "premium" {
  count = local.deploy_premium ? 1 : 0
}
```

### Pattern 3: Cost Control

```hcl
locals {
  # Expensive features only in primary region
  is_primary = var.region == "us-east-1"
  enable_premium = local.is_primary
}

resource "aws_opensearch_domain" "analytics" {
  count = local.enable_premium ? 1 : 0
  # Only in us-east-1 to save costs
}
```

---

## Outputs When Resource Skipped

### Method 1: Use `try()`

```hcl
output "bucket_id" {
  value = try(aws_s3_bucket.logs[0].id, "NOT DEPLOYED")
}
```

### Method 2: Use Conditional

```hcl
output "bucket_id" {
  value = var.region == "us-east-1" ? aws_s3_bucket.logs[0].id : "NOT DEPLOYED"
}
```

### Method 3: Structured Output

```hcl
output "deployment_status" {
  value = {
    region  = var.region
    storage = var.region == "us-east-1" ? aws_s3_bucket.logs[0].id : null
    created = var.region == "us-east-1"
  }
}
```

---

## Gotchas & Tips

### ⚠️ Gotcha 1: Dependent Resources Must Also Be Skipped

```hcl
# ❌ WRONG - S3 bucket may not exist!
resource "aws_s3_bucket" "logs" {
  count = var.region == "us-east-1" ? 1 : 0
  bucket = "logs"
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs[0].id  # ERROR if count=0!
}

# ✅ RIGHT - Skip dependent resource too
resource "aws_s3_bucket_versioning" "logs" {
  count = var.region == "us-east-1" ? 1 : 0  # ← Add count here too
  bucket = aws_s3_bucket.logs[0].id
}
```

### ⚠️ Gotcha 2: Module Outputs May Not Exist

```hcl
# ❌ WRONG - Module outputs may not exist if count=0
output "bucket_arn" {
  value = module.storage[0].bucket_arn  # ERROR if count=0!
}

# ✅ RIGHT - Use try()
output "bucket_arn" {
  value = try(module.storage[0].bucket_arn, "NOT DEPLOYED")
}
```

### 💡 Tip 1: Use Locals for Readability

```hcl
# Better than repeating conditions
locals {
  deploy_storage = var.region == "us-east-1"
}

resource "aws_s3_bucket" "logs" {
  count = local.deploy_storage ? 1 : 0
}

resource "aws_s3_bucket_versioning" "logs" {
  count = local.deploy_storage ? 1 : 0
}
```

### 💡 Tip 2: Document Why Resource is Skipped

```hcl
# Expensive - only in primary region
resource "aws_elasticsearch_domain" "analytics" {
  count = var.region == "us-east-1" ? 1 : 0
  # ...
}

output "analytics_note" {
  value = var.region == "us-east-1" ? "Deployed" : "Not deployed in secondary regions (cost optimization)"
}
```

---

## Quick Decision Tree

```
Want to skip resource in specific region?
    │
    ├─ YES, skip in ONE region
    │  └─ Use: count = var.region == "primary" ? 1 : 0
    │
    ├─ YES, skip in MULTIPLE regions
    │  └─ Use: locals with list + contains()
    │
    ├─ YES, skip based on ENVIRONMENT
    │  └─ Use: variable flag + count
    │
    ├─ YES, skip ENTIRE MODULE
    │  └─ Use: module with count
    │
    └─ YES, skip at WORKFLOW LEVEL
       └─ Modify: scripts/generate_matrix.py
```

---

## Summary

| Task | Solution |
|------|----------|
| Skip S3 in ap-south-1 | `count = var.region == "us-east-1" ? 1 : 0` |
| Skip in 2+ regions | Use `locals` with list + `contains()` |
| Skip by environment | Add `variable` flag, use in `count` |
| Skip entire module | Add `count` to `module` block |
| Skip at pipeline | Modify `generate_matrix.py` |
| Handle missing resource | Use `try()` in outputs |

All examples above show production-ready patterns! 🚀
