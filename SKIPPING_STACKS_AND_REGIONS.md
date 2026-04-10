# Skipping Stacks and Managing Multi-Region Deployments

## How to Skip Stacks (e.g., Skip Compute)

### Method 1: Modify `include.txt` (Recommended)

The `include.txt` file controls which stacks are deployed. Simply comment out or remove stacks you want to skip.

**Current Configuration** (`include.txt`):
```
stacks/network/**
stacks/iam/**
```

**To skip compute stack**: Remove it from the list (it's already not included above).

**To include compute stack**: Add it back:
```
stacks/network/**
stacks/compute/**
stacks/iam/**
```

**To skip IAM temporarily**: Comment it out:
```
stacks/network/**
# stacks/iam/**       # Skipped for now
stacks/compute/**
```

### How It Works

1. The matrix generation script (`scripts/generate_matrix.py`) reads `include.txt`
2. It only includes stacks listed in `include.txt`
3. Removed stacks are completely skipped from the pipeline
4. No jobs are created for skipped stacks

### Example Scenarios

**Scenario 1: Deploy only network (development)**
```
stacks/network/**
```

**Scenario 2: Skip compute, deploy everything else (hotfix)**
```
stacks/network/**
stacks/iam/**
stacks/storage/**
```

**Scenario 3: Deploy all stacks (production)**
```
stacks/network/**
stacks/compute/**
stacks/iam/**
stacks/storage/**
```

---

## Multi-Region S3 Deployments - Global Uniqueness

### Problem: S3 Bucket Names Are Globally Unique

S3 bucket names must be **unique across ALL AWS accounts and ALL regions**. You cannot have the same bucket name in two regions.

❌ **This will FAIL**:
```hcl
# Region 1 (us-east-1)
resource "aws_s3_bucket" "app" {
  bucket = "my-app-bucket"
}

# Region 2 (ap-south-1)
resource "aws_s3_bucket" "app" {
  bucket = "my-app-bucket"  # ERROR: Already exists in us-east-1!
}
```

### Solution 1: Use Region in Bucket Name (RECOMMENDED)

✅ **This works**:
```hcl
resource "aws_s3_bucket" "app" {
  bucket = "my-app-bucket-${var.region}"
  # Results in:
  # - my-app-bucket-us-east-1
  # - my-app-bucket-ap-south-1
}
```

**Variables needed**:
```hcl
variable "region" {
  description = "AWS region"
  type        = string
}
```

**Pass from workflow**:
```yaml
terraform plan -var="region=${{ matrix.region }}"
```

### Solution 2: Use Account ID and Region

✅ **More unique (recommended for multi-account)**:
```hcl
variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

resource "aws_s3_bucket" "app" {
  bucket = "${var.environment}-app-${var.aws_account_id}-${var.region}"
  # Results in: prod-app-123456789012-us-east-1
}
```

### Solution 3: Use Data Source to Get Account ID

```hcl
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "app" {
  bucket = "app-${data.aws_caller_identity.current.account_id}-${var.region}"
}
```

### Solution 4: Separate Stacks per Region (Not Recommended)

Instead of deploying same stack to multiple regions, create separate stacks:

```
stacks/
  storage-us-east-1/
    main.tf
    backend.tf
  storage-ap-south-1/
    main.tf
    backend.tf
```

Not recommended because it duplicates code.

---

## Complete Example: Multi-Region S3 Stack

**File: `stacks/storage/main.tf`**

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Global unique bucket name with region
resource "aws_s3_bucket" "app_bucket" {
  bucket = "my-company-data-${var.environment}-${var.region}"
  
  tags = {
    Environment = var.environment
    Region      = var.region
  }
}

# Enable versioning for safety
resource "aws_s3_bucket_versioning" "app_bucket" {
  bucket = aws_s3_bucket.app_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "app_bucket" {
  bucket = aws_s3_bucket.app_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "app_bucket" {
  bucket = aws_s3_bucket.app_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

**File: `stacks/storage/variables.tf`**

```hcl
variable "region" {
  description = "AWS region"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}
```

**File: `stacks/storage/outputs.tf`**

```hcl
output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.app_bucket.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.app_bucket.arn
}
```

**File: `stacks/storage/backend.tf`**

```hcl
terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    key            = "storage/${var.region}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
  }
}
```

---

## Multi-Region Deployment via Pipeline

### Setup `regions.txt`

```
us-east-1
ap-south-1
eu-west-1
```

### Workflow passes region to Terraform

**In `.github/workflows/reusable.yml`**:

```yaml
- name: Terraform Plan
  working-directory: stacks/${{ inputs.stack }}
  run: |
    terraform plan -var="region=${{ inputs.region }}" -out=tfplan
```

### Result: Parallel Deployments

For each region and stack:
- **stacks/storage + us-east-1** → bucket: `my-company-data-dev-us-east-1`
- **stacks/storage + ap-south-1** → bucket: `my-company-data-dev-ap-south-1`
- **stacks/storage + eu-west-1** → bucket: `my-company-data-dev-eu-west-1`

All deployed in parallel!

---

## Summary: Skipping vs Multi-Region

| Scenario | How to Do It |
|----------|-------------|
| Skip compute stack | Remove `stacks/compute/**` from `include.txt` |
| Deploy only to us-east-1 | Remove other regions from `regions.txt` |
| Deploy same stack to multiple regions | Keep in `include.txt`, keep regions in `regions.txt`, use `${var.region}` in resource names |
| Deploy different stacks per region | Use conditional in Terraform (advanced) |
| Temporary skip for debugging | Comment out in `include.txt` with `#` |

---

## Common Gotchas

1. **S3 bucket name conflicts**: Always include region/account in name
2. **Forgetting var.region**: Pass it in workflow commands
3. **Forgetting to commit**: `include.txt` changes must be committed
4. **Backend key format**: Use `${var.region}` in backend.tf key path
5. **State file isolation**: Different regions need different state keys

---

## Next Steps

1. Update `include.txt` to include/exclude stacks
2. Update `regions.txt` to add/remove regions
3. Update S3 bucket names to include region (if multi-region)
4. Commit and push to test in CI/CD
