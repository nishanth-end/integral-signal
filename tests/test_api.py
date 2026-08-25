import os
import sys
import tempfile
import unittest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import app
from backend import storage, snapshot

class TestArticlesAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_api.db")
        os.environ["INTEGRAL_SIGNAL_DB_PATH"] = self.db_path
        storage.init_db(self.db_path)
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()
        if "INTEGRAL_SIGNAL_DB_PATH" in os.environ:
            del os.environ["INTEGRAL_SIGNAL_DB_PATH"]

    def test_articles_endpoints_crud(self):
        # 1. Create Article
        res = self.client.post("/articles", json={"title": "Investigative Report"})
        self.assertEqual(res.status_code, 200)
        art = res.json()
        self.assertEqual(art["title"], "Investigative Report")
        article_id = art["id"]

        # 2. List Articles
        res = self.client.get("/articles")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["count"] >= 1)
        self.assertEqual(data["articles"][0]["title"], "Investigative Report")

        # 3. Get Article
        res = self.client.get(f"/articles/{article_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], article_id)

        # 4. Get Non-existent Article
        res = self.client.get("/articles/99999")
        self.assertEqual(res.status_code, 404)

    def test_article_sources_and_unlink(self):
        art_res = self.client.post("/articles", json={"title": "Climate Analysis"})
        art_id = art_res.json()["id"]

        # Mock snapshot fetch for testing
        orig_fetch = snapshot.fetch_content
        snapshot.fetch_content = lambda url, **kwargs: "Mock content for testing snapshot"
        try:
            # Add Source to Article
            res = self.client.post(f"/articles/{art_id}/sources", json={"url": "https://climate.gov/report"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["url"], "https://climate.gov/report")
            source_id = data["source_id"]

            # List Sources for Article
            res = self.client.get(f"/articles/{art_id}/sources")
            self.assertEqual(res.status_code, 200)
            sources_data = res.json()
            self.assertEqual(sources_data["count"], 1)
            self.assertEqual(sources_data["sources"][0]["id"], source_id)
            self.assertEqual(sources_data["sources"][0]["status"], "initial")

            # Unlink Source
            del_res = self.client.delete(f"/articles/{art_id}/sources/{source_id}")
            self.assertEqual(del_res.status_code, 200)

            # Verify unlinked
            res = self.client.get(f"/articles/{art_id}/sources")
            self.assertEqual(res.json()["count"], 0)

            # Unlink again returns 404
            del_res2 = self.client.delete(f"/articles/{art_id}/sources/{source_id}")
            self.assertEqual(del_res2.status_code, 404)

        finally:
            snapshot.fetch_content = orig_fetch

    def test_rename_and_delete_article_endpoints(self):
        art_res = self.client.post("/articles", json={"title": "Original Title"})
        art_id = art_res.json()["id"]

        # Rename
        patch_res = self.client.patch(f"/articles/{art_id}", json={"title": "Renamed Title"})
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["title"], "Renamed Title")

        # Rename invalid
        patch_inv = self.client.patch(f"/articles/{art_id}", json={"title": "   "})
        self.assertEqual(patch_inv.status_code, 400)

        # Delete article
        del_res = self.client.delete(f"/articles/{art_id}")
        self.assertEqual(del_res.status_code, 200)

        # Delete again 404
        del_res404 = self.client.delete(f"/articles/{art_id}")
        self.assertEqual(del_res404.status_code, 404)

    def test_delete_source_endpoint(self):
        orig_fetch = snapshot.fetch_content
        snapshot.fetch_content = lambda url, **kwargs: "Mock content"
        try:
            art = self.client.post("/articles", json={"title": "Container"}).json()
            add_res = self.client.post(f"/articles/{art['id']}/sources", json={"url": "https://delete-me.org"})
            source_id = add_res.json()["source_id"]

            # Permanently delete source
            del_res = self.client.delete(f"/sources/{source_id}")
            self.assertEqual(del_res.status_code, 200)

            # Check article sources is empty
            sources_res = self.client.get(f"/articles/{art['id']}/sources")
            self.assertEqual(sources_res.json()["count"], 0)

            # Delete again 404
            del_res404 = self.client.delete(f"/sources/{source_id}")
            self.assertEqual(del_res404.status_code, 404)
        finally:
            snapshot.fetch_content = orig_fetch

if __name__ == "__main__":
    unittest.main()
