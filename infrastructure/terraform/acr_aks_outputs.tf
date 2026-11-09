
output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "aks_identity_id" {
  value = azurerm_user_assigned_identity.aks.id
}

output "aks_node_resource_group" {
  value = azurerm_kubernetes_cluster.main.node_resource_group
}

output "aks_kubelet_identity" {
  value = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
}

