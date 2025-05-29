#!/usr/bin/env python3
"""
Simplified GLiNER Research Script for DataFog Integration Analysis

Focused on key performance and compatibility metrics for v4.2.0 integration decisions.
"""

import json
import os
import time

# Check if GLiNER is available
try:
    from gliner import GLiNER

    GLINER_AVAILABLE = True
except ImportError:
    print(
        "GLiNER not available. Please install with: pip install gliner torch transformers"
    )
    GLINER_AVAILABLE = False

# DataFog imports for comparison
try:
    from datafog import detect

    DATAFOG_AVAILABLE = True
except ImportError:
    print("DataFog not available in current environment")
    DATAFOG_AVAILABLE = False


def quick_gliner_analysis():
    """Quick GLiNER performance and compatibility analysis"""

    # Test data - realistic PII content
    test_text = """
    Dear John Doe,
    
    Thank you for your inquiry. Please contact us at support@company.com or call (555) 123-4567.
    Your account number is 987654321 and your social security number 123-45-6789 is on file.
    Please verify your credit card 4532-1234-5678-9012 for payment processing.
    
    We have scheduled your appointment for March 15, 2024 at 2:30 PM.
    Dr. Sarah Wilson will be your primary physician.
    
    Best regards,
    Customer Service Team
    MedCorp Healthcare Solutions
    Email: billing@medcorp.com
    IP Address for reference: 192.168.1.100
    """

    # GLiNER labels for PII detection
    gliner_labels = [
        "person",
        "email address",
        "phone number",
        "social security number",
        "credit card number",
        "ip address",
        "date",
        "time",
        "organization",
        "doctor",
        "medical facility",
    ]

    results = {
        "environment": {
            "gliner_available": GLINER_AVAILABLE,
            "datafog_available": DATAFOG_AVAILABLE,
        },
        "performance": {},
        "entity_mapping": {},
        "recommendations": {},
    }

    if not GLINER_AVAILABLE:
        return results

    print("=== GLiNER Quick Analysis ===")

    # Test basic functionality and performance
    try:
        print("Loading GLiNER base model...")
        start_load = time.perf_counter()
        model = GLiNER.from_pretrained("urchade/gliner_base")
        load_time = time.perf_counter() - start_load

        print(f"Model loaded in {load_time:.1f} seconds")

        # Performance test
        print("Testing processing speed...")

        # Warmup
        model.predict_entities(test_text[:100], ["person"], threshold=0.5)

        # Measured runs
        times = []
        for i in range(3):  # Reduced from 5 for speed
            start = time.perf_counter()
            entities = model.predict_entities(test_text, gliner_labels, threshold=0.5)
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        text_size_kb = len(test_text.encode("utf-8")) / 1024
        throughput = text_size_kb / avg_time

        print("GLiNER Performance:")
        print(f"  Average time: {avg_time*1000:.1f}ms")
        print(f"  Throughput: {throughput:.1f} KB/s")
        print(f"  Entities found: {len(entities)}")

        # Entity mapping analysis
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
            "doctor": "PERSON",
        }

        mapped_entities = {}
        for entity in entities:
            datafog_type = gliner_to_datafog.get(entity["label"].lower())
            if datafog_type:
                if datafog_type not in mapped_entities:
                    mapped_entities[datafog_type] = []
                mapped_entities[datafog_type].append(
                    {"text": entity["text"], "confidence": entity.get("score", 0)}
                )

        print("\nEntity Mapping Results:")
        for datafog_type, entities_list in mapped_entities.items():
            print(f"  {datafog_type}: {len(entities_list)} entities")
            for ent in entities_list[:2]:  # Show first 2
                print(f"    '{ent['text']}' (confidence: {ent['confidence']:.3f})")

        results["performance"] = {
            "status": "success",
            "model_load_time_s": load_time,
            "avg_processing_time_ms": avg_time * 1000,
            "throughput_kb_per_s": throughput,
            "entities_found": len(entities),
            "text_size_kb": text_size_kb,
        }

        results["entity_mapping"] = {
            "status": "success",
            "mapping_schema": gliner_to_datafog,
            "mapped_entities": mapped_entities,
            "total_entities": len(entities),
            "mapped_count": sum(len(v) for v in mapped_entities.values()),
        }

    except Exception as e:
        print(f"GLiNER analysis error: {e}")
        results["performance"] = {"status": "error", "error": str(e)}
        results["entity_mapping"] = {"status": "error", "error": str(e)}

    # Compare with DataFog regex if available
    if DATAFOG_AVAILABLE:
        try:
            print("\n=== DataFog Regex Comparison ===")

            # Warmup
            detect(test_text[:100])

            # Measured runs
            times = []
            for i in range(3):
                start = time.perf_counter()
                regex_entities = detect(test_text)
                end = time.perf_counter()
                times.append(end - start)

            regex_avg_time = sum(times) / len(times)
            regex_throughput = text_size_kb / regex_avg_time
            regex_total = sum(len(v) for v in regex_entities.values())

            print("DataFog Regex Performance:")
            print(f"  Average time: {regex_avg_time*1000:.1f}ms")
            print(f"  Throughput: {regex_throughput:.1f} KB/s")
            print(f"  Entities found: {regex_total}")

            if results["performance"]["status"] == "success":
                gliner_time = results["performance"]["avg_processing_time_ms"]
                regex_time = regex_avg_time * 1000
                speed_ratio = gliner_time / regex_time

                print("\nPerformance Comparison:")
                print(f"  GLiNER is {speed_ratio:.1f}x slower than regex")
                print(f"  Regex is {1/speed_ratio:.1f}x faster than GLiNER")

                results["performance"]["comparison"] = {
                    "regex_avg_time_ms": regex_time,
                    "regex_throughput_kb_per_s": regex_throughput,
                    "regex_entities_found": regex_total,
                    "gliner_vs_regex_ratio": speed_ratio,
                }

        except Exception as e:
            print(f"DataFog comparison error: {e}")

    # Generate recommendations
    if results["performance"]["status"] == "success":
        gliner_time = results["performance"]["avg_processing_time_ms"]
        load_time = results["performance"]["model_load_time_s"]

        recommendations = {
            "integration_feasibility": "feasible",
            "performance_position": "unknown",
            "recommended_use_cases": [],
            "cascade_position": "unknown",
            "risks": [],
            "next_steps": [],
        }

        # Analyze performance position
        if "comparison" in results["performance"]:
            ratio = results["performance"]["comparison"]["gliner_vs_regex_ratio"]
            if ratio > 100:  # Much slower than regex
                recommendations["performance_position"] = "much_slower_than_regex"
                recommendations["cascade_position"] = "after_spacy"
                recommendations["recommended_use_cases"] = [
                    "batch_processing",
                    "offline_analysis",
                ]
                recommendations["risks"].append(
                    "Significant performance impact for real-time use"
                )
            elif ratio > 10:  # Moderately slower than regex
                recommendations["performance_position"] = "slower_than_regex"
                recommendations["cascade_position"] = "between_regex_and_spacy"
                recommendations["recommended_use_cases"] = [
                    "contextual_entity_detection",
                    "medium_throughput",
                ]
            else:
                recommendations["performance_position"] = "comparable_to_regex"
                recommendations["cascade_position"] = "near_regex"
                recommendations["recommended_use_cases"] = [
                    "real_time_processing",
                    "high_throughput",
                ]

        if load_time > 30:
            recommendations["risks"].append(
                "Long model loading time impacts startup performance"
            )

        if gliner_time > 1000:  # > 1 second
            recommendations["risks"].append(
                "Processing time too slow for real-time applications"
            )

        recommendations["next_steps"] = [
            "Test with larger documents to validate scalability",
            "Implement caching strategy for model loading",
            "Evaluate memory usage under sustained load",
            "Design entity type mapping strategy",
            "Plan optional dependency integration",
        ]

        results["recommendations"] = recommendations

    return results


