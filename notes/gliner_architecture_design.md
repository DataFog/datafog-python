# GLiNER Architecture Design for DataFog v4.2.0+

## System Architecture Overview

### Current DataFog Architecture
```
DataFog Core
├── Simple API (detect, process)
├── TextService (regex, spacy, auto engines)
├── RegexAnnotator (fast, structured PII)
├── SpacyPIIAnnotator (contextual, comprehensive)
└── Anonymizer (redact, replace, hash)
```

### Proposed GLiNER Integration Architecture
```
DataFog Enhanced
├── Simple API (detect, process) - Enhanced with accuracy modes
├── TextService (regex, gliner, spacy, smart_cascade engines)
├── API Service (optimized for endpoints)
├── Transfer Service (reversible de-identification)
├── Annotators
│   ├── RegexAnnotator (speed-optimized)
│   ├── GLiNERAnnotator (accuracy-optimized) [NEW]
│   └── SpacyPIIAnnotator (comprehensive)
├── Monitoring
│   ├── AccuracyMonitor [NEW]
│   └── PerformanceTracker [NEW]
└── Enhanced Anonymizer (with confidence-based processing)
```

## Core Design Principles

### 1. **Backward Compatibility**
- All existing APIs remain unchanged
- New GLiNER features are additive, not replacing
- Graceful degradation when GLiNER dependencies unavailable

### 2. **Performance Optimization**
- Lazy loading of GLiNER models
- Model caching and reuse across requests
- Configurable accuracy vs speed trade-offs

### 3. **Production Readiness**
- Comprehensive error handling
- Monitoring and observability
- A/B testing capabilities

### 4. **Flexibility**
- Multiple detection modes (speed/balanced/accuracy)
- Configurable confidence thresholds
- Engine selection per use case

## Detailed Component Design

### 1. Enhanced Simple API

```python
# Enhanced simple API with accuracy modes
def detect(text: str, mode: str = "balanced") -> Dict[str, List[str]]:
    """
    Detect PII with configurable accuracy modes
    
    Args:
        text: Input text to scan
        mode: "speed" (regex), "balanced" (smart), "accuracy" (GLiNER)
    """
    pass

def process(text: str, method: str = "redact", mode: str = "balanced") -> str:
    """
    Process text with PII anonymization
    
    Args:
        text: Input text
        method: "redact", "replace", "hash"
        mode: Detection accuracy mode
    """
    pass

# New API for advanced use cases
def detect_with_confidence(text: str, threshold: float = 0.7) -> Dict[str, List[Dict]]:
    """
    Detect PII with confidence scores and positions
    
    Returns:
        {
            "PERSON": [
                {"text": "John Doe", "confidence": 0.95, "start": 0, "end": 8}
            ],
            "EMAIL": [...]
        }
    """
    pass
```

### 2. Engine Selection Strategy

```python
class EngineSelector:
    """Smart engine selection based on use case"""
    
    def select_engine(self, text: str, mode: str, context: Dict) -> str:
        """
        Select optimal engine based on:
        - Mode preference (speed/balanced/accuracy)
        - Text characteristics (length, complexity)
        - Context (API vs batch, compliance requirements)
        """
        
        if mode == "speed":
            return "regex"
        elif mode == "accuracy":
            return "gliner"
        elif mode == "balanced":
            return self._smart_selection(text, context)
    
    def _smart_selection(self, text: str, context: Dict) -> str:
        """
        Smart selection algorithm:
        1. Short text + API context -> GLiNER (accuracy matters)
        2. Long text + batch context -> cascade (regex first)
        3. High compliance requirement -> GLiNER
        4. Performance critical -> regex
        """
        
        # Text characteristics
        text_length = len(text)
        complexity_score = self._calculate_complexity(text)
        
        # Context factors
        is_api_request = context.get('source') == 'api'
        compliance_critical = context.get('compliance_required', False)
        performance_critical = context.get('performance_critical', False)
        
        # Decision matrix
        if compliance_critical or (is_api_request and text_length < 10000):
            return "gliner"
        elif performance_critical:
            return "regex"
        else:
            return "cascade"  # Try regex first, GLiNER if insufficient
```

