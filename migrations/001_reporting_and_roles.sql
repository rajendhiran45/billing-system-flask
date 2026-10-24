-- Run once for a manual upgrade if the application cannot run its automatic upgrade.
-- Do not include credentials in this file or source it from an environment file.
ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'cashier';
UPDATE users SET role='admin' WHERE id=(SELECT id FROM (SELECT MIN(id) AS id FROM users) AS first_user);
CREATE TABLE customers (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL, phone VARCHAR(30) NULL, email VARCHAR(120) NULL,
  address VARCHAR(255) NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_customer_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
ALTER TABLE bills ADD COLUMN customer_id BIGINT UNSIGNED NULL;
ALTER TABLE bills ADD COLUMN cashier_id BIGINT UNSIGNED NULL;
CREATE TABLE inventory_alerts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, product_id BIGINT UNSIGNED NOT NULL,
  stock_at_alert INT NOT NULL, resolved_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, INDEX idx_alert_product_open (product_id, resolved_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
