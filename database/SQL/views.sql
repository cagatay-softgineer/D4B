CREATE OR REPLACE VIEW v_active_users AS
SELECT
    id,
    email,
    name,
    avatar_url,
    status,
    role,
    created_at,
    updated_at
FROM users
WHERE status = 'active';

CREATE OR REPLACE VIEW v_current_system_health AS
SELECT *
FROM system_health
ORDER BY last_updated DESC
LIMIT 1;

CREATE OR REPLACE VIEW v_job_overview AS
SELECT
    j.id,
    j.job_code,
    j.title,
    j.status,
    j.priority,
    j.location,
    j.latitude,
    j.longitude,
    j.created_at,
    j.updated_at,
    j.completed_at,
    reporter.email AS reporter_email,
    assignee.email AS assignee_email,
    t.name AS team_name
FROM jobs j
LEFT JOIN users reporter ON j.reporter_id = reporter.id
LEFT JOIN users assignee ON j.assignee_id = assignee.id
LEFT JOIN teams t ON j.team_id = t.id;

CREATE OR REPLACE VIEW v_job_status_history AS
SELECT
    h.id,
    h.job_id,
    j.title AS job_title,
    h.old_status,
    h.new_status,
    h.changed_at,
    u.id AS user_id,
    u.name AS user_name
FROM job_status_history h
JOIN jobs j ON h.job_id = j.id
LEFT JOIN users u ON h.changed_by = u.id;

CREATE OR REPLACE VIEW v_latest_job_metrics AS
SELECT *
FROM job_metrics
ORDER BY created_at DESC
LIMIT 1;

CREATE OR REPLACE VIEW v_open_jobs AS
SELECT
    j.id,
    j.job_code,
    j.title,
    j.priority,
    t.name AS team_name,
    j.status,
    j.created_at
FROM jobs j
LEFT JOIN teams t ON j.team_id = t.id
WHERE j.status = 'open';

CREATE OR REPLACE VIEW v_open_jobs_priority AS
SELECT
    priority,
    COUNT(*) AS open_jobs
FROM jobs
WHERE status = 'open'
GROUP BY priority
ORDER BY
    CASE priority
        WHEN 'Critical' THEN 1
        WHEN 'High' THEN 2
        WHEN 'Medium' THEN 3
        WHEN 'Low' THEN 4
        ELSE 5
    END;

CREATE OR REPLACE VIEW v_recent_activity_logs AS
SELECT
    l.id,
    l.action,
    l.type,
    l.user_id,
    u.name AS user_name,
    u.email AS user_email,
    l.details,
    l.timestamp
FROM activity_logs l
LEFT JOIN users u ON l.user_id = u.id
ORDER BY l.timestamp DESC
LIMIT 100;

CREATE OR REPLACE VIEW v_team_members AS
SELECT
    tm.team_id,
    t.name AS team_name,
    u.id AS user_id,
    u.name AS user_name,
    u.email,
    tm.joined_at
FROM team_members tm
JOIN teams t ON tm.team_id = t.id
JOIN users u ON tm.user_id = u.id;

CREATE OR REPLACE VIEW v_unread_notifications AS
SELECT
    n.id,
    n.user_id,
    u.name AS user_name,
    n.job_id,
    j.title AS job_title,
    n.message,
    n.status,
    n.created_at
FROM notifications n
LEFT JOIN users u ON n.user_id = u.id
LEFT JOIN jobs j ON n.job_id = j.id
WHERE n.status = 'unread';
