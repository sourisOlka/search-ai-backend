import httpx
import re
from pymorphy3 import MorphAnalyzer

class FixWordsService:
    def __init__(
        self
    ):
        self.morph = MorphAnalyzer()
    def word_is_known(self, word: str) -> bool:
        parsed = self.morph.parse(word)
        return any(p.is_known for p in parsed)
    
    def process_match(self,match):
            word = match.group(0)
            fixed = re.sub(r'(\w)\1+', r'\1', word, flags=re.IGNORECASE)
            if fixed.lower() != word.lower():
                if self.word_is_known(word):
                    return word
                else: 
                    if self.word_is_known(fixed):
                        return fixed

            return word
    
    def fix_broken_words(self, text):
        text = text.replace('\xad', '').replace('\xa0', ' ')
        text = text.strip(" \t\n\r")
        text = re.sub(r'\s*<\s*[\.…]+\s*>\s*', ' ', text)
        text = re.sub(r'([а-яА-Яa-zA-Z])\?([а-яА-Яa-zA-Z])', r'\1-\2', text)
        text = re.sub(r'\?([а-яА-Яa-zA-Z])', r'-\1', text)
        text = re.sub(r'([а-яА-Яa-zA-Z])\?', r'\1-', text)
        
        if len(text) < 2:
            return text

        text = re.sub(r'\s*&\s*', '-', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(_\s*){3,}', '', text)
        text = re.sub(r'(-\s*){3,}', '', text)
        text = re.sub(r'\s*\.\s*(?:\.\s*)+', '. ', text)

        if len(text) > 3:
            text = re.sub(r'\b\w*(\w)\1+\w*\b', self.process_match, text)
        return text.strip()
    
    def smart_suffix_fix(self, text):
        pattern =  r'([а-яА-ЯёЁ]{2,10})\s+([а-яА-ЯёЁ]{2,10})'
        
        def match_resolver(match):
            root = match.group(1)
            suffix = match.group(2)
            combined = (root + suffix).lower()

            if self.word_is_known(combined):
                return root + suffix
            
            return match.group(0)

        return re.sub(pattern, match_resolver, text)

fix_words_service = FixWordsService()