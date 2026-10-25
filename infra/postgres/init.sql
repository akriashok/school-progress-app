-- Runs once when the dev database volume is first created.
-- app_user is the NON-OWNER role the API connects as, so Row-Level Security
-- policies are enforced (RLS does not apply to the table owner).
-- Dev-only password; production roles are created by the infra team.
CREATE ROLE app_user LOGIN PASSWORD 'app_user_dev';
GRANT CONNECT ON DATABASE vidyatrack TO app_user;

CREATE DATABASE vidyatrack_test OWNER vidya_owner;
GRANT CONNECT ON DATABASE vidyatrack_test TO app_user;
