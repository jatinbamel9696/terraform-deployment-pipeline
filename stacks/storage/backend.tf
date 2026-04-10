terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    # Use placeholder - will be set at runtime via -backend-config
    # key format: stacks/storage/REGION/terraform.tfstate
    # region: always us-east-1 (where bucket exists)
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}