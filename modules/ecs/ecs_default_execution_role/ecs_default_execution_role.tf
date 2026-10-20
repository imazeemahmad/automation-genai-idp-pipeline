module "execution_role" {
  source  = "registry.example.com/terraform-modules__aws-services/iam_role_service/aws"
  version = "1.2.0"

  role_name = "App_ecs_def_exec_role"
  managed_policies_arns = {
    policy_1 = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  }
  aws_service = "ecs-tasks"

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ecs_default_execution_role"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })
}
