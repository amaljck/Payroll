-- Backup first (run outside this file)
-- mysqldump -u root -p payroll > ~/payroll_backup_YYYYMMDD.sql

-- 1) Drop FK that referenced users (payslips_ibfk_1)
ALTER TABLE payslips DROP FOREIGN KEY `payslips_ibfk_1`;

-- 2) Remap payslips.employee_id from users.id -> employees.id (requires employees.user_id mapping)
START TRANSACTION;
UPDATE payslips p
JOIN employees e ON e.user_id = p.employee_id
SET p.employee_id = e.id
WHERE p.employee_id IS NOT NULL;
COMMIT;

-- 3) Verify there are no orphaned payslips:
SELECT COUNT(*) AS orphan_count
FROM payslips p
LEFT JOIN employees e ON p.employee_id = e.id
WHERE e.id IS NULL;

-- 4) After verification, drop employees.user_id (only when safe)
ALTER TABLE employees DROP COLUMN user_id;
