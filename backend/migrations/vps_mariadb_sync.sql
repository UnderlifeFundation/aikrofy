-- ====================================================================
-- Script de sincronización idónea e idempotente para MariaDB / MySQL
-- Proyecto: AIKROFY (Producción / Local VPS)
-- ====================================================================

-- 1. Ampliar ENUM de roles de usuario para soportar AGENCY
ALTER TABLE users MODIFY COLUMN role ENUM('SUPER_ADMIN','AGENCY','ADMIN','MANAGER','EMPLOYEE') NOT NULL DEFAULT 'ADMIN';

-- 2. Asegurar columnas de cuotas en companies
ALTER TABLE companies ADD COLUMN IF NOT EXISTS agency_max_companies INT NOT NULL DEFAULT 0;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS max_agents INT NOT NULL DEFAULT 3;

-- 3. Tabla para acceso y gestión de múltiples compañías por Agencias
CREATE TABLE IF NOT EXISTS `agency_company_access` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `agency_user_id` int(11) NOT NULL,
  `company_id` int(11) NOT NULL,
  `role_in_client` varchar(50) NOT NULL DEFAULT 'admin',
  `monthly_fee` float NOT NULL DEFAULT 99.0,
  `monthly_credits` int(11) NOT NULL DEFAULT 5000,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `status` varchar(50) DEFAULT 'active',
  `invite_token` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `ix_agency_company_access_agency_user_id` (`agency_user_id`),
  KEY `ix_agency_company_access_company_id` (`company_id`),
  CONSTRAINT `fk_agency_access_user` FOREIGN KEY (`agency_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_agency_access_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 4. Asegurar campos en agency_company_access si la tabla ya existía
ALTER TABLE agency_company_access ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';
ALTER TABLE agency_company_access ADD COLUMN IF NOT EXISTS invite_token VARCHAR(255) DEFAULT NULL;

-- 5. Tabla de Catálogo Modular de Marketplace (Blog, eCommerce, etc.)
CREATE TABLE IF NOT EXISTS `modular_assets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `slug` varchar(100) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `asset_type` enum('BLOG_MODULE','ECOMMERCE_MODULE','LANDING_SUITE','CUSTOM_ASSET') NOT NULL DEFAULT 'BLOG_MODULE',
  `version` varchar(50) NOT NULL DEFAULT '1.0.0',
  `price_usd` float NOT NULL DEFAULT 49.0,
  `credits_cost` int(11) NOT NULL DEFAULT 500,
  `zip_filename` varchar(255) DEFAULT NULL,
  `zip_url` varchar(500) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `features` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`features`)),
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_modular_assets_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 6. Tabla de Licencias Criptográficas de Módulos (Ancladas a VPS / Dominio)
CREATE TABLE IF NOT EXISTS `asset_licenses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `license_key` varchar(128) NOT NULL,
  `company_id` int(11) NOT NULL,
  `asset_id` int(11) NOT NULL,
  `allowed_domains` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`allowed_domains`)),
  `allowed_ip` varchar(100) DEFAULT NULL,
  `vps_signature` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `status_message` varchar(255) DEFAULT 'Active and Verified',
  `downloads_count` int(11) DEFAULT 0,
  `last_verified_at` datetime DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_asset_licenses_license_key` (`license_key`),
  KEY `ix_asset_licenses_company_id` (`company_id`),
  KEY `ix_asset_licenses_asset_id` (`asset_id`),
  CONSTRAINT `fk_asset_licenses_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_asset_licenses_asset` FOREIGN KEY (`asset_id`) REFERENCES `modular_assets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 7. Actualizar alembic_version al head unificado
UPDATE alembic_version SET version_num = 'f9e8d7c6b5a4';
