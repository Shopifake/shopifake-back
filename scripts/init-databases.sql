-- PostgreSQL 16 initialization script for all Shopifake databases
-- This script is idempotent and can be run multiple times safely

-- Create databases (idempotent)
SELECT 'CREATE DATABASE shopifake_access_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_access_db')\gexec

SELECT 'CREATE DATABASE shopifake_audit_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_audit_db')\gexec

SELECT 'CREATE DATABASE shopifake_catalog_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_catalog_db')\gexec

SELECT 'CREATE DATABASE shopifake_customers_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_customers_db')\gexec

SELECT 'CREATE DATABASE shopifake_inventory_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_inventory_db')\gexec

SELECT 'CREATE DATABASE shopifake_orders_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_orders_db')\gexec

SELECT 'CREATE DATABASE shopifake_pricing_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_pricing_db')\gexec

SELECT 'CREATE DATABASE shopifake_sales_dashboard_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_sales_dashboard_db')\gexec

SELECT 'CREATE DATABASE shopifake_sites_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_sites_db')\gexec

SELECT 'CREATE DATABASE shopifake_chatbot_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_chatbot_db')\gexec

SELECT 'CREATE DATABASE shopifake_recommender_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_recommender_db')\gexec

SELECT 'CREATE DATABASE shopifake_auth_b2c_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_auth_b2c_db')\gexec

SELECT 'CREATE DATABASE shopifake_auth_b2e_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shopifake_auth_b2e_db')\gexec

-- Create users with passwords (idempotent)
-- Note: Password is set via environment variable interpolation in the workflow
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_access_user') THEN
    CREATE USER shopifake_access_user WITH PASSWORD :'DB_PASSWORD_ACCESS';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_audit_user') THEN
    CREATE USER shopifake_audit_user WITH PASSWORD :'DB_PASSWORD_AUDIT';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_catalog_user') THEN
    CREATE USER shopifake_catalog_user WITH PASSWORD :'DB_PASSWORD_CATALOG';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_customers_user') THEN
    CREATE USER shopifake_customers_user WITH PASSWORD :'DB_PASSWORD_CUSTOMERS';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_inventory_user') THEN
    CREATE USER shopifake_inventory_user WITH PASSWORD :'DB_PASSWORD_INVENTORY';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_orders_user') THEN
    CREATE USER shopifake_orders_user WITH PASSWORD :'DB_PASSWORD_ORDERS';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_pricing_user') THEN
    CREATE USER shopifake_pricing_user WITH PASSWORD :'DB_PASSWORD_PRICING';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_sales_dashboard_user') THEN
    CREATE USER shopifake_sales_dashboard_user WITH PASSWORD :'DB_PASSWORD_SALES_DASHBOARD';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_sites_user') THEN
    CREATE USER shopifake_sites_user WITH PASSWORD :'DB_PASSWORD_SITES';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_chatbot_user') THEN
    CREATE USER shopifake_chatbot_user WITH PASSWORD :'DB_PASSWORD_CHATBOT';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_recommender_user') THEN
    CREATE USER shopifake_recommender_user WITH PASSWORD :'DB_PASSWORD_RECOMMENDER';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_auth_b2c_user') THEN
    CREATE USER shopifake_auth_b2c_user WITH PASSWORD :'DB_PASSWORD_AUTH_B2C';
  END IF;
  
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'shopifake_auth_b2e_user') THEN
    CREATE USER shopifake_auth_b2e_user WITH PASSWORD :'DB_PASSWORD_AUTH_B2E';
  END IF;
END
$$;

-- Grant privileges (idempotent - GRANT is idempotent by nature)
GRANT ALL PRIVILEGES ON DATABASE shopifake_access_db TO shopifake_access_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_audit_db TO shopifake_audit_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_catalog_db TO shopifake_catalog_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_customers_db TO shopifake_customers_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_inventory_db TO shopifake_inventory_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_orders_db TO shopifake_orders_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_pricing_db TO shopifake_pricing_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_sales_dashboard_db TO shopifake_sales_dashboard_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_sites_db TO shopifake_sites_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_chatbot_db TO shopifake_chatbot_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_recommender_db TO shopifake_recommender_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_auth_b2c_db TO shopifake_auth_b2c_user;
GRANT ALL PRIVILEGES ON DATABASE shopifake_auth_b2e_db TO shopifake_auth_b2e_user;