def main():
    """Main execution"""
    print("GLiNER Quick Analysis for DataFog Integration")
    print("=" * 50)

    results = quick_gliner_analysis()

    # Save results
    timestamp = int(time.time())
    filename = f"gliner_analysis_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 50)
    print("ANALYSIS SUMMARY")
    print("=" * 50)

    if results["performance"].get("status") == "success":
        perf = results["performance"]
        print(f"Model Load Time: {perf['model_load_time_s']:.1f}s")
        print(f"Processing Time: {perf['avg_processing_time_ms']:.1f}ms")
        print(f"Throughput: {perf['throughput_kb_per_s']:.1f} KB/s")
        print(f"Entities Found: {perf['entities_found']}")

        if "comparison" in perf:
            ratio = perf["comparison"]["gliner_vs_regex_ratio"]
            print(f"Speed vs Regex: {ratio:.1f}x slower")

    if "recommendations" in results:
        rec = results["recommendations"]
        print(
            f"Integration Feasibility: {rec.get('integration_feasibility', 'unknown')}"
        )
        print(f"Performance Position: {rec.get('performance_position', 'unknown')}")
        print(f"Recommended Cascade Position: {rec.get('cascade_position', 'unknown')}")

        if rec.get("risks"):
            print("Key Risks:")
            for risk in rec["risks"]:
                print(f"  - {risk}")

    print(f"\nDetailed results saved to: {filepath}")
    return results


if __name__ == "__main__":
    main()
