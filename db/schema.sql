-- Fitness Repair Reference Database Schema
-- 10 tables: manufacturers, brands, oem_factories, models, parts_catalog,
-- failure_patterns, triage_flows, service_zones, techs, service_calls

CREATE TABLE IF NOT EXISTS manufacturers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  hq_country TEXT,
  website TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  parent_company_id INTEGER REFERENCES manufacturers(id),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
  name TEXT NOT NULL UNIQUE,
  equipment_types TEXT,
  price_tier TEXT,
  sold_at TEXT,
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS oem_factories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  location TEXT,
  country TEXT,
  components_produced TEXT,
  brands_supplied TEXT
);

CREATE TABLE IF NOT EXISTS models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id INTEGER NOT NULL REFERENCES brands(id),
  name TEXT NOT NULL,
  equipment_type TEXT NOT NULL,
  years_produced_start INTEGER,
  years_produced_end INTEGER,
  motor_type TEXT,
  motor_hp REAL,
  weight_lbs REAL,
  msrp_range TEXT,
  oem_factory_id INTEGER REFERENCES oem_factories(id),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS parts_catalog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  component_type TEXT NOT NULL,
  oem_factory_id INTEGER REFERENCES oem_factories(id),
  compatible_model_ids TEXT,
  cross_compatible_part_ids TEXT,
  typical_price_range TEXT,
  sources TEXT
);

CREATE TABLE IF NOT EXISTS failure_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type TEXT NOT NULL,
  component_type TEXT NOT NULL,
  symptom TEXT NOT NULL,
  root_cause TEXT,
  frequency TEXT,
  typical_age_years INTEGER,
  diy_fixable INTEGER DEFAULT 0,
  requires_tech INTEGER DEFAULT 1,
  estimated_repair_cost TEXT,
  triage_priority INTEGER
);

CREATE TABLE IF NOT EXISTS triage_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type TEXT NOT NULL,
  entry_symptom TEXT NOT NULL,
  decision_tree TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_zones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zone_name TEXT NOT NULL,
  state TEXT NOT NULL,
  zip_codes TEXT NOT NULL,
  rate_type TEXT NOT NULL,
  trip_charge_amount REAL,
  availability TEXT NOT NULL,
  tech_ids TEXT
);

CREATE TABLE IF NOT EXISTS techs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  base_state TEXT,
  az_availability TEXT,
  ca_availability TEXT,
  zones TEXT,
  specialties TEXT,
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS service_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  caller_phone TEXT,
  equipment_type TEXT,
  brand TEXT,
  model TEXT,
  symptom TEXT,
  triage_result TEXT,
  customer_name TEXT,
  customer_address TEXT,
  customer_zip TEXT,
  zone_id INTEGER REFERENCES service_zones(id),
  state TEXT,
  requested_days TEXT,
  requested_time_window TEXT,
  trip_charge INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_brands_manufacturer ON brands(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_models_brand ON models(brand_id);
CREATE INDEX IF NOT EXISTS idx_models_equipment ON models(equipment_type);
CREATE INDEX IF NOT EXISTS idx_failure_equipment ON failure_patterns(equipment_type);
CREATE INDEX IF NOT EXISTS idx_failure_component ON failure_patterns(component_type);
CREATE INDEX IF NOT EXISTS idx_service_calls_status ON service_calls(status);
CREATE INDEX IF NOT EXISTS idx_service_calls_date ON service_calls(timestamp);
