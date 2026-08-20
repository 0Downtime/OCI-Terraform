output "integration_instance_ocids" { value = { for key, instance in oci_integration_integration_instance.this : key => instance.id } }
output "fusion_environment_ocids" { value = { for key, environment in oci_fusion_apps_fusion_environment.this : key => environment.id } }
output "external_workload_metadata" { value = var.external_workload_metadata }
