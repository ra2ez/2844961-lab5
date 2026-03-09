
import subprocess
import sys
import time
import json
import re
import socket
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

EXPECTED_PORT = 3000
BASE_URL = f"http://127.0.0.1:{EXPECTED_PORT}"

def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def pass_line(msg):
    print(f"[PASS] {msg}")

def fail_line(msg):
    print(f"[FAIL] {msg}")

def info_line(msg):
    print(f"[INFO] {msg}")

def http_request(method, path, body=None):
    url = BASE_URL + path
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except Exception:
                parsed = raw
            return {
                "ok": True,
                "status": status,
                "body": parsed,
                "raw": raw,
                "content_type": content_type,
            }
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        content_type = e.headers.get("Content-Type", "")
        try:
            parsed = json.loads(raw) if raw.strip() else None
        except Exception:
            parsed = raw
        return {
            "ok": False,
            "status": e.code,
            "body": parsed,
            "raw": raw,
            "content_type": content_type,
        }
    except URLError as e:
        return {
            "ok": False,
            "status": None,
            "body": None,
            "raw": str(e),
            "content_type": "",
        }

def port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def wait_for_server(port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if port_open("127.0.0.1", port):
            return True
        time.sleep(0.2)
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python lab5_tester.py <student-number-lab5.js>")
        sys.exit(1)

    js_path = Path(sys.argv[1]).resolve()

    if not js_path.exists():
        print(f"File not found: {js_path}")
        sys.exit(1)

    all_passed = True
    content = js_path.read_text(encoding="utf-8", errors="ignore")
    filename = js_path.name

    print_section("STATIC CHECKS")

    filename_ok = bool(re.fullmatch(r"\d+-lab5\.js", filename))
    if filename_ok:
        pass_line(f"Filename looks correct: {filename}")
    else:
        fail_line(f"Filename must match <student-id>-lab5.js, got: {filename}")
        all_passed = False

    student_id = filename.split("-lab5.js")[0] if filename_ok else None

    local_import_patterns = [
        r"require\(\s*['\"]\./",
        r"require\(\s*['\"]\.\./",
        r"from\s+['\"]\./",
        r"from\s+['\"]\.\./",
        r"import\s+.*from\s+['\"]\./",
        r"import\s+.*from\s+['\"]\.\./",
    ]
    local_import_found = any(re.search(p, content) for p in local_import_patterns)
    if local_import_found:
        fail_line("Found local file imports/requires. Spec says all code must be in one file.")
        all_passed = False
    else:
        pass_line("No local file imports/requires found.")

    if "3000" in content:
        pass_line("File contains 3000 somewhere (good sign for required port).")
    else:
        fail_line("Could not find 3000 in file. Port must be 3000.")
        all_passed = False

    print_section("STARTING SERVER")

    proc = subprocess.Popen(
        ["node", str(js_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        if wait_for_server(EXPECTED_PORT, timeout=10):
            pass_line("Server started and is listening on port 3000.")
        else:
            fail_line("Server did not start on port 3000 within 10 seconds.")
            all_passed = False
            try:
                out, err = proc.communicate(timeout=1)
            except Exception:
                out, err = "", ""
            if out.strip():
                info_line("STDOUT:")
                print(out)
            if err.strip():
                info_line("STDERR:")
                print(err)
            raise SystemExit(1)

        print_section("API TESTS")

        # GET /whoami
        r = http_request("GET", "/whoami")
        expected_whoami = {"studentNumber": student_id} if student_id else None
        if r["status"] == 200 and isinstance(r["body"], dict) and r["body"] == expected_whoami:
            pass_line("GET /whoami returns exactly the correct JSON and student number matches filename.")
        else:
            fail_line(f"GET /whoami incorrect. Expected {expected_whoami}, got status={r['status']} body={r['body']}")
            all_passed = False

        if "application/json" in r["content_type"].lower():
            pass_line("GET /whoami returns application/json.")
        else:
            fail_line(f"GET /whoami content-type should include application/json, got: {r['content_type']}")
            all_passed = False

        # GET /books initially
        r = http_request("GET", "/books")
        if r["status"] == 200 and r["body"] == []:
            pass_line("GET /books returns empty array initially.")
        else:
            fail_line(f"GET /books should return [] initially. Got status={r['status']} body={r['body']}")
            all_passed = False

        if "application/json" in r["content_type"].lower():
            pass_line("GET /books returns application/json.")
        else:
            fail_line(f"GET /books content-type should include application/json, got: {r['content_type']}")
            all_passed = False

        # GET non-existent book
        r = http_request("GET", "/books/999")
        if r["status"] == 404 and r["body"] == {"error": "Book not found"}:
            pass_line("GET /books/:id returns correct 404 JSON for missing book.")
        else:
            fail_line(f"GET /books/999 incorrect. Expected 404 {{'error':'Book not found'}}, got status={r['status']} body={r['body']}")
            all_passed = False

        # POST /books missing fields
        r = http_request("POST", "/books", {"title": "Missing ID"})
        if r["status"] == 400 and r["body"] == {"error": "Missing required fields"}:
            pass_line("POST /books with missing fields returns correct 400 JSON.")
        else:
            fail_line(f"POST /books missing fields incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # POST /books create
        book_payload = {
            "id": "1",
            "title": "1984",
            "details": [
                {
                    "id": "1",
                    "author": "George Orwell",
                    "genre": "Dystopian",
                    "publicationYear": 1949
                }
            ]
        }
        r = http_request("POST", "/books", book_payload)
        if r["status"] == 201 and isinstance(r["body"], dict) and r["body"].get("id") == "1" and r["body"].get("title") == "1984":
            pass_line("POST /books creates a book and returns 201.")
        else:
            fail_line(f"POST /books incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # GET created book
        r = http_request("GET", "/books/1")
        if r["status"] == 200 and isinstance(r["body"], dict) and r["body"].get("id") == "1" and r["body"].get("title") == "1984":
            pass_line("GET /books/:id returns created book.")
        else:
            fail_line(f"GET /books/1 incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # PUT missing book
        r = http_request("PUT", "/books/999", {"title": "Updated"})
        if r["status"] == 404 and r["body"] == {"error": "Book not found"}:
            pass_line("PUT /books/:id returns correct 404 JSON for missing book.")
        else:
            fail_line(f"PUT /books/999 incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # PUT missing title
        r = http_request("PUT", "/books/1", {})
        if r["status"] == 400 and r["body"] == {"error": "Missing required fields"}:
            pass_line("PUT /books/:id with missing title returns correct 400 JSON.")
        else:
            fail_line(f"PUT /books/1 missing title incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # PUT update
        r = http_request("PUT", "/books/1", {"title": "Updated Title"})
        if r["status"] == 200 and isinstance(r["body"], dict) and r["body"].get("title") == "Updated Title":
            pass_line("PUT /books/:id updates book.")
        else:
            fail_line(f"PUT /books/1 incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # POST detail to missing book
        detail_payload = {
            "id": "2",
            "author": "Another Author",
            "genre": "Mystery",
            "publicationYear": 2020
        }
        r = http_request("POST", "/books/999/details", detail_payload)
        if r["status"] == 404 and r["body"] == {"error": "Book not found"}:
            pass_line("POST /books/:id/details returns correct 404 JSON for missing book.")
        else:
            fail_line(f"POST /books/999/details incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # POST detail
        r = http_request("POST", "/books/1/details", detail_payload)
        body = r["body"]
        details_ok = (
            r["status"] == 201 and isinstance(body, dict)
            and isinstance(body.get("details"), list)
            and any(d.get("id") == "2" for d in body["details"])
        )
        if details_ok:
            pass_line("POST /books/:id/details adds detail and returns 201.")
        else:
            fail_line(f"POST /books/1/details incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # DELETE detail missing
        r = http_request("DELETE", "/books/1/details/999")
        if r["status"] == 404 and r["body"] == {"error": "Book or detail not found"}:
            pass_line("DELETE /books/:id/details/:detailId returns correct 404 JSON for missing detail.")
        else:
            fail_line(f"DELETE /books/1/details/999 incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # DELETE detail existing
        r = http_request("DELETE", "/books/1/details/2")
        if r["status"] in (200, 204):
            pass_line("DELETE /books/:id/details/:detailId removes detail.")
        else:
            fail_line(f"DELETE /books/1/details/2 should return 200 or 204. Got status={r['status']} body={r['body']}")
            all_passed = False

        # DELETE missing book
        r = http_request("DELETE", "/books/999")
        if r["status"] == 404 and r["body"] == {"error": "Book not found"}:
            pass_line("DELETE /books/:id returns correct 404 JSON for missing book.")
        else:
            fail_line(f"DELETE /books/999 incorrect. Got status={r['status']} body={r['body']}")
            all_passed = False

        # DELETE existing book
        r = http_request("DELETE", "/books/1")
        if r["status"] in (200, 204):
            pass_line("DELETE /books/:id removes book.")
        else:
            fail_line(f"DELETE /books/1 should return 200 or 204. Got status={r['status']} body={r['body']}")
            all_passed = False

        # confirm removed
        r = http_request("GET", "/books/1")
        if r["status"] == 404:
            pass_line("Deleted book is no longer accessible.")
        else:
            fail_line(f"Deleted book still accessible. Got status={r['status']} body={r['body']}")
            all_passed = False

        print_section("SUMMARY")
        if all_passed:
            print("All checks passed.")
        else:
            print("Some checks failed. Fix the items marked [FAIL].")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    main()
