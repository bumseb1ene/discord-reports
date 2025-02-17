import json
import os

class PromptManager:
    def __init__(self, prompts_dir=".", default_lang="en"):
        self.prompts_dir = prompts_dir
        self.default_lang = default_lang
        self.cache = {}

    def load_prompts(self, lang: str):
        if lang in self.cache:
            return self.cache[lang]
        filename = os.path.join(self.prompts_dir, f"prompts_{lang}.json")
        try:
            with open(filename, "r", encoding="utf8") as f:
                prompts = json.load(f)
                self.cache[lang] = prompts
                return prompts
        except FileNotFoundError:
            if lang != self.default_lang:
                return self.load_prompts(self.default_lang)
            else:
                return {}

    def get_nested_prompt(self, key_path: str, lang: str) -> str:
        """Returns the value from a nested key path in the JSON structure.
        Example: key_path = "prompts.classification.report.templates.instructions" """
        keys = key_path.split('.')
        data = self.load_prompts(lang)
        try:
            for key in keys:
                data = data[key]
            return data
        except KeyError:
            if lang != self.default_lang:
                return self.get_nested_prompt(key_path, self.default_lang)
            else:
                return ""

    def get_prompt(self, key_path: str, lang: str) -> str:
        return self.get_nested_prompt(key_path, lang)
