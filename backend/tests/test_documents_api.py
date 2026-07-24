import time


def test_upload_creates_completed_job(client):
    response = client.post(
        "/api/upload",
        files={"files": ("test.txt", b"Refund policy: 30 days.", "text/plain")},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = None
    for _ in range(50):
        status = client.get(f"/api/upload/{job_id}").json()
        if status["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert status is not None
    assert status["status"] == "completed"
    assert status["added"] == 1
    assert status["skipped"] == 0


def test_upload_csv_with_utf8_characters(client):
    # CSV content with >4096 bytes of pure ASCII first, then non-ASCII characters to trigger ASCII auto-detect failure in MarkItDown
    header = "question,answer\n"
    padding = "a,b\n" * 1500  # 1500 * 4 = 6000 bytes
    non_ascii_line = "Is this a smart quote?,Yes it’s a smart quote.\nAccented?,élégant\n"
    csv_content = header + padding + non_ascii_line
    
    response = client.post(
        "/api/upload",
        files={"files": ("test_utf8.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status = None
    for _ in range(50):
        status = client.get(f"/api/upload/{job_id}").json()
        if status["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert status is not None
    print("\nDEBUG STATUS:", status)
    assert status["status"] == "completed"
    assert status["added"] == 1
    assert status["skipped"] == 0


