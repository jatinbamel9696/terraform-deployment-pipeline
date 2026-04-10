terraform {
  backend "s3" {
    bucket         = "s3-backend-git-9696"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