### 3. Cascade Processing Architecture

```python
class CascadeProcessor:
    """Intelligent cascade processing for optimal accuracy/speed balance"""
    
    def __init__(self):
        self.regex_annotator = RegexAnnotator()
        self.gliner_annotator = None  # Lazy loaded
        self.performance_tracker = PerformanceTracker()
    
    def process_cascade(self, text: str, min_entities: int = 1) -> Dict:
        """
        Cascade processing:
        1. Try regex first (fast)
        2. Evaluate results quality
        3. Use GLiNER if needed for better coverage
        """
        
        # Stage 1: Regex detection
        start_time = time.perf_counter()
        regex_entities = self.regex_annotator.annotate(text)
        regex_time = time.perf_counter() - start_time
        
        # Evaluate regex results
        total_entities = sum(len(v) for v in regex_entities.values())
        confidence_score = self._evaluate_regex_confidence(text, regex_entities)
        
        # Decision: is regex sufficient?
        if total_entities >= min_entities and confidence_score > 0.7:
            self.performance_tracker.record('regex_sufficient', regex_time)
            return self._format_with_confidence(regex_entities, 0.9)
        
        # Stage 2: GLiNER for better coverage
        if self.gliner_annotator is None:
            self.gliner_annotator = GLiNERAnnotator.create()
        
        start_time = time.perf_counter()
        gliner_entities = self.gliner_annotator.annotate_with_confidence(text)
        gliner_time = time.perf_counter() - start_time
        
        # Merge results (prefer GLiNER for overlaps)
        merged_entities = self._merge_entity_results(regex_entities, gliner_entities)
        
        self.performance_tracker.record('cascade_full', regex_time + gliner_time)
        return merged_entities
    
    def _evaluate_regex_confidence(self, text: str, entities: Dict) -> float:
        """
        Evaluate how confident we are in regex results
        Based on:
        - Entity density
        - Pattern complexity in text
        - Known regex limitations
        """
        
        # Simple heuristic: if text has complex formatting, regex confidence lower
        complexity_indicators = [
            'dr.', 'mr.', 'mrs.',  # Titles that might indicate missed persons
            'born', 'dob',  # Date contexts
            'contact', 'reach',  # Communication contexts
        ]
        
        complexity_count = sum(1 for indicator in complexity_indicators if indicator in text.lower())
        entity_density = sum(len(v) for v in entities.values()) / max(1, len(text) // 100)
        
        # Lower confidence if high complexity but low entity detection
        if complexity_count > 2 and entity_density < 1:
            return 0.5
        
        return min(1.0, 0.8 + entity_density * 0.2)
```

### 4. Monitoring and Observability Architecture

```python
class MonitoringSystem:
    """Comprehensive monitoring for GLiNER integration"""
    
    def __init__(self):
        self.accuracy_monitor = AccuracyMonitor()
        self.performance_monitor = PerformanceMonitor()
        self.alert_manager = AlertManager()
    
    def track_detection_request(self, request_id: str, context: Dict):
        """Track complete detection lifecycle"""
        
        return DetectionTracker(
            request_id=request_id,
            context=context,
            monitors=[self.accuracy_monitor, self.performance_monitor]
        )

class DetectionTracker:
    """Context manager for tracking individual detection requests"""
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.total_time = time.perf_counter() - self.start_time
        self._record_metrics()
    
    def record_engine_used(self, engine: str, processing_time: float):
        """Record which engine was used and performance"""
        self.engine = engine
        self.engine_time = processing_time
    
    def record_entities(self, entities: Dict, confidence_stats: Dict):
        """Record entity detection results"""
        self.entities = entities
        self.confidence_stats = confidence_stats
    
    def _record_metrics(self):
        """Send metrics to monitoring systems"""
        
        metrics = {
            'request_id': self.request_id,
            'total_time_ms': self.total_time * 1000,
            'engine_used': getattr(self, 'engine', 'unknown'),
            'engine_time_ms': getattr(self, 'engine_time', 0) * 1000,
            'entities_found': sum(len(v) for v in getattr(self, 'entities', {}).values()),
            'avg_confidence': self.confidence_stats.get('avg_confidence', 0),
            'high_confidence_entities': self.confidence_stats.get('high_confidence_count', 0)
        }
        
        # Send to monitoring systems
        for monitor in self.monitors:
            monitor.record_metrics(metrics)
        
        # Check for alerts
        self._check_alerts(metrics)
```

