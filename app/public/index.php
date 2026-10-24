<?php
// A7 front page: prove that the pod reads both databases, and that the SQLite
// file on the host is the same file the container sees.
declare(strict_types=1);

require __DIR__ . '/../bootstrap.php';

$sqliteRows = [];
$sqliteError = null;
$pgRows = [];
$pgError = null;

// SQLite is local and must always work; a failure here is a mount/permission bug.
try {
    $sqliteRows = sqlite()->query('SELECT id, body FROM notes ORDER BY id')->fetchAll();
} catch (Throwable $e) {
    $sqliteError = $e->getMessage();
}

// PostgreSQL may legitimately be down; show the error instead of a blank page.
try {
    $pdo = postgres();
    $pdo->exec('CREATE TABLE IF NOT EXISTS notes (id SERIAL PRIMARY KEY, body TEXT NOT NULL)');
    if ((int) $pdo->query('SELECT COUNT(*) FROM notes')->fetchColumn() === 0) {
        $pdo->exec("INSERT INTO notes (body) VALUES ('seeded by PHP on first request')");
    }
    $pgRows = $pdo->query('SELECT id, body FROM notes ORDER BY id')->fetchAll();
} catch (Throwable $e) {
    $pgError = $e->getMessage();
}

// Small helper for output escaping.
function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>k8s lab — A7</title>
    <style>
      body { font-family: system-ui, sans-serif; margin: 3rem; background: #0f172a; color: #e2e8f0; }
      code, pre { background: #1e293b; padding: .15rem .4rem; border-radius: .25rem; }
      .ok { color: #4ade80; } .bad { color: #f87171; }
      section { margin-bottom: 2rem; }
    </style>
  </head>
  <body>
    <h1>k8s lab — A7</h1>
    <p>Pod: <code><?= e(getenv('HOSTNAME') ?: 'unknown') ?></code></p>

    <section>
      <h2>SQLite <code><?= e(env('SQLITE_PATH')) ?></code></h2>
      <?php if ($sqliteError !== null): ?>
        <p class="bad">failed: <?= e($sqliteError) ?></p>
      <?php else: ?>
        <p class="ok">read <?= count($sqliteRows) ?> row(s) through the host mount</p>
        <ul>
          <?php foreach ($sqliteRows as $row): ?>
            <li><code>#<?= e((string) $row['id']) ?></code> <?= e($row['body']) ?></li>
          <?php endforeach; ?>
        </ul>
        <p>Add a row on the host, reload, and it appears here. No restart.</p>
      <?php endif; ?>
    </section>

    <section>
      <h2>PostgreSQL <code><?= e(env('DB_HOST')) ?>/<?= e(env('DB_DATABASE')) ?></code></h2>
      <?php if ($pgError !== null): ?>
        <p class="bad">failed: <?= e($pgError) ?></p>
      <?php else: ?>
        <p class="ok">read <?= count($pgRows) ?> row(s)</p>
        <ul>
          <?php foreach ($pgRows as $row): ?>
            <li><code>#<?= e((string) $row['id']) ?></code> <?= e($row['body']) ?></li>
          <?php endforeach; ?>
        </ul>
      <?php endif; ?>
    </section>
  </body>
</html>
