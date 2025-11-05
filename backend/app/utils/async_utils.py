"""
Async processing utilities for performance optimization
"""
import asyncio
import time
from typing import AsyncGenerator, List, Any, Callable, Optional, Dict
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncProcessingPipeline:
    """
    Async generator-based processing pipeline for streaming document processing
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_in_chunks(
        self, 
        data: List[Any], 
        processor: Callable,
        chunk_size: int = 10
    ) -> AsyncGenerator[Any, None]:
        """
        Process data in chunks asynchronously using generators
        
        Args:
            data: List of items to process
            processor: Async function to process each item
            chunk_size: Number of items to process in parallel
            
        Yields:
            Processed results as they complete
        """
        start_time = time.time()
        total_items = len(data)
        processed_count = 0
        
        logger.info(
            "async_pipeline_started",
            total_items=total_items,
            chunk_size=chunk_size,
            max_workers=self.max_workers
        )
        
        # Process data in chunks
        for i in range(0, total_items, chunk_size):
            chunk = data[i:i + chunk_size]
            
            # Create tasks for the chunk
            tasks = [processor(item) for item in chunk]
            
            # Process chunk concurrently
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for j, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            "pipeline_item_failed",
                            item_index=i + j,
                            error=str(result)
                        )
                        continue
                    
                    processed_count += 1
                    yield result
                    
            except Exception as e:
                logger.error(
                    "pipeline_chunk_failed",
                    chunk_start=i,
                    chunk_size=len(chunk),
                    error=str(e)
                )
                continue
        
        processing_time = time.time() - start_time
        logger.info(
            "async_pipeline_completed",
            total_items=total_items,
            processed_items=processed_count,
            processing_time=processing_time,
            items_per_second=processed_count / processing_time if processing_time > 0 else 0
        )
    
    async def process_with_semaphore(
        self,
        items: List[Any],
        processor: Callable,
        max_concurrent: int = 10
    ) -> List[Any]:
        """
        Process items with concurrency control using semaphore
        
        Args:
            items: List of items to process
            processor: Async function to process each item
            max_concurrent: Maximum number of concurrent operations
            
        Returns:
            List of processed results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_processor(item):
            async with semaphore:
                return await processor(item)
        
        start_time = time.time()
        
        logger.info(
            "semaphore_processing_started",
            total_items=len(items),
            max_concurrent=max_concurrent
        )
        
        try:
            results = await asyncio.gather(
                *[bounded_processor(item) for item in items],
                return_exceptions=True
            )
            
            # Filter out exceptions and log them
            successful_results = []
            error_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(
                        "semaphore_item_failed",
                        item_index=i,
                        error=str(result)
                    )
                else:
                    successful_results.append(result)
            
            processing_time = time.time() - start_time
            
            logger.info(
                "semaphore_processing_completed",
                total_items=len(items),
                successful_items=len(successful_results),
                failed_items=error_count,
                processing_time=processing_time
            )
            
            return successful_results
            
        except Exception as e:
            logger.error(
                "semaphore_processing_error",
                error=str(e)
            )
            raise
    
    def close(self):
        """Close the thread pool executor"""
        self.executor.shutdown(wait=True)


class ConnectionPoolOptimizer:
    """
    Advanced connection pool management with health monitoring
    """
    
    def __init__(self):
        self.pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "failed_connections": 0,
            "connection_wait_time": 0.0
        }
        self._lock = asyncio.Lock()
    
    @asynccontextmanager
    async def get_optimized_connection(self, pool):
        """
        Get connection with performance monitoring and optimization
        
        Args:
            pool: Database connection pool
            
        Yields:
            Database connection with performance tracking
        """
        start_time = time.time()
        connection = None
        
        try:
            async with self._lock:
                self.pool_stats["total_connections"] += 1
            
            # Acquire connection with timeout
            connection = await asyncio.wait_for(
                pool.acquire(),
                timeout=30.0  # 30 second timeout
            )
            
            connection_wait_time = time.time() - start_time
            
            async with self._lock:
                self.pool_stats["active_connections"] += 1
                self.pool_stats["connection_wait_time"] += connection_wait_time
            
            logger.debug(
                "connection_acquired",
                wait_time=connection_wait_time,
                pool_size=pool.get_size(),
                idle_connections=pool.get_idle_size()
            )
            
            yield connection
            
        except asyncio.TimeoutError:
            async with self._lock:
                self.pool_stats["failed_connections"] += 1
            
            logger.error(
                "connection_timeout",
                wait_time=time.time() - start_time,
                pool_size=pool.get_size() if pool else 0
            )
            raise
            
        except Exception as e:
            async with self._lock:
                self.pool_stats["failed_connections"] += 1
            
            logger.error(
                "connection_error",
                error=str(e),
                wait_time=time.time() - start_time
            )
            raise
            
        finally:
            if connection:
                try:
                    await pool.release(connection)
                    
                    async with self._lock:
                        self.pool_stats["active_connections"] -= 1
                        
                    logger.debug("connection_released")
                    
                except Exception as e:
                    logger.error(
                        "connection_release_error",
                        error=str(e)
                    )
    
    async def get_pool_metrics(self, pool) -> Dict[str, Any]:
        """
        Get comprehensive pool performance metrics
        
        Args:
            pool: Database connection pool
            
        Returns:
            Dictionary with pool performance metrics
        """
        async with self._lock:
            avg_wait_time = (
                self.pool_stats["connection_wait_time"] / 
                max(1, self.pool_stats["total_connections"])
            )
            
            return {
                "pool_size": pool.get_size() if pool else 0,
                "idle_connections": pool.get_idle_size() if pool else 0,
                "max_size": pool.get_max_size() if pool else 0,
                "total_connections_requested": self.pool_stats["total_connections"],
                "active_connections": self.pool_stats["active_connections"],
                "failed_connections": self.pool_stats["failed_connections"],
                "average_wait_time": avg_wait_time,
                "success_rate": (
                    (self.pool_stats["total_connections"] - self.pool_stats["failed_connections"]) /
                    max(1, self.pool_stats["total_connections"])
                ) * 100
            }


