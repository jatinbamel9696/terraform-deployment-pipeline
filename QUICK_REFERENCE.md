# Quick Reference: Skipping Stacks & Multi-Region S3

## Skip Stacks - Quick Guide

### Current `include.txt`:
```
stacks/network/**
stacks/iam/**
```

### To Skip Compute (Already Skipped)
✅ Compute is already NOT in `include.txt`, so it won't deploy.

### To Add Compute Back:
```
stacks/network/**
stacks/compute/**     # Add this line
stacks/iam/**
```

### To Temporarily Skip IAM:
```
stacks/network/**
# stacks/iam/**       # Comment out with #
```

### To Deploy ONLY Network:
```
stacks/network/**
```

---

## S3 Bucket Names - Quick Guide

### ❌ DON'T DO THIS (Will Fail):
```hcl
resource "aws_s3_bucket" "app" {
  bucket = "my-app-bucket"  # Same name for all regions = FAIL
}
```

### ✅ DO THIS INSTEAD (Region-Aware):
```hcl
resource "aws_s3_bucket" "app" {
  bucket = "my-app-bucket-${var.region}"
  # Creates: my-app-bucket-us-east-1, my-app-bucket-ap-south-1, etc.
}
```

### ✅ OR THIS (More Unique):
```hcl
resource "aws_s3_bucket" "app" {
  bucket = "my-company-${var.environment}-${var.region}"
  # Creates: my-company-dev-us-east-1, my-company-prod-ap-south-1, etc.
}
```

---

## File Locations for Changes

| What to Change | File | Action |
|---|---|---|
| Skip stacks | `include.txt` | Remove/comment out stack patterns |
| Change regions | `regions.txt` | Add/remove regions |
| Bucket naming | `stacks/*/main.tf` | Add `${var.region}` to bucket name |
| Dependencies | `dependencies.json` | Update if stacks depend on each other |

---

## Real Example

### Current Setup (Network + IAM only, 2 regions)

**include.txt**:
```
stacks/network/**
stacks/iam/**
```

**regions.txt**:
```
us-east-1
ap-south-1
```

**Result**: 4 jobs (2 stacks × 2 regions)
- network + us-east-1
- network + ap-south-1
- iam + us-east-1
- iam + ap-south-1

### If You Add Storage Stack

**include.txt**:
```
stacks/network/**
stacks/iam/**
stacks/storage/**
```

**Result**: 6 jobs (3 stacks × 2 regions)
- network + us-east-1
- network + ap-south-1
- iam + us-east-1
- iam + ap-south-1
- storage + us-east-1 → Creates bucket: `my-app-bucket-us-east-1`
- storage + ap-south-1 → Creates bucket: `my-app-bucket-ap-south-1`

### If You Skip Compute & Only Deploy to us-east-1

**include.txt**:
```
stacks/network/**
stacks/iam/**
```

**regions.txt**:
```
us-east-1
```

**Result**: 2 jobs (2 stacks × 1 region)
- network + us-east-1
- iam + us-east-1

---

## Common Questions

**Q: How do I know if compute is skipped?**
A: Check `include.txt`. If `stacks/compute/**` is NOT there, it's skipped.

**Q: What if I forget the region in S3 bucket name?**
A: Second deployment will FAIL because bucket name already exists.

**Q: Can I deploy different stacks to different regions?**
A: Not easily with current setup. All stacks deploy to all regions. For per-region stacks, see advanced section in `SKIPPING_STACKS_AND_REGIONS.md`.

**Q: Does `include.txt` need to be committed?**
A: Yes! Push changes to trigger pipeline.

**Q: How many regions can I deploy to?**
A: Unlimited. Add to `regions.txt`, one per line.

---

## Example Changes

### Add Storage Stack + Keep Same S3 Naming Pattern

**1. Create `stacks/storage/main.tf`**:
```hcl
resource "aws_s3_bucket" "app" {
  bucket = "my-app-bucket-${var.region}"
}
```

**2. Add to `include.txt`**:
```
stacks/network/**
stacks/iam/**
stacks/storage/**
```

**3. Commit & push** → Pipeline runs → S3 buckets created in both regions with unique names!

---

## Debug: Check What Will Deploy

Before committing, check what the matrix generator will create:

```bash
cd /path/to/repo
python scripts/generate_matrix.py all all
```

Output shows all stacks × regions that will be deployed.

---

For detailed guide, see: [SKIPPING_STACKS_AND_REGIONS.md](SKIPPING_STACKS_AND_REGIONS.md)
