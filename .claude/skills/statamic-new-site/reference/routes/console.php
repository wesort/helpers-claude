<?php

use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Schedule;
use Illuminate\Support\Stringable;

/*
|--------------------------------------------------------------------------
| Schedule
|--------------------------------------------------------------------------
|
| Runs from one Forge scheduled job on production, every minute:
| php8.x /home/forge/DOMAIN/current/artisan schedule:run
|
| Statamic adds its own jobs, including publishing scheduled entries to
| search and static caching when their date arrives. See docs/deploy.md.
|
*/

// Commit content edited in the control panel and push it to GitHub
Schedule::exec('bash autobackup.sh')
    ->name('content-backup')
    ->dailyAt('03:00')
    ->timezone('Europe/London')
    ->environments('production')
    ->withoutOverlapping()
    ->appendOutputTo(storage_path('logs/autobackup.log'))
    ->onFailureWithOutput(function (Stringable $output) {
        // Logged as an error, so it reaches the alerts channel when LOG_SLACK_WEBHOOK_URL is set
        Log::error('Content backup failed: autobackup.sh exited with an error', [
            'output' => (string) $output->explode("\n")->filter()->take(-15)->implode("\n"),
        ]);
    });
