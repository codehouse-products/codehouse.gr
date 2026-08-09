<?php
// Temporary diagnostic — delete after use
header('Content-Type: text/plain');
echo "DOCUMENT_ROOT: " . $_SERVER['DOCUMENT_ROOT'] . "\n";
echo "SCRIPT_FILENAME: " . $_SERVER['SCRIPT_FILENAME'] . "\n";
echo "realpath(__DIR__): " . realpath(__DIR__) . "\n";
echo "PHP_SELF: " . $_SERVER['PHP_SELF'] . "\n";
