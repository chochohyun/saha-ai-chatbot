"""
APScheduler 스케줄러.
start_scheduler(job_fn) 을 호출하면 매일 새벽 01:00 KST에 job_fn 을 실행합니다.
job_fn 을 외부에서 주입받으므로 순환 임포트가 없습니다.
"""

import logging
from typing import Callable

logger = logging.getLogger("incremental_crawl")


def start_scheduler(job_fn: Callable):
    """
    APScheduler BackgroundScheduler 시작.

    Args:
        job_fn: 매일 새벽 01:00 KST 에 실행할 함수 (인수 없음)

    Returns:
        실행 중인 scheduler 인스턴스, 또는 APScheduler 미설치 시 None
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler 미설치 → 자동 스케줄링 비활성화. "
            "`pip install apscheduler` 후 서버를 재시작하세요."
        )
        return None

    # uvicorn 기본 워커 수 = 1 (--workers 미지정 시)
    # 워커가 2개 이상이면 각 프로세스가 독립적으로 스케줄러를 기동합니다.
    # 이 경우 APScheduler 대신 시스템 cron 사용을 권장합니다.
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        job_fn,
        trigger=CronTrigger(hour=1, minute=0, timezone="Asia/Seoul"),
        id="incremental_crawl",
        name="증분 크롤링 (매일 새벽 01:00 KST)",
        replace_existing=True,
        misfire_grace_time=3600,  # 1시간 이내 놓친 실행은 즉시 보완
    )
    scheduler.start()
    logger.info(
        "스케줄러 시작 — 매일 01:00 KST 증분 크롤링 예약 "
        "(단일 uvicorn 워커 전제; 다중 워커 시 cron 대체 권장)"
    )
    return scheduler


def stop_scheduler(scheduler) -> None:
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
