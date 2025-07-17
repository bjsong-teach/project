import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
import redis.asyncio as redis

from models import Post

# 로그 설정을 통해 모든 출력이 즉시 터미널에 보이도록 합니다.
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='--- [Worker] %(message)s')

# 환경 변수 로드
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL)
REDIS_URL = os.getenv("REDIS_URL")

async def sync_redis_to_mysql():
    """Redis의 조회수를 MySQL에 동기화하는 핵심 로직"""
    logging.info("조회수 동기화 작업 시작")
    redis_client = None
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        post_ids_to_sync = await redis_client.zrange("view_sync_queue", 0, -1)
        if not post_ids_to_sync:
            logging.info("동기화할 게시물이 없습니다.")
            return

        logging.info(f"{len(post_ids_to_sync)}개의 동기화 대상 발견: {post_ids_to_sync}")
        
        updates_to_commit = []
        for post_id_str in post_ids_to_sync:
            post_id = int(post_id_str)
            redis_key = f"views:post:{post_id}"
            view_count_str = await redis_client.get(redis_key)
            if view_count_str:
                updates_to_commit.append({"id": post_id, "views": int(view_count_str)})

        if updates_to_commit:
            async with AsyncSession(engine) as session:
                for update in updates_to_commit:
                    db_post = await session.get(Post, update["id"])
                    if db_post:
                        db_post.views = update["views"]
                await session.commit()
                logging.info(f"DB에 {len(updates_to_commit)}개 업데이트 완료.")

        await redis_client.zrem("view_sync_queue", *post_ids_to_sync)
        logging.info("작업 큐 정리 완료.")

    except Exception as e:
        logging.error(f"동기화 중 오류 발생: {e}", exc_info=True)
    finally:
        if redis_client:
            await redis_client.aclose()

async def main_worker_loop():
    """1분마다 동기화 함수를 호출하는 무한 루프"""
    logging.info("백그라운드 워커 시작. 1분마다 작업을 확인합니다.")
    while True:
        await sync_redis_to_mysql()
        await asyncio.sleep(60) # 60초 (1분) 대기

if __name__ == "__main__":
    asyncio.run(main_worker_loop())