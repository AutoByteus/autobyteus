# file: autobyteus/llm/utils/rate_limiter.py
import asyncio
import time
from autobyteus.llm.utils.llm_config import LLMConfig

class RateLimiter:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.rate_limit = config.rate_limit
        self.time_window = 60  # seconds, configurable
        self.request_count = 0
        self.window_start = time.time()

    async def wait_if_needed(self):
        if not self.rate_limit:
            return

        current_time = time.time()
        time_passed = current_time - self.window_start

        if time_passed < self.time_window:
            if self.request_count >= self.rate_limit:
                wait_time = self.time_window - time_passed
                await asyncio.sleep(wait_time)
                self.request_count = 1
                self.window_start = time.time()
            else:
                self.request_count += 1
        else:
            self.request_count = 1
            self.window_start = current_time

    @property
    def rate_limit(self):
        return self._rate_limit

    @rate_limit.setter
    def rate_limit(self, value):
        if value is not None and value <= 0:
            raise ValueError("Rate limit must be a positive integer or None")
        self._rate_limit = value