### 5. API Gateway Architecture

```python
class DataFogAPIGateway:
    """Main API gateway with intelligent routing"""
    
    def __init__(self):
        self.speed_service = TextService(engine="regex")
        self.accuracy_service = TextService(engine="gliner")
        self.balanced_service = TextService(engine="cascade")
        self.monitoring = MonitoringSystem()
        
        # Pre-warm GLiNER model for API responsiveness
        self._warmup_models()
    
    async def detect_pii_endpoint(self, request: PiiDetectionRequest) -> PiiDetectionResponse:
        """Main PII detection API endpoint"""
        
        with self.monitoring.track_detection_request(request.id, request.context) as tracker:
            
            # Route to appropriate service
            if request.mode == "speed":
                service = self.speed_service
            elif request.mode == "accuracy":
                service = self.accuracy_service
            else:
                service = self.balanced_service
            
            # Process request
            start_time = time.perf_counter()
            entities = service.annotate_text_sync(
                request.text, 
                structured=request.return_confidence
            )
            processing_time = time.perf_counter() - start_time
            
            # Track metrics
            tracker.record_engine_used(service.engine, processing_time)
            tracker.record_entities(entities, self._calculate_confidence_stats(entities))
            
            # Format response
            return self._format_api_response(entities, processing_time, request)
    
    def _warmup_models(self):
        """Pre-warm models to reduce first-request latency"""
        
        # Warm up GLiNER with sample text
        try:
            self.accuracy_service.annotate_text_sync("Sample text for John Doe at john@example.com")
            logging.info("GLiNER model warmed up successfully")
        except Exception as e:
            logging.warning(f"GLiNER warmup failed: {e}")
```

### 6. Configuration Management

```python
class GLiNERConfig:
    """Configuration management for GLiNER integration"""
    
    # Model configurations
    MODEL_CONFIGS = {
        "gliner_base": {
            "model_name": "urchade/gliner_base",
            "default_threshold": 0.7,
            "max_processing_time_ms": 1000,
            "memory_usage_mb": 500
        },
        "gliner_medium": {
            "model_name": "urchade/gliner_medium-v2.1", 
            "default_threshold": 0.6,
            "max_processing_time_ms": 1500,
            "memory_usage_mb": 800
        }
    }
    
    # Engine selection rules
    ENGINE_RULES = {
        "api_short_text": {
            "condition": lambda text, context: len(text) < 5000 and context.get('source') == 'api',
            "engine": "gliner",
            "reason": "API requests prioritize accuracy for short text"
        },
        "batch_long_text": {
            "condition": lambda text, context: len(text) > 50000 and context.get('source') == 'batch',
            "engine": "cascade",
            "reason": "Large documents benefit from cascade approach"
        },
        "compliance_critical": {
            "condition": lambda text, context: context.get('compliance_required', False),
            "engine": "gliner",
            "reason": "Compliance scenarios require maximum accuracy"
        }
    }
    
    @classmethod
    def select_optimal_config(cls, text: str, context: Dict) -> Dict:
        """Select optimal configuration based on use case"""
        
        # Apply rules in priority order
        for rule_name, rule in cls.ENGINE_RULES.items():
            if rule['condition'](text, context):
                return {
                    'engine': rule['engine'],
                    'model_config': cls.MODEL_CONFIGS.get('gliner_base'),
                    'reason': rule['reason']
                }
        
        # Default configuration
        return {
            'engine': 'balanced',
            'model_config': cls.MODEL_CONFIGS['gliner_base'],
            'reason': 'Default balanced approach'
        }
```

