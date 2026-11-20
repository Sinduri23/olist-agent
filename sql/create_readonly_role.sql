-- Run as a superuser AFTER loading the data. Layer 2 of the defence: even if the SQL guard were bypassed,
-- this role cannot write anything.
CREATE ROLE olist_agent LOGIN PASSWORD 'change_me';
GRANT CONNECT ON DATABASE olist TO olist_agent;
GRANT USAGE ON SCHEMA public TO olist_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO olist_agent;
ALTER ROLE olist_agent SET default_transaction_read_only = on;
ALTER ROLE olist_agent SET statement_timeout = '10s';