class BackgroundTaskProcessor:
    """
    Background task processing for long-running analyses (optional enhancement)
    """
    
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.task_queue = asyncio.Queue()
        self.workers = []
        self.running = False
        self.processed_tasks = 0
        self.failed_tasks = 0
    
    async def start(self):
        """Start background task workers"""
        if self.running:
            return
        
        self.running = True
        
        logger.info(
            "background_processor_starting",
            max_workers=self.max_workers
        )
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        logger.info("background_processor_started")
    
    async def stop(self):
        """Stop background task workers"""
        if not self.running:
            return
        
        self.running = False
        
        logger.info("background_processor_stopping")
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        
        logger.info(
            "background_processor_stopped",
            processed_tasks=self.processed_tasks,
            failed_tasks=self.failed_tasks
        )
    
    async def submit_task(self, task_func: Callable, *args, **kwargs):
        """
        Submit a task for background processing
        
        Args:
            task_func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        if not self.running:
            await self.start()
        
        task_data = {
            "func": task_func,
            "args": args,
            "kwargs": kwargs,
            "submitted_at": time.time()
        }
        
        await self.task_queue.put(task_data)
        
        logger.debug(
            "background_task_submitted",
            function_name=task_func.__name__,
            queue_size=self.task_queue.qsize()
        )
    
    async def _worker(self, worker_name: str):
        """
        Background worker that processes tasks from the queue
        
        Args:
            worker_name: Name identifier for the worker
        """
        logger.info("background_worker_started", worker_name=worker_name)
        
        while self.running:
            try:
                # Wait for task with timeout
                task_data = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                start_time = time.time()
                wait_time = start_time - task_data["submitted_at"]
                
                logger.debug(
                    "background_task_processing",
                    worker_name=worker_name,
                    function_name=task_data["func"].__name__,
                    wait_time=wait_time
                )
                
                # Execute the task
                try:
                    await task_data["func"](*task_data["args"], **task_data["kwargs"])
                    
                    processing_time = time.time() - start_time
                    self.processed_tasks += 1
                    
                    logger.info(
                        "background_task_completed",
                        worker_name=worker_name,
                        function_name=task_data["func"].__name__,
                        processing_time=processing_time,
                        wait_time=wait_time
                    )
                    
                except Exception as e:
                    self.failed_tasks += 1
                    
                    logger.error(
                        "background_task_failed",
                        worker_name=worker_name,
                        function_name=task_data["func"].__name__,
                        error=str(e)
                    )
                
                # Mark task as done
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # No tasks available, continue waiting
                continue
                
            except asyncio.CancelledError:
                logger.info("background_worker_cancelled", worker_name=worker_name)
                break
                
            except Exception as e:
                logger.error(
                    "background_worker_error",
                    worker_name=worker_name,
                    error=str(e)
                )
                continue
        
        logger.info("background_worker_stopped", worker_name=worker_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get background processor statistics"""
        return {
            "running": self.running,
            "workers": len(self.workers),
            "queue_size": self.task_queue.qsize(),
            "processed_tasks": self.processed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": (
                self.processed_tasks / max(1, self.processed_tasks + self.failed_tasks)
            ) * 100
        }


def async_timer(func):
    """
    Decorator to measure async function execution time
    
    Args:
        func: Async function to time
        
    Returns:
        Wrapped function with timing
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.debug(
                "async_function_completed",
                function_name=func.__name__,
                execution_time=execution_time
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                "async_function_failed",
                function_name=func.__name__,
                execution_time=execution_time,
                error=str(e)
            )
            raise
    
    return wrapper


# Global instances
async_pipeline = AsyncProcessingPipeline()
connection_optimizer = ConnectionPoolOptimizer()
background_processor = BackgroundTaskProcessor()