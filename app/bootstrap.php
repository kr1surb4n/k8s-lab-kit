<?php
// Shared bootstrap for the A7 stand-in app: read the environment and open
// both databases. The file layout copies Laravel so a real app can replace it.
declare(strict_types=1);

// Read one environment variable with a default.
function env(string $key, string $default = ''): string
{
    $value = getenv($key);
    return $value === false || $value === '' ? $default : $value;
}

// Open the SQLite file that lives on the host mount.
function sqlite(): PDO
{
    $path = env('SQLITE_PATH', '/var/www/html/database/database.sqlite');
    $pdo = new PDO('sqlite:' . $path, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    // DELETE journal: the safe choice on a 9p/hostPath mount.
    $pdo->exec('PRAGMA journal_mode = DELETE');
    $pdo->exec('CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL)');
    if ((int) $pdo->query('SELECT COUNT(*) FROM notes')->fetchColumn() === 0) {
        $pdo->exec("INSERT INTO notes (body) VALUES ('seeded by PHP on first request')");
    }
    return $pdo;
}

// Open the PostgreSQL connection; the caller decides what to do on failure.
function postgres(): PDO
{
    $dsn = sprintf(
        'pgsql:host=%s;port=%s;dbname=%s',
        env('DB_HOST', 'postgres'),
        env('DB_PORT', '5432'),
        env('DB_DATABASE', 'lab')
    );
    return new PDO($dsn, env('DB_USERNAME', 'lab'), env('DB_PASSWORD', ''), [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_TIMEOUT => 3,
    ]);
}
