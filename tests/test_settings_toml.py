import unittest
import tomllib
import os

class TestParseSettingsToml(unittest.TestCase):
   
    # We're using the example file as our test input
    with open("settings.toml.example", "rb") as f:
        settings = tomllib.load(f)

    def test_selected_ocr_engine(self):
        self.assertEqual(self.settings["selected_ocr_engine"], "open_ai")

    def test_open_ai_api_key(self):
        self.assertEqual(self.settings["open_ai"]["api_key"], "Your OpenAI API key")

    def test_open_ai_model_selection(self):
        self.assertEqual(self.settings["open_ai"]["model"], "default")

    def test_mistral_api_key(self):
        self.assertEqual(self.settings["mistral_ai"]["api_key"], "Your Mistral API key")
    
    def test_mistral_model_selection(self):
        self.assertEqual(self.settings["mistral_ai"]["model"], "default")

    def test_gemini_api_key(self):
        self.assertEqual(self.settings["gemini_ai"]["api_key"], "Your Gemini API key")

    def test_gemini_model_selection(self):
        self.assertEqual(self.settings["gemini_ai"]["model"], "default")

if __name__ == '__main__':
    unittest.main()