## Deployment Architecture

### Container Strategy
```dockerfile
# Dockerfile for GLiNER-enabled DataFog
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install DataFog with GLiNER support
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install datafog[gliner]

# Pre-download GLiNER model to reduce startup time
RUN python -c "from gliner import GLiNER; GLiNER.from_pretrained('urchade/gliner_base')"

# Application code
COPY . /app
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from datafog import detect; detect('test')" || exit 1

CMD ["python", "-m", "datafog.api_server"]
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datafog-gliner
spec:
  replicas: 3
  selector:
    matchLabels:
      app: datafog-gliner
  template:
    metadata:
      labels:
        app: datafog-gliner
    spec:
      containers:
      - name: datafog
        image: datafog:gliner-v4.2.0
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi" 
            cpu: "1000m"
        env:
        - name: GLINER_MODEL_CACHE
          value: "/app/model_cache"
        - name: ACCURACY_MODE
          value: "balanced"
        volumeMounts:
        - name: model-cache
          mountPath: /app/model_cache
      volumes:
      - name: model-cache
        emptyDir:
          sizeLimit: 2Gi
```

### Load Balancing Strategy
```python
class LoadBalancer:
    """Smart load balancing for GLiNER requests"""
    
    def __init__(self):
        self.instances = {
            'speed': [SpeedInstance() for _ in range(5)],
            'accuracy': [AccuracyInstance() for _ in range(2)],
            'balanced': [BalancedInstance() for _ in range(3)]
        }
        self.request_queue = RequestQueue()
    
    def route_request(self, request: PiiDetectionRequest) -> Instance:
        """Route request to optimal instance"""
        
        # Check instance health and load
        available_instances = [
            instance for instance in self.instances[request.mode]
            if instance.is_healthy() and instance.current_load < 0.8
        ]
        
        if not available_instances:
            # Fallback to different mode if needed
            return self._fallback_routing(request)
        
        # Select least loaded instance
        return min(available_instances, key=lambda x: x.current_load)
```

## Testing Strategy

### Performance Testing
```python
class GLiNERPerformanceTest:
    """Comprehensive performance testing for GLiNER integration"""
    
    def test_api_response_times(self):
        """Test API response times under various loads"""
        
        test_scenarios = [
            {'mode': 'speed', 'expected_max_ms': 50},
            {'mode': 'balanced', 'expected_max_ms': 300},
            {'mode': 'accuracy', 'expected_max_ms': 1000}
        ]
        
        for scenario in test_scenarios:
            with self.subTest(mode=scenario['mode']):
                response_times = []
                
                for _ in range(100):
                    start_time = time.perf_counter()
                    response = self.api_client.detect_pii(
                        text=self.sample_text,
                        mode=scenario['mode']
                    )
                    response_time = (time.perf_counter() - start_time) * 1000
                    response_times.append(response_time)
                
                avg_time = statistics.mean(response_times)
                p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
                
                self.assertLess(avg_time, scenario['expected_max_ms'])
                self.assertLess(p95_time, scenario['expected_max_ms'] * 1.5)
    
    def test_memory_usage(self):
        """Test memory usage patterns"""
        
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Load GLiNER model
        annotator = GLiNERAnnotator.create()
        model_load_memory = process.memory_info().rss / 1024 / 1024
        
        # Process multiple documents
        for _ in range(50):
            annotator.annotate(self.sample_text)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        # Assertions
        self.assertLess(model_load_memory - baseline_memory, 1000)  # <1GB for model
        self.assertLess(final_memory - model_load_memory, 100)     # <100MB growth
```

This architecture provides a comprehensive foundation for integrating GLiNER into DataFog while maintaining performance, reliability, and backward compatibility.