terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    key            = "storage/${var.region}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
  }
}