#!/usr/bin/env python3
"""
GLiNER Research Script for DataFog Integration Analysis

This script conducts comprehensive research on GLiNER's performance characteristics
and compatibility with DataFog's existing architecture to inform v4.2.0 integration decisions.

Research Tasks:
1. Basic GLiNER functionality validation
2. Performance benchmarking vs DataFog's regex (190x) and spaCy engines
3. Entity type mapping analysis
4. Model comparison (base/medium/large)
5. PII detection accuracy testing

Usage:
    python scripts/gliner_research.py
"""

import json
import os
import sys
import time
import traceback
from typing import Any, Dict

# Check if GLiNER is available
try:
    from gliner import GLiNER

    GLINER_AVAILABLE = True
except ImportError:
    print("GLiNER not available. Please install with:")
    print("pip install gliner torch transformers")
    GLINER_AVAILABLE = False

# DataFog imports for comparison
try:
    from datafog import detect
    from datafog.processing.text_processing.regex_annotator import RegexAnnotator

    DATAFOG_AVAILABLE = True
except ImportError:
    print("DataFog not available in current environment")
    DATAFOG_AVAILABLE = False

# spaCy imports for comparison
try:
    import spacy

    from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator

    SPACY_AVAILABLE = True
except ImportError:
    print("spaCy not available. Install with: pip install datafog[nlp]")
    SPACY_AVAILABLE = False


