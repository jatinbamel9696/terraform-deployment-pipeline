# GitHub Secrets Quick Reference

## Required Secrets for CI/CD Pipeline

Add these to your GitHub repository under: **Settings → Secrets and variables → Actions**

### ASSUME_ROLE_ARN (Required)

**Value**: Your AWS IAM role ARN for GitHub Actions

```
arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-terraform-role
```

**Example**:
```
arn:aws:iam::123456789012:role/github-actions-terraform-role
```

Replace `123456789012` with your AWS Account ID.

---

### AWS_ROLE_SESSION_NAME (Optional)

**Value**: Session name for assumed role (defaults to 'GitHubActions')

```
GitHubActions
```

---

## How to Find Your AWS Account ID

1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Click your account name in top-right
3. Copy the Account ID

Or run:
```bash
aws sts get-caller-identity --query Account --output text
```

---

## How to Set GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings**
3. Click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter:
   - **Name**: `ASSUME_ROLE_ARN`
   - **Value**: `arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-terraform-role`
6. Click **Add secret**

Repeat for `AWS_ROLE_SESSION_NAME` if needed.

---

## Verify Secrets

Once added, you'll see them listed in the Secrets section. You cannot view secret values after creation (GitHub hides them for security).

---

## If Credentials Still Fail

1. **Verify IAM role exists** in AWS console
2. **Check trust relationship** is configured correctly
3. **Verify OIDC provider** exists with correct URL
4. **Check secret names** match exactly (case-sensitive):
   - `ASSUME_ROLE_ARN`
   - `AWS_ROLE_SESSION_NAME`
5. **Test role assumption locally**:
   ```bash
   aws sts assume-role-with-web-identity \
     --role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/github-actions-terraform-role \
     --web-identity-token $GITHUB_TOKEN \
     --role-session-name test
   ```

---

## AWS CLI Commands to Setup Everything

```bash
# 1. Create S3 bucket for backend
aws s3api create-bucket \
  --bucket s3-backend-git-9696 \
  --region us-east-1

# 2. Enable versioning
aws s3api put-bucket-versioning \
  --bucket s3-backend-git-9696 \
  --versioning-configuration Status=Enabled

# 3. Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1

# 4. Get your AWS Account ID (use as ASSUME_ROLE_ARN)
aws sts get-caller-identity --query Account --output text
```

---

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed IAM role creation.
