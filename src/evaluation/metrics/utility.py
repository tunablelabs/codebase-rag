import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from typing import Set, List
import re

def ensure_nltk_downloads():
    """
    Ensure all required NLTK data is downloaded.
    Downloads required data if not already present.
    """
    required_packages = ['punkt', 'stopwords', 'punkt_tab']
    for package in required_packages:
        try:
            nltk.data.find(f'tokenizers/{package}')
        except LookupError:
            print(f"Downloading required NLTK package: {package}")
            nltk.download(package, quiet=True)

ensure_nltk_downloads()

class TextProcessing:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
    
    def tokenize_and_clean(self, text: str) -> Set[str]:
        """
        Tokenize and clean text by removing stop words and non-alphanumeric characters
        
        Args:
            text: Input text string
            
        Returns:
            Set of cleaned tokens
        """
        tokens = word_tokenize(text.lower())
        return {token for token in tokens 
                if token.isalnum() and token not in self.stop_words}
    
    def extract_facts(self, text: str) -> List[str]:
        """
        Extract potential factual statements from text
        
        Args:
            text: Input text string
            
        Returns:
            List of extracted factual statements
        """
        sentences = sent_tokenize(text)
        facts = []
        
        for sentence in sentences:
            # Look for patterns that typically indicate facts
            if re.search(r'\bis\b|\bwas\b|\bhas\b|\bhave\b|\bcontains\b', sentence.lower()):
                facts.append(sentence)
                
        return facts
    
    def is_substring_match(self, shorter: str, longer: str) -> bool:
        """
        Check if shorter text appears in longer text with significant overlap
        
        Args:
            shorter: Shorter text string
            longer: Longer text string
            
        Returns:
            Boolean indicating if match found
        """
        shorter_words = self.tokenize_and_clean(shorter)
        longer_words = self.tokenize_and_clean(longer)
        
        if not shorter_words:
            return False
            
        # Check if significant portion of shorter text appears in longer text
        overlap = len(shorter_words & longer_words)
        return overlap / len(shorter_words) > 0.7

class TextSimilarity:
    @staticmethod
    def calculate_overlap_score(set1: Set[str], set2: Set[str]) -> float:
        """
        Calculate overlap score between two sets of tokens
        
        Args:
            set1: First set of tokens
            set2: Second set of tokens
            
        Returns:
            Overlap score between 0 and 1
        """
        if not set1 or not set2:
            return 0.0
        
        overlap = len(set1 & set2)
        return overlap / len(set1)

class TextStats:
    @staticmethod
    def word_count(text: str) -> int:
        """
        Count words in text
        
        Args:
            text: Input text string
            
        Returns:
            Number of words
        """
        return len(word_tokenize(text))