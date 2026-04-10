terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    key            = "network/${var.region}/terraform.tfstate"
    region         = "us-east-1"  # or var.region?
    dynamodb_table = "terraform-locks"
  }
}