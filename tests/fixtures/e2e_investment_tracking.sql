-- Fixture for Investment Tracking page.
-- Creates an investment account with one position and seeded market prices.

-- Accounts
INSERT INTO accounts (
    account_id,
    name,
    account_type,
    current_balance_minor,
    currency,
    is_active,
    account_class,
    account_role
)
VALUES
    ('house_checking', 'House Checking', 'asset', 0, 'USD', TRUE, 'cash', 'on_budget'),
    ('brokerage_account', 'Brokerage Account', 'asset', 100000, 'USD', TRUE, 'investment', 'on_budget')
ON CONFLICT (account_id) DO UPDATE
    SET
        name = excluded.name,
        account_type = excluded.account_type,
        current_balance_minor = excluded.current_balance_minor,
        currency = excluded.currency,
        is_active = excluded.is_active,
        account_class = excluded.account_class,
        account_role = excluded.account_role;

-- Ledger cash basis (transactions drive portfolio history series)
INSERT INTO transactions (
    transaction_version_id,
    concept_id,
    account_id,
    category_id,
    transaction_date,
    amount_minor,
    memo,
    recorded_at,
    valid_from
)
VALUES (
    '00000000-0000-0000-0000-00000000d001',
    '00000000-0000-0000-0000-00000000d002',
    'brokerage_account',
    'account_transfer',
    DATE '2025-11-01',
    100000,
    'Seed brokerage basis',
    TIMESTAMP '2025-11-01 00:00:00',
    TIMESTAMP '2025-11-01 00:00:00'
) ON CONFLICT (transaction_version_id) DO NOTHING;

-- Investment account details (uninvested cash = 0)
INSERT INTO investment_account_details (
    detail_id,
    account_id,
    risk_free_sweep_rate,
    manager,
    is_self_directed,
    tax_classification,
    uninvested_cash_minor,
    valid_from,
    valid_to,
    is_active,
    created_at,
    updated_at
)
VALUES (
    '00000000-0000-0000-0000-00000000a001',
    'brokerage_account',
    0,
    NULL,
    FALSE,
    NULL,
    0,
    TIMESTAMP '2025-11-01 00:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    TIMESTAMP '2025-11-01 00:00:00',
    TIMESTAMP '2025-11-01 00:00:00'
) ON CONFLICT (detail_id) DO NOTHING;

-- Security registry
INSERT INTO securities (
    security_id,
    ticker,
    name,
    type,
    currency,
    created_at,
    updated_at
)
VALUES (
    '00000000-0000-0000-0000-00000000b001',
    'AAPL',
    'Apple Inc.',
    'STOCK',
    'USD',
    TIMESTAMP '2025-11-01 00:00:00',
    TIMESTAMP '2025-11-01 00:00:00'
) ON CONFLICT (ticker) DO NOTHING;

-- Seed two market prices so the 1M chart has an as-of price.
INSERT INTO market_prices (
    security_id,
    market_date,
    open_minor,
    high_minor,
    low_minor,
    close_minor,
    adj_close_minor,
    volume,
    recorded_at
)
VALUES
    (
        '00000000-0000-0000-0000-00000000b001',
        DATE '2025-11-15',
        10500,
        10500,
        10500,
        10500,
        10500,
        1000,
        TIMESTAMP '2025-11-15 12:00:00'
    ),
    (
        '00000000-0000-0000-0000-00000000b001',
        DATE '2025-12-15',
        11000,
        11000,
        11000,
        11000,
        11000,
        1000,
        TIMESTAMP '2025-12-15 12:00:00'
    )
ON CONFLICT (security_id, market_date) DO UPDATE
    SET
        open_minor = excluded.open_minor,
        high_minor = excluded.high_minor,
        low_minor = excluded.low_minor,
        close_minor = excluded.close_minor,
        adj_close_minor = excluded.adj_close_minor,
        volume = excluded.volume,
        recorded_at = excluded.recorded_at;

-- Active position (10 shares AAPL)
INSERT INTO positions (
    position_id,
    concept_id,
    account_id,
    security_id,
    quantity,
    avg_cost_minor,
    valid_from,
    valid_to,
    is_active,
    recorded_at
)
VALUES (
    '00000000-0000-0000-0000-00000000c001',
    '00000000-0000-0000-0000-00000000c002',
    'brokerage_account',
    '00000000-0000-0000-0000-00000000b001',
    10.0,
    10000,
    TIMESTAMP '2025-11-01 00:00:00',
    TIMESTAMP '9999-12-31 00:00:00',
    TRUE,
    TIMESTAMP '2025-11-01 00:00:00'
) ON CONFLICT (position_id) DO NOTHING;
