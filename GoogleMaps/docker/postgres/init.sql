-- PostgreSQL + PostGIS initialization for Google Maps Clone
-- This script sets up the spatial database schema

-- Create extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS spatial;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO spatial, public;

-- Create spatial reference systems table updates
-- Update spatial_ref_sys table with commonly used SRID if needed

-- Roads and navigation tables
CREATE TABLE IF NOT EXISTS spatial.roads (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name VARCHAR(255),
    highway VARCHAR(50),
    maxspeed INTEGER,
    oneway BOOLEAN DEFAULT FALSE,
    surface VARCHAR(50),
    geometry GEOMETRY(LINESTRING, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index on roads
CREATE INDEX IF NOT EXISTS idx_roads_geometry ON spatial.roads USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_roads_highway ON spatial.roads (highway);
CREATE INDEX IF NOT EXISTS idx_roads_name ON spatial.roads (name);

-- Places of Interest table
CREATE TABLE IF NOT EXISTS spatial.places (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    address TEXT,
    phone VARCHAR(50),
    website VARCHAR(255),
    opening_hours TEXT,
    rating DECIMAL(3,2),
    location GEOMETRY(POINT, 4326),
    boundary GEOMETRY(POLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index on places
CREATE INDEX IF NOT EXISTS idx_places_location ON spatial.places USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_places_boundary ON spatial.places USING GIST (boundary);
CREATE INDEX IF NOT EXISTS idx_places_category ON spatial.places (category, subcategory);

-- Administrative boundaries
CREATE TABLE IF NOT EXISTS spatial.boundaries (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name VARCHAR(255),
    admin_level INTEGER,
    boundary_type VARCHAR(50),
    country_code CHAR(2),
    geometry GEOMETRY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index on boundaries
CREATE INDEX IF NOT EXISTS idx_boundaries_geometry ON spatial.boundaries USING GIST (geometry);
CREATE INDEX IF NOT EXISTS idx_boundaries_admin_level ON spatial.boundaries (admin_level);

-- Traffic incidents table
CREATE TABLE IF NOT EXISTS spatial.traffic_incidents (
    id SERIAL PRIMARY KEY,
    incident_type VARCHAR(50),
    severity INTEGER CHECK (severity BETWEEN 1 AND 5),
    description TEXT,
    location GEOMETRY(POINT, 4326),
    affected_road_id INTEGER REFERENCES spatial.roads(id),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    reporter_id VARCHAR(50)
);

-- Create spatial index on traffic incidents
CREATE INDEX IF NOT EXISTS idx_traffic_incidents_location ON spatial.traffic_incidents USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_traffic_incidents_status ON spatial.traffic_incidents (status);
CREATE INDEX IF NOT EXISTS idx_traffic_incidents_time ON spatial.traffic_incidents (start_time, end_time);

-- Analytics schema tables
SET search_path TO analytics, public;

-- User analytics
CREATE TABLE IF NOT EXISTS analytics.user_journeys (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    origin GEOMETRY(POINT, 4326),
    destination GEOMETRY(POINT, 4326),
    route_geometry GEOMETRY(LINESTRING, 4326),
    distance_km DECIMAL(10,3),
    duration_seconds INTEGER,
    travel_mode VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for analytics
CREATE INDEX IF NOT EXISTS idx_user_journeys_user_id ON analytics.user_journeys (user_id);
CREATE INDEX IF NOT EXISTS idx_user_journeys_origin ON analytics.user_journeys USING GIST (origin);
CREATE INDEX IF NOT EXISTS idx_user_journeys_destination ON analytics.user_journeys USING GIST (destination);
CREATE INDEX IF NOT EXISTS idx_user_journeys_time ON analytics.user_journeys (started_at, completed_at);

-- Popular places analytics
CREATE TABLE IF NOT EXISTS analytics.place_visits (
    id SERIAL PRIMARY KEY,
    place_id INTEGER REFERENCES spatial.places(id),
    visit_count INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    avg_rating DECIMAL(3,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for place analytics
CREATE INDEX IF NOT EXISTS idx_place_visits_place_id ON analytics.place_visits (place_id);
CREATE INDEX IF NOT EXISTS idx_place_visits_count ON analytics.place_visits (visit_count DESC);

-- Functions for spatial operations
SET search_path TO spatial, public;

-- Function to find nearby places
CREATE OR REPLACE FUNCTION find_nearby_places(
    input_location GEOMETRY,
    radius_meters INTEGER DEFAULT 1000,
    place_category VARCHAR DEFAULT NULL,
    limit_count INTEGER DEFAULT 50
)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR,
    category VARCHAR,
    distance_meters DOUBLE PRECISION,
    location GEOMETRY
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.category,
        ST_Distance(ST_Transform(p.location, 3857), ST_Transform(input_location, 3857)) as distance_meters,
        p.location
    FROM spatial.places p
    WHERE ST_DWithin(
        ST_Transform(p.location, 3857), 
        ST_Transform(input_location, 3857), 
        radius_meters
    )
    AND (place_category IS NULL OR p.category = place_category)
    ORDER BY ST_Distance(ST_Transform(p.location, 3857), ST_Transform(input_location, 3857))
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get road segments within bounding box
CREATE OR REPLACE FUNCTION get_roads_in_bbox(
    min_lat DOUBLE PRECISION,
    min_lng DOUBLE PRECISION,
    max_lat DOUBLE PRECISION,
    max_lng DOUBLE PRECISION
)
RETURNS TABLE (
    id INTEGER,
    name VARCHAR,
    highway VARCHAR,
    geometry GEOMETRY
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        r.name,
        r.highway,
        r.geometry
    FROM spatial.roads r
    WHERE ST_Intersects(
        r.geometry,
        ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
    );
END;
$$ LANGUAGE plpgsql;

-- Insert sample data
INSERT INTO spatial.places (name, category, subcategory, address, location) VALUES 
('Golden Gate Bridge', 'landmark', 'bridge', 'Golden Gate Bridge, San Francisco, CA', ST_GeomFromText('POINT(-122.4783 37.8199)', 4326)),
('Fisherman''s Wharf', 'tourism', 'attraction', 'Fishermans Wharf, San Francisco, CA', ST_GeomFromText('POINT(-122.4177 37.8080)', 4326)),
('Union Square', 'shopping', 'plaza', 'Union Square, San Francisco, CA', ST_GeomFromText('POINT(-122.4075 37.7880)', 4326)),
('Lombard Street', 'landmark', 'street', 'Lombard Street, San Francisco, CA', ST_GeomFromText('POINT(-122.4194 37.8021)', 4326)),
('Alcatraz Island', 'tourism', 'historic_site', 'Alcatraz Island, San Francisco Bay', ST_GeomFromText('POINT(-122.4230 37.8267)', 4326))
ON CONFLICT DO NOTHING;

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_roads_updated_at BEFORE UPDATE ON spatial.roads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_places_updated_at BEFORE UPDATE ON spatial.places
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Set default search path
SET search_path TO spatial, analytics, public;