-- AI Shift Agent Database Schema
-- PostgreSQL 16+

-- Enable UUID extension for secure key generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    avatar_url TEXT,
    spreadsheet_id VARCHAR(255),
    gemini_api_key VARCHAR(255),
    google_maps_api_key VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast API key lookups
CREATE INDEX idx_users_api_key ON users(api_key) WHERE is_active = TRUE;
CREATE INDEX idx_users_active ON users(is_active);

-- System Settings Table
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast key lookups
CREATE INDEX idx_system_settings_key ON system_settings(key);

-- Prompts Table
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    template TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shifts Table (for local caching and history)
CREATE TABLE IF NOT EXISTS shifts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    shift_date DATE NOT NULL,
    slot_1 VARCHAR(50),
    slot_2 VARCHAR(50),
    notes TEXT,
    source VARCHAR(50) DEFAULT 'ocr', -- 'ocr', 'manual', 'sheets'
    synced_to_sheets BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, shift_date)
);

-- Indexes for shift queries
CREATE INDEX idx_shifts_user_date ON shifts(user_id, shift_date);
CREATE INDEX idx_shifts_date ON shifts(shift_date);
CREATE INDEX idx_shifts_synced ON shifts(synced_to_sheets) WHERE synced_to_sheets = FALSE;

-- Activity Logs Table
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    level VARCHAR(20) DEFAULT 'INFO', -- 'INFO', 'WARNING', 'ERROR'
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for log queries
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at DESC);
CREATE INDEX idx_activity_logs_level ON activity_logs(level);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);

-- Sessions Table (for Redis-backed sessions)
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    data JSONB,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for session cleanup
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompts_updated_at BEFORE UPDATE ON prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shifts_updated_at BEFORE UPDATE ON shifts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default system prompt
INSERT INTO prompts (name, template, description, is_active) VALUES
(
    'ocr_shift_extraction',
    'Analizza l''immagine per l''utente {target_user}. 
REGOLE: 
1. Estrai orari pulendo simboli grafici (es. 🎵). 
2. Primo orario in ''slot_1'', altri in ''slot_2'' separati da virgola. 
3. Se la cella è vuota, scrivi ''RIPOSO''.
Input esempio: "🎵 08:30-12:30, 13:30-15:30" 
Output JSON: {"slot_1": "08:30-12:30", "slot_2": "13:30-15:30"}',
    'Default OCR prompt for shift extraction from images',
    TRUE
) ON CONFLICT (name) DO NOTHING;

-- Insert default system settings
INSERT INTO system_settings (key, value, description) VALUES
    ('vision_model', 'gemini-2.5-flash', 'Google Gemini model for vision tasks'),
    ('nlp_model', 'gemini-2.5-flash', 'Google Gemini model for NLP tasks'),
    ('traffic_update_interval', '300', 'Traffic widget update interval in seconds'),
    ('max_logs_display', '100', 'Maximum number of logs to display in admin panel'),
    ('session_timeout', '3600', 'Session timeout in seconds')
ON CONFLICT (key) DO NOTHING;

-- Create view for active users (for user picker)
CREATE OR REPLACE VIEW active_users AS
SELECT id, name, display_name, avatar_url, api_key
FROM users
WHERE is_active = TRUE
ORDER BY display_name;

-- Create view for recent activity (for admin dashboard)
CREATE OR REPLACE VIEW recent_activity AS
SELECT 
    al.id,
    al.action,
    al.level,
    al.created_at,
    u.display_name as user_name,
    al.details
FROM activity_logs al
LEFT JOIN users u ON al.user_id = u.id
ORDER BY al.created_at DESC
LIMIT 100;

COMMENT ON TABLE users IS 'User accounts with authentication and configuration';
COMMENT ON TABLE system_settings IS 'Global system configuration key-value pairs';
COMMENT ON TABLE prompts IS 'AI prompt templates for various tasks';
COMMENT ON TABLE shifts IS 'User shift data with sync status';
COMMENT ON TABLE activity_logs IS 'Audit trail of all system actions';
COMMENT ON TABLE sessions IS 'Web session storage';
