import os
import sys
import tempfile
import unittest

# Add root directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend import storage

class TestArticlesStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_integral.db")
        storage.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_legacy_sources_migration(self):
        # Create a source directly in DB before migration
        with storage.get_connection(self.db_path) as conn:
            conn.execute("INSERT INTO sources (url, created_at) VALUES (?, ?)", ("https://legacy-item.com", "2026-01-01T00:00:00"))
            conn.commit()

        # Re-run init_db to trigger migration
        storage.init_db(self.db_path)

        articles = storage.get_all_articles(self.db_path)
        legacy = next((a for a in articles if a["title"] == "Legacy Sources"), None)
        self.assertIsNotNone(legacy, "Legacy Sources article should have been created")
        self.assertEqual(legacy["source_count"], 1)

        sources = storage.get_sources_for_article(legacy["id"], self.db_path)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["url"], "https://legacy-item.com")

    def test_create_and_get_articles(self):
        art1 = storage.create_article("Tech Policy 2026", self.db_path)
        self.assertEqual(art1["title"], "Tech Policy 2026")
        self.assertIn("id", art1)
        self.assertEqual(art1["source_count"], 0)

        art2 = storage.create_article("Market Trends", self.db_path)
        self.assertEqual(art2["title"], "Market Trends")

        all_articles = storage.get_all_articles(self.db_path)
        self.assertTrue(len(all_articles) >= 2)
        titles = [a["title"] for a in all_articles]
        self.assertIn("Tech Policy 2026", titles)
        self.assertIn("Market Trends", titles)

        fetched = storage.get_article(art1["id"], self.db_path)
        self.assertEqual(fetched["id"], art1["id"])
        self.assertEqual(fetched["title"], "Tech Policy 2026")

    def test_link_source_and_many_to_many(self):
        art1 = storage.create_article("Article One", self.db_path)
        art2 = storage.create_article("Article Two", self.db_path)

        # Save snapshot for url
        url1 = "https://example.com/shared-source"
        storage.save_snapshot(url1, "Shared content text", trigger="manual", db_path=self.db_path)

        # Link to art1
        link1 = storage.link_source_to_article(art1["id"], url1, self.db_path)
        self.assertEqual(link1["article_id"], art1["id"])

        # Link same source to art2
        link2 = storage.link_source_to_article(art2["id"], url1, self.db_path)
        self.assertEqual(link2["article_id"], art2["id"])
        self.assertEqual(link1["source_id"], link2["source_id"], "Should reference same underlying source_id")

        # Duplicate link should be idempotent
        link1_dup = storage.link_source_to_article(art1["id"], url1, self.db_path)
        self.assertEqual(link1_dup["source_id"], link1["source_id"])

        sources_art1 = storage.get_sources_for_article(art1["id"], self.db_path)
        sources_art2 = storage.get_sources_for_article(art2["id"], self.db_path)
        self.assertEqual(len(sources_art1), 1)
        self.assertEqual(len(sources_art2), 1)
        self.assertEqual(sources_art1[0]["url"], url1)
        self.assertEqual(sources_art2[0]["url"], url1)
        self.assertEqual(sources_art1[0]["status"], "initial")
        self.assertEqual(sources_art1[0]["snapshot_count"], 1)

    def test_unlink_source_non_destructive(self):
        art1 = storage.create_article("Project Alpha", self.db_path)
        art2 = storage.create_article("Project Beta", self.db_path)

        url = "https://example.com/common"
        storage.save_snapshot(url, "Initial snapshot text", trigger="manual", db_path=self.db_path)

        storage.link_source_to_article(art1["id"], url, self.db_path)
        storage.link_source_to_article(art2["id"], url, self.db_path)

        sources_art1 = storage.get_sources_for_article(art1["id"], self.db_path)
        source_id = sources_art1[0]["id"]

        # Unlink from art1
        unlinked = storage.unlink_source_from_article(art1["id"], source_id, self.db_path)
        self.assertTrue(unlinked)

        # Confirm removed from art1
        sources_art1_after = storage.get_sources_for_article(art1["id"], self.db_path)
        self.assertEqual(len(sources_art1_after), 0)

        # Confirm still present in art2
        sources_art2 = storage.get_sources_for_article(art2["id"], self.db_path)
        self.assertEqual(len(sources_art2), 1)
        self.assertEqual(sources_art2[0]["id"], source_id)

        # Confirm underlying source and snapshot history still exist globally
        all_sources = storage.get_all_sources(self.db_path)
        self.assertTrue(any(s["id"] == source_id for s in all_sources))
        history = storage.get_snapshot_history(url, self.db_path)
        self.assertEqual(len(history), 1)

    def test_error_handling(self):
        with self.assertRaises(ValueError):
            storage.create_article("   ", self.db_path)

        with self.assertRaises(ValueError):
            storage.link_source_to_article(9999, "https://example.com", self.db_path)

        with self.assertRaises(ValueError):
            storage.get_sources_for_article(9999, self.db_path)

        # Unlinking non-existent link returns False
        unlinked = storage.unlink_source_from_article(9999, 9999, self.db_path)
        self.assertFalse(unlinked)

if __name__ == "__main__":
    unittest.main()
