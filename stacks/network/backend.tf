terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    key            = "network/${var.region}/terraform.tfstate"
    region         = var.region
    dynamodb_table = "terraform-locks"
  }
}