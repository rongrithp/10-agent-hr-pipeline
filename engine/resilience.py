import time
import random
import functools
from typing import Callable, Any, Tuple, Type

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator สำหรับการทำ Retry กับ External API Calls ด้วย Exponential Backoff และ Jitter
    ดักจับข้อผิดพลาด Network Error, API Rate Limit (429), Transient Server Errors (500/502/503/504)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    err_msg = str(e)
                    
                    if attempt == max_retries:
                        print(f"❌ [Resilience Engine] {func.__name__} ล้มเหลวในการ Retry ครบ {max_retries} ครั้ง: {err_msg}")
                        raise e
                    
                    # คำนวณระยะเวลารอ พร้อมเพิ่ม Jitter ป้องกัน Thundering Herd Problem
                    current_delay = delay
                    if jitter:
                        current_delay += random.uniform(0, current_delay * 0.25)
                    
                    print(f"⚠️ [Resilience Engine] {func.__name__} พบข้อผิดพลาด ({type(e).__name__}): {err_msg[:120]}... | Retry Attempt {attempt}/{max_retries} ใน {current_delay:.2f}s")
                    time.sleep(current_delay)
                    delay *= backoff_factor

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


@retry_with_backoff(max_retries=3, initial_delay=2.0, backoff_factor=2.0)
def generate_content_with_retry(client, model: str, contents: Any, config: Any = None):
    """
    Wrapper ฟังก์ชันสำหรับการเรียก Gemini client.models.generate_content พร้อม Exponential Backoff Retry
    """
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config
    )
