# tests/test_redis_utils.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import patch
import redis

import redis_utils

os.environ["REDIS_HOST"] = "test_host"
os.environ["REDIS_PORT"] = "1234"
os.environ["REDIS_DB"] = "5"

class TestRedisUtils(unittest.IsolatedAsyncioTestCase):
    """
    Tests for the redis_utils module.
    """

    def setUp(self):
        pass

    async def test_get_redis_dependency(self):
        """
        Tests if the get_redis dependency returns the global redis_client.
        """
        client = await redis_utils.get_redis()
        self.assertIs(client, redis_utils.redis_client)

    async def test_default_redis_configuration(self):
        """
        Tests if the default Redis configuration is used when
        environment variables are not set.
        """
        with patch.dict(os.environ, clear=True):
            # Re-import to load default values as environment variables are cleared
            import redis_utils as redis_utils_default

            self.assertEqual(redis_utils_default.REDIS_HOST, "localhost")
            self.assertEqual(redis_utils_default.REDIS_PORT, 6379)
            self.assertEqual(redis_utils_default.REDIS_DB, 0)
            self.assertIsInstance(redis_utils_default.redis_client, redis.Redis)
            self.assertEqual(redis_utils_default.redis_client.connection_pool.connection_kwargs.get('host'), "localhost")
            self.assertEqual(redis_utils_default.redis_client.connection_pool.connection_kwargs.get('port'), 6379)
            self.assertEqual(redis_utils_default.redis_client.connection_pool.connection_kwargs.get('db'), 0)
            self.assertTrue(redis_utils_default.redis_client.connection_pool.connection_kwargs.get('decode_responses'))

if __name__ == "__main__":
    unittest.main()