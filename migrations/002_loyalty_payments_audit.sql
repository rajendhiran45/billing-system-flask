-- Billora additive upgrade. Review and run once only if automatic schema upgrade cannot run.
ALTER TABLE customers ADD COLUMN loyalty_points INT NOT NULL DEFAULT 0;
ALTER TABLE customers ADD COLUMN loyalty_lifetime_points INT NOT NULL DEFAULT 0;
ALTER TABLE bills ADD COLUMN discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE bills ADD COLUMN loyalty_points_earned INT NOT NULL DEFAULT 0;
ALTER TABLE bills ADD COLUMN loyalty_points_redeemed INT NOT NULL DEFAULT 0;
CREATE TABLE bill_payments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, bill_id BIGINT UNSIGNED NOT NULL,
  method VARCHAR(20) NOT NULL, amount DECIMAL(12,2) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, INDEX idx_bill_payments_bill (bill_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE audit_logs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, user_id BIGINT UNSIGNED NULL,
  action VARCHAR(80) NOT NULL, entity_type VARCHAR(50) NOT NULL, entity_id BIGINT UNSIGNED NULL,
  details JSON NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_created (created_at), INDEX idx_audit_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