class GLiNERResearcher:
    """Comprehensive GLiNER research and analysis for DataFog integration"""

    def __init__(self):
        self.results = {
            "environment": {
                "gliner_available": GLINER_AVAILABLE,
                "datafog_available": DATAFOG_AVAILABLE,
                "spacy_available": SPACY_AVAILABLE,
            },
            "models": {},
            "performance": {},
            "entity_mapping": {},
            "accuracy": {},
            "recommendations": {},
        }

        # Test data - same as DataFog's benchmark data
        self.test_text = """
        Dear John Doe,
        
        Thank you for your inquiry. Please contact us at support@company.com or call (555) 123-4567.
        Our office is located at 123 Main Street, Springfield, IL 62701.
        
        Your account number is 987654321 and your social security number 123-45-6789 is on file.
        Please verify your credit card 4532-1234-5678-9012 for payment processing.
        
        We have scheduled your appointment for March 15, 2024 at 2:30 PM.
        Dr. Sarah Wilson will be your primary physician.
        
        Best regards,
        Customer Service Team
        MedCorp Healthcare Solutions
        Phone: +1 (800) 555-0199
        Email: billing@medcorp.com
        Website: https://www.medcorp.com
        
        IP Address for reference: 192.168.1.100
        Server Log: user_id=12345 logged in from 10.0.0.1 at 2024-03-15T14:30:00Z
        """

        # Expected PII entities for accuracy testing
        self.expected_entities = {
            "PERSON": ["John Doe", "Dr. Sarah Wilson"],
            "EMAIL": ["support@company.com", "billing@medcorp.com"],
            "PHONE": ["(555) 123-4567", "+1 (800) 555-0199"],
            "SSN": ["123-45-6789"],
            "CREDIT_CARD": ["4532-1234-5678-9012"],
            "IP_ADDRESS": ["192.168.1.100", "10.0.0.1"],
            "DATE": ["March 15, 2024"],
            "TIME": ["2:30 PM"],
            "ORG": ["MedCorp Healthcare Solutions", "Customer Service Team"],
            "ADDRESS": ["123 Main Street, Springfield, IL 62701"],
        }

        # GLiNER label mapping to DataFog entity types
        self.gliner_labels = [
            "person",
            "email address",
            "phone number",
            "social security number",
            "credit card number",
            "ip address",
            "date",
            "time",
            "organization",
            "address",
            "location",
            "company",
            "doctor",
            "medical facility",
        ]

    def task_1_basic_functionality(self) -> Dict[str, Any]:
        """Task 1: Basic GLiNER functionality validation"""
        print("\n=== Task 1: Basic GLiNER Functionality Validation ===")

        if not GLINER_AVAILABLE:
            return {"status": "skipped", "reason": "GLiNER not available"}

        try:
            # Load default GLiNER model
            print("Loading GLiNER base model...")
            start_time = time.perf_counter()
            model = GLiNER.from_pretrained("urchade/gliner_base")
            load_time = time.perf_counter() - start_time

            print(f"Model loaded in {load_time:.2f} seconds")

            # Test basic entity detection
            print("Testing basic entity detection...")
            entities = model.predict_entities(
                self.test_text, self.gliner_labels, threshold=0.5
            )

            print(f"Found {len(entities)} entities:")
            for entity in entities[:10]:  # Show first 10
                print(
                    f"  {entity['label']}: '{entity['text']}' (confidence: {entity.get('score', 'N/A'):.3f})"
                )

            if len(entities) > 10:
                print(f"  ... and {len(entities) - 10} more entities")

            return {
                "status": "success",
                "model_load_time": load_time,
                "entities_found": len(entities),
                "sample_entities": entities[:5],  # First 5 for analysis
                "all_entities": entities,  # All entities for further processing
            }

        except Exception as e:
            print(f"Error in basic functionality test: {e}")
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    def task_2_performance_benchmarking(self) -> Dict[str, Any]:
        """Task 2: Performance benchmarking against DataFog's baselines"""
        print("\n=== Task 2: Performance Benchmarking ===")

        results = {
            "gliner": {"status": "skipped"},
            "regex": {"status": "skipped"},
            "spacy": {"status": "skipped"},
            "comparison": {},
        }

        # Benchmark GLiNER
        if GLINER_AVAILABLE:
            try:
                print("Benchmarking GLiNER...")
                model = GLiNER.from_pretrained("urchade/gliner_base")

                # Warmup run
                model.predict_entities(self.test_text[:100], ["person"], threshold=0.5)

                # Measured runs
                times = []
                for i in range(5):
                    start = time.perf_counter()
                    entities = model.predict_entities(
                        self.test_text, self.gliner_labels, threshold=0.5
                    )
                    end = time.perf_counter()
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                text_size_kb = len(self.test_text.encode("utf-8")) / 1024
                throughput = text_size_kb / avg_time

                results["gliner"] = {
                    "status": "success",
                    "avg_time_ms": avg_time * 1000,
                    "throughput_kb_per_s": throughput,
                    "entities_found": len(entities),
                    "individual_times": [t * 1000 for t in times],
                }

                print(
                    f"GLiNER: {avg_time*1000:.1f}ms avg, {throughput:.1f} KB/s, {len(entities)} entities"
                )

            except Exception as e:
                print(f"GLiNER benchmark error: {e}")
                results["gliner"] = {"status": "error", "error": str(e)}

        # Benchmark DataFog Regex (for comparison)
        if DATAFOG_AVAILABLE:
            try:
                print("Benchmarking DataFog Regex...")

                # Warmup
                detect(self.test_text[:100])

                # Measured runs
                times = []
                for i in range(5):
                    start = time.perf_counter()
                    entities = detect(self.test_text)
                    end = time.perf_counter()
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                text_size_kb = len(self.test_text.encode("utf-8")) / 1024
                throughput = text_size_kb / avg_time

                results["regex"] = {
                    "status": "success",
                    "avg_time_ms": avg_time * 1000,
                    "throughput_kb_per_s": throughput,
                    "entities_found": sum(len(v) for v in entities.values()),
                    "individual_times": [t * 1000 for t in times],
                }

                print(
                    f"Regex: {avg_time*1000:.1f}ms avg, {throughput:.1f} KB/s, {sum(len(v) for v in entities.values())} entities"
                )

            except Exception as e:
                print(f"Regex benchmark error: {e}")
                results["regex"] = {"status": "error", "error": str(e)}

        # Benchmark spaCy (if available)
        if SPACY_AVAILABLE:
            try:
                print("Benchmarking spaCy...")
                annotator = SpacyPIIAnnotator.create()

                # Warmup
                annotator.annotate(self.test_text[:100])

                # Measured runs
                times = []
                for i in range(5):
                    start = time.perf_counter()
                    entities = annotator.annotate(self.test_text)
                    end = time.perf_counter()
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                text_size_kb = len(self.test_text.encode("utf-8")) / 1024
                throughput = text_size_kb / avg_time

                results["spacy"] = {
                    "status": "success",
                    "avg_time_ms": avg_time * 1000,
                    "throughput_kb_per_s": throughput,
                    "entities_found": sum(len(v) for v in entities.values()),
                    "individual_times": [t * 1000 for t in times],
                }

                print(
                    f"spaCy: {avg_time*1000:.1f}ms avg, {throughput:.1f} KB/s, {sum(len(v) for v in entities.values())} entities"
                )

            except Exception as e:
                print(f"spaCy benchmark error: {e}")
                results["spacy"] = {"status": "error", "error": str(e)}

        # Calculate performance comparisons
        if results["gliner"]["status"] == "success":
            gliner_time = results["gliner"]["avg_time_ms"]

            if results["regex"]["status"] == "success":
                regex_time = results["regex"]["avg_time_ms"]
                results["comparison"][
                    "gliner_vs_regex"
                ] = f"{regex_time / gliner_time:.1f}x faster than GLiNER"
                results["comparison"][
                    "regex_vs_gliner"
                ] = f"{gliner_time / regex_time:.1f}x faster than regex"

            if results["spacy"]["status"] == "success":
                spacy_time = results["spacy"]["avg_time_ms"]
                results["comparison"][
                    "gliner_vs_spacy"
                ] = f"{spacy_time / gliner_time:.1f}x faster than spaCy"
                results["comparison"][
                    "spacy_vs_gliner"
                ] = f"{gliner_time / spacy_time:.1f}x faster than GLiNER"

        return results

    def task_3_entity_mapping(self) -> Dict[str, Any]:
        """Task 3: Entity type mapping analysis"""
        print("\n=== Task 3: Entity Type Mapping Analysis ===")

        if not GLINER_AVAILABLE:
            return {"status": "skipped", "reason": "GLiNER not available"}

        try:
            model = GLiNER.from_pretrained("urchade/gliner_base")
            entities = model.predict_entities(
                self.test_text, self.gliner_labels, threshold=0.4
            )

            # Create mapping from GLiNER to DataFog format
            gliner_to_datafog = {
                "person": "PERSON",
                "email address": "EMAIL",
                "phone number": "PHONE",
                "social security number": "SSN",
                "credit card number": "CREDIT_CARD",
                "ip address": "IP_ADDRESS",
                "date": "DATE",
                "time": "TIME",
                "organization": "ORG",
                "company": "ORG",
                "address": "ADDRESS",
                "location": "LOCATION",
                "doctor": "PERSON",
                "medical facility": "ORG",
            }

            # Group entities by DataFog type
            mapped_entities = {}
            unmapped_entities = []

            for entity in entities:
                gliner_label = entity["label"].lower()
                datafog_type = gliner_to_datafog.get(gliner_label)

                if datafog_type:
                    if datafog_type not in mapped_entities:
                        mapped_entities[datafog_type] = []
                    mapped_entities[datafog_type].append(
                        {
                            "text": entity["text"],
                            "confidence": entity.get("score", 0),
                            "gliner_label": entity["label"],
                        }
                    )
                else:
                    unmapped_entities.append(entity)

            print("Entity mapping results:")
            for datafog_type, entities_list in mapped_entities.items():
                print(f"  {datafog_type}: {len(entities_list)} entities")
                for ent in entities_list[:3]:  # Show first 3
                    print(f"    '{ent['text']}' (confidence: {ent['confidence']:.3f})")

            if unmapped_entities:
                print(f"\nUnmapped entities ({len(unmapped_entities)}):")
                for ent in unmapped_entities[:5]:
                    print(f"  {ent['label']}: '{ent['text']}'")

            return {
                "status": "success",
                "mapping_schema": gliner_to_datafog,
                "mapped_entities": mapped_entities,
                "unmapped_entities": unmapped_entities,
                "total_entities": len(entities),
                "mapped_count": len(entities) - len(unmapped_entities),
                "unmapped_count": len(unmapped_entities),
            }

        except Exception as e:
            print(f"Error in entity mapping: {e}")
            return {"status": "error", "error": str(e)}

    def task_4_model_comparison(self) -> Dict[str, Any]:
        """Task 4: Model comparison (base/medium/large)"""
        print("\n=== Task 4: Model Comparison ===")

        if not GLINER_AVAILABLE:
            return {"status": "skipped", "reason": "GLiNER not available"}

        models_to_test = [
            "urchade/gliner_base",
            "urchade/gliner_medium-v2.1",
            "urchade/gliner_large-v2.1",
        ]

        results = {}

        for model_name in models_to_test:
            print(f"\nTesting {model_name}...")

            try:
                # Load model and measure load time
                start_load = time.perf_counter()
                model = GLiNER.from_pretrained(model_name)
                load_time = time.perf_counter() - start_load

                # Test processing speed
                start_process = time.perf_counter()
                entities = model.predict_entities(
                    self.test_text, self.gliner_labels, threshold=0.5
                )
                process_time = time.perf_counter() - start_process

                text_size_kb = len(self.test_text.encode("utf-8")) / 1024
                throughput = text_size_kb / process_time

                results[model_name] = {
                    "status": "success",
                    "load_time_s": load_time,
                    "process_time_ms": process_time * 1000,
                    "throughput_kb_per_s": throughput,
                    "entities_found": len(entities),
                    "avg_confidence": (
                        sum(e.get("score", 0) for e in entities) / len(entities)
                        if entities
                        else 0
                    ),
                }

                print(
                    f"  Load: {load_time:.1f}s, Process: {process_time*1000:.1f}ms, Entities: {len(entities)}"
                )

            except Exception as e:
                print(f"  Error: {e}")
                results[model_name] = {"status": "error", "error": str(e)}

        return results

    def task_5_accuracy_testing(self) -> Dict[str, Any]:
        """Task 5: PII detection accuracy testing"""
        print("\n=== Task 5: PII Detection Accuracy Testing ===")

        results = {
            "gliner": {"status": "skipped"},
            "regex": {"status": "skipped"},
            "comparison": {},
        }

        # Test GLiNER accuracy
        if GLINER_AVAILABLE:
            try:
                model = GLiNER.from_pretrained("urchade/gliner_base")
                entities = model.predict_entities(
                    self.test_text, self.gliner_labels, threshold=0.4
                )

                # Map to DataFog format for comparison
                gliner_to_datafog = {
                    "person": "PERSON",
                    "email address": "EMAIL",
                    "phone number": "PHONE",
                    "social security number": "SSN",
                    "credit card number": "CREDIT_CARD",
                    "ip address": "IP_ADDRESS",
                    "date": "DATE",
                    "time": "TIME",
                    "organization": "ORG",
                    "company": "ORG",
                    "address": "ADDRESS",
                }

                detected = {}
                for entity in entities:
                    datafog_type = gliner_to_datafog.get(entity["label"].lower())
                    if datafog_type:
                        if datafog_type not in detected:
                            detected[datafog_type] = []
                        detected[datafog_type].append(entity["text"])

                # Calculate precision/recall
                total_expected = sum(len(v) for v in self.expected_entities.values())
                total_detected = sum(len(v) for v in detected.values())

                # Simple overlap counting (could be more sophisticated)
                correct = 0
                for entity_type, expected_list in self.expected_entities.items():
                    detected_list = detected.get(entity_type, [])
                    for expected in expected_list:
                        if any(
                            expected.lower() in det.lower()
                            or det.lower() in expected.lower()
                            for det in detected_list
                        ):
                            correct += 1

                precision = correct / total_detected if total_detected > 0 else 0
                recall = correct / total_expected if total_expected > 0 else 0
                f1 = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0
                    else 0
                )

                results["gliner"] = {
                    "status": "success",
                    "detected_entities": detected,
                    "total_detected": total_detected,
                    "total_expected": total_expected,
                    "correct_matches": correct,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1,
                }

                print(
                    f"GLiNER accuracy: Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}"
                )

            except Exception as e:
                results["gliner"] = {"status": "error", "error": str(e)}

        # Test DataFog regex accuracy for comparison
        if DATAFOG_AVAILABLE:
            try:
                detected = detect(self.test_text)

                total_detected = sum(len(v) for v in detected.values())
                total_expected = sum(len(v) for v in self.expected_entities.values())

                correct = 0
                for entity_type, expected_list in self.expected_entities.items():
                    detected_list = detected.get(entity_type, [])
                    for expected in expected_list:
                        if any(
                            expected.lower() in det.lower()
                            or det.lower() in expected.lower()
                            for det in detected_list
                        ):
                            correct += 1

                precision = correct / total_detected if total_detected > 0 else 0
                recall = correct / total_expected if total_expected > 0 else 0
                f1 = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0
                    else 0
                )

                results["regex"] = {
                    "status": "success",
                    "detected_entities": detected,
                    "total_detected": total_detected,
                    "total_expected": total_expected,
                    "correct_matches": correct,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1,
                }

                print(
                    f"Regex accuracy: Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}"
                )

            except Exception as e:
                results["regex"] = {"status": "error", "error": str(e)}

        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive research report"""
        print("\n=== Generating Comprehensive Report ===")

        # Run all tasks
        task1_results = self.task_1_basic_functionality()
        task2_results = self.task_2_performance_benchmarking()
        task3_results = self.task_3_entity_mapping()
        task4_results = self.task_4_model_comparison()
        task5_results = self.task_5_accuracy_testing()

        # Compile results
        self.results.update(
            {
                "task1_basic_functionality": task1_results,
                "task2_performance_benchmarking": task2_results,
                "task3_entity_mapping": task3_results,
                "task4_model_comparison": task4_results,
                "task5_accuracy_testing": task5_results,
            }
        )

        # Generate recommendations
        recommendations = self._generate_recommendations()
        self.results["recommendations"] = recommendations

        return self.results

    def _generate_recommendations(self) -> Dict[str, Any]:
        """Generate integration recommendations based on research results"""

        recommendations = {
            "integration_feasibility": "unknown",
            "performance_position": "unknown",
            "recommended_model": "unknown",
            "cascade_position": "unknown",
            "use_cases": [],
            "risks": [],
            "next_steps": [],
        }

        # Analyze performance results
        if "task2_performance_benchmarking" in self.results:
            perf = self.results["task2_performance_benchmarking"]

            if perf.get("gliner", {}).get("status") == "success":
                gliner_time = perf["gliner"]["avg_time_ms"]

                if perf.get("regex", {}).get("status") == "success":
                    regex_time = perf["regex"]["avg_time_ms"]
                    if (
                        gliner_time > regex_time * 10
                    ):  # If GLiNER is >10x slower than regex
                        recommendations["performance_position"] = (
                            "slower_than_regex_significant"
                        )
                    elif (
                        gliner_time > regex_time * 2
                    ):  # If GLiNER is >2x slower than regex
                        recommendations["performance_position"] = (
                            "slower_than_regex_moderate"
                        )
                    else:
                        recommendations["performance_position"] = "comparable_to_regex"

                if perf.get("spacy", {}).get("status") == "success":
                    spacy_time = perf["spacy"]["avg_time_ms"]
                    if (
                        gliner_time < spacy_time * 0.5
                    ):  # If GLiNER is >2x faster than spaCy
                        recommendations["performance_position"] += "_faster_than_spacy"
                    elif gliner_time < spacy_time:  # If GLiNER is faster than spaCy
                        recommendations[
                            "performance_position"
                        ] += "_moderately_faster_than_spacy"
                    else:
                        recommendations["performance_position"] += "_slower_than_spacy"

        # Determine integration feasibility
        if (
            GLINER_AVAILABLE
            and self.results.get("task1_basic_functionality", {}).get("status")
            == "success"
        ):
            recommendations["integration_feasibility"] = "feasible"
        else:
            recommendations["integration_feasibility"] = "not_feasible"
            recommendations["risks"].append(
                "GLiNER dependencies not available or basic functionality failed"
            )

        # Recommend model based on performance
        if "task4_model_comparison" in self.results:
            model_results = self.results["task4_model_comparison"]
            best_model = None
            best_score = float("inf")

            for model_name, result in model_results.items():
                if result.get("status") == "success":
                    # Score based on speed (lower is better)
                    score = result["process_time_ms"]
                    if score < best_score:
                        best_score = score
                        best_model = model_name

            recommendations["recommended_model"] = best_model or "gliner_base"

        # Suggest cascade position
        perf_pos = recommendations["performance_position"]
        if "slower_than_regex_significant" in perf_pos:
            recommendations["cascade_position"] = (
                "after_spacy"  # Too slow for middle position
            )
            recommendations["use_cases"] = ["batch_processing", "offline_analysis"]
        elif (
            "slower_than_regex_moderate" in perf_pos and "faster_than_spacy" in perf_pos
        ):
            recommendations["cascade_position"] = "between_regex_and_spacy"
            recommendations["use_cases"] = [
                "contextual_entity_detection",
                "medium_throughput_scenarios",
            ]
        else:
            recommendations["cascade_position"] = "needs_further_analysis"

        # Add specific recommendations
        recommendations["next_steps"] = [
            "Validate GLiNER performance with larger datasets",
            "Test memory usage under sustained load",
            "Implement prototype integration in TextService",
            "Define entity type mapping strategy",
            "Plan dependency management approach",
        ]

        return recommendations

    def save_report(self, filename: str = None) -> str:
        """Save research report to file"""
        if filename is None:
            filename = f"gliner_research_report_{int(time.time())}.json"

        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\nReport saved to: {filepath}")
        return filepath


def main():
    """Main research execution"""
    print("GLiNER Research for DataFog Integration")
    print("=" * 50)

    if not GLINER_AVAILABLE:
        print("ERROR: GLiNER not available. Please install with:")
        print("pip install gliner torch transformers")
        sys.exit(1)

    researcher = GLiNERResearcher()

    try:
        # Generate comprehensive report
        results = researcher.generate_report()

        # Save to file
        report_file = researcher.save_report()

        # Print summary
        print("\n" + "=" * 50)
        print("RESEARCH SUMMARY")
        print("=" * 50)

        recommendations = results.get("recommendations", {})
        print(
            f"Integration Feasibility: {recommendations.get('integration_feasibility', 'unknown')}"
        )
        print(
            f"Performance Position: {recommendations.get('performance_position', 'unknown')}"
        )
        print(
            f"Recommended Model: {recommendations.get('recommended_model', 'unknown')}"
        )
        print(f"Cascade Position: {recommendations.get('cascade_position', 'unknown')}")

        if recommendations.get("use_cases"):
            print(f"Recommended Use Cases: {', '.join(recommendations['use_cases'])}")

        if recommendations.get("risks"):
            print("Identified Risks:")
            for risk in recommendations["risks"]:
                print(f"  - {risk}")

        print(f"\nFull report available at: {report_file}")

    except Exception as e:
        print(f"Research failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
