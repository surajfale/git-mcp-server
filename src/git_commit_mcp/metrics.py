"""Metrics collection and Prometheus-compatible endpoint for Git Commit MCP Server.

This module provides metrics tracking for monitoring server performance,
Git operations, and request handling. Metrics are exposed in Prometheus
text format for integration with monitoring systems.
"""

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional
from collections import defaultdict


@dataclass
class Counter:
    """A monotonically increasing counter metric.
    
    Attributes:
        name: Metric name
        help_text: Description of what this metric measures
        value: Current counter value
        labels: Dictionary of label key-value pairs
    """
    name: str
    help_text: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment the counter by the specified amount.
        
        Args:
            amount: Amount to increment (default: 1.0)
        """
        self.value += amount
    
    def get(self) -> float:
        """Get the current counter value.
        
        Returns:
            Current counter value
        """
        return self.value


@dataclass
class Gauge:
    """A gauge metric that can go up and down.
    
    Attributes:
        name: Metric name
        help_text: Description of what this metric measures
        value: Current gauge value
        labels: Dictionary of label key-value pairs
    """
    name: str
    help_text: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def set(self, value: float) -> None:
        """Set the gauge to a specific value.
        
        Args:
            value: New gauge value
        """
        self.value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment the gauge by the specified amount.
        
        Args:
            amount: Amount to increment (default: 1.0)
        """
        self.value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement the gauge by the specified amount.
        
        Args:
            amount: Amount to decrement (default: 1.0)
        """
        self.value -= amount
    
    def get(self) -> float:
        """Get the current gauge value.
        
        Returns:
            Current gauge value
        """
        return self.value


@dataclass
class Histogram:
    """A histogram metric for tracking distributions of values.
    
    Attributes:
        name: Metric name
        help_text: Description of what this metric measures
        buckets: List of bucket boundaries
        counts: Count of observations in each bucket
        sum: Sum of all observed values
        count: Total number of observations
        labels: Dictionary of label key-value pairs
    """
    name: str
    help_text: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    counts: Dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize bucket counts."""
        for bucket in self.buckets:
            self.counts[bucket] = 0
        # Add +Inf bucket
        self.counts[float('inf')] = 0
    
    def observe(self, value: float) -> None:
        """Record an observation.
        
        Args:
            value: Value to observe
        """
        self.sum += value
        self.count += 1
        
        # Increment bucket counts
        for bucket in sorted(self.counts.keys()):
            if value <= bucket:
                self.counts[bucket] += 1


