# GLiNER Pipeline Implementation Guide

## Implementation Roadmap for API & Document Processing Use Cases

### Phase 1: Core GLiNER Integration (Week 1-2)

#### 1.1 Add GLiNER as Optional Extra
```python
# setup.py updates
extras_require = {
    "gliner": [
        "gliner>=0.2.20",
        "torch>=2.0.0", 
        "transformers>=4.50.0",
        "accelerate>=0.20.0"  # For optimized model loading
    ],
    # ... existing extras
}
```

#### 1.2 Create GLiNER Annotator Class
```python
# datafog/processing/text_processing/gliner_annotator.py
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
import logging

try:
    from gliner import GLiNER
    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False

class GLiNERAnnotator(BaseModel):
    """GLiNER-based PII annotator optimized for accuracy"""
    
    model_name: str = "urchade/gliner_base"
    confidence_threshold: float = 0.7
    _model: Optional[object] = None
    
    class Config:
        arbitrary_types_allowed = True
        
    @classmethod
    def create(cls, model_name: str = "urchade/gliner_base") -> "GLiNERAnnotator":
        """Factory method with dependency checking"""
        if not GLINER_AVAILABLE:
            raise ImportError(
                "GLiNER not available. Install with: pip install datafog[gliner]"
            )
        return cls(model_name=model_name)
    
    @property
    def model(self):
        """Lazy load model to avoid startup penalties"""
        if self._model is None:
            logging.info(f"Loading GLiNER model: {self.model_name}")
            self._model = GLiNER.from_pretrained(self.model_name)
        return self._model
    
    def annotate(self, text: str) -> Dict[str, List[str]]:
        """Match existing DataFog interface"""
        entities = self.annotate_with_confidence(text)
        
        # Convert to DataFog format
        result = {}
        for entity_type, entity_list in entities.items():
            result[entity_type] = [e['text'] for e in entity_list]
        
        return result
    
    def annotate_with_confidence(self, text: str) -> Dict[str, List[Dict]]:
        """Enhanced interface with confidence scores"""
        
        # GLiNER entity labels
        labels = [
            'person', 'email address', 'phone number', 'social security number',
            'credit card number', 'ip address', 'date', 'time', 'organization',
            'address', 'website', 'url', 'medical record number', 'account number'
        ]
        
        # Predict entities
        entities = self.model.predict_entities(
            text, 
            labels, 
            threshold=self.confidence_threshold
        )
        
        # Map to DataFog entity types
        mapping = {
            'person': 'PERSON',
            'email address': 'EMAIL',
            'phone number': 'PHONE',
            'social security number': 'SSN',
            'credit card number': 'CREDIT_CARD',
            'ip address': 'IP_ADDRESS',
            'date': 'DATE',
            'time': 'TIME',
            'organization': 'ORG',
            'address': 'ADDRESS',
            'website': 'URL',
            'url': 'URL',
            'medical record number': 'MEDICAL_RECORD',
            'account number': 'ACCOUNT_NUMBER'
        }
        
        # Group by entity type
        result = {}
        for entity in entities:
            datafog_type = mapping.get(entity['label'].lower())
            if datafog_type:
                if datafog_type not in result:
                    result[datafog_type] = []
                
                result[datafog_type].append({
                    'text': entity['text'],
                    'confidence': entity.get('score', 0),
                    'start': entity.get('start', 0),
                    'end': entity.get('end', 0)
                })
        
        return result
```

#### 1.3 Extend TextService for GLiNER
```python
# datafog/services/text_service.py updates
class TextService:
    def __init__(self, engine: str = "auto"):
        # ... existing code ...
        self.gliner_annotator = None
        
        if engine == "gliner":
            self._initialize_gliner()
        elif engine == "auto":
            # New cascade: regex -> gliner -> spacy
            self.engine = "auto_with_gliner"
    
    def _initialize_gliner(self):
        """Initialize GLiNER with proper error handling"""
        try:
            from datafog.processing.text_processing.gliner_annotator import GLiNERAnnotator
            self.gliner_annotator = GLiNERAnnotator.create()
        except ImportError as e:
            logging.warning(f"GLiNER not available: {e}")
            raise
    
    def _annotate_with_gliner(self, text: str, structured: bool = False):
        """GLiNER annotation with confidence support"""
        if self.gliner_annotator is None:
            self._initialize_gliner()
        
        if structured:
            return self.gliner_annotator.annotate_with_confidence(text)
        else:
            return self.gliner_annotator.annotate(text)
```

