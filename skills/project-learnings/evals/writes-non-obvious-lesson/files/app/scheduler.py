import ratelib

# Nightly report at 02:00 local time.
scheduler = ratelib.Scheduler(tz="America/Sao_Paulo")


def schedule_report(job):
    scheduler.cron("0 2 * * *", job)
