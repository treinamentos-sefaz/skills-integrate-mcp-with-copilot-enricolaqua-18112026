import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

import auth
import app


def request(method, path, *, data=None, cookie=None, origin=None):
    async def run():
        headers = [(b"host", b"testserver")]
        if data is not None:
            headers.append((b"content-type", b"application/json"))
        if cookie:
            headers.append((b"cookie", cookie.encode()))
        if origin:
            headers.append((b"origin", origin.encode()))
        url, _, query = path.partition("?")
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": url, "raw_path": url.encode(),
            "query_string": query.encode(), "headers": headers,
            "client": ("127.0.0.1", 1234), "server": ("testserver", 80),
        }
        body = json.dumps(data).encode() if data is not None else b""
        messages = []
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await app.app(scope, receive, send)
        start = next(message for message in messages if message["type"] == "http.response.start")
        content = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return start["status"], dict(start["headers"]), json.loads(content)

    return asyncio.run(run())


class AdminModeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.file_patch = patch.object(auth, "TEACHERS_FILE", Path(self.directory.name) / "teachers.json")
        self.iterations_patch = patch.object(auth, "ITERATIONS", 1000)
        self.file_patch.start()
        self.iterations_patch.start()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.file_patch.stop)
        self.addCleanup(self.iterations_patch.stop)
        self.original = list(app.activities["Chess Club"]["participants"])
        self.addCleanup(app.activities["Chess Club"]["participants"].__setitem__, slice(None), self.original)
        app.sessions.clear()
        salt = b"test-salt"
        auth.TEACHERS_FILE.write_text(json.dumps({
            "teacher": {"salt": salt.hex(), "hash": auth.password_hash("correct", salt)}
        }))

    def login(self):
        status, headers, _ = request("POST", "/auth/login", data={"username": "teacher", "password": "correct"})
        self.assertEqual(status, 200)
        cookie = headers[b"set-cookie"].decode()
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        return cookie.split(";", 1)[0]

    def test_public_read_and_restricted_mutations(self):
        self.assertEqual(request("GET", "/activities")[0], 200)
        path = "/activities/Chess%20Club/signup?" + urlencode({"email": "new@example.com"})
        # ASGI servers decode the path before passing it to the application.
        path = path.replace("%20", " ")
        self.assertEqual(request("POST", path)[0], 401)
        self.assertEqual(request("DELETE", path.replace("signup", "unregister"))[0], 401)
        self.assertNotIn("new@example.com", app.activities["Chess Club"]["participants"])

    def test_login_registration_logout_and_session(self):
        self.assertEqual(request("POST", "/auth/login", data={"username": "teacher", "password": "wrong"})[0], 401)
        cookie = self.login()
        self.assertTrue(request("GET", "/auth/session", cookie=cookie)[2]["authenticated"])
        path = "/activities/Chess Club/signup?" + urlencode({"email": "new@example.com"})
        self.assertEqual(request("POST", path, cookie=cookie)[0], 200)
        self.assertEqual(request("POST", path, cookie=cookie)[0], 400)
        self.assertEqual(request("DELETE", path.replace("signup", "unregister"), cookie=cookie)[0], 200)
        self.assertEqual(request("POST", "/auth/logout", cookie=cookie)[0], 200)
        self.assertEqual(request("POST", path, cookie=cookie)[0], 401)

    def test_cross_origin_and_missing_credentials(self):
        cookie = self.login()
        self.assertEqual(request("POST", "/activities/Chess Club/signup?email=x", cookie=cookie, origin="http://evil.example")[0], 403)
        auth.TEACHERS_FILE.unlink()
        self.assertEqual(request("POST", "/auth/login", data={"username": "teacher", "password": "correct"})[0], 503)

    def test_create_teacher_stores_hash_and_rejects_duplicate(self):
        with patch("auth.getpass.getpass", side_effect=["new-password", "new-password"]):
            auth.add_teacher("another")
        self.assertTrue(auth.verify_teacher("another", "new-password"))
        self.assertNotIn("new-password", auth.TEACHERS_FILE.read_text())
        with patch("auth.getpass.getpass", side_effect=["new-password", "new-password"]):
            with self.assertRaises(ValueError):
                auth.add_teacher("another")

    def test_expired_session_is_rejected(self):
        cookie = self.login()
        token = cookie.split("=", 1)[1]
        app.sessions[token] = 0
        self.assertFalse(request("GET", "/auth/session", cookie=cookie)[2]["authenticated"])
        self.assertEqual(request("POST", "/activities/Chess Club/signup?email=x", cookie=cookie)[0], 401)


if __name__ == "__main__":
    unittest.main()
