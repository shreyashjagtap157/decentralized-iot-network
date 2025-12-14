output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = aws_eks_cluster.iot_network_cluster.endpoint
}

output "eks_cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.iot_network_cluster.vpc_config[0].cluster_security_group_id
}

output "db_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.iot_network_db.endpoint
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.iot_network_vpc.id
}
