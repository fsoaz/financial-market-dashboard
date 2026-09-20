data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

data "tls_certificate" "github" {
  count = var.github_repository == "" ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = var.github_repository == "" ? 0 : 1
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github[0].certificates[0].sha1_fingerprint]
}

resource "aws_iam_role" "github_actions" {
  count = var.github_repository == "" ? 0 : 1
  name  = "${var.project_name}-github-actions"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github[0].arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_environment}"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  count = var.github_repository == "" ? 0 : 1
  role  = aws_iam_role.github_actions[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid      = "InspectCallerIdentity"
          Effect   = "Allow"
          Action   = ["sts:GetCallerIdentity"]
          Resource = "*"
        },
        {
          Sid      = "GetEcrAuthorizationToken"
          Effect   = "Allow"
          Action   = ["ecr:GetAuthorizationToken"]
          Resource = "*"
        },
        {
          Sid    = "ManageDashboardEcrRepository"
          Effect = "Allow"
          Action = [
            "ecr:BatchCheckLayerAvailability",
            "ecr:BatchDeleteImage",
            "ecr:CompleteLayerUpload",
            "ecr:CreateRepository",
            "ecr:DeleteLifecyclePolicy",
            "ecr:DeleteRepository",
            "ecr:DeleteRepositoryPolicy",
            "ecr:DescribeImages",
            "ecr:DescribeRepositories",
            "ecr:GetDownloadUrlForLayer",
            "ecr:GetLifecyclePolicy",
            "ecr:GetRepositoryPolicy",
            "ecr:InitiateLayerUpload",
            "ecr:ListImages",
            "ecr:ListTagsForResource",
            "ecr:PutImage",
            "ecr:PutImageScanningConfiguration",
            "ecr:PutImageTagMutability",
            "ecr:PutLifecyclePolicy",
            "ecr:SetRepositoryPolicy",
            "ecr:TagResource",
            "ecr:UntagResource",
            "ecr:UploadLayerPart"
          ]
          Resource = aws_ecr_repository.dashboard.arn
        },
        {
          Sid    = "ManageDashboardDataBucket"
          Effect = "Allow"
          Action = [
            "s3:CreateBucket",
            "s3:DeleteBucket",
            "s3:DeleteBucketPolicy",
            "s3:DeleteBucketPublicAccessBlock",
            "s3:DeleteBucketWebsite",
            "s3:GetAccelerateConfiguration",
            "s3:GetBucketAcl",
            "s3:GetBucketCORS",
            "s3:GetBucketLogging",
            "s3:GetBucketPolicy",
            "s3:GetBucketPublicAccessBlock",
            "s3:GetBucketRequestPayment",
            "s3:GetBucketTagging",
            "s3:GetBucketVersioning",
            "s3:GetBucketWebsite",
            "s3:GetEncryptionConfiguration",
            "s3:GetLifecycleConfiguration",
            "s3:GetReplicationConfiguration",
            "s3:ListBucket",
            "s3:ListBucketVersions",
            "s3:PutBucketPolicy",
            "s3:PutBucketPublicAccessBlock",
            "s3:PutBucketTagging",
            "s3:PutBucketVersioning",
            "s3:PutEncryptionConfiguration"
          ]
          Resource = aws_s3_bucket.data.arn
        },
        {
          Sid    = "ManageDashboardDataObjects"
          Effect = "Allow"
          Action = [
            "s3:AbortMultipartUpload",
            "s3:DeleteObject",
            "s3:DeleteObjectVersion",
            "s3:GetObject",
            "s3:GetObjectVersion",
            "s3:PutObject"
          ]
          Resource = "${aws_s3_bucket.data.arn}/*"
        },
        {
          Sid    = "ManageDashboardCompute"
          Effect = "Allow"
          Action = [
            "ec2:AuthorizeSecurityGroupEgress",
            "ec2:AuthorizeSecurityGroupIngress",
            "ec2:CreateLaunchTemplate",
            "ec2:CreateLaunchTemplateVersion",
            "ec2:CreateSecurityGroup",
            "ec2:CreateTags",
            "ec2:DeleteLaunchTemplate",
            "ec2:DeleteLaunchTemplateVersions",
            "ec2:DeleteSecurityGroup",
            "ec2:DescribeAccountAttributes",
            "ec2:DescribeAvailabilityZones",
            "ec2:DescribeImages",
            "ec2:DescribeInstanceTypes",
            "ec2:DescribeLaunchTemplateVersions",
            "ec2:DescribeLaunchTemplates",
            "ec2:DescribeSecurityGroups",
            "ec2:DescribeSubnets",
            "ec2:DescribeVpcs",
            "ec2:ModifyLaunchTemplate",
            "ec2:RevokeSecurityGroupEgress",
            "ec2:RevokeSecurityGroupIngress"
          ]
          Resource = "*"
        },
        {
          Sid    = "ManageDashboardLoadBalancer"
          Effect = "Allow"
          Action = [
            "elasticloadbalancing:AddTags",
            "elasticloadbalancing:CreateListener",
            "elasticloadbalancing:CreateLoadBalancer",
            "elasticloadbalancing:CreateTargetGroup",
            "elasticloadbalancing:DeleteListener",
            "elasticloadbalancing:DeleteLoadBalancer",
            "elasticloadbalancing:DeleteTargetGroup",
            "elasticloadbalancing:DeregisterTargets",
            "elasticloadbalancing:DescribeListeners",
            "elasticloadbalancing:DescribeLoadBalancerAttributes",
            "elasticloadbalancing:DescribeLoadBalancers",
            "elasticloadbalancing:DescribeTags",
            "elasticloadbalancing:DescribeTargetGroupAttributes",
            "elasticloadbalancing:DescribeTargetGroups",
            "elasticloadbalancing:DescribeTargetHealth",
            "elasticloadbalancing:ModifyListener",
            "elasticloadbalancing:ModifyLoadBalancerAttributes",
            "elasticloadbalancing:ModifyTargetGroup",
            "elasticloadbalancing:ModifyTargetGroupAttributes",
            "elasticloadbalancing:RegisterTargets",
            "elasticloadbalancing:RemoveTags"
          ]
          Resource = "*"
        },
        {
          Sid    = "ManageDashboardAutoScaling"
          Effect = "Allow"
          Action = [
            "autoscaling:AttachLoadBalancerTargetGroups",
            "autoscaling:CreateAutoScalingGroup",
            "autoscaling:DeleteAutoScalingGroup",
            "autoscaling:DescribeAutoScalingGroups",
            "autoscaling:DescribeAutoScalingInstances",
            "autoscaling:DescribeLaunchConfigurations",
            "autoscaling:DescribeLoadBalancerTargetGroups",
            "autoscaling:DetachLoadBalancerTargetGroups",
            "autoscaling:SetDesiredCapacity",
            "autoscaling:UpdateAutoScalingGroup"
          ]
          Resource = "*"
        },
        {
          Sid    = "ManageDashboardEc2Role"
          Effect = "Allow"
          Action = [
            "iam:CreateRole",
            "iam:DeleteRole",
            "iam:DeleteRolePolicy",
            "iam:GetRole",
            "iam:GetRolePolicy",
            "iam:ListAttachedRolePolicies",
            "iam:ListRolePolicies",
            "iam:ListRoleTags",
            "iam:PutRolePolicy",
            "iam:TagRole",
            "iam:UntagRole",
            "iam:UpdateAssumeRolePolicy"
          ]
          Resource = aws_iam_role.ec2.arn
        },
        {
          Sid    = "InspectGitHubDeploymentRole"
          Effect = "Allow"
          Action = [
            "iam:GetRole",
            "iam:GetRolePolicy",
            "iam:ListAttachedRolePolicies",
            "iam:ListRolePolicies",
            "iam:ListRoleTags"
          ]
          Resource = aws_iam_role.github_actions[0].arn
        },
        {
          Sid    = "ManageDashboardInstanceProfile"
          Effect = "Allow"
          Action = [
            "iam:AddRoleToInstanceProfile",
            "iam:CreateInstanceProfile",
            "iam:DeleteInstanceProfile",
            "iam:GetInstanceProfile",
            "iam:ListInstanceProfilesForRole",
            "iam:RemoveRoleFromInstanceProfile",
            "iam:TagInstanceProfile",
            "iam:UntagInstanceProfile"
          ]
          Resource = aws_iam_instance_profile.ec2.arn
        },
        {
          Sid      = "PassDashboardEc2Role"
          Effect   = "Allow"
          Action   = ["iam:PassRole"]
          Resource = aws_iam_role.ec2.arn
          Condition = {
            StringEquals = {
              "iam:PassedToService" = "ec2.amazonaws.com"
            }
          }
        },
        {
          Sid    = "ManageGitHubOidcProvider"
          Effect = "Allow"
          Action = [
            "iam:AddClientIDToOpenIDConnectProvider",
            "iam:CreateOpenIDConnectProvider",
            "iam:DeleteOpenIDConnectProvider",
            "iam:GetOpenIDConnectProvider",
            "iam:ListOpenIDConnectProviderTags",
            "iam:RemoveClientIDFromOpenIDConnectProvider",
            "iam:TagOpenIDConnectProvider",
            "iam:UntagOpenIDConnectProvider",
            "iam:UpdateOpenIDConnectProviderThumbprint"
          ]
          Resource = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
      ],
      var.terraform_state_bucket == "" ? [] : [
        {
          Sid    = "ReadWriteTerraformStateBucket"
          Effect = "Allow"
          Action = [
            "s3:GetBucketLocation",
            "s3:GetBucketVersioning",
            "s3:ListBucket"
          ]
          Resource = "arn:${data.aws_partition.current.partition}:s3:::${var.terraform_state_bucket}"
        },
        {
          Sid    = "ReadWriteTerraformState"
          Effect = "Allow"
          Action = [
            "s3:DeleteObject",
            "s3:GetObject",
            "s3:PutObject"
          ]
          Resource = "arn:${data.aws_partition.current.partition}:s3:::${var.terraform_state_bucket}/financial-market-dashboard/terraform.tfstate*"
        }
      ]
    )
  })
}
