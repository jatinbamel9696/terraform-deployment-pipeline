terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    # Use placeholder - will be set at runtime via -backend-config
    # key format: stacks/iam/REGION/terraform.tfstate
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}