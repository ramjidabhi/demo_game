variable "subscription_id" {
  type = string
}

variable "location" {
  type    = string
  default = "centralindia"
}

variable "project_name" {
  type    = string
  default = "demogame"
}

variable "node_vm_size" {
  type    = string
  default = "Standard_D2s_v3"
}
