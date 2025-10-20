"""Tests for metrics collection and Prometheus endpoint."""

import pytest
from git_commit_mcp.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    get_metrics_collector,
    reset_metrics_collector,
    record_http_request,
    record_git_commit,
    record_git_push,
    record_git_error,
    record_auth_attempt,
    record_rate_limit_exceeded,
    MetricsTimer
)


class TestCounter:
    """Tests for Counter metric."""
    
    def test_counter_initialization(self):
        """Test counter initializes with zero value."""
        counter = Counter("test_counter", "Test counter")
        assert counter.value == 0.0
        assert counter.name == "test_counter"
        assert counter.help_text == "Test counter"
    
    def test_counter_increment(self):
        """Test counter increments correctly."""
        counter = Counter("test_counter", "Test counter")
        counter.inc()
        assert counter.value == 1.0
        counter.inc(5.0)
        assert counter.value == 6.0
    
    def test_counter_with_labels(self):
        """Test counter with labels."""
        counter = Counter("test_counter", "Test counter", labels={"method": "GET"})
        assert counter.labels == {"method": "GET"}


class TestGauge:
    """Tests for Gauge metric."""
    
    def test_gauge_initialization(self):
        """Test gauge initializes with zero value."""
        gauge = Gauge("test_gauge", "Test gauge")
        assert gauge.value == 0.0
    
    def test_gauge_set(self):
        """Test gauge set operation."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(42.0)
        assert gauge.value == 42.0
    
    def test_gauge_increment(self):
        """Test gauge increment operation."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.inc(10.0)
        assert gauge.value == 10.0
        gauge.inc()
        assert gauge.value == 11.0
    
    def test_gauge_decrement(self):
        """Test gauge decrement operation."""
        gauge = Gauge("test_gauge", "Test gauge")
        gauge.set(10.0)
        gauge.dec(3.0)
        assert gauge.value == 7.0
        gauge.dec()
        assert gauge.value == 6.0


