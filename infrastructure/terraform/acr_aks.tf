
# --------------------------------------------
# UNIQUE RESOURCE NAMING
# --------------------------------------------

locals {
  acr_name       = "demoacr${substr(replace(var.subscription_id, "-", ""), 0, 12)}"
  aks_name       = "${var.project_name}-${var.environment}-aks"
  aks_dns_prefix = "demogame-${var.environment}-${substr(replace(var.subscription_id, "-", ""), 0, 6)}"
}

# --------------------------------------------
# PHASE 2 - AZURE CONTAINER REGISTRY
# --------------------------------------------

resource "azurerm_container_registry" "main" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku           = "Basic"
  admin_enabled = false

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# --------------------------------------------
# AKS USER ASSIGNED MANAGED IDENTITY
# --------------------------------------------

resource "azurerm_user_assigned_identity" "aks" {
  name                = "${var.project_name}-aks-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# --------------------------------------------
# AKS NETWORK PERMISSION
# --------------------------------------------

resource "azurerm_role_assignment" "aks_network" {
  scope                = azurerm_subnet.aks.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# --------------------------------------------
# PHASE 3 - AZURE KUBERNETES SERVICE
# --------------------------------------------

resource "azurerm_kubernetes_cluster" "main" {
  name                = local.aks_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  dns_prefix = local.aks_dns_prefix

  sku_tier = "Free"

  default_node_pool {
    name       = "system"
    node_count = 1
    vm_size    = "Standard_D2s_v3"

    os_disk_size_gb = 30

    type = "VirtualMachineScaleSets"

    vnet_subnet_id = azurerm_subnet.aks.id

    only_critical_addons_enabled = true
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  # Kubelet uses its automatically managed
  # identity to pull images from ACR.
  kubelet_identity {}

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"

    pod_cidr       = "10.244.0.0/16"
    service_cidr   = "10.1.0.0/16"
    dns_service_ip = "10.1.0.10"

    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  depends_on = [
    azurerm_role_assignment.aks_network
  ]
}

# --------------------------------------------
# ACR IMAGE PULL PERMISSION FOR AKS
# --------------------------------------------

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"

  principal_id = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id

  depends_on = [
    azurerm_kubernetes_cluster.main
  ]
}

