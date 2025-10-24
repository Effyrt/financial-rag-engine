# AURELIA GCP Infrastructure - COMPLETE TERRAFORM CONFIGURATION

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "aurelia-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ===== Enable Required APIs =====
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "storage-api.googleapis.com",
    "composer.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com"
  ])
  
  project = var.project_id
  service = each.key
  disable_on_destroy = false
}

# ===== GCS Bucket for Artifacts =====
resource "google_storage_bucket" "artifacts" {
  name          = "${var.project_id}-aurelia-artifacts"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# ===== VPC Network =====
resource "google_compute_network" "vpc" {
  name                    = "aurelia-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "aurelia-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  private_ip_google_access = true
}

# ===== Cloud SQL PostgreSQL =====
resource "google_sql_database_instance" "postgres" {
  name             = "aurelia-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = true
  
  settings {
    tier              = "db-custom-2-7680"
    availability_type = "REGIONAL"
    disk_size         = 20
    disk_type         = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
  }
  
  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "aurelia" {
  name     = "aurelia"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "aurelia_user" {
  name     = "aurelia_user"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# ===== VPC Peering for Cloud SQL =====
resource "google_compute_global_address" "private_ip" {
  name          = "aurelia-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

# ===== VPC Connector for Cloud Run =====
resource "google_vpc_access_connector" "connector" {
  name          = "aurelia-vpc-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 3
}

# ===== Secret Manager =====
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "pinecone_api_key" {
  secret_id = "pinecone-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "aurelia-db-url"
  replication {
    auto {}
  }
}

# ===== Cloud Composer (Managed Airflow) =====
resource "google_composer_environment" "aurelia_composer" {
  name   = "aurelia-composer"
  region = var.region
  
  config {
    node_config {
      network    = google_compute_network.vpc.id
      subnetwork = google_compute_subnetwork.subnet.id
      service_account = google_service_account.composer_sa.email
    }
    
    software_config {
      image_version = "composer-2-airflow-2"
      
      pypi_packages = {
        "apache-airflow-providers-google" = ">=10.0.0"
        "PyMuPDF"                        = "==1.23.8"
        "openai"                         = "==1.6.1"
        "langchain"                      = "==0.1.0"
        "pinecone-client"                = "==3.0.0"
        "instructor"                     = "==0.4.5"
      }
    }
    
    workloads_config {
      scheduler {
        cpu        = 2
        memory_gb  = 7.5
        storage_gb = 5
        count      = 1
      }
      web_server {
        cpu        = 1
        memory_gb  = 3.75
        storage_gb = 5
      }
      worker {
        cpu        = 2
        memory_gb  = 7.5
        storage_gb = 5
        min_count  = 1
        max_count  = 3
      }
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# ===== Service Account =====
resource "google_service_account" "composer_sa" {
  account_id   = "aurelia-composer"
  display_name = "AURELIA Composer Service Account"
}

resource "google_project_iam_member" "composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.composer_sa.email}"
}

resource "google_storage_bucket_iam_member" "composer_bucket" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.composer_sa.email}"
}