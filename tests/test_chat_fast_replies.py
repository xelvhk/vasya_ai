from __future__ import annotations

import unittest
from unittest.mock import patch

from utils.chat_fast_replies import generate_local_chat_reply


class ChatFastRepliesTests(unittest.TestCase):
    def test_child_mode_uses_child_specific_support(self) -> None:
        response = generate_local_chat_reply("мне страшно", history_size=0, child_mode=True)
        self.assertEqual(response, "Я рядом. Давай спокойно подышим и поговорим.")

    def test_adult_mode_uses_general_support(self) -> None:
        response = generate_local_chat_reply("мне страшно", history_size=0, child_mode=False)
        self.assertEqual(response, "Понимаю. Давай спокойно. Можешь рассказать, что именно пугает?")

    def test_child_mode_story_is_available(self) -> None:
        response = generate_local_chat_reply("расскажи сказку", history_size=0, child_mode=True)
        self.assertIn("маленький фонарик", response)

    def test_weather_variants_are_routed_to_local_weather_reply(self) -> None:
        with patch(
            "utils.chat_fast_replies.get_weather_quick_reply",
            return_value="Погода в Москве: ясно, 22°C.",
        ):
            response = generate_local_chat_reply(
                "какая погода на улице",
                history_size=1,
            )
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("Погода в Москве: ясно, 22°C.", response)

    def test_weather_today_variant_is_fast(self) -> None:
        with patch(
            "utils.chat_fast_replies.get_weather_quick_reply",
            return_value="Погода в Москве: пасмурно, 16°C.",
        ):
            response = generate_local_chat_reply(
                "какая погода сегодня",
                history_size=0,
            )
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("пасмурно", response.lower())


if __name__ == "__main__":
    unittest.main()
