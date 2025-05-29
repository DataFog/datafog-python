#!/usr/bin/env python3
"""
Final GLiNER Analysis with proper DataFog comparison
"""

import json
import os
import time

# Check dependencies
try:
    from gliner import GLiNER

    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False

try:
    from datafog import detect

    DATAFOG_AVAILABLE = True
except ImportError:
    DATAFOG_AVAILABLE = False


def comprehensive_analysis():
    """Comprehensive GLiNER vs DataFog analysis"""

    # Test data - same as DataFog benchmarks for fair comparison
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
    Phone: +1 (800) 555-0199
    Email: billing@medcorp.com
    Website: https://www.medcorp.com
    
    IP Address for reference: 192.168.1.100
    Server Log: user_id=12345 logged in from 10.0.0.1 at 2024-03-15T14:30:00Z
    """

    text_size_kb = len(test_text.encode("utf-8")) / 1024

    results = {
        "environment": {
            "gliner_available": GLINER_AVAILABLE,
            "datafog_available": DATAFOG_AVAILABLE,
            "test_text_size_kb": text_size_kb,
        },
        "gliner": {"status": "skipped"},
        "datafog_regex": {"status": "skipped"},
        "comparison": {},
        "entity_analysis": {},
        "recommendations": {},
    }

    print("=== Comprehensive GLiNER vs DataFog Analysis ===")
    print(f"Test text size: {text_size_kb:.2f} KB")

    # GLiNER Analysis
    if GLINER_AVAILABLE:
        try:
            print("\n--- GLiNER Analysis ---")

            # Load model (measure load time)
            print("Loading GLiNER base model...")
            start_load = time.perf_counter()
            model = GLiNER.from_pretrained("urchade/gliner_base")
            load_time = time.perf_counter() - start_load
            print(f"Model loaded in {load_time:.1f} seconds")

            # GLiNER labels
            labels = [
                "person",
                "email address",
                "phone number",
                "social security number",
                "credit card number",
                "ip address",
                "date",
                "time",
                "organization",
                "website",
                "url",
                "address",
                "location",
            ]

            # Warmup
            model.predict_entities(test_text[:100], labels[:3], threshold=0.5)

            # Performance measurement
            times = []
            for i in range(5):
                start = time.perf_counter()
                entities = model.predict_entities(test_text, labels, threshold=0.4)
                end = time.perf_counter()
                times.append(end - start)

            avg_time = sum(times) / len(times)
            throughput = text_size_kb / avg_time

            print("GLiNER Performance:")
            print(f"  Average time: {avg_time*1000:.1f}ms")
            print(f"  Throughput: {throughput:.1f} KB/s")
            print(f"  Entities found: {len(entities)}")

            # Show some entities
            print("Sample entities:")
            for ent in entities[:8]:
                print(
                    f"  {ent['label']}: '{ent['text']}' (conf: {ent.get('score', 0):.3f})"
                )

            results["gliner"] = {
                "status": "success",
                "model_load_time_s": load_time,
                "avg_processing_time_ms": avg_time * 1000,
                "throughput_kb_per_s": throughput,
                "entities_found": len(entities),
                "entities_detail": entities,
                "individual_times_ms": [t * 1000 for t in times],
            }

        except Exception as e:
            print(f"GLiNER error: {e}")
            results["gliner"] = {"status": "error", "error": str(e)}

    # DataFog Regex Analysis
    if DATAFOG_AVAILABLE:
        try:
            print("\n--- DataFog Regex Analysis ---")

            # Warmup
            detect(test_text[:100])

            # Performance measurement
            times = []
            for i in range(5):
                start = time.perf_counter()
                entities = detect(test_text)
                end = time.perf_counter()
                times.append(end - start)

            avg_time = sum(times) / len(times)
            throughput = text_size_kb / avg_time
            total_entities = sum(len(v) for v in entities.values())

            print("DataFog Regex Performance:")
            print(f"  Average time: {avg_time*1000:.1f}ms")
            print(f"  Throughput: {throughput:.1f} KB/s")
            print(f"  Entities found: {total_entities}")

            # Show entities by type
            print("Entities by type:")
            for entity_type, entity_list in entities.items():
                if entity_list:
                    print(f"  {entity_type}: {entity_list}")

            results["datafog_regex"] = {
                "status": "success",
                "avg_processing_time_ms": avg_time * 1000,
                "throughput_kb_per_s": throughput,
                "entities_found": total_entities,
                "entities_by_type": entities,
                "individual_times_ms": [t * 1000 for t in times],
            }

        except Exception as e:
            print(f"DataFog error: {e}")
            results["datafog_regex"] = {"status": "error", "error": str(e)}

    # Performance Comparison
    if (
        results["gliner"]["status"] == "success"
        and results["datafog_regex"]["status"] == "success"
    ):

        print("\n--- Performance Comparison ---")

        gliner_time = results["gliner"]["avg_processing_time_ms"]
        regex_time = results["datafog_regex"]["avg_processing_time_ms"]

        speed_ratio = gliner_time / regex_time
        regex_advantage = regex_time / gliner_time

        gliner_throughput = results["gliner"]["throughput_kb_per_s"]
        regex_throughput = results["datafog_regex"]["throughput_kb_per_s"]

        print("Speed Comparison:")
        print(f"  DataFog Regex: {regex_time:.1f}ms")
        print(f"  GLiNER: {gliner_time:.1f}ms")
        print(f"  Regex is {1/regex_advantage:.1f}x faster than GLiNER")
        print(f"  GLiNER is {speed_ratio:.1f}x slower than Regex")

        print("Throughput Comparison:")
        print(f"  DataFog Regex: {regex_throughput:.1f} KB/s")
        print(f"  GLiNER: {gliner_throughput:.1f} KB/s")

        results["comparison"] = {
            "gliner_vs_regex_ratio": speed_ratio,
            "regex_advantage": 1 / regex_advantage,
            "gliner_time_ms": gliner_time,
            "regex_time_ms": regex_time,
            "gliner_throughput": gliner_throughput,
            "regex_throughput": regex_throughput,
            "throughput_ratio": regex_throughput / gliner_throughput,
        }

    # Entity Analysis
    if results["gliner"]["status"] == "success":
        try:
            print("\n--- Entity Type Mapping Analysis ---")

            gliner_entities = results["gliner"]["entities_detail"]

            # Mapping from GLiNER to DataFog format
            mapping = {
                "person": "PERSON",
                "email address": "EMAIL",
                "phone number": "PHONE",
                "social security number": "SSN",
                "credit card number": "CREDIT_CARD",
                "ip address": "IP_ADDRESS",
                "date": "DATE",
                "time": "TIME",
                "organization": "ORG",
                "website": "URL",
                "url": "URL",
                "address": "ADDRESS",
                "location": "LOCATION",
            }

            mapped_entities = {}
            unmapped_entities = []

            for entity in gliner_entities:
                label = entity["label"].lower()
                datafog_type = mapping.get(label)

                if datafog_type:
                    if datafog_type not in mapped_entities:
                        mapped_entities[datafog_type] = []
                    mapped_entities[datafog_type].append(
                        {
                            "text": entity["text"],
                            "confidence": entity.get("score", 0),
                            "start": entity.get("start", 0),
                            "end": entity.get("end", 0),
                        }
                    )
                else:
                    unmapped_entities.append(entity)

            print("GLiNER entities mapped to DataFog types:")
            for datafog_type, entities_list in mapped_entities.items():
                print(f"  {datafog_type}: {len(entities_list)} entities")
                for ent in entities_list[:2]:  # Show first 2
                    print(f"    '{ent['text']}' (confidence: {ent['confidence']:.3f})")

            if unmapped_entities:
                print(f"Unmapped entities: {len(unmapped_entities)}")
                for ent in unmapped_entities[:3]:
                    print(f"  {ent['label']}: '{ent['text']}'")

            results["entity_analysis"] = {
                "mapping_schema": mapping,
                "mapped_entities": mapped_entities,
                "unmapped_entities": unmapped_entities,
                "total_gliner_entities": len(gliner_entities),
                "mapped_count": sum(len(v) for v in mapped_entities.values()),
                "unmapped_count": len(unmapped_entities),
            }

        except Exception as e:
            print(f"Entity analysis error: {e}")

    # Generate Recommendations
    print("\n--- Integration Recommendations ---")

    recommendations = {
        "integration_feasibility": "unknown",
        "performance_assessment": "unknown",
        "cascade_position": "unknown",
        "use_cases": [],
        "risks": [],
        "benefits": [],
        "next_steps": [],
    }

    if results["gliner"]["status"] == "success":
        recommendations["integration_feasibility"] = "feasible"

        load_time = results["gliner"]["model_load_time_s"]
        process_time = results["gliner"]["avg_processing_time_ms"]

        if "comparison" in results:
            ratio = results["comparison"]["gliner_vs_regex_ratio"]

            if ratio > 50:  # Much slower
                recommendations["performance_assessment"] = "much_slower_than_regex"
                recommendations["cascade_position"] = "after_spacy"
                recommendations["use_cases"] = [
                    "batch_processing",
                    "offline_analysis",
                    "comprehensive_entity_detection",
                ]
                recommendations["risks"].append("Too slow for real-time applications")
            elif ratio > 10:  # Moderately slower
                recommendations["performance_assessment"] = (
                    "moderately_slower_than_regex"
                )
                recommendations["cascade_position"] = "between_regex_and_spacy"
                recommendations["use_cases"] = [
                    "contextual_entities",
                    "medium_throughput",
                    "hybrid_approach",
                ]
                recommendations["risks"].append(
                    "Performance impact for high-throughput scenarios"
                )
            else:  # Comparable
                recommendations["performance_assessment"] = "comparable_to_regex"
                recommendations["cascade_position"] = "alternative_to_spacy"
                recommendations["use_cases"] = [
                    "real_time_processing",
                    "contextual_entities",
                    "modern_nlp",
                ]

        if load_time > 10:
            recommendations["risks"].append("Long model loading time impacts startup")

        if process_time > 500:
            recommendations["risks"].append(
                "Processing time too slow for interactive use"
            )

        # Benefits
        if results["gliner"]["entities_found"] > 0:
            recommendations["benefits"].append(
                "Detects contextual entities regex cannot find"
            )
            recommendations["benefits"].append("No need for predefined patterns")
            recommendations["benefits"].append("Modern transformer-based approach")
            recommendations["benefits"].append("Flexible entity type definition")

        # Next steps
        recommendations["next_steps"] = [
            "Test with DataFog production datasets",
            "Implement lazy loading for model initialization",
            "Design caching strategy for repeated use",
            "Evaluate memory usage patterns",
            "Plan integration with existing TextService architecture",
        ]
    else:
        recommendations["integration_feasibility"] = "not_feasible"
        recommendations["risks"].append("GLiNER dependencies or functionality issues")

    results["recommendations"] = recommendations

    # Print summary
    print("\n" + "=" * 60)
    print("FINAL RECOMMENDATIONS")
    print("=" * 60)

    print(f"Integration Feasibility: {recommendations['integration_feasibility']}")
    print(f"Performance Assessment: {recommendations['performance_assessment']}")
    print(f"Recommended Cascade Position: {recommendations['cascade_position']}")

    if recommendations["use_cases"]:
        print(f"Recommended Use Cases: {', '.join(recommendations['use_cases'])}")

    if recommendations["benefits"]:
        print("Key Benefits:")
        for benefit in recommendations["benefits"]:
            print(f"  + {benefit}")

    if recommendations["risks"]:
        print("Key Risks:")
        for risk in recommendations["risks"]:
            print(f"  - {risk}")

    return results


def main():
    """Main execution"""
    print("GLiNER Final Analysis for DataFog v4.2.0 Integration")
    print("=" * 60)

    if not GLINER_AVAILABLE:
        print(
            "ERROR: GLiNER not available. Install with: pip install gliner torch transformers"
        )
        return

    if not DATAFOG_AVAILABLE:
        print("WARNING: DataFog not available for comparison")

    results = comprehensive_analysis()

    # Save results
    timestamp = int(time.time())
    filename = f"gliner_final_analysis_{timestamp}.json"
    filepath = os.path.join(os.path.dirname(__file__), filename)

    with open(filepath, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDetailed analysis saved to: {filepath}")

    return results


if __name__ == "__main__":
    main()
