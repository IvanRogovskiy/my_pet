import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets/examples"))
import mechanisms


class Mechanisms(unittest.TestCase):
    def test_conditional_update_uses_affected_rows(self):
        result = mechanisms.transactions()
        self.assertEqual(result["stale_read"], {"accepted":["A","B"],"remaining":0})
        self.assertEqual(result["conditional_write_rows"], [1,0])
        self.assertFalse(result["postgres_concurrency_verified"])

    def test_sibling_failure_waits_for_cleanup(self):
        result = asyncio.run(mechanisms.async_scope())
        self.assertEqual(result["events"], ["resource-open","resource-closed","scope-left"])
        self.assertTrue(result["value_error_observed"])
        self.assertTrue(result["timeout_cleanup"])
        self.assertEqual(result["live_children"], 0)

    def test_demo_does_not_leave_cancellation_on_its_caller(self):
        async def scenario():
            caller = asyncio.current_task()
            before = caller.cancelling()
            await mechanisms.async_scope()
            self.assertEqual(caller.cancelling(), before)
            await mechanisms.async_scope()
            self.assertEqual(caller.cancelling(), before)
        asyncio.run(scenario())

    def test_publish_before_mark_crash_delivers_twice_effect_once(self):
        result = mechanisms.outbox()
        self.assertEqual(result["pending_after_publish_crash"], 1)
        self.assertEqual(result["deliveries"], 2)
        self.assertEqual(result["effects"], (1,100))

    def test_old_client_reads_writes_after_expand_and_backfill_is_repeatable(self):
        result = mechanisms.release()
        self.assertEqual(result["rows_after_rollback_write"], [(1,250),(2,100),(3,150),(4,200)])
        self.assertTrue(result["select_star_tuple_broken"])
        self.assertEqual(result["backfill_changed"], 3)
        self.assertEqual(result["repeat_changed"], 0)

    def test_restore_marks_loss_and_does_not_invent_rpo(self):
        result = mechanisms.restore()
        self.assertEqual(result["restored"], [(1,250)])
        self.assertEqual(result["lost_post_backup_ids"], [2])
        self.assertIsNone(result["rpo_seconds"])


if __name__ == '__main__':
    unittest.main()