### Phase 2: API Optimization (Week 3)

#### 2.1 API-Specific Service
```python
# datafog/services/api_service.py
from typing import Dict, List, Optional
from pydantic import BaseModel
import time

class PiiDetectionRequest(BaseModel):
    text: str
    confidence_threshold: Optional[float] = 0.7
    return_confidence: bool = False
    accuracy_mode: str = "balanced"  # "speed", "balanced", "accuracy"

class PiiDetectionResponse(BaseModel):
    entities: Dict[str, List[Dict]]
    processing_time_ms: float
    total_entities: int
    high_confidence_entities: int

class APIService:
    """Optimized service for API endpoints"""
    
    def __init__(self):
        self.gliner_annotator = None
        self.regex_annotator = None
        self._initialize_annotators()
    
    def _initialize_annotators(self):
        """Pre-load models for API performance"""
        try:
            from datafog.processing.text_processing.gliner_annotator import GLiNERAnnotator
            self.gliner_annotator = GLiNERAnnotator.create()
            # Warm up the model
            self.gliner_annotator.annotate("warmup text")
        except ImportError:
            logging.warning("GLiNER not available, falling back to regex only")
        
        # Initialize regex annotator
        # ... existing code ...
    
    async def detect_pii(self, request: PiiDetectionRequest) -> PiiDetectionResponse:
        """Main API endpoint for PII detection"""
        start_time = time.perf_counter()
        
        if request.accuracy_mode == "speed":
            entities = self._detect_with_regex(request.text)
        elif request.accuracy_mode == "accuracy":
            entities = self._detect_with_gliner(request.text, request.confidence_threshold)
        else:  # balanced
            entities = self._detect_balanced(request.text, request.confidence_threshold)
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        # Calculate metrics
        total_entities = sum(len(v) for v in entities.values())
        high_confidence = sum(
            len([e for e in entity_list if e.get('confidence', 1.0) > 0.9])
            for entity_list in entities.values()
        )
        
        return PiiDetectionResponse(
            entities=entities if request.return_confidence else self._strip_confidence(entities),
            processing_time_ms=processing_time,
            total_entities=total_entities,
            high_confidence_entities=high_confidence
        )
    
    def _detect_balanced(self, text: str, threshold: float) -> Dict:
        """Balanced approach: regex first, GLiNER for edge cases"""
        # Try regex first
        regex_entities = self._detect_with_regex(text)
        
        # If regex finds sufficient entities, use it
        total_regex = sum(len(v) for v in regex_entities.values())
        if total_regex > 0:
            return self._add_confidence_scores(regex_entities, 0.95)  # High confidence for regex
        
        # Otherwise, use GLiNER
        return self._detect_with_gliner(text, threshold)
```