class MetricsCollector:
    """Central metrics collector for the MCP server.
    
    This class manages all metrics and provides thread-safe access
    for recording and retrieving metric values.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._lock = Lock()
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        
        # Initialize standard metrics
        self._init_standard_metrics()
    
    def _init_standard_metrics(self) -> None:
        """Initialize standard metrics for the server."""
        # Request metrics
        self.register_counter(
            "http_requests_total",
            "Total number of HTTP requests",
            labels={"method": "", "endpoint": "", "status": ""}
        )
        
        self.register_histogram(
            "http_request_duration_seconds",
            "HTTP request latency in seconds",
            labels={"method": "", "endpoint": ""}
        )
        
        # Git operation metrics
        self.register_counter(
            "git_commits_total",
            "Total number of Git commits created",
            labels={"status": ""}
        )
        
        self.register_counter(
            "git_pushes_total",
            "Total number of Git pushes attempted",
            labels={"status": ""}
        )
        
        self.register_counter(
            "git_operations_errors_total",
            "Total number of Git operation errors",
            labels={"operation": "", "error_type": ""}
        )
        
        self.register_histogram(
            "git_operation_duration_seconds",
            "Git operation duration in seconds",
            labels={"operation": ""}
        )
        
        # Authentication metrics
        self.register_counter(
            "auth_attempts_total",
            "Total number of authentication attempts",
            labels={"status": ""}
        )
        
        self.register_counter(
            "rate_limit_exceeded_total",
            "Total number of rate limit exceeded events"
        )
        
        # Server metrics
        self.register_gauge(
            "server_info",
            "Server information",
            labels={"version": "1.0.0"}
        )
        
        self.register_gauge(
            "server_health",
            "Server health status (1 = healthy, 0 = unhealthy)"
        )
        
        # Set initial values
        self.set_gauge("server_info", 1.0, labels={"version": "1.0.0"})
        self.set_gauge("server_health", 1.0)
    
    def register_counter(self, name: str, help_text: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Register a new counter metric.
        
        Args:
            name: Metric name
            help_text: Description of the metric
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key not in self._counters:
                self._counters[key] = Counter(name, help_text, labels=labels or {})
    
    def register_gauge(self, name: str, help_text: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Register a new gauge metric.
        
        Args:
            name: Metric name
            help_text: Description of the metric
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key not in self._gauges:
                self._gauges[key] = Gauge(name, help_text, labels=labels or {})
    
    def register_histogram(self, name: str, help_text: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Register a new histogram metric.
        
        Args:
            name: Metric name
            help_text: Description of the metric
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key not in self._histograms:
                self._histograms[key] = Histogram(name, help_text, labels=labels or {})
    
    def inc_counter(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric.
        
        Args:
            name: Metric name
            amount: Amount to increment (default: 1.0)
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key in self._counters:
                self._counters[key].inc(amount)
            else:
                # Auto-register if not exists (without nested lock)
                self._counters[key] = Counter(name, f"Auto-registered counter: {name}", labels=labels or {})
                self._counters[key].inc(amount)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric to a specific value.
        
        Args:
            name: Metric name
            value: New gauge value
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key in self._gauges:
                self._gauges[key].set(value)
            else:
                # Auto-register if not exists (without nested lock)
                self._gauges[key] = Gauge(name, f"Auto-registered gauge: {name}", labels=labels or {})
                self._gauges[key].set(value)
    
    def inc_gauge(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a gauge metric.
        
        Args:
            name: Metric name
            amount: Amount to increment (default: 1.0)
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key in self._gauges:
                self._gauges[key].inc(amount)
    
    def dec_gauge(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement a gauge metric.
        
        Args:
            name: Metric name
            amount: Amount to decrement (default: 1.0)
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key in self._gauges:
                self._gauges[key].dec(amount)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation in a histogram metric.
        
        Args:
            name: Metric name
            value: Value to observe
            labels: Optional label key-value pairs
        """
        with self._lock:
            key = self._make_key(name, labels or {})
            if key in self._histograms:
                self._histograms[key].observe(value)
            else:
                # Auto-register if not exists (without nested lock)
                self._histograms[key] = Histogram(name, f"Auto-registered histogram: {name}", labels=labels or {})
                self._histograms[key].observe(value)
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key for a metric with labels.
        
        Args:
            name: Metric name
            labels: Label key-value pairs
            
        Returns:
            Unique key string
        """
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus text format.
        
        Args:
            labels: Label key-value pairs
            
        Returns:
            Formatted label string
        """
        if not labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"
    
    def generate_prometheus_text(self) -> str:
        """Generate metrics in Prometheus text format.
        
        Returns:
            Metrics formatted as Prometheus text
        """
        lines = []
        
        with self._lock:
            # Group metrics by name
            counter_groups = defaultdict(list)
            gauge_groups = defaultdict(list)
            histogram_groups = defaultdict(list)
            
            for counter in self._counters.values():
                counter_groups[counter.name].append(counter)
            
            for gauge in self._gauges.values():
                gauge_groups[gauge.name].append(gauge)
            
            for histogram in self._histograms.values():
                histogram_groups[histogram.name].append(histogram)
            
            # Format counters
            for name, counters in sorted(counter_groups.items()):
                lines.append(f"# HELP {name} {counters[0].help_text}")
                lines.append(f"# TYPE {name} counter")
                for counter in counters:
                    labels_str = self._format_labels(counter.labels)
                    lines.append(f"{name}{labels_str} {counter.value}")
                lines.append("")
            
            # Format gauges
            for name, gauges in sorted(gauge_groups.items()):
                lines.append(f"# HELP {name} {gauges[0].help_text}")
                lines.append(f"# TYPE {name} gauge")
                for gauge in gauges:
                    labels_str = self._format_labels(gauge.labels)
                    lines.append(f"{name}{labels_str} {gauge.value}")
                lines.append("")
            
            # Format histograms
            for name, histograms in sorted(histogram_groups.items()):
                lines.append(f"# HELP {name} {histograms[0].help_text}")
                lines.append(f"# TYPE {name} histogram")
                for histogram in histograms:
                    labels_str = self._format_labels(histogram.labels)
                    
                    # Output bucket counts
                    for bucket in sorted(histogram.counts.keys()):
                        bucket_labels = dict(histogram.labels)
                        bucket_labels["le"] = str(bucket) if bucket != float('inf') else "+Inf"
                        bucket_labels_str = self._format_labels(bucket_labels)
                        lines.append(f"{name}_bucket{bucket_labels_str} {histogram.counts[bucket]}")
                    
                    # Output sum and count
                    lines.append(f"{name}_sum{labels_str} {histogram.sum}")
                    lines.append(f"{name}_count{labels_str} {histogram.count}")
                lines.append("")
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset all metrics to their initial state.
        
        This is primarily useful for testing.
        """
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._init_standard_metrics()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector.
    
    This is primarily useful for testing.
    """
    global _metrics_collector
    _metrics_collector = None


