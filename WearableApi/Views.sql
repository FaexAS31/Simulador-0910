-- ==========================================================
-- CONSUMER DASHBOARD VIEWS (REVISED)
-- ==========================================================
-- Streamlined views for consumer-specific dashboards
-- Designed to be exposed via Django REST API GET requests

-- ==========================================================
-- 1. SMOKING/HABIT TRACKING SUMMARY
-- ==========================================================
-- Tracks total cigarettes/habits smoked over time
CREATE OR REPLACE VIEW vw_habit_tracking AS
SELECT 
    f.consumidor_id,
    h.nombre AS habito_nombre,
    DATE(f.fecha_envio) AS fecha,
    COUNT(f.id) AS total_cigarrillos,
    COUNT(f.id) FILTER (WHERE DATE(f.fecha_envio) = CURRENT_DATE) AS cigarrillos_hoy,
    COUNT(f.id) FILTER (WHERE DATE(f.fecha_envio) >= CURRENT_DATE - INTERVAL '7 days') AS cigarrillos_semana,
    COUNT(f.id) FILTER (WHERE DATE(f.fecha_envio) >= CURRENT_DATE - INTERVAL '30 days') AS cigarrillos_mes
FROM formularios f
LEFT JOIN habitos h ON f.habito_id = h.id
GROUP BY f.consumidor_id, h.nombre, DATE(f.fecha_envio)
ORDER BY fecha DESC;

COMMENT ON VIEW vw_habit_tracking IS 'Daily cigarette/habit tracking with totals for timeline charts';


