# Visual Guide: Skipping Stacks & Multi-Region S3

## Problem 1: S3 Deployment to Multiple Regions

### ❌ What Fails

```
regions.txt:
  us-east-1
  ap-south-1

stacks/storage/main.tf:
  resource "aws_s3_bucket" "app" {
    bucket = "my-bucket"  ← Same name everywhere!
  }

Pipeline deploys to both regions:
  
  [us-east-1] Create bucket: "my-bucket" ✅
  [ap-south-1] Create bucket: "my-bucket" ❌ FAIL - Already exists!
```

### ✅ What Works

```
stacks/storage/main.tf:
  variable "region" { type = string }
  
  resource "aws_s3_bucket" "app" {
    bucket = "my-bucket-${var.region}"
  }

Pipeline deploys to both regions:
  
  [us-east-1] Create bucket: "my-bucket-us-east-1" ✅
  [ap-south-1] Create bucket: "my-bucket-ap-south-1" ✅
```

---

## Solution Flow: How to Fix S3 Multi-Region

```
┌─────────────────────────────────────────┐
│ Problem: S3 name conflict in 2+ regions │
└─────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Solution: Add region to bucket name      │
│ bucket = "my-bucket-${var.region}"       │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Add region variable to Terraform         │
│ variable "region" { type = string }      │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Workflow passes region automatically     │
│ terraform plan -var="region=${{ region }}"
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ ✅ Each region gets unique bucket!       │
│ my-bucket-us-east-1                      │
│ my-bucket-ap-south-1                     │
└──────────────────────────────────────────┘
```

---

## Problem 2: Skip Stack in Deployment

### Current Setup (includes compute)

```
include.txt:
  stacks/network/**
  stacks/compute/**      ← Want to skip this
  stacks/iam/**

regions.txt:
  us-east-1

Pipeline creates 3 jobs:
  ✅ network + us-east-1
  ✅ compute + us-east-1    ← Don't want this
  ✅ iam + us-east-1
```

### Solution: Remove from include.txt

```
include.txt:
  stacks/network/**
  # stacks/compute/**    ← Commented out = skipped
  stacks/iam/**

Pipeline creates 2 jobs:
  ✅ network + us-east-1
  ✅ iam + us-east-1
```

---

## Solution Flow: How to Skip Stacks

```
┌──────────────────────────────────────────────┐
│ Want to skip deploying compute stack?        │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Edit include.txt                             │
│ Remove or comment: stacks/compute/**         │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Commit and push                              │
│ git add include.txt && git commit && push    │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ Pipeline matrix generator reads include.txt  │
│ Skips stacks not in the list                 │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│ ✅ Compute stack is NOT deployed             │
└──────────────────────────────────────────────┘
```

---

## Complete Example: 3 Stacks × 2 Regions

### Configuration Files

```
include.txt:
  stacks/network/**
  stacks/iam/**
  stacks/storage/**        ← Add this

regions.txt:
  us-east-1
  ap-south-1

dependencies.json:
  {
    "network": [],
    "iam": [],
    "storage": ["network"]  ← Depends on network
  }
```

### Pipeline Execution (Automatic)

```
STAGE 1 (Parallel):
  ┌─────────────────────┐
  │ network + us-east-1 │ → Deploys VPC
  └─────────────────────┘
  ┌─────────────────────┐
  │ network + ap-south-1│ → Deploys VPC
  └─────────────────────┘
  ┌─────────────────────┐
  │ iam + us-east-1     │ → Deploys IAM roles
  └─────────────────────┘
  ┌─────────────────────┐
  │ iam + ap-south-1    │ → Deploys IAM roles
  └─────────────────────┘

Wait for Stage 1 to complete...

STAGE 2 (Parallel, after Stage 1):
  ┌──────────────────────┐
  │ storage + us-east-1  │ → Deploys S3: my-bucket-us-east-1
  └──────────────────────┘
  ┌──────────────────────┐
  │ storage + ap-south-1 │ → Deploys S3: my-bucket-ap-south-1
  └──────────────────────┘

✅ All 8 jobs completed successfully!
   (2 stages × 4 jobs per stage = 8 total)
```

