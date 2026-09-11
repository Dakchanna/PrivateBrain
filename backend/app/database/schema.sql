-- ============================================================
-- PrivateBrain Database Schema
-- Run this SQL in your Supabase SQL editor to create all tables
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── ENUMS ────────────────────────────────────────────────────

CREATE TYPE robot_status AS ENUM ('ONLINE', 'IDLE', 'PROCESSING', 'OFFLINE', 'ERROR');
CREATE TYPE task_type AS ENUM ('object_detection', 'image_classification', 'speech_processing');
CREATE TYPE priority_level AS ENUM ('critical', 'high', 'normal', 'low');
CREATE TYPE request_status AS ENUM (
    'RECEIVED', 'AUTHENTICATING', 'VALIDATED', 'QUEUED',
    'SCHEDULED', 'PROCESSING', 'COMPLETED', 'RETRYING',
    'RECOVERING', 'ERROR', 'FAILED'
);

-- ── ROBOTS ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS robots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    robot_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(128),
    description TEXT,
    api_key_hash VARCHAR(256) NOT NULL,
    status robot_status NOT NULL DEFAULT 'OFFLINE',
    last_seen TIMESTAMPTZ,
    total_requests INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms FLOAT NOT NULL DEFAULT 0.0,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_robots_robot_id ON robots (robot_id);

-- ── AI REQUESTS ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ai_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(32) UNIQUE NOT NULL,
    robot_id VARCHAR(64) NOT NULL REFERENCES robots(robot_id),
    task_type task_type NOT NULL,
    priority priority_level NOT NULL DEFAULT 'normal',
    status request_status NOT NULL DEFAULT 'RECEIVED',
    payload JSONB,
    metadata JSONB,
    selected_model VARCHAR(128),
    retry_count INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    latency_ms FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ai_requests_request_id ON ai_requests (request_id);
CREATE INDEX IF NOT EXISTS idx_ai_requests_robot_id ON ai_requests (robot_id);
CREATE INDEX IF NOT EXISTS idx_ai_requests_status ON ai_requests (status);

-- ── REQUEST EVENTS ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS request_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(32) NOT NULL REFERENCES ai_requests(request_id),
    event_type VARCHAR(64) NOT NULL,
    message TEXT,
    data JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_request_events_request_id ON request_events (request_id);

-- ── INFERENCE RESULTS ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS inference_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(32) UNIQUE NOT NULL REFERENCES ai_requests(request_id),
    model_used VARCHAR(128) NOT NULL,
    result_data JSONB NOT NULL,
    confidence FLOAT,
    processing_time_ms FLOAT NOT NULL DEFAULT 0.0,
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── AGENT DECISIONS ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(32) NOT NULL REFERENCES ai_requests(request_id),
    action VARCHAR(32) NOT NULL,
    priority VARCHAR(16),
    selected_model VARCHAR(128),
    reason TEXT,
    context_snapshot JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_decisions_request_id ON agent_decisions (request_id);

-- ── SYSTEM EVENTS ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS system_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(64) NOT NULL,
    robot_id VARCHAR(64),
    request_id VARCHAR(32),
    message TEXT NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'info',
    data JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_system_events_event_type ON system_events (event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events (timestamp DESC);
