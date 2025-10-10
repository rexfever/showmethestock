PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                verification_type TEXT DEFAULT 'signup'  -- 'signup' or 'password_reset'
            );
DELETE FROM sqlite_sequence;
COMMIT;
