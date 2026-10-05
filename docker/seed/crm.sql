-- type-10052026-Maurice: Seed the offline CRM schema with deterministic fixture-shaped input.
CREATE TABLE IF NOT EXISTS crm_customers (source_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, account_id TEXT NOT NULL, data_as_of DATE NOT NULL);
INSERT INTO crm_customers (source_id, name, email, account_id, data_as_of) VALUES
  ('crm-001', 'Juan Dela Cruz', 'juan@example.test', 'acct-001', DATE '2026-01-31'),
  ('crm-002', 'Jane Smith', 'jane@example.test', 'acct-002', DATE '2026-01-31')
ON CONFLICT (source_id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email, account_id = EXCLUDED.account_id, data_as_of = EXCLUDED.data_as_of;
