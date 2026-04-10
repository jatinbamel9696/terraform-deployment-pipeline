variable "bucket_name" {
  description = "S3 bucket name (should include region for global uniqueness)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

resource "aws_s3_bucket" "b" {
  bucket = var.bucket_name

  tags = {
    Region = var.region
  }
}

resource "aws_s3_bucket_versioning" "b" {
  bucket = aws_s3_bucket.b.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "b" {
  bucket = aws_s3_bucket.b.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}