#### 2.2 Document Transfer Service
```python
# datafog/services/transfer_service.py
from typing import Dict, List, Tuple
import hashlib
import json

class DocumentTransferService:
    """Optimized for document transfer pipelines with reversible de-identification"""
    
    def __init__(self):
        self.gliner_annotator = GLiNERAnnotator.create()
        self.entity_counter = 0
    
    def process_for_transfer(self, document: str, doc_id: str) -> Tuple[str, Dict]:
        """Process document for secure transfer with reversible tokens"""
        
        # Detect entities with high accuracy
        entities = self.gliner_annotator.annotate_with_confidence(document)
        
        # Create reversible token mapping
        token_map = {}
        de_identified_text = document
        
        # Process entities in reverse order to maintain positions
        all_entities = []
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                all_entities.append({
                    'type': entity_type,
                    'text': entity['text'],
                    'start': entity['start'],
                    'end': entity['end'],
                    'confidence': entity['confidence']
                })
        
        # Sort by position (reverse order for replacement)
        all_entities.sort(key=lambda x: x['start'], reverse=True)
        
        for entity in all_entities:
            # Only tokenize high-confidence entities
            if entity['confidence'] >= 0.7:
                self.entity_counter += 1
                token = f"{entity['type']}_TOKEN_{self.entity_counter}"
                
                # Store mapping for reversal
                token_map[token] = {
                    'original_text': entity['text'],
                    'entity_type': entity['type'],
                    'confidence': entity['confidence'],
                    'doc_id': doc_id
                }
                
                # Replace in text
                de_identified_text = (
                    de_identified_text[:entity['start']] + 
                    token + 
                    de_identified_text[entity['end']:]
                )
        
        return de_identified_text, token_map
    
    def restore_document(self, de_identified_text: str, token_map: Dict) -> str:
        """Restore original document from tokens"""
        restored_text = de_identified_text
        
        for token, entity_info in token_map.items():
            restored_text = restored_text.replace(token, entity_info['original_text'])
        
        return restored_text
```

### Phase 3: Production Monitoring (Week 4)

#### 3.1 Accuracy Monitoring
```python
# datafog/monitoring/accuracy_monitor.py
from typing import Dict, List
import logging
from datetime import datetime

class AccuracyMonitor:
    """Monitor GLiNER accuracy in production"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger("datafog.accuracy")
    
    def track_detection(self, text: str, entities: Dict, processing_time: float):
        """Track detection metrics"""
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'text_length': len(text),
            'entities_found': sum(len(v) for v in entities.values()),
            'processing_time_ms': processing_time,
            'entities_by_type': {k: len(v) for k, v in entities.items()},
            'high_confidence_count': self._count_high_confidence(entities)
        }
        
        # Log unusual patterns
        if metrics['entities_found'] > 50:  # Unusually high
            self.logger.warning(f"High entity count detected: {metrics}")
        
        if processing_time > 1000:  # > 1 second
            self.logger.warning(f"Slow processing detected: {processing_time}ms")
        
        return metrics
    
    def _count_high_confidence(self, entities: Dict) -> int:
        """Count entities with confidence > 0.9"""
        count = 0
        for entity_list in entities.values():
            if isinstance(entity_list, list) and entity_list:
                if isinstance(entity_list[0], dict):
                    count += len([e for e in entity_list if e.get('confidence', 0) > 0.9])
        return count
```

#### 3.2 Performance Benchmarks
```python
# scripts/gliner_production_benchmark.py
import time
import statistics
from datafog.services.api_service import APIService

def benchmark_production_performance():
    """Benchmark GLiNER for production scenarios"""
    
    api_service = APIService()
    
    # Test cases representing real usage
    test_cases = [
        "Short email with john@example.com and phone (555) 123-4567",
        """
        Longer medical record: Patient John Doe, DOB 03/15/1985, 
        SSN: 123-45-6789, seen by Dr. Sarah Wilson at Medical Center.
        Contact at (555) 123-4567 or john.doe@email.com.
        Insurance: Policy #ABC123456789
        """,
        # Add more realistic test cases...
    ]
    
    results = {}
    
    for i, test_case in enumerate(test_cases):
        times = []
        entities_counts = []
        
        # Run multiple iterations
        for _ in range(10):
            start_time = time.perf_counter()
            
            response = api_service.detect_pii(PiiDetectionRequest(
                text=test_case,
                accuracy_mode="accuracy",
                return_confidence=True
            ))
            
            processing_time = time.perf_counter() - start_time
            times.append(processing_time * 1000)  # Convert to ms
            entities_counts.append(response.total_entities)
        
        results[f"test_case_{i+1}"] = {
            'text_length': len(test_case),
            'avg_time_ms': statistics.mean(times),
            'median_time_ms': statistics.median(times),
            'std_time_ms': statistics.stdev(times),
            'avg_entities': statistics.mean(entities_counts),
            'throughput_chars_per_sec': len(test_case) / (statistics.mean(times) / 1000)
        }
    
    return results

if __name__ == "__main__":
    results = benchmark_production_performance()
    print("Production Performance Benchmark Results:")
    for test_name, metrics in results.items():
        print(f"\n{test_name}:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.2f}")
```

