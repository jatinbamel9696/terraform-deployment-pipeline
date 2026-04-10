resource "aws_instance" "example" {
  ami           = "ami-0c55b159cbfafe1d0"  # Example AMI, update as needed
  instance_type = "t2.micro"