class TestHistogram:
    """Tests for Histogram metric."""
    
    def test_histogram_initialization(self):
        """Test histogram initializes correctly."""
        histogram = Histogram("test_histogram", "Test histogram")
        assert histogram.sum == 0.0
        assert histogram.count == 0
        assert len(histogram.counts) > 0
    
    def test_histogram_observe(self):
        """Test histogram observe operation."""
        histogram = Histogram("test_histogram", "Test histogram")
        histogram.observe(0.5)
        assert histogram.count == 1
        assert histogram.sum == 0.5
        
        histogram.observe(1.5)
        assert histogram.count == 2
        assert histogram.sum == 2.0
    
    def test_histogram_buckets(self):
        """Test histogram bucket counting."""
        histogram = Histogram("test_histogram", "Test histogram")
        histogram.observe(0.01)
        histogram.observe(0.5)
        histogram.observe(5.0)
        
        # Check that buckets are incremented correctly
        assert histogram.counts[0.025] >= 1  # 0.01 should be in this bucket
        assert histogram.counts[1.0] >= 2  # 0.01 and 0.5 should be in this bucket
        assert histogram.counts[float('inf')] == 3  # All values should be in +Inf


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        reset_metrics_collector()
    
    def test_collector_initialization(self):
        """Test collector initializes with standard metrics."""
        collector = get_metrics_collector()
        assert collector is not None
        
        # Check that standard metrics are registered
        text = collector.generate_prometheus_text()
        assert "http_requests_total" in text
        assert "git_commits_total" in text
        assert "git_commit_mcp_health" in text
    
    def test_register_and_increment_counter(self):
        """Test registering and incrementing a counter."""
        collector = get_metrics_collector()
        collector.register_counter("test_counter", "Test counter")
        collector.inc_counter("test_counter", 5.0)
        
        text = collector.generate_prometheus_text()
        assert "test_counter" in text
        assert "5.0" in text or "5" in text
    
    def test_register_and_set_gauge(self):
        """Test registering and setting a gauge."""
        collector = get_metrics_collector()
        collector.register_gauge("test_gauge", "Test gauge")
        collector.set_gauge("test_gauge", 42.0)
        
        text = collector.generate_prometheus_text()
        assert "test_gauge" in text
        assert "42.0" in text or "42" in text
    
    def test_register_and_observe_histogram(self):
        """Test registering and observing a histogram."""
        collector = get_metrics_collector()
        collector.register_histogram("test_histogram", "Test histogram")
        collector.observe_histogram("test_histogram", 0.5)
        collector.observe_histogram("test_histogram", 1.5)
        
        text = collector.generate_prometheus_text()
        assert "test_histogram" in text
        assert "test_histogram_sum" in text
        assert "test_histogram_count" in text
    
    def test_metrics_with_labels(self):
        """Test metrics with labels."""
        collector = get_metrics_collector()
        collector.inc_counter("test_counter", labels={"method": "GET", "status": "200"})
        collector.inc_counter("test_counter", labels={"method": "POST", "status": "201"})
        
        text = collector.generate_prometheus_text()
        assert 'method="GET"' in text
        assert 'method="POST"' in text
        assert 'status="200"' in text
        assert 'status="201"' in text
    
    def test_prometheus_text_format(self):
        """Test Prometheus text format output."""
        collector = get_metrics_collector()
        collector.inc_counter("test_counter", labels={"status": "200"})
        
        text = collector.generate_prometheus_text()
        
        # Check for required Prometheus format elements
        assert "# HELP" in text
        assert "# TYPE" in text
        assert "counter" in text or "gauge" in text
    
    def test_auto_registration(self):
        """Test that metrics are auto-registered when used."""
        collector = get_metrics_collector()
        
        # Use a metric without registering it first
        collector.inc_counter("auto_counter", 1.0)
        
        text = collector.generate_prometheus_text()
        assert "auto_counter" in text


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        reset_metrics_collector()
    
    def test_record_http_request(self):
        """Test recording HTTP request metrics."""
        record_http_request("GET", "/health", 200, 0.5)
        
        collector = get_metrics_collector()
        text = collector.generate_prometheus_text()
        
        assert "http_requests_total" in text
        assert "http_request_duration_seconds" in text
        assert 'method="GET"' in text
        assert 'endpoint="/health"' in text
        assert 'status="200"' in text
    
    def test_record_git_commit(self):
        """Test recording Git commit metrics."""
        record_git_commit(True, 1.5)
        record_git_commit(False, 0.8)
        
        collector = get_metrics_collector()
        text = collector.generate_prometheus_text()
        
        assert "git_commits_total" in text
        assert "git_operation_duration_seconds" in text
        assert 'status="success"' in text
        assert 'status="failure"' in text
    
    def test_record_git_push(self):
        """Test recording Git push metrics."""
        record_git_push(True, 2.0)
        
        collector = get_metrics_collector()
        text = collector.generate_prometheus_text()
        
        assert "git_pushes_total" in text
        assert 'status="success"' in text
    
    def test_record_git_error(self):
        """Test recording Git error metrics."""
        record_git_error("commit", "authentication")
        
        collector = get_metrics_collector()
        text = collector.generate_prometheus_text()
        
        assert "git_operations_errors_total" in text
        assert 'operation="commit"' in text
        assert 'error_type="authentication"' in text
    
    def test_record_auth_attempt(self):
        """Test recording authentication attempt metrics."""
        record_auth_attempt(True)
        record_auth_attempt(False)
        
        collector = get_metrics_collector()
        text = collector.generate_prometheus_text()
        
        assert "auth_attempts_total" in text
        assert 'status="success"' in text
        assert 'status="failure"' in text
    
    def test_record_rate_limit_exceeded(self):
        """Test recording rate limit exceeded metrics."""
        record_rate_limit_exceeded()
        
        collector = get_metrics_collector()
        text = collector.generate_prometheus_text()
        
        assert "rate_limit_exceeded_total" in text


class TestMetricsTimer:
    """Tests for MetricsTimer context manager."""
    
    def test_timer_measures_duration(self):
        """Test that timer measures duration correctly."""
        import time
        
        with MetricsTimer() as timer:
            time.sleep(0.1)
        
        assert timer.duration >= 0.1
        assert timer.duration < 0.2  # Should be close to 0.1
    
    def test_timer_with_exception(self):
        """Test that timer works even when exception occurs."""
        with pytest.raises(ValueError):
            with MetricsTimer() as timer:
                raise ValueError("Test error")
        
        assert timer.duration > 0