### Phase 4: Customer Validation (Week 5-6)

#### 4.1 A/B Testing Framework
```python
# datafog/testing/ab_testing.py
import random
from enum import Enum

class DetectionEngine(Enum):
    REGEX = "regex"
    GLINER = "gliner"
    BALANCED = "balanced"

class ABTestFramework:
    """A/B test GLiNER vs existing engines"""
    
    def __init__(self, test_percentage: float = 0.1):
        self.test_percentage = test_percentage
        self.results = {}
    
    def should_use_gliner(self, user_id: str) -> bool:
        """Determine if user should get GLiNER (consistent per user)"""
        # Use hash for consistent assignment
        user_hash = hash(user_id) % 100
        return user_hash < (self.test_percentage * 100)
    
    def track_result(self, user_id: str, engine: DetectionEngine, 
                    entities_found: int, processing_time: float, 
                    user_feedback: Optional[str] = None):
        """Track A/B test results"""
        
        if user_id not in self.results:
            self.results[user_id] = []
        
        self.results[user_id].append({
            'engine': engine.value,
            'entities_found': entities_found,
            'processing_time_ms': processing_time,
            'user_feedback': user_feedback,
            'timestamp': datetime.utcnow().isoformat()
        })
```

### Testing Strategy

#### Unit Tests
```python
# tests/test_gliner_annotator.py
import pytest
from datafog.processing.text_processing.gliner_annotator import GLiNERAnnotator

@pytest.mark.skipif(not GLINER_AVAILABLE, reason="GLiNER not installed")
class TestGLiNERAnnotator:
    
    def test_basic_detection(self):
        annotator = GLiNERAnnotator.create()
        text = "Contact John Doe at john@example.com"
        
        entities = annotator.annotate(text)
        
        assert 'PERSON' in entities
        assert 'EMAIL' in entities
        assert 'John Doe' in entities['PERSON']
        assert 'john@example.com' in entities['EMAIL']
    
    def test_confidence_scores(self):
        annotator = GLiNERAnnotator.create()
        text = "SSN: 123-45-6789"
        
        entities = annotator.annotate_with_confidence(text)
        
        assert 'SSN' in entities
        assert len(entities['SSN']) > 0
        assert entities['SSN'][0]['confidence'] > 0.5
    
    def test_empty_text(self):
        annotator = GLiNERAnnotator.create()
        entities = annotator.annotate("")
        assert entities == {}
```

#### Integration Tests
```python
# tests/test_gliner_integration.py
def test_api_service_gliner_mode():
    service = APIService()
    request = PiiDetectionRequest(
        text="John Doe works at Acme Corp, contact: john@acme.com",
        accuracy_mode="accuracy",
        return_confidence=True
    )
    
    response = service.detect_pii(request)
    
    assert response.total_entities > 0
    assert response.processing_time_ms > 0
    assert response.processing_time_ms < 1000  # Should be under 1 second

def test_document_transfer_workflow():
    service = DocumentTransferService()
    original_doc = "Patient John Doe, SSN: 123-45-6789"
    
    de_identified, token_map = service.process_for_transfer(original_doc, "doc_123")
    restored = service.restore_document(de_identified, token_map)
    
    assert original_doc == restored
    assert "John Doe" not in de_identified
    assert "123-45-6789" not in de_identified
```

### Deployment Checklist

- [ ] GLiNER dependencies added to extras_require
- [ ] GLiNERAnnotator class implemented with error handling
- [ ] TextService extended with GLiNER engine option
- [ ] API service optimized for GLiNER workflows
- [ ] Document transfer service with reversible de-identification
- [ ] Production monitoring and accuracy tracking
- [ ] Performance benchmarks established
- [ ] A/B testing framework implemented
- [ ] Unit and integration tests added
- [ ] Documentation updated for new GLiNER features
- [ ] Customer beta testing plan executed
- [ ] Performance monitoring alerts configured