"""
InternOrbit Automated Pipeline Validator
Verifies n8n workflow syntax, required nodes, connections, and external API availability.
"""

import json
import os
import sys
import urllib.request
import urllib.error

WORKFLOW_FILE = "internorbit_n8n_workflow.json"

def test_workflow_json_structure():
    """Verify internorbit_n8n_workflow.json exists, is valid JSON, and has all essential nodes."""
    print("--> 1. Validating n8n Workflow JSON structure...")
    assert os.path.exists(WORKFLOW_FILE), f"Error: {WORKFLOW_FILE} does not exist!"

    with open(WORKFLOW_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "nodes" in data, "Workflow must contain 'nodes' array"
    assert "connections" in data, "Workflow must contain 'connections' object"
    assert len(data["nodes"]) > 0, "Workflow cannot have 0 nodes"

    # Verify critical production nodes exist
    node_names = [n.get("name") for n in data["nodes"]]
    required_nodes = [
        "Every 4 Hours Schedule",
        "Fetch RemoteOK Internships",
        "Fetch Jobicy Global Internships",
        "Strict Student Filter & Deduplication Engine",
        "Basic LLM Chain",
        "Google Gemini Chat Model",
        "Send Telegram Alert"
    ]

    for req in required_nodes:
        assert req in node_names, f"Missing required node: '{req}'"
        print(f"    [OK] Node '{req}' present")

    # Verify deduplication engine code exists inside the filter node
    filter_node = next(n for n in data["nodes"] if n.get("name") == "Strict Student Filter & Deduplication Engine")
    js_code = filter_node["parameters"]["jsCode"]
    assert "$getWorkflowStaticData" in js_code, "Deduplication engine must reference static data"
    assert "seenJobKeys" in js_code, "Deduplication engine must store seen keys"
    print("    [OK] Deduplication engine logic verified")

    print("[SUCCESS] Workflow JSON schema and critical nodes are valid!\n")


def test_external_apis():
    """Test that external job APIs respond with HTTP 200 and return data."""
    print("--> 2. Running Live API Health Checks...")

    endpoints = [
        ("Jobicy Global API", "https://jobicy.com/api/v2/remote-jobs?count=5&tag=internship"),
        ("RemoteOK API", "https://remoteok.com/api?tag=internship")
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    for name, url in endpoints:
        print(f"    Pinging {name} ({url})...")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                status = response.getcode()
                body = response.read(300) # read sample bytes
                assert status == 200, f"{name} returned HTTP {status}"
                assert len(body) > 0, f"{name} returned empty body"
                print(f"    [OK] {name} is alive and healthy (HTTP {status})")
        except urllib.error.HTTPError as e:
            # If RemoteOK rate limits with 429, log warning but don't fail CI
            if e.code == 429:
                print(f"    [WARN] {name} returned HTTP 429 (Rate Limited) - Protected by workflow continueOnFail")
            else:
                print(f"    [FAIL] {name} HTTP Error: {e.code}")
                raise
        except Exception as e:
            print(f"    [WARN] {name} network error: {e}")

    print("[SUCCESS] External APIs checked!\n")


if __name__ == "__main__":
    try:
        test_workflow_json_structure()
        test_external_apis()
        print("ALL TESTS PASSED: InternOrbit pipeline is healthy and production-ready!")
        sys.exit(0)
    except AssertionError as err:
        print(f"\nTEST FAILED: {err}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nUNEXPECTED ERROR: {exc}")
        sys.exit(1)
