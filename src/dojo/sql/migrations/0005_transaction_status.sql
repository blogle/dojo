ALTER TABLE transactions
ADD COLUMN status TEXT DEFAULT 'pending';

UPDATE transactions
SET status = 'cleared';