-- ==========================================================
-- 2. AGGREGATED HABIT STATISTICS
-- ==========================================================
-- Overall statistics per consumer
CREATE OR REPLACE VIEW vw_habit_stats AS
SELECT 
    f.consumidor_id,
    h.nombre AS habito_nombre,
    COUNT(f.id) AS total_eventos,
    MIN(f.fecha_envio) AS primer_registro,
    MAX(f.fecha_envio) AS ultimo_registro,
    -- Events per day average
    ROUND(
        COUNT(f.id)::NUMERIC / 
        NULLIF(EXTRACT(DAY FROM (MAX(f.fecha_envio) - MIN(f.fecha_envio))) + 1, 0),
        2
    ) AS promedio_diario,
    -- This month count
    COUNT(f.id) FILTER (WHERE DATE_TRUNC('month', f.fecha_envio) = DATE_TRUNC('month', CURRENT_DATE)) AS eventos_mes_actual,
    -- Last month count
    COUNT(f.id) FILTER (WHERE DATE_TRUNC('month', f.fecha_envio) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')) AS eventos_mes_anterior
FROM formularios f
LEFT JOIN habitos h ON f.habito_id = h.id
GROUP BY f.consumidor_id, h.nombre;

COMMENT ON VIEW vw_habit_stats IS 'Aggregated habit statistics for KPI cards and comparison charts';


-- ==========================================================
-- 3. HEART RATE ANALYSIS
-- ==========================================================
-- Heart rate data over time for charts
CREATE OR REPLACE VIEW vw_heart_rate_timeline AS
SELECT 
    v.consumidor_id,
    v.window_start,
    v.window_end,
    v.hr_mean AS heart_rate_mean,
    v.hr_std AS heart_rate_std,
    -- Calculate min/max estimates
    ROUND((v.hr_mean - v.hr_std)::NUMERIC, 2) AS heart_rate_min_estimate,
    ROUND((v.hr_mean + v.hr_std)::NUMERIC, 2) AS heart_rate_max_estimate,
    DATE(v.window_start) AS fecha,
    EXTRACT(HOUR FROM v.window_start) AS hora
FROM ventanas v
WHERE v.hr_mean IS NOT NULL
ORDER BY v.window_start DESC;

COMMENT ON VIEW vw_heart_rate_timeline IS 'Heart rate data over time for line/area charts';


-- ==========================================================
-- 4. HEART RATE STATISTICS
-- ==========================================================
-- Aggregated HR stats per consumer
CREATE OR REPLACE VIEW vw_heart_rate_stats AS
SELECT 
    v.consumidor_id,
    COUNT(v.id) AS total_mediciones,
    ROUND(AVG(v.hr_mean)::NUMERIC, 2) AS hr_promedio_general,
    ROUND(MIN(v.hr_mean)::NUMERIC, 2) AS hr_minimo,
    ROUND(MAX(v.hr_mean)::NUMERIC, 2) AS hr_maximo,
    ROUND(STDDEV(v.hr_mean)::NUMERIC, 2) AS hr_desviacion,
    -- Recent averages
    ROUND(AVG(v.hr_mean) FILTER (WHERE v.window_start >= CURRENT_DATE)::NUMERIC, 2) AS hr_promedio_hoy,
    ROUND(AVG(v.hr_mean) FILTER (WHERE v.window_start >= CURRENT_DATE - INTERVAL '7 days')::NUMERIC, 2) AS hr_promedio_semana
FROM ventanas v
WHERE v.hr_mean IS NOT NULL
GROUP BY v.consumidor_id;

COMMENT ON VIEW vw_heart_rate_stats IS 'Aggregated heart rate statistics for KPI cards';


-- ==========================================================
-- 5. PREDICTION TIMELINE
-- ==========================================================
-- Predictions over time for trend analysis
CREATE OR REPLACE VIEW vw_prediction_timeline AS
SELECT 
    v.consumidor_id,
    a.id AS analisis_id,
    v.window_start,
    v.window_end,
    a.modelo_usado,
    a.urge_label,
    a.probabilidad_modelo,
    a.accuracy,
    DATE(v.window_start) AS fecha,
    EXTRACT(HOUR FROM v.window_start) AS hora
FROM analisis a
JOIN ventanas v ON a.ventana_id = v.id
ORDER BY v.window_start DESC;

COMMENT ON VIEW vw_prediction_timeline IS 'Individual predictions over time for detailed charts';


-- ==========================================================
-- 6. PREDICTION ACCURACY SUMMARY
-- ==========================================================
-- Simple prediction accuracy metrics for consumer
CREATE OR REPLACE VIEW vw_prediction_summary AS
SELECT 
    v.consumidor_id,
    COUNT(a.id) AS total_predicciones,
    COUNT(a.id) FILTER (WHERE a.urge_label = 1) AS predicciones_urge,
    COUNT(a.id) FILTER (WHERE a.urge_label = 0) AS predicciones_no_urge,
    ROUND(
        (COUNT(a.id) FILTER (WHERE a.urge_label = 1)::NUMERIC / NULLIF(COUNT(a.id), 0)) * 100,
        2
    ) AS porcentaje_urge,
    -- Count predictions by day
    COUNT(a.id) FILTER (WHERE DATE(v.window_start) = CURRENT_DATE) AS predicciones_hoy,
    COUNT(a.id) FILTER (WHERE DATE(v.window_start) >= CURRENT_DATE - INTERVAL '7 days') AS predicciones_semana
FROM analisis a
JOIN ventanas v ON a.ventana_id = v.id
GROUP BY v.consumidor_id;

COMMENT ON VIEW vw_prediction_summary IS 'Simple prediction statistics for consumer dashboard';


-- ==========================================================
-- 7. DESIRES TRACKING
-- ==========================================================
-- Track desires (urges) and resolution status
CREATE OR REPLACE VIEW vw_desires_tracking AS
SELECT 
    d.consumidor_id,
    d.id AS deseo_id,
    d.tipo AS deseo_tipo,
    d.resolved,
    d.created_at AS fecha_creacion,
    v.window_start AS ventana_inicio,
    v.hr_mean AS heart_rate_durante,
    -- Check if there's an associated analysis
    a.urge_label,
    a.probabilidad_modelo,
    -- Time to resolution (if resolved)
    CASE 
        WHEN d.resolved THEN EXTRACT(EPOCH FROM (d.updated_at - d.created_at)) / 3600
        ELSE NULL 
    END AS horas_hasta_resolucion
FROM deseos d
LEFT JOIN ventanas v ON d.ventana_id = v.id
LEFT JOIN analisis a ON v.id = a.ventana_id
ORDER BY d.created_at DESC;

COMMENT ON VIEW vw_desires_tracking IS 'Desire/urge tracking with resolution times and associated metrics';


-- ==========================================================
-- 8. DESIRES STATISTICS
-- ==========================================================
-- Aggregated desire statistics
CREATE OR REPLACE VIEW vw_desires_stats AS
SELECT 
    d.consumidor_id,
    d.tipo AS deseo_tipo,
    COUNT(d.id) AS total_deseos,
    COUNT(d.id) FILTER (WHERE d.resolved = TRUE) AS deseos_resueltos,
    COUNT(d.id) FILTER (WHERE d.resolved = FALSE) AS deseos_activos,
    ROUND(
        (COUNT(d.id) FILTER (WHERE d.resolved = TRUE)::NUMERIC / NULLIF(COUNT(d.id), 0)) * 100,
        2
    ) AS porcentaje_resolucion,
    -- Average resolution time in hours
    ROUND(
        AVG(EXTRACT(EPOCH FROM (d.updated_at - d.created_at)) / 3600) 
        FILTER (WHERE d.resolved = TRUE)::NUMERIC,
        2
    ) AS promedio_horas_resolucion,
    -- Today's stats
    COUNT(d.id) FILTER (WHERE DATE(d.created_at) = CURRENT_DATE) AS deseos_hoy,
    COUNT(d.id) FILTER (WHERE DATE(d.updated_at) = CURRENT_DATE AND d.resolved = TRUE) AS deseos_resueltos_hoy
FROM deseos d
GROUP BY d.consumidor_id, d.tipo;

COMMENT ON VIEW vw_desires_stats IS 'Aggregated desire statistics by type with resolution rates';


-- ==========================================================
-- 9. DAILY SUMMARY DASHBOARD
-- ==========================================================
-- Complete daily summary for main dashboard
CREATE OR REPLACE VIEW vw_daily_summary AS
SELECT 
    c.id AS consumidor_id,
    CURRENT_DATE AS fecha,
    -- Cigarettes/habits today
    (SELECT COUNT(*) 
     FROM formularios f 
     WHERE f.consumidor_id = c.id 
       AND DATE(f.fecha_envio) = CURRENT_DATE
    ) AS cigarrillos_hoy,
    -- Cigarettes this week
    (SELECT COUNT(*) 
     FROM formularios f 
     WHERE f.consumidor_id = c.id 
       AND DATE(f.fecha_envio) >= CURRENT_DATE - INTERVAL '7 days'
    ) AS cigarrillos_semana,
    -- Cigarettes this month
    (SELECT COUNT(*) 
     FROM formularios f 
     WHERE f.consumidor_id = c.id 
       AND DATE(f.fecha_envio) >= CURRENT_DATE - INTERVAL '30 days'
    ) AS cigarrillos_mes,
    -- HR average today
    (SELECT ROUND(AVG(v.hr_mean)::NUMERIC, 2)
     FROM ventanas v
     WHERE v.consumidor_id = c.id
       AND DATE(v.window_start) = CURRENT_DATE
    ) AS hr_promedio_hoy,
    -- Desires today
    (SELECT COUNT(*)
     FROM deseos d
     WHERE d.consumidor_id = c.id
       AND DATE(d.created_at) = CURRENT_DATE
    ) AS deseos_hoy,
    -- Resolved desires today
    (SELECT COUNT(*)
     FROM deseos d
     WHERE d.consumidor_id = c.id
       AND DATE(d.updated_at) = CURRENT_DATE
       AND d.resolved = TRUE
    ) AS deseos_resueltos_hoy,
    -- Active desires (unresolved)
    (SELECT COUNT(*)
     FROM deseos d
     WHERE d.consumidor_id = c.id
       AND d.resolved = FALSE
    ) AS deseos_activos,
    -- Predictions today
    (SELECT COUNT(*)
     FROM analisis a
     JOIN ventanas v ON a.ventana_id = v.id
     WHERE v.consumidor_id = c.id
       AND DATE(v.window_start) = CURRENT_DATE
    ) AS predicciones_hoy,
    -- Total correct predictions (urge detected)
    (SELECT COUNT(*)
     FROM analisis a
     JOIN ventanas v ON a.ventana_id = v.id
     WHERE v.consumidor_id = c.id
       AND a.urge_label = 1
    ) AS total_predicciones_correctas
FROM consumidores c;

COMMENT ON VIEW vw_daily_summary IS 'Daily summary with all key metrics for main dashboard KPI cards';


-- ==========================================================
-- 10. WEEKLY COMPARISON
-- ==========================================================
-- Compare current week vs previous week
CREATE OR REPLACE VIEW vw_weekly_comparison AS
SELECT 
    c.id AS consumidor_id,
    -- Current week (last 7 days)
    (SELECT COUNT(*) 
     FROM formularios f 
     WHERE f.consumidor_id = c.id 
       AND f.fecha_envio >= CURRENT_DATE - INTERVAL '7 days'
    ) AS cigarrillos_semana_actual,
    -- Previous week (8-14 days ago)
    (SELECT COUNT(*) 
     FROM formularios f 
     WHERE f.consumidor_id = c.id 
       AND f.fecha_envio >= CURRENT_DATE - INTERVAL '14 days'
       AND f.fecha_envio < CURRENT_DATE - INTERVAL '7 days'
    ) AS cigarrillos_semana_anterior,
    -- Calculate percentage change
    CASE 
        WHEN (SELECT COUNT(*) 
              FROM formularios f 
              WHERE f.consumidor_id = c.id 
                AND f.fecha_envio >= CURRENT_DATE - INTERVAL '14 days'
                AND f.fecha_envio < CURRENT_DATE - INTERVAL '7 days') > 0
        THEN ROUND(
            ((
                (SELECT COUNT(*) FROM formularios f WHERE f.consumidor_id = c.id AND f.fecha_envio >= CURRENT_DATE - INTERVAL '7 days')::NUMERIC -
                (SELECT COUNT(*) FROM formularios f WHERE f.consumidor_id = c.id AND f.fecha_envio >= CURRENT_DATE - INTERVAL '14 days' AND f.fecha_envio < CURRENT_DATE - INTERVAL '7 days')::NUMERIC
            ) / 
            NULLIF((SELECT COUNT(*) FROM formularios f WHERE f.consumidor_id = c.id AND f.fecha_envio >= CURRENT_DATE - INTERVAL '14 days' AND f.fecha_envio < CURRENT_DATE - INTERVAL '7 days')::NUMERIC, 0)
            ) * 100,
            2
        )
        ELSE NULL
    END AS porcentaje_cambio,
    -- Desires comparison
    (SELECT COUNT(*) 
     FROM deseos d 
     WHERE d.consumidor_id = c.id 
       AND d.created_at >= CURRENT_DATE - INTERVAL '7 days'
    ) AS deseos_semana_actual,
    (SELECT COUNT(*) 
     FROM deseos d 
     WHERE d.consumidor_id = c.id 
       AND d.created_at >= CURRENT_DATE - INTERVAL '14 days'
       AND d.created_at < CURRENT_DATE - INTERVAL '7 days'
    ) AS deseos_semana_anterior
FROM consumidores c;

COMMENT ON VIEW vw_weekly_comparison IS 'Week-over-week comparison for progress tracking';


-- ==========================================================
-- INDEXES FOR VIEW PERFORMANCE
-- ==========================================================
-- Additional indexes to optimize view queries

-- For date-based filtering
CREATE INDEX IF NOT EXISTS idx_formularios_consumidor_fecha 
ON formularios(consumidor_id, fecha_envio DESC);

CREATE INDEX IF NOT EXISTS idx_ventanas_consumidor_window 
ON ventanas(consumidor_id, window_start DESC);

CREATE INDEX IF NOT EXISTS idx_deseos_consumidor_created 
ON deseos(consumidor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deseos_resolved_status 
ON deseos(consumidor_id, resolved);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_ventanas_consumer_date 
ON ventanas(consumidor_id, window_start DESC);

CREATE INDEX IF NOT EXISTS idx_deseos_unresolved 
ON deseos(consumidor_id, resolved) 
WHERE resolved = FALSE;