import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8001/api"
HEADERS = {}


def login(username, password):
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    r = urllib.request.urlopen(req)
    result = json.loads(r.read())
    HEADERS["Authorization"] = f"Bearer {result['access_token']}"
    HEADERS["Content-Type"] = "application/json"
    print(f"[OK] Login as {username}")


def get(url):
    req = urllib.request.Request(f"{BASE_URL}{url}", headers=HEADERS)
    r = urllib.request.urlopen(req)
    return json.loads(r.read())


def post(url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE_URL}{url}", data=body, headers=HEADERS, method="POST")
    r = urllib.request.urlopen(req)
    return json.loads(r.read())


_mat_counter = 0

def create_material():
    global _mat_counter
    _mat_counter += 1
    data = {
        "code": f"MAT-TEST-{_mat_counter:03d}",
        "name": "测试试剂",
        "category": "reagent",
        "unit": "瓶",
        "specification": "500ml",
        "min_stock": 5
    }
    result = post("/admin/materials", data)
    print(f"[OK] Created material: id={result['id']}, name={result['name']}")
    return result["id"]


_inv_counter = 0

def create_inventory(material_id):
    global _inv_counter
    _inv_counter += 1
    from datetime import datetime, timedelta
    data = {
        "material_id": material_id,
        "batch_no": f"BATCH-2026-{_inv_counter:03d}",
        "quantity": 100,
        "original_expiry_date": (datetime.now() + timedelta(days=365)).isoformat(),
        "location": "A-01-01"
    }
    result = post("/inventory", data)
    print(f"[OK] Created inventory: id={result['id']}, qty={result['quantity']}")
    return result["id"]


def test_dashboard_stats():
    result = get("/dashboard/stats")
    print(f"[OK] Dashboard stats: ongoing={result['ongoing_stocktake_tasks']}, pending_review={result['pending_review_diffs']}")
    assert "ongoing_stocktake_tasks" in result
    assert "pending_review_diffs" in result


def test_create_stocktake_task(material_ids):
    data = {
        "title": "6月月度盘点",
        "description": "测试月度盘点任务",
        "material_ids": material_ids
    }
    result = post("/stocktake", data)
    print(f"[OK] Created stocktake task: id={result['id']}, no={result['task_no']}, status={result['status']}, items={len(result.get('items', []))}")
    assert result["status"] == "in_progress"
    assert len(result["items"]) > 0
    return result["id"], result["items"][0]["id"]


def test_list_stocktake_tasks():
    result = get("/stocktake")
    print(f"[OK] Stocktake task list: count={len(result)}")
    assert len(result) > 0


def test_get_stocktake_task(task_id):
    result = get(f"/stocktake/{task_id}")
    print(f"[OK] Stocktake task detail: id={result['id']}, status={result['status']}")
    for item in result["items"]:
        print(f"     - item {item['id']}: snapshot_qty={item['snapshot_quantity']}, current_qty={item['current_quantity']}, diff={item['diff_quantity']}")
    return result


def test_save_stocktake_items(task_id, item_id):
    data = {
        "item_ids": [item_id],
        "items": [{"actual_quantity": 95, "remark": "盘点时发现少了5瓶"}]
    }
    result = post(f"/stocktake/{task_id}/save", data)
    print(f"[OK] Saved stocktake items: status={result['status']}")
    for item in result["items"]:
        if item["id"] == item_id:
            print(f"     - item {item['id']}: actual_qty={item['actual_quantity']}, status={item['status']}, remark={item['remark']}")
            assert item["status"] == "saved"
            assert item["actual_quantity"] == 95
            assert item["diff_quantity"] == 95 - item["snapshot_quantity"]


def test_submit_stocktake_task(task_id):
    result = post(f"/stocktake/{task_id}/submit")
    print(f"[OK] Submitted stocktake task: status={result['status']}")
    assert result["status"] == "pending_review"
    for item in result["items"]:
        assert item["status"] == "submitted"


def test_confirm_stocktake_task(task_id, inv_id):
    inv_before = get(f"/inventory/{inv_id}")
    print(f"     - Before confirm: inventory qty={inv_before['quantity']}")

    result = post(f"/stocktake/{task_id}/confirm")
    print(f"[OK] Confirmed stocktake task: status={result['status']}")
    assert result["status"] == "confirmed"

    inv_after = get(f"/inventory/{inv_id}")
    print(f"     - After confirm: inventory qty={inv_after['quantity']}")
    assert inv_after["quantity"] == 95


def test_double_confirm(task_id):
    try:
        post(f"/stocktake/{task_id}/confirm")
        print("[FAIL] Double confirm should have failed")
        assert False
    except urllib.error.HTTPError as e:
        print(f"[OK] Double confirm correctly rejected: HTTP {e.code}")


def test_operations_with_task_filter(task_id):
    result = get(f"/operations?stocktake_task_id={task_id}")
    print(f"[OK] Operations filtered by task: count={len(result)}")
    for op in result:
        print(f"     - op {op['id']}: type={op['operation_type']}, change={op['quantity_change']}, task_id={op.get('stocktake_task_id')}")
        assert op["stocktake_task_id"] == task_id


def test_close_stocktake_task():
    mat_id2 = create_material()
    inv_id2 = create_inventory(mat_id2)
    task_id2, _ = test_create_stocktake_task([mat_id2])
    
    data = {"close_reason": "测试关闭任务"}
    result = post(f"/stocktake/{task_id2}/close", data)
    print(f"[OK] Closed stocktake task: status={result['status']}, reason={result['close_reason']}")
    assert result["status"] == "closed"


if __name__ == "__main__":
    import urllib.error
    try:
        print("=" * 60)
        print("Stocktake Module Integration Test")
        print("=" * 60)

        login("admin", "admin123")
        print()

        test_dashboard_stats()
        print()

        mat_id = create_material()
        inv_id = create_inventory(mat_id)
        print()

        task_id, item_id = test_create_stocktake_task([mat_id])
        test_list_stocktake_tasks()
        test_get_stocktake_task(task_id)
        print()

        test_save_stocktake_items(task_id, item_id)
        test_submit_stocktake_task(task_id)
        print()

        test_confirm_stocktake_task(task_id, inv_id)
        test_double_confirm(task_id)
        test_operations_with_task_filter(task_id)
        print()

        test_close_stocktake_task()
        print()

        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
