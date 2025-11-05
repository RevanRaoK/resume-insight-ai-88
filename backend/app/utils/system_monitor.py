"""
System resource monitoring utilities
"""
import asyncio
import psutil
from typing import Dict, Any
from datetime import datetime

from app.utils.logger import get_logger
from app.utils.metrics import metrics_collector

logger = get_logger(__name__)


class SystemResourceMonitor:
    """
    Monitor system resources (CPU, memory, disk) and collect metrics
    """
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.monitoring_task = None
        self.running = False
    
    async def start_monitoring(self):
        """Start continuous system resource monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info(
            "system_monitoring_started",
            collection_interval=self.collection_interval
        )
    
    async def stop_monitoring(self):
        """Stop system resource monitoring"""
        if not self.running:
            return
        
        self.running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("system_monitoring_stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that collects system metrics"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                logger.error(
                    "system_monitoring_error",
                    error=str(e)
                )
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics(self):
        """Collect and record system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            await metrics_collector.record_metric("system_cpu_percent", cpu_percent)
            await metrics_collector.record_metric("system_cpu_count", cpu_count)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            await metrics_collector.record_metric("system_memory_total", memory.total)
            await metrics_collector.record_metric("system_memory_used", memory.used)
            await metrics_collector.record_metric("system_memory_percent", memory.percent)
            await metrics_collector.record_metric("system_memory_available", memory.available)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            await metrics_collector.record_metric("system_disk_total", disk.total)
            await metrics_collector.record_metric("system_disk_used", disk.used)
            await metrics_collector.record_metric("system_disk_percent", (disk.used / disk.total) * 100)
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                await metrics_collector.record_metric("system_network_bytes_sent", network.bytes_sent)
                await metrics_collector.record_metric("system_network_bytes_recv", network.bytes_recv)
                await metrics_collector.record_metric("system_network_packets_sent", network.packets_sent)
                await metrics_collector.record_metric("system_network_packets_recv", network.packets_recv)
            except Exception:
                # Network metrics might not be available on all systems
                pass
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            
            await metrics_collector.record_metric("process_memory_rss", process_memory.rss)
            await metrics_collector.record_metric("process_memory_vms", process_memory.vms)
            await metrics_collector.record_metric("process_cpu_percent", process.cpu_percent())
            await metrics_collector.record_metric("process_num_threads", process.num_threads())
            
            # File descriptor count (Unix-like systems)
            try:
                await metrics_collector.record_metric("process_num_fds", process.num_fds())
            except (AttributeError, psutil.AccessDenied):
                # Not available on Windows or access denied
                pass
            
            logger.debug(
                "system_metrics_collected",
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=(disk.used / disk.total) * 100
            )
            
        except Exception as e:
            logger.error(
                "system_metrics_collection_error",
                error=str(e)
            )
    
    async def get_current_system_status(self) -> Dict[str, Any]:
        """
        Get current system resource status
        
        Returns:
            Dictionary with current system resource information
        """
        try:
            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk information
            disk = psutil.disk_usage('/')
            
            # Process information
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Network information (if available)
            network_info = {}
            try:
                network = psutil.net_io_counters()
                network_info = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            except Exception:
                network_info = {"status": "unavailable"}
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": {
                        "current": cpu_freq.current if cpu_freq else None,
                        "min": cpu_freq.min if cpu_freq else None,
                        "max": cpu_freq.max if cpu_freq else None
                    } if cpu_freq else None
                },
                "memory": {
                    "total": memory.total,
                    "used": memory.used,
                    "available": memory.available,
                    "percent": memory.percent,
                    "swap": {
                        "total": swap.total,
                        "used": swap.used,
                        "percent": swap.percent
                    }
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "pid": process.pid,
                    "create_time": process.create_time()
                },
                "network": network_info
            }
            
        except Exception as e:
            logger.error(
                "system_status_error",
                error=str(e)
            )
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "unavailable"
            }


# Global system monitor instance
system_monitor = SystemResourceMonitor()