# Convenience functions for common operations

def record_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record an HTTP request with metrics.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Request endpoint path
        status: HTTP status code
        duration: Request duration in seconds
    """
    collector = get_metrics_collector()
    collector.inc_counter(
        "http_requests_total",
        labels={"method": method, "endpoint": endpoint, "status": str(status)}
    )
    collector.observe_histogram(
        "http_request_duration_seconds",
        duration,
        labels={"method": method, "endpoint": endpoint}
    )


def record_git_commit(success: bool, duration: float) -> None:
    """Record a Git commit operation.
    
    Args:
        success: Whether the commit was successful
        duration: Operation duration in seconds
    """
    collector = get_metrics_collector()
    status = "success" if success else "failure"
    collector.inc_counter("git_commits_total", labels={"status": status})
    collector.observe_histogram(
        "git_operation_duration_seconds",
        duration,
        labels={"operation": "commit"}
    )


def record_git_push(success: bool, duration: float) -> None:
    """Record a Git push operation.
    
    Args:
        success: Whether the push was successful
        duration: Operation duration in seconds
    """
    collector = get_metrics_collector()
    status = "success" if success else "failure"
    collector.inc_counter("git_pushes_total", labels={"status": status})
    collector.observe_histogram(
        "git_operation_duration_seconds",
        duration,
        labels={"operation": "push"}
    )


def record_git_error(operation: str, error_type: str) -> None:
    """Record a Git operation error.
    
    Args:
        operation: Git operation that failed (commit, push, etc.)
        error_type: Type of error encountered
    """
    collector = get_metrics_collector()
    collector.inc_counter(
        "git_operations_errors_total",
        labels={"operation": operation, "error_type": error_type}
    )


def record_auth_attempt(success: bool) -> None:
    """Record an authentication attempt.
    
    Args:
        success: Whether authentication was successful
    """
    collector = get_metrics_collector()
    status = "success" if success else "failure"
    collector.inc_counter("auth_attempts_total", labels={"status": status})


def record_rate_limit_exceeded() -> None:
    """Record a rate limit exceeded event."""
    collector = get_metrics_collector()
    collector.inc_counter("rate_limit_exceeded_total")


class MetricsTimer:
    """Context manager for timing operations.
    
    Example:
        with MetricsTimer() as timer:
            # Do some work
            pass
        duration = timer.duration
    """
    
    def __init__(self):
        """Initialize the timer."""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: float = 0.0
    
    def __enter__(self) -> 'MetricsTimer':
        """Start the timer.
        
        Returns:
            Self for context manager protocol
        """
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop the timer and calculate duration.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.end_time = time.time()
        if self.start_time is not None:
            self.duration = self.end_time - self.start_time
