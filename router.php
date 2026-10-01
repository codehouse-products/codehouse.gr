<?php
/**
 * PHP preview router. Never expose private/archive lead data or development
 * files through the built-in web server. Production nginx needs equivalent
 * restrictions; see nginx-private.conf.
 */
$requestPath = rawurldecode(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/');
$segments = [];
foreach (explode('/', str_replace('\\', '/', $requestPath)) as $segment) {
    if ($segment === '' || $segment === '.') {
        continue;
    }
    if ($segment === '..') {
        array_pop($segments);
    } else {
        $segments[] = $segment;
    }
}
$path = '/' . implode('/', $segments);
$blocked = preg_match('~^/(?:leads|scripts|attached_assets|docs)(?:/|$)~i', $path)
    || preg_match('~(?:^|/)\.(?!well-known(?:/|$))~i', $path)
    || preg_match('~\.(?:jsonl|log|env|sql|sqlite|ini|bak)(?:$|/)~i', $path)
    || in_array($path, ['/main.py', '/pyproject.toml', '/uv.lock', '/replit.md', '/router.php', '/nginx-private.conf', '/nginx-perf.conf'], true);
if ($blocked) {
    http_response_code(404);
    header('Cache-Control: no-store');
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Not found';
    return true;
}
return false;