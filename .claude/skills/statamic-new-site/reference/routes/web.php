<?php

use Illuminate\Support\Facades\Route;

// Route::redirect('/old/page-name', '/new-page', 301);

Route::redirect('/sitemap', '/sitemap.xml', 301);
Route::statamic('sitemap.xml', 'sitemap_xml', [
    'layout' => null,
    'content_type' => 'text/xml',
]);
