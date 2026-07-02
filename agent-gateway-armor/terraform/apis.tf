resource "google_project_service" "model_armor" {
  project            = var.project
  service            = "modelarmor.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "network_services" {
  project            = var.project
  service            = "networkservices.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "network_security" {
  project            = var.project
  service            = "networksecurity.googleapis.com"
  disable_on_destroy = false
}
