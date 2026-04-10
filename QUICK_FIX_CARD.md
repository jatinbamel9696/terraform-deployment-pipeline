# ⚡ Quick Fix Card (Save This!)

## Your 2 Questions - Quick Answers

### Q1: S3 Multi-Region Same Name - What Happens?
**A:** ❌ FAILS! S3 names are globally unique.

**Fix in 3 steps:**
```bash
# 1. Edit stacks/storage/main.tf
bucket = "my-bucket-${var.region}"  # Add region

# 2. Add to include.txt
stacks/storage/**

# 3. Push
git add . && git commit -m "Multi-region S3" && git push
```

**Result:** ✅ Buckets: my-bucket-us-east-1, my-bucket-ap-south-1

---

### Q2: Skip Compute Stack - How?
**A:** Edit `include.txt` - remove or comment out the stack.

**Fix in 2 steps:**
```bash
# 1. Edit include.txt - Comment out compute
# stacks/compute/**

# 2. Push
git add . && git commit -m "Skip compute" && git push
```

**Result:** ✅ Compute stack is NOT deployed

---

## Key Patterns

```
TO SKIP:              TO ADD REGION:          TO CHANGE REGIONS:
include.txt           main.tf                 regions.txt

# stacks/compute/**   bucket =                us-east-1
                      "app-${var.region}"     ap-south-1
                                              eu-west-1
```

---

## Files to Edit

| What | File | Change |
|-----|------|--------|
| Skip stack | `include.txt` | Remove/comment pattern |
| Skip region | `regions.txt` | Remove region |
| S3 multi-region | `stacks/*/main.tf` | Add `${var.region}` |
| Dependencies | `dependencies.json` | Update order |

---

## Most Common Mistakes (Avoid These!)

```
❌ WRONG                          ✅ RIGHT
bucket = "my-bucket"             bucket = "my-bucket-${var.region}"
(same everywhere,                (unique per region,
fails on 2nd region)             works everywhere)

include.txt:                      include.txt:
stacks/compute/**                # stacks/compute/**
(still deploys)                  (skipped)

Edit but no commit                Edit & commit & push
(changes don't apply)             (changes apply)
```

---

## Quick Commands

```bash
# Verify what will deploy
python scripts/generate_matrix.py all all

# Test Terraform locally
cd stacks/network
terraform init -backend=false
terraform plan -var="region=us-east-1"

# Check git status before push
git status

# Push changes
git add .
git commit -m "Your message"
git push origin main
```

---

## Decision Flowchart

```
Multi-region S3?
  ├─ YES → Add ${var.region} to bucket name ✅
  └─ NO  → Use fixed bucket name ✅

Skip a stack?
  ├─ YES → Remove from include.txt ✅
  └─ NO  → Keep in include.txt ✅

Skip a region?
  ├─ YES → Remove from regions.txt ✅
  └─ NO  → Keep all regions ✅
```

---

## Before You Push

Checklist:
- [ ] Bucket name has `${var.region}` (if multi-region)
- [ ] `variable "region"` defined
- [ ] `include.txt` has correct stacks
- [ ] `regions.txt` has correct regions
- [ ] Committed changes: `git status` clean
- [ ] Ready to push: `git push origin main`

---

## Troubleshooting Quick Fixes

| Problem | Fix |
|---------|-----|
| Bucket conflict | Add `${var.region}` to bucket name |
| Stack shouldn't deploy | Remove from `include.txt` |
| Stack not deploying | Add to `include.txt` |
| Credentials error | Check `ASSUME_ROLE_ARN` secret in GitHub |
| No jobs created | Check `include.txt` not empty |

---

## Documentation Shortcuts

**Your exact questions:**
→ [YOUR_QUESTIONS_ANSWERED.md](YOUR_QUESTIONS_ANSWERED.md)

**Visual explanation:**
→ [VISUAL_GUIDE.md](VISUAL_GUIDE.md)

**Real examples:**
→ [EXAMPLES.md](EXAMPLES.md)

**Quick lookup:**
→ [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

**Complete guide:**
→ [SETUP_GUIDE.md](SETUP_GUIDE.md)

**All files index:**
→ [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

---

## Remember These 2 Rules

### Rule 1: S3 Multi-Region
```
bucket = "unique-name-${var.region}"
```
Always include region for global resources!

### Rule 2: Skip Stacks
```
# Comment out in include.txt to skip
# stacks/compute/**
```
Not in include.txt = Not deployed!

---

## Git Workflow (Copy-Paste Ready)

```bash
# Make changes to files...

# Verify changes
git status

# Stage changes
git add .

# Commit with message
git commit -m "Add multi-region S3 and skip compute"

# Push to main
git push origin main

# Watch GitHub Actions run
# → Go to Actions tab
# → Click latest workflow
# → Watch it deploy! ✅
```

---

**Print this page or save as bookmark! 📌**

Questions? → See [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)
