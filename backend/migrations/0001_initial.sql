-- 0001_initial.sql - Dojo initial schema
-- Defines base tables, enums, indexes and triggers

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enums
CREATE TYPE account_type AS ENUM ('asset','credit');
CREATE TYPE category_type AS ENUM ('group','standard','non_reportable','credit_payment');
CREATE TYPE transaction_status AS ENUM ('pending','settled');
CREATE TYPE transaction_source AS ENUM ('manual','plaid','system');

-- Base tables
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE households (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    default_currency TEXT NOT NULL DEFAULT 'USD',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE household_members (
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('owner','member')),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (household_id, user_id)
);

CREATE TABLE category_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    sort_order      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    group_id        UUID REFERENCES category_groups(id) ON DELETE SET NULL,
    name            TEXT NOT NULL,
    type            category_type NOT NULL DEFAULT 'standard',
    monthly_amount  NUMERIC(14,2) NOT NULL DEFAULT 0,
    goal_amount     NUMERIC(14,2),
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_categories_household ON categories(household_id);

CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    type            account_type NOT NULL,
    starting_balance NUMERIC(14,2) NOT NULL,
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_accounts_household ON accounts(household_id);

CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    payee           TEXT,
    memo            TEXT,
    account_id      UUID REFERENCES accounts(id) ON DELETE CASCADE,
    category_id     UUID REFERENCES categories(id) ON DELETE SET NULL,
    inflow          NUMERIC(14,2) NOT NULL DEFAULT 0,
    outflow         NUMERIC(14,2) NOT NULL DEFAULT 0,
    status          transaction_status NOT NULL,
    source          transaction_source NOT NULL,
    external_id     TEXT UNIQUE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tx_household_date ON transactions(household_id, date DESC);
CREATE INDEX idx_tx_account_status ON transactions(account_id, status);

CREATE TABLE category_transfers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    from_category_id UUID REFERENCES categories(id) ON DELETE RESTRICT,
    to_category_id   UUID REFERENCES categories(id) ON DELETE RESTRICT,
    amount          NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    memo            TEXT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reconciliations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    account_id      UUID REFERENCES accounts(id) ON DELETE CASCADE,
    reconciled_at   TIMESTAMPTZ NOT NULL,
    statement_balance NUMERIC(14,2) NOT NULL,
    created_by      UUID REFERENCES users(id)
);

CREATE TABLE plaid_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID REFERENCES households(id) ON DELETE CASCADE,
    access_token    TEXT NOT NULL,
    institution     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Materialized views
CREATE MATERIALIZED VIEW v_category_balance AS
SELECT  c.id               AS category_id,
        c.household_id,
        COALESCE(SUM(t.inflow - t.outflow),0)
        + COALESCE(SUM(ct_in.amount),0)
        - COALESCE(SUM(ct_out.amount),0) AS balance
FROM    categories c
LEFT JOIN transactions t      ON t.category_id = c.id AND t.status = 'settled'
LEFT JOIN category_transfers ct_in  ON ct_in.to_category_id = c.id
LEFT JOIN category_transfers ct_out ON ct_out.from_category_id = c.id
GROUP BY c.id;

CREATE MATERIALIZED VIEW v_account_balance AS
SELECT  a.id as account_id,
        a.household_id,
        a.starting_balance + COALESCE(SUM(t.inflow - t.outflow),0) AS balance
FROM    accounts a
LEFT JOIN transactions t ON t.account_id = a.id AND t.status = 'settled'
GROUP BY a.id;


-- Trigger: credit card auto-fund
CREATE OR REPLACE FUNCTION trg_credit_card_autofund() RETURNS TRIGGER AS $$
DECLARE
    payment_cat UUID;
BEGIN
    IF NEW.outflow > 0 AND
       (SELECT type FROM accounts WHERE id = NEW.account_id) = 'credit' AND
       NEW.category_id IS NOT NULL THEN
        SELECT id INTO payment_cat
        FROM categories
        WHERE type = 'credit_payment'
          AND household_id = NEW.household_id
        LIMIT 1;
        IF payment_cat IS NOT NULL AND payment_cat <> NEW.category_id THEN
            INSERT INTO category_transfers(
                id, household_id, date,
                from_category_id, to_category_id,
                amount, memo, created_by
            ) VALUES (
                gen_random_uuid(), NEW.household_id, NEW.date,
                NEW.category_id, payment_cat,
                NEW.outflow, 'auto-fund credit card', NEW.created_by
            );
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER credit_card_autofund
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION trg_credit_card_autofund();
