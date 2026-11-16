-- Verdant schema v1 (SQLite). Dates are ISO-8601 text; JSON columns hold lists/objects.
-- Every garden-scoped table carries garden_id with ON DELETE CASCADE and an index.

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

CREATE TABLE gardens (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    owner_user_id TEXT NOT NULL REFERENCES users(id),
    city TEXT NOT NULL DEFAULT '',
    region TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    timezone TEXT NOT NULL,
    zone_label TEXT,
    zone_source TEXT
);

CREATE TABLE garden_memberships (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
    UNIQUE (garden_id, user_id)
);

CREATE TABLE growing_spaces (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    setting TEXT NOT NULL,
    growing_method TEXT NOT NULL,
    light_source TEXT NOT NULL,
    exposure TEXT NOT NULL,
    estimated_direct_sun_hours REAL,
    grow_light_hours REAL,
    grow_light_ppfd REAL,
    soil_medium TEXT,
    irrigation_method TEXT,
    notes TEXT NOT NULL DEFAULT ''
);

-- Seed varieties are a shared reference catalogue; what a garden owns lives in seed_inventory.
CREATE TABLE seed_varieties (
    id TEXT PRIMARY KEY,
    common_name TEXT NOT NULL,
    category TEXT NOT NULL,
    cultivar TEXT,
    scientific_name TEXT,
    crop_key TEXT,
    brand TEXT,
    packet_label TEXT,
    source_url TEXT,
    requirements_source TEXT,
    germination_days_min INTEGER,
    germination_days_max INTEGER,
    maturity_days_min INTEGER,
    maturity_days_max INTEGER,
    sunlight_requirement TEXT NOT NULL,
    preferred_temperature_range TEXT,
    planting_notes TEXT NOT NULL DEFAULT '',
    image_path TEXT,
    verification_status TEXT NOT NULL
);

CREATE TABLE seed_inventory (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    seed_variety_id TEXT NOT NULL REFERENCES seed_varieties(id),
    packet_count INTEGER,
    approximate_seed_count INTEGER,
    acquired_on TEXT,
    expiry_on TEXT,
    notes TEXT NOT NULL DEFAULT '',
    packet_photo_path TEXT,
    import_key TEXT,
    UNIQUE (garden_id, import_key)
);

CREATE TABLE plantings (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    growing_space_id TEXT NOT NULL REFERENCES growing_spaces(id),
    seed_variety_id TEXT NOT NULL REFERENCES seed_varieties(id),
    quantity INTEGER NOT NULL,
    nickname TEXT,
    sown_on TEXT,
    germinated_on TEXT,
    transplanted_on TEXT,
    growth_stage TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE garden_tasks (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    due_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    priority TEXT NOT NULL,
    recurrence TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    planting_id TEXT REFERENCES plantings(id),
    growing_space_id TEXT REFERENCES growing_spaces(id),
    recommendation_id TEXT,
    source TEXT NOT NULL,
    idempotency_key TEXT,
    UNIQUE (garden_id, idempotency_key)
);

CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    planting_id TEXT NOT NULL REFERENCES plantings(id),
    observed_at TEXT NOT NULL,
    height_cm REAL,
    leaf_count INTEGER,
    moisture_assessment TEXT,
    light_notes TEXT,
    symptoms TEXT,
    notes TEXT NOT NULL DEFAULT '',
    photo_path TEXT,
    data_origin TEXT NOT NULL
);

CREATE TABLE weather_snapshots (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    forecast_for TEXT NOT NULL,
    temperature REAL,
    min_temperature REAL,
    precipitation_probability REAL,
    precipitation_amount REAL,
    wind_speed REAL,
    sunshine_duration REAL,
    units TEXT NOT NULL,
    raw_reference TEXT
);

CREATE TABLE recommendations (
    id TEXT PRIMARY KEY,
    garden_id TEXT NOT NULL REFERENCES gardens(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    suitability TEXT NOT NULL,
    title TEXT NOT NULL,
    explanation TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    planting_id TEXT,
    growing_space_id TEXT,
    evidence TEXT NOT NULL DEFAULT '[]',
    unknowns TEXT NOT NULL DEFAULT '[]',
    limitations TEXT NOT NULL DEFAULT '',
    suggested_task TEXT,
    generated_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL
);

CREATE INDEX idx_memberships_user ON garden_memberships(user_id);
CREATE INDEX idx_spaces_garden ON growing_spaces(garden_id);
CREATE INDEX idx_inventory_garden ON seed_inventory(garden_id);
CREATE INDEX idx_plantings_garden ON plantings(garden_id);
CREATE INDEX idx_tasks_garden_date ON garden_tasks(garden_id, due_date);
CREATE INDEX idx_observations_garden ON observations(garden_id, planting_id);
CREATE INDEX idx_weather_garden ON weather_snapshots(garden_id, forecast_for);
CREATE INDEX idx_recommendations_garden ON recommendations(garden_id, status);
