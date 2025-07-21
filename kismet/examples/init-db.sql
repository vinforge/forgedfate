-- PostgreSQL initialization script for Kismet export
-- This script creates the necessary tables and indexes for optimal performance

-- Create the main devices table
CREATE TABLE IF NOT EXISTS kismet_devices (
    mac_addr TEXT PRIMARY KEY,
    name TEXT,
    username TEXT,
    phy_type TEXT,
    manufacturer TEXT,
    first_seen BIGINT,
    last_seen BIGINT,
    channel TEXT,
    frequency BIGINT,
    total_packets BIGINT DEFAULT 0,
    tx_packets BIGINT DEFAULT 0,
    rx_packets BIGINT DEFAULT 0,
    data_size BIGINT DEFAULT 0,
    signal_dbm INTEGER,
    noise_dbm INTEGER,
    snr_db INTEGER,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    altitude DOUBLE PRECISION,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_kismet_devices_last_seen ON kismet_devices(last_seen);
CREATE INDEX IF NOT EXISTS idx_kismet_devices_phy_type ON kismet_devices(phy_type);
CREATE INDEX IF NOT EXISTS idx_kismet_devices_manufacturer ON kismet_devices(manufacturer);
CREATE INDEX IF NOT EXISTS idx_kismet_devices_signal ON kismet_devices(signal_dbm);
CREATE INDEX IF NOT EXISTS idx_kismet_devices_last_updated ON kismet_devices(last_updated);
CREATE INDEX IF NOT EXISTS idx_kismet_devices_location ON kismet_devices(latitude, longitude) WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create events table for storing Kismet events
CREATE TABLE IF NOT EXISTS kismet_events (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_time TIMESTAMP DEFAULT NOW(),
    device_mac TEXT,
    event_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for events table
CREATE INDEX IF NOT EXISTS idx_kismet_events_type ON kismet_events(event_type);
CREATE INDEX IF NOT EXISTS idx_kismet_events_time ON kismet_events(event_time);
CREATE INDEX IF NOT EXISTS idx_kismet_events_device ON kismet_events(device_mac);
CREATE INDEX IF NOT EXISTS idx_kismet_events_data ON kismet_events USING GIN(event_data);

-- Create a view for recent device activity
CREATE OR REPLACE VIEW recent_devices AS
SELECT 
    mac_addr,
    name,
    phy_type,
    manufacturer,
    signal_dbm,
    total_packets,
    latitude,
    longitude,
    last_seen,
    last_updated,
    EXTRACT(EPOCH FROM (NOW() - last_updated)) AS seconds_since_update
FROM kismet_devices 
WHERE last_updated > NOW() - INTERVAL '1 hour'
ORDER BY last_updated DESC;

-- Create a view for device statistics
CREATE OR REPLACE VIEW device_stats AS
SELECT 
    phy_type,
    COUNT(*) as device_count,
    AVG(signal_dbm) as avg_signal,
    MIN(signal_dbm) as min_signal,
    MAX(signal_dbm) as max_signal,
    SUM(total_packets) as total_packets,
    COUNT(CASE WHEN last_updated > NOW() - INTERVAL '5 minutes' THEN 1 END) as active_devices
FROM kismet_devices 
GROUP BY phy_type
ORDER BY device_count DESC;

-- Create a function to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data(retention_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete old events
    DELETE FROM kismet_events 
    WHERE event_time < NOW() - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Update devices that haven't been seen recently
    UPDATE kismet_devices 
    SET last_updated = NOW() 
    WHERE last_seen < EXTRACT(EPOCH FROM (NOW() - INTERVAL '1 day' * retention_days))
    AND last_updated < NOW() - INTERVAL '1 day';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get device summary
CREATE OR REPLACE FUNCTION get_device_summary()
RETURNS TABLE(
    total_devices BIGINT,
    active_devices BIGINT,
    wifi_devices BIGINT,
    bluetooth_devices BIGINT,
    avg_signal NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_devices,
        COUNT(CASE WHEN last_updated > NOW() - INTERVAL '5 minutes' THEN 1 END)::BIGINT as active_devices,
        COUNT(CASE WHEN phy_type LIKE '%802.11%' THEN 1 END)::BIGINT as wifi_devices,
        COUNT(CASE WHEN phy_type LIKE '%Bluetooth%' THEN 1 END)::BIGINT as bluetooth_devices,
        ROUND(AVG(signal_dbm), 2) as avg_signal
    FROM kismet_devices;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions to kismet user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kismet;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kismet;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO kismet;

-- Insert some sample data for testing (optional)
-- INSERT INTO kismet_devices (mac_addr, name, phy_type, manufacturer, signal_dbm, total_packets)
-- VALUES 
--     ('aa:bb:cc:dd:ee:01', 'Test Device 1', 'IEEE802.11', 'Apple', -45, 100),
--     ('aa:bb:cc:dd:ee:02', 'Test Device 2', 'Bluetooth', 'Samsung', -60, 50);

COMMIT;
