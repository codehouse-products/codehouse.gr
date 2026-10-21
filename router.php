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
$blocked = preg_match('~^/(?:leads|scripts|attached_assets|docs|editorial|deployment)(?:/|$)~i', $path)
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
// Keep preview semantics aligned with the production nginx routing include.
// Preserve query strings, but use fixed destinations (never user input).
$redirects = [
    '/dimiourgia-site' => '/dimioyrgia-site/',
    '/blog/checklist-dorean-istoselida' => '/blog/dorean-istoselida/',
    '/blog/checklist-dorean-istoselida-epixeirisi' => '/blog/dorean-istoselida/',
    '/dorean-istoselida' => '/prosfora/',
    '/en/blog/checklist-dorean-istoselida' => '/en/blog/dorean-istoselida/',
    '/en/blog/checklist-dorean-istoselida-epixeirisi' => '/en/blog/dorean-istoselida/',
    '/en/dorean-istoselida' => '/en/prosfora/',
];
if (isset($redirects[$path])) {
    $query = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_QUERY);
    header('Location: ' . $redirects[$path] . ($query !== null && $query !== '' ? '?' . $query : ''), true, 301);
    return true;
}
return false;