---

## Matrix Generation Logic

```
┌────────────────────────────────────────────┐
│ Input Files                                │
├────────────────────────────────────────────┤
│ include.txt      : network, iam, storage   │
│ regions.txt      : us-east-1, ap-south-1  │
│ dependencies.json: storage→network         │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ scripts/generate_matrix.py processes:      │
├────────────────────────────────────────────┤
│ 1. Load included stacks                    │
│ 2. Load regions                            │
│ 3. Load dependencies                       │
│ 4. Build execution stages                  │
│ 5. Output JSON matrix                      │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ Output Matrix JSON                         │
├────────────────────────────────────────────┤
│ {                                          │
│   "stages": [                              │
│     {                                      │
│       "stacks": ["network", "iam"],        │
│       "regions": ["us-east-1", "ap-south-1"]
│     },                                     │
│     {                                      │
│       "stacks": ["storage"],               │
│       "regions": ["us-east-1", "ap-south-1"]
│     }                                      │
│   ]                                        │
│ }                                          │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ GitHub Actions uses matrix to spawn jobs:  │
├────────────────────────────────────────────┤
│ stage-1 creates: 4 parallel jobs           │
│ stage-2 (after stage-1): 2 parallel jobs   │
└────────────────────────────────────────────┘
```

---

## Decision Tree: How to Handle S3 Multi-Region

```
                    Start
                      │
                      ↓
        Are you deploying S3
           to multiple regions
               same name?
                  /    \
                NO      YES
               /          \
              ✅           Need to change
           Works!       bucket name strategy
                          │
                          ↓
            Add region to bucket name:
        bucket = "my-bucket-${var.region}"
                          │
                          ↓
              Variable "region" defined?
                      /          \
                    YES           NO
                   /               \
                  ✅         Add to variables.tf:
                       variable "region" {
                         type = string
                       }
                          │
                          ↓
              Workflow passes region var?
                      /          \
                    YES           NO
                   /               \
                  ✅         In reusable.yml:
                       terraform plan \
                        -var="region=${{ inputs.region }}"
                          │
                          ↓
                    ✅ Ready to deploy!
```

---

## Decision Tree: How to Skip Stack

```
                Start
                  │
                  ↓
        Want to skip a stack?
            (e.g. compute)
                  │
                  ↓
         Edit include.txt
         Remove or comment:
         # stacks/compute/**
                  │
                  ↓
         Save and commit
         git add include.txt
         git commit -m "Skip compute"
                  │
                  ↓
         Push to main or PR
         git push
                  │
                  ↓
         Pipeline triggers
         Reads include.txt
         Skips compute stack
                  │
                  ↓
          ✅ Stack skipped!
         Compute won't deploy
```

---

## Troubleshooting Matrix

| Problem | Symptom | Solution |
|---------|---------|----------|
| **S3 conflict** | "Bucket already exists" error | Add `${var.region}` to bucket name |
| **Stack deployed when shouldn't** | Stack running but shouldn't | Check `include.txt`, remove pattern |
| **Stack NOT deployed when should** | Stack missing | Check `include.txt`, add pattern |
| **Wrong deployment order** | Stack runs before dependency | Check `dependencies.json` |
| **No jobs created** | Matrix empty | Check `include.txt` is not empty |
| **Parallel jobs conflict** | Resources compete in same region | Ensure unique names (region-aware) |

---

## Files You Edit for Different Changes

| What You Want | Edit This File | Example |
|---------------|---|---|
| Skip a stack | `include.txt` | Remove `stacks/compute/**` |
| Skip a region | `regions.txt` | Remove `ap-south-1` |
| Add dependency | `dependencies.json` | Add `"app": ["network"]` |
| Fix S3 naming | `stacks/storage/main.tf` | Add `${var.region}` |
| Add new stack | `include.txt` | Add `stacks/new-stack/**` |
| Change regions | `regions.txt` | Add/remove regions |

---

For detailed examples, see: [EXAMPLES.md](EXAMPLES.md)
