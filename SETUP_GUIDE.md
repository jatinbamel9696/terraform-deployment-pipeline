# Terraform CI/CD Pipeline - Setup Guide

This guide walks you through setting up the complete Terraform CI/CD pipeline with GitHub Actions.

## Prerequisites

- AWS Account with IAM permissions
- GitHub Repository with Actions enabled
- Git CLI (optional, for local testing)

---

## Step 1: Create AWS IAM Role for GitHub OIDC

### 1.1 Create OpenID Connect (OIDC) Provider

1. Go to AWS Console → IAM → Identity Providers
2. Click "Add Provider"
3. Select "OpenID Connect"
4. Fill in:
   - **Provider URL**: `https://token.actions.githubusercontent.com`
   - **Audience**: `sts.amazonaws.com`
5. Click "Add Provider"

### 1.2 Create IAM Role

1. Go to IAM → Roles → Create Role
2. Select "Web Identity" as the trusted entity type
3. Choose:
   - **Identity Provider**: `token.actions.githubusercontent.com`
   - **Audience**: `sts.amazonaws.com`
4. Click Next
5. **Attach Permissions** (minimum required):
   ```
   - AmazonS3FullAccess (for S3 backend)
   - AmazonDynamoDBFullAccess (for state locking)
   - AmazonEC2FullAccess (for compute resources)
   - AmazonVPCFullAccess (for network resources)
   - IAMFullAccess (for IAM resources)
   ```
   Or create a custom policy with specific permissions
6. Name the role: `github-actions-terraform-role`
7. Click Create

### 1.3 Update Trust Relationship

Go to the created role → Trust relationships → Edit trust policy:

Replace with:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_USERNAME/terraform-deployment-pipeline:*"
        }
      }
    }
  ]
}
```

Replace:
- `ACCOUNT_ID` with your AWS Account ID
- `YOUR_GITHUB_USERNAME` with your GitHub username

---

## Step 2: Create S3 Backend and DynamoDB Table

### 2.1 Create S3 Bucket

```bash
aws s3api create-bucket \
  --bucket s3-backend-git-9696 \
  --region us-east-1
```

Enable versioning:
```bash
aws s3api put-bucket-versioning \
  --bucket s3-backend-git-9696 \
  --versioning-configuration Status=Enabled
```

Enable encryption:
```bash
aws s3api put-bucket-encryption \
  --bucket s3-backend-git-9696 \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'
```

### 2.2 Create DynamoDB Table

```bash
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

---

## Step 3: Add GitHub Secrets

Go to your GitHub Repository → Settings → Secrets and Variables → Actions

### Add the following secrets:

| Secret Name | Value |
|---|---|
| `ASSUME_ROLE_ARN` | `arn:aws:iam::ACCOUNT_ID:role/github-actions-terraform-role` |
| `AWS_ROLE_SESSION_NAME` | `GitHubActions` (optional, defaults if not set) |

Replace `ACCOUNT_ID` with your actual AWS Account ID.

---

## Step 4: Verify Configuration

### 4.1 Repository Structure

Ensure your repo has:

```
.github/
  workflows/
    plan.yml           # PR plan workflow
    apply.yml          # Push apply workflow
    drift.yml          # Scheduled drift detection
    reusable.yml       # Reusable workflow (called by others)
scripts/
  generate_matrix.py   # Dynamic matrix generation
stacks/
  network/
    main.tf
    providers.tf
    variables.tf
    backend.tf
  iam/
    main.tf
    providers.tf
    variables.tf
    backend.tf
  compute/
    main.tf
    providers.tf
    variables.tf
    backend.tf
modules/
  vpc/
    main.tf
  s3/
    main.tf
include.txt            # Stacks to deploy
regions.txt            # Regions to deploy to
dependencies.json      # Stack dependencies
```

### 4.2 Test the Pipeline

1. Create a test branch
2. Make a change to `stacks/network/main.tf`
3. Open a Pull Request
4. Watch the "Terraform Plan" workflow execute
5. Verify the plan output in PR comments

---

## Step 5: Workflow Files Explained

### `plan.yml` (PR Workflow)
- Triggers on: Pull Requests to `main`
- Generates matrix of affected stacks
- Runs `terraform plan` (read-only)
- Can be used to review changes before merging

### `apply.yml` (Push Workflow)
- Triggers on: Push to `main`
- Runs `terraform apply` with dependency ordering
- Uses staged execution to respect dependencies
- Automatic deployment

### `drift.yml` (Drift Detection)
- Triggers on: Daily schedule (6 AM UTC)
- Runs `terraform plan -detailed-exitcode`
- Detects infrastructure drift
- Fails if drift detected

### `reusable.yml` (Shared Workflow)
- Called by plan, apply, and drift workflows
- Handles: init, validate, fmt check, plan/apply
- Supports multiple commands via matrix

---

## Step 6: Matrix Generation

The `scripts/generate_matrix.py` script:
- Detects changed files from git diffs
- Filters stacks using `include.txt`
- Resolves dependencies from `dependencies.json`
- Creates parallel execution stages

### How to Add New Stacks

1. Create folder: `stacks/new-stack/`
2. Add Terraform files
3. Update `dependencies.json` with dependencies (if any)
4. Update `include.txt` to include it
5. Add to `include.txt`:
   ```
   stacks/new-stack/**
   ```

---

## Step 7: Configuration Files

### `include.txt`
Controls which stacks are deployed:
```
stacks/network/**
stacks/compute/**
stacks/iam/**
```

### `regions.txt`
Multi-region deployment:
```
us-east-1
ap-south-1
```

### `dependencies.json`
Defines deployment order:
```json
{
  "network": [],
  "compute": ["network"],
  "iam": []
}
```

---

## Troubleshooting

### "Credentials could not be loaded"

**Cause**: ASSUME_ROLE_ARN secret not set or invalid

**Fix**:
1. Verify secret exists in GitHub: Settings → Secrets
2. Verify ARN format: `arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME`
3. Verify role trust relationship includes your GitHub repo

### "No changes detected"

**Cause**: No Terraform files changed in PR

**Fix**: This is expected behavior. No jobs run if no affected stacks.

### "Dependency ordering wrong"

**Cause**: `dependencies.json` doesn't match actual dependencies

**Fix**: Update `dependencies.json` with correct dependency tree

### "Plan passes but Apply fails"

**Cause**: State file permissions or AWS credentials changed

**Fix**:
1. Check IAM role permissions
2. Verify S3 bucket and DynamoDB table exist
3. Check backend configuration in `backend.tf` files

---

## Production Best Practices

1. **Enable Terraform State Locking**: Already configured with DynamoDB
2. **Use Quality Checks**: Included in reusable workflow
3. **Require PR Reviews**: Add branch protection rules
4. **Enable Drift Detection**: Scheduled daily
5. **Lock Down Secrets**: Restrict secret access to trusted roles
6. **Audit IAM Role**: Review permissions regularly
7. **Enable S3 Versioning**: Enabled in setup script above
8. **Use Variable Files**: Store `.tfvars` separately (not in repo)

---

## Next Steps

1. Set up backend bucket and DynamoDB table (Step 2)
2. Create IAM role with OIDC (Step 1)
3. Add GitHub secrets (Step 3)
4. Push to repository
5. Create a test PR to verify workflow execution

For issues or questions, check workflow run logs in GitHub Actions.
