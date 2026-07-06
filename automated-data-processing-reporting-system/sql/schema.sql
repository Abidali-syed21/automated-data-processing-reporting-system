-- =====================================================================
-- Automated Data Processing & Reporting System
-- MySQL Schema
-- =====================================================================

CREATE DATABASE IF NOT EXISTS sales_reporting_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sales_reporting_db;

-- ---------------------------------------------------------------------
-- Raw/cleaned transactional data loaded by the ETL pipeline
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales_transactions (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id            VARCHAR(50)     NOT NULL,
    order_date          DATE            NOT NULL,
    customer_name       VARCHAR(150)    NOT NULL,
    region              VARCHAR(100)    NOT NULL,
    product_category    VARCHAR(100)    NOT NULL,
    product_name        VARCHAR(150)    NOT NULL,
    quantity            INT             NOT NULL,
    unit_price          DECIMAL(10, 2)  NOT NULL,
    discount            DECIMAL(5, 4)   NOT NULL DEFAULT 0,
    payment_method      VARCHAR(50)     NOT NULL,
    total_amount        DECIMAL(12, 2)  NOT NULL,
    order_year          SMALLINT        NOT NULL,
    order_month         TINYINT         NOT NULL,
    loaded_at           TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_order_id (order_id),
    INDEX idx_region (region),
    INDEX idx_category (product_category),
    INDEX idx_year_month (order_year, order_month)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Log of every ETL run, for auditing/automation history
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_file     VARCHAR(255)    NOT NULL,
    rows_read       INT             NOT NULL,
    rows_cleaned    INT             NOT NULL,
    rows_rejected   INT             NOT NULL,
    rows_loaded     INT             NOT NULL,
    status          ENUM('SUCCESS', 'FAILED', 'PARTIAL') NOT NULL,
    error_message   TEXT NULL,
    started_at      TIMESTAMP       NOT NULL,
    finished_at     TIMESTAMP       NULL,
    duration_seconds DECIMAL(10,2) NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Pre-aggregated monthly summary (refreshed by the reporting module)
-- Speeds up dashboards/reports that don't need row-level detail
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monthly_region_summary (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_year          SMALLINT        NOT NULL,
    order_month         TINYINT         NOT NULL,
    region              VARCHAR(100)    NOT NULL,
    total_orders        INT             NOT NULL,
    total_quantity      INT             NOT NULL,
    total_revenue        DECIMAL(14, 2)  NOT NULL,
    avg_order_value     DECIMAL(12, 2)  NOT NULL,
    refreshed_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_year_month_region (order_year, order_month, region)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Useful ad-hoc reporting queries (reference only, also used by
-- src/report_generator.py)
-- ---------------------------------------------------------------------

-- Revenue by region
-- SELECT region, SUM(total_amount) AS revenue
-- FROM sales_transactions
-- GROUP BY region
-- ORDER BY revenue DESC;

-- Top N products by revenue
-- SELECT product_name, SUM(total_amount) AS revenue, SUM(quantity) AS units_sold
-- FROM sales_transactions
-- GROUP BY product_name
-- ORDER BY revenue DESC
-- LIMIT 10;

-- Monthly sales trend
-- SELECT order_year, order_month, SUM(total_amount) AS revenue
-- FROM sales_transactions
-- GROUP BY order_year, order_month
-- ORDER BY order_year, order_month;
