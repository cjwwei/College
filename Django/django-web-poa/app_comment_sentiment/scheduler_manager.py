from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
import subprocess
import datetime

# pip install django-apscheduler

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")

def run_crawler_job():
    subprocess.call(["python", "manage.py", "scrape_yahoo"])

def run_analyzer_job():
    subprocess.call(["python", "manage.py", "analyze_sentiment"])

# 啟動排程器 (背景執行)
try:
    if not scheduler.running:
        scheduler.start()
except Exception as e:
    print(f"啟動排程器時發生錯誤: {e}")

def start_jobs():
    if not scheduler.get_job('crawler_job'):
        
        ## 每天凌晨2:00執行爬蟲任務
        # scheduler.add_job(
        #     run_crawler_job,
        #     'cron',
        #     hour=2,
        #     minute=0,
        #     id='crawler_job',
        #     replace_existing=True,
        #     misfire_grace_time=3600
        # )
        
        # 每小時執行一次爬蟲任務
        scheduler.add_job(
            run_crawler_job,
            'interval',
            hours=1,
            id='crawler_job',
            replace_existing=True,
            misfire_grace_time=3600
        )
    if not scheduler.get_job('analyzer_job'):
        scheduler.add_job(
            run_analyzer_job,
            'cron',
            hour=2,
            minute=0,
            id='analyzer_job',
            replace_existing=True,
            misfire_grace_time=3600
        )

def stop_jobs():
    if scheduler.get_job('crawler_job'):
        scheduler.remove_job('crawler_job')
    if scheduler.get_job('analyzer_job'):
        scheduler.remove_job('analyzer_job')

def get_job_status():
    # 獲取所有任務的詳細資訊
    jobs = []

    def format_job_time(job, attr):
        timestamp = getattr(job, attr, None)
        return timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else None
    
    crawler_job = scheduler.get_job('crawler_job')
    analyzer_job = scheduler.get_job('analyzer_job')
    
    if crawler_job:
        jobs.append({
            'name': '爬蟲任務',
            'description': '每小時執行一次新聞爬蟲',
            'schedule': '每小時',
            'status': 'running' if crawler_job.next_run_time else 'stopped',
            'last_run': format_job_time(crawler_job, 'last_run_time'),
            'next_run': format_job_time(crawler_job, 'next_run_time')
        })
    
    if analyzer_job:
        jobs.append({
            'name': '情緒分析任務',
            'description': '每天凌晨2:00執行情緒分析',
            'schedule': '每天 02:00',
            'status': 'running' if analyzer_job.next_run_time else 'stopped',
            'last_run': format_job_time(analyzer_job, 'last_run_time'),
            'next_run': format_job_time(analyzer_job, 'next_run_time')
        })
    
    return {
        'scheduled': len(jobs) > 0,
        'jobs': jobs,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# 新增：獲取任務執行歷史
def get_execution_history():
    # 這是一個簡單的實現，實際應用中可能需要從資料庫或日誌中獲取
    return {
        'history': [
            {
                'task': '爬蟲任務',
                'start_time': '2024-05-14 09:00:00',
                'end_time': '2024-05-14 09:05:30',
                'status': 'success',
                'duration': '5分30秒'
            },
            {
                'task': '情緒分析任務',
                'start_time': '2024-05-14 02:00:00',
                'end_time': '2024-05-14 02:03:15',
                'status': 'success',
                'duration': '3分15秒'
            }
        ]
    }
