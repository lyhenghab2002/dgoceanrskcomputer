-- Complete SQL file with REAL data from your database
-- This includes the primary key disable command and all your actual data

-- Disable sql_require_primary_key for this session
SET sql_require_primary_key = 0;

-- Disable other MySQL restrictions
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

-- Your real data will be imported from individual table files
