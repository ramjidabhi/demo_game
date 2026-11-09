
variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "demo-game"
}

variable "location" {
  description = "Azure deployment region"
  type        = string
  default     = "Central India"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "vnet_address_space" {
  description = "VNet address space"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "aks_subnet_prefix" {
  description = "AKS subnet address prefix"
  type        = list(string)
  default     = ["10.0.1.0/24"]
}

variable "future_subnet_prefix" {
  description = "Future subnet address prefix"
  type        = list(string)
  default     = ["10.0.2.0/24"]
}
