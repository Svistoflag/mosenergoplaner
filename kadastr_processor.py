import re
import requests
from config import DADATA_API_KEY

class KadastrProcessor:
    def __init__(self):
        self.regex = re.compile(r"\b\d{2,3}[:\s\-_]*\d+[:\s\-_]*\d+[:\s\-_]*\d+\b")
        self.dadata_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/address"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {DADATA_API_KEY}"
        }

    def find_kadastr_in_cell(self, text):
        if not isinstance(text, str): return []
        return self.regex.findall(text)

    def convert_to_address(self, cadastral_number):
        response = requests.post(
            self.dadata_url,
            headers=self.headers,
            json={"query": cadastral_number}
        )
        if response.ok:
            suggestions = response.json().get("suggestions")
            if suggestions:
                return suggestions[0]["value"]
        return None

    def process_dataframe(self, df, address_col):
        stats = {"total_found": 0, "converted": 0, "failed": 0}
        updated_cells = []

        for idx, val in df[address_col].items():
            found = self.find_kadastr_in_cell(str(val))
            if found:
                stats["total_found"] += len(found)
                for number in found:
                    addr = self.convert_to_address(number)
                    if addr:
                        df.at[idx, address_col] = addr
                        stats["converted"] += 1
                    else:
                        stats["failed"] += 1
                updated_cells.append((idx, val, df.at[idx, address_col]))
        return df, stats, updated_cells